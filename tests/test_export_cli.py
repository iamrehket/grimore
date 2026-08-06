"""The export flag surface on `grim render`.

Both exports print to standard output and neither touches the tree, so
selecting one makes a command that looks read-only actually read-only.
"""

import subprocess
import sys
from pathlib import Path

import grim
from history_fixture import History

GRIM = Path(grim.__file__).resolve()


def run_cli(*args, cwd):
    return subprocess.run(
        [sys.executable, str(GRIM), *args], capture_output=True, text=True, cwd=cwd
    )


def snapshot(root):
    current = root / "docs" / "current"
    if not current.is_dir():
        return {}
    return {p.name: p.read_bytes() for p in sorted(current.glob("*.md"))}


def seeded(tmp_path):
    h = History(tmp_path)
    h.write("adr", "alpha", status="current", date="2026-05-01", body="Alpha decided.")
    h.write("term", "widget", status="current", date="2026-05-02", body="A widget is.")
    h.commit("baseline", when="2026-05-02T12:00:00+0000")
    return h


# -- the happy paths --------------------------------------------------------


def test_digest_prints_to_stdout(tmp_path):
    h = seeded(tmp_path)
    r = run_cli("render", "--digest", "--since", "2026-05-01", "--root", str(h.root), cwd=h.root)

    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("# Catch-up digest")
    assert "adr-alpha" in r.stdout


def test_bundle_prints_to_stdout(tmp_path):
    h = seeded(tmp_path)
    r = run_cli("render", "--bundle", "--root", str(h.root), cwd=h.root)

    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("# Component bundle")
    assert "Alpha decided." in r.stdout


def test_digest_without_since_covers_everything(tmp_path):
    h = seeded(tmp_path)
    r = run_cli("render", "--digest", "--root", str(h.root), cwd=h.root)

    assert r.returncode == 0, r.stderr
    assert "All landings" in r.stdout


# -- the export writes nothing ---------------------------------------------


def test_an_export_does_not_touch_the_rendered_view(tmp_path):
    # Asserted by byte-comparing what is on disk, not by checking that some
    # function went uncalled - the second passes if a later refactor moves the
    # write somewhere else.
    h = seeded(tmp_path)
    assert run_cli("render", "--root", str(h.root), cwd=h.root).returncode == 0
    before = snapshot(h.root)
    assert before, "the plain render should have written something to compare against"

    for flags in (["--digest"], ["--bundle"]):
        r = run_cli("render", *flags, "--root", str(h.root), cwd=h.root)
        assert r.returncode == 0, r.stderr
        assert snapshot(h.root) == before


def test_an_export_writes_nothing_even_when_the_view_is_stale(tmp_path):
    # The sharper case: a store change that a plain render would write out.
    h = seeded(tmp_path)
    assert run_cli("render", "--root", str(h.root), cwd=h.root).returncode == 0
    before = snapshot(h.root)
    h.write("adr", "bravo", status="current", date="2026-05-03", body="Bravo decided.")

    r = run_cli("render", "--bundle", "--root", str(h.root), cwd=h.root)
    assert r.returncode == 0, r.stderr
    assert "Bravo decided." in r.stdout, "the export must reflect the live store"
    assert snapshot(h.root) == before, "but must not write it out"


def test_a_bare_render_still_writes(tmp_path):
    h = seeded(tmp_path)
    r = run_cli("render", "--root", str(h.root), cwd=h.root)

    assert r.returncode == 0, r.stderr
    assert "RENDERED" in r.stdout
    assert snapshot(h.root)


# -- refusals, never silent no-ops -----------------------------------------


def test_the_two_export_flags_are_mutually_exclusive(tmp_path):
    h = seeded(tmp_path)
    r = run_cli("render", "--digest", "--bundle", "--root", str(h.root), cwd=h.root)

    assert r.returncode != 0
    assert r.stdout == ""


def test_since_without_digest_is_an_error(tmp_path):
    h = seeded(tmp_path)
    r = run_cli("render", "--since", "2026-05-01", "--root", str(h.root), cwd=h.root)

    assert r.returncode != 0
    assert r.stdout == ""
    assert "--digest" in r.stderr


def test_a_malformed_since_is_an_error(tmp_path):
    h = seeded(tmp_path)
    r = run_cli("render", "--digest", "--since", "last tuesday", "--root", str(h.root), cwd=h.root)

    assert r.returncode != 0
    assert r.stdout == ""


def test_json_does_not_apply_to_an_export(tmp_path):
    # An export prints its own format. Accepting --json and ignoring it would
    # be the silent no-op this surface refuses everywhere else.
    h = seeded(tmp_path)
    r = run_cli("render", "--digest", "--json", "--root", str(h.root), cwd=h.root)

    assert r.returncode != 0
    assert r.stdout == ""
