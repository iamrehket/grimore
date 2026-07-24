import shutil
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


def transitions(root, strict=False):
    cfg = grim.load_config(root)
    store = grim.load_store(cfg)
    return grim.check_transitions(store, cfg, strict)


def codes(findings):
    return [f.code for f in findings]


def test_promotion_is_legal(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x", status="draft")
    commit_all(tmp_path, "add draft")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(tmp_path, "adr", "x", status="current")
    assert transitions(tmp_path) == []


def test_abandonment_is_legal(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x", status="draft")
    commit_all(tmp_path, "add draft")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(tmp_path, "adr", "x", status="superseded")
    assert transitions(tmp_path) == []


def test_resurrection_is_e040(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x", status="superseded")
    commit_all(tmp_path, "add superseded")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(tmp_path, "adr", "x", status="current")
    findings = transitions(tmp_path)
    assert codes(findings) == ["E040"]
    assert "'superseded' -> 'current'" in findings[0].message


def test_demotion_is_e040(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x", status="current")
    commit_all(tmp_path, "add current")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(tmp_path, "adr", "x", status="draft")
    assert codes(transitions(tmp_path)) == ["E040"]


def test_deletion_is_e041(tmp_path):
    make_repo(tmp_path)
    p = write_component(tmp_path, "adr", "x")
    commit_all(tmp_path, "add component")
    git(tmp_path, "checkout", "-b", "feature")
    p.unlink()
    assert codes(transitions(tmp_path)) == ["E041"]


def test_new_component_any_status_legal(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(tmp_path, "adr", "born-current", status="current")
    write_component(tmp_path, "adr", "born-draft", status="draft")
    assert transitions(tmp_path) == []


def test_no_repo_best_effort_is_w042(tmp_path):
    write_component(tmp_path, "adr", "x")
    findings = transitions(tmp_path, strict=False)
    assert codes(findings) == ["W042"]
    assert findings[0].level == "warning"


def test_no_repo_strict_is_e042(tmp_path):
    write_component(tmp_path, "adr", "x")
    findings = transitions(tmp_path, strict=True)
    assert codes(findings) == ["E042"]
    assert findings[0].level == "error"


def test_empty_store_skips_git_entirely(tmp_path):
    assert transitions(tmp_path, strict=True) == []


def test_broken_but_present_component_is_not_deleted(tmp_path):
    make_repo(tmp_path)
    d = tmp_path / "docs" / "components" / "adr"
    d.mkdir(parents=True)
    (d / "broken.md").write_text("---\nstatus: [unterminated\n", encoding="utf-8")
    commit_all(tmp_path, "add broken component")
    assert transitions(tmp_path) == []


def test_project_root_below_git_root(tmp_path):
    make_repo(tmp_path)
    project = tmp_path / "sub"
    write_component(project, "adr", "x", status="current")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(project, "adr", "x", status="draft")
    assert codes(transitions(project)) == ["E040"]


def test_wholesale_store_deletion_is_e041(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x")
    write_component(tmp_path, "adr", "y")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    shutil.rmtree(tmp_path / "docs" / "components")
    findings = transitions(tmp_path, strict=True)
    assert codes(findings) == ["E041", "E041"]
    assert findings[0].path == "docs/components/adr/x.md"
