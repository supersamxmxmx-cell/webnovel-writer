import json
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PLUGIN_ROOT.parent
SKILLS_ROOT = PLUGIN_ROOT / "skills"
COMMANDS = {
    "webnovel-init",
    "webnovel-plan",
    "webnovel-write",
    "webnovel-review",
    "webnovel-query",
    "webnovel-learn",
    "webnovel-doctor",
    "webnovel-dashboard",
}


def test_codex_manifest_points_to_native_skill_root():
    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))

    assert manifest["name"] == "webnovel-writer"
    assert manifest["skills"] == "./skills/"
    assert (PLUGIN_ROOT / manifest["skills"][2:]).is_dir()


def test_repository_marketplace_exposes_plugin_and_agents_guidance():
    marketplace_path = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    entry = next(item for item in marketplace["plugins"] if item["name"] == "webnovel-writer")
    source = entry["source"]

    assert marketplace["name"] == "webnovel-writer-marketplace"
    assert source["source"] == "local"
    assert source["path"].startswith("./")
    assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert (REPO_ROOT / source["path"][2:] / ".codex-plugin" / "plugin.json").is_file()
    assert (REPO_ROOT / "AGENTS.md").is_file()


def test_every_codex_skill_is_self_contained_and_keeps_full_flow():
    for command in COMMANDS:
        skill_path = SKILLS_ROOT / command / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")

        assert content.startswith(f"---\nname: {command}\n")
        assert 'export PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-<plugin root>}"' in content
        assert 'export PYTHON_BIN="${PYTHON_BIN:-python3}"' in content
        assert len(content.splitlines()) >= 40
        assert (SKILLS_ROOT / command / "agents" / "openai.yaml").is_file()


def test_codex_skills_use_portable_frontmatter_and_runtime():
    for skill_path in SKILLS_ROOT.glob("*/SKILL.md"):
        content = skill_path.read_text(encoding="utf-8")
        assert "allowed-tools:" not in content
        assert "argument-hint:" not in content
        assert "Use the Agent tool" not in content
        assert "${SCRIPTS_DIR}" in content
