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
