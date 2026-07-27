#!/usr/bin/env python3
"""Require plugin.json's version to move by at least what the change type implies.

The plugin ships as the whole repository (marketplace.json declares
source "./"), so the version string in .claude-plugin/plugin.json is the only
signal a consumer has that anything changed. This check makes that signal
mandatory rather than remembered.

Rules, in order:

1. A Version-Waive trailer in any commit skips the check. The reason is
   mandatory and is echoed so reviewers see every bypass.
2. A pull request touching only exempt paths passes. Exempt paths ship to
   consumers but cannot change behaviour.
3. Otherwise the highest Conventional Commit type found in the pull request
   title or any non-merge commit sets a required floor - breaking major,
   feat minor, fix patch. Declaring no type at all is a failure, not a pass:
   the whole point is that an untyped change cannot ship silently.
4. The actual version bump must be at least that floor. More is fine; less,
   none, or a decrease is not.

Reads PR_TITLE and BASE_REF from the environment rather than interpolating
them into a shell command - the title is attacker-controlled text.
"""

import json
import os
import re
import subprocess
import sys

PLUGIN_MANIFEST = ".claude-plugin/plugin.json"

# Paths that reach consumers but cannot change how the plugin behaves.
EXEMPT_PREFIXES = ("docs/", "tests/", ".github/")
EXEMPT_FILES = (".gitignore",)

LEVELS = ("none", "patch", "minor", "major")

SUBJECT_RE = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\([^)]*\))?(?P<bang>!)?:\s+\S")
BREAKING_RE = re.compile(r"^BREAKING[ -]CHANGE:\s*\S", re.MULTILINE)
WAIVE_RE = re.compile(r"^Version-Waive:\s*(\S.*)$", re.MULTILINE)

# Consumers receive changed bytes whatever the intent, so every type that
# represents real work on shipped code earns at least a patch. Types absent
# here (chore, docs, test, ci, style) are not expected on consumer-facing
# paths at all; seeing one there means the label is probably wrong, so the
# check fails rather than guessing.
TYPE_LEVELS = {
    "feat": "minor",
    "fix": "patch",
    "refactor": "patch",
    "perf": "patch",
    "revert": "patch",
    "build": "patch",
}


def run(*args):
    """Return stdout of a git command, or exit if git itself fails."""
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"command failed: {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout


def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)


def rank(level):
    return LEVELS.index(level)


def parse_version(raw):
    parts = raw.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        fail(f"version {raw!r} is not MAJOR.MINOR.PATCH")
    return tuple(int(p) for p in parts)


def bump_level(base, head):
    """Classify the move from base to head, or 'invalid' if it went backwards."""
    if head < base:
        return "invalid"
    if head[0] > base[0]:
        return "major"
    if head[0] == base[0] and head[1] > base[1]:
        return "minor"
    if head[0:2] == base[0:2] and head[2] > base[2]:
        return "patch"
    return "none"


def message_level(message):
    """Highest level implied by one commit message or pull request title."""
    subject, _, body = message.partition("\n")
    match = SUBJECT_RE.match(subject.strip())
    if not match:
        return "none"
    if match.group("bang") or BREAKING_RE.search(body):
        return "major"
    return TYPE_LEVELS.get(match.group("type").lower(), "none")


def is_exempt(path):
    if path.startswith(EXEMPT_PREFIXES) or path in EXEMPT_FILES:
        return True
    # Root-level markdown: README, CHANGELOG, and friends.
    return "/" not in path and path.endswith(".md")


def main():
    pr_title = os.environ.get("PR_TITLE", "")
    # CI passes the pull request's base SHA, which is already in history under
    # fetch-depth: 0. The origin/<branch> form is the local-testing fallback.
    base = os.environ.get("BASE_SHA") or f"origin/{os.environ.get('BASE_REF') or 'main'}"

    merge_base = run("git", "merge-base", "HEAD", base).strip()
    if not merge_base:
        fail(f"no merge-base with {base}; CI needs fetch-depth: 0")

    # git puts a newline between entries, so every chunk after the first
    # arrives with a leading blank line. Without stripping it the subject
    # parses as empty and that commit's type is silently dropped.
    raw = run("git", "log", "--no-merges", "--format=%B%x00", f"{merge_base}..HEAD")
    commits = [chunk.strip() for chunk in raw.split("\0")]
    commits = [chunk for chunk in commits if chunk]

    waiver = WAIVE_RE.search("\n".join(commits))
    if waiver:
        print(f"WAIVED by trailer: {waiver.group(1).strip()}")
        return

    changed = [p for p in run(
        "git", "diff", "--name-only", merge_base, "HEAD"
    ).splitlines() if p]
    consumer_facing = [p for p in changed if not is_exempt(p)]
    if not consumer_facing:
        print(f"exempt: {len(changed)} changed path(s), none consumer-facing")
        return

    required = "none"
    for message in [pr_title, *commits]:
        level = message_level(message)
        if rank(level) > rank(required):
            required = level

    if required == "none":
        fail(
            "consumer-facing change with no Conventional Commit type.\n"
            f"  changed: {', '.join(consumer_facing[:5])}"
            f"{' ...' if len(consumer_facing) > 5 else ''}\n"
            "  declare feat:, fix:, or a breaking change (type! or a\n"
            "  BREAKING CHANGE: footer) in the PR title or a commit,\n"
            "  or add a 'Version-Waive: <reason>' commit trailer."
        )

    base_manifest = json.loads(run("git", "show", f"{merge_base}:{PLUGIN_MANIFEST}"))
    with open(PLUGIN_MANIFEST) as handle:
        head_manifest = json.load(handle)
    base_version = parse_version(base_manifest["version"])
    head_version = parse_version(head_manifest["version"])
    actual = bump_level(base_version, head_version)

    shown = ".".join(str(n) for n in base_version), ".".join(str(n) for n in head_version)
    if actual == "invalid":
        fail(f"version went backwards: {shown[0]} -> {shown[1]}")
    if rank(actual) < rank(required):
        fail(
            f"change requires a {required} bump, got {actual} "
            f"({shown[0]} -> {shown[1]}).\n"
            f"  raise {PLUGIN_MANIFEST}'s version to at least a {required} bump."
        )

    print(f"ok: {required} required, {actual} applied ({shown[0]} -> {shown[1]})")


if __name__ == "__main__":
    main()
