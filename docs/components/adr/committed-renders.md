---
id: adr-committed-renders
type: adr
status: current
paths: [doc-components/CI.md]
date: 2026-07-24
---

# Commit rendered docs, pay with merge discipline

Rendered aggregates generated in CI rather than committed cannot go stale, and
adversarial review recommended exactly that. grimore commits the rendered
agent view anyway, paired with a required merge discipline - branches up to
date before merge, grim check in PR CI, and grim check on the default branch
as a backstop - so cross-branch invariants are enforced before they land
rather than discovered after. The trade-off was taken knowingly: doc-touching
merges serialize, and every such branch re-runs lint --fix and render after an
update. Bought in exchange: zero-setup consumption, where the web view and
agents without a build step read current docs straight out of the checkout.
