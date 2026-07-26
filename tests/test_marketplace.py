import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
PLUGIN = REPO / ".claude-plugin" / "plugin.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def skill_frontmatter(skill_dir: Path) -> dict:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{skill_dir.name}/SKILL.md missing frontmatter"
    fm = text.split("---\n", 2)[1]
    return yaml.safe_load(fm)


def declared_skill_dirs() -> list[Path]:
    return [REPO / rel for rel in load_json(PLUGIN)["skills"]]


def test_marketplace_manifest_shape():
    data = load_json(MARKETPLACE)
    assert data["name"] == "grimore"
    assert data["owner"]["name"]
    [entry] = data["plugins"]
    assert entry["name"] == "grimore"
    assert entry["source"] == "./"


def test_plugin_manifest_matches_marketplace_entry():
    plugin = load_json(PLUGIN)
    [entry] = load_json(MARKETPLACE)["plugins"]
    assert plugin["name"] == entry["name"]
    assert plugin["skills"], "plugin must declare at least one skill path"
    for rel in plugin["skills"]:
        assert rel.startswith("./"), f"skill path {rel!r} must be plugin-root-relative"


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
