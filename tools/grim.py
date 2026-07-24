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
