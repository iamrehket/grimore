"""Scenarios for .github/scripts/check_version_bump.py.

The checker is a CI entry point rather than an importable module, so these
drive it as a subprocess with the same environment CI supplies.
"""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "check_version_bump.py"
MANIFESTS = {
    "claude": Path(".claude-plugin/plugin.json"),
    "codex": Path(".codex-plugin/plugin.json"),
}


def git(root, *args):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def manifest_data(version="0.2.0", **overrides):
    data = {
        "name": "grimore",
        "version": version,
        "description": "Grimore test plugin",
        "author": {"name": "Test"},
        "skills": ["./adopt-docs"],
    }
    data.update(overrides)
    return data


def write_manifest(root, host, version="0.2.0", **overrides):
    path = root / MANIFESTS[host]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest_data(version, **overrides), indent=2) + "\n",
        encoding="utf-8",
    )


def set_version(root, version, hosts=("claude", "codex")):
    for host in hosts:
        path = root / MANIFESTS[host]
        data = json.loads(path.read_text(encoding="utf-8"))
        data["version"] = version
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def set_manifest_field(root, host, field, value):
    path = root / MANIFESTS[host]
    data = json.loads(path.read_text(encoding="utf-8"))
    data[field] = value
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def repo(root, *, codex_at_base=True):
    """Init a repo at version 0.2.0, then branch; returns the base SHA."""
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    write_manifest(root, "claude")
    if codex_at_base:
        write_manifest(root, "codex")
    (root / "adopt-docs").mkdir()
    (root / "adopt-docs" / "SKILL.md").write_text("base\n")
    (root / "docs").mkdir()
    (root / "docs" / "note.md").write_text("base\n")
    git(root, "add", "-A")
    git(root, "commit", "-m", "initial")
    base = git(root, "rev-parse", "HEAD").strip()
    git(root, "checkout", "-b", "feature")
    return base


def commit(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-m", message)


def touch_skill(root):
    (root / "adopt-docs" / "SKILL.md").write_text("changed\n")


def check(root, base, title="", *args):
    r = subprocess.run(
        ["python3", str(CHECKER), *args],
        cwd=root,
        capture_output=True,
        text=True,
        env={**os.environ, "BASE_SHA": base, "PR_TITLE": title},
    )
    return r.returncode, r.stdout + r.stderr


def version_of(root, host="claude"):
    return json.loads((root / MANIFESTS[host]).read_text())["version"]


def versions_of(root):
    return {host: version_of(root, host) for host in MANIFESTS}


def load_checker():
    spec = importlib.util.spec_from_file_location("check_version_bump_under_test", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exempt_only_change_passes(tmp_path):
    base = repo(tmp_path)
    (tmp_path / "docs" / "note.md").write_text("more\n")
    commit(tmp_path, "chore: docs tweak")
    code, out = check(tmp_path, base, "chore: docs tweak")
    assert code == 0
    assert "none consumer-facing" in out


def test_consumer_change_without_type_fails(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    commit(tmp_path, "IAM-99 adopt a thing")
    code, out = check(tmp_path, base, "IAM-99 adopt a thing")
    assert code == 1
    assert "no Conventional Commit type" in out


def test_feat_without_bump_fails(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    commit(tmp_path, "feat: thing")
    code, out = check(tmp_path, base, "feat: thing")
    assert code == 1
    assert "requires a minor bump, got none" in out


def test_feat_with_patch_bump_fails(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.2.1")
    commit(tmp_path, "feat: thing")
    code, out = check(tmp_path, base, "feat: thing")
    assert code == 1
    assert "requires a minor bump, got patch" in out


def test_feat_with_minor_bump_passes(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.3.0")
    commit(tmp_path, "feat: thing")
    assert check(tmp_path, base, "feat: thing")[0] == 0


def test_feat_accepts_a_larger_bump_than_required(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "1.0.0")
    commit(tmp_path, "feat: thing")
    code, out = check(tmp_path, base, "feat: thing")
    assert code == 0
    assert "minor required, major applied" in out


def test_fix_with_patch_bump_passes(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.2.1")
    commit(tmp_path, "fix: thing")
    assert check(tmp_path, base, "fix: thing")[0] == 0


def test_refactor_maps_to_patch(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.2.1")
    commit(tmp_path, "refactor: reshape the interview flow")
    code, out = check(tmp_path, base, "refactor: reshape the interview flow")
    assert code == 0
    assert "patch required, patch applied" in out


def test_perf_maps_to_patch(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.2.1")
    commit(tmp_path, "perf: fewer store reads")
    assert check(tmp_path, base, "perf: fewer store reads")[0] == 0


def test_bang_breaking_requires_major(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.3.0")
    commit(tmp_path, "feat!: thing")
    code, out = check(tmp_path, base, "feat!: thing")
    assert code == 1
    assert "requires a major bump, got minor" in out


def test_bang_breaking_with_major_bump_passes(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "1.0.0")
    commit(tmp_path, "feat!: thing")
    assert check(tmp_path, base, "feat!: thing")[0] == 0


def test_breaking_change_footer_requires_major(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.3.0")
    commit(tmp_path, "feat!: thing\n\nBREAKING CHANGE: drops the old flag")
    code, out = check(tmp_path, base, "feat!: thing")
    assert code == 1
    assert "requires a major bump" in out


def test_version_decrease_fails(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.1.0")
    commit(tmp_path, "feat: thing")
    code, out = check(tmp_path, base, "feat: thing")
    assert code == 1
    assert "went backwards" in out


def test_waiver_trailer_skips_an_untyped_change(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    commit(
        tmp_path,
        "IAM-99 revert unreleased change\n\nVersion-Waive: reverts an unreleased commit",
    )
    code, out = check(tmp_path, base, "IAM-99 revert unreleased change")
    assert code == 0
    assert "WAIVED by trailer: reverts an unreleased commit" in out


def test_type_may_come_from_the_pull_request_title_alone(tmp_path):
    """Squash-merge keeps only the title, so it has to count on its own."""
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.3.0")
    commit(tmp_path, "IAM-99 untyped subject")
    assert check(tmp_path, base, "feat: thing")[0] == 0


def test_title_must_declare_the_highest_type(tmp_path):
    """Squash keeps only the title, so a lower title would lose the type."""
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "1.0.0")
    commit(tmp_path, "feat!: breaking inside")
    code, out = check(tmp_path, base, "feat: thing")
    assert code == 1
    assert "title declares minor, but a commit declares major" in out


def test_title_matching_the_highest_type_passes(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "1.0.0")
    commit(tmp_path, "feat!: breaking inside")
    assert check(tmp_path, base, "feat!: thing")[0] == 0


def test_scoped_type_parses(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.3.0")
    commit(tmp_path, "feat(adopt-docs): thing")
    assert check(tmp_path, base, "feat(adopt-docs): thing")[0] == 0


def test_chore_on_a_consumer_path_fails(tmp_path):
    """A chore touching shipped code is a mislabel, not a reason to skip."""
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.3.0")
    commit(tmp_path, "chore: thing")
    code, out = check(tmp_path, base, "chore: thing")
    assert code == 1
    assert "no Conventional Commit type" in out


def test_every_commit_in_the_range_is_parsed(tmp_path):
    """git log's entry separator must not swallow types after the first."""
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.2.1")
    # git log is newest-first, so the feat must be the OLDER commit: it is the
    # later entries, not the first, that a separator bug drops.
    commit(tmp_path, "feat: first")
    (tmp_path / "adopt-docs" / "SKILL.md").write_text("again\n")
    commit(tmp_path, "fix: second")
    code, out = check(tmp_path, base, "")
    assert code == 1
    assert "requires a minor bump, got patch" in out


def test_merging_the_base_branch_does_not_import_its_types(tmp_path):
    """CI passes the base tip, so an update merge adds nothing to the range."""
    base_start = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "0.2.1")
    commit(tmp_path, "fix: thing")
    git(tmp_path, "checkout", "main")
    (tmp_path / "docs" / "note.md").write_text("moved on\n")
    commit(tmp_path, "feat: unrelated work on main")
    base_tip = git(tmp_path, "rev-parse", "HEAD").strip()
    git(tmp_path, "checkout", "feature")
    git(tmp_path, "merge", "--no-edit", "main")
    assert base_tip != base_start
    code, out = check(tmp_path, base_tip, "fix: thing")
    assert code == 0
    assert "patch required, patch applied" in out


def test_apply_writes_the_computed_version(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    commit(tmp_path, "feat: thing")
    code, out = check(tmp_path, base, "feat: thing", "--apply")
    assert code == 0
    assert version_of(tmp_path) == "0.3.0"
    assert "set 0.2.0 -> 0.3.0 (minor from 0.2.0)" in out


def test_apply_is_idempotent(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    commit(tmp_path, "feat: thing")
    check(tmp_path, base, "feat: thing", "--apply")
    code, out = check(tmp_path, base, "feat: thing", "--apply")
    assert code == 0
    assert version_of(tmp_path) == "0.3.0"
    assert "already at 0.3.0" in out


def test_apply_lowers_a_version_raised_beyond_the_commits(tmp_path):
    """The version is a function of the range, so it can move down too."""
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "5.0.0")
    commit(tmp_path, "fix: thing")
    code, out = check(tmp_path, base, "fix: thing", "--apply")
    assert code == 0
    assert version_of(tmp_path) == "0.2.1"
    assert "lowering 5.0.0" in out


def test_apply_counts_an_in_flight_message(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    commit(tmp_path, "fix: groundwork")
    code, _ = check(tmp_path, base, "", "--apply", "--message", "feat: about to commit")
    assert code == 0
    assert version_of(tmp_path) == "0.3.0"


def test_apply_preserves_manifest_formatting(tmp_path):
    base = repo(tmp_path)
    original_modes = {
        host: (tmp_path / path).stat().st_mode for host, path in MANIFESTS.items()
    }
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        '{\n  "name": "grimore",\n  "version": "0.2.0",\n'
        '  "description": "Grimore test plugin",\n'
        '  "author": {"name": "Test"},\n'
        '  "skills": ["./adopt-docs"]\n}\n'
    )
    (tmp_path / ".codex-plugin" / "plugin.json").write_text(
        '{"name":"grimore","version":"0.2.0",'
        '"description":"Grimore test plugin","author":{"name":"Test"},'
        '"skills":["./adopt-docs"]}\n'
    )
    commit(tmp_path, "chore: reformat")
    touch_skill(tmp_path)
    commit(tmp_path, "feat: thing")
    check(tmp_path, base, "feat: thing", "--apply")
    claude = (tmp_path / ".claude-plugin" / "plugin.json").read_text()
    codex = (tmp_path / ".codex-plugin" / "plugin.json").read_text()
    assert claude == (
        '{\n  "name": "grimore",\n  "version": "0.3.0",\n'
        '  "description": "Grimore test plugin",\n'
        '  "author": {"name": "Test"},\n'
        '  "skills": ["./adopt-docs"]\n}\n'
    )
    assert codex == (
        '{"name":"grimore","version":"0.3.0",'
        '"description":"Grimore test plugin","author":{"name":"Test"},'
        '"skills":["./adopt-docs"]}\n'
    )
    assert {
        host: (tmp_path / path).stat().st_mode for host, path in MANIFESTS.items()
    } == original_modes


def test_print_reports_the_target_without_writing(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    commit(tmp_path, "feat: thing")
    code, out = check(tmp_path, base, "feat: thing", "--print")
    assert code == 0
    assert out.strip() == "0.3.0"
    assert version_of(tmp_path) == "0.2.0"


def test_squashing_yields_the_same_version(tmp_path):
    """The whole point of title-dominance: same answer before and after."""
    base = repo(tmp_path)
    title = "feat: the actual change"
    touch_skill(tmp_path)
    commit(tmp_path, "fix: groundwork")
    (tmp_path / "adopt-docs" / "SKILL.md").write_text("again\n")
    commit(tmp_path, title)
    code, before = check(tmp_path, base, title, "--print")
    assert code == 0

    # Collapse to one commit whose subject is the title, as a squash-merge does.
    git(tmp_path, "reset", "--soft", base)
    commit(tmp_path, title)
    code, after = check(tmp_path, base, title, "--print")
    assert code == 0
    assert before.strip() == after.strip() == "0.3.0"


def test_waiver_also_blocks_apply(tmp_path):
    """A waived baseline must not be recomputed and clobbered."""
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "1.0.0")
    commit(tmp_path, "feat: thing\n\nVersion-Waive: deliberate 1.0.0 baseline")
    code, out = check(tmp_path, base, "feat: thing", "--apply")
    assert code == 0
    assert "WAIVED" in out
    assert version_of(tmp_path) == "1.0.0"


@pytest.mark.parametrize(
    ("field", "codex_value"),
    [
        ("name", "not-grimore"),
        ("description", "different"),
        ("author", {"name": "Someone Else"}),
        ("skills", ["./explain-diff", "./adopt-docs"]),
        ("version", "0.2.1"),
    ],
)
def test_check_rejects_shared_manifest_drift(tmp_path, field, codex_value):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_manifest_field(tmp_path, "codex", field, codex_value)
    commit(tmp_path, "fix: thing")
    code, out = check(tmp_path, base, "fix: thing")
    assert code == 1
    assert f"shared field {field!r}" in out


def test_print_rejects_shared_manifest_drift(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_manifest_field(tmp_path, "codex", "description", "different")
    commit(tmp_path, "fix: thing")
    code, out = check(tmp_path, base, "fix: thing", "--print")
    assert code == 1
    assert "shared field 'description'" in out


def test_exempt_only_change_still_rejects_manifest_drift(tmp_path):
    base = repo(tmp_path)
    (tmp_path / "docs" / "note.md").write_text("more\n")
    commit(tmp_path, "docs: note")
    set_manifest_field(tmp_path, "codex", "author", {"name": "Drift"})
    code, out = check(tmp_path, base, "docs: note")
    assert code == 1
    assert "shared field 'author'" in out


def test_apply_rejects_non_version_drift_without_writing(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_manifest_field(tmp_path, "codex", "description", "different")
    commit(tmp_path, "feat: thing")
    before = versions_of(tmp_path)
    code, out = check(tmp_path, base, "feat: thing", "--apply")
    assert code == 1
    assert "shared field 'description'" in out
    assert versions_of(tmp_path) == before


def test_apply_accepts_version_only_drift_and_writes_both(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    commit(tmp_path, "feat: thing")
    set_version(tmp_path, "9.9.9", hosts=("codex",))
    code, out = check(tmp_path, base, "feat: thing", "--apply")
    assert code == 0
    assert versions_of(tmp_path) == {"claude": "0.3.0", "codex": "0.3.0"}
    assert "set" in out


def test_bootstrap_uses_claude_base_when_codex_is_absent_at_base(tmp_path):
    base = repo(tmp_path, codex_at_base=False)
    write_manifest(tmp_path, "codex")
    touch_skill(tmp_path)
    commit(tmp_path, "feat: add Codex manifest")
    code, out = check(tmp_path, base, "feat: add Codex manifest", "--apply")
    assert code == 0
    assert versions_of(tmp_path) == {"claude": "0.3.0", "codex": "0.3.0"}
    assert "minor from 0.2.0" in out


@pytest.mark.parametrize("missing_host", ["claude", "codex"])
def test_missing_head_manifest_fails_after_both_exist_at_base(tmp_path, missing_host):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    commit(tmp_path, "fix: thing")
    (tmp_path / MANIFESTS[missing_host]).unlink()
    code, out = check(tmp_path, base, "fix: thing")
    assert code == 1
    assert str(MANIFESTS[missing_host]) in out


@pytest.mark.parametrize(
    "invalid_content",
    [
        "{",
        "[]",
        json.dumps({"name": "grimore"}),
    ],
)
def test_invalid_head_manifest_fails_cleanly(tmp_path, invalid_content):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    commit(tmp_path, "fix: thing")
    (tmp_path / MANIFESTS["codex"]).write_text(invalid_content, encoding="utf-8")

    code, out = check(tmp_path, base, "fix: thing")

    assert code == 1
    assert str(MANIFESTS["codex"]) in out
    assert "Traceback" not in out


def test_manifest_exists_at_distinguishes_an_absent_path(tmp_path, monkeypatch):
    base = repo(tmp_path, codex_at_base=False)
    checker = load_checker()
    monkeypatch.chdir(tmp_path)

    assert checker.manifest_exists_at(base, MANIFESTS["claude"])
    assert not checker.manifest_exists_at(base, MANIFESTS["codex"])


def test_waiver_short_circuits_drift_and_apply_writes_neither(tmp_path):
    base = repo(tmp_path)
    touch_skill(tmp_path)
    set_version(tmp_path, "9.9.9", hosts=("codex",))
    commit(tmp_path, "feat: thing\n\nVersion-Waive: preserve deliberate mismatch")
    before = versions_of(tmp_path)
    code, out = check(tmp_path, base, "feat: thing", "--apply")
    assert code == 0
    assert "WAIVED" in out
    assert versions_of(tmp_path) == before


def test_atomic_write_restores_both_files_when_second_replace_fails(
    tmp_path, monkeypatch
):
    checker = load_checker()
    claude = tmp_path / "claude.json"
    codex = tmp_path / "codex.json"
    claude.write_text("claude original\n")
    codex.write_text("codex original\n")
    real_replace = checker.os.replace
    calls = 0

    def fail_second_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second replace failure")
        return real_replace(source, destination)

    monkeypatch.setattr(checker.os, "replace", fail_second_replace)

    with pytest.raises(checker.AtomicWriteError, match="simulated second replace"):
        checker.write_versions_atomically(
            {
                claude: "claude replacement\n",
                codex: "codex replacement\n",
            }
        )

    assert claude.read_text() == "claude original\n"
    assert codex.read_text() == "codex original\n"
