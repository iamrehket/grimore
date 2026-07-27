---
id: nongoal-full-staleness-tripwire
type: nongoal
status: current
date: 2026-07-24
---

# Full staleness tripwire

Coverage reporting, path-hygiene tooling that detects stale or renamed
`paths:` globs, and any semantic comparison of a diff against doc content are
out of scope for v1. The minimal touched-path guard ships instead, and is
deliberately crude: it cannot report what fraction of the codebase is
documented, cannot notice when a declared glob stops matching anything, and
cannot tell a meaningful change from a trivial one. Deferred because each
addition needs either a semantic model of the diff or a maintenance surface of
its own, and neither earns its cost before the basic guard has been lived
with.
