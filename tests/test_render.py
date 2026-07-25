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
