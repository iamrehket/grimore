---
id: constraint-deterministic-render
type: constraint
status: superseded
date: 2026-07-24
---

# Renders are byte-deterministic

Rendering the same store twice must produce byte-identical output. Ordering
within every rendered file is by date then id ascending, and nothing in the
output may depend on filesystem order, locale, or the time of the run.
Verification rests on this: grim check re-renders and byte-compares, so any
nondeterminism would turn the check into a random failure.
