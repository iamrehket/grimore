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
import hashlib
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
RESERVED_OUTPUTS = ("charter", "decisions", "glossary", "general")
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
    for key in ("components", "current", "specs", "plans", "default_branch"):
        if key in raw and not isinstance(raw[key], str):
            raise ConfigError(f".grimore.toml: {key} must be a string")
    raw_types = raw.get("types", COMPONENT_TYPES)
    if not isinstance(raw_types, (list, tuple)) or not all(
        isinstance(t, str) for t in raw_types
    ):
        raise ConfigError(".grimore.toml: types must be a list of strings")
    types = tuple(raw_types)
    unknown = set(types) - set(COMPONENT_TYPES)
    if unknown:
        raise ConfigError(f".grimore.toml: unknown component types: {sorted(unknown)}")
    resolved_root = root.resolve()
    paths = {
        key: root / raw.get(key, DEFAULTS[key])
        for key in ("components", "current", "specs", "plans")
    }
    for key, p in paths.items():
        if not p.resolve().is_relative_to(resolved_root):
            raise ConfigError(
                f".grimore.toml: {key} must resolve inside the project root, got {p}"
            )
    return Config(
        root=root,
        components=paths["components"],
        current=paths["current"],
        specs=paths["specs"],
        plans=paths["plans"],
        default_branch=raw.get("default_branch", DEFAULTS["default_branch"]),
        types=types,
    )


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
        try:
            comp, errs = parse_component(path, cfg.root)
        except UnicodeDecodeError:
            findings.append(error("E006", rel, "file is not valid UTF-8"))
            continue
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
            elif not SLUG_RE.fullmatch(fm["subsystem"]):
                out.append(error("E062", rel, f"subsystem {fm['subsystem']!r} must match [a-z0-9][a-z0-9-]*", cid))
            elif fm["subsystem"] in RESERVED_OUTPUTS:
                out.append(error("E063", rel, f"subsystem {fm['subsystem']!r} collides with a fixed render output", cid))
    return out


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
            if c.status == "current" and isinstance(c.cid, str):
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


def _git(cfg: Config, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cfg.root, capture_output=True, text=True
    )


def check_transitions(store: Store, cfg: Config, strict: bool) -> list[Finding]:
    out: list[Finding] = []
    top = _git(cfg, "rev-parse", "--show-toplevel")
    refs_tried = [cfg.default_branch, f"origin/{cfg.default_branch}"]
    base = None
    if top.returncode == 0:
        for ref in refs_tried:
            mb = _git(cfg, "merge-base", "HEAD", ref)
            if mb.returncode == 0:
                base = mb.stdout.strip()
                break
    if base is None:
        if not cfg.components.is_dir():
            return out  # nothing on disk and no history to compare against
        if strict:
            return [
                error(
                    "E042", ".",
                    f"cannot resolve git merge-base with any of {refs_tried}; "
                    "failing closed (fix CI: fetch-depth: 0)",
                )
            ]
        return [
            warning(
                "W042", ".",
                f"cannot resolve git merge-base with any of {refs_tried}; "
                "skipping transition check",
            )
        ]
    git_root = Path(top.stdout.strip()).resolve()
    try:
        comp_prefix = cfg.components.resolve().relative_to(git_root).as_posix()
    except ValueError:
        raise ConfigError(
            f"components dir {cfg.components} is outside the git repository {git_root}"
        ) from None
    ls = _git(cfg, "ls-tree", "--full-tree", "-r", "-z", "--name-only", base, "--", comp_prefix)
    if ls.returncode != 0:
        if strict:
            return [
                error(
                    "E042",
                    ".",
                    "cannot list components at merge-base; "
                    "failing closed (fix CI: fetch-depth: 0)",
                )
            ]
        return [
            warning(
                "W042",
                ".",
                "cannot list components at merge-base; skipping transition check",
            )
        ]
    old_paths = {p for p in ls.stdout.split("\0") if p}
    present_paths = (
        {
            p.resolve().relative_to(git_root).as_posix()
            for p in cfg.components.rglob("*.md")
        }
        if cfg.components.is_dir()
        else set()
    )
    by_git_rel = {
        c.path.resolve().relative_to(git_root).as_posix(): c for c in store.components
    }
    root_resolved = cfg.root.resolve()
    for old in sorted(old_paths):
        if old.endswith(".md") and old not in present_paths:
            abs_old = git_root / old
            try:
                rel = abs_old.relative_to(root_resolved).as_posix()
            except ValueError:
                rel = old
            out.append(error("E041", rel, "component deleted; components are never deleted"))
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


def check_plans(cfg: Config) -> list[Finding]:
    out: list[Finding] = []
    if not cfg.plans.is_dir():
        return out
    for path in sorted(cfg.plans.rglob("*.md")):
        rel = path.relative_to(cfg.root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            out.append(warning("W060", rel, "plan is not valid UTF-8; spec: check skipped"))
            continue
        m = FM_RE.match(text)
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


def _yaml_scalar(value, *, key: str | None = None, in_flow: bool = False) -> str:
    """Emit a scalar that YAML re-parses to the same string, quoting only
    when the plain form would change meaning (e.g. yes -> bool) or break
    flow-sequence syntax (commas, brackets, braces)."""
    s = str(value)
    try:
        reparsed = yaml.safe_load(s)
    except yaml.YAMLError:
        reparsed = object()
    if key == "date" and isinstance(reparsed, datetime.date):
        reparsed = reparsed.isoformat()
    needs_quotes = reparsed != s
    if in_flow and any(ch in s for ch in ",[]{}"):
        needs_quotes = True
    return json.dumps(s) if needs_quotes else s


def _format_fm_value(key: str, value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_yaml_scalar(v, key=key, in_flow=True) for v in value) + "]"
    return _yaml_scalar(value, key=key)


def normalize_component(c: Component) -> str:
    lines = ["---"]
    for key in FIELD_ORDER:
        if key in c.fm:
            lines.append(f"{key}: {_format_fm_value(key, c.fm[key])}")
    lines.append("---")
    body = c.body.strip("\n")
    if not body:
        return "\n".join(lines) + "\n"
    return "\n".join(lines) + "\n\n" + body + "\n"


HEADING_RE = re.compile(r"^(#{1,6})(?=\s)", re.MULTILINE)


def demote_headings(body: str, levels: int) -> str:
    return HEADING_RE.sub(lambda m: "#" * min(6, len(m.group(1)) + levels), body)


def store_hash(store: Store) -> str:
    h = hashlib.sha256()
    pairs = sorted(
        (c.rel, normalize_component(c))
        for c in store.components
        if c.status == "current"
    )
    for rel, content in pairs:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(content.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


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


CHARTER_SECTIONS = (("usecase", "Use cases"), ("constraint", "Constraints"), ("nongoal", "Non-goals"))


def _current_sorted(store: Store, *types: str) -> list[Component]:
    return sorted(
        (c for c in store.components if c.status == "current" and c.ctype in types),
        key=lambda c: (str(c.fm.get("date", "")), str(c.cid or "")),
    )


def render_store(store: Store) -> dict[str, str]:
    header = [
        f"<!-- grim:store-hash sha256:{store_hash(store)} -->",
        "<!-- generated by grim render; do not edit -->",
        "",
    ]
    out: dict[str, str] = {}

    def emit(name: str, title: str, chunks: list[str]) -> None:
        if chunks:
            out[name] = "\n".join(header + [f"# {title}", ""] + chunks).rstrip("\n") + "\n"

    def body(c: Component, levels: int) -> str:
        return demote_headings(c.body.strip("\n"), levels) + "\n"

    charter: list[str] = []
    for ctype, heading in CHARTER_SECTIONS:
        comps = _current_sorted(store, ctype)
        if comps:
            charter.append(f"## {heading}\n")
            charter += [body(c, 2) for c in comps]
    emit("charter.md", "Charter", charter)
    emit("decisions.md", "Decisions", [body(c, 1) for c in _current_sorted(store, "adr")])
    emit("glossary.md", "Glossary", [body(c, 1) for c in _current_sorted(store, "term")])
    by_subsystem: dict[str, list[Component]] = {}
    for c in _current_sorted(store, "note"):
        sub = c.fm.get("subsystem")
        by_subsystem.setdefault(sub if isinstance(sub, str) and sub else "general", []).append(c)
    for sub, comps in sorted(by_subsystem.items()):
        emit(f"{sub}.md", sub, [body(c, 1) for c in comps])
    return out


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


def write_render(cfg: Config, rendered: dict[str, str]) -> tuple[list[str], list[str]]:
    written: list[str] = []
    removed: list[str] = []
    for name in rendered:
        # Belt and suspenders: the lint gate (E062) already rejects
        # path-hostile subsystems; refuse to write outside cfg.current
        # even if a future caller skips the gate.
        if "/" in name or "\\" in name or name.startswith("."):
            raise ValueError(f"unsafe render output name {name!r}")
    if rendered:
        cfg.current.mkdir(parents=True, exist_ok=True)
    for name in sorted(rendered):
        path = cfg.current / name
        if not path.is_file() or path.read_text(encoding="utf-8") != rendered[name]:
            path.write_text(rendered[name], encoding="utf-8")
            written.append(path.relative_to(cfg.root).as_posix())
    if cfg.current.is_dir():
        for path in sorted(cfg.current.glob("*.md")):
            if path.name not in rendered:
                path.unlink()
                removed.append(path.relative_to(cfg.root).as_posix())
    return written, removed


@dataclasses.dataclass
class RenderResult:
    written: list[str]
    removed: list[str]
    findings: list[Finding]

    @property
    def exit_code(self) -> int:
        return 1 if any(f.level == "error" for f in self.findings) else 0

    def to_json(self) -> str:
        return json.dumps(
            {
                "ok": self.exit_code == 0,
                "written": self.written,
                "removed": self.removed,
                "errors": [
                    dataclasses.asdict(f) for f in self.findings if f.level == "error"
                ],
                "warnings": [
                    dataclasses.asdict(f) for f in self.findings if f.level == "warning"
                ],
            },
            indent=2,
        )


def run_render(root: Path) -> RenderResult:
    root = root.resolve()
    lint = run_lint(root, fix=False, strict=False)
    if lint.errors:
        return RenderResult(written=[], removed=[], findings=lint.findings)
    cfg = load_config(root)
    store = load_store(cfg)
    written, removed = write_render(cfg, render_store(store))
    return RenderResult(written=written, removed=removed, findings=lint.findings)


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
    render_p = sub.add_parser("render", help="compile docs/current/ from current components")
    render_p.add_argument("--json", action="store_true", help="machine-readable output")
    render_p.add_argument("--root", type=Path, default=Path.cwd(), help="project root (default: cwd)")
    args = parser.parse_args(argv)
    try:
        if args.verb == "lint":
            result = run_lint(args.root, fix=args.fix, strict=args.strict)
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
        elif args.verb == "render":
            result = run_render(args.root)
            if args.json:
                print(result.to_json())
            else:
                for f in result.findings:
                    if f.level == "error":
                        location = f.path + (f" [{f.component}]" if f.component else "")
                        print(f"{f.level.upper()} {f.code} {location}: {f.message}")
                if result.exit_code != 0:
                    print("render refused: fix lint errors first")
                else:
                    for rel in result.written:
                        print(f"RENDERED {rel}")
                    for rel in result.removed:
                        print(f"REMOVED {rel}")
                    summary = f"{len(result.written)} file(s) written, {len(result.removed)} removed"
                    print(summary)
            return result.exit_code
    except ConfigError as exc:
        print(f"grim: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
