---
components:
  - adr-never-empty-banner
  - adr-banner-qualifier-clauses
  - adr-quoted-stamp-format
implemented: "2026-07-28 (PR #15)"
---

<!-- grim:status -->
> **Implemented 2026-07-28 (PR #15).**
> References current.
<!-- /grim:status -->

# Banner Derivation - Design

Date: 2026-07-28

## Problem

`grim` writes no status banner. The marker `grim:status` appears nowhere in
the tool; the only working-layer logic warns when a plan omits its `spec:`
line. Every spec and plan in the repository carries an empty banner block.

Meanwhile the schema, the glossary term, and the spec template all state that
`grim lint --fix` rewrites that block, and the term describing the behavior is
`current`. A current component documents a code path that does not exist. The
issue tracking this work was closed by a documentation pull request that named
it, so nothing surfaced the gap: an empty block looks exactly like correct
output, and no check compares a documented capability against a built one.

The consequence a reader feels is that a spec or plan cannot answer "is this
still worth reading" without manually tracing every component it references.

## Approach

`grim lint --fix` derives the block interior from the spec's frontmatter and
the component graph, and `grim lint` reports drift as an error so a stale
banner fails continuous integration rather than rotting quietly. The rendered
views are verified by re-render and byte-compare, but that comparison covers
only the rendered directory, so working-layer files need an explicit finding
to be governed at all.

Ownership is split along the line between derived facts and event facts. The
banner is a pure function of the store and is owned by the script. The
`implemented:` stamp records that a branch finished and is owned by the
reconciliation pass, which writes it and then invokes the script. The script
reads the stamp and never writes it; the reconciliation pass never authors
banner text. Keeping that boundary executable is why the stamp parser lives
here, one issue ahead of the writer it serves.

Banner text is composed rather than enumerated: a provenance line, then
qualifier clauses in fixed order. This is what lets a draft reference and an
empty component list produce output instead of falling through, and it is
recorded as `adr-banner-qualifier-clauses`.

Two properties are load-bearing and constrain the implementation. The block
is never empty, because emptiness cannot be distinguished from a tool that
never ran - `adr-never-empty-banner`. And the interior is byte-deterministic,
because it is compared rather than merely displayed: every identifier list is
sorted, supersede pairs order by source, and the date comes from the stamp
rather than the clock.

Supersede chains resolve transitively. The existing edge check records a
successor only when that successor is itself current, so a decision superseded
twice would otherwise be reported as abandoned while a live successor exists
two hops away - the one word the design reserves for a genuinely dead
decision. Resolution walks forward with a visited set, because two mutually
superseding current components pass every existing check and would hang a
naive walk.

The alternative of treating banners as advisory and never failing on drift was
rejected: it reproduces the rot this work exists to remove, since a banner goes
stale whenever a component is superseded on a branch that does not re-derive.

## Decisions

- Banner blocks are never empty; emptiness cannot be distinguished from an
  unexecuted tool: adr-never-empty-banner
- Banner text composes ordered clauses instead of enumerating states, so new
  statuses extend rather than multiply: adr-banner-qualifier-clauses
- The `implemented:` stamp is quoted on disk, because the documented unquoted
  form truncates at a YAML comment: adr-quoted-stamp-format

## Out of scope

Writing the `implemented:` stamp, reconciling drafts against a diff, and
authoring supersede edges all belong to the reconciliation pass. Governing the
legacy working-layer tree is excluded, since configuration points the specs and
plans directories elsewhere. Any semantic comparison of a spec against a diff
remains excluded by standing non-goal.
