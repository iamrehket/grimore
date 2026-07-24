import grim
from helpers import write_component


def schema_findings(root):
    cfg = grim.load_config(root)
    store = grim.load_store(cfg)
    return store.findings + grim.check_schema(store, cfg)


def codes(findings):
    return [f.code for f in findings]


def test_clean_component_no_findings(tmp_path):
    write_component(tmp_path, "note", "arch", extra={"subsystem": "store", "paths": "[src/]"})
    assert schema_findings(tmp_path) == []


def test_missing_components_dir_is_empty_store(tmp_path):
    assert schema_findings(tmp_path) == []


def test_file_at_store_root_is_e004(tmp_path):
    d = tmp_path / "docs" / "components"
    d.mkdir(parents=True)
    (d / "stray.md").write_text("---\nid: x\n---\n\nb\n", encoding="utf-8")
    assert codes(schema_findings(tmp_path)) == ["E004"]


def test_unknown_type_directory_is_e005(tmp_path):
    d = tmp_path / "docs" / "components" / "widget"
    d.mkdir(parents=True)
    (d / "x.md").write_text("---\nid: x\n---\n\nb\n", encoding="utf-8")
    assert codes(schema_findings(tmp_path)) == ["E005"]


def test_missing_required_fields_is_e010(tmp_path):
    write_component(tmp_path, "adr", "x", raw_fm="id: adr-x\ntype: adr")
    assert codes(schema_findings(tmp_path)) == ["E010"]


def test_unknown_field_is_e011(tmp_path):
    write_component(tmp_path, "adr", "x", extra={"superseds": "adr-y"})
    assert "E011" in codes(schema_findings(tmp_path))


def test_bad_type_value_is_e012(tmp_path):
    write_component(
        tmp_path, "adr", "x",
        raw_fm="id: adr-x\ntype: widget\nstatus: current\ndate: 2026-07-24",
    )
    found = codes(schema_findings(tmp_path))
    assert "E012" in found


def test_type_dir_mismatch_is_e013(tmp_path):
    write_component(
        tmp_path, "adr", "x",
        raw_fm="id: term-x\ntype: term\nstatus: current\ndate: 2026-07-24",
    )
    assert "E013" in codes(schema_findings(tmp_path))


def test_bad_status_is_e014(tmp_path):
    write_component(tmp_path, "adr", "x", status="live")
    assert "E014" in codes(schema_findings(tmp_path))


def test_bad_slug_is_e015(tmp_path):
    write_component(tmp_path, "adr", "Bad_Slug", cid="adr-Bad_Slug")
    assert "E015" in codes(schema_findings(tmp_path))


def test_id_filename_mismatch_is_e016(tmp_path):
    write_component(tmp_path, "adr", "x", cid="adr-other")
    assert "E016" in codes(schema_findings(tmp_path))


def test_invalid_calendar_date_is_e017(tmp_path):
    write_component(tmp_path, "adr", "x", date='"2026-13-40"')
    assert "E017" in codes(schema_findings(tmp_path))


def test_non_date_string_is_e017(tmp_path):
    write_component(tmp_path, "adr", "x", date="soon")
    assert "E017" in codes(schema_findings(tmp_path))


def test_paths_on_term_is_e018(tmp_path):
    write_component(tmp_path, "term", "x", extra={"paths": "[src/]"})
    assert "E018" in codes(schema_findings(tmp_path))


def test_scalar_supersedes_is_e019(tmp_path):
    write_component(tmp_path, "adr", "x", extra={"supersedes": "adr-old"})
    assert "E019" in codes(schema_findings(tmp_path))


def test_subsystem_on_adr_is_w061(tmp_path):
    write_component(tmp_path, "adr", "x", extra={"subsystem": "store"})
    findings = schema_findings(tmp_path)
    assert codes(findings) == ["W061"]
    assert findings[0].level == "warning"
