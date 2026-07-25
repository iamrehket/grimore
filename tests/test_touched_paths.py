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


def base_of(root):
    return git(root, "merge-base", "HEAD", "main").strip()


def test_collect_waivers_parses_trailers(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "a.txt").write_text("a")
    commit_all(tmp_path, "init")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "b.txt").write_text("b")
    commit_all(tmp_path, "change\n\nGrim-Waive: note-renderer just a comment tweak")
    (tmp_path / "c.txt").write_text("c")
    commit_all(
        tmp_path,
        "more\n\nGrim-Waive: note-renderer second reason\nGrim-Waive: adr-render-hash separate id",
    )
    cfg = grim.load_config(tmp_path)
    waivers = grim.collect_waivers(cfg, base_of(tmp_path))
    assert waivers == {
        "note-renderer": ["just a comment tweak", "second reason"],
        "adr-render-hash": ["separate id"],
    }


def test_collect_waivers_ignores_base_side_and_malformed(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "a.txt").write_text("a")
    commit_all(tmp_path, "init\n\nGrim-Waive: note-old on the base, out of range")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "b.txt").write_text("b")
    commit_all(tmp_path, "change\n\nGrim-Waive:\nGrim-Waive: lone-id-no-reason")
    cfg = grim.load_config(tmp_path)
    assert grim.collect_waivers(cfg, base_of(tmp_path)) == {}


def test_body_mention_outside_trailer_block_is_not_a_waiver(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "a.txt").write_text("a")
    commit_all(tmp_path, "init")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "b.txt").write_text("b")
    # The line starts exactly with "Grim-Waive:" but sits in a NON-final
    # paragraph, so it is not part of the git trailer block. A naive
    # multiline ^Grim-Waive: regex would match it (this test must fail such
    # an implementation); git trailer parsing must not.
    commit_all(
        tmp_path,
        "docs: explain waivers\n\n"
        "Grim-Waive: note-renderer some reason\n"
        "is the trailer format reviewers use to bypass the guard.\n\n"
        "This final paragraph makes the paragraph above body prose, not trailers.",
    )
    cfg = grim.load_config(tmp_path)
    assert grim.collect_waivers(cfg, base_of(tmp_path)) == {}


def lint_codes(root, strict=False):
    result = grim.run_lint(root, strict=strict)
    return [f.code for f in result.findings]


def guarded_repo(tmp_path):
    """main: a note declaring paths: [src/render/] plus src/render/x.py; then a feature branch."""
    make_repo(tmp_path)
    write_component(
        tmp_path, "note", "renderer",
        extra={"subsystem": "renderer", "paths": "[src/render/]"},
    )
    src = tmp_path / "src" / "render"
    src.mkdir(parents=True)
    (src / "x.py").write_text("x = 1\n")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    return src


def test_hit_without_component_change_is_e070(tmp_path):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak renderer")
    # Exact list: this fixture produces no unrelated findings.
    assert lint_codes(tmp_path) == ["E070"]
    [finding] = [f for f in grim.run_lint(tmp_path).findings if f.code == "E070"]
    assert "Grim-Waive: note-renderer" in finding.message  # tells the operator the exact trailer


def test_hit_with_component_change_is_clean(tmp_path):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    write_component(
        tmp_path, "note", "renderer", body="Updated fact.",
        extra={"subsystem": "renderer", "paths": "[src/render/]"},
    )
    commit_all(tmp_path, "tweak renderer and its note")
    assert "E070" not in lint_codes(tmp_path)


def test_hit_with_waiver_is_w071_echo(tmp_path):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak\n\nGrim-Waive: note-renderer comment-only change")
    # Exact list: this fixture produces no unrelated findings.
    assert lint_codes(tmp_path) == ["W071"]
    [finding] = [f for f in grim.run_lint(tmp_path).findings if f.code == "W071"]
    assert "comment-only change" in finding.message  # reason echoed for reviewers


def test_waiver_for_other_component_does_not_apply(tmp_path):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak\n\nGrim-Waive: note-other wrong id")
    assert "E070" in lint_codes(tmp_path)


def test_draft_component_does_not_gate(tmp_path):
    # A fresh repo whose gating note is draft from the start: flipping an
    # existing current component to draft would itself be an illegal
    # transition (E040), which would pollute this test's assertion.
    make_repo(tmp_path)
    write_component(tmp_path, "note", "renderer", status="draft", extra={"paths": "[src/render/]"})
    src = tmp_path / "src" / "render"
    src.mkdir(parents=True)
    (src / "x.py").write_text("x = 1\n")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak")
    assert "E070" not in lint_codes(tmp_path)


def test_uncommitted_working_tree_changes_count(tmp_path):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")  # not committed
    assert "E070" in lint_codes(tmp_path)


def test_fnmatch_glob_without_trailing_slash(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "render-hash", extra={"paths": "[src/*.py]"})
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("m = 1\n")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "src" / "m.py").write_text("m = 2\n")
    commit_all(tmp_path, "tweak")
    assert "E070" in lint_codes(tmp_path)


def test_paths_on_non_gating_type_never_fires_guard(tmp_path):
    # A usecase with paths: is an E018 schema error; the guard itself must
    # not also fire on it (only current note/adr gate).
    make_repo(tmp_path)
    write_component(tmp_path, "usecase", "u", extra={"paths": "[src/]"})
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("m = 1\n")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "src" / "m.py").write_text("m = 2\n")
    commit_all(tmp_path, "tweak")
    codes = lint_codes(tmp_path)
    assert "E018" in codes and "E070" not in codes


def test_e070_fails_grim_check(tmp_path):
    # Integration: an unwaived hit must fail the CI entry point end to end.
    src = guarded_repo(tmp_path)
    grim.main(["render", "--root", str(tmp_path)])  # store is clean pre-hit
    commit_all(tmp_path, "commit rendered view")
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak renderer without touching the note")
    result = grim.run_check(tmp_path)
    assert "E070" in [f.code for f in result.lint.errors]
    assert result.exit_code == 1


def test_no_merge_base_skips_guard_with_single_warning(tmp_path):
    # No commits at all: resolve_merge_base already emits one W042; the guard
    # must not add another finding.
    write_component(tmp_path, "note", "renderer", extra={"paths": "[src/]"})
    result = grim.run_lint(tmp_path)
    assert [f.code for f in result.findings] == ["W042"]


def _failing_diff_git(real_git):
    def wrapper(cfg, *args):
        r = real_git(cfg, *args)
        if args and args[0] == "diff":
            r.returncode = 128
        return r
    return wrapper


def test_diff_failure_fails_closed_in_strict(tmp_path, monkeypatch):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak")
    monkeypatch.setattr(grim, "_git", _failing_diff_git(grim._git))
    result = grim.run_lint(tmp_path, strict=True)
    codes = [f.code for f in result.findings]
    assert "E072" in codes and "E070" not in codes  # failed closed, not silently green


def test_diff_failure_warns_locally(tmp_path, monkeypatch):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak")
    monkeypatch.setattr(grim, "_git", _failing_diff_git(grim._git))
    result = grim.run_lint(tmp_path, strict=False)
    codes = [f.code for f in result.findings]
    assert "W072" in codes and "E070" not in codes and "E072" not in codes
