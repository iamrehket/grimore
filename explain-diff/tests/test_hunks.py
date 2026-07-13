import json
import subprocess

import pytest

from render import PayloadError, extract_hunk, resolve_hunks, write_hashes

FILE_BODY = "\n".join(f"line {n}" for n in range(1, 21)) + "\n"


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src.py").write_text(FILE_BODY)
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True, env=env)
    return tmp_path


def hunk(ref):
    return {"type": "hunk", "file": "src.py", "lines": "3-5", "ref": ref, "md": "note"}


def test_extract_from_worktree(repo):
    code, digest = extract_hunk(hunk("WORKTREE"), repo)
    assert code == "line 3\nline 4\nline 5"
    assert len(digest) == 16


def test_extract_from_ref(repo):
    (repo / "src.py").write_text("changed\n")
    code, _ = extract_hunk(hunk("HEAD"), repo)
    assert code == "line 3\nline 4\nline 5"


def test_missing_file_raises(repo):
    bad = hunk("WORKTREE") | {"file": "nope.py"}
    with pytest.raises(PayloadError, match="nope.py"):
        extract_hunk(bad, repo)


def test_out_of_range_raises(repo):
    bad = hunk("WORKTREE") | {"lines": "900-910"}
    with pytest.raises(PayloadError, match="900"):
        extract_hunk(bad, repo)


def test_reversed_or_zero_range_raises(repo):
    for bad_lines in ("5-3", "0-4"):
        bad = hunk("WORKTREE") | {"lines": bad_lines}
        with pytest.raises(PayloadError, match=bad_lines):
            extract_hunk(bad, repo)


def test_resolve_warns_on_drift(repo):
    h = hunk("WORKTREE") | {"sha256": "not-the-real-hash"}
    payload = {"sections": [h]}
    warnings = resolve_hunks(payload, repo)
    assert len(warnings) == 1 and "drift" in warnings[0]
    assert h["_code"].startswith("line 3")


def test_write_hashes_round_trip(repo, tmp_path):
    payload = {"sections": [hunk("WORKTREE")]}
    resolve_hunks(payload, repo)
    out = tmp_path / "p.json"
    write_hashes(payload, out)
    saved = json.loads(out.read_text())
    h = saved["sections"][0]
    assert h["sha256"] == payload["sections"][0]["_sha256"]
    assert not any(k.startswith("_") for k in h)
