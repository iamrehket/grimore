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
