# grim lint core (IAM-38) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `grim lint [--fix]` — a single-file, `uv run`-able Python linter for the doc-components store, pytest-TDD'd, with JSON output and exit codes for agent consumption.

**Architecture:** One file, `tools/grim.py`: config loader (`.grimore.toml` + defaults), frontmatter parser producing `Component` records, a `Store` loader, independent check functions each returning `Finding` lists, a `--fix` normalizer, and an argparse CLI that aggregates everything through `run_lint()`. Tests live in `tests/` and import `grim` directly (pytest `pythonpath` points at `tools/`).

**Tech Stack:** Python >= 3.11 (stdlib `tomllib`), PyYAML (the only third-party runtime dep, declared via PEP 723 inline metadata), pytest via uv dependency groups.

Spec: docs/superpowers/specs/2026-07-24-doc-components-design.md (Lifecycle rules, Tooling, Testing).
Requirements doc: doc-components/SCHEMA.md. Linear: IAM-38.

## Global Constraints

- `tools/grim.py` is a **single file**; runtime dependencies are **stdlib + PyYAML only**; it carries a PEP 723 `# /// script` header so `uv run tools/grim.py` works standalone.
- Python floor: `requires-python = ">=3.11"` (needed for `tomllib`).
- Branch: `aalbright/iam-38-grim-lint-core-tdd`. All work commits there.
- **Stage named paths only** — never `git add .`, `git add -A`, or `git add --all` in the grimore repo (a prior broad add swept junk into a commit). Inside throwaway test-fixture repos created under `tmp_path`, `git add -A` is fine.
- No emojis in any output, code, or docs.
- Test command: `uv run pytest -q` (uv syncs the `dev` dependency group by default). Per-test: `uv run pytest tests/<file>.py::<test> -v`.
- Out of scope (do NOT implement): `grim render` and `grim check` verbs (IAM-40), touched-path guard and `Grim-Waive` trailers (IAM-42), banner blocks / `implemented:` stamping (IAM-41), human exports (IAM-45). `--strict` on lint ships now as the fail-closed hook `check` will reuse.
- `doc-components/examples/` must lint clean by the end (Task 10).
- Reference files by path, never by commit SHA.

## Design decisions (local to this plan; spec left them open)

- **Escape marker syntax:** a line containing `<!-- grim:ok -->` is exempt from Avoid-term checks.
- **Avoid-term sources:** `_Avoid_:` lines in `status: current` term components only (live terms govern terminology). Bodies of `draft` and `current` components are scanned; `superseded` bodies are historic and skipped. `_Avoid_:` lines themselves are never scanned.
- **Unknown frontmatter fields are errors** (typo protection — a misspelled `supersedes:` silently ignored would be worse).
- **`--fix` only rewrites components that have no error findings** (never risks data loss on a file it does not fully understand).
- **Exit codes:** 0 = clean or warnings only; 1 = one or more errors; 2 = config/usage failure.
- **Deletion detection** rides the transition check: a component present at the merge-base but missing from the working tree is an error (components are never deleted).
- **New files** (absent at merge-base) may carry any status — a component can be born and abandoned within one branch.

## Finding codes (shared vocabulary, all tasks)

| Code | Level | Meaning |
|---|---|---|
| E001 | error | missing or unterminated frontmatter block |
| E002 | error | invalid YAML in frontmatter |
| E003 | error | frontmatter is not a mapping |
| E004 | error | component file not at `<components>/<type>/<slug>.md` depth |
| E005 | error | unknown component type directory |
| E010 | error | missing required frontmatter field(s) |
| E011 | error | unknown frontmatter field |
| E012 | error | `type` not an enabled component type |
| E013 | error | `type` does not match parent directory |
| E014 | error | invalid `status` |
| E015 | error | filename slug fails `[a-z0-9][a-z0-9-]*` |
| E016 | error | `id` != `<type>-<filename slug>` |
| E017 | error | `date` not a valid ISO `YYYY-MM-DD` |
| E018 | error | `paths:` on a type other than note/adr |
| E019 | error | field has wrong value type (supersedes/paths not str-lists, subsystem not str) |
| E020 | error | duplicate id |
| E030 | error | supersedes target missing from store (or self-supersede) |
| E031 | error | dual-live-successor conflict ("reconcile") |
| E040 | error | illegal status transition since merge-base |
| E041 | error | component deleted since merge-base |
| E042 | error | merge-base unresolvable under `--strict` (fail closed) |
| W042 | warning | merge-base unresolvable, best-effort skip (non-strict) |
| W043 | warning | could not read status at merge-base for one file; skipped |
| E050 | error | avoided term used in a component body |
| W060 | warning | plan missing `spec:` frontmatter |
| W061 | warning | `subsystem` on a non-note component (no effect) |

## File structure

- `pyproject.toml` — uv virtual project (`package = false`), pytest config, dev group.
- `tools/grim.py` — the whole tool (single file, ~450 lines when done).
- `tests/helpers.py` — `write_component()` fixture-builder shared by all test files.
- `tests/test_config.py`, `test_parsing.py`, `test_schema.py`, `test_ids_edges.py`, `test_transitions.py`, `test_avoid_terms.py`, `test_plans.py`, `test_fix.py`, `test_cli.py`, `test_examples.py` — one file per concern, added task by task.
- `doc-components/SCHEMA.md` — small amendment documenting the escape marker (Task 10).

---

### Task 1: Scaffolding + config loading

**Files:**
- Create: `pyproject.toml`
- Create: `tools/grim.py`
- Create: `tests/test_config.py`
- Modify: `.gitignore` (append `.venv/`)

**Interfaces:**
- Produces: `grim.COMPONENT_TYPES: tuple[str, ...]`, `grim.ConfigError(Exception)`, `grim.Config` dataclass (fields `root, components, current, specs, plans, default_branch: str, types: tuple[str, ...]` — path fields are `Path`), `grim.load_config(root: Path) -> Config`.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "grimore-tools"
version = "0.1.0"
description = "Tooling for the grimore doc-components system"
requires-python = ">=3.11"

[dependency-groups]
dev = ["pytest>=8", "pyyaml>=6"]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["tools"]
```

- [ ] **Step 2: Append `.venv/` to `.gitignore`** (one line; check it is not already there).

- [ ] **Step 3: Write the failing tests** — `tests/test_config.py`:

```python
from pathlib import Path

import pytest

import grim


def test_defaults(tmp_path):
    cfg = grim.load_config(tmp_path)
    assert cfg.root == tmp_path
    assert cfg.components == tmp_path / "docs" / "components"
    assert cfg.current == tmp_path / "docs" / "current"
    assert cfg.specs == tmp_path / "docs" / "specs"
    assert cfg.plans == tmp_path / "docs" / "plans"
    assert cfg.default_branch == "main"
    assert cfg.types == grim.COMPONENT_TYPES


def test_toml_overrides(tmp_path):
    (tmp_path / ".grimore.toml").write_text(
        '[grimore]\ncomponents = "store"\ndefault_branch = "trunk"\n'
        'types = ["adr", "term"]\n',
        encoding="utf-8",
    )
    cfg = grim.load_config(tmp_path)
    assert cfg.components == tmp_path / "store"
    assert cfg.default_branch == "trunk"
    assert cfg.types == ("adr", "term")


def test_invalid_toml_raises(tmp_path):
    (tmp_path / ".grimore.toml").write_text("not toml [", encoding="utf-8")
    with pytest.raises(grim.ConfigError):
        grim.load_config(tmp_path)


def test_unknown_component_type_raises(tmp_path):
    (tmp_path / ".grimore.toml").write_text(
        '[grimore]\ntypes = ["adr", "bogus"]\n', encoding="utf-8"
    )
    with pytest.raises(grim.ConfigError):
        grim.load_config(tmp_path)
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'grim'` (or collection error).

- [ ] **Step 5: Write the implementation** — create `tools/grim.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""grim - doc-components tooling. IAM-38 ships the lint verb.

Requirements doc: doc-components/SCHEMA.md.
Spec: docs/superpowers/specs/2026-07-24-doc-components-design.md.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

COMPONENT_TYPES = ("adr", "term", "usecase", "constraint", "nongoal", "note")
STATUSES = ("draft", "current", "superseded")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ESCAPE_MARKER = "<!-- grim:ok -->"
AVOID_LINE_RE = re.compile(r"^_Avoid_:\s*(.+?)\.?\s*$")
FIELD_ORDER = ("id", "type", "status", "supersedes", "subsystem", "paths", "date")
REQUIRED_FIELDS = ("id", "type", "status", "date")
PATHS_TYPES = {"note", "adr"}
LEGAL_TRANSITIONS = {
    ("draft", "current"),
    ("draft", "superseded"),
    ("current", "superseded"),
}

DEFAULTS = {
    "components": "docs/components",
    "current": "docs/current",
    "specs": "docs/specs",
    "plans": "docs/plans",
    "default_branch": "main",
}


class ConfigError(Exception):
    """Unusable .grimore.toml or config values."""


@dataclasses.dataclass
class Config:
    root: Path
    components: Path
    current: Path
    specs: Path
    plans: Path
    default_branch: str
    types: tuple[str, ...]


def load_config(root: Path) -> Config:
    raw: dict = {}
    cfg_path = root / ".grimore.toml"
    if cfg_path.is_file():
        try:
            raw = tomllib.loads(cfg_path.read_text(encoding="utf-8")).get("grimore", {})
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f".grimore.toml: {exc}") from None
    types = tuple(raw.get("types", COMPONENT_TYPES))
    unknown = set(types) - set(COMPONENT_TYPES)
    if unknown:
        raise ConfigError(f".grimore.toml: unknown component types: {sorted(unknown)}")
    return Config(
        root=root,
        components=root / raw.get("components", DEFAULTS["components"]),
        current=root / raw.get("current", DEFAULTS["current"]),
        specs=root / raw.get("specs", DEFAULTS["specs"]),
        plans=root / raw.get("plans", DEFAULTS["plans"]),
        default_branch=raw.get("default_branch", DEFAULTS["default_branch"]),
        types=types,
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tools/grim.py tests/test_config.py .gitignore
git commit -m "feat(grim): scaffolding + .grimore.toml config loading"
```

If uv generated a `uv.lock`, add it to the same commit (`git add uv.lock`).

---

### Task 2: Findings, Component model, frontmatter parsing

**Files:**
- Modify: `tools/grim.py`
- Create: `tests/helpers.py`
- Create: `tests/test_parsing.py`

**Interfaces:**
- Consumes: constants from Task 1.
- Produces: `grim.Finding` dataclass (`level: str, code: str, path: str, message: str, component: str | None = None`), `grim.error(...)`/`grim.warning(...)` constructors, `grim.Component` dataclass (`path: Path, rel: str, dir_type: str, fm: dict, body: str`; properties `cid`, `ctype`, `status`, `supersedes`), `grim.parse_component(path: Path, root: Path) -> tuple[Component | None, list[Finding]]`, `grim.FM_RE`.
- `tests/helpers.py` produces `write_component(root, ctype, slug, *, status="current", date="2026-07-24", body="Body text.", cid=None, extra=None, raw_fm=None) -> Path` used by every later test file.

- [ ] **Step 1: Write the shared fixture helper** — `tests/helpers.py`:

```python
from pathlib import Path


def write_component(
    root: Path,
    ctype: str,
    slug: str,
    *,
    status: str = "current",
    date: str = "2026-07-24",
    body: str = "Body text.",
    cid: str | None = None,
    extra: dict | None = None,
    raw_fm: str | None = None,
) -> Path:
    """Write a component file under root/docs/components/<ctype>/<slug>.md.

    raw_fm, when given, is used verbatim as the frontmatter (for malformed
    cases); otherwise a well-formed frontmatter is assembled.
    """
    d = root / "docs" / "components" / ctype
    d.mkdir(parents=True, exist_ok=True)
    if raw_fm is None:
        lines = [
            f"id: {cid or f'{ctype}-{slug}'}",
            f"type: {ctype}",
            f"status: {status}",
        ]
        for key, value in (extra or {}).items():
            lines.append(f"{key}: {value}")
        lines.append(f"date: {date}")
        raw_fm = "\n".join(lines)
    path = d / f"{slug}.md"
    path.write_text(f"---\n{raw_fm}\n---\n\n{body}\n", encoding="utf-8")
    return path
```

- [ ] **Step 2: Write the failing tests** — `tests/test_parsing.py`:

```python
import grim
from helpers import write_component


def parse(root, path):
    return grim.parse_component(path, root)


def test_valid_component_parses(tmp_path):
    p = write_component(tmp_path, "adr", "x")
    comp, findings = parse(tmp_path, p)
    assert findings == []
    assert comp.cid == "adr-x"
    assert comp.ctype == "adr"
    assert comp.status == "current"
    assert comp.dir_type == "adr"
    assert comp.rel == "docs/components/adr/x.md"
    assert comp.body.strip() == "Body text."
    assert comp.supersedes == []


def test_yaml_date_coerced_to_string(tmp_path):
    # PyYAML parses an unquoted ISO date as datetime.date; grim must coerce.
    p = write_component(tmp_path, "adr", "x")
    comp, _ = parse(tmp_path, p)
    assert comp.fm["date"] == "2026-07-24"
    assert isinstance(comp.fm["date"], str)


def test_missing_frontmatter_is_e001(tmp_path):
    d = tmp_path / "docs" / "components" / "adr"
    d.mkdir(parents=True)
    p = d / "x.md"
    p.write_text("just a body, no frontmatter\n", encoding="utf-8")
    comp, findings = parse(tmp_path, p)
    assert comp is None
    assert [f.code for f in findings] == ["E001"]


def test_unterminated_frontmatter_is_e001(tmp_path):
    d = tmp_path / "docs" / "components" / "adr"
    d.mkdir(parents=True)
    p = d / "x.md"
    p.write_text("---\nid: adr-x\n", encoding="utf-8")
    comp, findings = parse(tmp_path, p)
    assert comp is None
    assert [f.code for f in findings] == ["E001"]


def test_invalid_yaml_is_e002(tmp_path):
    p = write_component(tmp_path, "adr", "x", raw_fm="id: [unclosed")
    comp, findings = parse(tmp_path, p)
    assert comp is None
    assert [f.code for f in findings] == ["E002"]


def test_non_mapping_frontmatter_is_e003(tmp_path):
    p = write_component(tmp_path, "adr", "x", raw_fm="- just\n- a list")
    comp, findings = parse(tmp_path, p)
    assert comp is None
    assert [f.code for f in findings] == ["E003"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_parsing.py -v`
Expected: FAIL — `AttributeError: module 'grim' has no attribute 'parse_component'`.

- [ ] **Step 4: Write the implementation** — append to `tools/grim.py`:

```python
@dataclasses.dataclass
class Finding:
    level: str  # "error" or "warning"
    code: str
    path: str  # config-root-relative posix path ("." when store-wide)
    message: str
    component: str | None = None


def error(code: str, path: str, message: str, component: str | None = None) -> Finding:
    return Finding("error", code, path, message, component)


def warning(code: str, path: str, message: str, component: str | None = None) -> Finding:
    return Finding("warning", code, path, message, component)


@dataclasses.dataclass
class Component:
    path: Path  # absolute
    rel: str  # config-root-relative posix path
    dir_type: str  # parent directory name
    fm: dict
    body: str

    @property
    def cid(self):
        return self.fm.get("id")

    @property
    def ctype(self):
        return self.fm.get("type")

    @property
    def status(self):
        return self.fm.get("status")

    @property
    def supersedes(self) -> list:
        value = self.fm.get("supersedes")
        return value if isinstance(value, list) else []


FM_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)


def parse_component(path: Path, root: Path) -> tuple[Component | None, list[Finding]]:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return None, [error("E001", rel, "missing or unterminated frontmatter block")]
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        return None, [error("E002", rel, f"invalid YAML frontmatter: {exc}")]
    if not isinstance(fm, dict):
        return None, [error("E003", rel, "frontmatter is not a mapping")]
    if isinstance(fm.get("date"), datetime.date):
        fm["date"] = fm["date"].isoformat()
    return (
        Component(path=path, rel=rel, dir_type=path.parent.name, fm=fm, body=m.group(2)),
        [],
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_parsing.py -v`
Expected: 6 passed. Also run `uv run pytest -q` — everything green.

- [ ] **Step 6: Commit**

```bash
git add tools/grim.py tests/helpers.py tests/test_parsing.py
git commit -m "feat(grim): Finding/Component models + frontmatter parsing"
```

---

### Task 3: Store loading + per-component schema validation

**Files:**
- Modify: `tools/grim.py`
- Create: `tests/test_schema.py`

**Interfaces:**
- Consumes: `Config`, `Component`, `parse_component`, `Finding` constructors.
- Produces: `grim.Store` dataclass (`components: list[Component], findings: list[Finding]`), `grim.load_store(cfg: Config) -> Store`, `grim.check_schema(store: Store, cfg: Config) -> list[Finding]`.

- [ ] **Step 1: Write the failing tests** — `tests/test_schema.py`:

```python
import grim
from helpers import write_component


def schema_findings(root):
    cfg = grim.load_config(root)
    store = grim.load_store(cfg)
    return store.findings + grim.check_schema(store, cfg)


def codes(findings):
    return [f.code for f in findings]


def test_clean_component_no_findings(tmp_path):
    write_component(tmp_path, "note", "arch", extra={"subsystem": "store", "paths": "[src/]"})
    assert schema_findings(tmp_path) == []


def test_missing_components_dir_is_empty_store(tmp_path):
    assert schema_findings(tmp_path) == []


def test_file_at_store_root_is_e004(tmp_path):
    d = tmp_path / "docs" / "components"
    d.mkdir(parents=True)
    (d / "stray.md").write_text("---\nid: x\n---\n\nb\n", encoding="utf-8")
    assert codes(schema_findings(tmp_path)) == ["E004"]


def test_unknown_type_directory_is_e005(tmp_path):
    d = tmp_path / "docs" / "components" / "widget"
    d.mkdir(parents=True)
    (d / "x.md").write_text("---\nid: x\n---\n\nb\n", encoding="utf-8")
    assert codes(schema_findings(tmp_path)) == ["E005"]


def test_missing_required_fields_is_e010(tmp_path):
    write_component(tmp_path, "adr", "x", raw_fm="id: adr-x\ntype: adr")
    assert codes(schema_findings(tmp_path)) == ["E010"]


def test_unknown_field_is_e011(tmp_path):
    write_component(tmp_path, "adr", "x", extra={"superseds": "adr-y"})
    assert "E011" in codes(schema_findings(tmp_path))


def test_bad_type_value_is_e012(tmp_path):
    write_component(
        tmp_path, "adr", "x",
        raw_fm="id: adr-x\ntype: widget\nstatus: current\ndate: 2026-07-24",
    )
    found = codes(schema_findings(tmp_path))
    assert "E012" in found


def test_type_dir_mismatch_is_e013(tmp_path):
    write_component(
        tmp_path, "adr", "x",
        raw_fm="id: term-x\ntype: term\nstatus: current\ndate: 2026-07-24",
    )
    assert "E013" in codes(schema_findings(tmp_path))


def test_bad_status_is_e014(tmp_path):
    write_component(tmp_path, "adr", "x", status="live")
    assert "E014" in codes(schema_findings(tmp_path))


def test_bad_slug_is_e015(tmp_path):
    write_component(tmp_path, "adr", "Bad_Slug", cid="adr-Bad_Slug")
    assert "E015" in codes(schema_findings(tmp_path))


def test_id_filename_mismatch_is_e016(tmp_path):
    write_component(tmp_path, "adr", "x", cid="adr-other")
    assert "E016" in codes(schema_findings(tmp_path))


def test_invalid_calendar_date_is_e017(tmp_path):
    write_component(tmp_path, "adr", "x", date='"2026-13-40"')
    assert "E017" in codes(schema_findings(tmp_path))


def test_non_date_string_is_e017(tmp_path):
    write_component(tmp_path, "adr", "x", date="soon")
    assert "E017" in codes(schema_findings(tmp_path))


def test_paths_on_term_is_e018(tmp_path):
    write_component(tmp_path, "term", "x", extra={"paths": "[src/]"})
    assert "E018" in codes(schema_findings(tmp_path))


def test_scalar_supersedes_is_e019(tmp_path):
    write_component(tmp_path, "adr", "x", extra={"supersedes": "adr-old"})
    assert "E019" in codes(schema_findings(tmp_path))


def test_subsystem_on_adr_is_w061(tmp_path):
    write_component(tmp_path, "adr", "x", extra={"subsystem": "store"})
    findings = schema_findings(tmp_path)
    assert codes(findings) == ["W061"]
    assert findings[0].level == "warning"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_schema.py -v`
Expected: FAIL — `AttributeError: module 'grim' has no attribute 'load_store'`.

- [ ] **Step 3: Write the implementation** — append to `tools/grim.py`:

```python
@dataclasses.dataclass
class Store:
    components: list[Component]
    findings: list[Finding]


def load_store(cfg: Config) -> Store:
    components: list[Component] = []
    findings: list[Finding] = []
    if not cfg.components.is_dir():
        return Store(components, findings)
    for path in sorted(cfg.components.rglob("*.md")):
        rel = path.relative_to(cfg.root).as_posix()
        parent = path.parent
        if parent == cfg.components or parent.parent != cfg.components:
            findings.append(
                error("E004", rel, "component files must live at <components>/<type>/<slug>.md")
            )
            continue
        if parent.name not in cfg.types:
            findings.append(
                error("E005", rel, f"unknown component type directory {parent.name!r}")
            )
            continue
        comp, errs = parse_component(path, cfg.root)
        findings.extend(errs)
        if comp is not None:
            components.append(comp)
    return Store(components, findings)


def _valid_date(value: str) -> bool:
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def check_schema(store: Store, cfg: Config) -> list[Finding]:
    out: list[Finding] = []
    for c in store.components:
        rel, fm = c.rel, c.fm
        for key in fm:
            if key not in FIELD_ORDER:
                out.append(error("E011", rel, f"unknown frontmatter field {key!r}", c.cid))
        missing = [k for k in REQUIRED_FIELDS if k not in fm]
        if missing:
            out.append(
                error("E010", rel, f"missing required fields: {', '.join(missing)}", c.cid)
            )
            continue
        ctype, status, cid, date = fm["type"], fm["status"], fm["id"], fm["date"]
        if ctype not in cfg.types:
            out.append(
                error("E012", rel, f"type must be one of {list(cfg.types)}, got {ctype!r}", cid)
            )
        elif ctype != c.dir_type:
            out.append(
                error("E013", rel, f"type {ctype!r} does not match directory {c.dir_type!r}", cid)
            )
        if status not in STATUSES:
            out.append(
                error("E014", rel, f"status must be one of {list(STATUSES)}, got {status!r}", cid)
            )
        slug = c.path.stem
        if not SLUG_RE.fullmatch(slug):
            out.append(
                error("E015", rel, f"filename slug {slug!r} must match [a-z0-9][a-z0-9-]*", cid)
            )
        if isinstance(ctype, str):
            expected = f"{ctype}-{slug}"
            if cid != expected:
                out.append(
                    error("E016", rel, f"id must be {expected!r} (type + filename slug), got {cid!r}", cid)
                )
        if not (isinstance(date, str) and DATE_RE.fullmatch(date) and _valid_date(date)):
            out.append(
                error("E017", rel, f"date must be a valid ISO YYYY-MM-DD date, got {date!r}", cid)
            )
        if "paths" in fm and ctype not in PATHS_TYPES:
            out.append(error("E018", rel, "paths: is only allowed on note and adr components", cid))
        if "supersedes" in fm and not (
            isinstance(fm["supersedes"], list)
            and all(isinstance(x, str) for x in fm["supersedes"])
        ):
            out.append(error("E019", rel, "supersedes must be a list of component IDs", cid))
        if "paths" in fm and not (
            isinstance(fm["paths"], list) and all(isinstance(x, str) for x in fm["paths"])
        ):
            out.append(error("E019", rel, "paths must be a list of glob strings", cid))
        if "subsystem" in fm:
            if not isinstance(fm["subsystem"], str):
                out.append(error("E019", rel, "subsystem must be a string", cid))
            elif ctype != "note":
                out.append(
                    warning("W061", rel, "subsystem has no effect on non-note components", cid)
                )
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schema.py -v`
Expected: 16 passed. Then `uv run pytest -q` — all green.

- [ ] **Step 5: Commit**

```bash
git add tools/grim.py tests/test_schema.py
git commit -m "feat(grim): store loading + frontmatter schema validation"
```

---

### Task 4: ID uniqueness + supersede-edge integrity

**Files:**
- Modify: `tools/grim.py`
- Create: `tests/test_ids_edges.py`

**Interfaces:**
- Consumes: `Store`, `Component`, `Finding` constructors.
- Produces: `grim.check_ids(store: Store) -> list[Finding]`, `grim.check_edges(store: Store) -> list[Finding]`.

- [ ] **Step 1: Write the failing tests** — `tests/test_ids_edges.py`:

```python
import grim
from helpers import write_component


def load(root):
    return grim.load_store(grim.load_config(root))


def codes(findings):
    return [f.code for f in findings]


def test_duplicate_id_is_e020(tmp_path):
    # Same id declared in two files of different types.
    write_component(tmp_path, "adr", "x")
    write_component(
        tmp_path, "term", "y",
        raw_fm="id: adr-x\ntype: term\nstatus: current\ndate: 2026-07-24",
    )
    store = load(tmp_path)
    assert codes(grim.check_ids(store)) == ["E020"]


def test_unique_ids_are_clean(tmp_path):
    write_component(tmp_path, "adr", "x")
    write_component(tmp_path, "adr", "y")
    assert grim.check_ids(load(tmp_path)) == []


def test_missing_supersede_target_is_e030(tmp_path):
    write_component(tmp_path, "adr", "new", extra={"supersedes": "[adr-ghost]"})
    assert codes(grim.check_edges(load(tmp_path))) == ["E030"]


def test_self_supersede_is_e030(tmp_path):
    write_component(tmp_path, "adr", "x", extra={"supersedes": "[adr-x]"})
    assert codes(grim.check_edges(load(tmp_path))) == ["E030"]


def test_valid_edge_is_clean(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "new", extra={"supersedes": "[adr-old]"})
    assert grim.check_edges(load(tmp_path)) == []


def test_dual_live_successor_is_e031(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "left", status="current", extra={"supersedes": "[adr-old]"})
    write_component(tmp_path, "adr", "right", status="current", extra={"supersedes": "[adr-old]"})
    findings = grim.check_edges(load(tmp_path))
    assert codes(findings) == ["E031"]
    assert "adr-left" in findings[0].message and "adr-right" in findings[0].message


def test_draft_successor_does_not_count_as_live(tmp_path):
    write_component(tmp_path, "adr", "old", status="superseded")
    write_component(tmp_path, "adr", "left", status="current", extra={"supersedes": "[adr-old]"})
    write_component(tmp_path, "adr", "right", status="draft", extra={"supersedes": "[adr-old]"})
    assert grim.check_edges(load(tmp_path)) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ids_edges.py -v`
Expected: FAIL — `AttributeError: module 'grim' has no attribute 'check_ids'`.

- [ ] **Step 3: Write the implementation** — append to `tools/grim.py`:

```python
def check_ids(store: Store) -> list[Finding]:
    out: list[Finding] = []
    seen: dict[str, str] = {}
    for c in store.components:
        cid = c.cid
        if not isinstance(cid, str):
            continue
        if cid in seen:
            out.append(error("E020", c.rel, f"duplicate id {cid!r} (also in {seen[cid]})", cid))
        else:
            seen[cid] = c.rel
    return out


def check_edges(store: Store) -> list[Finding]:
    out: list[Finding] = []
    ids = {c.cid for c in store.components if isinstance(c.cid, str)}
    rel_by_id = {c.cid: c.rel for c in store.components if isinstance(c.cid, str)}
    live_successors: dict[str, list[str]] = {}
    for c in store.components:
        for target in c.supersedes:
            if not isinstance(target, str):
                continue  # E019 already reported by check_schema
            if target == c.cid:
                out.append(error("E030", c.rel, "component supersedes itself", c.cid))
                continue
            if target not in ids:
                out.append(
                    error("E030", c.rel, f"supersedes target {target!r} does not exist in the store", c.cid)
                )
                continue
            if c.status == "current":
                live_successors.setdefault(target, []).append(c.cid)
    for target, succs in sorted(live_successors.items()):
        if len(succs) >= 2:
            out.append(
                error(
                    "E031",
                    rel_by_id.get(target, "."),
                    f"{target!r} has {len(succs)} live successors ({', '.join(sorted(succs))}); reconcile which stands",
                    target,
                )
            )
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ids_edges.py -v`
Expected: 7 passed. Then `uv run pytest -q` — all green.

- [ ] **Step 5: Commit**

```bash
git add tools/grim.py tests/test_ids_edges.py
git commit -m "feat(grim): id uniqueness + supersede-edge integrity checks"
```

---

### Task 5: Transition check against the merge-base

**Files:**
- Modify: `tools/grim.py`
- Create: `tests/test_transitions.py`

**Interfaces:**
- Consumes: `Store`, `Config`, `FM_RE`, `LEGAL_TRANSITIONS`, `Finding` constructors.
- Produces: `grim.check_transitions(store: Store, cfg: Config, strict: bool) -> list[Finding]`, `grim._git(cfg: Config, *args) -> subprocess.CompletedProcess`.

Semantics (from spec "Lifecycle rules"): resolve `git merge-base HEAD <default_branch>`. Unresolvable (not a repo, no commits, unknown branch): `strict=True` -> single E042 error ("fail closed, fix CI: fetch-depth: 0"); `strict=False` -> single W042 warning and skip. When resolvable: (a) every `.md` under the components dir present at the merge-base but absent from the working tree is E041; (b) for each current component also present at the merge-base, old status -> new status must be identical or in `LEGAL_TRANSITIONS`, else E040; unreadable old status is W043 and skipped; files new since the merge-base are skipped (any initial status legal). A missing components dir returns [] only when git is also unresolvable; when the merge-base resolves, the deletion pass still runs, so a wholesale store deletion yields E041 per file (operator decision at final review, 2026-07-24; the reference code below predates it).

- [ ] **Step 1: Write the failing tests** — `tests/test_transitions.py`:

```python
import subprocess

import grim
from helpers import write_component


def git(root, *args):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def make_repo(root):
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")


def commit_all(root, msg):
    # Broad add is fine here: throwaway fixture repo under tmp_path.
    git(root, "add", "-A")
    git(root, "commit", "-m", msg)


def transitions(root, strict=False):
    cfg = grim.load_config(root)
    store = grim.load_store(cfg)
    return grim.check_transitions(store, cfg, strict)


def codes(findings):
    return [f.code for f in findings]


def test_promotion_is_legal(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x", status="draft")
    commit_all(tmp_path, "add draft")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(tmp_path, "adr", "x", status="current")
    assert transitions(tmp_path) == []


def test_abandonment_is_legal(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x", status="draft")
    commit_all(tmp_path, "add draft")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(tmp_path, "adr", "x", status="superseded")
    assert transitions(tmp_path) == []


def test_resurrection_is_e040(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x", status="superseded")
    commit_all(tmp_path, "add superseded")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(tmp_path, "adr", "x", status="current")
    findings = transitions(tmp_path)
    assert codes(findings) == ["E040"]
    assert "'superseded' -> 'current'" in findings[0].message


def test_demotion_is_e040(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x", status="current")
    commit_all(tmp_path, "add current")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(tmp_path, "adr", "x", status="draft")
    assert codes(transitions(tmp_path)) == ["E040"]


def test_deletion_is_e041(tmp_path):
    make_repo(tmp_path)
    p = write_component(tmp_path, "adr", "x")
    commit_all(tmp_path, "add component")
    git(tmp_path, "checkout", "-b", "feature")
    p.unlink()
    assert codes(transitions(tmp_path)) == ["E041"]


def test_new_component_any_status_legal(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "x")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    write_component(tmp_path, "adr", "born-current", status="current")
    write_component(tmp_path, "adr", "born-draft", status="draft")
    assert transitions(tmp_path) == []


def test_no_repo_best_effort_is_w042(tmp_path):
    write_component(tmp_path, "adr", "x")
    findings = transitions(tmp_path, strict=False)
    assert codes(findings) == ["W042"]
    assert findings[0].level == "warning"


def test_no_repo_strict_is_e042(tmp_path):
    write_component(tmp_path, "adr", "x")
    findings = transitions(tmp_path, strict=True)
    assert codes(findings) == ["E042"]
    assert findings[0].level == "error"


def test_empty_store_skips_git_entirely(tmp_path):
    assert transitions(tmp_path, strict=True) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_transitions.py -v`
Expected: FAIL — `AttributeError: module 'grim' has no attribute 'check_transitions'`.

- [ ] **Step 3: Write the implementation** — append to `tools/grim.py`:

```python
def _git(cfg: Config, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cfg.root, capture_output=True, text=True
    )


def check_transitions(store: Store, cfg: Config, strict: bool) -> list[Finding]:
    out: list[Finding] = []
    if not cfg.components.is_dir():
        return out
    top = _git(cfg, "rev-parse", "--show-toplevel")
    mb = _git(cfg, "merge-base", "HEAD", cfg.default_branch)
    if top.returncode != 0 or mb.returncode != 0:
        if strict:
            return [
                error(
                    "E042",
                    ".",
                    f"cannot resolve git merge-base with {cfg.default_branch!r}; "
                    "failing closed (fix CI: fetch-depth: 0)",
                )
            ]
        return [
            warning(
                "W042",
                ".",
                f"cannot resolve git merge-base with {cfg.default_branch!r}; "
                "skipping transition check",
            )
        ]
    git_root = Path(top.stdout.strip()).resolve()
    base = mb.stdout.strip()
    comp_prefix = cfg.components.resolve().relative_to(git_root).as_posix()
    ls = _git(cfg, "ls-tree", "-r", "--name-only", base, "--", comp_prefix)
    old_paths = set(ls.stdout.split())
    by_git_rel = {
        c.path.resolve().relative_to(git_root).as_posix(): c for c in store.components
    }
    for old in sorted(old_paths):
        if old.endswith(".md") and old not in by_git_rel:
            out.append(error("E041", old, "component deleted; components are never deleted"))
    for git_rel, c in sorted(by_git_rel.items()):
        if git_rel not in old_paths:
            continue  # new on this branch; any initial status is legal
        show = _git(cfg, "show", f"{base}:{git_rel}")
        old_status = None
        if show.returncode == 0:
            m = FM_RE.match(show.stdout)
            if m:
                try:
                    old_fm = yaml.safe_load(m.group(1))
                except yaml.YAMLError:
                    old_fm = None
                if isinstance(old_fm, dict):
                    old_status = old_fm.get("status")
        if old_status is None:
            out.append(
                warning("W043", c.rel, "could not read status at merge-base; transition skipped", c.cid)
            )
            continue
        new_status = c.status
        if new_status == old_status or (old_status, new_status) in LEGAL_TRANSITIONS:
            continue
        out.append(
            error(
                "E040",
                c.rel,
                f"illegal status transition {old_status!r} -> {new_status!r} since merge-base",
                c.cid,
            )
        )
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_transitions.py -v`
Expected: 9 passed. Then `uv run pytest -q` — all green.

- [ ] **Step 5: Commit**

```bash
git add tools/grim.py tests/test_transitions.py
git commit -m "feat(grim): status-transition check vs merge-base, best-effort and strict"
```

---

### Task 6: Glossary Avoid-term check

**Files:**
- Modify: `tools/grim.py`
- Create: `tests/test_avoid_terms.py`

**Interfaces:**
- Consumes: `Store`, `AVOID_LINE_RE`, `ESCAPE_MARKER`, `Finding` constructors.
- Produces: `grim.check_avoid_terms(store: Store) -> list[Finding]`.

Semantics: collect avoided terms from `_Avoid_:` lines of `status: current` term components (comma-separated, trailing period stripped, case-insensitive). Scan every body line of every non-superseded component. A line is exempt when it is itself an `_Avoid_:` line or contains `<!-- grim:ok -->`. Matching is word-boundary (`(?<!\w)term(?!\w)`), case-insensitive; multi-word terms are matched as phrases.

- [ ] **Step 1: Write the failing tests** — `tests/test_avoid_terms.py`:

```python
import grim
from helpers import write_component

TERM_BODY = "**Component**: one documentation idea in one file.\n\n_Avoid_: fragment, doclet, entry."


def findings_for(root):
    store = grim.load_store(grim.load_config(root))
    return grim.check_avoid_terms(store)


def codes(findings):
    return [f.code for f in findings]


def test_avoided_term_in_body_is_e050(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    write_component(tmp_path, "note", "arch", body="Each doclet holds one idea.")
    findings = findings_for(tmp_path)
    assert codes(findings) == ["E050"]
    assert "doclet" in findings[0].message
    assert "term-component" in findings[0].message


def test_match_is_case_insensitive(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    write_component(tmp_path, "note", "arch", body="A Fragment of the docs.")
    assert codes(findings_for(tmp_path)) == ["E050"]


def test_word_boundary_no_substring_match(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    write_component(tmp_path, "note", "arch", body="Defragmentation and entryway are fine.")
    assert findings_for(tmp_path) == []


def test_escape_marker_exempts_line(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    write_component(
        tmp_path, "note", "arch",
        body="The old system called these entry records. <!-- grim:ok -->",
    )
    assert findings_for(tmp_path) == []


def test_own_avoid_line_not_flagged(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    assert findings_for(tmp_path) == []


def test_draft_term_does_not_govern(tmp_path):
    write_component(tmp_path, "term", "component", status="draft", body=TERM_BODY)
    write_component(tmp_path, "note", "arch", body="Each doclet holds one idea.")
    assert findings_for(tmp_path) == []


def test_superseded_bodies_not_scanned(tmp_path):
    write_component(tmp_path, "term", "component", body=TERM_BODY)
    write_component(
        tmp_path, "note", "arch", status="superseded", body="Each doclet holds one idea."
    )
    assert findings_for(tmp_path) == []


def test_multiword_term_matches_as_phrase(tmp_path):
    write_component(
        tmp_path, "term", "store",
        body="**Store**: the component tree.\n\n_Avoid_: data lake.",
    )
    write_component(tmp_path, "note", "arch", body="Dump it in the data lake.")
    findings = findings_for(tmp_path)
    assert codes(findings) == ["E050"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_avoid_terms.py -v`
Expected: FAIL — `AttributeError: module 'grim' has no attribute 'check_avoid_terms'`.

- [ ] **Step 3: Write the implementation** — append to `tools/grim.py`:

```python
def check_avoid_terms(store: Store) -> list[Finding]:
    out: list[Finding] = []
    avoid: dict[str, str] = {}  # lowercased term -> defining component id
    for c in store.components:
        if c.ctype == "term" and c.status == "current":
            for line in c.body.splitlines():
                m = AVOID_LINE_RE.match(line.strip())
                if m:
                    for raw_term in m.group(1).split(","):
                        term = raw_term.strip().rstrip(".").strip()
                        if term:
                            avoid.setdefault(term.lower(), c.cid)
    if not avoid:
        return out
    patterns = {
        term: re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)
        for term in avoid
    }
    for c in store.components:
        if c.status == "superseded":
            continue
        for lineno, line in enumerate(c.body.splitlines(), start=1):
            if AVOID_LINE_RE.match(line.strip()) or ESCAPE_MARKER in line:
                continue
            for term, pattern in patterns.items():
                if pattern.search(line):
                    out.append(
                        error(
                            "E050",
                            c.rel,
                            f"body line {lineno} uses avoided term {term!r} (defined by {avoid[term]}); "
                            f"append {ESCAPE_MARKER} to the line if the mention is deliberate",
                            c.cid,
                        )
                    )
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_avoid_terms.py -v`
Expected: 8 passed. Then `uv run pytest -q` — all green.

- [ ] **Step 5: Commit**

```bash
git add tools/grim.py tests/test_avoid_terms.py
git commit -m "feat(grim): glossary Avoid-term check with grim:ok escape marker"
```

---

### Task 7: Plans missing `spec:` warning

**Files:**
- Modify: `tools/grim.py`
- Create: `tests/test_plans.py`

**Interfaces:**
- Consumes: `Config`, `FM_RE`, `warning`.
- Produces: `grim.check_plans(cfg: Config) -> list[Finding]`.

- [ ] **Step 1: Write the failing tests** — `tests/test_plans.py`:

```python
import grim


def write_plan(root, name, text):
    d = root / "docs" / "plans"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def check(root):
    return grim.check_plans(grim.load_config(root))


def test_plan_with_spec_is_clean(tmp_path):
    write_plan(tmp_path, "a.md", "---\nspec: docs/specs/a.md\n---\n\n# Plan\n")
    assert check(tmp_path) == []


def test_plan_without_spec_is_w060(tmp_path):
    write_plan(tmp_path, "a.md", "---\ntitle: x\n---\n\n# Plan\n")
    findings = check(tmp_path)
    assert [f.code for f in findings] == ["W060"]
    assert findings[0].level == "warning"
    assert findings[0].path == "docs/plans/a.md"


def test_plan_with_no_frontmatter_is_w060(tmp_path):
    write_plan(tmp_path, "a.md", "# Plan without frontmatter\n")
    assert [f.code for f in check(tmp_path)] == ["W060"]


def test_missing_plans_dir_is_clean(tmp_path):
    assert check(tmp_path) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_plans.py -v`
Expected: FAIL — `AttributeError: module 'grim' has no attribute 'check_plans'`.

- [ ] **Step 3: Write the implementation** — append to `tools/grim.py`:

```python
def check_plans(cfg: Config) -> list[Finding]:
    out: list[Finding] = []
    if not cfg.plans.is_dir():
        return out
    for path in sorted(cfg.plans.rglob("*.md")):
        rel = path.relative_to(cfg.root).as_posix()
        m = FM_RE.match(path.read_text(encoding="utf-8"))
        has_spec = False
        if m:
            try:
                fm = yaml.safe_load(m.group(1))
            except yaml.YAMLError:
                fm = None
            has_spec = (
                isinstance(fm, dict)
                and isinstance(fm.get("spec"), str)
                and bool(fm["spec"].strip())
            )
        if not has_spec:
            out.append(warning("W060", rel, "plan is missing spec: frontmatter"))
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_plans.py -v`
Expected: 4 passed. Then `uv run pytest -q` — all green.

- [ ] **Step 5: Commit**

```bash
git add tools/grim.py tests/test_plans.py
git commit -m "feat(grim): warn on plans missing spec: frontmatter"
```

---

### Task 8: `--fix` formatting normalization

**Files:**
- Modify: `tools/grim.py`
- Create: `tests/test_fix.py`

**Interfaces:**
- Consumes: `Store`, `Component`, `FIELD_ORDER`, `Finding`.
- Produces: `grim.normalize_component(c: Component) -> str`, `grim.apply_fixes(store: Store, findings: list[Finding]) -> list[str]` (returns config-root-relative paths of rewritten files).

Normal form: `---`, known fields in `FIELD_ORDER` order (unknown fields never reach here — files with error findings are skipped), lists rendered flow-style `[a, b]`, `---`, exactly one blank line, body with leading/trailing blank lines stripped, single trailing newline. Idempotent.

- [ ] **Step 1: Write the failing tests** — `tests/test_fix.py`:

```python
import grim
from helpers import write_component


def fix(root):
    cfg = grim.load_config(root)
    store = grim.load_store(cfg)
    findings = store.findings + grim.check_schema(store, cfg)
    return grim.apply_fixes(store, findings), store


def test_reorders_fields_canonically(tmp_path):
    p = write_component(
        tmp_path, "adr", "x",
        raw_fm="status: current\ndate: 2026-07-24\nid: adr-x\ntype: adr",
    )
    fixed, _ = fix(tmp_path)
    assert fixed == ["docs/components/adr/x.md"]
    assert p.read_text(encoding="utf-8") == (
        "---\nid: adr-x\ntype: adr\nstatus: current\ndate: 2026-07-24\n---\n\nBody text.\n"
    )


def test_block_list_normalized_to_flow(tmp_path):
    p = write_component(
        tmp_path, "adr", "new",
        raw_fm=(
            "id: adr-new\ntype: adr\nstatus: current\n"
            "supersedes:\n  - adr-old\ndate: 2026-07-24"
        ),
    )
    write_component(tmp_path, "adr", "old", status="superseded")
    fix(tmp_path)
    assert "supersedes: [adr-old]" in p.read_text(encoding="utf-8")


def test_idempotent(tmp_path):
    write_component(
        tmp_path, "adr", "x",
        raw_fm="status: current\ndate: 2026-07-24\nid: adr-x\ntype: adr",
    )
    first, _ = fix(tmp_path)
    assert first == ["docs/components/adr/x.md"]
    second, _ = fix(tmp_path)
    assert second == []


def test_already_normal_untouched(tmp_path):
    write_component(tmp_path, "adr", "x")
    fixed, _ = fix(tmp_path)
    assert fixed == []


def test_files_with_errors_are_skipped(tmp_path):
    p = write_component(tmp_path, "adr", "x", extra={"mystery": "field"})
    before = p.read_text(encoding="utf-8")
    fixed, _ = fix(tmp_path)
    assert fixed == []
    assert p.read_text(encoding="utf-8") == before  # no data loss


def test_strips_trailing_blank_lines(tmp_path):
    p = write_component(tmp_path, "adr", "x", body="Body text.\n\n\n")
    fix(tmp_path)
    assert p.read_text(encoding="utf-8").endswith("Body text.\n")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_fix.py -v`
Expected: FAIL — `AttributeError: module 'grim' has no attribute 'apply_fixes'`.

- [ ] **Step 3: Write the implementation** — append to `tools/grim.py`:

```python
def _format_fm_value(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    return str(value)


def normalize_component(c: Component) -> str:
    lines = ["---"]
    for key in FIELD_ORDER:
        if key in c.fm:
            lines.append(f"{key}: {_format_fm_value(c.fm[key])}")
    lines.append("---")
    body = c.body.strip("\n")
    return "\n".join(lines) + "\n\n" + body + "\n"


def apply_fixes(store: Store, findings: list[Finding]) -> list[str]:
    fixed: list[str] = []
    error_rels = {f.path for f in findings if f.level == "error"}
    for c in store.components:
        if c.rel in error_rels:
            continue
        new_text = normalize_component(c)
        if new_text != c.path.read_text(encoding="utf-8"):
            c.path.write_text(new_text, encoding="utf-8")
            fixed.append(c.rel)
    return fixed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_fix.py -v`
Expected: 6 passed. Then `uv run pytest -q` — all green.

- [ ] **Step 5: Commit**

```bash
git add tools/grim.py tests/test_fix.py
git commit -m "feat(grim): --fix formatting normalization, idempotent and loss-safe"
```

---

### Task 9: `run_lint` aggregation + CLI (JSON output, exit codes)

**Files:**
- Modify: `tools/grim.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `grim.LintResult` dataclass (`findings: list[Finding], fixed: list[str]`; properties `errors`, `warnings`, `exit_code`; method `to_json() -> str`), `grim.run_lint(root: Path, *, fix: bool = False, strict: bool = False) -> LintResult`, `grim.main(argv: list[str] | None = None) -> int`, `if __name__ == "__main__"` guard.

Check order inside `run_lint`: store findings, schema, ids, edges, transitions, avoid-terms, plans; then fixes when `fix=True` (passing the accumulated findings so errored files are skipped).

JSON shape:

```json
{
  "ok": false,
  "errors": [{"level": "error", "code": "E016", "path": "docs/components/adr/x.md", "message": "...", "component": "adr-wrong"}],
  "warnings": [],
  "fixed": []
}
```

- [ ] **Step 1: Write the failing tests** — `tests/test_cli.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

import grim
from helpers import write_component

GRIM = Path(grim.__file__).resolve()


def run_cli(*args, cwd):
    return subprocess.run(
        [sys.executable, str(GRIM), *args], capture_output=True, text=True, cwd=cwd
    )


def test_run_lint_aggregates_all_checks(tmp_path):
    write_component(
        tmp_path, "term", "widget",
        body="**Widget**: a thing.\n\n_Avoid_: gizmo.",
    )
    write_component(tmp_path, "note", "arch", body="The gizmo layer does X.")
    result = grim.run_lint(tmp_path)
    assert any(f.code == "E050" for f in result.errors)
    assert result.exit_code == 1


def test_run_lint_fix_reports_fixed_files(tmp_path):
    write_component(
        tmp_path, "adr", "x",
        raw_fm="status: current\ndate: 2026-07-24\nid: adr-x\ntype: adr",
    )
    result = grim.run_lint(tmp_path, fix=True)
    assert result.fixed == ["docs/components/adr/x.md"]


def test_cli_clean_store_exits_zero_with_json(tmp_path):
    write_component(tmp_path, "adr", "x")
    r = run_cli("lint", "--json", "--root", str(tmp_path), cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["ok"] is True
    assert payload["errors"] == []
    # tmp_path is not a git repo: best-effort merge-base warning expected
    assert [w["code"] for w in payload["warnings"]] == ["W042"]


def test_cli_errors_exit_one(tmp_path):
    write_component(tmp_path, "adr", "x", cid="adr-wrong")
    r = run_cli("lint", "--json", "--root", str(tmp_path), cwd=tmp_path)
    assert r.returncode == 1
    payload = json.loads(r.stdout)
    assert payload["ok"] is False
    assert any(e["code"] == "E016" for e in payload["errors"])


def test_cli_strict_promotes_merge_base_to_error(tmp_path):
    write_component(tmp_path, "adr", "x")
    r = run_cli("lint", "--strict", "--json", "--root", str(tmp_path), cwd=tmp_path)
    assert r.returncode == 1
    payload = json.loads(r.stdout)
    assert any(e["code"] == "E042" for e in payload["errors"])


def test_cli_config_error_exits_two(tmp_path):
    (tmp_path / ".grimore.toml").write_text("broken [", encoding="utf-8")
    r = run_cli("lint", "--root", str(tmp_path), cwd=tmp_path)
    assert r.returncode == 2
    assert "grim:" in r.stderr


def test_cli_human_output_has_summary(tmp_path):
    write_component(tmp_path, "adr", "x")
    r = run_cli("lint", "--root", str(tmp_path), cwd=tmp_path)
    assert r.returncode == 0
    assert "0 error(s)" in r.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — `AttributeError: module 'grim' has no attribute 'run_lint'`.

- [ ] **Step 3: Write the implementation** — append to `tools/grim.py`:

```python
@dataclasses.dataclass
class LintResult:
    findings: list[Finding]
    fixed: list[str]

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warning"]

    @property
    def exit_code(self) -> int:
        return 1 if self.errors else 0

    def to_json(self) -> str:
        return json.dumps(
            {
                "ok": not self.errors,
                "errors": [dataclasses.asdict(f) for f in self.errors],
                "warnings": [dataclasses.asdict(f) for f in self.warnings],
                "fixed": self.fixed,
            },
            indent=2,
        )


def run_lint(root: Path, *, fix: bool = False, strict: bool = False) -> LintResult:
    root = root.resolve()
    cfg = load_config(root)
    store = load_store(cfg)
    findings = list(store.findings)
    findings += check_schema(store, cfg)
    findings += check_ids(store)
    findings += check_edges(store)
    findings += check_transitions(store, cfg, strict)
    findings += check_avoid_terms(store)
    findings += check_plans(cfg)
    fixed = apply_fixes(store, findings) if fix else []
    return LintResult(findings=findings, fixed=fixed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grim", description="doc-components tooling")
    sub = parser.add_subparsers(dest="verb", required=True)
    lint_p = sub.add_parser("lint", help="validate the component store")
    lint_p.add_argument("--fix", action="store_true", help="normalize component formatting")
    lint_p.add_argument(
        "--strict", action="store_true",
        help="fail closed when the merge-base is unresolvable (CI mode)",
    )
    lint_p.add_argument("--json", action="store_true", help="machine-readable output")
    lint_p.add_argument(
        "--root", type=Path, default=Path.cwd(), help="project root (default: cwd)"
    )
    args = parser.parse_args(argv)
    try:
        result = run_lint(args.root, fix=args.fix, strict=args.strict)
    except ConfigError as exc:
        print(f"grim: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(result.to_json())
    else:
        for f in result.findings:
            location = f.path + (f" [{f.component}]" if f.component else "")
            print(f"{f.level.upper()} {f.code} {location}: {f.message}")
        for rel in result.fixed:
            print(f"FIXED {rel}")
        summary = f"{len(result.errors)} error(s), {len(result.warnings)} warning(s)"
        if result.fixed:
            summary += f", {len(result.fixed)} file(s) fixed"
        print(summary)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: 7 passed. Then `uv run pytest -q` — all green.

- [ ] **Step 5: Smoke-test standalone execution** (PEP 723 path):

Run: `uv run tools/grim.py lint --root . ; echo "exit: $?"`
Expected: runs without ImportError. This repo has no `docs/components/` under default config, so the store is empty, the transition check is skipped by its guard, and output is `0 error(s), 0 warning(s)` with exit 0.

- [ ] **Step 6: Commit**

```bash
git add tools/grim.py tests/test_cli.py
git commit -m "feat(grim): lint CLI with JSON output and exit codes"
```

---

### Task 10: Examples fixture gate + SCHEMA.md escape-marker note

**Files:**
- Create: `tests/test_examples.py`
- Modify: `doc-components/SCHEMA.md` (term bullet in "Body formats")
- Possibly modify: files under `doc-components/examples/` (only if the new test finds real violations)

**Interfaces:**
- Consumes: `grim.run_lint`.

- [ ] **Step 1: Write the test** — `tests/test_examples.py`:

```python
import shutil
from pathlib import Path

import grim

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_shipped_examples_lint_clean(tmp_path):
    """doc-components/examples/ is the clean fixture tree; lint must pass it.

    Copied into a store layout so the check is hermetic (no git, no repo
    config): schema, ids, edges, and avoid-term checks all run; the
    transition check downgrades to its documented W042 skip.
    """
    src = REPO_ROOT / "doc-components" / "examples"
    shutil.copytree(src, tmp_path / "docs" / "components")
    result = grim.run_lint(tmp_path)
    assert result.errors == [], [f"{f.code} {f.path}: {f.message}" for f in result.errors]
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/test_examples.py -v`
Expected: ideally PASS. If it FAILS, the failure list names real fixture violations: fix the fixture files themselves (reword an avoided term, correct frontmatter) — prefer rewording over `<!-- grim:ok -->` markers so the examples stay exemplary. Do not weaken the linter to make fixtures pass. Re-run until green.

- [ ] **Step 3: Document the escape marker in SCHEMA.md.** In `doc-components/SCHEMA.md`, in the "Body formats" section, extend the **term** bullet:

Replace:

```markdown
- **term** — `**Term**: one-two sentence definition.` then
  `_Avoid_: rejected synonyms.` Opinionated; context-specific terms only.
```

with:

```markdown
- **term** — `**Term**: one-two sentence definition.` then
  `_Avoid_: rejected synonyms.` Opinionated; context-specific terms only.
  Lint enforces Avoid-terms from `current` terms against draft and current
  component bodies (word-boundary, case-insensitive); append
  `<!-- grim:ok -->` to a line to mark a deliberate mention.
```

- [ ] **Step 4: Full suite + standalone smoke**

Run: `uv run pytest -q`
Expected: all tests pass.

Run: `uv run tools/grim.py lint --json --root . | head -20`
Expected: valid JSON, exit code 0 (check with `echo $?`).

- [ ] **Step 5: Commit**

```bash
git add tests/test_examples.py doc-components/SCHEMA.md
# plus any doc-components/examples/ files actually changed, by name
git commit -m "test(grim): gate lint on the shipped examples; document grim:ok marker"
```

---

## Verification (whole-branch, before PR)

1. `uv run pytest -q` — full suite green.
2. `uv run tools/grim.py lint --root . ; echo $?` — runs standalone via PEP 723, exits 0.
3. `git log --oneline main..HEAD` — commits present, none staging stray files (`git show --stat` spot-check).
4. Final whole-branch review on opus, then PR to main with the Linear issue attached (IAM-38 auto-completes on merge — expected).
