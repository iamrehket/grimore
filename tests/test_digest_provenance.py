"""Where a digest line says its component came from.

Two references answer different questions: the spec that claims the component
is where it came from, the commit is where this transition happened. The
commit is always available; the spec often is not - 41 of this repository's 52
live components are claimed by no spec at all, so the unclaimed case is the
majority path, not an edge.
"""

import re

import grim
from helpers import write_spec
from history_fixture import History


def digest(root, **kw):
    return grim.digest(grim.load_config(root), **kw)


def event_for(root, cid, **kw):
    got = [e for e in digest(root, **kw).events if e.cid == cid]
    assert len(got) == 1, f"expected one event for {cid}, got {got}"
    return got[0]


def seeded(tmp_path):
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    h.commit("baseline")
    return h


def test_a_component_claimed_by_one_spec_carries_it(tmp_path):
    h = seeded(tmp_path)
    write_spec(h.root, "2026-08-01-thing.md", raw_fm="components:\n  - adr-thing")
    h.write("adr", "thing", status="draft")
    h.commit("draft it")

    assert event_for(h.root, "adr-thing").specs == ("docs/specs/2026-08-01-thing.md",)


def test_a_component_no_spec_claims_carries_none(tmp_path):
    # The majority path. An empty tuple, not a placeholder - the renderer
    # decides how to show absence.
    h = seeded(tmp_path)
    h.write("adr", "orphan", status="draft")
    h.commit("draft it")

    assert event_for(h.root, "adr-orphan").specs == ()


def test_two_claiming_specs_are_both_listed_sorted_by_filename(tmp_path):
    # Nothing in lint forbids it and no component is doubly claimed today, so
    # this is a store defect rather than an expected case. The rule exists to
    # keep output deterministic when one occurs.
    h = seeded(tmp_path)
    write_spec(h.root, "2026-08-02-later.md", raw_fm="components:\n  - adr-shared")
    write_spec(h.root, "2026-08-01-earlier.md", raw_fm="components:\n  - adr-shared")
    h.write("adr", "shared", status="draft")
    h.commit("draft it")

    assert event_for(h.root, "adr-shared").specs == (
        "docs/specs/2026-08-01-earlier.md",
        "docs/specs/2026-08-02-later.md",
    )


def test_a_spec_with_no_frontmatter_is_skipped_not_fatal(tmp_path):
    # The two legacy design specs in this repository carry none at all.
    h = seeded(tmp_path)
    (h.root / "docs" / "specs").mkdir(parents=True, exist_ok=True)
    (h.root / "docs" / "specs" / "legacy.md").write_text("# Design\n\nNo frontmatter.\n")
    h.write("adr", "thing", status="draft")
    h.commit("draft it")

    assert event_for(h.root, "adr-thing").specs == ()


def test_a_spec_without_a_components_key_is_skipped(tmp_path):
    h = seeded(tmp_path)
    write_spec(h.root, "2026-08-01-thing.md", raw_fm="implemented: '2026-08-01 (PR #1)'")
    h.write("adr", "thing", status="draft")
    h.commit("draft it")

    assert event_for(h.root, "adr-thing").specs == ()


def test_only_the_configured_specs_directory_is_read(tmp_path):
    # An ungoverned tree of spec-shaped files must not contribute provenance,
    # even when it claims a component by id.
    h = seeded(tmp_path)
    legacy = h.root / "docs" / "superpowers" / "specs"
    legacy.mkdir(parents=True)
    (legacy / "old.md").write_text("---\ncomponents:\n  - adr-thing\n---\n\n# Old\n")
    h.write("adr", "thing", status="draft")
    h.commit("draft it")

    assert event_for(h.root, "adr-thing").specs == ()


def test_references_need_no_remote(tmp_path):
    # The fixture has no remote at all. Provenance is a repo-relative path and
    # an abbreviated hash, so it resolves on a checkout that was never pushed.
    h = seeded(tmp_path)
    write_spec(h.root, "2026-08-01-thing.md", raw_fm="components:\n  - adr-thing")
    h.write("adr", "thing", status="draft")
    h.commit("draft it")

    got = event_for(h.root, "adr-thing")
    assert got.specs == ("docs/specs/2026-08-01-thing.md",)
    assert re.fullmatch(r"[0-9a-f]{7,40}", got.commit)
    assert "://" not in got.specs[0]
