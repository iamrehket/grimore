---
id: adr-check-fails-closed
type: adr
status: current
paths: [.github/workflows/grim.yml]
date: 2026-07-24
---

# grim check fails closed on an unresolvable merge-base

Transition legality is checked by comparing each component's status against
its status at the merge-base, which requires a resolvable merge-base - and a
shallow CI checkout guarantees there is none. Treating that as a skip would
make the check silently pass on exactly the branches it exists to police, so
grim check treats an unresolvable merge-base as an error and tells the
operator to fix CI with fetch-depth: 0, while local grim lint stays
best-effort and skips with a warning instead. The trade-off: a misconfigured
CI job blocks the branch loudly rather than degrading quietly, and shallow
clones and pre-adoption history become configuration problems the operator
must resolve - accepted because a check that skips itself under the conditions
it exists to catch is not a check.
