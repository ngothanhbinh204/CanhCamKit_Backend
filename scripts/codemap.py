"""Codebase Knowledge Graph (Code Graph) builder and checker for CanhCam WordPress themes."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from kitlib import (
    DEFAULT_SCAN_DIRS,
    EXCLUDED_DIRS,
    SECTION_RE,
    classify_acf_json_key,
    classify_component_tier,
    collect_scannable_files,
    find_theme_root,
    hash_file_normalized,
    iter_acf_fields,
)


KIT_ROOT = Path(__file__).resolve().parents[1]
KIT_VERSION = (KIT_ROOT / "KIT_VERSION").read_text(encoding="utf-8").strip()

# Regex patterns for PHP static/dynamic extraction
TEMPLATE_NAME_RE = re.compile(r"Template Name:\s*(.+)", re.I)
REGISTER_CPT_RE = re.compile(r"\b(?:register_post_type|create_post_type)\(\s*['\"]([^'\"]+)['\"](.*?)\)\s*;", re.S)
REGISTER_TAX_RE = re.compile(
    r"\bregister_taxonomy\(\s*['\"]([^'\"]+)['\"]\s*,\s*(?:array\(([^)]*)\)|\[([^\]]*)\]|['\"]([^'\"]+)['\"])(.*?)\)\s*;",
    re.S,
)
CREATE_TAX_RE = re.compile(
    r"\bcreate_taxonomy\(\s*['\"]([^'\"]+)['\"]\s*,\s*(?:array\(|\[)(.*?)(?:\)|\])\s*\)\s*;",
    re.S,
)
OBJECT_TYPE_RE = re.compile(
    r"['\"]object_type['\"]\s*=>\s*(?:array\(([^)]*)\)|\[([^\]]*)\]|['\"]([^'\"]+)['\"])",
    re.S,
)
REWRITE_SLUG_RE = re.compile(r"['\"]slug['\"]\s*=>\s*['\"]([^'\"]+)['\"]")
HIERARCHICAL_RE = re.compile(r"['\"]hierarchical['\"]\s*=>\s*(true|false)", re.I)

OPTIONS_VAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['\"]([^'\"]+)['\"]\s*;")
ACF_OPTIONS_CALL_RE = re.compile(r"acf_add_options_(?:sub_)?page\(\s*(?:array\(|\[)(.*?)(?:\)|\])\s*\)", re.S)
MENU_SLUG_LITERAL_RE = re.compile(r"['\"]menu_slug['\"]\s*=>\s*['\"]([^'\"]+)['\"]")
MENU_SLUG_VAR_RE = re.compile(r"['\"]menu_slug['\"]\s*=>\s*\$([A-Za-z_][A-Za-z0-9_]*)")

FUNC_DEF_RE = re.compile(r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", re.M)
HOOK_CALL_RE = re.compile(r"\b(add_action|add_filter)\(\s*['\"]([^'\"]+)['\"]\s*,\s*([^,\n\)]+)")
WP_PARSE_ARGS_RE = re.compile(
    r"wp_parse_args\(\s*\$args[^,]*,\s*(?:array\(|\[)(.*?)(?:\)|\])\s*\)\s*;",
    re.S,
)
ARRAY_KEY_RE = re.compile(r"['\"]([A-Za-z0-9_]+)['\"]\s*=>")

GET_TEMPLATE_PART_CALL_RE = re.compile(r"get_template_part\(\s*([^,\n\)]+)(?:\s*,\s*([^,\n\)]+))?")
STRING_TEMPLATE_PATH_RE = re.compile(r"['\"]((?:template-parts|modules)/[A-Za-z0-9_/-]+)['\"]")

ACF_READ_CALL_RE = re.compile(
    r"\b(get_field|the_field|have_rows|get_sub_field|canhcam_get_option)\(\s*([^,\n\)]+)"
)

WP_QUERY_BLOCK_RE = re.compile(
    r"(?:new\s+WP_Query|get_posts)\(\s*(?:array\(|\[|\$[A-Za-z_][A-Za-z0-9_]*)(.*?)\)\s*;",
    re.S,
)
POST_TYPE_ARG_RE = re.compile(
    r"['\"]post_type['\"]\s*=>\s*(?:['\"]([^'\"]+)['\"]|array\(([^)]*)\)|\[([^\]]*)\]|(\$[A-Za-z_][A-Za-z0-9_\[\]'\"-]*))"
)


def strip_quotes(expr: str) -> tuple[bool, str]:
    s = expr.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return True, s[1:-1]
    return False, s


def build_graph(theme_root: Path, scan_dirs: tuple[str, ...] = DEFAULT_SCAN_DIRS) -> dict[str, Any]:
    root = theme_root.resolve()
    files = collect_scannable_files(root, scan_dirs, EXCLUDED_DIRS)

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str, str, str]] = set()

    def add_node(node_id: str, node_type: str, **attrs: Any) -> None:
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "type": node_type, **attrs}
        else:
            nodes[node_id].update(attrs)

    def add_edge(src: str, dst: str, rel: str, confidence: str) -> None:
        key = (src, dst, rel, confidence)
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append({"source": src, "target": dst, "type": rel, "confidence": confidence})

    html_files = [f for f in files if f.suffix.lower() == ".html"]
    json_files = [f for f in files if f.suffix.lower() == ".json"]
    php_files = [f for f in files if f.suffix.lower() == ".php"]

    # 1. Scan UI/*.html -> UISection nodes
    ui_sections_by_file: dict[str, list[str]] = {}
    section_to_html: dict[str, list[str]] = defaultdict(list)
    for hfile in html_files:
        rel = hfile.relative_to(root).as_posix()
        content = hfile.read_text(encoding="utf-8", errors="ignore")
        classes: list[str] = []
        for cls in SECTION_RE.findall(content):
            if cls not in classes:
                classes.append(cls)
            section_node_id = f"UISection:{cls}"
            add_node(section_node_id, "UISection", name=cls, path=rel)
            if rel not in section_to_html[cls]:
                section_to_html[cls].append(rel)
        ui_sections_by_file[rel] = classes

    for cls, hlist in section_to_html.items():
        nodes[f"UISection:{cls}"]["html_files"] = sorted(hlist)
        nodes[f"UISection:{cls}"]["page_count"] = len(hlist)

    # 2. Pre-classify PHP files into Template vs Component vs Inc
    php_rel_set: set[str] = set()
    php_contents: dict[str, str] = {}
    for pfile in php_files:
        rel = pfile.relative_to(root).as_posix()
        php_rel_set.add(rel)
        text = pfile.read_text(encoding="utf-8", errors="ignore")
        php_contents[rel] = text

        tier = classify_component_tier(rel)
        if tier is not None:
            parse_args_keys: list[str] = []
            for block in WP_PARSE_ARGS_RE.findall(text):
                for k in ARRAY_KEY_RE.findall(block):
                    if k not in parse_args_keys:
                        parse_args_keys.append(k)
            add_node(
                rel,
                "Component",
                path=rel,
                tier=tier,
                parse_args=parse_args_keys,
            )
        elif not rel.startswith("inc/") and rel not in ("functions.php", "comments-helper.php"):
            m_tpl = TEMPLATE_NAME_RE.search(text)
            tpl_name = m_tpl.group(1).strip() if m_tpl else ""
            add_node(rel, "Template", path=rel, template_name=tpl_name)

    # 3. Scan PHP for CPT, Taxonomy, OptionsPage, Functions, Hooks, AjaxActions
    for rel, text in sorted(php_contents.items()):
        # Local string variables (e.g. $options_menu_slug = 'theme-settings')
        local_vars = dict(OPTIONS_VAR_RE.findall(text))

        # CPT registrations
        for cpt_slug, body in REGISTER_CPT_RE.findall(text):
            m_rw = REWRITE_SLUG_RE.search(body)
            rw_slug = m_rw.group(1) if m_rw else cpt_slug
            cpt_id = f"CPT:{cpt_slug}"
            add_node(cpt_id, "CPT", slug=cpt_slug, rewrite_slug=rw_slug, source=rel)
            add_edge(rel, cpt_id, "registers", "static")

        # Taxonomy registrations
        for match in REGISTER_TAX_RE.finditer(text):
            tax_slug = match.group(1)
            cpts_raw = match.group(2) or match.group(3) or match.group(4) or ""
            body = match.group(5) or ""
            cpts = re.findall(r"['\"]([^'\"]+)['\"]", cpts_raw) if ("'" in cpts_raw or '"' in cpts_raw) else [cpts_raw.strip()]
            cpts = [c for c in cpts if c]
            m_rw = REWRITE_SLUG_RE.search(body)
            rw_slug = m_rw.group(1) if m_rw else tax_slug
            m_hier = HIERARCHICAL_RE.search(body)
            is_hier = m_hier.group(1).lower() == "true" if m_hier else False
            tax_id = f"Taxonomy:{tax_slug}"
            add_node(
                tax_id,
                "Taxonomy",
                slug=tax_slug,
                post_types=cpts,
                hierarchical=is_hier,
                rewrite_slug=rw_slug,
                source=rel,
            )
            add_edge(rel, tax_id, "registers", "static")

        for tax_slug, body in CREATE_TAX_RE.findall(text):
            m_obj = OBJECT_TYPE_RE.search(body)
            cpts_raw = (m_obj.group(1) or m_obj.group(2) or m_obj.group(3) or "") if m_obj else ""
            cpts = re.findall(r"['\"]([^'\"]+)['\"]", cpts_raw) if ("'" in cpts_raw or '"' in cpts_raw) else [cpts_raw.strip()]
            cpts = [c for c in cpts if c]
            m_rw = REWRITE_SLUG_RE.search(body)
            rw_slug = m_rw.group(1) if m_rw else tax_slug
            m_hier = HIERARCHICAL_RE.search(body)
            is_hier = m_hier.group(1).lower() == "true" if m_hier else False
            tax_id = f"Taxonomy:{tax_slug}"
            add_node(
                tax_id,
                "Taxonomy",
                slug=tax_slug,
                post_types=cpts,
                hierarchical=is_hier,
                rewrite_slug=rw_slug,
                source=rel,
            )
            add_edge(rel, tax_id, "registers", "static")

        # Options pages
        for block in ACF_OPTIONS_CALL_RE.findall(text):
            m_lit = MENU_SLUG_LITERAL_RE.search(block)
            m_var = MENU_SLUG_VAR_RE.search(block)
            if m_lit:
                opt_slug = m_lit.group(1)
                conf = "static"
            elif m_var and m_var.group(1) in local_vars:
                opt_slug = local_vars[m_var.group(1)]
                conf = "static"
            elif m_var:
                opt_slug = f"${m_var.group(1)}"
                conf = "dynamic"
            else:
                opt_slug = "acf-options"
                conf = "dynamic"
            opt_id = f"OptionsPage:{opt_slug}"
            add_node(opt_id, "OptionsPage", slug=opt_slug, source=rel)
            add_edge(rel, opt_id, "registers", conf)

        # Functions (in inc/ or root helper files)
        for fn_name, fn_params in FUNC_DEF_RE.findall(text):
            fn_id = f"Function:{fn_name}"
            params_clean = " ".join(fn_params.split())
            add_node(fn_id, "Function", name=fn_name, params=params_clean, source=rel)

        # Hooks & AJAX Actions
        for kind, hook_name, callback_raw in HOOK_CALL_RE.findall(text):
            cb_clean = callback_raw.strip().strip("'\"")
            if hook_name.startswith("wp_ajax_nopriv_"):
                action_name = hook_name[len("wp_ajax_nopriv_"):]
                ajax_id = f"AjaxAction:{action_name}"
                add_node(ajax_id, "AjaxAction", action=action_name, callback=cb_clean, nopriv=True, source=rel)
                add_edge(rel, ajax_id, "hooks_into", "static")
            elif hook_name.startswith("wp_ajax_"):
                action_name = hook_name[len("wp_ajax_"):]
                ajax_id = f"AjaxAction:{action_name}"
                add_node(ajax_id, "AjaxAction", action=action_name, callback=cb_clean, source=rel)
                add_edge(rel, ajax_id, "hooks_into", "static")
            else:
                hook_id = f"Hook:{hook_name}"
                add_node(hook_id, "Hook", name=hook_name, kind=kind, source=rel)
                add_edge(rel, hook_id, "hooks_into", "static")

    # 4. Scan acf-json/*.json -> ACFGroup, ACFField (or CPT/Taxonomy/OptionsPage by key prefix)
    field_name_to_keys: dict[str, list[str]] = defaultdict(list)
    acf_groups_summary: list[dict[str, Any]] = []

    for jfile in json_files:
        rel = jfile.relative_to(root).as_posix()
        try:
            data = json.loads(jfile.read_text(encoding="utf-8"))
        except Exception:
            continue

        top_key = data.get("key", "")
        key_kind = classify_acf_json_key(top_key)

        if key_kind == "post_type":
            cpt_slug = data.get("post_type") or top_key
            cpt_id = f"CPT:{cpt_slug}"
            add_node(cpt_id, "CPT", slug=cpt_slug, source=rel)
            add_edge(rel, cpt_id, "registers", "static")
            continue
        if key_kind == "taxonomy":
            tax_slug = data.get("taxonomy") or top_key
            tax_id = f"Taxonomy:{tax_slug}"
            add_node(tax_id, "Taxonomy", slug=tax_slug, source=rel)
            add_edge(rel, tax_id, "registers", "static")
            continue
        if key_kind == "options_page":
            opt_slug = data.get("menu_slug") or top_key
            opt_id = f"OptionsPage:{opt_slug}"
            add_node(opt_id, "OptionsPage", slug=opt_slug, source=rel)
            add_edge(rel, opt_id, "registers", "static")
            continue

        # Default: ACFGroup
        group_id = f"ACFGroup:{top_key}"
        title = data.get("title", "")
        location_rules = data.get("location", [])
        loc_strings: list[str] = []

        for or_group in location_rules:
            if not isinstance(or_group, list):
                continue
            and_parts: list[str] = []
            for rule in or_group:
                if not isinstance(rule, dict):
                    continue
                param = str(rule.get("param", ""))
                op = str(rule.get("operator", "=="))
                val = str(rule.get("value", ""))
                and_parts.append(f"{param} {op} {val}")
                conf = "static" if op == "==" and len(or_group) == 1 else "dynamic"

                if param == "page_template" and val in php_rel_set:
                    add_edge(group_id, val, "located_on", conf)
                elif param == "page_type" and val == "front_page":
                    target_tpl = "templates/template-home.php" if "templates/template-home.php" in php_rel_set else "front-page.php"
                    add_edge(group_id, target_tpl, "located_on", conf)
                elif param == "post_type":
                    add_edge(group_id, f"CPT:{val}", "located_on", conf)
                    for cand in (f"single-{val}.php", f"archive-{val}.php", "single.php", "home.php"):
                        if cand in php_rel_set and (cand.endswith(f"-{val}.php") or val == "post"):
                            add_edge(group_id, cand, "located_on", conf)
                elif param == "taxonomy":
                    add_edge(group_id, f"Taxonomy:{val}", "located_on", conf)
                    cand = f"taxonomy-{val}.php" if val != "category" else "category.php"
                    if cand in php_rel_set:
                        add_edge(group_id, cand, "located_on", conf)
                elif param == "options_page":
                    add_edge(group_id, f"OptionsPage:{val}", "located_on", conf)
                else:
                    add_edge(group_id, f"Location:{param}:{val}", "located_on", "dynamic")

            if and_parts:
                loc_strings.append(" AND ".join(and_parts))

        # Top-level tabs and fields for acf-schema.md (no sub_fields in shard!)
        tabs_structure: list[dict[str, Any]] = []
        current_tab = {"label": "(Mặc định / Không Tab)", "key": "-", "fields": []}

        for f in data.get("fields", []):
            if not isinstance(f, dict):
                continue
            ftype = f.get("type", "")
            fname = f.get("name", "")
            fkey = f.get("key", "")
            flabel = f.get("label", "")
            if ftype == "tab":
                if current_tab["fields"] or current_tab["key"] != "-":
                    tabs_structure.append(current_tab)
                current_tab = {"label": flabel or fname or fkey, "key": fkey, "fields": []}
            else:
                current_tab["fields"].append({"name": fname, "type": ftype, "key": fkey, "label": flabel})
        if current_tab["fields"] or current_tab["key"] != "-":
            tabs_structure.append(current_tab)

        # Full recursive fields for graph nodes and uses_field lookup
        for fpath, field in iter_acf_fields(data.get("fields", [])):
            fkey = field.get("key", "")
            fname = field.get("name", "")
            ftype = field.get("type", "")
            if fkey:
                field_node_id = f"ACFField:{fkey}"
                add_node(
                    field_node_id,
                    "ACFField",
                    key=fkey,
                    name=fname,
                    field_type=ftype,
                    group_key=top_key,
                    path=fpath,
                    source=rel,
                )
                if fname:
                    field_name_to_keys[fname].append(field_node_id)

        add_node(
            group_id,
            "ACFGroup",
            key=top_key,
            title=title,
            path=rel,
            locations=loc_strings,
        )
        acf_groups_summary.append(
            {
                "key": top_key,
                "title": title,
                "path": rel,
                "locations": loc_strings,
                "tabs": tabs_structure,
            }
        )

    # 5. Scan PHP files for includes, uses_field, queries, and renders (UI parity)
    for rel, text in sorted(php_contents.items()):
        # 5a. includes (get_template_part)
        has_dynamic_include = False
        for m_inc in GET_TEMPLATE_PART_CALL_RE.finditer(text):
            arg1_raw = m_inc.group(1)
            arg2_raw = m_inc.group(2)
            is_lit1, val1 = strip_quotes(arg1_raw)
            if is_lit1:
                if arg2_raw is not None:
                    is_lit2, val2 = strip_quotes(arg2_raw)
                    if is_lit2 and val2:
                        cand_specific = f"{val1}-{val2}.php"
                        cand_base = f"{val1}.php"
                        target = cand_specific if cand_specific in php_rel_set else cand_base
                        add_edge(rel, target, "includes", "static")
                    else:
                        cand_base = f"{val1}.php"
                        add_edge(rel, cand_base, "includes", "dynamic")
                else:
                    add_edge(rel, f"{val1}.php", "includes", "static")
            else:
                has_dynamic_include = True
                expr_clean = " ".join(arg1_raw.strip().split())
                add_edge(rel, f"dynamic:get_template_part({expr_clean})", "includes", "dynamic")

        if has_dynamic_include:
            for str_path in STRING_TEMPLATE_PATH_RE.findall(text):
                cand = f"{str_path}.php"
                if cand in php_rel_set:
                    add_edge(rel, cand, "includes", "literal-in-array")

        # 5b. uses_field (get_field, the_field, have_rows, get_sub_field, canhcam_get_option)
        for fn_call, arg1_raw in ACF_READ_CALL_RE.findall(text):
            # Ignore helper definition line `function canhcam_get_option($key`
            if fn_call == "canhcam_get_option" and f"function canhcam_get_option({arg1_raw}" in text:
                continue
            is_lit, val = strip_quotes(arg1_raw)
            if is_lit and val:
                matched_nodes = field_name_to_keys.get(val, [])
                if matched_nodes:
                    for fnode_id in matched_nodes:
                        add_edge(rel, fnode_id, "uses_field", "static")
                else:
                    add_edge(rel, f"ACFFieldName:{val}", "uses_field", "static")
            else:
                expr_clean = " ".join(arg1_raw.strip().split())
                add_edge(rel, f"dynamic:{fn_call}({expr_clean})", "uses_field", "dynamic")

        # 5c. queries (WP_Query / get_posts post_type)
        for m_pt in POST_TYPE_ARG_RE.finditer(text):
            lit_pt, arr1, arr2, var_pt = m_pt.groups()
            if lit_pt:
                add_edge(rel, f"CPT:{lit_pt}", "queries", "static")
            elif arr1 or arr2:
                raw_arr = arr1 or arr2
                for pt in re.findall(r"['\"]([^'\"]+)['\"]", raw_arr):
                    add_edge(rel, f"CPT:{pt}", "queries", "literal-in-array")
            elif var_pt:
                add_edge(rel, f"dynamic:post_type({var_pt.strip()})", "queries", "dynamic")

        # 5d. renders (UI section ↔ PHP using check_parity logic)
        php_sec_classes = set(SECTION_RE.findall(text))
        for sec_cls in sorted( section_to_html.keys() ):
            if sec_cls in php_sec_classes or f'"{sec_cls}' in text or f"'{sec_cls}" in text or f" {sec_cls} " in text:
                add_edge(rel, f"UISection:{sec_cls}", "renders", "static")

    sorted_nodes = [nodes[k] for k in sorted(nodes.keys())]
    sorted_edges = sorted(edges, key=lambda e: (e["type"], e["source"], e["target"], e["confidence"]))

    return {
        "nodes": sorted_nodes,
        "edges": sorted_edges,
        "acf_groups_summary": sorted(acf_groups_summary, key=lambda g: g["path"]),
        "ui_sections_by_file": dict(sorted(ui_sections_by_file.items())),
        "scannable_files": files,
    }


def split_if_over_limit(lines: list[str], max_lines: int = 195) -> list[list[str]]:
    if len(lines) <= max_lines:
        return [lines]
    chunks: list[list[str]] = []
    header = lines[:4]
    body = lines[4:]
    step = max_lines - len(header)
    for i in range(0, len(body), step):
        chunks.append(header + body[i : i + step])
    return chunks


def render_markdown_outputs(graph_data: dict[str, Any]) -> tuple[str, dict[str, str]]:
    nodes_by_id = {n["id"]: n for n in graph_data["nodes"]}
    edges = graph_data["edges"]

    cpts = [n for n in graph_data["nodes"] if n["type"] == "CPT"]
    taxonomies = [n for n in graph_data["nodes"] if n["type"] == "Taxonomy"]
    options_pages = [n for n in graph_data["nodes"] if n["type"] == "OptionsPage"]
    templates = [n for n in graph_data["nodes"] if n["type"] == "Template"]
    components = [n for n in graph_data["nodes"] if n["type"] == "Component"]
    functions = [n for n in graph_data["nodes"] if n["type"] == "Function"]
    hooks = [n for n in graph_data["nodes"] if n["type"] == "Hook"]
    ajax_actions = [n for n in graph_data["nodes"] if n["type"] == "AjaxAction"]
    ui_sections = [n for n in graph_data["nodes"] if n["type"] == "UISection"]

    # Calculate dynamic/literal-in-array edges per source file
    unresolved_by_file: dict[str, list[dict[str, str]]] = defaultdict(list)
    for e in edges:
        if e["confidence"] in ("dynamic", "literal-in-array"):
            unresolved_by_file[e["source"]].append(e)

    # Map Template -> ACF Groups & UI HTML
    tpl_to_groups: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e["type"] == "located_on" and e["source"].startswith("ACFGroup:"):
            gkey = e["source"].split(":", 1)[1]
            tpl_to_groups[e["target"]].append(gkey)

    # Map PHP file -> included PHP files
    inc_by_src: dict[str, list[tuple[str, str]]] = defaultdict(list)
    inc_by_dst: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for e in edges:
        if e["type"] == "includes":
            inc_by_src[e["source"]].append((e["target"], e["confidence"]))
            inc_by_dst[e["target"]].append((e["source"], e["confidence"]))

    # Map PHP file -> rendered UI sections
    renders_by_php: dict[str, list[str]] = defaultdict(list)
    renders_by_sec: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e["type"] == "renders" and e["target"].startswith("UISection:"):
            sec_cls = e["target"].split(":", 1)[1]
            renders_by_php[e["source"]].append(sec_cls)
            renders_by_sec[sec_cls].append(e["source"])

    # Determine matching UI HTML for each template based on rendered page-specific sections
    tpl_to_html: dict[str, list[str]] = defaultdict(list)
    for tpl in templates:
        tpath = tpl["id"]
        visited = {tpath}
        queue = [tpath]
        while queue:
            cur = queue.pop(0)
            for dst, _ in inc_by_src.get(cur, []):
                if dst not in visited and dst in nodes_by_id:
                    visited.add(dst)
                    queue.append(dst)
        sec_set: set[str] = set()
        for p in visited:
            sec_set.update(renders_by_php.get(p, []))
        for hfile, hsecs in graph_data["ui_sections_by_file"].items():
            page_specific_hsecs = [s for s in hsecs if s not in ("section-NomalBanner", "popup-wrapper")]
            if page_specific_hsecs and any(s in sec_set for s in page_specific_hsecs):
                tpl_to_html[tpath].append(hfile)

    # --- 1. CODEMAP.md (<= 150 lines) ---
    cm: list[str] = [
        "> Chỉ mục điều hướng, không phải nguồn sự thật. Mở file thật trước khi sửa.",
        "",
        f"# Bản đồ cấu trúc Theme (Code Graph — Kit v{KIT_VERSION})",
        "",
        "## 1. Thứ tự đọc khuyến nghị theo vai trò",
        "- **Mọi vai trò:** `PROJECT_OVERRIDES.md` → `CODEMAP.md` → Shard theo vai trò → File code/HTML thật.",
        "- **Architect (`MAPPING`):** `.ai-map/shards/architecture.md` + file `UI/*.html` được giao.",
        "- **ACF Builder (`ACF`):** `.ai-map/shards/acf-schema.md` + `acf-json/` được giao.",
        "- **Coder (`CODING`):** `.ai-map/shards/acf-schema.md` + `.ai-map/shards/php-contracts.md` + file PHP/HTML thật.",
        "- **Reviewer (`REVIEW`):** Chạy `codemap.py check`, đọc `.ai-map/shards/php-contracts.md` để tra ảnh hưởng chéo; **bắt buộc đọc file thật** khi chấm 18 ZTR.",
        "",
        "## 2. Tổng quan CPT, Taxonomy & Options Pages",
    ]
    for c in cpts:
        cm.append(f"- **CPT `{c['slug']}`**: rewrite `{c.get('rewrite_slug', '')}` (`{c.get('source', '')}`)")
    for t in taxonomies:
        hier = "Hierarchical" if t.get("hierarchical") else "Auxiliary/Flat"
        pts = ", ".join(t.get("post_types", []))
        cm.append(f"- **Taxonomy `{t['slug']}`** ({hier} -> `{pts}`): rewrite `{t.get('rewrite_slug', '')}` (`{t.get('source', '')}`)")
    for o in options_pages:
        cm.append(f"- **Options Page `{o['slug']}`**: `{o.get('source', '')}`")

    cm.extend(["", "## 3. Danh sách Component theo 4 Tầng (Blueprint §2)"])
    for tier_num, tier_label in (
        (1, "Tầng 1 — Global System Modules (`modules/`)"),
        (2, "Tầng 2 — Shared Business Sections (`template-parts/shared/`)"),
        (3, "Tầng 3 — Atomic Data Cards (`template-parts/cards/`)"),
        (4, "Tầng 4 — Page-Specific Sections (`template-parts/{page}/`)"),
    ):
        tier_items = [c["id"] for c in components if c.get("tier") == tier_num]
        if tier_items:
            cm.append(f"- **{tier_label}** ({len(tier_items)}): " + ", ".join(f"`{p}`" for p in tier_items))
        else:
            cm.append(f"- **{tier_label}** (0): *(chưa có)*")

    cm.extend([
        "",
        "## 4. Bảng ánh xạ Template ↔ ACF Group ↔ UI HTML",
        "| Template PHP | UI HTML tương ứng | ACF Group (`located_on`) | Số part `includes` |",
        "|---|---|---|---|",
    ])
    for tpl in templates:
        tpath = tpl["id"]
        hfiles = ", ".join(f"`{h}`" for h in tpl_to_html.get(tpath, [])) or "—"
        groups = ", ".join(f"`{g}`" for g in sorted(set(tpl_to_groups.get(tpath, [])))) or "—"
        inc_count = len(inc_by_src.get(tpath, []))
        cm.append(f"| `{tpath}` | {hfiles} | {groups} | {inc_count} |")

    cm.extend([
        "",
        "## 5. Điểm không phân giải được tĩnh (Dynamic / Literal-in-Array Edges)",
        "| File / Nguồn | Số cạnh `dynamic` | Số cạnh `literal-in-array` | Chi tiết tóm tắt |",
        "|---|---|---|---|",
    ])
    for src in sorted(unresolved_by_file.keys()):
        elist = unresolved_by_file[src]
        dyn_c = sum(1 for e in elist if e["confidence"] == "dynamic")
        lit_c = sum(1 for e in elist if e["confidence"] == "literal-in-array")
        details = "; ".join(f"`{e['type']} -> {e['target']}` ({e['confidence']})" for e in elist[:3])
        if len(elist) > 3:
            details += f" (+{len(elist) - 3})"
        cm.append(f"| `{src}` | {dyn_c} | {lit_c} | {details} |")

    codemap_md = "\n".join(cm[:150]) + "\n"

    # --- 2. Shard: architecture.md ---
    arch_lines: list[str] = [
        "> Shard điều hướng cho `wp-architect` & `main`. Không phải nguồn sự thật; luôn mở file thật khi cần xác minh.",
        "",
        "# Shard 1: Kiến trúc Đa Trang, UI Inventory & Component 4 Tầng",
        "",
        "## 1. Cross-Page UI Section Inventory (`UI/*.html` ↔ PHP `renders`)",
        "| Section First Class | Số trang | Phân tầng gợi ý | File HTML | File PHP render (`renders`) |",
        "|---|---|---|---|---|",
    ]
    for sec in sorted(ui_sections, key=lambda s: (-s.get("page_count", 0), s["name"])):
        sname = sec["name"]
        pcount = sec.get("page_count", 0)
        tier_sug = "Tier 1/2 (Global/Shared)" if pcount >= 2 else "Tier 4 (Page)"
        hlist = ", ".join(sec.get("html_files", []))
        plist = ", ".join(f"`{p}`" for p in sorted(renders_by_sec.get(sname, []))) or "*(chưa map)*"
        arch_lines.append(f"| `{sname}` | {pcount} | {tier_sug} | {hlist} | {plist} |")

    arch_lines.extend([
        "",
        "## 2. Chi tiết Component Tầng 1–3 & Hợp đồng `wp_parse_args`",
        "| Component Path | Tầng | Khóa `$args` (`wp_parse_args`) | Được gọi bởi (`includes`) |",
        "|---|---|---|---|",
    ])
    for comp in [c for c in components if c.get("tier") in (1, 2, 3)]:
        cpath = comp["id"]
        pargs = ", ".join(f"`{k}`" for k in comp.get("parse_args", [])) or "—"
        callers = ", ".join(f"`{src}` ({conf})" for src, conf in sorted(inc_by_dst.get(cpath, []))) or "—"
        arch_lines.append(f"| `{cpath}` | Tầng {comp['tier']} | {pargs} | {callers} |")

    arch_lines.extend([
        "",
        "## 3. Component Tầng 4 (Page-Specific Sections)",
        "| Component Path | Được gọi bởi Template | Render UI Section |",
        "|---|---|---|",
    ])
    for comp in [c for c in components if c.get("tier") == 4]:
        cpath = comp["id"]
        callers = ", ".join(f"`{src}`" for src, _ in sorted(inc_by_dst.get(cpath, []))) or "—"
        rsecs = ", ".join(f"`{s}`" for s in renders_by_php.get(cpath, [])) or "—"
        arch_lines.append(f"| `{cpath}` | {callers} | {rsecs} |")

    # --- 3. Shard: acf-schema.md (Group -> Location -> Tab -> Top-level field ONLY) ---
    acf_lines: list[str] = [
        "> Shard điều hướng cho `acf-builder` & `wp-coder`. Chỉ liệt kê field cấp cao nhất (không in `sub_fields`).",
        "",
        "# Shard 2: Lược đồ ACF Local JSON (`acf-json/*.json`)",
        "",
    ]
    for grp in graph_data["acf_groups_summary"]:
        locs = " OR ".join(f"`{l}`" for l in grp["locations"]) or "—"
        acf_lines.append(f"## `{grp['path']}` — Key: `{grp['key']}` ({grp['title']})")
        acf_lines.append(f"- **Location:** {locs}")
        for tab in grp["tabs"]:
            f_summaries = [
                f"`{f['name'] or '(no-name)'}` ({f['type']}, `{f['key']}`)"
                for f in tab["fields"]
            ]
            joined = ", ".join(f_summaries) if f_summaries else "*(trống)*"
            acf_lines.append(f"- **Tab `{tab['label']}` (`{tab['key']}`):** {joined}")
        acf_lines.append("")

    # --- 4. Shard: php-contracts.md ---
    php_lines: list[str] = [
        "> Shard điều hướng cho `wp-coder` & `wp-reviewer`. Dùng để tra cứu helper, hook, AJAX và phụ thuộc file.",
        "",
        "# Shard 3: Hợp đồng PHP, Helper, Hooks & Đồ thị phụ thuộc",
        "",
        "## 1. Helper & Functions (`inc/*.php`, `functions.php`)",
        "| Hàm | Tham số | File khai báo |",
        "|---|---|---|",
    ]
    for fn in functions:
        php_lines.append(f"| `{fn['name']}` | `({fn.get('params', '')})` | `{fn.get('source', '')}` |")

    php_lines.extend([
        "",
        "## 2. AJAX Actions & WordPress Hooks",
        "| Loại | Tên Hook / Action | Callback / Chi tiết | File nguồn |",
        "|---|---|---|---|",
    ])
    for aj in ajax_actions:
        np = " (có `nopriv`)" if aj.get("nopriv") else ""
        php_lines.append(f"| `AjaxAction` | `wp_ajax_{aj['action']}`{np} | `{aj.get('callback', '')}` | `{aj.get('source', '')}` |")
    for hk in hooks:
        php_lines.append(f"| `{hk.get('kind', 'hook')}` | `{hk['name']}` | — | `{hk.get('source', '')}` |")

    php_lines.extend([
        "",
        "## 3. Đồ thị `includes`, `queries` & `uses_field` theo File PHP",
        "| File PHP | `includes` (Template Parts) | `queries` (CPT) | Số field ACF đọc (`uses_field`) |",
        "|---|---|---|---|",
    ])
    uses_by_src: dict[str, list[tuple[str, str]]] = defaultdict(list)
    queries_by_src: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for e in edges:
        if e["type"] == "uses_field":
            uses_by_src[e["source"]].append((e["target"], e["confidence"]))
        elif e["type"] == "queries":
            queries_by_src[e["source"]].append((e["target"], e["confidence"]))

    all_php_sources = sorted(set(inc_by_src.keys()) | set(queries_by_src.keys()) | set(uses_by_src.keys()))
    for rel in all_php_sources:
        incs = ", ".join(f"`{t}` ({c})" for t, c in inc_by_src.get(rel, [])) or "—"
        qrys = ", ".join(f"`{t}` ({c})" for t, c in queries_by_src.get(rel, [])) or "—"
        ufields = uses_by_src.get(rel, [])
        dyn_u = sum(1 for _, c in ufields if c != "static")
        u_summary = f"{len(ufields)} field(s)" + (f" ({dyn_u} dynamic)" if dyn_u else "")
        php_lines.append(f"| `{rel}` | {incs} | {qrys} | {u_summary} |")

    shards: dict[str, str] = {}
    for base_name, raw_lines in (
        ("architecture", arch_lines),
        ("acf-schema", acf_lines),
        ("php-contracts", php_lines),
    ):
        parts = split_if_over_limit(raw_lines, max_lines=195)
        if len(parts) == 1:
            shards[f"{base_name}.md"] = "\n".join(parts[0]).rstrip() + "\n"
        else:
            for idx, part in enumerate(parts, start=1):
                fname = f"{base_name}.md" if idx == 1 else f"{base_name}-part{idx}.md"
                shards[fname] = "\n".join(part).rstrip() + "\n"

    return codemap_md, shards


def cmd_build(theme_root: Path) -> int:
    root = theme_root.resolve()
    graph_data = build_graph(root, DEFAULT_SCAN_DIRS)
    codemap_md, shards = render_markdown_outputs(graph_data)

    ai_map_dir = root / ".ai-map"
    shards_dir = ai_map_dir / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)

    # Write CODEMAP.md
    (root / "CODEMAP.md").write_text(codemap_md, encoding="utf-8")

    # Write shards (remove stale shard files first)
    for old_shard in shards_dir.glob("*.md"):
        if old_shard.name not in shards:
            old_shard.unlink()
    for sname, scontent in sorted(shards.items()):
        (shards_dir / sname).write_text(scontent, encoding="utf-8")

    # Write graph.json
    graph_payload = {
        "kit_version": KIT_VERSION,
        "nodes": graph_data["nodes"],
        "edges": graph_data["edges"],
    }
    (ai_map_dir / "graph.json").write_text(
        json.dumps(graph_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Write meta.json with normalized SHA-256 content hashes
    file_hashes: dict[str, str] = {}
    for fpath in graph_data["scannable_files"]:
        rel = fpath.relative_to(root).as_posix()
        file_hashes[rel] = hash_file_normalized(fpath)

    meta_payload = {
        "kit_version": KIT_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scan_dirs": list(DEFAULT_SCAN_DIRS),
        "files": file_hashes,
    }
    (ai_map_dir / "meta.json").write_text(
        json.dumps(meta_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"[PASS] CODEMAP built at {root.as_posix()}: "
        f"{len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges, "
        f"{len(file_hashes)} files hashed, {len(shards)} shards written."
    )
    return 0


def cmd_check(theme_root: Path) -> int:
    """Read-only check comparing current file SHA-256 hashes against .ai-map/meta.json."""
    root = theme_root.resolve()
    meta_path = root / ".ai-map" / "meta.json"
    if not meta_path.is_file():
        print(f"[WARN] Code map not found ({meta_path.as_posix()} missing). Run `codemap.py build`.")
        return 2

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[WARN] Invalid .ai-map/meta.json ({exc}). Run `codemap.py build`.")
        return 2

    scan_dirs = tuple(meta.get("scan_dirs", DEFAULT_SCAN_DIRS))
    recorded_files: dict[str, str] = meta.get("files", {})

    current_files_list = collect_scannable_files(root, scan_dirs, EXCLUDED_DIRS)
    current_hashes: dict[str, str] = {
        f.relative_to(root).as_posix(): hash_file_normalized(f) for f in current_files_list
    }

    added = sorted(set(current_hashes.keys()) - set(recorded_files.keys()))
    deleted = sorted(set(recorded_files.keys()) - set(current_hashes.keys()))
    modified = sorted(
        rel
        for rel in set(current_hashes.keys()) & set(recorded_files.keys())
        if current_hashes[rel] != recorded_files[rel]
    )

    if added or deleted or modified:
        print(
            f"[STALE] Code map is out of date "
            f"({len(modified)} modified, {len(added)} added, {len(deleted)} deleted):"
        )
        for rel in modified:
            print(f"  [MODIFIED] {rel}")
        for rel in added:
            print(f"  [ADDED]    {rel}")
        for rel in deleted:
            print(f"  [DELETED]  {rel}")
        return 1

    print(f"[PASS] Code map is fresh ({len(current_hashes)} files verified against .ai-map/meta.json).")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Đường dẫn thư mục gốc của theme (mặc định: find_theme_root())",
    )

    parser = argparse.ArgumentParser(description=__doc__, parents=[parent_parser])
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("build", parents=[parent_parser], help="Quét mã nguồn và ghi CODEMAP.md + .ai-map/")
    subparsers.add_parser("check", parents=[parent_parser], help="Chỉ đọc: kiểm tra độ tươi của .ai-map/meta.json")

    p_query = subparsers.add_parser("query", parents=[parent_parser], help="Tra cứu node/cạnh (P1)")
    p_query.add_argument("args", nargs="*", help="Tham số truy vấn")

    p_impact = subparsers.add_parser("impact", parents=[parent_parser], help="Phân tích bán kính ảnh hưởng (P1)")
    p_impact.add_argument("args", nargs="*", help="File hoặc field cần kiểm tra")

    ns = parser.parse_args()
    theme_root = Path(ns.root).resolve() if ns.root else find_theme_root()

    if ns.command == "build":
        return cmd_build(theme_root)
    if ns.command == "check":
        return cmd_check(theme_root)
    if ns.command in ("query", "impact"):
        print("chưa hỗ trợ ở P0")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
