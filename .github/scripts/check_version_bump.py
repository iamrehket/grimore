#!/usr/bin/env python3
"""Derive the plugin version from Conventional Commit types, and check or set it.

The plugin ships as the whole repository (marketplace.json declares
source "./"), so the version string in .claude-plugin/plugin.json is the only
signal a consumer has that anything changed. This computes what that version
must be, so CI can verify it and an author can apply it from the same code
path - a separate calculator would be free to drift from the checker.

The target version is a pure function of the commit range: the required level
is applied to the version at the merge-base, never to the current value.
Running --apply once or five times therefore yields the same answer, and it
will lower a version that was raised beyond what the commits justify. Express
a bigger intent with a bigger type (feat!: rather than a hand-edited major).

Rules, in order:

1. A Version-Waive trailer in any commit skips everything. The reason is
   mandatory and is echoed so reviewers see each bypass.
2. A pull request touching only exempt paths needs no bump. Exempt paths
   reach consumers but cannot change behaviour.
3. The pull request title must declare at least the highest type found in the
   commits. A squash-merge keeps only the title, so a title that under-declares
   would leave main's history justifying a smaller bump than the one that
   shipped. Requiring dominance makes the answer identical before and after a
   squash.
4. The highest type sets the required level - breaking major, feat minor,
   fix/refactor/perf/revert/build patch. No type at all on a consumer-facing
   change is a failure, not a pass: reading absence as permission would
   rebuild the hole this exists to close.
5. Verify mode requires the actual bump to be at least that level; apply mode
   writes exactly that level.

Reads PR_TITLE and BASE_SHA from the environment rather than interpolating
them into a shell command - the title is attacker-controlled text.
"""

import argparse
import os
import re
import subprocess
import sys
from typing import NoReturn

PLUGIN_MANIFEST = ".claude-plugin/plugin.json"

# Paths that reach consumers but cannot change how the plugin behaves.
EXEMPT_PREFIXES = ("docs/", "tests/", ".github/")
EXEMPT_FILES = (".gitignore",)

LEVELS = ("none", "patch", "minor", "major")

SUBJECT_RE = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\([^)]*\))?(?P<bang>!)?:\s+\S")
BREAKING_RE = re.compile(r"^BREAKING[ -]CHANGE:\s*\S", re.MULTILINE)
WAIVE_RE = re.compile(r"^Version-Waive:\s*(\S.*)$", re.MULTILINE)
VERSION_RE = re.compile(r'("version"\s*:\s*")([^"]*)(")')

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


def fail(message) -> NoReturn:
    print(f"FAIL: {message}")
    sys.exit(1)


def rank(level):
    return LEVELS.index(level)


def parse_version(raw):
    parts = raw.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        fail(f"version {raw!r} is not MAJOR.MINOR.PATCH")
    return tuple(int(p) for p in parts)


def show_version(version):
    return ".".join(str(n) for n in version)


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


def apply_level(version, level):
    """The version reached by applying one level to version."""
    major, minor, patch = version
    if level == "major":
        return (major + 1, 0, 0)
    if level == "minor":
        return (major, minor + 1, 0)
    if level == "patch":
        return (major, minor, patch + 1)
    return version


def message_level(message):
    """Highest level implied by one commit message or pull request title."""
    subject, _, body = message.partition("\n")
    match = SUBJECT_RE.match(subject.strip())
    if not match:
        return "none"
    if match.group("bang") or BREAKING_RE.search(body):
        return "major"
    return TYPE_LEVELS.get(match.group("type").lower(), "none")


def highest(messages):
    level = "none"
    for message in messages:
        candidate = message_level(message)
        if rank(candidate) > rank(level):
            level = candidate
    return level


def is_exempt(path):
    if path.startswith(EXEMPT_PREFIXES) or path in EXEMPT_FILES:
        return True
    # Root-level markdown: README, CHANGELOG, and friends.
    return "/" not in path and path.endswith(".md")


def read_manifest_version(text):
    match = VERSION_RE.search(text)
    if not match:
        fail(f"no version field in {PLUGIN_MANIFEST}")
    return parse_version(match.group(2))


def main():
    parser = argparse.ArgumentParser(
        description="Check or set the plugin version implied by the commit range."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply", action="store_true",
        help="write the computed version into the manifest",
    )
    mode.add_argument(
        "--print", dest="print_only", action="store_true",
        help="print the computed version and exit",
    )
    parser.add_argument(
        "--message",
        default="",
        help="message of a commit about to be made, counted alongside the range",
    )
    args = parser.parse_args()

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

    authored = [*commits, args.message] if args.message else commits
    commit_level = highest(authored)

    # Squash-merge keeps only the title, so it has to stand alone.
    if pr_title and rank(message_level(pr_title)) < rank(commit_level):
        fail(
            f"pull request title declares {message_level(pr_title)}, but a commit "
            f"declares {commit_level}.\n"
            "  raise the title to match: squashing keeps only the title, so a\n"
            "  lower title would leave the merged history justifying a smaller\n"
            "  bump than the one that shipped."
        )

    required = highest([pr_title, *authored]) if pr_title else commit_level
    if required == "none":
        fail(
            "consumer-facing change with no Conventional Commit type.\n"
            f"  changed: {', '.join(consumer_facing[:5])}"
            f"{' ...' if len(consumer_facing) > 5 else ''}\n"
            "  declare feat:, fix:, or a breaking change (type! or a\n"
            "  BREAKING CHANGE: footer) in the PR title or a commit,\n"
            "  or add a 'Version-Waive: <reason>' commit trailer."
        )

    base_version = read_manifest_version(
        run("git", "show", f"{merge_base}:{PLUGIN_MANIFEST}")
    )
    target = apply_level(base_version, required)

    if args.print_only:
        print(show_version(target))
        return

    with open(PLUGIN_MANIFEST) as handle:
        text = handle.read()
    head_version = read_manifest_version(text)

    if args.apply:
        if head_version == target:
            print(f"already at {show_version(target)} ({required} from "
                  f"{show_version(base_version)})")
            return
        if head_version > target:
            print(f"note: lowering {show_version(head_version)} to the computed "
                  f"{show_version(target)}; the version is a function of the "
                  f"commit range, so raise the type to raise the version")
        with open(PLUGIN_MANIFEST, "w") as handle:
            handle.write(VERSION_RE.sub(
                lambda m: f"{m.group(1)}{show_version(target)}{m.group(3)}",
                text,
                count=1,
            ))
        print(f"set {show_version(head_version)} -> {show_version(target)} "
              f"({required} from {show_version(base_version)})")
        return

    actual = bump_level(base_version, head_version)
    if actual == "invalid":
        fail(f"version went backwards: "
             f"{show_version(base_version)} -> {show_version(head_version)}")
    if rank(actual) < rank(required):
        fail(
            f"change requires a {required} bump, got {actual} "
            f"({show_version(base_version)} -> {show_version(head_version)}).\n"
            f"  run this script with --apply to set {show_version(target)}."
        )

    print(f"ok: {required} required, {actual} applied "
          f"({show_version(base_version)} -> {show_version(head_version)})")


if __name__ == "__main__":
    main()
