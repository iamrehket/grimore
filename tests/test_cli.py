import json
import subprocess
import sys
from pathlib import Path

import grim
from helpers import write_component

GRIM = Path(grim.__file__).resolve()


def run_cli(*args, cwd):
    return subprocess.run(
        [sys.executable, str(GRIM), *args], capture_output=True, text=True, cwd=cwd
    )


def test_run_lint_aggregates_all_checks(tmp_path):
    write_component(
        tmp_path, "term", "widget",
        body="**Widget**: a thing.\n\n_Avoid_: gizmo.",
    )
    write_component(tmp_path, "note", "arch", body="The gizmo layer does X.")
    result = grim.run_lint(tmp_path)
    assert any(f.code == "E050" for f in result.errors)
    assert result.exit_code == 1


def test_run_lint_fix_reports_fixed_files(tmp_path):
    write_component(
        tmp_path, "adr", "x",
        raw_fm="status: current\ndate: 2026-07-24\nid: adr-x\ntype: adr",
    )
    result = grim.run_lint(tmp_path, fix=True)
    assert result.fixed == ["docs/components/adr/x.md"]


def test_cli_clean_store_exits_zero_with_json(tmp_path):
    write_component(tmp_path, "adr", "x")
    r = run_cli("lint", "--json", "--root", str(tmp_path), cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["ok"] is True
    assert payload["errors"] == []
    # tmp_path is not a git repo: best-effort merge-base warning expected
    assert [w["code"] for w in payload["warnings"]] == ["W042"]


def test_cli_errors_exit_one(tmp_path):
    write_component(tmp_path, "adr", "x", cid="adr-wrong")
    r = run_cli("lint", "--json", "--root", str(tmp_path), cwd=tmp_path)
    assert r.returncode == 1
    payload = json.loads(r.stdout)
    assert payload["ok"] is False
    assert any(e["code"] == "E016" for e in payload["errors"])


def test_cli_strict_promotes_merge_base_to_error(tmp_path):
    write_component(tmp_path, "adr", "x")
    r = run_cli("lint", "--strict", "--json", "--root", str(tmp_path), cwd=tmp_path)
    assert r.returncode == 1
    payload = json.loads(r.stdout)
    assert any(e["code"] == "E042" for e in payload["errors"])


def test_cli_config_error_exits_two(tmp_path):
    (tmp_path / ".grimore.toml").write_text("broken [", encoding="utf-8")
    r = run_cli("lint", "--root", str(tmp_path), cwd=tmp_path)
    assert r.returncode == 2
    assert "grim:" in r.stderr


def test_cli_human_output_has_summary(tmp_path):
    write_component(tmp_path, "adr", "x")
    r = run_cli("lint", "--root", str(tmp_path), cwd=tmp_path)
    assert r.returncode == 0
    assert "0 error(s)" in r.stdout


def test_render_verb(tmp_path, capsys):
    write_component(tmp_path, "adr", "why")
    assert grim.main(["render", "--root", str(tmp_path)]) == 0
    assert (tmp_path / "docs" / "current" / "decisions.md").exists()
    out = capsys.readouterr().out
    assert "decisions.md" in out


def test_render_verb_json(tmp_path, capsys):
    import json
    write_component(tmp_path, "adr", "why")
    assert grim.main(["render", "--json", "--root", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["written"] == ["docs/current/decisions.md"]
    assert payload["removed"] == []
