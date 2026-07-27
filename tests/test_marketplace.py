import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
CLAUDE_PLUGIN = REPO / ".claude-plugin" / "plugin.json"
CODEX_PLUGIN = REPO / ".codex-plugin" / "plugin.json"
NATIVE_PLUGINS = (CLAUDE_PLUGIN, CODEX_PLUGIN)
SHARED_FIELDS = ("name", "version", "description", "author", "skills")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def skill_frontmatter(skill_dir: Path) -> dict:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{skill_dir.name}/SKILL.md missing frontmatter"
    fm = text.split("---\n", 2)[1]
    return yaml.safe_load(fm)


def declared_skill_dirs() -> list[Path]:
    return [REPO / rel for rel in load_json(CLAUDE_PLUGIN)["skills"]]


def test_marketplace_manifest_shape():
    data = load_json(MARKETPLACE)
    assert data["name"] == "grimore"
    assert data["owner"]["name"]
    [entry] = data["plugins"]
    assert entry["name"] == "grimore"
    assert entry["source"] == "./"


def test_native_plugin_manifests_match():
    claude = load_json(CLAUDE_PLUGIN)
    codex = load_json(CODEX_PLUGIN)
    assert isinstance(claude, dict)
    assert isinstance(codex, dict)
    for field in SHARED_FIELDS:
        assert field in claude, f"{CLAUDE_PLUGIN} missing shared field {field!r}"
        assert field in codex, f"{CODEX_PLUGIN} missing shared field {field!r}"
        assert codex[field] == claude[field], (
            f"shared field {field!r} differs between native manifests"
        )


def test_plugin_manifests_match_marketplace_entry():
    plugins = [load_json(path) for path in NATIVE_PLUGINS]
    [entry] = load_json(MARKETPLACE)["plugins"]
    assert {plugin["name"] for plugin in plugins} == {entry["name"]}
    for path, plugin in zip(NATIVE_PLUGINS, plugins, strict=True):
        assert plugin["skills"], f"{path} must declare at least one skill path"
        for rel in plugin["skills"]:
            assert rel.startswith("./"), (
                f"skill path {rel!r} in {path} must be plugin-root-relative"
            )


def test_declared_skills_exist_with_valid_frontmatter():
    for skill_dir in declared_skill_dirs():
        assert skill_dir.is_dir(), f"declared skill dir missing: {skill_dir.name}"
        fm = skill_frontmatter(skill_dir)
        assert fm["name"] == skill_dir.name
        assert fm["description"].strip()


def test_every_repo_skill_is_declared():
    on_disk = {
        child.name
        for child in REPO.iterdir()
        if child.is_dir() and (child / "SKILL.md").is_file()
    }
    declared = {path.name for path in declared_skill_dirs()}
    assert on_disk == declared, (
        f"skill dirs on disk {sorted(on_disk)} != declared in plugin.json "
        f"{sorted(declared)}; update .claude-plugin/plugin.json"
    )
