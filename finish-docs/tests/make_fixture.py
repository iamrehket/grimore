#!/usr/bin/env python3
"""Build the scenario-shipped-branch fixture described in
finish-docs/tests/scenario-shipped-branch.md.

Deliberately NOT inside grimore: a skill that assumes grimore-relative paths
must fail against this tree.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# finish-docs/tests/make_fixture.py -> the repository root three levels up.
GRIMORE = Path(__file__).resolve().parent.parent.parent


def git(root: Path, *args: str) -> None:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


GRIMORE_TOML = """\
[grimore]
components = "docs/components"
current = "docs/current"
specs = "docs/specs"
plans = "docs/plans"
default_branch = "main"
"""

CSV_ONLY = """\
---
id: adr-csv-only
type: adr
status: current
date: 2026-07-10
---

# CSV is the only export format

Three pilot customers all asked for spreadsheet import, and every additional
format doubles the escaping surface the writer has to get right. Exports are
therefore CSV and nothing else, quoted per RFC 4180. Trade-off accepted: a
customer who wants JSON gets a new writer later rather than a format flag now,
because a format flag leaks into every layer that touches a row.
"""

STREAMING_WRITER = """\
---
id: adr-streaming-writer
type: adr
status: current
date: 2026-07-12
---

# Stream rows instead of buffering the result set

An export of the largest tenant's order table did not fit in the worker's
memory budget, and paging it in the caller put the page size in two places.
Rows are therefore written to the output stream as they arrive from the cursor.
Trade-off accepted: the total row count is unknown until the export finishes,
so progress reporting is byte-based rather than percentage-based.
"""

COLUMN_ORDER = """\
---
id: adr-column-order-config
type: adr
status: draft
date: 2026-07-21
---

# Column order comes from configuration, not the query

Two tenants disagreed about column order and both were reading the CSV with
positional scripts, so the order cannot follow whatever the query happens to
select. Column order is therefore declared per tenant in configuration and the
writer reorders to match. Trade-off accepted: a column added to the query but
missing from the configuration is dropped from the export rather than appended
in an arbitrary position.
"""

SPEC_EXPORTS = """\
---
components: [adr-csv-only, adr-streaming-writer]
---

<!-- grim:status -->
<!-- /grim:status -->

# Exports - Design

Date: 2026-07-20

## Problem

Tenants export order data by hand-copying from the admin UI, which caps a
realistic export at a few hundred rows and produces a different column layout
every time. Support handles the difference by rewriting spreadsheets.

## Approach

A single export endpoint that streams CSV straight from the database cursor.
The alternative considered was a queued job writing to object storage, which
adds a bucket, a lifecycle policy, and a signed-URL flow to solve a problem
that only the largest tenant currently has.

## Decisions

- CSV is the only format: adr-csv-only
- Rows stream rather than buffer: adr-streaming-writer

## Out of scope

Scheduled exports, and any format other than CSV.
"""

SPEC_COLUMN_ORDER = """\
---
components: [adr-column-order-config]
---

<!-- grim:status -->
<!-- /grim:status -->

# Column order - Design

Date: 2026-07-21

## Problem

Two tenants read the exported CSV with positional scripts and disagree about
which column comes first, so whatever order the query returns breaks one of
them on every schema change.

## Approach

Declare column order per tenant in configuration and have the writer reorder
each row to match. The alternative considered was a header-driven contract,
which does not help callers that read by position.

## Decisions

- Column order is configured, not queried: adr-column-order-config

## Out of scope

Per-tenant column renaming, and column subsetting.
"""

PLAN_EXPORTS = """\
---
spec: docs/specs/2026-07-20-exports.md
---

<!-- grim:status -->
<!-- /grim:status -->

# Plan: exports

1. Add the cursor-streaming CSV writer in `src/exports.py`.
2. Wire the export endpoint to it.
3. Cover quoting and a multi-page result set with tests.
"""

PLAN_COLUMN_ORDER = """\
---
spec: docs/specs/2026-07-21-column-order.md
---

<!-- grim:status -->
<!-- /grim:status -->

# Plan: column order

1. Read the per-tenant column order from configuration.
2. Reorder each row in the writer before it is emitted.
3. Cover a missing column and an extra column with tests.
"""

CODE_BEFORE = '''\
"""Order exports."""


def export_orders(cursor):
    """Buffer the whole result set. Replaced by the streaming writer."""
    return list(cursor)
'''

CODE_AFTER = '''\
"""Order exports."""

import csv


def export_orders(cursor, out, columns):
    """Stream rows to `out` as CSV in the configured column order."""
    writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    for row in cursor:
        writer.writerow([row[name] for name in columns])
'''


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: make_fixture.py <fixture-root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.com")
    git(root, "config", "user.name", "Fixture")

    # Vendored tooling, as an adopting project would have it.
    (root / "tools").mkdir()
    shutil.copy2(GRIMORE / "tools" / "grim.py", root / "tools" / "grim.py")
    shutil.copytree(GRIMORE / "doc-components", root / "doc-components")

    write(root, ".grimore.toml", GRIMORE_TOML)
    write(root, "docs/components/adr/csv-only.md", CSV_ONLY)
    write(root, "docs/components/adr/streaming-writer.md", STREAMING_WRITER)
    write(root, "src/exports.py", CODE_BEFORE)
    write(root, "README.md", "# acme-exports\n\nOrder export service.\n")

    # Render main's committed view with grim itself, so the bytes are whatever
    # grim produces rather than whatever this script guesses.
    for verb in (["lint", "--fix"], ["render"]):
        r = subprocess.run(
            ["uv", "run", "--no-project", str(root / "tools" / "grim.py"),
             *verb, "--root", str(root)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            raise SystemExit(f"grim {verb} on main failed:\n{r.stdout}\n{r.stderr}")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "chore: adopt doc components")

    git(root, "checkout", "-q", "-b", "feature/exports")
    write(root, "docs/components/adr/column-order-config.md", COLUMN_ORDER)
    write(root, "docs/specs/2026-07-20-exports.md", SPEC_EXPORTS)
    write(root, "docs/specs/2026-07-21-column-order.md", SPEC_COLUMN_ORDER)
    write(root, "docs/plans/2026-07-20-exports.md", PLAN_EXPORTS)
    write(root, "docs/plans/2026-07-21-column-order.md", PLAN_COLUMN_ORDER)
    write(root, "src/exports.py", CODE_AFTER)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "feat: stream CSV exports in configured column order")

    print(f"fixture at {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
