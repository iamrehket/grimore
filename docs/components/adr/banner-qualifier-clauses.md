---
id: adr-banner-qualifier-clauses
type: adr
status: current
date: 2026-07-28
---

# Banners compose clauses rather than enumerate states

The design spec listed four banner outcomes keyed on whether referenced
components were current or superseded, and a spec whose components include a
draft - which the reconciliation pass explicitly produces when a decision was
designed but not built - matched none of them and fell through to no output at
all. Rather than extend the enumeration and invite the same gap on the next
status added, a banner is now composed: one provenance line stating whether
the spec is stamped, followed by qualifier clauses in a fixed order for an
empty component list, draft references, partial supersession, and full
supersession. Adding a component status or a new qualifier means adding one
clause instead of multiplying rows, and an unmatched combination degrades to
the provenance line rather than to silence. The trade-off: banner text is
assembled rather than looked up, so its exact bytes are less obvious from
reading the rules alone and determinism now rests on clause ordering and on
sorting every id list - both of which the test suite pins directly.
