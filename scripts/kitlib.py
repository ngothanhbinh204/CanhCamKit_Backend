"""Shared zero-dependency parser and utilities for CanhCam Agents Kit scripts."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import glob
import hashlib
from pathlib import Path
import re
from typing import Any


DEFAULT_SCAN_DIRS: tuple[str, ...] = (
    "UI",
    "acf-json",
    "inc",
    "modules",
    "template-parts",
    "templates",
)

EXCLUDED_DIRS: tuple[str, ...] = (
    "canhcam-agents-kit",
    "node_modules",
    "vendor",
    ".git",
    ".ai-map",
    ".agents",
    ".codex",
    ".cursor",
)

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


# --- Extended helpers for codemap.py (P0 Code Graph) ---


def is_excluded_path(rel_parts: tuple[str, ...], excluded: tuple[str, ...] = EXCLUDED_DIRS) -> bool:
    return any(part in excluded for part in rel_parts)


def collect_scannable_files(
    theme_root: Path,
    scan_dirs: tuple[str, ...] = DEFAULT_SCAN_DIRS,
    excluded_dirs: tuple[str, ...] = EXCLUDED_DIRS,
) -> list[Path]:
    """Return deterministic list of scannable files in theme_root."""
    root = theme_root.resolve()
    found: set[Path] = set()

    # 1. Root *.php files
    for php_file in root.glob("*.php"):
        if php_file.is_file():
            found.add(php_file.resolve())

    # 2. Configured directories
    for dir_name in scan_dirs:
        target_dir = root / dir_name
        if not target_dir.is_dir():
            continue
        if dir_name == "UI":
            patterns = ("*.html",)
        elif dir_name == "acf-json":
            patterns = ("*.json",)
        else:
            patterns = ("**/*.php",)

        for pat in patterns:
            for fpath in target_dir.glob(pat):
                if not fpath.is_file():
                    continue
                rel = fpath.resolve().relative_to(root)
                if not is_excluded_path(rel.parts, excluded_dirs):
                    found.add(fpath.resolve())

    return sorted(found, key=lambda p: p.relative_to(root).as_posix())


def hash_file_normalized(path: Path) -> str:
    """Compute SHA-256 hex digest with CRLF normalized to LF."""
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def classify_acf_json_key(key: str) -> str:
    """Classify an ACF JSON top-level key by its prefix."""
    if key.startswith("group_"):
        return "group"
    if key.startswith("post_type_"):
        return "post_type"
    if key.startswith("taxonomy_"):
        return "taxonomy"
    if key.startswith("ui_options_page_"):
        return "options_page"
    return "unknown"


def classify_component_tier(rel_path: str) -> int | None:
    """Return Blueprint 4-tier number (1..4) for a PHP file path, or None if it is a top-level template/inc file."""
    if rel_path.startswith("modules/common/") or rel_path.startswith("modules/"):
        return 1
    if rel_path.startswith("template-parts/shared/"):
        return 2
    if rel_path.startswith("template-parts/cards/"):
        return 3
    if rel_path.startswith("template-parts/"):
        return 4
    return None

