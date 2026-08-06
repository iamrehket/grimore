"""The since-date boundary, and what completeness means.

The walker reports everything; this is the layer that bounds it by date and
says whether the history it read was all of it.
"""

import grim
from history_fixture import History


def digest(root, **kw):
    return grim.digest(grim.load_config(root), **kw)


def cids(result):
    return [e.cid for e in result.events if e.cid != "adr-seed"]


def seeded(tmp_path, when="2026-03-01T12:00:00+0000"):
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    h.commit("baseline", when=when)
    return h


# -- the boundary -----------------------------------------------------------


def test_since_includes_the_named_day(tmp_path):
    h = seeded(tmp_path)
    h.write("adr", "onthedog", status="draft")
    h.commit("lands on the boundary", when="2026-03-05T09:00:00+0000")

    assert cids(digest(h.root, since="2026-03-05")) == ["adr-onthedog"]


def test_since_excludes_earlier_landings(tmp_path):
    h = seeded(tmp_path)
    h.write("adr", "early", status="draft")
    h.commit("before", when="2026-03-04T09:00:00+0000")
    h.write("adr", "late", status="draft")
    h.commit("after", when="2026-03-06T09:00:00+0000")

    assert cids(digest(h.root, since="2026-03-05")) == ["adr-late"]


def test_the_boundary_is_utc_not_the_committers_local_day(tmp_path):
    # Local day 2026-01-01 at +1300, UTC day 2025-12-31. A digest since
    # 2026-01-01 must not report it; since 2025-12-31 must.
    h = seeded(tmp_path, when="2025-01-01T12:00:00+0000")
    h.write("adr", "newyear", status="draft")
    h.commit("just after local midnight", committed="2026-01-01T01:30:00+1300")

    assert cids(digest(h.root, since="2026-01-01")) == []
    assert cids(digest(h.root, since="2025-12-31")) == ["adr-newyear"]


def test_out_of_order_history_is_still_fully_walked(tmp_path):
    # A walk that stopped at the first commit older than the boundary would
    # lose the newer landing sitting behind it.
    h = seeded(tmp_path)
    h.write("adr", "ancient", status="draft")
    h.commit("dated years back", when="2020-01-01T12:00:00+0000")
    h.write("adr", "recent", status="draft")
    h.commit("back to now", when="2026-03-10T12:00:00+0000")

    assert cids(digest(h.root, since="2026-03-05")) == ["adr-recent"]
    assert sorted(cids(digest(h.root, since="2019-01-01"))) == [
        "adr-ancient",
        "adr-recent",
    ]


def test_a_backdated_component_is_bounded_by_its_landing(tmp_path):
    # The adoption backfill's shape: frontmatter says 2026-07-24, the history
    # carrying it lands 2026-07-27. A digest whose since-date falls between
    # the two must still report it, dated by the landing.
    h = seeded(tmp_path, when="2026-07-01T12:00:00+0000")
    h.write("adr", "backdated", status="current", date="2026-07-24")
    h.commit("land it later", when="2026-07-27T12:00:00+0000")

    result = digest(h.root, since="2026-07-25")
    assert cids(result) == ["adr-backdated"]
    assert [e.date for e in result.events if e.cid == "adr-backdated"] == ["2026-07-27"]


# -- completeness -----------------------------------------------------------


def test_a_full_clone_is_not_truncated(tmp_path):
    h = seeded(tmp_path)
    h.write("adr", "thing", status="draft")
    h.commit("add it")

    assert digest(h.root).truncated is False


def test_a_shallow_clone_reports_truncated(tmp_path):
    h = History(tmp_path / "origin")
    for n in range(4):
        h.write("adr", f"c{n}", status="current")
        h.commit(f"commit {n}")
    clone = h.shallow_clone(tmp_path / "shallow", depth=1)

    assert digest(clone).truncated is True


def test_a_shallow_clone_does_not_invent_additions_at_the_graft(tmp_path):
    # Everything present at the graft looks added, because the graft has no
    # parent to diff against. Reporting those would be a confident wrong
    # answer about components that have existed for months.
    h = History(tmp_path / "origin")
    for n in range(4):
        h.write("adr", f"c{n}", status="current")
        h.commit(f"commit {n}")
    clone = h.shallow_clone(tmp_path / "shallow", depth=1)

    result = digest(clone)
    assert result.truncated is True
    assert [e.cid for e in result.events] == []


def test_the_truncation_label_is_unconditional(tmp_path):
    # Even when the graft predates the since-date and the answer is in fact
    # complete, the label stands: timestamps are not monotonic, so the digest
    # cannot prove the truncated region held nothing in range.
    h = History(tmp_path / "origin")
    h.write("adr", "old", status="current")
    h.commit("ancient", when="2020-01-01T12:00:00+0000")
    h.write("adr", "new", status="draft")
    h.commit("recent", when="2026-03-10T12:00:00+0000")
    clone = h.shallow_clone(tmp_path / "shallow", depth=1)

    assert digest(clone, since="2026-01-01").truncated is True


# -- which line gets walked -------------------------------------------------


def test_the_remote_tracking_ref_wins_over_a_divergent_local_branch(tmp_path):
    # Same rule the touched-path guard already follows: origin/<default> is
    # what a pull request merges into, so a stale or divergent local ref must
    # never be preferred.
    h = History(tmp_path / "origin")
    h.write("adr", "shared", status="draft")
    h.commit("upstream baseline")

    clone = tmp_path / "clone"
    h._git("clone", f"file://{h.root.resolve()}", str(clone), cwd=tmp_path)
    c = History.existing(clone)
    c.write("adr", "localonly", status="draft")
    c.commit("local-only commit on main")

    assert cids(digest(clone)) == ["adr-shared"]
