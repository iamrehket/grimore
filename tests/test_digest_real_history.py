"""The digest against this repository's own history, not a fixture.

Every other digest test builds a synthetic History and drives it through
shapes someone sat down and designed: a merge, a squash, a backdated
frontmatter date. Real history was not designed for anything - it is
whatever landed. `adr-payload-renderer-split` happens to carry two of those
shapes on its own: it was authored on a side branch and entered the default
branch's first-parent line at a pull request merge (a commit that never
touched the file itself, just brought a branch tip in), and it was later
promoted from draft to current in a single squashed commit with no merge to
attribute the change to. Testing against it catches anything the fixtures'
tidier shapes could not have thought to ask for.

Task 3's trap governs how these locate their boundary: no hardcoded
since-date. Each test finds the promotion commit with raw git plumbing -
never by reading grim.digest()'s own output - and derives the since-date
from that commit's own committer date. A walker that silently dropped the
event would otherwise be free to hand back a boundary chosen to exclude
exactly what it dropped, and the assertion would go green over a broken
walk. Deriving the boundary independently is what makes the assertion mean
something.

Two failure modes are named risks of testing against a live repository
rather than a fixture, and both are handled rather than ignored: a shallow
checkout cannot see far enough back, and this repository's own history can
be rebased, which moves commit hashes and dates. The tests skip loudly on
the first and are pinned to the component and its transition - never a
literal hash or date - to survive the second.
"""

from __future__ import annotations

import datetime
import re
import subprocess
from pathlib import Path

import pytest

import grim

REPO_ROOT = Path(__file__).resolve().parents[1]

COMPONENT_PATH = "docs/components/adr/payload-renderer-split.md"
COMPONENT_CID = "adr-payload-renderer-split"

# A deliberately independent frontmatter reader. Reusing grim's own YAML
# parsing would still be fine in principle - the trap is about the walker's
# *output*, not its parsing helpers - but a plain regex keeps this file's
# derivation legible as plumbing, with nothing borrowed from the code under
# test.
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
STATUS_LINE_RE = re.compile(r"^status:\s*(\S+)\s*$", re.MULTILINE)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True
    )


def _resolve_ref(cfg: grim.Config) -> str | None:
    """origin/<default> first, then the local branch.

    Same fallback order digest() itself uses, but resolved here with a
    direct plumbing call so this test's notion of "the default branch" does
    not depend on grim's resolver being correct.
    """
    for ref in (f"origin/{cfg.default_branch}", cfg.default_branch):
        if _git("rev-parse", "--verify", "--quiet", ref).returncode == 0:
            return ref
    return None


def _first_parent_shas(ref: str) -> list[str]:
    r = _git("rev-list", "--first-parent", "--reverse", ref)
    assert r.returncode == 0, f"git rev-list --first-parent failed: {r.stderr}"
    return r.stdout.split()


def _parent_count(sha: str) -> int:
    r = _git("rev-list", "--parents", "-n1", sha)
    assert r.returncode == 0, f"git rev-list --parents failed: {r.stderr}"
    return len(r.stdout.split()) - 1


def _status_at(rev: str, path: str) -> str | None:
    r = _git("show", f"{rev}:{path}")
    if r.returncode != 0:
        return None
    m = FRONTMATTER_RE.match(r.stdout)
    if not m:
        return None
    sm = STATUS_LINE_RE.search(m.group(1))
    return sm.group(1) if sm else None


def _short_sha(sha: str) -> str:
    r = _git("rev-parse", "--short", sha)
    assert r.returncode == 0, f"git rev-parse --short failed: {r.stderr}"
    return r.stdout.strip()


def _utc_date(sha: str) -> datetime.date:
    # Same conversion the digest uses for its own event dates: read the
    # epoch and convert here, rather than trust `--date=short`, which
    # renders in whatever offset the commit recorded.
    r = _git("log", "-1", "--format=%ct", sha)
    assert r.returncode == 0, f"git log failed: {r.stderr}"
    epoch = int(r.stdout.strip())
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).date()


def _find_transition(ref: str, path: str, prev: str, curr: str) -> str | None:
    """The first first-parent commit where `path`'s status moves prev -> curr.

    `git rev-list --first-parent` restricts traversal to first-parent edges
    only, so in the reversed (oldest-first) list each entry's predecessor
    *is* its first parent. Comparing consecutive entries here is therefore
    the same comparison the walker makes against parents[0] - just made
    independently, with no call into grim's own walk.
    """
    prior: str | None = None
    for sha in _first_parent_shas(ref):
        status = _status_at(sha, path)
        if prior == prev and status == curr:
            return sha
        prior = status
    return None


@pytest.fixture
def real_promotion():
    """Locate the component's draft -> current commit and its landing date.

    Entirely by git plumbing against this checkout's actual history, never
    by asking grim.digest() where the promotion happened.
    """
    cfg = grim.load_config(REPO_ROOT)
    if grim.is_shallow(cfg):
        pytest.skip("checkout is shallow; the digest cannot see full history")
    ref = _resolve_ref(cfg)
    if ref is None:
        pytest.skip(
            f"cannot resolve origin/{cfg.default_branch} or "
            f"{cfg.default_branch} locally"
        )
    sha = _find_transition(ref, COMPONENT_PATH, "draft", "current")
    assert sha is not None, (
        f"expected a draft -> current commit for {COMPONENT_CID} on "
        f"{ref}'s first-parent line; has this repository's history changed?"
    )
    # The plan describes this landing as squashed, with no merge to
    # attribute it to. A second parent here would mean the fixture this
    # test relies on no longer matches that shape.
    assert _parent_count(sha) == 1, (
        f"expected {COMPONENT_CID}'s promotion ({sha}) to be a single-"
        "parent, squashed commit; it now has a merge to attribute it to"
    )
    return cfg, ref, sha, _utc_date(sha)


def test_a_range_covering_the_promotions_landing_reports_it_against_that_commit(
    real_promotion,
):
    cfg, ref, sha, landing_date = real_promotion

    result = grim.digest(cfg, ref=ref, since=landing_date.isoformat())

    events = [e for e in result.events if e.cid == COMPONENT_CID]
    assert len(events) == 1, events
    event = events[0]
    assert event.label == "promoted"
    assert event.date == landing_date.isoformat()
    # The event's commit is grim's own abbreviation of the same sha this
    # test located independently, not a value copied from either side.
    assert sha.startswith(event.commit)
    assert event.commit == _short_sha(sha)


def test_a_range_starting_after_the_promotion_reports_no_transition_at_all(
    real_promotion,
):
    cfg, ref, sha, landing_date = real_promotion
    day_after = landing_date + datetime.timedelta(days=1)

    result = grim.digest(cfg, ref=ref, since=day_after.isoformat())

    events = [e for e in result.events if e.cid == COMPONENT_CID]
    assert events == []
