---
id: constraint-zero-setup-consumers
type: constraint
status: current
supersedes: [constraint-zero-setup-consumption]
date: 2026-08-09
---

# Zero-setup consumption, with or without the repository

Current documentation must be readable with no build step, no toolchain, and
no account. Three consumer classes count: the repository's web view, an
agent holding only a checkout, and a reader with no way into the repository
at all - handed the bundle in a ticket, a chat, or a release workflow. The
first two are what forced rendered views to be committed rather than
generated in CI, along with the merge discipline that keeps them honest.

No committed file can serve the third class, because reaching a committed
file is precisely what that reader cannot do. The bundle serves them
instead: a checkout-holder generates it and hands it over, and it carries
nothing that points back into a repository the reader cannot reach. Zero
setup for that reader is a property of the artifact, not of the tree - the
handing over is the setup, and it happens on the sender's side.
