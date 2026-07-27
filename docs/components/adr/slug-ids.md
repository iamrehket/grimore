---
id: adr-slug-ids
type: adr
status: current
date: 2026-07-24
---

# Slug IDs, not sequential ADR numbers

Architecture decision records are conventionally numbered sequentially, and
that numbering was the starting assumption here. Adversarial review rejected
it: two concurrent branches each allocate "the next number" independently, and
the collision only surfaces once both merge - at which point renumbering means
rewriting every reference. Every component type therefore uses `<type>-<slug>`
identifiers, with the slug equal to the filename and duplicate IDs anywhere in
the store a lint error. The trade-off: IDs no longer sort chronologically or
convey sequence at a glance, and authors must choose a name rather than take a
number - in exchange for allocation-free, collision-resistant identity that
concurrent branches cannot corrupt.
