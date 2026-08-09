---
id: constraint-zero-setup-consumption
type: constraint
status: superseded
date: 2026-07-24
---

# Zero-setup consumption

Current documentation must be readable with no build step, no toolchain, and
no account - the repository's web view and an agent holding only a checkout
both count as consumers. This is a hard requirement, and it is what forced
rendered views to be committed rather than generated in CI, along with the
merge discipline that keeps them honest.
