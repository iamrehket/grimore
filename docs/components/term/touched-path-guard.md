---
id: term-touched-path-guard
type: term
status: current
date: 2026-07-24
---

**Touched-path guard**: the check that intersects the branch diff against each
live component's declared paths globs. A hit requires that component to change
in the same branch, or a recorded Grim-Waive commit trailer naming it. Only
live components gate, and coverage grows only as paths are declared.

_Avoid_: path lint.
