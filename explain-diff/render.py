#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema>=4", "markdown-it-py>=3", "pygments>=2.17"]
# ///
"""Render an explain-diff payload (JSON + markdown) to a self-contained HTML guide or plain markdown."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

SKILL_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SKILL_DIR / "schema.json"


class PayloadError(Exception):
    """Payload is invalid; message tells the author what to fix."""


def load_payload(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise PayloadError(f"{path} is not valid JSON: {e}") from e
    schema = json.loads(SCHEMA_PATH.read_text())
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as e:
        loc = "/".join(str(p) for p in e.absolute_path) or "top level"
        raise PayloadError(f"schema violation at {loc}: {e.message}") from e

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
