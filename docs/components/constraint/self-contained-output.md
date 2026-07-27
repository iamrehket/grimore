---
id: constraint-self-contained-output
type: constraint
status: current
date: 2026-07-13
---

# Generated pages make no external requests

A generated guide is a single self-contained file: styles, scripts, and any
diagram runtime are inlined, and the page issues no network request when
opened. The constraint keeps a guide readable offline, on a locked-down
machine, and years later when whatever host it might have referenced is gone.
