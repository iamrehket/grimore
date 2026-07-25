import grim
from helpers import write_component


def load(root):
    cfg = grim.load_config(root)
    return cfg, grim.load_store(cfg)


def test_store_hash_ignores_non_current_components(tmp_path):
    write_component(tmp_path, "adr", "kept", status="current")
    _, store = load(tmp_path)
    baseline = grim.store_hash(store)
    write_component(tmp_path, "adr", "draftling", status="draft")
    write_component(tmp_path, "adr", "old", status="superseded")
    _, store = load(tmp_path)
    assert grim.store_hash(store) == baseline


def test_store_hash_changes_with_current_content(tmp_path):
    write_component(tmp_path, "adr", "kept", body="One.")
    _, store = load(tmp_path)
    h1 = grim.store_hash(store)
    write_component(tmp_path, "adr", "kept", body="Two.")
    _, store = load(tmp_path)
    assert grim.store_hash(store) != h1


def test_demote_headings():
    body = "# Title\n\nprose # not a heading\n\n## Sub\n\n###### Deep"
    assert grim.demote_headings(body, 1) == "## Title\n\nprose # not a heading\n\n### Sub\n\n###### Deep"
    assert grim.demote_headings(body, 2).startswith("### Title")


def render(root):
    _, store = load(root)
    return grim.render_store(store)


def test_render_mapping_and_ordering(tmp_path):
    write_component(tmp_path, "usecase", "b-case", date="2026-07-02", body="# B case\n\nProse.")
    write_component(tmp_path, "usecase", "a-case", date="2026-07-01", body="# A case\n\nProse.")
    write_component(tmp_path, "constraint", "limit", body="# Limit\n\nProse.")
    write_component(tmp_path, "adr", "why", body="# Why\n\nProse.")
    write_component(tmp_path, "term", "widget", body="**Widget**: a thing.\n\n_Avoid_: gadget.")
    write_component(tmp_path, "note", "pipeline", extra={"subsystem": "renderer"})
    write_component(tmp_path, "note", "loose")
    out = render(tmp_path)
    assert sorted(out) == ["charter.md", "decisions.md", "general.md", "glossary.md", "renderer.md"]
    charter = out["charter.md"]
    assert charter.splitlines()[0].startswith("<!-- grim:store-hash sha256:")
    assert "# Charter" in charter and "## Use cases" in charter and "## Constraints" in charter
    assert "## Non-goals" not in charter          # zero nongoals: section omitted
    assert charter.index("### A case") < charter.index("### B case")  # date order, demoted +2
    assert "## Why" in out["decisions.md"]        # demoted +1
    assert "**Widget**" in out["glossary.md"]


def test_render_skips_draft_and_superseded(tmp_path):
    # Unique body text per excluded component: rendered output contains bodies,
    # not ids, so asserting on ids would pass vacuously.
    write_component(tmp_path, "adr", "live", status="current", body="LIVE-BODY-MARKER")
    write_component(tmp_path, "adr", "draftling", status="draft", body="DRAFT-BODY-MARKER")
    write_component(tmp_path, "adr", "gone", status="superseded", body="SUPERSEDED-BODY-MARKER")
    decisions = render(tmp_path)["decisions.md"]
    assert "LIVE-BODY-MARKER" in decisions
    assert "DRAFT-BODY-MARKER" not in decisions
    assert "SUPERSEDED-BODY-MARKER" not in decisions


def test_render_empty_store_produces_nothing(tmp_path):
    assert render(tmp_path) == {}


def test_render_is_deterministic(tmp_path):
    write_component(tmp_path, "adr", "why")
    write_component(tmp_path, "note", "n", extra={"subsystem": "renderer"})
    assert render(tmp_path) == render(tmp_path)  # byte-identical for identical stores


def test_write_render_writes_and_prunes(tmp_path):
    write_component(tmp_path, "adr", "why")
    cfg, store = load(tmp_path)
    stale = tmp_path / "docs" / "current" / "stale.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("old\n")
    keepme = tmp_path / "docs" / "current" / "notes.txt"
    keepme.write_text("not markdown; renderer must leave it alone\n")
    written, removed = grim.write_render(cfg, grim.render_store(store))
    assert written == ["docs/current/decisions.md"]
    assert removed == ["docs/current/stale.md"]
    assert keepme.exists() and not stale.exists()


def test_write_render_is_idempotent(tmp_path):
    write_component(tmp_path, "adr", "why")
    cfg, store = load(tmp_path)
    grim.write_render(cfg, grim.render_store(store))
    written, removed = grim.write_render(cfg, grim.render_store(store))
    assert written == [] and removed == []


def test_run_render_refuses_invalid_store(tmp_path):
    # Lint gate: a store with errors must produce zero filesystem changes.
    write_component(tmp_path, "adr", "good")
    write_component(tmp_path, "note", "evil", extra={"subsystem": "../../escape"})
    result = grim.run_render(tmp_path)
    assert result.exit_code == 1
    assert result.written == [] and result.removed == []
    assert "E062" in [f.code for f in result.findings]
    assert not (tmp_path / "docs" / "current").exists()  # nothing written at all


def test_run_render_refusal_does_not_prune(tmp_path):
    # A previously valid render must survive the store turning invalid.
    write_component(tmp_path, "adr", "why")
    grim.run_render(tmp_path)
    assert (tmp_path / "docs" / "current" / "decisions.md").exists()
    write_component(tmp_path, "note", "broken", raw_fm="id: [unclosed")
    result = grim.run_render(tmp_path)
    assert result.exit_code == 1
    assert (tmp_path / "docs" / "current" / "decisions.md").exists()  # untouched


def test_render_never_touches_external_current_dir(tmp_path):
    # A current: configured outside the project root must die at load_config
    # (Task 1 validation) before write_render can write or prune anything there.
    import pytest
    project = tmp_path / "project"
    project.mkdir()
    write_component(project, "adr", "why")
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "innocent.md").write_text("do not prune me\n")
    (project / ".grimore.toml").write_text(
        f'[grimore]\ncurrent = "{victim.as_posix()}"\n'
    )
    with pytest.raises(grim.ConfigError):
        grim.run_render(project)
    assert (victim / "innocent.md").exists()
    assert list(victim.iterdir()) == [victim / "innocent.md"]  # nothing written either
