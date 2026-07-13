import re
import subprocess

import pytest

from render import render_html, resolve_hunks
from test_render_md import full_payload


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src.py").write_text("\n".join(f"line {n}" for n in range(1, 21)) + "\n")
    return tmp_path


@pytest.fixture
def fake_mermaid(monkeypatch, tmp_path):
    js = tmp_path / "mermaid.min.js"
    js.write_text("/* fake mermaid runtime */")
    import render
    monkeypatch.setattr(render, "MERMAID_PATH", js)
    return js


def rendered(repo):
    payload = full_payload()
    resolve_hunks(payload, repo)
    return render_html(payload)


def test_no_placeholders_left(repo, fake_mermaid):
    html = rendered(repo)
    assert not re.search(r"\{\{[A-Z_]+\}\}", html)


def test_self_contained(repo, fake_mermaid):
    html = rendered(repo)
    assert "http://" not in html and "https://" not in html


def test_core_content_present(repo, fake_mermaid):
    html = rendered(repo)
    text = re.sub(r"<[^>]+>", "", html)
    assert "Retry queue" in html and "at-least-once" in html.lower()
    assert 'id="d1"' in html and 'id="q1"' in html
    assert "line 3" in text                      # extracted hunk code, as rendered text
    assert "fake mermaid runtime" in html        # inlined because diagram present
    assert 'data-links=' in html                 # diagram interactivity hooks
    assert "Copy as prompt" in html              # composer
    assert "Approve" in html and "Discuss" in html and "Change" in html


def test_mermaid_omitted_without_diagrams(repo, fake_mermaid):
    payload = full_payload()
    payload["sections"] = [s for s in payload["sections"] if s["type"] != "diagram"]
    resolve_hunks(payload, repo)
    html = render_html(payload)
    assert "fake mermaid runtime" not in html


def test_no_emojis(repo, fake_mermaid):
    html = rendered(repo)
    assert not any(0x1F300 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF for c in html)
