"""Multi-page theme verifier for CanhCam WordPress themes (ACF ZTR & DOM Section Parity)."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
from collections import defaultdict
import json
from pathlib import Path

from kitlib import (
    SECTION_RE,
    TEMPLATE_PART_RE,
    find_theme_root,
    iter_acf_fields,
    resolve_php_files,
)


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

    from kitlib import section_classes
    html_sections = section_classes(html_path.read_text(encoding="utf-8", errors="ignore"))
    print('[NOT RUN] [ZTR-18] Runtime DOM structure / JS hooks / browser parity; static markers only.')
    if not html_sections:
        print('[NOT RUN] [ZTR-18] No literal source section markers to compare.')
        return 1
    php_sections: set[str] = set()
    for php_file in php_files:
        content = php_file.read_text(encoding="utf-8", errors="ignore")
        php_sections.update(section_classes(content, php=True))

    missing: list[str] = []
    for sec in html_sections:
        if sec not in php_sections:
            missing.append(sec)

    rel_html = html_path.resolve().relative_to(theme_root.resolve()).as_posix() if html_path.is_absolute() else html_arg
    if missing:
        print(
            f"[FAIL] [ZTR-18] Static section markers failed for {rel_html}: "
            f"missing section class(es) {missing} in {[p.name for p in php_files]}"
        )
        return 1

    print(
        f"[PASS] [ZTR-18 static markers only] {len(html_sections)}/{len(html_sections)} section(s) from "
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
