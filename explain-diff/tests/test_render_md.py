import json
import subprocess

import pytest

from render import main, render_md


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src.py").write_text("\n".join(f"line {n}" for n in range(1, 21)) + "\n")
    return tmp_path


def full_payload():
    return {
        "title": "Retry queue",
        "verdict": "Delivery is now at-least-once",
        "mode": "warm",
        "diff": "WORKTREE",
        "sections": [
            {"type": "narrative", "heading": "What changed", "md": "Webhooks now enqueue."},
            {"type": "diagram", "heading": "Path", "mermaid": "flowchart LR\n  A --> B"},
            {"type": "decision", "id": "d1", "title": "At-least-once", "provenance": "stated",
             "reversal_cost": "high", "md": "Dedup on receiver.", "alternatives": ["exactly-once"]},
            {"type": "hunk", "file": "src.py", "lines": "3-5", "ref": "WORKTREE", "md": "The lease query."},
            {"type": "comparison", "heading": "Send path", "before_md": "inline send", "after_md": "outbox worker"},
            {"type": "question", "id": "q1", "md": "Cap retries at 24h?"},
            {"type": "fallout", "items": ["renamed sender.py", "import shuffles"]},
        ],
    }


def test_render_md_structure(repo):
    payload = full_payload()
    from render import resolve_hunks
    resolve_hunks(payload, repo)
    md = render_md(payload)
    assert md.startswith("# Retry queue")
    assert "> Delivery is now at-least-once" in md
    assert "```mermaid" in md
    assert "line 3" in md and "src.py:3-5 @ WORKTREE" in md
    assert "- [ ] **q1**: Cap retries at 24h?" in md
    assert "reversal cost: high" in md and "stated" in md
    assert "Approve" not in md  # no composer in markdown target


def test_cli_md_end_to_end(repo, tmp_path, capsys):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps(full_payload()))
    out = tmp_path / "guide.md"
    rc = main([str(p), "--format", "md", "--repo", str(repo), "--out", str(out)])
    assert rc == 0
    assert out.read_text().startswith("# Retry queue")


def test_cli_invalid_payload_fails_loudly(tmp_path, capsys):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps({"title": "x"}))
    rc = main([str(p), "--format", "md"])
    assert rc == 1
    assert "error:" in capsys.readouterr().err


def test_cli_write_hashes(repo, tmp_path):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps(full_payload()))
    rc = main([str(p), "--format", "md", "--repo", str(repo), "--out", str(tmp_path / "g.md"), "--write-hashes"])
    assert rc == 0
    assert json.loads(p.read_text())["sections"][3]["sha256"]
