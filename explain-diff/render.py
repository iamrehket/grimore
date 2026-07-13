#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema>=4", "markdown-it-py>=3", "pygments>=2.17"]
# ///
"""Render an explain-diff payload (JSON + markdown) to a self-contained HTML guide or plain markdown."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import webbrowser
from pathlib import Path

import jsonschema
from markdown_it import MarkdownIt
from pygments import highlight as pygments_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.util import ClassNotFound

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
            check_mermaid(s["mermaid"])
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


MERMAID_TYPES = (
    "flowchart", "graph", "sequenceDiagram", "stateDiagram", "stateDiagram-v2",
    "classDiagram", "erDiagram", "gantt", "pie", "mindmap", "timeline", "journey",
)
_MD = MarkdownIt("commonmark").enable("table")


def check_mermaid(src: str) -> None:
    first = next((line.strip() for line in src.splitlines() if line.strip()), "")
    token = first.split()[0] if first else ""
    if token not in MERMAID_TYPES:
        raise PayloadError(
            f"mermaid block must start with a diagram type {MERMAID_TYPES}, got: {first!r}"
        )


def md_to_html(text: str) -> str:
    return _MD.render(text)


def highlight_code(code: str, filename: str) -> str:
    try:
        lexer = get_lexer_for_filename(filename)
    except ClassNotFound:
        lexer = TextLexer()
    return pygments_highlight(code, lexer, HtmlFormatter(cssclass="highlight"))


MODE_LABELS = {"warm": "live session", "cold": "cold read"}


def render_md(payload: dict) -> str:
    out = [f"# {payload['title']}", "", f"> {payload['verdict']}", "",
           f"_{MODE_LABELS[payload['mode']]} - diff: `{payload['diff']}`_", ""]
    questions = []
    for s in payload["sections"]:
        t = s["type"]
        if t == "narrative":
            out += [f"## {s['heading']}", "", s["md"], ""]
        elif t == "diagram":
            out += [f"## {s['heading']}", "", "```mermaid", s["mermaid"], "```", ""]
        elif t == "decision":
            out += [f"## Decision: {s['title']}",
                    f"_{s['provenance']}, reversal cost: {s['reversal_cost']}_", "", s["md"], ""]
            if s.get("alternatives"):
                out += ["Alternatives considered:"] + [f"- {a}" for a in s["alternatives"]] + [""]
        elif t == "hunk":
            lang = Path(s["file"]).suffix.lstrip(".")
            out += [f"### `{s['file']}:{s['lines']} @ {s['ref']}`", "", s["md"], "",
                    f"```{lang}", s["_code"], "```", ""]
        elif t == "comparison":
            out += [f"## {s['heading']}", "", "**Before:**", "", s["before_md"], "",
                    "**After:**", "", s["after_md"], ""]
        elif t == "question":
            questions.append(f"- [ ] **{s['id']}**: {s['md']}")
        elif t == "fallout":
            out += [f"## {s.get('heading', 'Mechanical fallout')}", ""]
            out += [f"- {item}" for item in s["items"]] + [""]
    if questions:
        out += ["## Open questions", ""] + questions + [""]
    return "\n".join(out)


def render_html(payload: dict) -> str:
    raise PayloadError("html renderer not built yet")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("payload", type=Path)
    ap.add_argument("--format", choices=["html", "md"], default="html")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--open", action="store_true", dest="open_after")
    ap.add_argument("--write-hashes", action="store_true")
    ap.add_argument("--repo", type=Path, default=Path("."))
    args = ap.parse_args(argv)
    try:
        payload = load_payload(args.payload)
        for w in resolve_hunks(payload, args.repo.resolve()):
            print(f"WARNING: {w}", file=sys.stderr)
        rendered = render_html(payload) if args.format == "html" else render_md(payload)
        if args.write_hashes:
            write_hashes(payload, args.payload)
    except PayloadError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    out_path = args.out or args.payload.with_suffix(f".{args.format}")
    out_path.write_text(rendered)
    print(out_path)
    if args.open_after:
        webbrowser.open(out_path.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
