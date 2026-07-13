import json

import pytest

from render import PayloadError, load_payload


def minimal_payload() -> dict:
    return {
        "title": "T",
        "verdict": "V",
        "mode": "warm",
        "diff": "WORKTREE",
        "sections": [{"type": "narrative", "heading": "H", "md": "body"}],
    }


def write(tmp_path, payload):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps(payload))
    return p


def test_valid_minimal_payload_loads(tmp_path):
    payload = load_payload(write(tmp_path, minimal_payload()))
    assert payload["title"] == "T"


def test_missing_verdict_rejected(tmp_path):
    bad = minimal_payload()
    del bad["verdict"]
    with pytest.raises(PayloadError, match="verdict"):
        load_payload(write(tmp_path, bad))


def test_duplicate_ids_rejected(tmp_path):
    bad = minimal_payload()
    bad["sections"] += [
        {"type": "question", "id": "q1", "md": "a?"},
        {"type": "question", "id": "q1", "md": "b?"},
    ]
    with pytest.raises(PayloadError, match="duplicate"):
        load_payload(write(tmp_path, bad))


def test_dangling_diagram_link_rejected(tmp_path):
    bad = minimal_payload()
    bad["sections"].append(
        {"type": "diagram", "heading": "D", "mermaid": "flowchart LR\n  A --> B",
         "links": {"A": "#nope"}}
    )
    with pytest.raises(PayloadError, match="nope"):
        load_payload(write(tmp_path, bad))


def test_unknown_section_type_rejected(tmp_path):
    bad = minimal_payload()
    bad["sections"].append({"type": "sparkles", "md": "x"})
    with pytest.raises(PayloadError, match="section types"):
        load_payload(write(tmp_path, bad))


def test_missing_payload_file_rejected(tmp_path):
    with pytest.raises(PayloadError, match="nope.json"):
        load_payload(tmp_path / "nope.json")
