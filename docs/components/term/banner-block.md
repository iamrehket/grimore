---
id: term-banner-block
type: term
status: current
date: 2026-07-24
---

**Banner block**: the delimited region at the top of a spec or plan, bounded
by grim:status markers, that grim lint --fix owns and rewrites from the
component graph. Humans and agents never edit inside it; everything outside it
is frozen once the spec is implemented.

_Avoid_: status header.
