"""Validate the distributable CanhCam agent kit without third-party packages."""

from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "KIT_VERSION").read_text(encoding="utf-8").strip()
ROLES = {
    "wp-architect": {"read_file", "run_command"},
    "acf-builder": {"read_file", "write_file", "edit_file", "run_command"},
    "wp-coder": {"read_file", "write_file", "edit_file", "run_command"},
    "wp-reviewer": {"read_file", "run_command"},
}
ROLE_SHARDS = {
    "wp-architect": "architecture.md",
    "acf-builder": "acf-schema.md",
    "wp-coder": "php-contracts.md",
    "wp-reviewer": "codemap.py",
}
REQUIRED = (
    "AGENTS.md",
    "CANHCAM_THEME_BLUEPRINT.md",
    "HANDOVER_TRACKING_TEMPLATE.md",
    "PAGE_HANDOFF_TEMPLATE.md",
    "PROJECT_OVERRIDES_TEMPLATE.md",
    "PROJECT_VARIANTS_TEMPLATE.md",
    "PROMPT_PLAYBOOK.md",
    "README.md",
)
REQUIRED_SCRIPTS = (
    "scripts/validate_kit.py",
    "scripts/verify_theme.py",
    "scripts/install_kit.py",
    "scripts/kitlib.py",
    "scripts/codemap.py",
    "install.ps1",
    "install.sh",
)
FORBIDDEN_IN_KIT = (
    ".agents",
    ".codex",
    "BAO_CAO_CAN_SUA.md",
)


def frontmatter(path: Path) -> tuple[dict[str, str], set[str]]:
    source = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", source, re.S)
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter")
    header = match.group(1)
    fields = dict(re.findall(r"^([A-Za-z]+):\s*(.+)$", header, re.M))
    tools = set(re.findall(r"^\s+- ([a-z_]+)$", header, re.M))
    return fields, tools


def main() -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", VERSION):
        raise ValueError("KIT_VERSION must be semver")

    for forbidden in FORBIDDEN_IN_KIT:
        if (ROOT / forbidden).exists():
            raise ValueError(f"{ROOT / forbidden}: forbidden duplicate/draft artifact in kit distribution")

    for rel_script in REQUIRED_SCRIPTS:
        if not (ROOT / rel_script).is_file():
            raise ValueError(f"Missing {rel_script}")

    for name in REQUIRED:
        path = ROOT / name
        if not path.is_file():
            raise ValueError(f"Missing {path}")
        text = path.read_text(encoding="utf-8")
        if VERSION not in text:
            raise ValueError(f"{name}: version mismatch (expected {VERSION})")
        if "file:///" in text:
            raise ValueError(f"{name}: broken file:/// link")

    for name, expected_tools in ROLES.items():
        path = ROOT / "custom-agents" / f"{name}.md"
        fields, tools = frontmatter(path)
        if fields.get("name") != name or fields.get("subagent") != "true" or fields.get("mainAgent") != "false":
            raise ValueError(f"{path}: invalid role flags")
        if fields.get("model") not in {"inherit", "pro"}:
            raise ValueError(f"{path}: invalid model")
        if fields.get("commandExecutionPolicy") != "sandbox":
            raise ValueError(f"{path}: invalid command policy")
        if tools != expected_tools:
            raise ValueError(f"{path}: unexpected tools {tools ^ expected_tools}")
        body = path.read_text(encoding="utf-8")
        if ROLE_SHARDS[name] not in body:
            raise ValueError(f"{path}: missing codemap shard reference '{ROLE_SHARDS[name]}'")

    for name in ("wp_architect", "acf_builder", "wp_coder", "wp_reviewer"):
        path = ROOT / "codex-agents" / f"{name}.toml"
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        if data.get("name") != name or not data.get("description") or not data.get("developer_instructions"):
            raise ValueError(f"{path}: invalid Codex agent")
        if "sandbox_mode" in data:
            raise ValueError(f"{path}: sandbox_mode cannot override parent")

    print(
        f"CanhCam kit {VERSION}: 4 Antigravity + 4 Codex agents + "
        f"install_kit.py + verify_theme.py + codemap.py validated"
    )


if __name__ == "__main__":
    main()
