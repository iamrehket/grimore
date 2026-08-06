"""The history builder's own contract.

Every shape here is one the digest's tests will depend on being real. A
builder whose "squash" is secretly a merge, or whose shallow clone is not
shallow, would make those tests pass while proving nothing.
"""

import datetime as dt
import subprocess

from history_fixture import History


def test_squash_landing_has_one_parent(tmp_path):
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    h.commit("baseline")
    h.start_branch("feature")
    h.write("adr", "thing", status="draft")
    h.commit("draft it")
    h.write("adr", "thing", status="current")
    h.commit("promote it")
    landed = h.land_squash("feature", "feat: thing (#1)")

    assert len(h.parents(landed)) == 1
    assert landed in h.first_parent_shas()


def test_merge_landing_has_two_parents_and_hides_branch_commits(tmp_path):
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    h.commit("baseline")
    h.start_branch("feature")
    h.write("adr", "thing", status="draft")
    inner = h.commit("draft it")
    h.write("adr", "thing", status="current")
    inner2 = h.commit("promote it")
    landed = h.land_merge("feature", "Merge pull request #1")

    assert len(h.parents(landed)) == 2
    first_parent = h.first_parent_shas()
    assert landed in first_parent
    # The whole point of first-parent: the branch's own commits are not on it.
    assert inner not in first_parent
    assert inner2 not in first_parent


def test_squash_collapses_create_and_promote_into_one_commit(tmp_path):
    # The shape this branch itself will land in: a component created as a
    # draft and promoted before landing reads as absent -> current.
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    h.commit("baseline")
    h.start_branch("feature")
    h.write("adr", "thing", status="draft")
    h.commit("draft it")
    h.write("adr", "thing", status="current")
    h.commit("promote it")
    landed = h.land_squash("feature", "feat: thing (#1)")

    missing = subprocess.run(
        ["git", "cat-file", "-e", f"{landed}~1:docs/components/adr/thing.md"],
        cwd=h.root,
        capture_output=True,
    )
    assert missing.returncode != 0, "component should not exist before the landing"
    after = h._git("show", f"{landed}:docs/components/adr/thing.md")
    assert "status: current" in after


def test_timestamps_need_not_increase(tmp_path):
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    parent = h.commit("baseline", when="2026-03-10T12:00:00+0000")
    h.write("adr", "later", status="current")
    child = h.commit("dated earlier than its parent", when="2026-03-01T12:00:00+0000")

    assert h.committer_epoch(child) < h.committer_epoch(parent)
    assert h.parents(child) == [parent]


def test_local_day_and_utc_day_can_differ(tmp_path):
    # A commit just after local midnight at +1300 belongs to the previous UTC
    # day. The digest resolves its boundary in UTC, so this is the case that
    # separates a correct implementation from one reading `--date=short`.
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    sha = h.commit("new year at +1300", committed="2026-01-01T01:30:00+1300")

    local_day = h._git("log", "-1", "--format=%cd", "--date=short", sha).strip()
    utc_day = str(
        dt.datetime.fromtimestamp(h.committer_epoch(sha), dt.timezone.utc).date()
    )
    assert local_day == "2026-01-01"
    assert utc_day == "2025-12-31"


def test_frontmatter_date_can_disagree_with_landing_date(tmp_path):
    # The adoption backfill's shape: components backdated to when the decision
    # was made, landing weeks later.
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    h.commit("baseline", when="2026-07-01T12:00:00+0000")
    h.write("adr", "backdated", status="current", date="2026-07-24")
    sha = h.commit("land it later", when="2026-07-27T12:00:00+0000")

    text = h._git("show", f"{sha}:docs/components/adr/backdated.md")
    assert "date: 2026-07-24" in text
    landed_day = str(
        dt.datetime.fromtimestamp(h.committer_epoch(sha), dt.timezone.utc).date()
    )
    assert landed_day == "2026-07-27"


def test_one_commit_can_add_many_components(tmp_path):
    h = History(tmp_path)
    h.write("adr", "seed", status="current")
    h.commit("baseline")
    for n in range(12):
        h.write("adr", f"bulk-{n:02d}", status="current")
    sha = h.commit("adoption backfill")

    names = h._git("show", "--name-only", "--format=", sha).split()
    assert len([p for p in names if "bulk-" in p]) == 12


def test_delete_removes_a_component(tmp_path):
    h = History(tmp_path)
    h.write("adr", "doomed", status="current")
    h.commit("baseline")
    h.delete("adr", "doomed")
    sha = h.commit("remove it")

    gone = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}:docs/components/adr/doomed.md"],
        cwd=h.root,
        capture_output=True,
    )
    assert gone.returncode != 0


def test_shallow_clone_is_actually_shallow(tmp_path):
    h = History(tmp_path / "origin")
    for n in range(4):
        h.write("adr", f"c{n}", status="current")
        h.commit(f"commit {n}")

    dest = h.shallow_clone(tmp_path / "shallow", depth=1)
    count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"], cwd=dest, capture_output=True, text=True
    ).stdout.strip()
    assert count == "1", "shallow_clone asserted shallow but kept full history"


def test_local_path_clone_would_not_have_been_shallow(tmp_path):
    # Guards the reason shallow_clone uses a file:// URL. If git ever starts
    # honouring --depth on a local path, this fails and the helper can simplify.
    h = History(tmp_path / "origin")
    for n in range(4):
        h.write("adr", f"c{n}", status="current")
        h.commit(f"commit {n}")

    dest = tmp_path / "plain"
    subprocess.run(
        ["git", "clone", "--depth", "1", str(h.root), str(dest)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    shallow = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=dest,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert shallow == "false"
