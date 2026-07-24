import grim
from helpers import write_component


def fix(root):
    cfg = grim.load_config(root)
    store = grim.load_store(cfg)
    findings = store.findings + grim.check_schema(store, cfg)
    return grim.apply_fixes(store, findings), store


def test_reorders_fields_canonically(tmp_path):
    p = write_component(
        tmp_path, "adr", "x",
        raw_fm="status: current\ndate: 2026-07-24\nid: adr-x\ntype: adr",
    )
    fixed, _ = fix(tmp_path)
    assert fixed == ["docs/components/adr/x.md"]
    assert p.read_text(encoding="utf-8") == (
        "---\nid: adr-x\ntype: adr\nstatus: current\ndate: 2026-07-24\n---\n\nBody text.\n"
    )


def test_block_list_normalized_to_flow(tmp_path):
    p = write_component(
        tmp_path, "adr", "new",
        raw_fm=(
            "id: adr-new\ntype: adr\nstatus: current\n"
            "supersedes:\n  - adr-old\ndate: 2026-07-24"
        ),
    )
    write_component(tmp_path, "adr", "old", status="superseded")
    fix(tmp_path)
    assert "supersedes: [adr-old]" in p.read_text(encoding="utf-8")


def test_idempotent(tmp_path):
    write_component(
        tmp_path, "adr", "x",
        raw_fm="status: current\ndate: 2026-07-24\nid: adr-x\ntype: adr",
    )
    first, _ = fix(tmp_path)
    assert first == ["docs/components/adr/x.md"]
    second, _ = fix(tmp_path)
    assert second == []


def test_already_normal_untouched(tmp_path):
    write_component(tmp_path, "adr", "x")
    fixed, _ = fix(tmp_path)
    assert fixed == []


def test_files_with_errors_are_skipped(tmp_path):
    p = write_component(tmp_path, "adr", "x", extra={"mystery": "field"})
    before = p.read_text(encoding="utf-8")
    fixed, _ = fix(tmp_path)
    assert fixed == []
    assert p.read_text(encoding="utf-8") == before  # no data loss


def test_strips_trailing_blank_lines(tmp_path):
    p = write_component(tmp_path, "adr", "x", body="Body text.\n\n\n")
    fix(tmp_path)
    assert p.read_text(encoding="utf-8").endswith("Body text.\n")


def test_ambiguous_scalar_survives_normalization(tmp_path):
    write_component(
        tmp_path, "note", "arch",
        raw_fm='status: current\ndate: 2026-07-24\nid: note-arch\ntype: note\nsubsystem: "yes"',
    )
    fixed, _ = fix(tmp_path)
    assert fixed == ["docs/components/note/arch.md"]
    cfg = grim.load_config(tmp_path)
    store = grim.load_store(cfg)
    assert store.components[0].fm["subsystem"] == "yes"
    assert grim.check_schema(store, cfg) == []


def test_comma_glob_in_paths_survives_normalization(tmp_path):
    write_component(
        tmp_path, "note", "arch",
        raw_fm='status: current\ndate: 2026-07-24\nid: note-arch\ntype: note\npaths: ["src/**/*.{js,ts}"]',
    )
    fixed, _ = fix(tmp_path)
    assert fixed == ["docs/components/note/arch.md"]
    store = grim.load_store(grim.load_config(tmp_path))
    assert store.components[0].fm["paths"] == ["src/**/*.{js,ts}"]


def test_empty_body_single_trailing_newline(tmp_path):
    write_component(
        tmp_path, "adr", "x",
        raw_fm="status: current\ndate: 2026-07-24\nid: adr-x\ntype: adr",
        body="",
    )
    fix(tmp_path)
    text = (tmp_path / "docs" / "components" / "adr" / "x.md").read_text(encoding="utf-8")
    assert text.endswith("---\n")
    assert not text.endswith("\n\n")


def test_fix_output_relints_clean(tmp_path):
    write_component(
        tmp_path, "note", "arch",
        raw_fm='status: current\ndate: 2026-07-24\nid: note-arch\ntype: note\nsubsystem: "2026-07-24"',
    )
    first = grim.run_lint(tmp_path, fix=True)
    assert first.errors == []
    second = grim.run_lint(tmp_path)
    assert second.errors == []
    assert grim.run_lint(tmp_path, fix=True).fixed == []
