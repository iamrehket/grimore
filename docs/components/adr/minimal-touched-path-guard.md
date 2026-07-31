---
id: adr-minimal-touched-path-guard
type: adr
status: superseded
date: 2026-07-24
---

# A deterministic touched-path guard, not semantic comparison

Documentation goes stale silently when code moves and nobody updates the doc
describing it, and the thorough fix - semantic comparison of the diff against
doc content - is expensive per branch and hard to make deterministic. v1 ships
a minimal touched-path guard instead: the branch diff intersected with each
component's declared paths: globs, where a hit requires the component to
change in the same branch or a recorded Grim-Waive commit trailer. The
trade-off: the guard is coarse and only as good as the globs declared - it
cannot tell a meaningful change from a whitespace one, and undeclared paths
gate nothing - in exchange for a check that is deterministic, reviewable, and
costs no tokens.
