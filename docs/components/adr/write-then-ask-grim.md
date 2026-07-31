---
id: adr-write-then-ask-grim
type: adr
status: draft
date: 2026-07-30
---

# Apply the writes, then ask grim, then roll back

Validating a proposed store change before writing it means reimplementing the
rules grim already owns, and doing exactly that produced eleven divergences
across two review rounds of the stamping pass - every one a case where the
script accepted what grim rejects. Reconciliation instead snapshots the bytes
of every file it will touch, applies all its writes, runs grim over the
result, and restores the snapshot unless grim reports the store clean, so
illegal transitions, dual live successors and missing edge targets are all
caught by the component that defines them. The gate is inverted deliberately:
it rolls back unless grim answered and answered clean, because grim emits
nothing on standard output when configuration loading fails, and a check
phrased as "did any error appear" would read that silence as success and keep
the writes. Trade-off accepted: an inconsistent state exists on disk for the
duration of one lint, which is safe because the snapshot restore is exact and
nothing else reads the store concurrently.
