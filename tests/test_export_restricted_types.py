"""Bundle and digest behavior under a restricted `.grimore.toml`.

IAM-46's lifecycle gate asks for a scenario exercising a config that
enables only a subset of the six component types. Nothing else in the
suite runs the human exports (`grim render --bundle` and `grim render
--digest`) against a restricted `types` list, so this file is that
scenario, written as pytest tests rather than a scenario document.

Four questions drive the coverage:

- Bundle: does a restricted config omit whole sections for disabled
  types, rather than emitting empty headings?
- Digest: does it still report lifecycle events correctly when the
  config is restricted?
- A disabled type's component on disk: lint objects to it (E005, from
  `load_store`) and it never enters the store, but `walk_events` diffs
  raw git blobs under the whole components directory and does not
  consult `cfg.types` at all. That asymmetry is real, not a bug this
  file invents - it is pinned explicitly below rather than left
  accidental.
- Bundle coherence: do section ordering and the store hash stay
  consistent when the live store is a strict subset of the six types?
"""

import grim
from history_fixture import History


def restrict(root, types):
    """Write a `.grimore.toml` that enables only the given types."""
    listed = ", ".join(f'"{t}"' for t in types)
    (root / ".grimore.toml").write_text(
        f"[grimore]\ntypes = [{listed}]\n", encoding="utf-8"
    )


def bundle(root):
    cfg = grim.load_config(root)
    return grim.render_bundle(cfg, grim.load_store(cfg))


def events_by_cid(root, **kw):
    cfg = grim.load_config(root)
    return {e.cid: e for e in grim.digest(cfg, **kw).events}


def test_bundle_omits_whole_sections_for_disabled_types(tmp_path):
    # Only adr and usecase are enabled: term, constraint, nongoal, and
    # note never appear on disk at all, which is the ordinary shape of
    # a restricted project rather than a migration in progress.
    restrict(tmp_path, ["adr", "usecase"])
    h = History(tmp_path)
    h.write("adr", "alpha", status="current", body="Alpha decided.")
    h.write("usecase", "catch-up", status="current", body="Catching up.")
    h.commit("baseline")

    text = bundle(h.root)

    assert "## Use cases" in text
    assert "# Decisions" in text
    # The other charter subsections and the disabled top-level
    # sections have nothing to render, and disabled must mean absent
    # rather than an empty heading.
    assert "## Constraints" not in text
    assert "## Non-goals" not in text
    assert "# Glossary" not in text


def test_digest_reports_events_normally_under_a_restricted_config(tmp_path):
    restrict(tmp_path, ["adr", "usecase"])
    h = History(tmp_path)
    h.write("adr", "alpha", status="draft")
    h.commit("first landing", when="2026-05-01T12:00:00+0000")
    h.write("adr", "alpha", status="current")
    h.write("usecase", "catch-up", status="current")
    h.commit("second landing", when="2026-05-02T12:00:00+0000")

    events = events_by_cid(h.root)

    assert events["adr-alpha"].label == "promoted"
    assert events["usecase-catch-up"].label == "added, live"


def test_a_disabled_types_component_is_lint_rejected_but_still_walked(tmp_path):
    # term is on disk but not in the enabled set - the shape the plan
    # asks to pin down. check_schema's E005 fires from load_store,
    # which filters by directory name against cfg.types, so the
    # component never reaches the store or the bundle. walk_events,
    # which the digest is built on, diffs raw git blobs under the
    # whole components directory and never consults cfg.types, so it
    # reports the same component's history regardless.
    restrict(tmp_path, ["adr"])
    h = History(tmp_path)
    h.write("adr", "alpha", status="current", body="Alpha decided.")
    h.write("term", "widget", status="current", body="A widget is a thing.")
    h.commit("baseline")

    cfg = grim.load_config(h.root)
    store = grim.load_store(cfg)

    assert "E005" in [f.code for f in store.findings]
    assert "term-widget" not in [c.cid for c in store.components]

    text = grim.render_bundle(cfg, store)
    assert "A widget is a thing." not in text

    events = events_by_cid(h.root)
    assert events["term-widget"].label == "added, live"


def test_bundle_ordering_and_store_hash_hold_under_a_restricted_config(tmp_path):
    restrict(tmp_path, ["term", "usecase", "adr"])
    h = History(tmp_path)
    h.write("usecase", "catch-up", status="current", body="A use case.")
    h.write("adr", "alpha", status="current", body="A decision.")
    h.write("term", "widget", status="current", body="A term.")
    h.commit("baseline")

    cfg = grim.load_config(h.root)
    store = grim.load_store(cfg)
    expected_hash = grim.store_hash(store)

    text = grim.render_bundle(cfg, store)

    assert (
        text.index("# Charter")
        < text.index("# Decisions")
        < text.index("# Glossary")
    )
    assert f"sha256:{expected_hash}" in text
