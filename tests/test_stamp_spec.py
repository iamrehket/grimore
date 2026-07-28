"""Executable contract for the finish-docs implemented: stamp (phase A)."""

import subprocess
import sys
from pathlib import Path

STAMPER = (
    Path(__file__).resolve().parents[1] / "finish-docs" / "scripts" / "stamp_spec.py"
)

BLOCK = "<!-- grim:status -->\n<!-- /grim:status -->\n"


def run(root, *args):
    return subprocess.run(
        [sys.executable, str(STAMPER), "--root", str(root), *args],
        capture_output=True,
        text=True,
    )


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def write_component(root, slug, status="current"):
    d = root / "docs" / "components" / "adr"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{slug}.md").write_text(
        f"---\nid: adr-{slug}\ntype: adr\nstatus: {status}\ndate: 2026-07-24\n---\n\nBody.\n",
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
    assert after.replace('implemented: "2026-07-27"\n', "") == before


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
    spec = write_spec(tmp_path, raw_fm="components: {a: b}")
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "2026-07-27")
    assert r.returncode == 1
    assert "implemented" not in spec.read_text(encoding="utf-8")


def test_superseded_components_do_not_block_a_stamp(tmp_path):
    """A spec whose decisions have since been superseded was still implemented."""
    write_component(tmp_path, "old", status="superseded")
    spec = write_spec(tmp_path, raw_fm="components: [adr-old]")
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


def test_branch_diff_ignores_specs_without_components_frontmatter(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "T")
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "base")
    git(tmp_path, "checkout", "-b", "feature")
    write_spec(tmp_path, raw_fm="title: not a governed spec")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "add doc")
    r = run(tmp_path, "--branch-diff", "--date", "2026-07-27")
    assert r.returncode == 0
    assert "nothing to stamp" in r.stdout


# --------------------------------------------------------------------------
# Argument handling
# --------------------------------------------------------------------------


def test_bad_date_is_rejected(tmp_path):
    r = run(tmp_path, "--spec", "docs/specs/a.md", "--date", "last tuesday")
    assert r.returncode == 2
    assert "YYYY-MM-DD" in r.stderr


def test_no_target_mode_is_rejected(tmp_path):
    r = run(tmp_path, "--date", "2026-07-27")
    assert r.returncode == 2


def test_missing_spec_path_is_rejected(tmp_path):
    r = run(tmp_path, "--spec", "docs/specs/gone.md", "--date", "2026-07-27")
    assert r.returncode == 2
    assert "no such spec" in r.stderr
