import pytest

from render import PayloadError, check_mermaid, highlight_code, md_to_html


def test_known_mermaid_type_passes():
    check_mermaid("flowchart LR\n  A --> B")
    check_mermaid("\n  sequenceDiagram\n  A->>B: hi")
    check_mermaid("gitGraph\n  commit")


def test_unknown_mermaid_type_rejected():
    with pytest.raises(PayloadError, match="diagram type"):
        check_mermaid("banana LR\n  A --> B")


def test_empty_mermaid_rejected():
    with pytest.raises(PayloadError):
        check_mermaid("   \n  ")


def test_prefix_collision_rejected():
    with pytest.raises(PayloadError, match="diagram type"):
        check_mermaid("graphite\n  A --> B")


def test_state_diagram_v2_passes():
    check_mermaid("stateDiagram-v2\n  [*] --> A")


def test_md_to_html_renders_emphasis_and_code():
    html = md_to_html("uses `outbox` and **must** dedup")
    assert "<code>outbox</code>" in html and "<strong>must</strong>" in html


def test_highlight_python():
    html = highlight_code("def f():\n    return 1", "src/thing.py")
    assert 'class="highlight"' in html and "def" in html


def test_highlight_unknown_extension_falls_back():
    html = highlight_code("plain text", "notes.xyzzy")
    assert 'class="highlight"' in html
