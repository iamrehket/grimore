#!/usr/bin/env python3
"""Resolve the source identity stamped by adopt-docs.

The resolver is deliberately read-only and dependency-free. It prints exactly
one identity to stdout on every successful resolution, including the safe
``unknown`` fallback. Unusable metadata is reported separately on stderr.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

CLAUDE_MANIFEST = Path(".claude-plugin/plugin.json")
CODEX_MANIFEST = Path(".codex-plugin/plugin.json")


def existing_directory(value):
    path = Path(value)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"not a directory: {value}")
    return path.resolve()


def git_value(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def read_manifest(path):
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, f"{path} is missing"
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"{path} is not valid JSON: {exc.msg}"
    if not isinstance(data, dict):
        return None, f"{path} must contain a JSON object"
    return data, None


def identity_fields(manifest, path):
    name = manifest.get("name")
    version = manifest.get("version")
    if name != "grimore":
        return None, f"{path} must identify plugin name 'grimore'"
    if not isinstance(version, str) or not version.strip():
        return None, f"{path} must contain a non-empty string version"
    return (name, version), None


def git_identity(skill_dir, target):
    source_top = git_value(skill_dir, "rev-parse", "--show-toplevel")
    target_top = git_value(target, "rev-parse", "--show-toplevel")
    if source_top is None or target_top is None:
        return None

    source_root = Path(source_top).resolve()
    target_root = Path(target_top).resolve()
    if source_root == target_root:
        return None

    manifest, error = read_manifest(source_root / CLAUDE_MANIFEST)
    if error is not None or manifest.get("name") != "grimore":
        return None
    return git_value(source_root, "rev-parse", "HEAD")


def version_identity(skill_dir):
    source_root = skill_dir.parent
    claude_path = source_root / CLAUDE_MANIFEST
    claude, error = read_manifest(claude_path)
    if error is not None:
        return None, error
    claude_identity, error = identity_fields(claude, claude_path)
    if error is not None:
        return None, error

    codex_path = source_root / CODEX_MANIFEST
    if not codex_path.exists():
        return f"grimore plugin v{claude_identity[1]}", None

    codex, error = read_manifest(codex_path)
    if error is not None:
        return None, error
    codex_identity, error = identity_fields(codex, codex_path)
    if error is not None:
        return None, error
    if claude_identity != codex_identity:
        return (
            None,
            "native plugin manifest names and versions do not match: "
            f"{claude_path} != {codex_path}",
        )
    return f"grimore plugin v{claude_identity[1]}", None


def resolve(skill_dir, target):
    commit = git_identity(skill_dir, target)
    if commit is not None:
        return commit, None
    return version_identity(skill_dir)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Resolve the read-only source identity for adopt-docs."
    )
    parser.add_argument(
        "--skill-dir",
        required=True,
        type=existing_directory,
        help="path to the adopt-docs skill directory",
    )
    parser.add_argument(
        "--target",
        required=True,
        type=existing_directory,
        help="path to the adopting repository",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        identity, warning = resolve(args.skill_dir, args.target)
    except OSError as exc:
        print(f"error: provenance resolution failed: {exc}", file=sys.stderr)
        return 1

    if warning is not None:
        print(f"warning: {warning}", file=sys.stderr)
    print(identity or "unknown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
