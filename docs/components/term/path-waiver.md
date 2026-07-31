---
id: term-path-waiver
type: term
status: draft
date: 2026-07-30
---

**Waiver**: a recorded, reasoned bypass of a touched-path guard hit, in one of
two forms. A `Grim-Waive` commit trailer names a component and a mandatory
reason and covers that component for the remainder of the branch; it is echoed
as W071. A standing waiver, declared in `.grimore.toml`, names a component, a
subset of its declared paths, and a mandatory reason, and covers those paths
permanently; it is echoed as W073. The trailer is deaf once and has to be
re-justified next time; the standing waiver is deaf until someone deletes it.

_Avoid_: blanket waiver, silent bypass.
