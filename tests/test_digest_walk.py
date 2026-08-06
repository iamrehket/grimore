"""The first-parent walker and the event model.

One test per row of the spec's events table, plus the rule covering every
transition the table does not list. The walker reports what landed on the
default branch's first-parent line; it does not filter by date, which is
Task 3's job.
"""

import grim
from history_fixture import History


def events_for(h, cid):
    cfg = grim.load_config(h.root)
    return [e for e in grim.walk_events(cfg) if e.cid == cid]


def only_event(h, cid):
    got = events_for(h, cid)
    assert len(got) == 1, f"expected exactly one event for {cid}, got {got}"
    return got[0]


def seeded(tmp_path):
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    h.commit("baseline")
    return h


# -- the six legal transitions ---------------------------------------------


def test_absent_to_draft_is_added_draft(tmp_path):
    h = seeded(tmp_path)
    h.write("adr", "thing", status="draft")
    h.commit("draft it")

    assert only_event(h, "adr-thing").label == "added, draft"


def test_absent_to_current_is_added_live(tmp_path):
    # The collapsed shape a squashed branch produces, and the one this branch
    # will itself land in.
    h = seeded(tmp_path)
    h.start_branch("feature")
    h.write("adr", "thing", status="draft")
    h.commit("draft it")
    h.write("adr", "thing", status="current")
    h.commit("promote it")
    h.land_squash("feature", "feat: thing (#1)")

    assert only_event(h, "adr-thing").label == "added, live"


def test_absent_to_superseded_is_added_already_superseded(tmp_path):
    h = seeded(tmp_path)
    h.start_branch("feature")
    h.write("adr", "thing", status="draft")
    h.commit("draft it")
    h.write("adr", "thing", status="superseded")
    h.commit("abandon it")
    h.land_squash("feature", "feat: never mind (#1)")

    assert only_event(h, "adr-thing").label == "added, already superseded"


def test_draft_to_current_is_promoted(tmp_path):
    h = seeded(tmp_path)
    h.write("adr", "thing", status="draft")
    h.commit("draft it")
    h.write("adr", "thing", status="current")
    h.commit("promote it")

    labels = [e.label for e in events_for(h, "adr-thing")]
    assert labels == ["added, draft", "promoted"]


def test_draft_to_superseded_is_abandoned(tmp_path):
    h = seeded(tmp_path)
    h.write("adr", "thing", status="draft")
    h.commit("draft it")
    h.write("adr", "thing", status="superseded")
    h.commit("abandon it")

    assert [e.label for e in events_for(h, "adr-thing")][-1] == "abandoned"


def test_current_to_superseded_is_superseded(tmp_path):
    h = seeded(tmp_path)
    h.write("adr", "thing", status="current")
    h.commit("add it live")
    h.write("adr", "thing", status="superseded")
    h.commit("replace it")

    assert [e.label for e in events_for(h, "adr-thing")][-1] == "superseded"


# -- everything the table does not list ------------------------------------


def test_current_to_draft_is_a_violation(tmp_path):
    h = seeded(tmp_path)
    h.write("adr", "thing", status="current")
    h.commit("add it live")
    h.write("adr", "thing", status="draft")
    h.commit("illegally demote it")

    got = events_for(h, "adr-thing")[-1]
    assert got.violation
    assert "current" in got.label and "draft" in got.label


def test_removal_is_a_violation(tmp_path):
    h = seeded(tmp_path)
    h.write("adr", "doomed", status="current")
    h.commit("add it live")
    h.delete("adr", "doomed")
    h.commit("delete it")

    got = events_for(h, "adr-doomed")[-1]
    assert got.violation
    assert "absent" in got.label


def test_superseded_to_current_is_a_violation(tmp_path):
    h = seeded(tmp_path)
    h.write("adr", "thing", status="superseded")
    h.commit("add it superseded")
    h.write("adr", "thing", status="current")
    h.commit("resurrect it")

    got = events_for(h, "adr-thing")[-1]
    assert got.violation


# -- walking rules ----------------------------------------------------------


def test_merge_landing_reports_one_event_at_the_merge(tmp_path):
    h = seeded(tmp_path)
    h.start_branch("feature")
    h.write("adr", "thing", status="draft")
    h.commit("draft it")
    h.write("adr", "thing", status="current")
    h.commit("promote it")
    landed = h.land_merge("feature", "Merge pull request #1")

    got = only_event(h, "adr-thing")
    assert got.label == "added, live"
    assert landed.startswith(got.commit)


def test_event_date_is_the_utc_day_not_the_committer_local_day(tmp_path):
    # A commit just after local midnight at +1300 belongs to the previous UTC
    # day. Reading `--date=short` would report the local day and still pass
    # every determinism run, so this is the assertion that separates them.
    h = seeded(tmp_path)
    h.write("adr", "thing", status="draft")
    h.commit("new year at +1300", committed="2026-01-01T01:30:00+1300")

    assert only_event(h, "adr-thing").date == "2025-12-31"


def test_walk_does_not_stop_at_a_commit_older_than_its_child(tmp_path):
    # Timestamps are not monotonic. A walk that short-circuits on date order
    # would lose everything behind the out-of-order commit.
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    h.commit("baseline", when="2026-03-01T12:00:00+0000")
    h.write("adr", "early", status="draft")
    h.commit("dated far in the past", when="2020-01-01T12:00:00+0000")
    h.write("adr", "late", status="draft")
    h.commit("back to now", when="2026-03-02T12:00:00+0000")

    assert only_event(h, "adr-early").date == "2020-01-01"
    assert only_event(h, "adr-late").date == "2026-03-02"


def test_ordering_is_commits_oldest_first_then_id_ascending(tmp_path):
    h = seeded(tmp_path)
    for slug in ("zulu", "alpha", "mike"):
        h.write("adr", slug, status="draft")
    h.commit("bulk add")
    h.write("adr", "alpha", status="current")
    h.commit("promote alpha")

    cfg = grim.load_config(h.root)
    got = [(e.cid, e.label) for e in grim.walk_events(cfg) if e.cid != "adr-seed"]
    assert got == [
        ("adr-alpha", "added, draft"),
        ("adr-mike", "added, draft"),
        ("adr-zulu", "added, draft"),
        ("adr-alpha", "promoted"),
    ]
