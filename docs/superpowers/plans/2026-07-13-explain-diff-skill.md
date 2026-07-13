# explain-diff Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `explain-diff` skill: a JSON+markdown payload authored by the agent, rendered by a zero-token build script into a self-contained interactive HTML guide (or plain markdown) that explains a diff's intent, load-bearing decisions, and open questions.

**Architecture:** Three artifacts: `schema.json` (payload contract), `render.py` (uv single-file script that validates, extracts hunks from git, and renders html/md from a static template), and `assets/template.html` (all CSS/JS written once: feedback composer, interactive Mermaid diagrams, print styles). `SKILL.md` teaches the analysis method and payload authoring.

**Tech Stack:** Python 3.11+ via `uv run` single-file script; deps `jsonschema`, `markdown-it-py`, `pygments`; vendored `mermaid.min.js` (pinned 11.4.1); pytest for tests.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-13-explain-diff-skill-design.md` — plan implements it fully.
- **No emojis anywhere**: not in template, rendered pages, SKILL.md, code, or commit messages. Composer buttons are plain text: `Approve` / `Discuss` / `Change`.
- Rendered HTML must be **self-contained**: no external URLs (`http://`/`https://`) in the output page.
- `render.py` must **fail loudly** with actionable messages (exit code 1, message on stderr) — never render a page missing requested content.
- Mermaid runtime is inlined **only when the payload contains a `diagram` section**.
- All commands below run from `/Users/adama/workspace/grimore/explain-diff/` unless stated otherwise.
- Test command (used in every task): `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests -v`

---

### Task 1: Scaffold, payload schema, and validation

**Files:**
- Create: `explain-diff/schema.json`
- Create: `explain-diff/render.py`
- Create: `explain-diff/tests/conftest.py`
- Test: `explain-diff/tests/test_validation.py`
- Modify: `.gitignore` (repo root)

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `PayloadError(Exception)`; `load_payload(path: Path) -> dict` — parses JSON, validates against `schema.json`, checks unique `id`s across decision/question sections and that every diagram `links` value targets `#<existing id>`. Raises `PayloadError` with a human-actionable message on any failure.

- [ ] **Step 1: Scaffold and gitignore**

```bash
mkdir -p explain-diff/tests explain-diff/assets explain-diff/examples
printf '__pycache__/\n.pytest_cache/\n' >> .gitignore
```

- [ ] **Step 2: Write schema.json**

Create `explain-diff/schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "explain-diff payload",
  "type": "object",
  "required": ["title", "verdict", "mode", "diff", "sections"],
  "additionalProperties": false,
  "properties": {
    "title": { "type": "string", "minLength": 1 },
    "verdict": { "type": "string", "minLength": 1 },
    "mode": { "enum": ["warm", "cold"] },
    "diff": { "type": "string", "minLength": 1, "description": "Git range (e.g. 'main...HEAD') or 'WORKTREE'" },
    "sections": {
      "type": "array",
      "minItems": 1,
      "items": {
        "oneOf": [
          { "$ref": "#/$defs/narrative" },
          { "$ref": "#/$defs/diagram" },
          { "$ref": "#/$defs/decision" },
          { "$ref": "#/$defs/hunk" },
          { "$ref": "#/$defs/comparison" },
          { "$ref": "#/$defs/question" },
          { "$ref": "#/$defs/fallout" }
        ]
      }
    }
  },
  "$defs": {
    "md": { "type": "string", "minLength": 1 },
    "ident": { "type": "string", "pattern": "^[a-z][a-z0-9_-]*$" },
    "narrative": {
      "type": "object",
      "required": ["type", "heading", "md"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "narrative" },
        "heading": { "type": "string", "minLength": 1 },
        "md": { "$ref": "#/$defs/md" }
      }
    },
    "diagram": {
      "type": "object",
      "required": ["type", "heading", "mermaid"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "diagram" },
        "heading": { "type": "string", "minLength": 1 },
        "mermaid": { "type": "string", "minLength": 1 },
        "links": {
          "type": "object",
          "additionalProperties": { "type": "string", "pattern": "^#" }
        }
      }
    },
    "decision": {
      "type": "object",
      "required": ["type", "id", "title", "provenance", "reversal_cost", "md"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "decision" },
        "id": { "$ref": "#/$defs/ident" },
        "title": { "type": "string", "minLength": 1 },
        "provenance": { "enum": ["stated", "inferred"] },
        "reversal_cost": { "enum": ["low", "medium", "high"] },
        "md": { "$ref": "#/$defs/md" },
        "alternatives": { "type": "array", "items": { "type": "string" } }
      }
    },
    "hunk": {
      "type": "object",
      "required": ["type", "file", "lines", "ref", "md"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "hunk" },
        "file": { "type": "string", "minLength": 1 },
        "lines": { "type": "string", "pattern": "^[0-9]+-[0-9]+$" },
        "ref": { "type": "string", "minLength": 1, "description": "git ref, or WORKTREE for on-disk state" },
        "md": { "$ref": "#/$defs/md" },
        "sha256": { "type": "string" }
      }
    },
    "comparison": {
      "type": "object",
      "required": ["type", "heading", "before_md", "after_md"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "comparison" },
        "heading": { "type": "string", "minLength": 1 },
        "before_md": { "$ref": "#/$defs/md" },
        "after_md": { "$ref": "#/$defs/md" }
      }
    },
    "question": {
      "type": "object",
      "required": ["type", "id", "md"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "question" },
        "id": { "$ref": "#/$defs/ident" },
        "md": { "$ref": "#/$defs/md" }
      }
    },
    "fallout": {
      "type": "object",
      "required": ["type", "items"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "fallout" },
        "heading": { "type": "string" },
        "items": { "type": "array", "minItems": 1, "items": { "type": "string" } }
      }
    }
  }
}
```

- [ ] **Step 3: Write conftest.py**

Create `explain-diff/tests/conftest.py` (makes `import render` work from tests):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
```

- [ ] **Step 4: Write the failing tests**

Create `explain-diff/tests/test_validation.py`:

```python
import json

import pytest

from render import PayloadError, load_payload


def minimal_payload() -> dict:
    return {
        "title": "T",
        "verdict": "V",
        "mode": "warm",
        "diff": "WORKTREE",
        "sections": [{"type": "narrative", "heading": "H", "md": "body"}],
    }


def write(tmp_path, payload):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps(payload))
    return p


def test_valid_minimal_payload_loads(tmp_path):
    payload = load_payload(write(tmp_path, minimal_payload()))
    assert payload["title"] == "T"


def test_missing_verdict_rejected(tmp_path):
    bad = minimal_payload()
    del bad["verdict"]
    with pytest.raises(PayloadError, match="verdict"):
        load_payload(write(tmp_path, bad))


def test_duplicate_ids_rejected(tmp_path):
    bad = minimal_payload()
    bad["sections"] += [
        {"type": "question", "id": "q1", "md": "a?"},
        {"type": "question", "id": "q1", "md": "b?"},
    ]
    with pytest.raises(PayloadError, match="duplicate"):
        load_payload(write(tmp_path, bad))


def test_dangling_diagram_link_rejected(tmp_path):
    bad = minimal_payload()
    bad["sections"].append(
        {"type": "diagram", "heading": "D", "mermaid": "flowchart LR\n  A --> B",
         "links": {"A": "#nope"}}
    )
    with pytest.raises(PayloadError, match="nope"):
        load_payload(write(tmp_path, bad))


def test_unknown_section_type_rejected(tmp_path):
    bad = minimal_payload()
    bad["sections"].append({"type": "sparkles", "md": "x"})
    with pytest.raises(PayloadError):
        load_payload(write(tmp_path, bad))
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests -v`
Expected: collection error — `ModuleNotFoundError: No module named 'render'` (or ImportError for `PayloadError`).

- [ ] **Step 6: Write render.py with load_payload**

Create `explain-diff/render.py`:

```python
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
```

Note: `jsonschema` reports a missing required property with the property name in the message (e.g. `'verdict' is a required property`), which satisfies the `match="verdict"` test.

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests -v`
Expected: 5 passed.

- [ ] **Step 8: Commit**

```bash
git add .gitignore explain-diff/schema.json explain-diff/render.py explain-diff/tests
git commit -m "feat(explain-diff): payload schema and validation"
```

---

### Task 2: Hunk extraction and drift hashes

**Files:**
- Modify: `explain-diff/render.py` (append functions)
- Test: `explain-diff/tests/test_hunks.py`

**Interfaces:**
- Consumes: `PayloadError` from Task 1.
- Produces:
  - `extract_hunk(hunk: dict, repo_root: Path) -> tuple[str, str]` — returns `(code, sha256_16)` where code is lines `start..end` (1-based, inclusive) of `hunk["file"]` at `hunk["ref"]` (`"WORKTREE"` reads from disk; anything else via `git show ref:file`). Raises `PayloadError` if the file/ref/range does not resolve.
  - `resolve_hunks(payload: dict, repo_root: Path) -> list[str]` — mutates each hunk section, setting `"_code"` and `"_sha256"`; returns drift warnings (payload `sha256` present and different from computed).
  - `write_hashes(payload: dict, path: Path) -> None` — writes payload back to `path` with each hunk's `sha256` set from `_sha256`, underscore keys stripped, `indent=2`.

- [ ] **Step 1: Write the failing tests**

Create `explain-diff/tests/test_hunks.py`:

```python
import json
import subprocess

import pytest

from render import PayloadError, extract_hunk, resolve_hunks, write_hashes

FILE_BODY = "\n".join(f"line {n}" for n in range(1, 21)) + "\n"


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src.py").write_text(FILE_BODY)
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True, env=env)
    return tmp_path


def hunk(ref):
    return {"type": "hunk", "file": "src.py", "lines": "3-5", "ref": ref, "md": "note"}


def test_extract_from_worktree(repo):
    code, digest = extract_hunk(hunk("WORKTREE"), repo)
    assert code == "line 3\nline 4\nline 5"
    assert len(digest) == 16


def test_extract_from_ref(repo):
    (repo / "src.py").write_text("changed\n")
    code, _ = extract_hunk(hunk("HEAD"), repo)
    assert code == "line 3\nline 4\nline 5"


def test_missing_file_raises(repo):
    bad = hunk("WORKTREE") | {"file": "nope.py"}
    with pytest.raises(PayloadError, match="nope.py"):
        extract_hunk(bad, repo)


def test_out_of_range_raises(repo):
    bad = hunk("WORKTREE") | {"lines": "900-910"}
    with pytest.raises(PayloadError, match="900"):
        extract_hunk(bad, repo)


def test_resolve_warns_on_drift(repo):
    h = hunk("WORKTREE") | {"sha256": "not-the-real-hash"}
    payload = {"sections": [h]}
    warnings = resolve_hunks(payload, repo)
    assert len(warnings) == 1 and "drift" in warnings[0]
    assert h["_code"].startswith("line 3")


def test_write_hashes_round_trip(repo, tmp_path):
    payload = {"sections": [hunk("WORKTREE")]}
    resolve_hunks(payload, repo)
    out = tmp_path / "p.json"
    write_hashes(payload, out)
    saved = json.loads(out.read_text())
    h = saved["sections"][0]
    assert h["sha256"] == payload["sections"][0]["_sha256"]
    assert not any(k.startswith("_") for k in h)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests/test_hunks.py -v`
Expected: ImportError — `extract_hunk` not defined.

- [ ] **Step 3: Implement**

Append to `explain-diff/render.py` (add `import hashlib`, `import subprocess` to the imports):

```python
def extract_hunk(hunk: dict, repo_root: Path) -> tuple[str, str]:
    start, end = (int(n) for n in hunk["lines"].split("-"))
    where = f"{hunk['file']}:{hunk['lines']} @ {hunk['ref']}"
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
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add explain-diff/render.py explain-diff/tests/test_hunks.py
git commit -m "feat(explain-diff): hunk extraction from git with drift hashes"
```

---

### Task 3: Mermaid sanity check, markdown and highlight helpers

**Files:**
- Modify: `explain-diff/render.py` (append functions; hook mermaid check into `load_payload`)
- Test: `explain-diff/tests/test_helpers.py`

**Interfaces:**
- Consumes: `PayloadError`, `load_payload` from Task 1.
- Produces:
  - `check_mermaid(src: str) -> None` — raises `PayloadError` unless the first non-empty line starts with a known diagram type. Called by `load_payload` for every diagram section.
  - `md_to_html(text: str) -> str` — CommonMark to HTML via markdown-it-py.
  - `highlight_code(code: str, filename: str) -> str` — Pygments HTML (`cssclass="highlight"`), lexer guessed from filename, falling back to plain text.

- [ ] **Step 1: Write the failing tests**

Create `explain-diff/tests/test_helpers.py`:

```python
import pytest

from render import PayloadError, check_mermaid, highlight_code, md_to_html


def test_known_mermaid_type_passes():
    check_mermaid("flowchart LR\n  A --> B")
    check_mermaid("\n  sequenceDiagram\n  A->>B: hi")


def test_unknown_mermaid_type_rejected():
    with pytest.raises(PayloadError, match="diagram type"):
        check_mermaid("banana LR\n  A --> B")


def test_empty_mermaid_rejected():
    with pytest.raises(PayloadError):
        check_mermaid("   \n  ")


def test_md_to_html_renders_emphasis_and_code():
    html = md_to_html("uses `outbox` and **must** dedup")
    assert "<code>outbox</code>" in html and "<strong>must</strong>" in html


def test_highlight_python():
    html = highlight_code("def f():\n    return 1", "src/thing.py")
    assert 'class="highlight"' in html and "def" in html


def test_highlight_unknown_extension_falls_back():
    html = highlight_code("plain text", "notes.xyzzy")
    assert 'class="highlight"' in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests/test_helpers.py -v`
Expected: ImportError — `check_mermaid` not defined.

- [ ] **Step 3: Implement**

Append to `explain-diff/render.py` (add imports: `from markdown_it import MarkdownIt`, `from pygments import highlight as pygments_highlight`, `from pygments.formatters import HtmlFormatter`, `from pygments.lexers import TextLexer, get_lexer_for_filename`, `from pygments.util import ClassNotFound`):

```python
MERMAID_TYPES = (
    "flowchart", "graph", "sequenceDiagram", "stateDiagram", "classDiagram",
    "erDiagram", "gantt", "pie", "mindmap", "timeline", "journey",
)
_MD = MarkdownIt("commonmark").enable("table")


def check_mermaid(src: str) -> None:
    first = next((line.strip() for line in src.splitlines() if line.strip()), "")
    if not first.startswith(MERMAID_TYPES):
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
```

Then hook the mermaid check into `load_payload` — inside its final `for s in payload["sections"]:` loop, before the links check, add:

```python
        if s["type"] == "diagram":
            check_mermaid(s["mermaid"])
```

(The existing links check stays; both run under the same `if s["type"] == "diagram":` branch — merge them into one branch.)

- [ ] **Step 4: Run all tests to verify they pass**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests -v`
Expected: 17 passed. (Existing `test_dangling_diagram_link_rejected` still passes because its mermaid source `flowchart LR...` is valid.)

- [ ] **Step 5: Commit**

```bash
git add explain-diff/render.py explain-diff/tests/test_helpers.py
git commit -m "feat(explain-diff): mermaid sanity check, markdown and highlight helpers"
```

---

### Task 4: Markdown renderer and CLI

**Files:**
- Modify: `explain-diff/render.py` (append `render_md`, `main`)
- Test: `explain-diff/tests/test_render_md.py`

**Interfaces:**
- Consumes: `load_payload`, `resolve_hunks`, `write_hashes` from Tasks 1-2.
- Produces:
  - `render_md(payload: dict) -> str` — payload (hunks already resolved, `_code` present) to plain markdown. Diagrams become fenced ` ```mermaid ` blocks; hunks become fenced code blocks with a `file:lines @ref` header line; questions become a `- [ ]` checklist under "Open questions"; composer is omitted.
  - `main(argv: list[str] | None = None) -> int` — CLI: `render.py PAYLOAD [--format html|md] [--out PATH] [--open] [--write-hashes] [--repo PATH]`. Default format `html`, default repo `.`, default out = payload path with format suffix. Prints drift warnings to stderr prefixed `WARNING:`. On `PayloadError`, prints `error: <msg>` to stderr, returns 1. Task 4 implements the `md` path; `html` raises `PayloadError("html renderer not built yet")` until Task 5 replaces it.
  - Module tail: `if __name__ == "__main__": sys.exit(main())`

- [ ] **Step 1: Write the failing tests**

Create `explain-diff/tests/test_render_md.py`:

```python
import json
import subprocess

import pytest

from render import main, render_md


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src.py").write_text("\n".join(f"line {n}" for n in range(1, 21)) + "\n")
    return tmp_path


def full_payload():
    return {
        "title": "Retry queue",
        "verdict": "Delivery is now at-least-once",
        "mode": "warm",
        "diff": "WORKTREE",
        "sections": [
            {"type": "narrative", "heading": "What changed", "md": "Webhooks now enqueue."},
            {"type": "diagram", "heading": "Path", "mermaid": "flowchart LR\n  A --> B"},
            {"type": "decision", "id": "d1", "title": "At-least-once", "provenance": "stated",
             "reversal_cost": "high", "md": "Dedup on receiver.", "alternatives": ["exactly-once"]},
            {"type": "hunk", "file": "src.py", "lines": "3-5", "ref": "WORKTREE", "md": "The lease query."},
            {"type": "comparison", "heading": "Send path", "before_md": "inline send", "after_md": "outbox worker"},
            {"type": "question", "id": "q1", "md": "Cap retries at 24h?"},
            {"type": "fallout", "items": ["renamed sender.py", "import shuffles"]},
        ],
    }


def test_render_md_structure(repo):
    payload = full_payload()
    from render import resolve_hunks
    resolve_hunks(payload, repo)
    md = render_md(payload)
    assert md.startswith("# Retry queue")
    assert "> Delivery is now at-least-once" in md
    assert "```mermaid" in md
    assert "line 3" in md and "src.py:3-5 @ WORKTREE" in md
    assert "- [ ] **q1**: Cap retries at 24h?" in md
    assert "reversal cost: high" in md and "stated" in md
    assert "Approve" not in md  # no composer in markdown target


def test_cli_md_end_to_end(repo, tmp_path, capsys):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps(full_payload()))
    out = tmp_path / "guide.md"
    rc = main([str(p), "--format", "md", "--repo", str(repo), "--out", str(out)])
    assert rc == 0
    assert out.read_text().startswith("# Retry queue")


def test_cli_invalid_payload_fails_loudly(tmp_path, capsys):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps({"title": "x"}))
    rc = main([str(p), "--format", "md"])
    assert rc == 1
    assert "error:" in capsys.readouterr().err


def test_cli_write_hashes(repo, tmp_path):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps(full_payload()))
    rc = main([str(p), "--format", "md", "--repo", str(repo), "--out", str(tmp_path / "g.md"), "--write-hashes"])
    assert rc == 0
    assert json.loads(p.read_text())["sections"][3]["sha256"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests/test_render_md.py -v`
Expected: ImportError — `main` / `render_md` not defined.

- [ ] **Step 3: Implement**

Append to `explain-diff/render.py` (add imports: `import argparse`, `import sys`, `import webbrowser`):

```python
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
        if args.write_hashes:
            write_hashes(payload, args.payload)
        rendered = render_html(payload) if args.format == "html" else render_md(payload)
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
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests -v`
Expected: 21 passed.

- [ ] **Step 5: Commit**

```bash
git add explain-diff/render.py explain-diff/tests/test_render_md.py
git commit -m "feat(explain-diff): markdown renderer and CLI"
```

---

### Task 5: HTML template and HTML renderer

**Files:**
- Create: `explain-diff/assets/template.html`
- Modify: `explain-diff/render.py` (replace the `render_html` stub)
- Test: `explain-diff/tests/test_render_html.py`

**Interfaces:**
- Consumes: everything prior; `full_payload()` test fixture shape from Task 4.
- Produces: `render_html(payload: dict) -> str` — substitutes `{{TITLE}}`, `{{VERDICT}}`, `{{MODE}}` (css class `warm|cold`), `{{MODE_LABEL}}`, `{{DIFF}}`, `{{TOC}}`, `{{SECTIONS}}`, `{{PYGMENTS_CSS}}`, `{{PAYLOAD_HASH}}` (sha256-16 of canonical payload JSON, underscore keys excluded), `{{MERMAID}}` (inlined `<script>` with vendored mermaid source if any diagram section, else empty string) into `assets/template.html`. Raises `PayloadError` if a diagram exists but `assets/mermaid.min.js` is missing.

- [ ] **Step 1: Write the failing tests**

Create `explain-diff/tests/test_render_html.py`:

```python
import re
import subprocess

import pytest

from render import render_html, resolve_hunks
from test_render_md import full_payload


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src.py").write_text("\n".join(f"line {n}" for n in range(1, 21)) + "\n")
    return tmp_path


@pytest.fixture
def fake_mermaid(monkeypatch, tmp_path):
    js = tmp_path / "mermaid.min.js"
    js.write_text("/* fake mermaid runtime */")
    import render
    monkeypatch.setattr(render, "MERMAID_PATH", js)
    return js


def rendered(repo):
    payload = full_payload()
    resolve_hunks(payload, repo)
    return render_html(payload)


def test_no_placeholders_left(repo, fake_mermaid):
    html = rendered(repo)
    assert not re.search(r"\{\{[A-Z_]+\}\}", html)


def test_self_contained(repo, fake_mermaid):
    html = rendered(repo)
    assert "http://" not in html and "https://" not in html


def test_core_content_present(repo, fake_mermaid):
    html = rendered(repo)
    assert "Retry queue" in html and "at-least-once" in html.lower()
    assert 'id="d1"' in html and 'id="q1"' in html
    assert "line 3" in html                      # extracted hunk code
    assert "fake mermaid runtime" in html        # inlined because diagram present
    assert 'data-links=' in html                 # diagram interactivity hooks
    assert "Copy as prompt" in html              # composer
    assert "Approve" in html and "Discuss" in html and "Change" in html


def test_mermaid_omitted_without_diagrams(repo, fake_mermaid):
    payload = full_payload()
    payload["sections"] = [s for s in payload["sections"] if s["type"] != "diagram"]
    resolve_hunks(payload, repo)
    html = render_html(payload)
    assert "fake mermaid runtime" not in html


def test_no_emojis(repo, fake_mermaid):
    html = rendered(repo)
    assert not any(0x1F300 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF for c in html)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests/test_render_html.py -v`
Expected: FAIL — `render_html` raises `PayloadError("html renderer not built yet")`.

- [ ] **Step 3: Write the template**

Create `explain-diff/assets/template.html`:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
:root{
  --bg:#f7f7f5;--panel:#ffffff;--ink:#1a1a1a;--muted:#6b6b6b;--line:#e2e2dd;
  --accent:#2f6f4f;--low:#5e8c62;--medium:#b3831f;--high:#b3402f;--code-bg:#f0f0ec;
}
@media (prefers-color-scheme: dark){
  :root{--bg:#161618;--panel:#1f1f23;--ink:#e8e8e4;--muted:#9a9a94;--line:#33333a;
        --accent:#7bbf9a;--low:#8fbf94;--medium:#d9a94a;--high:#d97862;--code-bg:#26262c;}
}
*{box-sizing:border-box}
body{margin:0;font:16px/1.6 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);}
code,pre{font:13px/1.5 ui-monospace,"SF Mono",Menlo,monospace;}
code{background:var(--code-bg);padding:.1em .35em;border-radius:4px;}
pre code{background:none;padding:0;}
header.page{position:sticky;top:0;z-index:10;background:var(--panel);border-bottom:1px solid var(--line);padding:.9rem 1.5rem;}
header.page h1{margin:0;font-size:1.15rem;display:inline;}
header.page .verdict{margin:.25rem 0 0;font-size:.95rem;color:var(--muted);}
.badge{font-size:.7rem;letter-spacing:.05em;text-transform:uppercase;border:1px solid var(--line);
       border-radius:99px;padding:.15rem .6rem;margin-left:.6rem;vertical-align:middle;color:var(--muted);}
.badge.warm{border-color:var(--accent);color:var(--accent);}
.badge.cold{border-color:var(--medium);color:var(--medium);}
.diffref{font-size:.75rem;color:var(--muted);margin:.15rem 0 0;}
main,nav#toc{max-width:60rem;margin:0 auto;padding:0 1.5rem;}
nav#toc{padding-top:1rem;font-size:.85rem;color:var(--muted);}
nav#toc a{color:inherit;margin-right:1rem;}
section{margin:2rem auto;}
section h2{font-size:1.05rem;border-bottom:1px solid var(--line);padding-bottom:.3rem;}
.card{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--accent);
      border-radius:8px;padding:1rem 1.25rem;}
.card.rc-low{border-left-color:var(--low);}
.card.rc-medium{border-left-color:var(--medium);}
.card.rc-high{border-left-color:var(--high);}
.card h3{margin:0 0 .25rem;font-size:1rem;}
.card .tags{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;}
.card.hl-card{outline:2px solid var(--accent);}
.alts{font-size:.9rem;color:var(--muted);}
.hunk{background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden;}
.hunk-meta{padding:.4rem .9rem;border-bottom:1px solid var(--line);font-size:.8rem;color:var(--muted);}
.hunk-body{display:grid;grid-template-columns:minmax(14rem,1fr) 2fr;}
.hunk-body .annotation{padding:.75rem 1rem;border-right:1px solid var(--line);font-size:.92rem;}
.hunk-body .code{overflow-x:auto;background:var(--code-bg);}
.hunk-body .code pre{margin:0;padding:.75rem 1rem;}
@media (max-width:50rem){.hunk-body{grid-template-columns:1fr}.hunk-body .annotation{border-right:none;border-bottom:1px solid var(--line);}}
.comparison{display:grid;grid-template-columns:1fr 1fr;gap:1rem;}
.comparison>div{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:.75rem 1rem;}
.comparison h4{margin:.1rem 0 .4rem;font-size:.8rem;text-transform:uppercase;color:var(--muted);}
details.fallout{color:var(--muted);font-size:.9rem;}
.mermaid-wrap{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:1rem;overflow:hidden;}
.mermaid-wrap svg{max-width:100%;height:auto;touch-action:none;}
g.node.linked{cursor:pointer;}
g.node.linked rect,g.node.linked circle,g.node.linked polygon{stroke:var(--accent);stroke-width:2px;}
g.node.hl rect,g.node.hl circle,g.node.hl polygon{fill:var(--accent);fill-opacity:.25;}
.respond{margin-top:.75rem;border-top:1px dashed var(--line);padding-top:.6rem;}
.respond button{font:inherit;font-size:.8rem;padding:.25rem .8rem;margin-right:.4rem;border-radius:6px;
                border:1px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer;}
.respond button.active{border-color:var(--accent);background:var(--accent);color:var(--panel);}
.respond textarea{display:block;width:100%;margin-top:.5rem;font:inherit;font-size:.85rem;
                  background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:.4rem;}
footer#composer{position:sticky;bottom:0;background:var(--panel);border-top:1px solid var(--line);
                padding:.6rem 1.5rem;display:flex;justify-content:space-between;align-items:center;z-index:10;}
footer#composer button{font:inherit;font-size:.85rem;padding:.35rem 1rem;border-radius:6px;
                       border:1px solid var(--accent);background:var(--accent);color:var(--panel);cursor:pointer;}
#tally{font-size:.85rem;color:var(--muted);}
{{PYGMENTS_CSS}}
@media print{
  header.page{position:static;}
  nav#toc,footer#composer,.respond{display:none;}
  body{background:#fff;color:#000;}
  section{break-inside:avoid;}
}
</style>
</head>
<body data-payload-hash="{{PAYLOAD_HASH}}">
<header class="page">
  <h1>{{TITLE}}</h1><span class="badge {{MODE}}">{{MODE_LABEL}}</span>
  <p class="verdict">{{VERDICT}}</p>
  <p class="diffref">diff: <code>{{DIFF}}</code></p>
</header>
<nav id="toc">{{TOC}}</nav>
<main>
{{SECTIONS}}
</main>
<footer id="composer">
  <span id="tally">No responses yet</span>
  <button id="copy-prompt" type="button">Copy as prompt</button>
</footer>
{{MERMAID}}
<script>
(function(){
  "use strict";
  window.addEventListener("beforeprint", function () {
    document.querySelectorAll("details").forEach(function (d) { d.open = true; });
  });

  var HASH = document.body.dataset.payloadHash;
  var KEY = "explain-diff:" + HASH;
  var CHOICES = ["Approve", "Discuss", "Change"];
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { state = {}; }

  function save() { localStorage.setItem(KEY, JSON.stringify(state)); tally(); }

  function tally() {
    var n = Object.keys(state).filter(function (k) { return state[k].choice || state[k].note; }).length;
    var total = document.querySelectorAll("[data-card-id]").length;
    document.getElementById("tally").textContent = n + " of " + total + " responded";
  }

  document.querySelectorAll("[data-card-id]").forEach(function (card) {
    var id = card.dataset.cardId;
    var box = card.querySelector(".respond");
    state[id] = state[id] || {};
    CHOICES.forEach(function (choice) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = choice;
      if (state[id].choice === choice) b.classList.add("active");
      b.addEventListener("click", function () {
        state[id].choice = state[id].choice === choice ? null : choice;
        box.querySelectorAll("button").forEach(function (x) {
          x.classList.toggle("active", x.textContent === state[id].choice);
        });
        save();
      });
      box.appendChild(b);
    });
    var note = document.createElement("textarea");
    note.rows = 1;
    note.placeholder = "Optional note";
    note.value = state[id].note || "";
    note.addEventListener("input", function () { state[id].note = note.value; save(); });
    box.appendChild(note);
  });
  tally();

  document.getElementById("copy-prompt").addEventListener("click", function () {
    var lines = ["Re: \"" + document.title + "\" (explain-diff guide, payload " + HASH + ")"];
    document.querySelectorAll("[data-card-id]").forEach(function (card) {
      var id = card.dataset.cardId;
      var s = state[id] || {};
      if (!s.choice && !s.note) return;
      var label = card.dataset.cardTitle || id;
      var line = "- " + id + " (" + label + "): " + (s.choice || "note").toUpperCase();
      if (s.note) line += " - " + s.note;
      lines.push(line);
    });
    if (lines.length === 1) lines.push("(no responses recorded)");
    var text = lines.join("\n");
    navigator.clipboard.writeText(text).then(function () {
      var b = document.getElementById("copy-prompt");
      b.textContent = "Copied";
      setTimeout(function () { b.textContent = "Copy as prompt"; }, 1500);
    });
  });

  function wireDiagrams() {
    document.querySelectorAll(".mermaid-wrap").forEach(function (wrap) {
      var links = {};
      try { links = JSON.parse(wrap.dataset.links || "{}"); } catch (e) { links = {}; }
      var svg = wrap.querySelector("svg");
      if (!svg) return;
      Object.keys(links).forEach(function (label) {
        svg.querySelectorAll("g.node").forEach(function (node) {
          if (node.textContent.trim().indexOf(label) !== -1) {
            node.classList.add("linked");
            node.dataset.anchor = links[label];
            node.addEventListener("click", function () { location.hash = links[label]; });
          }
        });
      });
      panZoom(svg);
    });
    document.querySelectorAll("[data-card-id]").forEach(function (card) {
      card.addEventListener("mouseenter", function () { crossHl(card.dataset.cardId, true); });
      card.addEventListener("mouseleave", function () { crossHl(card.dataset.cardId, false); });
    });
  }

  function crossHl(id, on) {
    document.querySelectorAll('g.node[data-anchor="#' + id + '"]').forEach(function (n) {
      n.classList.toggle("hl", on);
    });
  }

  function panZoom(svg) {
    var vb = svg.viewBox.baseVal;
    if (!vb || !vb.width) return;
    var drag = null;
    svg.addEventListener("wheel", function (e) {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      var k = e.deltaY < 0 ? 0.9 : 1.1;
      vb.width *= k; vb.height *= k;
    }, { passive: false });
    svg.addEventListener("pointerdown", function (e) {
      drag = { x: e.clientX, y: e.clientY, vx: vb.x, vy: vb.y };
      svg.setPointerCapture(e.pointerId);
    });
    svg.addEventListener("pointermove", function (e) {
      if (!drag) return;
      var s = vb.width / svg.clientWidth;
      vb.x = drag.vx - (e.clientX - drag.x) * s;
      vb.y = drag.vy - (e.clientY - drag.y) * s;
    });
    svg.addEventListener("pointerup", function () { drag = null; });
  }

  if (window.mermaid) {
    mermaid.initialize({
      startOnLoad: false,
      theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default",
    });
    mermaid.run({ querySelector: ".mermaid" }).then(wireDiagrams);
  }
})();
</script>
</body>
</html>
```

- [ ] **Step 4: Implement render_html**

In `explain-diff/render.py`: add `import html as html_mod` to imports, add module constants next to `SCHEMA_PATH`:

```python
TEMPLATE_PATH = SKILL_DIR / "assets" / "template.html"
MERMAID_PATH = SKILL_DIR / "assets" / "mermaid.min.js"
```

Replace the `render_html` stub with:

```python
def _esc(text: str) -> str:
    return html_mod.escape(text, quote=True)


def _payload_hash(payload: dict) -> str:
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in sorted(obj.items()) if not k.startswith("_")}
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
```

- [ ] **Step 5: Run all tests to verify they pass**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests -v`
Expected: 26 passed.

- [ ] **Step 6: Commit**

```bash
git add explain-diff/assets/template.html explain-diff/render.py explain-diff/tests/test_render_html.py
git commit -m "feat(explain-diff): HTML template and renderer with composer and interactive diagrams"
```

---

### Task 6: Vendor Mermaid, example payload, end-to-end test

**Files:**
- Create: `explain-diff/assets/mermaid.min.js` (downloaded, pinned)
- Create: `explain-diff/examples/payload.example.json`
- Test: `explain-diff/tests/test_e2e.py`

**Interfaces:**
- Consumes: `main` from Task 4, `render_html` from Task 5.
- Produces: a committed vendored runtime and a canonical example payload used by tests and by SKILL.md as the authoring reference.

- [ ] **Step 1: Vendor mermaid (pinned 11.4.1)**

```bash
curl -fsSL https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js -o explain-diff/assets/mermaid.min.js
ls -lh explain-diff/assets/mermaid.min.js
```

Expected: file of roughly 2-3 MB. If the CDN is unreachable, stop and report — do not substitute an unpinned version.

- [ ] **Step 2: Write the example payload**

Create `explain-diff/examples/payload.example.json`. The hunk points at `render.py` itself (lines 1-12 at WORKTREE) so the example renders from a real repo without fixtures — run render from the `explain-diff/` directory:

```json
{
  "title": "Example: retry queue for webhook delivery",
  "verdict": "Webhook delivery moves from fire-and-forget to an at-least-once outbox worker.",
  "mode": "warm",
  "diff": "main...HEAD",
  "sections": [
    {
      "type": "narrative",
      "heading": "What changed",
      "md": "Webhooks now **enqueue** into an `outbox` table instead of firing inline during the request. A worker claims rows with a lease and delivers them, retrying on failure."
    },
    {
      "type": "diagram",
      "heading": "New delivery path",
      "mermaid": "flowchart LR\n  API[API handler] --> OB[(outbox table)]\n  OB --> W[worker]\n  W --> EP[endpoint]\n  W -->|failure| OB",
      "links": { "OB": "#d1", "W": "#q1" }
    },
    {
      "type": "decision",
      "id": "d1",
      "title": "At-least-once over exactly-once",
      "provenance": "stated",
      "reversal_cost": "high",
      "md": "Receivers must **dedup by event id**. Exactly-once would require distributed transactions between our DB and every receiver.",
      "alternatives": ["exactly-once via 2PC", "best-effort with no retries (status quo)"]
    },
    {
      "type": "hunk",
      "file": "render.py",
      "lines": "1-12",
      "ref": "WORKTREE",
      "md": "Example annotation: in a real guide this points at the load-bearing hunk and explains what makes it safe."
    },
    {
      "type": "comparison",
      "heading": "Send path",
      "before_md": "`send_webhook()` called inline; a slow endpoint stalls the request thread.",
      "after_md": "Request writes one row; the worker owns delivery, retries, and backoff."
    },
    {
      "type": "question",
      "id": "q1",
      "md": "Cap retries at 24h and dead-letter, or retry forever?"
    },
    {
      "type": "fallout",
      "items": ["renamed sender.py to outbox.py", "import updates in 6 call sites"]
    }
  ]
}
```

- [ ] **Step 3: Write the failing end-to-end test**

Create `explain-diff/tests/test_e2e.py`:

```python
import re
from pathlib import Path

from render import SKILL_DIR, main

EXAMPLE = SKILL_DIR / "examples" / "payload.example.json"


def test_example_renders_self_contained_html(tmp_path):
    out = tmp_path / "guide.html"
    rc = main([str(EXAMPLE), "--repo", str(SKILL_DIR), "--out", str(out)])
    assert rc == 0
    html = out.read_text()
    # No external-fetch vectors. Plain "https://" strings inside the vendored
    # mermaid bundle are fine; what matters is nothing is loaded from the network.
    for vector in ("<script src=", "<link ", "url(http", "@import"):
        assert vector not in html, f"external-fetch vector found: {vector}"
    assert not re.search(r"\{\{[A-Z_]+\}\}", html)
    assert "Copy as prompt" in html
    assert "mermaid" in html.lower()


def test_example_renders_markdown(tmp_path):
    out = tmp_path / "guide.md"
    rc = main([str(EXAMPLE), "--format", "md", "--repo", str(SKILL_DIR), "--out", str(out)])
    assert rc == 0
    assert out.read_text().startswith("# Example: retry queue")
```

- [ ] **Step 4: Run tests**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests/test_e2e.py -v`
Expected: PASS if steps 1-2 done correctly (this task's code was already built in Tasks 4-5; the failing state here is only before the assets exist).

- [ ] **Step 5: Manual smoke check**

```bash
cd explain-diff
uv run render.py examples/payload.example.json --repo . --out /tmp/explain-diff-smoke.html --open
```

Expected: browser opens; verify visually: header badge reads "live session"; diagram renders and node "outbox table" is clickable (jumps to decision d1); hovering the d1 card highlights the OB node; hunk shows highlighted code beside annotation; Approve/Discuss/Change buttons work; Copy as prompt puts structured text on the clipboard; print preview (Cmd+P) hides composer. Fix template regressions before committing.

- [ ] **Step 6: Commit**

```bash
git add explain-diff/assets/mermaid.min.js explain-diff/examples/payload.example.json explain-diff/tests/test_e2e.py
git commit -m "feat(explain-diff): vendored mermaid 11.4.1, example payload, e2e test"
```

---

### Task 7: SKILL.md and skill verification

**Files:**
- Create: `explain-diff/SKILL.md`

**Interfaces:**
- Consumes: the CLI contract from Task 4 (`render.py PAYLOAD [--format html|md] [--out] [--open] [--write-hashes] [--repo]`), the schema vocabulary from Task 1.
- Produces: the user-facing skill.

- [ ] **Step 1: Write SKILL.md**

Create `explain-diff/SKILL.md`:

````markdown
---
name: explain-diff
description: Turn a code diff into a rich, self-contained HTML guide (or plain markdown) that explains what changed, why, which design decisions are load-bearing, and what questions remain - so the human and the agent start the next iteration with shared understanding. Use when the user asks to explain a diff or change, walk through what was implemented, prepare a change walkthrough or PR explanation, or hand off a large change for review. Works on the current session's changes (warm) or any git range or PR (cold). Not a code review - this skill explains intent and implications, it does not judge or hunt for bugs.
---

# Explain a Diff

Produce an explanation guide for a change. You author a JSON payload (prose in
markdown); `render.py` does everything mechanical - validation, pulling hunk
code from git, diagrams, styling, interactivity - at zero token cost. Never
hand-write HTML. Never paste code into the payload; point at it.

## Pipeline

1. Resolve the diff and mode:
   - **warm**: the change was made in this session. Rationale comes from the
     conversation; label decisions `"provenance": "stated"`.
   - **cold**: an arbitrary range, branch, or PR (`gh pr checkout` first).
     Read the code, infer intent, and label decisions `"provenance": "inferred"`.
     Never present inferred rationale as stated.
2. Author `explanation.json` (see Authoring below). Put it in the scratch
   directory unless the user wants it kept.
3. Render and open:

   ```bash
   uv run <skill-dir>/render.py explanation.json --repo <repo-root> --open --write-hashes
   ```

   Markdown target (PR descriptions, docs): add `--format md`.
   The script fails loudly on schema violations, bad hunk refs, dangling ids,
   or malformed mermaid - fix the payload and re-run. A drift WARNING means
   the code changed since hashes were written; re-check your annotations.

## Analysis method

Build the explanation around intent, not files:

1. **Verdict first** - one sentence: what does the system do now that it
   did not do before. This is the `verdict` field; everything hangs off it.
2. **Group hunks into 2-5 moves** - e.g. "introduce outbox table", "reroute
   send path". Never walk file-by-file. Mechanical churn (renames, imports,
   lockfiles) goes in one `fallout` section, acknowledged and out of the way.
3. **Surface load-bearing decisions.** A decision is load-bearing if
   reversing it later would cost more than re-doing this diff, or if other
   parts of the change silently assume it. Each gets a `decision` section
   with `reversal_cost` and rejected `alternatives`.
4. **Implications** - what the reader's mental model must update: new
   invariants, changed edge behavior, operational consequences (migrations,
   config, perf). Use `narrative` or `comparison` sections.
5. **Open questions** - genuine decision points, each phrased so an answer
   unblocks the next loop. These become `question` sections and feed the
   page's feedback composer (the user clicks Approve/Discuss/Change and
   pastes the composed prompt back to you).

Caps: at most ~6 `hunk` sections - pick only load-bearing code; the guide is
a lens, not an archive. Use a `diagram` only when structure genuinely helps
(data flow, state machines, before/after topology) - wire `links` from node
names to decision/question ids so the diagram is clickable.

## Authoring the payload

Schema: `schema.json` (validated on render). Reference: `examples/payload.example.json`.

Section vocabulary:

| Type | Use for |
|---|---|
| `narrative` | Prose under a heading (markdown) |
| `diagram` | Mermaid source plus optional `links` {node label -> "#id"} |
| `decision` | Load-bearing choice: id, provenance, reversal_cost, alternatives |
| `hunk` | `{file, lines "N-M", ref}` - code is extracted by render.py. Use `"ref": "WORKTREE"` for uncommitted changes, a commit/branch otherwise |
| `comparison` | Before/after, two markdown columns |
| `question` | Open question with id |
| `fallout` | Collapsed list of mechanical changes |

Rules:
- Ids are lowercase (`d1`, `q1`, ...) and unique; diagram `links` must target them.
- No emojis anywhere in the payload.
- Always pass `--write-hashes` on first render so later re-renders detect drift.
- Line numbers in `hunk` refer to the file at `ref` (for WORKTREE: as on disk
  now). Verify with `sed -n 'START,ENDp' file` before authoring.

## Sizing

Small diff (< 100 lines): verdict, one narrative, 1-2 decisions or questions.
Skip diagrams. Medium: add hunks and a comparison. Large: full vocabulary,
but still 2-5 moves - if you need more, the change should have been split,
and saying so is part of the explanation.
````

- [ ] **Step 2: Verify skill quality per writing-skills**

Invoke `superpowers:writing-skills` and run its verification checklist against `explain-diff/SKILL.md` (description triggers correctly, instructions actionable, no contradictions with render.py's actual CLI). Fix findings inline.

- [ ] **Step 3: Full test suite one last time**

Run: `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests -v`
Expected: 28 passed.

- [ ] **Step 4: Commit**

```bash
git add explain-diff/SKILL.md
git commit -m "feat(explain-diff): SKILL.md with analysis method and authoring guide"
```

---

## Verification (whole feature)

1. `uv run --with pytest --with jsonschema --with markdown-it-py --with pygments python -m pytest tests -v` - all green.
2. Manual smoke (Task 6 Step 5) confirmed in a real browser: interactivity, composer, print view, dark mode (toggle OS theme).
3. Render this repo's own latest commit as a cold diff and eyeball the result:
   author a small payload against `HEAD~1..HEAD` - the dogfood test.
