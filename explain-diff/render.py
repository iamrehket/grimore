#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema>=4", "markdown-it-py>=3", "pygments>=2.17"]
# ///
"""Render an explain-diff payload (JSON + markdown) to a self-contained HTML guide or plain markdown."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import jsonschema

SKILL_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SKILL_DIR / "schema.json"


class PayloadError(Exception):
    """Payload is invalid; message tells the author what to fix."""


def load_payload(path: Path) -> dict:
    try:
        text = path.read_text()
    except OSError as e:
        raise PayloadError(f"cannot read payload file {path}: {e}") from e
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        raise PayloadError(f"{path} is not valid JSON: {e}") from e
    schema = json.loads(SCHEMA_PATH.read_text())
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as e:
        err = jsonschema.exceptions.best_match([e]) or e
        loc = "/".join(str(p) for p in err.absolute_path) or "top level"
        msg = f"schema violation at {loc}: {err.message}"
        if e.validator == "oneOf":
            msg += (" (section types: narrative, diagram, decision, hunk, "
                    "comparison, question, fallout)")
        raise PayloadError(msg) from e

    ids = [s["id"] for s in payload["sections"] if s["type"] in ("decision", "question")]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise PayloadError(f"duplicate section ids: {dupes}")
    for s in payload["sections"]:
        if s["type"] == "diagram":
            for node, anchor in s.get("links", {}).items():
                if anchor.lstrip("#") not in ids:
                    raise PayloadError(
                        f"diagram link {node!r} -> {anchor!r} targets no decision/question id"
                    )
    return payload


def extract_hunk(hunk: dict, repo_root: Path) -> tuple[str, str]:
    start, end = (int(n) for n in hunk["lines"].split("-"))
    where = f"{hunk['file']}:{hunk['lines']} @ {hunk['ref']}"
    if start < 1 or end < start:
        raise PayloadError(f"{where}: invalid line range (need 1 <= start <= end)")
    if hunk["ref"] == "WORKTREE":
        target = repo_root / hunk["file"]
        if not target.is_file():
            raise PayloadError(f"hunk file not found on disk: {hunk['file']}")
        text = target.read_text()
    else:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{hunk['ref']}:{hunk['file']}"],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise PayloadError(f"cannot resolve {where}: {proc.stderr.strip()}")
        text = proc.stdout
    lines = text.splitlines()[start - 1 : end]
    if len(lines) < (end - start + 1):
        raise PayloadError(f"{where}: file has fewer lines than requested range {start}-{end}")
    code = "\n".join(lines)
    return code, hashlib.sha256(code.encode()).hexdigest()[:16]


def resolve_hunks(payload: dict, repo_root: Path) -> list[str]:
    warnings = []
    for s in payload["sections"]:
        if s["type"] != "hunk":
            continue
        s["_code"], s["_sha256"] = extract_hunk(s, repo_root)
        if s.get("sha256") and s["sha256"] != s["_sha256"]:
            warnings.append(
                f"hunk {s['file']}:{s['lines']} has drifted since hashes were written; "
                "annotations may no longer match the code"
            )
    return warnings


def write_hashes(payload: dict, path: Path) -> None:
    def clean(obj):
        if isinstance(obj, dict):
            out = {k: clean(v) for k, v in obj.items() if not k.startswith("_")}
            if obj.get("type") == "hunk" and "_sha256" in obj:
                out["sha256"] = obj["_sha256"]
            return out
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        return obj

    path.write_text(json.dumps(clean(payload), indent=2) + "\n")
