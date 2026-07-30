import grim
from helpers import write_component


def load(root):
    return grim.load_store(grim.load_config(root))


def codes(findings):
    return [f.code for f in findings]


def test_duplicate_id_is_e020(tmp_path):
    # Same id declared in two files of different types.
    write_component(tmp_path, "adr", "x")
    write_component(
        tmp_path, "term", "y",
        raw_fm="id: adr-x\ntype: term\nstatus: current\ndate: 2026-07-24",
    )
    store = load(tmp_path)
    assert codes(grim.check_ids(store)) == ["E020"]


def test_unique_ids_are_clean(tmp_path):
    write_component(tmp_path, "adr", "x")
    write_component(tmp_path, "adr", "y")
    assert grim.check_ids(load(tmp_path)) == []


def test_missing_supersede_target_is_e030(tmp_path):
    write_component(tmp_path, "adr", "new", extra={"supersedes": "[adr-ghost]"})
    assert codes(grim.check_edges(load(tmp_path))) == ["E030"]


def test_self_supersede_is_e030(tmp_path):
    write_component(tmp_path, "adr", "x", extra={"supersedes": "[adr-x]"})
    assert codes(grim.check_edges(load(tmp_path))) == ["E030"]


def test_valid_edge_is_clean(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "new", extra={"supersedes": "[adr-old]"})
    assert grim.check_edges(load(tmp_path)) == []


def test_dual_live_successor_is_e031(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "left", status="current", extra={"supersedes": "[adr-old]"})
    write_component(tmp_path, "adr", "right", status="current", extra={"supersedes": "[adr-old]"})
    findings = grim.check_edges(load(tmp_path))
    assert codes(findings) == ["E031"]
    assert "adr-left" in findings[0].message and "adr-right" in findings[0].message


def test_draft_successor_does_not_count_as_live(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "left", status="current", extra={"supersedes": "[adr-old]"})
    write_component(tmp_path, "adr", "right", status="draft", extra={"supersedes": "[adr-old]"})
    assert grim.check_edges(load(tmp_path)) == []


def test_successor_without_id_does_not_crash(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "a", status="current", extra={"supersedes": "[adr-old]"})
    write_component(
        tmp_path, "adr", "noid",
        raw_fm="type: adr\nstatus: current\nsupersedes: [adr-old]\ndate: 2026-07-24",
    )
    assert grim.check_edges(load(tmp_path)) == []


def test_uncascaded_promotion_is_e032(tmp_path):
    # SCHEMA: the edge takes effect at promotion, when the target flips to
    # superseded in the same pass. Before E032 this lint-ed and check-ed clean
    # while rendering both decisions into the consumer view as live.
    write_component(tmp_path, "adr", "old", status="current")
    write_component(tmp_path, "adr", "new", status="current", extra={"supersedes": "[adr-old]"})
    findings = grim.check_edges(load(tmp_path))
    assert codes(findings) == ["E032"]
    assert findings[0].component == "adr-old"
    # Reported against the file that must change, matching E031's convention.
    assert findings[0].path.endswith("old.md")


def test_draft_successor_does_not_trip_e032(tmp_path):
    # The normal pre-promotion state: the edge is authored on the draft and
    # takes effect later. Flagging it would fire on every unfinished branch.
    write_component(tmp_path, "adr", "old", status="current")
    write_component(tmp_path, "adr", "new", status="draft", extra={"supersedes": "[adr-old]"})
    assert grim.check_edges(load(tmp_path)) == []


def test_cascaded_promotion_is_clean(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "new", status="current", extra={"supersedes": "[adr-old]"})
    assert grim.check_edges(load(tmp_path)) == []


def test_e032_blocks_banner_derivation(tmp_path):
    # The banner is not merely uninformative in this state, it is wrong: it
    # renders "References current." about a component the store says was
    # replaced. Writing that into a frozen spec bakes the error in.
    from helpers import write_spec

    write_component(tmp_path, "adr", "old", status="current")
    write_component(tmp_path, "adr", "new", status="current", extra={"supersedes": "[adr-old]"})
    write_spec(
        tmp_path, "s.md",
        raw_fm='components: [adr-old]\nimplemented: "2026-07-24 (PR #1)"',
    )
    result = grim.run_lint(tmp_path, fix=True)
    assert "E032" in codes(result.findings)
    assert result.fixed == []


def test_duplicate_supersede_entry_is_not_two_live_successors(tmp_path):
    # A repeated target is idempotent, not a fork. Counting occurrences made
    # E031 report "'adr-old' has 2 live successors (adr-new, adr-new)".
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(
        tmp_path, "adr", "new", status="current",
        extra={"supersedes": "[adr-old, adr-old]"},
    )
    assert grim.check_edges(load(tmp_path)) == []
