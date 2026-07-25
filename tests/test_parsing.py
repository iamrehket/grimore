import grim
from helpers import write_component


def parse(root, path):
    return grim.parse_component(path, root)


def test_valid_component_parses(tmp_path):
    p = write_component(tmp_path, "adr", "x")
    comp, findings = parse(tmp_path, p)
    assert findings == []
    assert comp.cid == "adr-x"
    assert comp.ctype == "adr"
    assert comp.status == "current"
    assert comp.dir_type == "adr"
    assert comp.rel == "docs/components/adr/x.md"
    assert comp.body.strip() == "Body text."
    assert comp.supersedes == []


def test_yaml_date_coerced_to_string(tmp_path):
    # PyYAML parses an unquoted ISO date as datetime.date; grim must coerce.
    p = write_component(tmp_path, "adr", "x")
    comp, _ = parse(tmp_path, p)
    assert comp.fm["date"] == "2026-07-24"
    assert isinstance(comp.fm["date"], str)


def test_missing_frontmatter_is_e001(tmp_path):
    d = tmp_path / "docs" / "components" / "adr"
    d.mkdir(parents=True)
    p = d / "x.md"
    p.write_text("just a body, no frontmatter\n", encoding="utf-8")
    comp, findings = parse(tmp_path, p)
    assert comp is None
    assert [f.code for f in findings] == ["E001"]


def test_unterminated_frontmatter_is_e001(tmp_path):
    d = tmp_path / "docs" / "components" / "adr"
    d.mkdir(parents=True)
    p = d / "x.md"
    p.write_text("---\nid: adr-x\n", encoding="utf-8")
    comp, findings = parse(tmp_path, p)
    assert comp is None
    assert [f.code for f in findings] == ["E001"]


def test_invalid_yaml_is_e002(tmp_path):
    p = write_component(tmp_path, "adr", "x", raw_fm="id: [unclosed")
    comp, findings = parse(tmp_path, p)
    assert comp is None
    assert [f.code for f in findings] == ["E002"]


def test_non_mapping_frontmatter_is_e003(tmp_path):
    p = write_component(tmp_path, "adr", "x", raw_fm="- just\n- a list")
    comp, findings = parse(tmp_path, p)
    assert comp is None
    assert [f.code for f in findings] == ["E003"]
