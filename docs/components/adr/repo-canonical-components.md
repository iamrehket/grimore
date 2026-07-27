---
id: adr-repo-canonical-components
type: adr
status: current
date: 2026-07-24
---

# Components are repo-canonical; external stores hold pointers

Agent harnesses often route durable knowledge to an external store, which
makes such a store the obvious home for architecture decisions. grimore
instead keeps every component repo-canonical: versioned, PR-reviewed, and
merged alongside the code it describes. External knowledge and tracking stores
hold pointers and status, never the canonical content - and no particular
store is assumed, because not every adopting project has one. The trade-off:
decisions no longer travel between projects and tools for free, and the same
fact can exist in two places. In exchange, an agent working the code reads the
decision out of the checkout it already has, with no external dependency to
configure or authenticate.
