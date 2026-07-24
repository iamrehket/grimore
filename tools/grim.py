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
