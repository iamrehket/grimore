"""Executable contract for finish-docs reconciliation (phase B).

Driven entirely by subprocess, matching test_stamp_spec.py: the scripts ship as
standalone `uv run` files and pytest's pythonpath covers tools/ only, so this
also exercises the production import path for grim rather than a pytest-only one.
"""

import subprocess
import sys
from pathlib import Path

RECONCILE = (
    Path(__file__).resolve().parents[1] / "finish-docs" / "scripts" / "reconcile.py"
)
GRIM = Path(__file__).resolve().parents[1] / "tools" / "grim.py"

OK, WRONG, USAGE, INPUT_REQUIRED = 0, 1, 2, 4
BLOCK = "<!-- grim:status -->\n<!-- /grim:status -->\n"


def run(root, *args, grim=None):
    return subprocess.run(
        [sys.executable, str(RECONCILE), "--root", str(root),
         "--grim", str(grim or GRIM), *args],
        capture_output=True, text=True,
    )


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def component(root, slug, status="current", *, ctype="adr", supersedes=None,
              body="Body prose.", paths=None):
    d = root / "docs" / "components" / ctype
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"id: {ctype}-{slug}", f"type: {ctype}", f"status: {status}"]
    if supersedes:
        lines.append(f"supersedes: [{', '.join(supersedes)}]")
    if paths:
        lines.append(f"paths: [{', '.join(paths)}]")
    lines.append("date: 2026-07-24")
    path = d / f"{slug}.md"
    path.write_text("---\n" + "\n".join(lines) + "\n---\n\n" + body + "\n", encoding="utf-8")
    return path


def spec(root, name="a.md", components=()):
    d = root / "docs" / "specs"
    d.mkdir(parents=True, exist_ok=True)
    path = d / name
    refs = "[" + ", ".join(components) + "]"
    path.write_text(f"---\ncomponents: {refs}\n---\n\n{BLOCK}\n# Spec\n", encoding="utf-8")
    return path


def repo(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "T")
    (tmp_path / ".grimore.toml").write_text("[grimore]\n", encoding="utf-8")
    return tmp_path


def commit(root, msg="change"):
    git(root, "add", "-A")
    git(root, "commit", "-m", msg)


def branch(root, name="feature"):
    git(root, "checkout", "-b", name)


def simple_branch(tmp_path, status="draft"):
    """main with one current component; a branch adding one draft and a spec."""
    repo(tmp_path)
    component(tmp_path, "settled")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "new-thing", status=status)
    spec(tmp_path, "s.md", ["adr-new-thing"])
    commit(tmp_path, "work")
    return tmp_path


# --- survey ------------------------------------------------------------------

def test_survey_lists_the_required_verdict_and_asks_for_input(tmp_path):
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff")
    assert result.returncode == INPUT_REQUIRED, result.stderr
    assert "adr-new-thing" in result.stdout
    assert "VERDICT REQUIRED" in result.stdout


def test_scope_with_nothing_to_decide_is_not_an_input_request(tmp_path):
    # Exit 4 means "you owe me a decision". A branch whose specs reference only
    # settled components owes nothing.
    repo(tmp_path)
    component(tmp_path, "settled")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    spec(tmp_path, "s.md", ["adr-settled"])
    commit(tmp_path, "work")
    result = run(tmp_path, "--branch-diff")
    assert result.returncode == OK, result.stderr
    assert "nothing to reconcile" in result.stdout


def test_no_scope_is_a_usage_error(tmp_path):
    simple_branch(tmp_path)
    assert run(tmp_path).returncode == USAGE


# --- outcomes ----------------------------------------------------------------

def test_promote_flips_only_the_status_byte_range(tmp_path):
    simple_branch(tmp_path)
    path = tmp_path / "docs/components/adr/new-thing.md"
    before = path.read_bytes()
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:promote:built as designed")
    assert result.returncode == OK, result.stderr
    after = path.read_bytes()
    assert after == before.replace(b"status: draft", b"status: current")


def test_promote_preserves_unusual_body_bytes(tmp_path):
    # A reserialize would strip the trailing spaces and collapse the blank
    # lines; only a splice leaves frozen bytes alone.
    repo(tmp_path)
    component(tmp_path, "settled")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    body = "Line one.   \n\n\n   Indented line.\t\n"
    component(tmp_path, "odd", status="draft", body=body)
    spec(tmp_path, "s.md", ["adr-odd"])
    commit(tmp_path, "work")
    path = tmp_path / "docs/components/adr/odd.md"
    before = path.read_bytes()
    assert run(tmp_path, "--branch-diff",
               "--verdict", "adr-odd:promote:shipped").returncode == OK
    assert path.read_bytes() == before.replace(b"status: draft", b"status: current")


def test_keep_draft_writes_nothing(tmp_path):
    simple_branch(tmp_path)
    path = tmp_path / "docs/components/adr/new-thing.md"
    before = path.read_bytes()
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:keep-draft:deferred to a later branch")
    assert result.returncode == OK, result.stderr
    assert path.read_bytes() == before


def test_drop_supersedes_and_warns(tmp_path):
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:drop:never built; the requirement went away")
    assert result.returncode == OK, result.stderr
    assert "status: superseded" in (tmp_path / "docs/components/adr/new-thing.md").read_text()
    assert "WARNING" in result.stdout and "never built" in result.stdout


def test_supersede_writes_the_edge_and_flips_both(tmp_path):
    repo(tmp_path)
    component(tmp_path, "old-way", status="current")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "new-way", status="draft")
    spec(tmp_path, "s.md", ["adr-new-way"])
    commit(tmp_path, "work")
    result = run(
        tmp_path, "--branch-diff", "--component", "adr-old-way",
        "--verdict", "adr-new-way:promote:this is what shipped",
        "--verdict", "adr-old-way:supersede=adr-new-way:replaced by the new way",
    )
    assert result.returncode == OK, result.stderr
    new = (tmp_path / "docs/components/adr/new-way.md").read_text()
    old = (tmp_path / "docs/components/adr/old-way.md").read_text()
    assert "supersedes: [adr-old-way]" in new and "status: current" in new
    assert "status: superseded" in old
    # The cascade is what E032 exists to require. Only E090 banner drift should
    # remain, which is the normal state until `lint --fix` runs.
    lint = subprocess.run(
        [sys.executable, str(GRIM), "lint", "--root", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert "E032" not in lint.stdout
    assert [line.split()[1] for line in lint.stdout.splitlines() if line.startswith("ERROR")] == ["E090"]


def test_amend_reports_changed_lines_for_a_draft_present_at_the_merge_base(tmp_path):
    repo(tmp_path)
    component(tmp_path, "thing", status="draft", body="As designed.")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "thing", status="draft", body="As actually built.")
    spec(tmp_path, "s.md", ["adr-thing"])
    commit(tmp_path, "work")
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-thing:amend:details differ, the decision stands")
    assert result.returncode == OK, result.stderr
    assert "body amended since the merge-base" in result.stdout


def test_branch_new_draft_is_not_labelled_amended(tmp_path):
    # Every branch-new draft would otherwise report its whole body as amended,
    # turning the signal into noise on the common case.
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:promote:built as designed")
    assert "amended" not in result.stdout
    assert "new on this branch" in result.stdout


# --- completeness ------------------------------------------------------------

def test_missing_verdict_asks_for_input(tmp_path):
    repo(tmp_path)
    component(tmp_path, "settled")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "one", status="draft")
    component(tmp_path, "two", status="draft")
    spec(tmp_path, "s.md", ["adr-one", "adr-two"])
    commit(tmp_path, "work")
    result = run(tmp_path, "--branch-diff", "--verdict", "adr-one:promote:shipped")
    assert result.returncode == INPUT_REQUIRED
    assert "adr-two" in result.stdout
    assert (tmp_path / "docs/components/adr/one.md").read_text().count("draft") == 1


def test_a_draft_no_spec_references_is_still_required(tmp_path):
    # Created on the branch and forgotten: nothing else in the system notices.
    repo(tmp_path)
    component(tmp_path, "settled")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "orphan", status="draft")
    spec(tmp_path, "s.md", [])
    commit(tmp_path, "work")
    result = run(tmp_path, "--branch-diff")
    assert result.returncode == INPUT_REQUIRED
    assert "adr-orphan" in result.stdout
    assert "created on this branch" in result.stdout


def test_untracked_files_under_governed_dirs_are_refused(tmp_path):
    # One tracked spec would satisfy a zero-spec check while an untracked spec
    # and its untracked draft stayed outside the required set entirely.
    simple_branch(tmp_path)
    spec(tmp_path, "unstaged.md", ["adr-new-thing"])
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:promote:shipped")
    assert result.returncode == USAGE
    assert "untracked" in result.stderr and "unstaged.md" in result.stderr
    assert "git add" in result.stderr


def test_branch_diff_with_no_specs_refuses(tmp_path):
    repo(tmp_path)
    component(tmp_path, "settled")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    (tmp_path / "code.py").write_text("x = 1\n")
    commit(tmp_path, "code only")
    result = run(tmp_path, "--branch-diff")
    assert result.returncode == USAGE
    assert "no specs" in result.stderr


def test_duplicate_verdicts_are_refused(tmp_path):
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:promote:a",
                 "--verdict", "adr-new-thing:drop:b")
    assert result.returncode == WRONG
    assert "two verdicts" in result.stderr


def test_verdict_outside_scope_is_refused(tmp_path):
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:promote:shipped",
                 "--verdict", "adr-settled:drop:unrelated")
    assert result.returncode == WRONG
    assert "not in scope" in result.stderr and "--component adr-settled" in result.stderr


# --- composition -------------------------------------------------------------

def test_three_link_chain_conflict_is_refused(tmp_path):
    # A:supersede=B promotes B, while B:supersede=C supersedes it. Inspecting
    # only cascade targets would let this through and invert an explicit verdict.
    repo(tmp_path)
    component(tmp_path, "a", status="current")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "b", status="draft")
    component(tmp_path, "c", status="draft")
    spec(tmp_path, "s.md", ["adr-b", "adr-c"])
    commit(tmp_path, "work")
    result = run(
        tmp_path, "--branch-diff", "--component", "adr-a",
        "--verdict", "adr-a:supersede=adr-b:replaced by b",
        "--verdict", "adr-b:supersede=adr-c:replaced by c",
        "--verdict", "adr-c:promote:this is what shipped",
    )
    assert result.returncode == WRONG
    assert "conflicting intents for 'adr-b'" in result.stderr


def test_keep_draft_conflicting_with_a_supersede_is_refused(tmp_path):
    repo(tmp_path)
    component(tmp_path, "a", status="current")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "b", status="draft")
    spec(tmp_path, "s.md", ["adr-b"])
    commit(tmp_path, "work")
    result = run(
        tmp_path, "--branch-diff", "--component", "adr-a",
        "--verdict", "adr-a:supersede=adr-b:replaced by b",
        "--verdict", "adr-b:keep-draft:not ready",
    )
    assert result.returncode == WRONG
    assert "conflicting intents for 'adr-b'" in result.stderr


def test_unaccounted_supersede_edge_is_refused(tmp_path):
    # An agent that hand-writes supersedes: before running would otherwise flip
    # a live decision with nobody stating that it should be flipped.
    repo(tmp_path)
    component(tmp_path, "old", status="current")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "new", status="draft", supersedes=["adr-old"])
    spec(tmp_path, "s.md", ["adr-new"])
    commit(tmp_path, "work")
    result = run(tmp_path, "--branch-diff", "--verdict", "adr-new:promote:shipped")
    assert result.returncode == WRONG
    assert "no verdict accounts for" in result.stderr
    assert "--verdict 'adr-old:supersede=adr-new" in result.stderr


def test_preauthored_edge_is_not_duplicated(tmp_path):
    # Edges merge as a set: appending a target already on disk made check_edges
    # report the same successor twice as two live successors.
    repo(tmp_path)
    component(tmp_path, "old", status="current")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "new", status="draft", supersedes=["adr-old"])
    spec(tmp_path, "s.md", ["adr-new"])
    commit(tmp_path, "work")
    result = run(
        tmp_path, "--branch-diff", "--component", "adr-old",
        "--verdict", "adr-new:promote:shipped",
        "--verdict", "adr-old:supersede=adr-new:replaced",
    )
    assert result.returncode == OK, result.stderr
    text = (tmp_path / "docs/components/adr/new.md").read_text()
    assert text.count("adr-old") == 1
    assert "supersedes: [adr-old]" in text


def test_supersede_cycle_is_refused(tmp_path):
    # grim cannot catch this: two mutually-superseding components lint clean.
    repo(tmp_path)
    component(tmp_path, "settled")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "a", status="draft")
    component(tmp_path, "b", status="draft", supersedes=["adr-a"])
    spec(tmp_path, "s.md", ["adr-a", "adr-b"])
    commit(tmp_path, "work")
    result = run(
        tmp_path, "--branch-diff",
        "--verdict", "adr-b:supersede=adr-a:b replaced by a",
        "--verdict", "adr-a:promote:shipped",
    )
    assert result.returncode == WRONG
    assert "cycle" in result.stderr


def test_promoting_a_non_draft_is_refused(tmp_path):
    # E040 skips components new on the branch, so grim would not catch a
    # superseded -> current resurrection of one. This is the only guard.
    repo(tmp_path)
    component(tmp_path, "settled")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "gone", status="superseded")
    spec(tmp_path, "s.md", [])
    commit(tmp_path, "work")
    result = run(tmp_path, "--component", "adr-gone",
                 "--verdict", "adr-gone:promote:looks done")
    assert result.returncode == WRONG
    assert "not a legal transition" in result.stderr


# --- the orphan route --------------------------------------------------------

def test_component_promotes_a_draft_no_spec_references(tmp_path):
    # The acceptance shape: a backfilled draft recording a decision implemented
    # long ago, reachable by no spec.
    repo(tmp_path)
    component(tmp_path, "backfilled", status="draft", paths=["src/"])
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "x.py").write_text("x = 1\n")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    (tmp_path / "unrelated.txt").write_text("hello\n")
    commit(tmp_path, "unrelated work")
    result = run(tmp_path, "--component", "adr-backfilled",
                 "--verdict", "adr-backfilled:promote:src/ has implemented this since June")
    assert result.returncode == OK, result.stderr
    assert "status: current" in (tmp_path / "docs/components/adr/backfilled.md").read_text()
    # Reported, never gated - a gate here would refuse the acceptance case.
    assert "which this branch does not touch" in result.stdout
    assert "no spec references this component" in result.stdout


# --- the transaction ---------------------------------------------------------

def flaky_grim(tmp_path, mode):
    """A grim that behaves normally once, then fails the way `mode` says.

    The same file is used for the import and the subprocess, which is the
    contract: helper semantics and lint semantics must not come from different
    versions.
    """
    marker = tmp_path / "grim-calls.txt"
    shim = tmp_path / "flaky_grim.py"
    shim.write_text(f'''
import importlib.util, json, pathlib, sys
_spec = importlib.util.spec_from_file_location("real_grim", {str(GRIM)!r})
_m = importlib.util.module_from_spec(_spec)
sys.modules["real_grim"] = _m
_spec.loader.exec_module(_m)
globals().update({{k: v for k, v in vars(_m).items() if not k.startswith("__")}})

if __name__ == "__main__":
    marker = pathlib.Path({str(marker)!r})
    n = int(marker.read_text()) if marker.exists() else 0
    marker.write_text(str(n + 1))
    if n >= 1:
        if {mode!r} == "crash":
            sys.stderr.write("simulated grim explosion\\n")
            sys.exit(2)
        print(json.dumps({{"errors": [
            {{"code": "E031", "path": "docs/components/adr/x.md",
              "message": "simulated post-write breakage"}}]}}))
        sys.exit(1)
    sys.exit(_m.main(sys.argv[1:]))
''', encoding="utf-8")
    return shim


def test_rollback_is_byte_identical_when_grim_reports_a_new_error(tmp_path):
    simple_branch(tmp_path)
    path = tmp_path / "docs/components/adr/new-thing.md"
    before = path.read_bytes()
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:promote:shipped",
                 grim=flaky_grim(tmp_path, "errors"))
    assert result.returncode == WRONG
    assert "simulated post-write breakage" in result.stderr
    assert "nothing was written" in result.stderr
    assert path.read_bytes() == before


def test_rollback_when_grim_exits_two_with_no_json(tmp_path):
    # The failure the naive gate missed: parsing `errors` out of stdout finds
    # none, so "no errors appeared" would read as success and keep the writes.
    simple_branch(tmp_path)
    path = tmp_path / "docs/components/adr/new-thing.md"
    before = path.read_bytes()
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:promote:shipped",
                 grim=flaky_grim(tmp_path, "crash"))
    assert result.returncode == USAGE
    assert "could not evaluate" in result.stderr
    assert path.read_bytes() == before


def test_dry_run_verifies_then_writes_nothing(tmp_path):
    simple_branch(tmp_path)
    path = tmp_path / "docs/components/adr/new-thing.md"
    before = path.read_bytes()
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:promote:shipped", "--dry-run")
    assert result.returncode == OK, result.stderr
    assert "WOULD PROMOTE" in result.stdout
    assert path.read_bytes() == before


def test_dry_run_still_catches_an_illegal_result(tmp_path):
    # Same code path as a real run: apply, ask grim, roll back. A dry run that
    # only printed intentions would report this as fine.
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:promote:shipped", "--dry-run",
                 grim=flaky_grim(tmp_path, "errors"))
    assert result.returncode == WRONG


# --- argument handling -------------------------------------------------------

def test_evidence_is_required(tmp_path):
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff", "--verdict", "adr-new-thing:promote:")
    assert result.returncode == USAGE
    assert "evidence is required" in result.stderr


def test_evidence_may_contain_colons(tmp_path):
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff",
                 "--verdict", "adr-new-thing:promote:built: exactly as designed")
    assert result.returncode == OK, result.stderr
    assert "built: exactly as designed" in result.stdout


def test_unknown_outcome_is_a_usage_error(tmp_path):
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff", "--verdict", "adr-new-thing:merge:why")
    assert result.returncode == USAGE
    assert "unknown outcome" in result.stderr


def test_supersede_needs_a_successor(tmp_path):
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff", "--verdict", "adr-new-thing:supersede:why")
    assert result.returncode == USAGE
    assert "needs a successor" in result.stderr


def test_missing_grim_is_a_usage_error(tmp_path):
    simple_branch(tmp_path)
    result = run(tmp_path, "--branch-diff", grim=tmp_path / "nope.py")
    assert result.returncode == USAGE
    assert "grim not found" in result.stderr


# --- the drop -> stamp seam --------------------------------------------------

STAMPER = (
    Path(__file__).resolve().parents[1] / "finish-docs" / "scripts" / "stamp_spec.py"
)


def stamp(root, *args):
    return subprocess.run(
        [sys.executable, str(STAMPER), "--root", str(root), "--grim", str(GRIM),
         "--date", "2026-07-30", "--pr", "99", *args],
        capture_output=True, text=True,
    )


def test_dropped_work_cannot_then_be_stamped_implemented(tmp_path):
    # The laundering path, end to end: reconcile writes `superseded` for work
    # that was never built, and a superseded component does not otherwise block
    # a stamp. Only reachability distinguishes it from a replacement.
    simple_branch(tmp_path)
    assert run(tmp_path, "--branch-diff",
               "--verdict", "adr-new-thing:drop:never built; requirement withdrawn"
               ).returncode == OK
    result = stamp(tmp_path, "--spec", "docs/specs/s.md")
    assert result.returncode == 1
    assert "abandoned with no live successor" in result.stderr
    assert "implemented" not in (tmp_path / "docs/specs/s.md").read_text()


def test_superseded_work_can_be_stamped_implemented(tmp_path):
    # The same status, the opposite meaning: replaced work WAS implemented.
    repo(tmp_path)
    component(tmp_path, "old-way", status="current")
    commit(tmp_path, "baseline")
    branch(tmp_path)
    component(tmp_path, "new-way", status="draft")
    spec(tmp_path, "s.md", ["adr-old-way", "adr-new-way"])
    commit(tmp_path, "work")
    assert run(
        tmp_path, "--branch-diff", "--component", "adr-old-way",
        "--verdict", "adr-new-way:promote:this is what shipped",
        "--verdict", "adr-old-way:supersede=adr-new-way:replaced by the new way",
    ).returncode == OK
    result = stamp(tmp_path, "--spec", "docs/specs/s.md")
    assert result.returncode == 0, result.stderr
    assert "implemented" in (tmp_path / "docs/specs/s.md").read_text()
