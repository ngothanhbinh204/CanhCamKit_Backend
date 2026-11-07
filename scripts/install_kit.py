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


def bump_kit_version_in_file(path: Path, new_version: str, dry_run: bool) -> bool:
    content = path.read_text(encoding="utf-8")
    updated = re.sub(
        r"(Kit version:\s*`?)(\d+\.\d+\.\d+)(`?)",
        rf"\g<1>{new_version}\g<3>",
        content,
    )
    if updated != content:
        if not dry_run:
            path.write_text(updated, encoding="utf-8")
        return True
    return False


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


def ensure_gitignore(theme_root: Path, kit_folder_name: str, dry_run: bool, actions: list[str]) -> None:
    gitignore = theme_root / ".gitignore"
    entry = f"{kit_folder_name}/"
    if gitignore.is_file():
        lines = [line.strip() for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()]
        if entry in lines or kit_folder_name in lines or f"/{kit_folder_name}" in lines or f"/{entry}" in lines:
            actions.append(f"  [OK]          .gitignore (đã có '{entry}')")
            return
        actions.append(f"  [UPDATE]      .gitignore (thêm '{entry}')")
        if not dry_run:
            with gitignore.open("a", encoding="utf-8") as f:
                if lines and lines[-1] != "":
                    f.write("\n")
                f.write(f"# CanhCam Agents Kit source repo\n{entry}\n")
    else:
        actions.append(f"  [CREATE]      .gitignore (thêm '{entry}')")
        if not dry_run:
            gitignore.write_text(f"# CanhCam Agents Kit source repo\n{entry}\n", encoding="utf-8")


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
        help="Cập nhật bộ rule/agent mới nhất và nâng số Kit version trong các file state/handoff hiện có",
    )
    parser.add_argument(
        "--force-reset",
        action="store_true",
        help="Ghi đè lại cả các file state (PROJECT_OVERRIDES.md, HANDOVER_TRACKING.md, PROJECT_VARIANTS.md)",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Không tự động thêm canhcam-agents-kit/ vào .gitignore của theme",
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
            if args.upgrade:
                changed = bump_kit_version_in_file(dst_path, VERSION, args.dry_run)
                if changed:
                    actions.append(f"  [UPGRADE-VER] {dst_path.as_posix()} (-> v{VERSION})")
                else:
                    actions.append(f"  [KEEP]        {dst_path.as_posix()} (bảo toàn dữ liệu dự án)")
            else:
                actions.append(f"  [SKIP]        {dst_path.as_posix()} (đã tồn tại — giữ nguyên dữ liệu dự án)")
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
        if args.upgrade:
            for h_file in sorted(handoffs_dir.glob("*.md")):
                if bump_kit_version_in_file(h_file, VERSION, args.dry_run):
                    actions.append(f"  [UPGRADE-VER] {h_file.as_posix()} (-> v{VERSION})")
        actions.append(f"  [OK]          {handoffs_dir.as_posix()}/")

    # Step 4: Git Hygiene (.gitignore)
    if not args.no_gitignore and KIT_ROOT.parent == theme_root:
        ensure_gitignore(theme_root, KIT_ROOT.name, args.dry_run, actions)

    for line in actions:
        print(line)

    # Step 5: Auto-Inventory if UI/ exists
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
    print("  2. Kiểm tra `PROJECT_OVERRIDES.md` và chạy Prompt 0.1 trong `PROMPT_PLAYBOOK.md`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
