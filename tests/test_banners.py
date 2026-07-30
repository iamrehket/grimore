import os
import subprocess

import pytest

import grim
from helpers import banner_interior, write_component, write_plan, write_spec


def analyze(root):
    cfg = grim.load_config(root)
    return grim.analyze_working_layer(cfg, grim.load_store(cfg))


def codes(root):
    findings, _ = analyze(root)
    return sorted(f.code for f in findings)


def derived(root, rel="docs/specs/a.md"):
    """The interior grim wants for rel.

    Fixtures write an empty block, which always differs from a derived one
    (adr-never-empty-banner), so every doc appears in the desired map.
    """
    _, desired = analyze(root)
    assert rel in desired, f"{rel} not among {sorted(desired)}"
    return desired[rel][1]


def fix(root):
    findings, desired = analyze(root)
    return grim.apply_banner_fixes(desired, findings)


def git(root, *args):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def make_repo(root):
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")


# --------------------------------------------------------------------------
# Stamp parsing. The unquoted form is the one the template and the design
# spec both showed, and it truncates at the YAML comment marker.
# --------------------------------------------------------------------------


def test_quoted_stamp_parses_whole():
    assert grim.parse_implemented("2026-07-24 (PR #14)") == ("2026-07-24", "14")


def test_bare_date_object_is_coerced():
    import datetime

    assert grim.parse_implemented(datetime.date(2026, 7, 24)) == ("2026-07-24", None)


@pytest.mark.parametrize(
    "value",
    [
        "2026-07-24 (PR",  # what an unquoted stamp actually becomes
        "last tuesday",
        "2026-13-99",
        "20260724",
        20260724,
        True,
        None,
        ["2026-07-24"],
    ],
)
def test_malformed_stamps_are_rejected(value):
    with pytest.raises(ValueError):
        grim.parse_implemented(value)


def test_datetime_is_rejected_not_silently_truncated():
    import datetime

    with pytest.raises(ValueError):
        grim.parse_implemented(datetime.datetime(2026, 7, 24, 10, 0))


def test_unquoted_stamp_on_disk_is_e091(tmp_path):
    """Regression for the format the template shipped. Must round-trip through
    a real file: parsing the string directly would never surface it."""
    write_spec(tmp_path, raw_fm="components: []\nimplemented: 2026-07-24 (PR #14)")
    assert "E091" in codes(tmp_path)


def test_quoted_stamp_on_disk_round_trips(tmp_path):
    write_spec(tmp_path, raw_fm='components: []\nimplemented: "2026-07-24 (PR #14)"')
    assert derived(tmp_path).startswith("> **Implemented 2026-07-24 (PR #14).**")


# --------------------------------------------------------------------------
# Banner states
# --------------------------------------------------------------------------


def test_unstamped_spec_says_not_yet_implemented(tmp_path):
    write_component(tmp_path, "adr", "x")
    write_spec(tmp_path, raw_fm="components: [adr-x]")
    assert derived(tmp_path) == "> **Not yet implemented.**\n"


def test_stamped_all_current(tmp_path):
    write_component(tmp_path, "adr", "x")
    write_spec(tmp_path, raw_fm='components: [adr-x]\nimplemented: "2026-07-24"')
    assert derived(tmp_path) == "> **Implemented 2026-07-24.**\n> References current.\n"


def test_stamped_with_a_draft_component(tmp_path):
    """The reconciliation pass explicitly parks unbuilt components as draft, so
    this state is reachable and must not fall through to silence."""
    write_component(tmp_path, "adr", "built")
    write_component(tmp_path, "adr", "parked", status="draft")
    write_spec(tmp_path, raw_fm='components: [adr-built, adr-parked]\nimplemented: "2026-07-24"')
    assert derived(tmp_path) == (
        "> **Implemented 2026-07-24.**\n> Not fully realized: adr-parked still draft.\n"
    )


def test_empty_component_list_is_stated_not_vacuous(tmp_path):
    write_spec(tmp_path, raw_fm='components: []\nimplemented: "2026-07-24"')
    assert derived(tmp_path) == (
        "> **Implemented 2026-07-24.**\n> References no components.\n"
    )


def test_partial_supersede_names_the_successor(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "new", extra={"supersedes": "[adr-old]"})
    write_component(tmp_path, "adr", "kept")
    write_spec(tmp_path, raw_fm='components: [adr-old, adr-kept]\nimplemented: "2026-07-24"')
    assert derived(tmp_path) == (
        "> **Implemented 2026-07-24.**\n> Superseded in part: adr-old -> adr-new\n"
    )


def test_all_superseded_collapses_to_one_word(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "new", extra={"supersedes": "[adr-old]"})
    write_spec(tmp_path, raw_fm='components: [adr-old]\nimplemented: "2026-07-24"')
    assert derived(tmp_path) == "> **Implemented 2026-07-24.**\n> Superseded.\n"


def test_superseded_with_no_successor_is_abandoned(tmp_path):
    write_component(tmp_path, "adr", "dead", status="superseded")
    write_component(tmp_path, "adr", "kept")
    write_spec(tmp_path, raw_fm='components: [adr-dead, adr-kept]\nimplemented: "2026-07-24"')
    assert "adr-dead -> abandoned" in derived(tmp_path)


def test_unknown_component_id_is_reported(tmp_path):
    write_spec(tmp_path, raw_fm="components: [adr-ghost]")
    assert "W092" in codes(tmp_path)
    assert "Unknown references: adr-ghost." in derived(tmp_path)


def test_components_not_a_list_of_strings_is_a_blocking_error(tmp_path):
    """Must be an error, not a warning. Derivation is skipped for this file, so
    no E090 can fire; a warning would let grim check pass over a stale or empty
    banner - the exact hole the feature exists to close."""
    write_spec(tmp_path, raw_fm="components: {a: b}")
    findings, desired = analyze(tmp_path)
    assert [f.code for f in findings if f.level == "error"] == ["E094"]
    assert desired == {}


def test_banner_is_never_empty(tmp_path):
    """The rule the whole feature rests on: emptiness must never be valid
    output, because it cannot be told apart from a tool that never ran."""
    write_spec(tmp_path, "bare.md", raw_fm="components: []")
    write_spec(tmp_path, "ghost.md", raw_fm="components: [adr-nope]")
    _, desired = analyze(tmp_path)
    assert desired
    for _rel, (_path, interior) in desired.items():
        assert interior.strip()


# --------------------------------------------------------------------------
# Supersede chains
# --------------------------------------------------------------------------


def test_chained_supersede_resolves_past_the_intermediate(tmp_path):
    """a <- b <- c with b since superseded. The existing live-successor map
    keys only when the successor is current, so a naive reuse reports the
    decision abandoned while a live successor sits two hops away."""
    write_component(tmp_path, "adr", "a", status="superseded")
    write_component(tmp_path, "adr", "b", status="superseded", extra={"supersedes": "[adr-a]"})
    write_component(tmp_path, "adr", "c", extra={"supersedes": "[adr-b]"})
    write_component(tmp_path, "adr", "kept")
    write_spec(tmp_path, raw_fm='components: [adr-a, adr-kept]\nimplemented: "2026-07-24"')
    assert "adr-a -> adr-c" in derived(tmp_path)
    assert "abandoned" not in derived(tmp_path)


def test_supersede_cycle_terminates(tmp_path):
    """Two mutually-superseding components pass check_edges, which rejects only
    self-supersede and missing targets. Without a visited set this loops."""
    write_component(tmp_path, "adr", "x", status="superseded", extra={"supersedes": "[adr-y]"})
    write_component(tmp_path, "adr", "y", status="superseded", extra={"supersedes": "[adr-x]"})
    write_component(tmp_path, "adr", "seed", status="superseded", extra={"supersedes": "[adr-x]"})
    write_component(tmp_path, "adr", "kept")
    write_spec(tmp_path, raw_fm='components: [adr-seed, adr-kept]\nimplemented: "2026-07-24"')
    assert "adr-seed -> abandoned" in derived(tmp_path)


def test_forked_chain_names_every_live_successor(tmp_path):
    """A fork reaching two current endpoints does not trip E031, which inspects
    only immediate successors. Returning the first match would state one as
    authoritative and silently drop the other."""
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "b", status="superseded", extra={"supersedes": "[adr-old]"})
    write_component(tmp_path, "adr", "c", status="superseded", extra={"supersedes": "[adr-old]"})
    write_component(tmp_path, "adr", "alpha", extra={"supersedes": "[adr-b]"})
    write_component(tmp_path, "adr", "omega", extra={"supersedes": "[adr-c]"})
    write_component(tmp_path, "adr", "kept")
    write_spec(tmp_path, raw_fm='components: [adr-old, adr-kept]\nimplemented: "2026-07-24"')
    cfg = grim.load_config(tmp_path)
    assert grim.check_edges(grim.load_store(cfg)) == []  # E031 does not see it
    assert "adr-old -> adr-alpha or adr-omega" in derived(tmp_path)


def test_successor_choice_is_deterministic_under_reordering(tmp_path):
    write_component(tmp_path, "adr", "zzz", status="superseded")
    write_component(tmp_path, "adr", "aaa", status="superseded")
    write_component(tmp_path, "adr", "mid", extra={"supersedes": "[adr-zzz, adr-aaa]"})
    write_component(tmp_path, "adr", "kept")
    write_spec(tmp_path, raw_fm='components: [adr-zzz, adr-aaa, adr-kept]\nimplemented: "2026-07-24"')
    first = derived(tmp_path)
    assert "adr-aaa -> adr-mid, adr-zzz -> adr-mid" in first
    # declaration order in components: must not change the rendered order
    write_spec(tmp_path, raw_fm='components: [adr-kept, adr-aaa, adr-zzz]\nimplemented: "2026-07-24"')
    assert derived(tmp_path) == first


# --------------------------------------------------------------------------
# Plans
# --------------------------------------------------------------------------


def test_plan_inherits_its_spec_banner(tmp_path):
    write_component(tmp_path, "adr", "x")
    write_spec(tmp_path, raw_fm='components: [adr-x]\nimplemented: "2026-07-24"')
    write_plan(tmp_path, raw_fm="spec: docs/specs/a.md")
    assert derived(tmp_path, "docs/plans/a.md") == derived(tmp_path)


def test_plan_carrying_a_stamp_is_e092(tmp_path):
    write_plan(tmp_path, raw_fm='spec: docs/specs/a.md\nimplemented: "2026-07-24"')
    assert "E092" in codes(tmp_path)


def test_plan_with_unresolvable_spec_still_gets_a_block(tmp_path):
    write_plan(tmp_path, raw_fm="spec: docs/specs/gone.md")
    assert derived(tmp_path, "docs/plans/a.md").strip()
    assert "W093" in codes(tmp_path)


def test_plan_spec_escaping_the_root_is_not_read(tmp_path):
    write_plan(tmp_path, raw_fm="spec: ../../../etc/passwd")
    assert "W093" in codes(tmp_path)


# --------------------------------------------------------------------------
# The write path
# --------------------------------------------------------------------------


def test_fix_writes_only_between_the_delimiters(tmp_path):
    write_component(tmp_path, "adr", "x")
    p = write_spec(tmp_path, raw_fm="components: [adr-x]", body="# Spec\n\nProse stays.\n")
    before = p.read_text(encoding="utf-8")
    assert fix(tmp_path) == ["docs/specs/a.md"]
    after = p.read_text(encoding="utf-8")
    assert banner_interior(p) == "> **Not yet implemented.**\n"
    # everything outside the delimiters is byte-identical
    head, _, rest = before.partition(grim.BANNER_OPEN)
    assert after.startswith(head + grim.BANNER_OPEN)
    assert after.endswith(rest.split(grim.BANNER_CLOSE, 1)[1])


def test_fix_is_idempotent(tmp_path):
    write_component(tmp_path, "adr", "x")
    p = write_spec(tmp_path, raw_fm="components: [adr-x]")
    fix(tmp_path)
    once = p.read_text(encoding="utf-8")
    assert fix(tmp_path) == []
    assert p.read_text(encoding="utf-8") == once


def test_fix_converges_from_a_mangled_block(tmp_path):
    write_component(tmp_path, "adr", "x")
    p = write_spec(tmp_path, raw_fm="components: [adr-x]", interior="> hand-written nonsense\n")
    fix(tmp_path)
    assert banner_interior(p) == "> **Not yet implemented.**\n"


def test_missing_block_warns_and_is_never_inserted(tmp_path):
    """grim writes only between the delimiters; a spec without them is a human
    decision, not drift."""
    write_component(tmp_path, "adr", "x")
    p = write_spec(tmp_path, raw_fm="components: [adr-x]", interior=None)
    before = p.read_text(encoding="utf-8")
    assert "W090" in codes(tmp_path)
    fix(tmp_path)
    assert p.read_text(encoding="utf-8") == before


def test_crlf_bytes_outside_the_block_are_preserved(tmp_path):
    """read_text/write_text normalizes CRLF to LF and would rewrite the whole
    file, changing frozen bytes. Asserted on raw bytes, since text-mode reads
    hide the very translation under test."""
    write_component(tmp_path, "adr", "x")
    d = tmp_path / "docs" / "specs"
    d.mkdir(parents=True)
    p = d / "a.md"
    p.write_bytes(
        "---\r\ncomponents: [adr-x]\r\n---\r\n\r\n"
        f"{grim.BANNER_OPEN}\r\n{grim.BANNER_CLOSE}\r\n\r\n# Spec\r\n\r\nProse.\r\n".encode()
    )
    before = p.read_bytes()
    assert fix(tmp_path) == ["docs/specs/a.md"]
    after = p.read_bytes()
    tail_before = before.split(grim.BANNER_CLOSE.encode(), 1)[1]
    tail_after = after.split(grim.BANNER_CLOSE.encode(), 1)[1]
    assert tail_after == tail_before
    assert after.split(grim.BANNER_OPEN.encode(), 1)[0] == before.split(
        grim.BANNER_OPEN.encode(), 1
    )[0]


def test_plan_missing_block_is_w091(tmp_path):
    write_plan(tmp_path, raw_fm="spec: docs/specs/a.md", interior=None)
    assert "W091" in codes(tmp_path)


def test_drift_alone_does_not_block_its_own_repair(tmp_path):
    """apply_fixes skips any file carrying an error; reusing that rule here
    would make --fix a no-op on exactly the files E090 names."""
    write_component(tmp_path, "adr", "x")
    write_spec(tmp_path, raw_fm="components: [adr-x]")
    assert fix(tmp_path) == ["docs/specs/a.md"]


def test_bad_stamp_blocks_the_write(tmp_path):
    write_spec(tmp_path, raw_fm="components: []\nimplemented: nonsense")
    assert fix(tmp_path) == []


def test_broken_graph_blocks_every_write(tmp_path):
    """Two live successors of one target is an unreconciled graph; summarizing
    it into a frozen document would bake in the wrong answer."""
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "b", extra={"supersedes": "[adr-old]"})
    write_component(tmp_path, "adr", "c", extra={"supersedes": "[adr-old]"})
    write_spec(tmp_path, raw_fm='components: [adr-old]\nimplemented: "2026-07-24"')
    cfg = grim.load_config(tmp_path)
    store = grim.load_store(cfg)
    findings, desired = grim.analyze_working_layer(cfg, store)
    findings += grim.check_edges(store)
    assert any(f.code == "E031" for f in findings)
    assert grim.apply_banner_fixes(desired, findings) == []


def test_symlinked_spec_is_refused(tmp_path):
    write_component(tmp_path, "adr", "x")
    real = tmp_path / "real.md"
    real.write_text(
        f"---\ncomponents: [adr-x]\n---\n\n{grim.BANNER_OPEN}\n{grim.BANNER_CLOSE}\n\n# S\n",
        encoding="utf-8",
    )
    d = tmp_path / "docs" / "specs"
    d.mkdir(parents=True)
    os.symlink(real, d / "a.md")
    with pytest.raises(grim.ConfigError):
        fix(tmp_path)


# --------------------------------------------------------------------------
# Exit codes and the CI gate
# --------------------------------------------------------------------------


def test_fixing_run_exits_zero_when_drift_was_the_only_error(tmp_path):
    """Findings are computed once and exit_code derives from that list, so a
    repaired E090 left in place would break `lint --fix && render`."""
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x")
    write_spec(tmp_path, raw_fm="components: [adr-x]")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "seed")
    result = grim.run_lint(tmp_path, fix=True)
    assert "docs/specs/a.md" in result.fixed
    assert [f.code for f in result.errors] == []
    assert result.exit_code == 0


def test_lint_without_fix_reports_drift_as_an_error(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x")
    write_spec(tmp_path, raw_fm="components: [adr-x]")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "seed")
    result = grim.run_lint(tmp_path, fix=False)
    assert "E090" in [f.code for f in result.errors]
    assert result.exit_code == 1


def test_check_fails_on_a_stale_banner(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x")
    write_spec(tmp_path, raw_fm="components: [adr-x]")
    grim.run_lint(tmp_path, fix=True)
    grim.main(["render", "--root", str(tmp_path)])
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-m", "seed")
    assert grim.run_check(tmp_path).exit_code == 0
    spec = tmp_path / "docs" / "specs" / "a.md"
    spec.write_text(
        spec.read_text(encoding="utf-8").replace(
            "> **Not yet implemented.**", "> **Implemented yesterday.**"
        ),
        encoding="utf-8",
    )
    assert grim.run_check(tmp_path).exit_code == 1


def test_abandoned_references_needs_no_live_successor(tmp_path):
    status = {"adr-gone": "superseded", "adr-live": "current"}
    # Replaced: a live successor exists, so it was implemented and then moved on.
    assert grim.abandoned_references(["adr-gone"], status, {"adr-gone": ["adr-live"]}) == []
    # Abandoned: nothing live replaces it.
    assert grim.abandoned_references(["adr-gone"], status, {}) == ["adr-gone"]
    # Current and draft references are not abandonment either way.
    assert grim.abandoned_references(["adr-live"], status, {}) == []


def test_stamped_spec_with_only_abandoned_components_is_e095(tmp_path):
    # The laundering path: reconcile writes `superseded` for work never built,
    # a superseded component does not block a stamp, and the banner renders a
    # bare "Superseded." either way - so nothing downstream said no.
    write_component(tmp_path, "adr", "never-built", status="superseded")
    write_spec(
        tmp_path, "s.md",
        raw_fm='components: [adr-never-built]\nimplemented: "2026-07-24 (PR #1)"',
    )
    findings, _ = grim.analyze_working_layer(
        grim.load_config(tmp_path), grim.load_store(grim.load_config(tmp_path))
    )
    assert "E095" in [f.code for f in findings]


def test_stamped_spec_with_a_replaced_component_is_clean(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "new", status="current", extra={"supersedes": "[adr-old]"})
    write_spec(
        tmp_path, "s.md",
        raw_fm='components: [adr-old]\nimplemented: "2026-07-24 (PR #1)"',
    )
    cfg = grim.load_config(tmp_path)
    findings, _ = grim.analyze_working_layer(cfg, grim.load_store(cfg))
    assert "E095" not in [f.code for f in findings]


def test_unstamped_spec_with_abandoned_components_is_clean(tmp_path):
    # Abandoning without claiming implementation is honest; only the stamp lies.
    write_component(tmp_path, "adr", "never-built", status="superseded")
    write_spec(tmp_path, "s.md", raw_fm="components: [adr-never-built]")
    cfg = grim.load_config(tmp_path)
    findings, _ = grim.analyze_working_layer(cfg, grim.load_store(cfg))
    assert "E095" not in [f.code for f in findings]


def test_partially_abandoned_stamped_spec_is_clean(tmp_path):
    # One component shipped, one was dropped: the spec was implemented in part,
    # and the banner already reports the discrepancy. Only "nothing was built"
    # contradicts the stamp outright.
    write_component(tmp_path, "adr", "shipped", status="current")
    write_component(tmp_path, "adr", "dropped", status="superseded")
    write_spec(
        tmp_path, "s.md",
        raw_fm='components: [adr-shipped, adr-dropped]\nimplemented: "2026-07-24 (PR #1)"',
    )
    cfg = grim.load_config(tmp_path)
    findings, _ = grim.analyze_working_layer(cfg, grim.load_store(cfg))
    assert "E095" not in [f.code for f in findings]
