"""One-command installer and upgrader for CanhCam Agents Kit into a WordPress theme root."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import shutil
import subprocess
import sys


KIT_ROOT = Path(__file__).resolve().parents[1]
VERSION = (KIT_ROOT / "KIT_VERSION").read_text(encoding="utf-8").strip()

CORE_FILES = (
    "KIT_VERSION",
    "AGENTS.md",
    "CANHCAM_THEME_BLUEPRINT.md",
    "PROMPT_PLAYBOOK.md",
    "PAGE_HANDOFF_TEMPLATE.md",
)

STATE_TEMPLATES = (
    ("PROJECT_OVERRIDES_TEMPLATE.md", "PROJECT_OVERRIDES.md"),
    ("PROJECT_VARIANTS_TEMPLATE.md", "PROJECT_VARIANTS.md"),
    ("HANDOVER_TRACKING_TEMPLATE.md", "HANDOVER_TRACKING.md"),
)


def detect_theme_metadata(theme_root: Path) -> dict[str, str]:
    meta = {
        "theme_slug": theme_root.name,
        "theme_name": theme_root.name,
        "text_domain": "canhcamtheme",
        "options_menu_slug": "[chưa chốt]",
    }
    style_css = theme_root / "style.css"
    if style_css.is_file():
        css_text = style_css.read_text(encoding="utf-8", errors="ignore")
        m_name = re.search(r"^\s*Theme Name:\s*(.+)$", css_text, re.M | re.I)
        if m_name:
            meta["theme_name"] = m_name.group(1).strip()
        m_td = re.search(r"^\s*Text Domain:\s*([A-Za-z0-9_-]+)", css_text, re.M | re.I)
        if m_td:
            meta["text_domain"] = m_td.group(1).strip()

    php_candidates = list((theme_root / "inc").glob("*.php")) if (theme_root / "inc").is_dir() else []
    if (theme_root / "functions.php").is_file():
        php_candidates.append(theme_root / "functions.php")

    for php_file in php_candidates:
        content = php_file.read_text(encoding="utf-8", errors="ignore")
        if "acf_add_options_page" in content:
            m_slug = re.search(r"['\"]menu_slug['\"]\s*=>\s*['\"]([^'\"]+)['\"]", content)
            if m_slug:
                rel = php_file.relative_to(theme_root).as_posix()
                meta["options_menu_slug"] = f"`{m_slug.group(1)}` (tự động phát hiện từ `{rel}`)"
                break

    return meta


def render_state_template(src_name: str, raw_text: str, meta: dict[str, str]) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    text = raw_text
    if src_name == "HANDOVER_TRACKING_TEMPLATE.md":
        text = text.replace("[Tên dự án]", meta["theme_name"])
        text = text.replace("`canhcamtheme`", f"`{meta['theme_slug']}`")
        text = text.replace("[YYYY-MM-DD HH:mm]", now_str)
    elif src_name == "PROJECT_OVERRIDES_TEMPLATE.md":
        if meta["text_domain"] != "canhcamtheme":
            text = text.replace("`canhcamtheme`", f"`{meta['text_domain']}`")
        if meta["options_menu_slug"] != "[chưa chốt]":
            text = text.replace("| `options_menu_slug` | `[chưa chốt]` | [file đăng ký hoặc người duyệt] |",
                                f"| `options_menu_slug` | {meta['options_menu_slug']} | Code hiện có |")
    return text


def copy_file(src: Path, dst: Path, dry_run: bool, actions: list[str]) -> None:
    rel_dst = dst.as_posix()
    exists = dst.is_file()
    if exists and dst.read_bytes() == src.read_bytes():
        actions.append(f"  [OK]          {rel_dst} (đã đồng bộ)")
        return
    tag = "[UPDATE]" if exists else "[CREATE]"
    actions.append(f"  {tag:<13} {rel_dst}")
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def ensure_gitignore(theme_root: Path, entries: list[str], dry_run: bool, actions: list[str]) -> None:
    gitignore = theme_root / ".gitignore"
    file_existed = gitignore.is_file()
    existing_lines: list[str] = []
    if file_existed:
        existing_lines = [
            line.strip() for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
        ]

    missing: list[str] = []
    for entry in entries:
        bare = entry.rstrip("/")
        variants = {entry, bare, f"/{entry}", f"/{bare}"}
        if any(v in existing_lines for v in variants):
            actions.append(f"  [OK]          .gitignore (đã có '{entry}')")
        else:
            missing.append(entry)
            tag = "[UPDATE]" if (file_existed or len(missing) > 1) else "[CREATE]"
            actions.append(f"  {tag:<13} .gitignore (thêm '{entry}')")

    if missing and not dry_run:
        header = "# CanhCam Agents Kit & AI Code Map"
        block_lines: list[str] = []
        if header not in existing_lines:
            block_lines.append(header)
        block_lines.extend(missing)
        block_text = "\n".join(block_lines) + "\n"
        if file_existed:
            with gitignore.open("a", encoding="utf-8") as f:
                if existing_lines and existing_lines[-1] != "":
                    f.write("\n")
                f.write(block_text)
        else:
            gitignore.write_text(block_text, encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        type=str,
        default=str(KIT_ROOT.parent),
        help="Đường dẫn thư mục gốc của theme (mặc định: thư mục cha của canhcam-agents-kit)",
    )
    parser.add_argument(
        "--tool",
        choices=("all", "antigravity", "codex"),
        default="all",
        help="Công cụ agent cần cài đặt cấu hình native (mặc định: all)",
    )
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Cập nhật rule/agent và CODEMAP; giữ nguyên state/handoff, không tự migrate schema",
    )
    parser.add_argument(
        "--force-reset",
        action="store_true",
        help="Ghi đè lại cả các file state (PROJECT_OVERRIDES.md, HANDOVER_TRACKING.md, PROJECT_VARIANTS.md)",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Không tự động thêm canhcam-agents-kit/, .ai-map/, CODEMAP.md vào .gitignore của theme",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ hiển thị những thay đổi dự kiến mà không ghi file xuống ổ cứng",
    )
    args = parser.parse_args()

    theme_root = Path(args.target).resolve()
    if theme_root == KIT_ROOT:
        print("[FAIL] Thư mục đích (--target) không được trùng với chính thư mục canhcam-agents-kit.")
        return 1

    # Step 1: Preflight validate_kit.py
    validate_script = KIT_ROOT / "scripts" / "validate_kit.py"
    res = subprocess.run([sys.executable, str(validate_script)], capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        print("[FAIL] Preflight validate_kit.py thất bại:")
        print(res.stdout + res.stderr)
        return 1

    print(f"=== CanhCam Agents Kit Installer v{VERSION} ===")
    print(f"Theme root : {theme_root}")
    print(f"Chế độ     : {'DRY-RUN (Xem trước)' if args.dry_run else ('UPGRADE' if args.upgrade else 'INSTALL')}")
    print(f"Agent tool : {args.tool}")
    print("-" * 65)

    actions: list[str] = []

    # Step 2: Copy Group A (Core Runtime & Rules)
    for filename in CORE_FILES:
        copy_file(KIT_ROOT / filename, theme_root / filename, args.dry_run, actions)

    if args.tool in ("all", "antigravity"):
        for md_file in sorted((KIT_ROOT / "custom-agents").glob("*.md")):
            copy_file(md_file, theme_root / ".agents" / "agents" / md_file.name, args.dry_run, actions)

    if args.tool in ("all", "codex"):
        for toml_file in sorted((KIT_ROOT / "codex-agents").glob("*.toml")):
            copy_file(toml_file, theme_root / ".codex" / "agents" / toml_file.name, args.dry_run, actions)

    # Step 3: Scaffold Group B (Project State Files)
    meta = detect_theme_metadata(theme_root)
    for src_tpl, dst_name in STATE_TEMPLATES:
        dst_path = theme_root / dst_name
        if dst_path.is_file() and not args.force_reset:
            actions.append(f"  [KEEP]        {dst_path.as_posix()} (giữ nguyên dữ liệu và version; migration cần review riêng)")
        else:
            raw_tpl = (KIT_ROOT / src_tpl).read_text(encoding="utf-8")
            rendered = render_state_template(src_tpl, raw_tpl, meta)
            tag = "[RESET]" if dst_path.is_file() else "[CREATE]"
            actions.append(f"  {tag:<13} {dst_path.as_posix()}")
            if not args.dry_run:
                dst_path.write_text(rendered, encoding="utf-8")

    # Ensure handoffs/ directory
    handoffs_dir = theme_root / "handoffs"
    if not handoffs_dir.is_dir():
        actions.append(f"  [CREATE-DIR]  {handoffs_dir.as_posix()}/")
        if not args.dry_run:
            handoffs_dir.mkdir(parents=True, exist_ok=True)
    else:
        actions.append(f"  [KEEP]        {handoffs_dir.as_posix()}/ (không đổi version handoff)")

    # Step 4: Git Hygiene (.gitignore)
    if not args.no_gitignore and KIT_ROOT.parent == theme_root:
        gitignore_entries = [f"{KIT_ROOT.name}/", ".ai-map/", "CODEMAP.md"]
        ensure_gitignore(theme_root, gitignore_entries, args.dry_run, actions)

    # Step 5: Build Group C (Code Graph: CODEMAP.md + .ai-map/)
    if args.dry_run:
        actions.append("  [WOULD BUILD] CODEMAP")
    else:
        codemap_script = KIT_ROOT / "scripts" / "codemap.py"
        cm_res = subprocess.run(
            [sys.executable, str(codemap_script), "build", "--root", str(theme_root)],
            cwd=str(theme_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if cm_res.returncode == 0:
            actions.append(f"  [BUILD-MAP]   {(theme_root / 'CODEMAP.md').as_posix()} & .ai-map/")
        else:
            actions.append(f"  [FAIL]        codemap.py build: {(cm_res.stdout + cm_res.stderr).strip()}")
            for line in actions:
                print(line)
            print('CÀI ĐẶT CHƯA HOÀN TẤT: core files đã được copy; sửa lỗi và chạy lại. State/handoff được giữ nguyên nếu không dùng --force-reset.')
            return 1

    for line in actions:
        print(line)

    # Step 6: Auto-Inventory if UI/ exists
    ui_dir = theme_root / "UI"
    if ui_dir.is_dir() and list(ui_dir.glob("*.html")):
        print("-" * 65)
        verify_script = KIT_ROOT / "scripts" / "verify_theme.py"
        inv_res = subprocess.run(
            [sys.executable, str(verify_script), "--inventory"],
            cwd=str(theme_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print(inv_res.stdout.strip())

    print("-" * 65)
    print("HOÀN TẤT! Bước tiếp theo:")
    print("  1. Mở phiên làm việc mới của Antigravity / Codex tại thư mục gốc của theme.")
    print("  2. Kiểm tra `PROJECT_OVERRIDES.md`, `CODEMAP.md` và chạy Prompt 0.1 trong `PROMPT_PLAYBOOK.md`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
