import subprocess

import grim
from helpers import write_component


def git(root, *args):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def make_repo(root):
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")


def commit_all(root, msg):
    # Broad add is fine here: throwaway fixture repo under tmp_path.
    git(root, "add", "-A")
    git(root, "commit", "-m", msg)


def fresh_repo(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "why", body="# Why\n\nProse.")
    grim.main(["render", "--root", str(tmp_path)])
    commit_all(tmp_path, "store + render")


def test_check_passes_on_fresh_render(tmp_path):
    fresh_repo(tmp_path)
    result = grim.run_check(tmp_path)
    assert result.mismatches == [] and result.exit_code == 0


def test_check_fails_on_stale_committed_render(tmp_path):
    fresh_repo(tmp_path)
    write_component(tmp_path, "adr", "why", body="# Why\n\nChanged.")
    result = grim.run_check(tmp_path)
    assert [f.code for f in result.mismatches] == ["E080"]
    assert result.exit_code == 1


def test_check_fails_on_renderer_change_without_component_edits(tmp_path, monkeypatch):
    # Spec requirement: a renderer/config change with no component edits fails.
    # Monkeypatch render_store to emit different bytes for the same store -
    # exactly what a code or config change does.
    fresh_repo(tmp_path)
    real = grim.render_store
    monkeypatch.setattr(grim, "render_store", lambda store: {
        name: content + "renderer v2 output\n" for name, content in real(store).items()
    })
    result = grim.run_check(tmp_path)
    assert [f.code for f in result.mismatches] == ["E080"]


def test_check_survives_non_utf8_file_in_current(tmp_path):
    # Byte comparison, not text: a binary stray must be an E080, not a crash.
    fresh_repo(tmp_path)
    (tmp_path / "docs" / "current" / "binary.md").write_bytes(b"\xff\xfe")
    result = grim.run_check(tmp_path)
    assert [f.code for f in result.mismatches] == ["E080"]


def test_check_fails_on_stray_file_in_current(tmp_path):
    fresh_repo(tmp_path)
    (tmp_path / "docs" / "current" / "extra.md").write_text("stray\n")
    result = grim.run_check(tmp_path)
    assert [f.code for f in result.mismatches] == ["E080"]
    assert "stale" in result.mismatches[0].message


def test_check_is_fail_closed_without_merge_base(tmp_path):
    # No git repo at all: strict lint must produce E042, and check must fail.
    write_component(tmp_path, "adr", "why")
    result = grim.run_check(tmp_path)
    assert "E042" in [f.code for f in result.lint.errors]
    assert result.exit_code == 1


def test_check_verb_json(tmp_path, capsys):
    import json
    fresh_repo(tmp_path)
    capsys.readouterr()  # discard setup output: fresh_repo ran the render verb
    assert grim.main(["check", "--json", "--root", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["mismatches"] == []
