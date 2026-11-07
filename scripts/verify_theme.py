"""Multi-page theme verifier for CanhCam WordPress themes (ACF ZTR & DOM Section Parity)."""

from __future__ import annotations

import argparse
from collections import defaultdict
import glob
import json
from pathlib import Path
import re
import sys
from typing import Any


SECTION_RE = re.compile(r"<section\b[^>]*\bclass=[\"']\s*([^\s\"']+)", re.I)
TEMPLATE_PART_RE = re.compile(r"get_template_part\(\s*['\"]([^'\"]+)['\"]")


def find_theme_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "style.css").is_file() or (cwd / "acf-json").is_dir():
        return cwd
    script_root = Path(__file__).resolve().parents[2]
    return script_root


def iter_acf_fields(fields: list[dict[str, Any]], parent_path: str = "") -> list[tuple[str, dict[str, Any]]]:
    collected: list[tuple[str, dict[str, Any]]] = []
    for field in fields or []:
        if not isinstance(field, dict):
            continue
        label = field.get("name") or field.get("label") or field.get("key") or "unknown"
        cur_path = f"{parent_path}.{label}" if parent_path else str(label)
        collected.append((cur_path, field))
        if isinstance(field.get("sub_fields"), list):
            collected.extend(iter_acf_fields(field["sub_fields"], cur_path))
        if isinstance(field.get("layouts"), list):
            for layout in field["layouts"]:
                if isinstance(layout, dict) and isinstance(layout.get("sub_fields"), list):
                    l_name = layout.get("name") or layout.get("key") or "layout"
                    collected.extend(iter_acf_fields(layout["sub_fields"], f"{cur_path}[{l_name}]"))
    return collected


def check_acf(theme_root: Path) -> int:
    acf_dir = theme_root / "acf-json"
    if not acf_dir.is_dir():
        print(f"[FAIL] Missing acf-json directory at {acf_dir}")
        return 1

    json_files = sorted(acf_dir.glob("*.json"))
    if not json_files:
        print(f"[WARN] No JSON files found in {acf_dir}")
        return 0

    errors: list[str] = []
    seen_group_keys: dict[str, str] = {}
    seen_field_keys: dict[str, tuple[str, str]] = {}
    total_fields = 0

    for path in json_files:
        rel = path.relative_to(theme_root).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"[ZTR-ACF-JSON] {rel}: invalid JSON ({exc})")
            continue

        group_key = data.get("key", "")
        if not group_key:
            errors.append(f"[ZTR-17] {rel}: missing group 'key'")
        elif group_key in seen_group_keys:
            errors.append(f"[ZTR-17] {rel}: duplicate group key '{group_key}' (also in {seen_group_keys[group_key]})")
        else:
            seen_group_keys[group_key] = rel

        if data.get("style") == "seamless":
            errors.append(f"[ZTR-12] {rel}: forbidden style 'seamless' (must be 'default')")

        for field_path, field in iter_acf_fields(data.get("fields", [])):
            total_fields += 1
            fkey = field.get("key", "")
            ftype = field.get("type", "")

            if not fkey:
                errors.append(f"[ZTR-17] {rel} ({field_path}): missing field 'key'")
            elif fkey in seen_field_keys:
                prev_file, prev_path = seen_field_keys[fkey]
                errors.append(
                    f"[ZTR-17] {rel} ({field_path}): duplicate field key '{fkey}' "
                    f"(already used in {prev_file} at {prev_path})"
                )
            else:
                seen_field_keys[fkey] = (rel, field_path)

            if ftype == "relationship":
                tax = field.get("taxonomy", "")
                if tax not in ("", [], None):
                    errors.append(
                        f"[ZTR-11] {rel} ({field_path}): relationship 'taxonomy' must be empty, got {tax!r}"
                    )

            if ftype == "image":
                ret = field.get("return_format", "array")
                if ret == "url":
                    errors.append(
                        f"[ZTR-14] {rel} ({field_path}): image 'return_format' cannot be 'url' (must be 'array')"
                    )

    if errors:
        print(f"[FAIL] ACF verification found {len(errors)} violation(s) across {len(json_files)} files:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(
        f"[PASS] ACF verification: {len(json_files)} JSON groups, {total_fields} fields checked "
        f"(0 duplicate keys, ZTR-11/12/14/17 clean)."
    )
    return 0


def run_inventory(theme_root: Path) -> int:
    ui_dir = theme_root / "UI"
    if not ui_dir.is_dir():
        print(f"[FAIL] Missing UI directory at {ui_dir}")
        return 1

    html_files = sorted(ui_dir.glob("*.html"))
    section_map: dict[str, list[str]] = defaultdict(list)

    for html_path in html_files:
        content = html_path.read_text(encoding="utf-8", errors="ignore")
        classes = SECTION_RE.findall(content)
        seen_in_file: list[str] = []
        for cls in classes:
            if cls not in seen_in_file:
                seen_in_file.append(cls)
        for cls in seen_in_file:
            section_map[cls].append(html_path.name)

    print(f"Cross-Page HTML Section Inventory ({len(html_files)} HTML files in UI/):")
    print(f"{'Section First Class':<36} | {'Pages':<5} | {'Suggested Tier':<22} | HTML Files")
    print("-" * 105)
    for cls, files in sorted(section_map.items(), key=lambda item: (-len(item[1]), item[0])):
        tier = "Tier 1/2 (Global/Shared)" if len(files) >= 2 else "Tier 4 (Page-Specific)"
        print(f"{cls:<36} | {len(files):<5} | {tier:<22} | {', '.join(files)}")
    return 0


def resolve_php_files(theme_root: Path, php_patterns: list[str]) -> list[Path]:
    resolved: list[Path] = []
    visited: set[Path] = set()

    for pattern in php_patterns:
        matches = glob.glob(str(theme_root / pattern), recursive=True) or glob.glob(pattern, recursive=True)
        for match in matches:
            p = Path(match).resolve()
            if p.is_file() and p not in visited:
                visited.add(p)
                resolved.append(p)

    queue = list(resolved)
    while queue:
        current = queue.pop(0)
        text = current.read_text(encoding="utf-8", errors="ignore")
        for slug in TEMPLATE_PART_RE.findall(text):
            candidate = (theme_root / f"{slug}.php").resolve()
            if candidate.is_file() and candidate not in visited:
                visited.add(candidate)
                resolved.append(candidate)
                queue.append(candidate)

    return resolved


def check_parity(theme_root: Path, html_arg: str, php_patterns: list[str]) -> int:
    html_path = Path(html_arg)
    if not html_path.is_file():
        html_path = theme_root / html_arg
    if not html_path.is_file():
        print(f"[FAIL] HTML file not found: {html_arg}")
        return 1

    php_files = resolve_php_files(theme_root, php_patterns)
    if not php_files:
        print(f"[FAIL] No PHP files matched: {php_patterns}")
        return 1

    html_sections = SECTION_RE.findall(html_path.read_text(encoding="utf-8", errors="ignore"))
    php_sections: set[str] = set()
    php_combined = ""
    for php_file in php_files:
        content = php_file.read_text(encoding="utf-8", errors="ignore")
        php_combined += "\n" + content
        php_sections.update(SECTION_RE.findall(content))

    missing: list[str] = []
    for sec in html_sections:
        if sec not in php_sections and sec not in php_combined:
            missing.append(sec)

    rel_html = html_path.resolve().relative_to(theme_root.resolve()).as_posix() if html_path.is_absolute() else html_arg
    if missing:
        print(
            f"[FAIL] [ZTR-18] DOM Section Parity failed for {rel_html}: "
            f"missing section class(es) {missing} in {[p.name for p in php_files]}"
        )
        return 1

    print(
        f"[PASS] [ZTR-18] DOM Section Parity: {len(html_sections)}/{len(html_sections)} section(s) from "
        f"{html_path.name} verified across {len(php_files)} PHP file(s) ({', '.join(html_sections)})."
    )
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", action="store_true", help="Scan UI/*.html for Cross-Page section inventory")
    parser.add_argument("--acf", action="store_true", help="Validate acf-json/*.json for duplicate keys and ZTR rules")
    parser.add_argument("--html", type=str, help="Source HTML file for DOM section parity check")
    parser.add_argument("--php", nargs="+", help="Target PHP template(s)/part(s) for DOM section parity check")
    args = parser.parse_args()

    theme_root = find_theme_root()
    ran_any = False
    exit_code = 0

    if args.inventory:
        ran_any = True
        exit_code |= run_inventory(theme_root)

    if args.acf or not (args.inventory or args.html):
        ran_any = True
        exit_code |= check_acf(theme_root)

    if args.html:
        if not args.php:
            print("[FAIL] --html requires at least one --php file/pattern")
            return 1
        ran_any = True
        exit_code |= check_parity(theme_root, args.html, args.php)

    return exit_code if ran_any else 0


if __name__ == "__main__":
    sys.exit(main())
