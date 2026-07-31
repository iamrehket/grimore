"""Executable contract for the finish-docs implemented: stamp (phase A)."""

import subprocess
import sys
from pathlib import Path

import pytest

import grim

STAMPER = (
    Path(__file__).resolve().parents[1] / "finish-docs" / "scripts" / "stamp_spec.py"
)

BLOCK = "<!-- grim:status -->\n<!-- /grim:status -->\n"


GRIM = Path(__file__).resolve().parents[1] / "tools" / "grim.py"


def run(root, *args):
    # Fixtures do not vendor grim, so point the preflight at this repo's copy.
    return subprocess.run(
        [sys.executable, str(STAMPER), "--root", str(root), "--grim", str(GRIM), *args],
        capture_output=True,
        text=True,
    )


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def write_component(root, slug, status="current", supersedes=None):
    d = root / "docs" / "components" / "adr"
    d.mkdir(parents=True, exist_ok=True)
    edge = f"supersedes: [{', '.join(supersedes)}]\n" if supersedes else ""
    (d / f"{slug}.md").write_text(
        f"---\nid: adr-{slug}\ntype: adr\nstatus: {status}\n{edge}date: 2026-07-24\n---\n\nBody.\n",
        encoding="utf-8",
    )


def write_spec(root, name="a.md", *, raw_fm="components: []", body="# Spec\n"):
    d = root / "docs" / "specs"
    d.mkdir(parents=True, exist_ok=True)
    path = d / name
    path.write_text(f"---\n{raw_fm}\n---\n\n{BLOCK}\n{body}", encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Stamping
# --------------------------------------------------------------------------


def test_stamps_a_spec_whose_components_are_all_current(tmp_path):
    write_component(tmp_path, "x")
    spec = write_spec(tmp_path, raw_fm="components: [adr-x]")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27", "--pr", "14")
    assert r.returncode == 0, r.stderr
    assert "STAMPED" in r.stdout
    assert 'implemented: "2026-07-27 (PR #14)"' in spec.read_text(encoding="utf-8")


def test_stamp_round_trips_through_yaml_on_disk(tmp_path):
    """The whole point of the quoted form. An unquoted stamp truncates at ' #',
    and a test that only parses a string would never surface it."""
    import yaml

    write_component(tmp_path, "x")
    spec = write_spec(tmp_path, raw_fm="components: [adr-x]")
    run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27", "--pr", "14")
    text = spec.read_text(encoding="utf-8")
    fm = yaml.safe_load(text.split("---")[1])
    assert fm["implemented"] == "2026-07-27 (PR #14)"


def test_stamp_without_a_pr_number_is_just_the_date(tmp_path):
    write_component(tmp_path, "x")
    spec = write_spec(tmp_path, raw_fm="components: [adr-x]")
    run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert 'implemented: "2026-07-27"' in spec.read_text(encoding="utf-8")


def test_stamping_preserves_every_other_byte(tmp_path):
    write_component(tmp_path, "x")
    spec = write_spec(tmp_path, raw_fm="components: [adr-x]", body="# Spec\n\nProse.\n")
    before = spec.read_text(encoding="utf-8")
    run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    after = spec.read_text(encoding="utf-8")
    # count=1: an unbounded replace would still pass if the stamp were written twice
    assert after.replace('implemented: "2026-07-27"\n', "", 1) == before


def test_block_style_components_are_stamped(tmp_path):
    """Every real spec in docs/specs/ uses block style; the flow-style fixtures
    elsewhere in this file would not catch a splice that assumed one line."""
    write_component(tmp_path, "x")
    write_component(tmp_path, "y")
    spec = write_spec(tmp_path, raw_fm="components:\n  - adr-x\n  - adr-y")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 0, r.stderr
    import yaml

    fm = yaml.safe_load(spec.read_text(encoding="utf-8").split("---")[1])
    assert fm["components"] == ["adr-x", "adr-y"]
    assert fm["implemented"] == "2026-07-27"


def test_crlf_line_endings_are_preserved(tmp_path):
    write_component(tmp_path, "x")
    d = tmp_path / "docs" / "specs"
    d.mkdir(parents=True)
    spec = d / "a.md"
    spec.write_bytes(
        "---\r\ncomponents: [adr-x]\r\n---\r\n\r\n"
        "<!-- grim:status -->\r\n<!-- /grim:status -->\r\n\r\n# Spec\r\n".encode()
    )
    before = spec.read_bytes().count(b"\r\n")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 0, r.stderr
    after = spec.read_bytes()
    assert after.count(b"\r\n") == before + 1  # the stamp line, also CRLF
    assert b'implemented: "2026-07-27"\r\n---' in after


# --------------------------------------------------------------------------
# The guard that makes phase A a coherent subset rather than a fudge
# --------------------------------------------------------------------------


def test_refuses_a_spec_with_a_draft_component(tmp_path):
    """Stamping asserts the spec was implemented; nothing in phase A reconciles
    a draft against the diff, so there is nothing to justify the claim."""
    write_component(tmp_path, "built")
    write_component(tmp_path, "parked", status="draft")
    spec = write_spec(tmp_path, raw_fm="components: [adr-built, adr-parked]")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 1
    assert "REFUSED" in r.stderr and "adr-parked" in r.stderr
    assert "implemented" not in spec.read_text(encoding="utf-8")


def test_refuses_unknown_component_ids(tmp_path):
    spec = write_spec(tmp_path, raw_fm="components: [adr-ghost]")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 1
    assert "adr-ghost" in r.stderr
    assert "implemented" not in spec.read_text(encoding="utf-8")


def test_refuses_malformed_components(tmp_path):
    """Now caught by the grim preflight (E094) rather than by a duplicate check
    here, so it exits 2 as a broken store rather than 1 as a judgement call."""
    spec = write_spec(tmp_path, raw_fm="components: {a: b}")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 2
    assert "E094" in r.stderr
    assert "implemented" not in spec.read_text(encoding="utf-8")


def test_superseded_components_do_not_block_a_stamp(tmp_path):
    """A spec whose decisions have since been REPLACED was still implemented.

    The successor is load-bearing, not scenery. Status alone cannot tell a
    replacement from an abandonment - both read `superseded` - so the fixture
    has to carry the live successor that makes this a replacement.
    """
    write_component(tmp_path, "old", status="superseded")
    write_component(tmp_path, "new", status="current", supersedes=["adr-old"])
    spec = write_spec(tmp_path, raw_fm="components: [adr-old]")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 0, r.stderr
    assert "implemented" in spec.read_text(encoding="utf-8")


def test_wholly_abandoned_spec_is_refused(tmp_path):
    """Abandoning every component says the opposite of what the stamp asserts.

    Reachability is the only surviving signal: `superseded` is written both by
    "replaced" and by "never built", and the derived banner renders a bare
    "Superseded." for both. Without this, reconcile's `drop` outcome would
    launder unbuilt work into a governed "Implemented" claim.
    """
    write_component(tmp_path, "never-built", status="superseded")
    spec = write_spec(tmp_path, raw_fm="components: [adr-never-built]")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 1
    assert "abandoned with no live successor" in r.stderr
    assert "implemented" not in spec.read_text(encoding="utf-8")


def test_partially_abandoned_spec_still_stamps(tmp_path):
    """One shipped, one dropped: implemented in part, and the banner says so."""
    write_component(tmp_path, "shipped", status="current")
    write_component(tmp_path, "dropped", status="superseded")
    spec = write_spec(tmp_path, raw_fm="components: [adr-shipped, adr-dropped]")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 0, r.stderr
    assert "implemented" in spec.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Idempotency and dry run
# --------------------------------------------------------------------------


def test_already_stamped_spec_is_skipped_not_restamped(tmp_path):
    write_component(tmp_path, "x")
    spec = write_spec(
        tmp_path, raw_fm='components: [adr-x]\nimplemented: "2026-01-01"'
    )
    before = spec.read_text(encoding="utf-8")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 0
    assert "SKIP" in r.stdout
    assert spec.read_text(encoding="utf-8") == before


def test_dry_run_writes_nothing(tmp_path):
    write_component(tmp_path, "x")
    spec = write_spec(tmp_path, raw_fm="components: [adr-x]")
    before = spec.read_text(encoding="utf-8")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27", "--dry-run")
    assert r.returncode == 0
    assert "WOULD STAMP" in r.stdout
    assert spec.read_text(encoding="utf-8") == before


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


def test_branch_diff_discovers_a_changed_spec(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "T")
    write_component(tmp_path, "x")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "base")
    git(tmp_path, "checkout", "-b", "feature")
    spec = write_spec(tmp_path, raw_fm="components: [adr-x]")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "add spec")
    r = run(tmp_path, "--branch-diff", "--date", "2026-07-27", "--pr", "9")
    assert r.returncode == 0, r.stderr
    assert "STAMPED" in r.stdout
    assert 'implemented: "2026-07-27 (PR #9)"' in spec.read_text(encoding="utf-8")


def test_branch_diff_candidacy_is_decided_by_location_not_frontmatter(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "T")
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "base")
    git(tmp_path, "checkout", "-b", "feature")
    write_spec(tmp_path, raw_fm="title: no components key")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "add doc")
    r = run(tmp_path, "--branch-diff", "--date", "2026-07-27")
    # grim governs anything under the specs dir, so this script must too.
    # Pre-filtering here used to drop exactly the files classify should judge,
    # reporting "nothing to stamp" while grim reported drift on the same file.
    assert "nothing to stamp" not in r.stdout
    assert r.returncode == 0, r.stderr


# --------------------------------------------------------------------------
# Argument handling
# --------------------------------------------------------------------------


def test_bad_date_is_rejected(tmp_path):
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "last tuesday")
    assert r.returncode == 2
    assert "YYYY-MM-DD" in r.stderr


@pytest.mark.parametrize("date", ["2026-02-30", "2026-13-01", "2026-00-10"])
def test_calendar_invalid_dates_are_rejected(tmp_path, date):
    """The shape regex admits these; only the calendar check rejects them. grim
    pairs both for this reason and would report E091 on what we wrote."""
    write_component(tmp_path, "x")
    spec = write_spec(tmp_path, raw_fm="components: [adr-x]")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", date)
    assert r.returncode == 2
    assert "implemented" not in spec.read_text(encoding="utf-8")


@pytest.mark.parametrize("pr", ["abc", '1" evil: yes', "", "1\n2", "#14"])
def test_non_numeric_pr_is_rejected(tmp_path, pr):
    """--pr lands inside a double-quoted YAML scalar and is the field most
    likely to come from a CI variable. A quote in it corrupts the frontmatter."""
    write_component(tmp_path, "x")
    spec = write_spec(tmp_path, raw_fm="components: [adr-x]")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27", "--pr", pr)
    assert r.returncode == 2
    assert "implemented" not in spec.read_text(encoding="utf-8")


def test_spec_outside_the_specs_dir_is_rejected(tmp_path):
    stray = tmp_path / "stray.md"
    stray.write_text("---\ncomponents: []\n---\n\n# Stray\n", encoding="utf-8")
    r = run(tmp_path, "--spec", "stray.md", "--date", "2026-07-27")
    assert r.returncode == 2
    assert "must name a file under" in r.stderr
    assert "implemented" not in stray.read_text(encoding="utf-8")


def test_branch_diff_without_git_reports_failure(tmp_path):
    """An unresolvable merge-base must not read as 'no specs changed'. A shallow
    clone, detached HEAD, or fork without origin/<default> all land here."""
    write_component(tmp_path, "x")
    write_spec(tmp_path, raw_fm="components: [adr-x]")
    r = run(tmp_path, "--branch-diff", "--date", "2026-07-27")
    assert r.returncode == 2
    assert "merge-base" in r.stderr
    assert "nothing to stamp" not in r.stdout


def test_no_target_mode_is_rejected(tmp_path):
    r = run(tmp_path, "--date", "2026-07-27")
    assert r.returncode == 2


def test_missing_spec_path_is_rejected(tmp_path):
    r = run(tmp_path, "--spec", "docs/specs/gone.md", "--date", "2026-07-27")
    assert r.returncode == 2
    assert "no such spec" in r.stderr


# --------------------------------------------------------------------------
# The writer/deriver boundary
#
# The central claim of this change is that grim derives banners and this script
# writes the stamp, cleanly. Nothing else in the suite runs both halves against
# the same bytes - and every defect found in review was a case where the writer
# produced something the deriver rejects.
# --------------------------------------------------------------------------


def grim_findings(root):
    cfg = grim.load_config(root)
    findings, _desired = grim.analyze_working_layer(cfg, grim.load_store(cfg))
    return [f.code for f in findings]


def test_grim_accepts_what_the_stamper_writes(tmp_path):
    write_component(tmp_path, "x")
    write_spec(tmp_path, raw_fm="components: [adr-x]")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27", "--pr", "14")
    assert r.returncode == 0, r.stderr
    codes = grim_findings(tmp_path)
    assert "E091" not in codes, "grim rejects the stamp this script wrote"
    assert "E094" not in codes


def test_stamped_spec_derives_the_implemented_banner(tmp_path):
    write_component(tmp_path, "x")
    run_root = tmp_path
    write_spec(run_root, raw_fm="components: [adr-x]")
    run(run_root, "--spec", "docs/specs/a.md", "--date", "2026-07-27", "--pr", "14")
    cfg = grim.load_config(run_root)
    _findings, desired = grim.analyze_working_layer(cfg, grim.load_store(cfg))
    assert desired["docs/specs/a.md"][1] == (
        "> **Implemented 2026-07-27 (PR #14).**\n> References current.\n"
    )


def test_every_refusal_reason_is_one_grim_also_reports(tmp_path):
    """If the stamper refuses, grim should agree there is a problem - and if the
    stamper stamps, grim should find nothing wrong. Divergence in either
    direction means the two halves disagree about the same file."""
    write_component(tmp_path, "x")
    for raw_fm in ("components: no", "components: {a: b}", "components: [adr-ghost]"):
        spec = write_spec(tmp_path, raw_fm=raw_fm)
        r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
        codes = grim_findings(tmp_path)
        assert r.returncode != 0, f"stamper accepted {raw_fm!r}"
        assert any(c in codes for c in ("E094", "W092")), (
            f"stamper refused {raw_fm!r} but grim reported {codes}"
        )
        spec.unlink()


def test_stamper_refuses_a_stamp_grim_cannot_parse(tmp_path):
    """The unquoted form truncates at ' #'. Membership-only detection would call
    this 'already stamped' while grim reports E091 and refuses to derive."""
    write_component(tmp_path, "x")
    write_spec(
        tmp_path, raw_fm="components: [adr-x]\nimplemented: 2026-07-24 (PR #14)"
    )
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 2
    assert "E091" in r.stderr  # surfaced from grim rather than re-derived here
    assert "E091" in grim_findings(tmp_path)
