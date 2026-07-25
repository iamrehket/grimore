import grim
from helpers import write_component

TERM_BODY = "**Component**: one documentation idea in one file.\n\n_Avoid_: fragment, doclet, entry."


def findings_for(root):
    store = grim.load_store(grim.load_config(root))
    return grim.check_avoid_terms(store)


def codes(findings):
    return [f.code for f in findings]


def test_avoided_term_in_body_is_e050(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    write_component(tmp_path, "note", "arch", body="Each doclet holds one idea.")
    findings = findings_for(tmp_path)
    assert codes(findings) == ["E050"]
    assert "doclet" in findings[0].message
    assert "term-component" in findings[0].message


def test_match_is_case_insensitive(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    write_component(tmp_path, "note", "arch", body="A Fragment of the docs.")
    assert codes(findings_for(tmp_path)) == ["E050"]


def test_word_boundary_no_substring_match(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    write_component(tmp_path, "note", "arch", body="Defragmentation and entryway are fine.")
    assert findings_for(tmp_path) == []


def test_escape_marker_exempts_line(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    write_component(
        tmp_path, "note", "arch",
        body="The old system called these entry records. <!-- grim:ok -->",
    )
    assert findings_for(tmp_path) == []


def test_own_avoid_line_not_flagged(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    assert findings_for(tmp_path) == []


def test_draft_term_does_not_govern(tmp_path):
    write_component(tmp_path, "term", "component", status="draft", body=TERM_BODY)
    write_component(tmp_path, "note", "arch", body="Each doclet holds one idea.")
    assert findings_for(tmp_path) == []


def test_superseded_bodies_not_scanned(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    write_component(
        tmp_path, "note", "arch", status="superseded", body="Each doclet holds one idea."
    )
    assert findings_for(tmp_path) == []


def test_multiword_term_matches_as_phrase(tmp_path):
    write_component(
        tmp_path, "term", "store",
        body="**Store**: the component tree.\n\n_Avoid_: data lake.",
    )
    write_component(tmp_path, "note", "arch", body="Dump it in the data lake.")
    findings = findings_for(tmp_path)
    assert codes(findings) == ["E050"]
