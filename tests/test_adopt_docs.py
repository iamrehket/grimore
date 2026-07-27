"""Executable contract for adopt-docs provenance resolution."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

RESOLVER = (
    Path(__file__).resolve().parents[1]
    / "adopt-docs"
    / "scripts"
    / "resolve_provenance.py"
)


def git(root, *args):
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def init_repo(root):
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")


def commit_all(root, message="fixture"):
    git(root, "add", "-A")
    git(root, "commit", "--allow-empty", "-m", message)
    return git(root, "rev-parse", "HEAD")


def write_manifest(
    source_root,
    host="claude",
    *,
    name="grimore",
    version="0.2.0",
    extra=None,
):
    path = source_root / f".{host}-plugin" / "plugin.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"name": name, "version": version}
    if extra:
        data.update(extra)
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    return path


def make_bundle(root, *, claude=True, codex=False):
    skill_dir = root / "adopt-docs"
    skill_dir.mkdir(parents=True, exist_ok=True)
    if claude:
        write_manifest(root, "claude")
    if codex:
        write_manifest(root, "codex")
    return skill_dir


def run_resolver(skill_dir, target, *extra_args):
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(RESOLVER),
            "--skill-dir",
            str(skill_dir),
            "--target",
            str(target),
            *extra_args,
        ],
        capture_output=True,
        text=True,
    )


def assert_identity(result, expected, *, warning=False):
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"{expected}\n"
    assert len(result.stdout.splitlines()) == 1
    if warning:
        assert result.stderr.startswith("warning:")
    else:
        assert result.stderr == ""


def test_standalone_grimore_git_source_returns_its_commit(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    init_repo(source)
    skill_dir = make_bundle(source)
    source_commit = commit_all(source)
    init_repo(target)
    target_commit = commit_all(target)

    result = run_resolver(skill_dir, target)

    assert source_commit != target_commit
    assert_identity(result, source_commit)


def test_gitless_bundle_nested_in_target_never_returns_target_commit(tmp_path):
    target = tmp_path / "target"
    init_repo(target)
    skill_dir = make_bundle(target / "vendor" / "grimore")
    target_commit = commit_all(target)

    result = run_resolver(skill_dir, target)

    assert result.stdout.strip() != target_commit
    assert_identity(result, "grimore plugin v0.2.0")


def test_legacy_claude_only_bundle_returns_authoritative_version(tmp_path):
    target = tmp_path / "target"
    init_repo(target)
    commit_all(target)
    skill_dir = make_bundle(tmp_path / "bundle")

    assert_identity(
        run_resolver(skill_dir, target),
        "grimore plugin v0.2.0",
    )


def test_matching_dual_manifests_return_authoritative_version(tmp_path):
    target = tmp_path / "target"
    init_repo(target)
    commit_all(target)
    skill_dir = make_bundle(tmp_path / "bundle", codex=True)

    assert_identity(
        run_resolver(skill_dir, target),
        "grimore plugin v0.2.0",
    )


def test_extra_codex_fields_do_not_affect_the_identity(tmp_path):
    target = tmp_path / "target"
    init_repo(target)
    commit_all(target)
    source = tmp_path / "bundle"
    skill_dir = make_bundle(source)
    write_manifest(
        source,
        "codex",
        extra={"displayName": "Grimore", "keywords": ["docs"]},
    )

    assert_identity(
        run_resolver(skill_dir, target),
        "grimore plugin v0.2.0",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "not-grimore"),
        ("version", "9.9.9"),
    ],
)
def test_dual_manifest_mismatch_warns_and_returns_unknown(tmp_path, field, value):
    target = tmp_path / "target"
    init_repo(target)
    commit_all(target)
    source = tmp_path / "bundle"
    skill_dir = make_bundle(source, codex=True)
    codex = json.loads(
        (source / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    codex[field] = value
    (source / ".codex-plugin" / "plugin.json").write_text(
        json.dumps(codex) + "\n",
        encoding="utf-8",
    )

    assert_identity(run_resolver(skill_dir, target), "unknown", warning=True)


@pytest.mark.parametrize("host", ["claude", "codex"])
def test_malformed_json_warns_and_returns_unknown(tmp_path, host):
    target = tmp_path / "target"
    init_repo(target)
    commit_all(target)
    source = tmp_path / "bundle"
    skill_dir = make_bundle(source, codex=True)
    (source / f".{host}-plugin" / "plugin.json").write_text(
        "{",
        encoding="utf-8",
    )

    result = run_resolver(skill_dir, target)

    assert f".{host}-plugin/plugin.json" in result.stderr
    assert_identity(result, "unknown", warning=True)


def test_missing_authoritative_manifest_warns_and_returns_unknown(tmp_path):
    target = tmp_path / "target"
    init_repo(target)
    commit_all(target)
    skill_dir = make_bundle(tmp_path / "bundle", claude=False)

    result = run_resolver(skill_dir, target)

    assert ".claude-plugin/plugin.json" in result.stderr
    assert_identity(result, "unknown", warning=True)


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        json.dumps({"name": "grimore"}),
        json.dumps({"name": "grimore", "version": ""}),
    ],
)
def test_unusable_authoritative_metadata_warns_and_returns_unknown(
    tmp_path, content
):
    target = tmp_path / "target"
    init_repo(target)
    commit_all(target)
    source = tmp_path / "bundle"
    skill_dir = make_bundle(source)
    (source / ".claude-plugin" / "plugin.json").write_text(
        content,
        encoding="utf-8",
    )

    assert_identity(run_resolver(skill_dir, target), "unknown", warning=True)


def test_unusable_codex_metadata_warns_and_returns_unknown(tmp_path):
    target = tmp_path / "target"
    init_repo(target)
    commit_all(target)
    source = tmp_path / "bundle"
    skill_dir = make_bundle(source, codex=True)
    (source / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"name": "grimore"}),
        encoding="utf-8",
    )

    result = run_resolver(skill_dir, target)

    assert ".codex-plugin/plugin.json" in result.stderr
    assert_identity(result, "unknown", warning=True)


def test_invalid_cli_invocation_is_nonzero():
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(RESOLVER)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert result.stdout == ""
