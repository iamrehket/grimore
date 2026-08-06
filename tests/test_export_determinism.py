"""Determinism of the two human exports.

`grim render --digest` and `grim render --bundle` are declared byte-identical
across regeneration from the same declared inputs, and blind to everything
else - wall-clock time, machine timezone, filesystem enumeration order, and
locale (constraint-deterministic-human-exports). Each test below advances
exactly one of those four dimensions and nothing else, then byte-compares.

Two dimensions need active effort here, not passive absence, per the traps
named alongside this task in docs/plans/2026-08-01-human-exports.md (Task 8):

- Filesystem order: rebuilding the same files in a different creation order
  often yields the *same* directory enumeration on a modern filesystem, so a
  test that only reorders creation calls can vary nothing and pass
  vacuously. The tests below monkeypatch the directory walk itself and
  assert, separately from the output comparison, that the raw enumeration it
  fed grim genuinely differed between the two runs.
- Locale: Python's string comparison is code-point order and never consults
  the C locale, so this dimension is expected to pass trivially once grim's
  sorts are byte-ordered (which Task 5 commits the id ordering to be). That
  expected triviality is not a reason to fake the exercise - the locale
  tests spawn the real CLI in a subprocess with LC_ALL/LANG actually set to
  two different installed locales, rather than asserting something that
  could never fail.

What this suite cannot cover: a digest that reads a commit's date in the
wrong basis (local time instead of UTC) is *stable* across every axis
exercised here, so every run below would keep passing even with that defect.
Only the UTC-boundary fixture in tests/test_digest_boundary.py exercises
that; this file does not cover it.
"""

import os
import pathlib
import subprocess
import sys
import time
from pathlib import Path

import pytest

import grim
from helpers import write_spec
from history_fixture import History

GRIM = Path(grim.__file__).resolve()

# Captured once, at import time, before any test has a chance to monkeypatch
# Path.rglob - the fs-order tests below reuse this as the one true
# enumeration, regardless of how many times they re-patch rglob in the same
# test.
_REAL_RGLOB = pathlib.Path.rglob


def bundle_text(root):
    cfg = grim.load_config(root)
    return grim.render_bundle(cfg, grim.load_store(cfg))


def digest_text(root, **kw):
    return grim.render_digest(grim.digest(grim.load_config(root), **kw))


def run_cli(*args, cwd, env=None):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, str(GRIM), *args],
        capture_output=True, text=True, cwd=cwd, env=full_env,
    )


def bundle_fixture(root):
    """Several live components spanning types, so an enumeration order has
    something in it to disturb."""
    h = History(root)
    h.write("adr", "alpha", status="current", date="2026-05-01", body="Alpha decided.")
    h.write("adr", "bravo", status="current", date="2026-05-02", body="Bravo decided.")
    h.write("term", "widget", status="current", date="2026-05-03", body="A widget is.")
    h.write(
        "note", "sub", status="current", date="2026-05-04", body="A note.",
        extra={"subsystem": "render"},
    )
    h.commit("baseline", when="2026-05-04T12:00:00+0000")
    return h


def digest_fixture(root):
    """Several landings and two specs claiming overlapping components, so
    both the event walk and the provenance index have something in them."""
    h = History(root)
    write_spec(
        h.root, "2026-05-01-first.md",
        raw_fm="components:\n  - adr-alpha\n  - adr-bravo",
    )
    write_spec(h.root, "2026-05-02-second.md", raw_fm="components:\n  - adr-bravo")
    h.write("adr", "alpha", status="current")
    h.write("adr", "bravo", status="current")
    h.write("adr", "charlie", status="current")
    h.commit("first landing", when="2026-05-01T12:00:00+0000")
    h.write("adr", "delta", status="current")
    h.commit("second landing", when="2026-05-02T12:00:00+0000")
    return h


# -- wall clock ---------------------------------------------------------


def test_bundle_regenerated_after_the_wall_clock_visibly_advances_is_byte_identical(tmp_path):
    # grim currently reads no clock at all in the bundle path; this is the
    # test that would catch a datetime.now()/time.time() call creeping in.
    h = bundle_fixture(tmp_path)
    first = bundle_text(h.root)

    before = time.time()
    time.sleep(1.05)
    after = time.time()
    # A repeat inside the same instant proves nothing about the clock being
    # excluded - it only proves the code path is fast. Demand a real gap.
    assert after - before >= 1.0, "the clock must genuinely advance between runs"

    assert bundle_text(h.root) == first


def test_digest_regenerated_after_the_wall_clock_visibly_advances_is_byte_identical(tmp_path):
    h = digest_fixture(tmp_path)
    first = digest_text(h.root)

    before = time.time()
    time.sleep(1.05)
    after = time.time()
    assert after - before >= 1.0, "the clock must genuinely advance between runs"

    assert digest_text(h.root) == first


# -- machine timezone -----------------------------------------------------

# Kiritimati carries no DST and sits at the far edge of the calendar
# (UTC+14); Los Angeles is UTC-7 or -8 depending on the season. Whichever
# season this runs in, the two are never the same offset, so the identity
# check below is safe year-round.
TZ_A = "Pacific/Kiritimati"
TZ_B = "America/Los_Angeles"


def _utc_offset(tz):
    r = subprocess.run(
        ["date", "+%z"], env={**os.environ, "TZ": tz}, capture_output=True, text=True
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_bundle_is_identical_under_two_genuinely_different_machine_timezones(tmp_path):
    # Proof the two TZ names actually take effect on this machine, not just
    # that the env var held two different strings - an unrecognized zoneinfo
    # name falls back silently and would make this pass for the wrong reason.
    assert _utc_offset(TZ_A) != _utc_offset(TZ_B), "the chosen zones must actually differ here"

    h = bundle_fixture(tmp_path)
    a = run_cli("render", "--bundle", "--root", str(h.root), cwd=h.root, env={"TZ": TZ_A})
    b = run_cli("render", "--bundle", "--root", str(h.root), cwd=h.root, env={"TZ": TZ_B})

    assert a.returncode == 0, a.stderr
    assert b.returncode == 0, b.stderr
    assert a.stdout == b.stdout


def test_digest_is_identical_under_two_genuinely_different_machine_timezones(tmp_path):
    assert _utc_offset(TZ_A) != _utc_offset(TZ_B), "the chosen zones must actually differ here"

    h = digest_fixture(tmp_path)
    a = run_cli("render", "--digest", "--root", str(h.root), cwd=h.root, env={"TZ": TZ_A})
    b = run_cli("render", "--digest", "--root", str(h.root), cwd=h.root, env={"TZ": TZ_B})

    assert a.returncode == 0, a.stderr
    assert b.returncode == 0, b.stderr
    assert a.stdout == b.stdout


# -- filesystem enumeration order ------------------------------------------


def _install_reordering_rglob(monkeypatch, order_fn, captured):
    """Monkeypatch Path.rglob("*.md") to hand back matches in `order_fn`'s
    order, and record the raw sequence it fed the caller.

    grim always re-sorts what rglob hands it (tools/grim.py:261 for the
    component store, :1307 for specs/plans), so reordering here proves
    nothing about *output* by itself - only that the *input* enumeration
    genuinely varied between the two calls. `captured` is how the test below
    checks that, rather than trusting that a monkeypatch "did something."
    """

    def fake(self, pattern, *a, **kw):
        matches = list(_REAL_RGLOB(self, pattern, *a, **kw))
        if pattern == "*.md":
            matches = order_fn(matches)
            captured.append(tuple(str(p) for p in matches))
        return iter(matches)

    monkeypatch.setattr(pathlib.Path, "rglob", fake)


def test_bundle_is_identical_when_the_component_store_is_enumerated_in_a_different_order(
    tmp_path, monkeypatch
):
    h = bundle_fixture(tmp_path)
    captured = []

    _install_reordering_rglob(monkeypatch, lambda m: sorted(m), captured)
    first = bundle_text(h.root)

    _install_reordering_rglob(monkeypatch, lambda m: list(reversed(sorted(m))), captured)
    second = bundle_text(h.root)

    # The trap named in Task 8: creating the same files in a different order
    # often produces the *same* directory enumeration, so a genuine
    # difference in what grim actually received must be checked directly
    # rather than assumed from how the fixture was built.
    assert captured[0] != captured[1], "the two runs must feed grim genuinely different raw order"
    assert len(captured[0]) > 1, "need more than one file for an order to mean anything"

    assert first == second


def test_digest_is_identical_when_the_claiming_specs_are_enumerated_in_a_different_order(
    tmp_path, monkeypatch
):
    # The digest's event data comes from git plumbing (commit trees), not a
    # live directory walk, so filesystem order cannot reach it there. The one
    # filesystem enumeration the digest performs is the specs/plans walk
    # that builds the provenance index - this is what "store enumerated in a
    # different filesystem order" actually means for this export.
    h = digest_fixture(tmp_path)
    captured = []

    _install_reordering_rglob(monkeypatch, lambda m: sorted(m), captured)
    first = digest_text(h.root)

    _install_reordering_rglob(monkeypatch, lambda m: list(reversed(sorted(m))), captured)
    second = digest_text(h.root)

    assert captured[0] != captured[1], "the two runs must feed grim genuinely different raw order"
    assert len(captured[0]) > 1, "need more than one file for an order to mean anything"

    assert first == second


# -- locale -----------------------------------------------------------------


def _installed_locales():
    r = subprocess.run(["locale", "-a"], capture_output=True, text=True)
    if r.returncode != 0:
        return set()
    return {line.strip() for line in r.stdout.splitlines() if line.strip()}


def _pick_two_locales():
    """Two installed locales likely to disagree on collation/case-folding.

    Picked at run time rather than hardcoded, since which locales are
    generated is a property of the machine or CI image, not of this test -
    hardcoding one that is not installed would make LC_ALL a no-op and the
    test would pass without ever exercising a changed locale.
    """
    installed = _installed_locales()
    candidates = ["de_DE.UTF-8", "en_US.UTF-8", "C.UTF-8", "POSIX", "C"]
    found = [c for c in candidates if c in installed]
    return tuple(found[:2]) if len(found) >= 2 else None


_LOCALES = _pick_two_locales()
_SKIP_LOCALE = "fewer than two locales installed here to prove a genuine variation"


@pytest.mark.skipif(_LOCALES is None, reason=_SKIP_LOCALE)
def test_bundle_is_identical_under_two_different_locales(tmp_path):
    h = bundle_fixture(tmp_path)
    loc_a, loc_b = _LOCALES
    a = run_cli(
        "render", "--bundle", "--root", str(h.root), cwd=h.root,
        env={"LC_ALL": loc_a, "LANG": loc_a},
    )
    b = run_cli(
        "render", "--bundle", "--root", str(h.root), cwd=h.root,
        env={"LC_ALL": loc_b, "LANG": loc_b},
    )

    assert a.returncode == 0, a.stderr
    assert b.returncode == 0, b.stderr
    assert a.stdout == b.stdout


@pytest.mark.skipif(_LOCALES is None, reason=_SKIP_LOCALE)
def test_digest_is_identical_under_two_different_locales(tmp_path):
    h = digest_fixture(tmp_path)
    loc_a, loc_b = _LOCALES
    a = run_cli(
        "render", "--digest", "--root", str(h.root), cwd=h.root,
        env={"LC_ALL": loc_a, "LANG": loc_a},
    )
    b = run_cli(
        "render", "--digest", "--root", str(h.root), cwd=h.root,
        env={"LC_ALL": loc_b, "LANG": loc_b},
    )

    assert a.returncode == 0, a.stderr
    assert b.returncode == 0, b.stderr
    assert a.stdout == b.stdout
