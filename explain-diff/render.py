#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema>=4", "markdown-it-py>=3", "pygments>=2.17"]
# ///
"""Render an explain-diff payload (JSON + markdown) to a self-contained HTML guide or plain markdown."""
from __future__ import annotations

import argparse
import hashlib
import html as html_mod
import json
import re
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
TEMPLATE_PATH = SKILL_DIR / "assets" / "template.html"
MERMAID_PATH = SKILL_DIR / "assets" / "mermaid.min.js"


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
    rel = Path(hunk["file"])
    if rel.is_absolute() or ".." in rel.parts:
        raise PayloadError(f"{where}: file must be a relative path inside the repo")
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
    "flowchart", "graph", "gitGraph", "sequenceDiagram", "stateDiagram", "stateDiagram-v2",
    "classDiagram", "erDiagram", "gantt", "pie", "mindmap", "timeline", "journey",
)
_MD = MarkdownIt("commonmark", options_update={"html": False}).enable("table")
# Belt-and-suspenders: MarkdownIt with html=False already refuses to parse raw
# HTML as markup (it falls back to escaped text), but the literal tag source
# - including attribute names like `onerror` - still survives as inert text.
# Strip anything that looks like an HTML tag/comment/declaration before the
# markdown pass so no author-supplied markup fragments reach the page at all.
_RAW_HTML_RE = re.compile(r"<!--.*?-->|<[!?/]?[A-Za-z][^>]*>", re.DOTALL)


def check_mermaid(src: str) -> None:
    first = next((line.strip() for line in src.splitlines() if line.strip()), "")
    token = first.split()[0] if first else ""
    if token not in MERMAID_TYPES:
        raise PayloadError(
            f"mermaid block must start with a diagram type {MERMAID_TYPES}, got: {first!r}"
        )


def md_to_html(text: str) -> str:
    return _MD.render(_RAW_HTML_RE.sub("", text))


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


def _esc(text: str) -> str:
    return html_mod.escape(text, quote=True)


def _payload_hash(payload: dict) -> str:
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in sorted(obj.items()) if not (k.startswith("_") or k == "sha256")}
        if isinstance(obj, list):
            return [clean(v) for v in obj]
        return obj
    canonical = json.dumps(clean(payload), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _section_html(s: dict, anchor: str) -> str:
    t = s["type"]
    if t == "narrative":
        return (f'<section class="narrative" id="{anchor}"><h2>{_esc(s["heading"])}</h2>'
                f'{md_to_html(s["md"])}</section>')
    if t == "diagram":
        links = _esc(json.dumps(s.get("links", {})))
        return (f'<section class="diagram" id="{anchor}"><h2>{_esc(s["heading"])}</h2>'
                f'<div class="mermaid-wrap" data-links="{links}">'
                f'<pre class="mermaid">{_esc(s["mermaid"])}</pre></div></section>')
    if t == "decision":
        alts = ""
        if s.get("alternatives"):
            items = "".join(f"<li>{_esc(a)}</li>" for a in s["alternatives"])
            alts = f'<div class="alts"><h4>Alternatives considered</h4><ul>{items}</ul></div>'
        return (f'<section class="card decision rc-{s["reversal_cost"]}" id="{s["id"]}" '
                f'data-card-id="{s["id"]}" data-card-title="{_esc(s["title"])}">'
                f'<h3>{_esc(s["title"])}</h3>'
                f'<span class="tags">{s["provenance"]} - reversal cost: {s["reversal_cost"]}</span>'
                f'{md_to_html(s["md"])}{alts}<div class="respond"></div></section>')
    if t == "hunk":
        return (f'<section class="hunk" id="{anchor}">'
                f'<div class="hunk-meta"><code>{_esc(s["file"])}:{s["lines"]} @ {_esc(s["ref"])}</code>'
                f' <span data-sha="{s["_sha256"]}"></span></div>'
                f'<div class="hunk-body"><div class="annotation">{md_to_html(s["md"])}</div>'
                f'<div class="code">{highlight_code(s["_code"], s["file"])}</div></div></section>')
    if t == "comparison":
        return (f'<section id="{anchor}"><h2>{_esc(s["heading"])}</h2><div class="comparison">'
                f'<div><h4>Before</h4>{md_to_html(s["before_md"])}</div>'
                f'<div><h4>After</h4>{md_to_html(s["after_md"])}</div></div></section>')
    if t == "question":
        return (f'<section class="card question" id="{s["id"]}" data-card-id="{s["id"]}" '
                f'data-card-title="open question"><h3>Open question</h3>'
                f'{md_to_html(s["md"])}<div class="respond"></div></section>')
    if t == "fallout":
        items = "".join(f"<li>{_esc(i)}</li>" for i in s["items"])
        heading = _esc(s.get("heading", "Mechanical fallout"))
        return (f'<section id="{anchor}"><details class="fallout">'
                f'<summary>{heading} ({len(s["items"])} items)</summary><ul>{items}</ul>'
                f'</details></section>')
    raise PayloadError(f"unknown section type: {t}")


def render_html(payload: dict) -> str:
    sections_html, toc = [], []
    for i, s in enumerate(payload["sections"], 1):
        anchor = s.get("id", f"s{i}")
        sections_html.append(_section_html(s, anchor))
        label = s.get("heading") or s.get("title") or s.get("id") or s["type"]
        if s["type"] != "fallout":
            toc.append(f'<a href="#{anchor}">{_esc(label)}</a>')

    has_diagram = any(s["type"] == "diagram" for s in payload["sections"])
    mermaid_tag = ""
    if has_diagram:
        if not MERMAID_PATH.is_file():
            raise PayloadError(
                f"payload has diagrams but {MERMAID_PATH} is missing; "
                "vendor mermaid.min.js into assets/"
            )
        mermaid_tag = f"<script>{MERMAID_PATH.read_text()}</script>"

    page = TEMPLATE_PATH.read_text()
    for token, value in {
        "{{TITLE}}": _esc(payload["title"]),
        "{{VERDICT}}": _esc(payload["verdict"]),
        "{{MODE}}": payload["mode"],
        "{{MODE_LABEL}}": MODE_LABELS[payload["mode"]],
        "{{DIFF}}": _esc(payload["diff"]),
        "{{TOC}}": " ".join(toc),
        "{{SECTIONS}}": "\n".join(sections_html),
        "{{PYGMENTS_CSS}}": HtmlFormatter(cssclass="highlight").get_style_defs(".highlight"),
        "{{PAYLOAD_HASH}}": _payload_hash(payload),
        "{{MERMAID}}": mermaid_tag,
    }.items():
        page = page.replace(token, value)
    return page


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
        if args.write_hashes and any(s["type"] == "hunk" for s in payload["sections"]):
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
