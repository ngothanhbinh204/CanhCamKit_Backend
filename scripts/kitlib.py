"""Shared zero-dependency parser and utilities for CanhCam Agents Kit scripts."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import glob
import hashlib
from html.parser import HTMLParser
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


def php_views(source: str) -> tuple[str, str, str]:
    """Offset-preserving PHP (no comments), code (no strings), and literal HTML.

    Heredoc/nowdoc are opaque. This is a lexer, not a PHP interpreter.
    """
    blank = lambda s: ''.join('\n' if c == '\n' else ' ' for c in s)
    clean, code, markup = list(blank(source)), list(blank(source)), list(source)
    i, in_php = 0, False
    while i < len(source):
        if not in_php:
            opening = re.match(r'<\?(?:php\b|=)', source[i:], re.I)
            if not opening:
                i += 1
                continue
            end = i + opening.end()
            markup[i:end] = blank(source[i:end])
            # Mark interpolated attributes; whitespace must not look like a literal class.
            markup[i] = '\x00'
            i, in_php = end, True
            continue
        if source.startswith('?>', i):
            markup[i:i+2] = '  '
            i, in_php = i + 2, False
            continue
        start = i
        if source.startswith(('//', '#'), i) and not source.startswith('#[', i):
            end = source.find('\n', i)
            close = source.find('?>', i)
            i = min(x for x in (end, close, len(source)) if x >= 0)
        elif source.startswith('/*', i):
            end = source.find('*/', i + 2)
            i = len(source) if end < 0 else end + 2
        elif source.startswith('<<<', i):
            head = re.match(r"<<<[ \t]*['\"]?([A-Za-z_]\w*)['\"]?[^\n]*\n", source[i:])
            tail = re.search(r'^\s*' + re.escape(head[1]) + r'\b', source[i+head.end():], re.M) if head else None
            i = i + head.end() + tail.end() if tail else len(source)
        elif source[i] in "'\"`":
            quote = source[i]
            i += 1
            while i < len(source):
                if source[i] == '\\':
                    i += 2
                elif source[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
            i = min(i, len(source))
            clean[start:i] = source[start:i]
        else:
            clean[i] = code[i] = source[i]
            i += 1
        markup[start:i] = blank(source[start:i])
    return ''.join(clean), ''.join(code), ''.join(markup)


def literal_string(expr: str) -> str | None:
    expr = expr.strip()
    if not re.fullmatch(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", expr, re.S):
        return None
    if expr[0] == '"' and ('$' in expr or '\\' in expr):
        return None
    return expr[1:-1].replace("\\'", "'").replace('\\\\', '\\')


def closing_delimiter(code: str, start: int) -> int | None:
    stack = []
    for i in range(start, len(code)):
        c = code[i]
        if c in '([{':
            stack.append(c)
        elif c in ')]}':
            if not stack or stack.pop() != {')': '(', ']': '[', '}': '{'}[c]:
                return None
            if not stack:
                return i
    return None


def php_calls(source: str) -> list[dict[str, Any]]:
    clean, code, _ = php_views(source)
    calls = []
    for match in re.finditer(r'\b([A-Za-z_]\w*)\s*\(', code):
        prefix = code[:match.start()].rstrip()
        if prefix.endswith(('->', '::', '$', '\\')) or re.search(r'\bfunction\s*&?\s*$', prefix):
            continue
        opening = code.index('(', match.start())
        end = closing_delimiter(code, opening)
        if end is None:
            continue
        args, start, depth = [], opening + 1, 0
        for i in range(start, end):
            if code[i] in '([{':
                depth += 1
            elif code[i] in ')]}':
                depth -= 1
            elif code[i] == ',' and depth == 0:
                args.append(clean[start:i].strip())
                start = i + 1
        args.append(clean[start:end].strip())
        calls.append({'name': match[1], 'args': args, 'start': match.start(), 'end': end + 1,
                      'line': source.count('\n', 0, match.start()) + 1})
    return calls


def template_references(source: str, root: Path) -> list[dict[str, Any]]:
    refs = []
    for call in php_calls(source):
        name, args = call['name'], call['args']
        if name not in ('get_template_part', 'get_header', 'get_footer', 'get_sidebar'):
            continue
        slug = literal_string(args[0]) if name == 'get_template_part' else name[4:]
        variant_arg = (args[1] if len(args) > 1 else '') if name == 'get_template_part' else args[0]
        variant = '' if variant_arg in ('', 'null', 'false') else literal_string(variant_arg)
        confidence = 'static'
        if slug is None or variant is None:
            target, confidence = f"dynamic:{name}@{call['start']}", 'dynamic'
        else:
            specific = f'{slug}-{variant}.php' if variant else f'{slug}.php'
            target = specific if (root / specific).is_file() else f'{slug}.php'
            if not (root / target).is_file():
                confidence = 'unresolved'
        refs.append({**call, 'target': target, 'confidence': confidence})
    return refs


def section_classes(source: str, php: bool = False) -> list[str]:
    """First class of real literal section tags only; no runtime parity claim."""
    class Sections(HTMLParser):
        def __init__(self):
            super().__init__()
            self.sections = []
            self.opaque = 0

        def handle_starttag(self, tag, attrs):
            if tag in ('script', 'style'):
                self.opaque += 1
            if tag == 'section' and not self.opaque:
                value = dict(attrs).get('class') or ''
                if value.split() and '\x00' not in value:
                    self.sections.append(value.split()[0])

        def handle_endtag(self, tag):
            if tag in ('script', 'style'):
                self.opaque = max(0, self.opaque - 1)
    parser = Sections()
    parser.feed(php_views(source)[2] if php else source)
    return parser.sections


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
        for ref in template_references(text, theme_root):
            if ref['confidence'] != 'static':
                continue
            candidate = (theme_root / ref['target']).resolve()
            if not candidate.is_relative_to(theme_root.resolve()):
                continue
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

