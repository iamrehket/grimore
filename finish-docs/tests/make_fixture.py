#!/usr/bin/env python3
"""Build the fixture for one of the finish-docs test scenarios
(`--scenario shipped|contradicted|preauthored`, each described by the
matching scenario-*.md in this directory).

Deliberately NOT inside grimore: a skill that assumes grimore-relative paths
must fail against this tree.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
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

# The `contradicted` scenario. The draft says column order is declared per
# tenant in configuration and that a column missing from the configuration is
# dropped. This code does neither: order follows the cursor, and callers are
# expected to read by header name instead. The decision changed, so promoting
# the draft would leave a current component asserting something false.
#
# The trap is that it reads as done at a glance - the configuration key is
# still there, the plan's tasks all look satisfied, and the export plainly
# handles columns. Nothing in the diff announces that config.py is now dead.
CODE_AFTER_CONTRADICTED = '''\
"""Order exports."""

import csv


def export_orders(cursor, out):
    """Stream rows to `out` as CSV, header first, in whatever order the
    query selected. Callers read by header name rather than by position."""
    writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(cursor.column_names)
    for row in cursor:
        writer.writerow(list(row))
'''

CONFIG_BEFORE = '''\
"""Per-tenant settings."""

# Column order per tenant, applied by the export writer.
COLUMN_ORDER = {}
'''

CONFIG_AFTER = '''\
"""Per-tenant settings."""

# Column order per tenant. No longer read: exports emit a header row and
# callers match on names.
COLUMN_ORDER = {}
'''

# The `preauthored` scenario. Main already ships the streaming CSV exporter
# its two live decisions describe; the branch replaces CSV with Parquet and
# its draft carries a capture-time `supersedes:` edge naming adr-csv-only,
# exactly as an align session authors it. The reconciler must accept that
# edge as-is: promotion refuses until a verdict names the target, and the
# right move is to state the flip, never to strip or hand-flip anything.
CODE_CSV_MAIN = '''\
"""Order exports."""

import csv


def export_orders(cursor, out):
    """Stream rows to `out` as CSV, header first, as they arrive."""
    writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(cursor.column_names)
    for row in cursor:
        writer.writerow(list(row))
'''

PARQUET_EXPORT = """\
---
id: adr-parquet-export
type: adr
status: draft
supersedes: [adr-csv-only]
date: 2026-08-05
---

# Exports are Parquet, not CSV

Both warehouse-bound customers ingest exports into columnar stores and were
re-typing CSV back into typed columns by hand, and the last three export
bugs were all CSV quoting bugs. Exports therefore switch to Parquet: typed
columns, no escaping surface, and fixed-size row groups written as rows
arrive so streaming stays intact. Trade-off accepted: a spreadsheet user can
no longer open an export directly and gets a converter later rather than a
format flag now - the same one-format rule the CSV decision set, with the
format changed.
"""

SPEC_PARQUET = """\
---
components: [adr-parquet-export]
---

<!-- grim:status -->
<!-- /grim:status -->

# Parquet exports - Design

Date: 2026-08-05

## Problem

Both warehouse-bound customers re-type every CSV export back into typed
columns, and the last three export bugs were all CSV quoting bugs.

## Approach

Replace the CSV writer with a Parquet writer that emits fixed-size row
groups as rows arrive from the cursor. The alternative considered was a
format flag offering Parquet alongside CSV, rejected because the CSV
decision already ruled a format flag out and no caller still wants CSV.

## Decisions

- Exports switch to Parquet, replacing the CSV-only decision:
  adr-parquet-export (supersedes adr-csv-only)

## Out of scope

A CSV-to-Parquet converter for spreadsheet users, and any second format.
"""

PLAN_PARQUET = """\
---
spec: docs/specs/2026-08-05-parquet.md
---

<!-- grim:status -->
<!-- /grim:status -->

# Plan: parquet exports

1. Replace the CSV writer in `src/exports.py` with a row-group Parquet
   writer.
2. Keep the batch size fixed so the largest tenant's export stays inside
   the worker's memory budget.
3. Cover an empty result set and a multi-group export with tests.
"""

CODE_PARQUET = '''\
"""Order exports."""

import pyarrow as pa
import pyarrow.parquet as pq

ROW_GROUP_SIZE = 10_000


def export_orders(cursor, out):
    """Write the result set to `out` as Parquet, one row group per batch.

    Rows drain from the cursor in fixed-size batches as they arrive, so the
    largest tenant's export still fits the worker's memory budget.
    """
    writer = None
    batch = []
    for row in cursor:
        batch.append(list(row))
        if len(batch) == ROW_GROUP_SIZE:
            writer = _write_group(writer, out, cursor.column_names, batch)
            batch = []
    writer = _write_group(writer, out, cursor.column_names, batch)
    writer.close()


def _write_group(writer, out, names, rows):
    columns = {name: [row[i] for row in rows] for i, name in enumerate(names)}
    table = pa.table(columns)
    if writer is None:
        writer = pq.ParquetWriter(out, table.schema)
    writer.write_table(table)
    return writer
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a finish-docs test fixture.")
    parser.add_argument("root")
    # A separate scenario rather than a mutation of the first: baseline-red.md
    # and baseline-green.md are scored against the `shipped` tree, and
    # baseline-green's rubric line 8 is verified by replaying the mechanical
    # path from its pre-run commit. Changing that tree in place would
    # retroactively invalidate both writeups.
    parser.add_argument("--scenario",
                        choices=("shipped", "contradicted", "preauthored"),
                        default="shipped")
    args = parser.parse_args()
    contradicted = args.scenario == "contradicted"
    preauthored = args.scenario == "preauthored"

    root = Path(args.root).resolve()
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
    # For `preauthored`, main's code already matches its two live decisions -
    # the branch under test replaces the format, not the buffering.
    write(root, "src/exports.py", CODE_CSV_MAIN if preauthored else CODE_BEFORE)
    write(root, "README.md", "# acme-exports\n\nOrder export service.\n")
    if contradicted:
        write(root, "src/config.py", CONFIG_BEFORE)

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

    if preauthored:
        git(root, "checkout", "-q", "-b", "feature/parquet")
        write(root, "docs/components/adr/parquet-export.md", PARQUET_EXPORT)
        write(root, "docs/specs/2026-08-05-parquet.md", SPEC_PARQUET)
        write(root, "docs/plans/2026-08-05-parquet.md", PLAN_PARQUET)
        write(root, "src/exports.py", CODE_PARQUET)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "feat: export orders as parquet")
    else:
        git(root, "checkout", "-q", "-b", "feature/exports")
        write(root, "docs/components/adr/column-order-config.md", COLUMN_ORDER)
        write(root, "docs/specs/2026-07-20-exports.md", SPEC_EXPORTS)
        write(root, "docs/specs/2026-07-21-column-order.md", SPEC_COLUMN_ORDER)
        write(root, "docs/plans/2026-07-20-exports.md", PLAN_EXPORTS)
        write(root, "docs/plans/2026-07-21-column-order.md", PLAN_COLUMN_ORDER)
        write(root, "src/exports.py", CODE_AFTER_CONTRADICTED if contradicted else CODE_AFTER)
        if contradicted:
            write(root, "src/config.py", CONFIG_AFTER)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "feat: stream CSV exports in configured column order")

    print(f"fixture at {root} ({args.scenario})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
