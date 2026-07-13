import re
from pathlib import Path

from render import SKILL_DIR, main

EXAMPLE = SKILL_DIR / "examples" / "payload.example.json"


def test_example_renders_self_contained_html(tmp_path):
    out = tmp_path / "guide.html"
    rc = main([str(EXAMPLE), "--repo", str(SKILL_DIR), "--out", str(out)])
    assert rc == 0
    html = out.read_text()
    # No external-fetch vectors. Plain "https://" strings inside the vendored
    # mermaid bundle are fine; what matters is nothing is loaded from the network.
    for vector in ("<script src=", "<link ", "url(http", "@import url"):
        assert vector not in html, f"external-fetch vector found: {vector}"
    assert not re.search(r"\{\{[A-Z_]+\}\}", html)
    assert "Copy as prompt" in html
    assert "mermaid" in html.lower()


def test_example_renders_markdown(tmp_path):
    out = tmp_path / "guide.md"
    rc = main([str(EXAMPLE), "--format", "md", "--repo", str(SKILL_DIR), "--out", str(out)])
    assert rc == 0
    assert out.read_text().startswith("# Example: retry queue")
