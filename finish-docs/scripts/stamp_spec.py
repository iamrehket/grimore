#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""stamp_spec - write the implemented: stamp that finish-docs owns.

grim derives banner blocks and never writes this stamp; finish-docs writes the
stamp and never authors banner text. That split is deliberate: the banner is a
pure function of the store, while the stamp records an event only the
branch-finish pass witnesses.

Phase A of finish-docs covers discovery and stamping only. A spec whose
referenced components include a draft is REFUSED rather than stamped, because
stamping asserts the spec was implemented and nothing here reconciles a draft
against the diff to justify that claim. Reconciliation is phase B.

The stamp is written quoted. Unquoted, YAML reads ' #' as the start of a
comment and 'implemented: 2026-07-24 (PR #14)' silently truncates to
'2026-07-24 (PR'.
"""
from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PR_RE = re.compile(r"^\d+$")

# grim owns the contract for what a stamp may say; this is its parser's shape.
# Anything this script writes must satisfy it, or grim reports E091 and - because
# a bad stamp blocks derivation - `lint --fix` cannot repair what we wrote.
IMPLEMENTED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:\s+\(PR #(\d+)\))?$")

DEFAULTS = {"components": "docs/components", "specs": "docs/specs", "default_branch": "main"}

SKIP, REFUSE, STAMP = "skip", "refuse", "stamp"


class DiscoveryError(Exception):
    """git could not answer what the branch changed - never 'nothing changed'."""


def valid_date(value: str) -> bool:
    """Regex plus calendar check. The regex alone admits forms fromisoformat
    rejects, and fromisoformat alone admits forms the regex rejects; grim pairs
    them for that reason and so must anything writing what grim reads."""
    if not DATE_RE.fullmatch(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def load_config(root: Path) -> dict:
    raw: dict = {}
    cfg_path = root / ".grimore.toml"
    if cfg_path.is_file():
        raw = tomllib.loads(cfg_path.read_text(encoding="utf-8")).get("grimore", {})
    return {key: raw.get(key, default) for key, default in DEFAULTS.items()}


def read_frontmatter(path: Path) -> tuple[str, re.Match | None, dict | None]:
    """Raw text, the frontmatter match, and the parsed mapping.

    Decoded from bytes rather than read as text: text mode normalizes CRLF to
    LF, and a later write would then rewrite line endings the spec never asked
    us to touch.
    """
    raw = path.read_bytes().decode("utf-8")
    m = FM_RE.match(raw)
    if not m:
        return raw, None, None
    try:
        parsed = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return raw, m, None
    return raw, m, parsed if isinstance(parsed, dict) else None


def component_statuses(components_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not components_dir.is_dir():
        return out
    for path in sorted(components_dir.rglob("*.md")):
        _raw, m, fm = read_frontmatter(path)
        if m is None or not fm:
            continue
        cid, status = fm.get("id"), fm.get("status")
        if isinstance(cid, str) and isinstance(status, str):
            out[cid] = status
    return out


def merge_base(root: Path, default_branch: str) -> tuple[str | None, list[str]]:
    refs = [f"origin/{default_branch}", default_branch]
    for ref in refs:
        result = subprocess.run(
            ["git", "-C", str(root), "merge-base", "HEAD", ref],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip(), refs
    return None, refs


def discover_from_diff(root: Path, specs_dir: Path, default_branch: str) -> list[Path]:
    """Specs the branch touched. Raises DiscoveryError when git cannot answer.

    An unresolvable merge-base must not read as "no specs changed": a shallow
    clone, a detached HEAD, a fork without origin/<default>, or a wrong
    default_branch would all silently report success while stamping nothing.
    grim fails closed on exactly this condition rather than skipping.
    """
    base, refs = merge_base(root, default_branch)
    if base is None:
        raise DiscoveryError(
            f"cannot resolve a git merge-base with any of {refs}; "
            "fix the checkout (CI needs fetch-depth: 0) or pass --spec explicitly"
        )
    result = subprocess.run(
        ["git", "-C", str(root), "-c", "diff.relative=false", "diff",
         "--no-renames", "--name-only", "-z", base],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DiscoveryError(f"git diff against {base} failed: {result.stderr.strip()}")
    out = []
    for name in result.stdout.split("\0"):
        if not name.endswith(".md"):
            continue
        path = root / name
        if not path.is_file() or specs_dir.resolve() not in path.resolve().parents:
            continue
        _raw, m, fm = read_frontmatter(path)
        if m is not None and fm is not None and "components" in fm:
            out.append(path)
    return sorted(set(out))


def classify(path: Path, statuses: dict[str, str]) -> tuple[str, str]:
    """What to do with this spec, and why - one of skip, refuse, stamp."""
    _raw, m, fm = read_frontmatter(path)
    if m is None or fm is None:
        return REFUSE, "frontmatter is missing or unparseable"
    if "implemented" in fm:
        existing = fm["implemented"]
        if isinstance(existing, datetime.date) and not isinstance(existing, datetime.datetime):
            return SKIP, "already stamped"
        if isinstance(existing, str) and IMPLEMENTED_RE.match(existing.strip()):
            return SKIP, "already stamped"
        # Membership alone would report this as fine while grim reports E091 and
        # refuses to derive the banner. Never rewritten here - the stamp is
        # written once - but the operator has to be told.
        return REFUSE, (
            f"already carries a malformed stamp ({existing!r}); grim reports E091 "
            "and cannot derive the banner until it is corrected by hand"
        )
    # Not `or []`: that short-circuits before the type check, so a falsy
    # non-list (components: no, "", 0) would sail through as an empty list here
    # while grim reports E094 on the same file.
    components = fm.get("components")
    if components is None:
        components = []
    if not isinstance(components, list) or not all(isinstance(c, str) for c in components):
        return REFUSE, "components: is not a list of strings"
    unknown = sorted(c for c in components if c not in statuses)
    if unknown:
        return REFUSE, f"components not in the store, cannot verify: {', '.join(unknown)}"
    drafts = sorted(c for c in components if statuses[c] == "draft")
    if drafts:
        return REFUSE, (
            f"still draft, so nothing justifies an implemented claim: {', '.join(drafts)}"
            " (reconciliation is phase B)"
        )
    return STAMP, "all referenced components are current or superseded"


def stamp_value(date: str, pr: str | None) -> str:
    return f"{date} (PR #{pr})" if pr else date


def write_stamp(path: Path, value: str) -> None:
    raw, m, _fm = read_frontmatter(path)
    if m is None:  # not an assert: asserts vanish under -O
        raise ValueError(f"{path} has no parseable frontmatter")
    newline = "\r\n" if raw[: m.end()].find("\r\n") != -1 else "\n"
    insert_at = m.end(1)
    line = f'{newline}implemented: "{value}"'
    path.write_bytes((raw[:insert_at] + line + raw[insert_at:]).encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stamp_spec",
        description="Write the implemented: stamp on finished specs (finish-docs phase A).",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root")
    parser.add_argument("--spec", type=Path, action="append", default=[],
                        help="stamp this spec regardless of the branch diff; repeatable")
    parser.add_argument("--branch-diff", action="store_true",
                        help="discover specs changed in the branch diff")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD the work landed")
    parser.add_argument("--pr", help="pull request number, recorded alongside the date")
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args(argv)

    if not valid_date(args.date):
        print(f"error: --date must be a real YYYY-MM-DD date, got {args.date!r}",
              file=sys.stderr)
        return 2
    if args.pr is not None and not PR_RE.fullmatch(args.pr):
        print(f"error: --pr must be digits, got {args.pr!r}", file=sys.stderr)
        return 2
    if not args.spec and not args.branch_diff:
        print("error: pass --branch-diff or at least one --spec", file=sys.stderr)
        return 2

    value = stamp_value(args.date, args.pr)
    # Belt and braces. Everything reaching here is already validated, but the
    # composed value is what grim parses, so check the actual artifact rather
    # than trusting that validating the parts validated the whole.
    if not IMPLEMENTED_RE.match(value):
        print(f"error: refusing to write a stamp grim would reject: {value!r}",
              file=sys.stderr)
        return 2

    root = args.root.resolve()
    cfg = load_config(root)
    specs_dir = (root / cfg["specs"]).resolve()
    statuses = component_statuses(root / cfg["components"])

    targets = []
    for raw in args.spec:
        target = (root / raw).resolve()
        if not target.is_file():
            print(f"error: no such spec: {target}", file=sys.stderr)
            return 2
        # Mirrors the containment guard grim applies to configured paths. Without
        # it, --spec (or a symlink under the specs dir) writes anywhere on disk.
        if specs_dir not in target.parents:
            print(f"error: --spec must name a file under {specs_dir}, got {target}",
                  file=sys.stderr)
            return 2
        targets.append(target)

    if args.branch_diff:
        try:
            targets += discover_from_diff(root, specs_dir, cfg["default_branch"])
        except DiscoveryError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if not targets:
        print("no specs discovered; nothing to stamp")
        return 0
    refused = False
    for path in sorted(set(targets)):
        rel = path.relative_to(root).as_posix()
        action, why = classify(path, statuses)
        if action == STAMP:
            if not args.dry_run:
                write_stamp(path, value)
            print(f"{'WOULD STAMP' if args.dry_run else 'STAMPED'} {rel}: {value}")
        elif action == SKIP:
            print(f"SKIP {rel}: {why}")
        else:
            refused = True
            print(f"REFUSED {rel}: {why}", file=sys.stderr)

    if refused:
        print("\nrefusals above were not stamped; resolve them or wait for "
              "finish-docs phase B", file=sys.stderr)
    return 1 if refused else 0


if __name__ == "__main__":
    raise SystemExit(main())
