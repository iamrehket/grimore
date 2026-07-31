---
id: adr-implemented-stamp-branch-finish
type: adr
status: current
date: 2026-07-30
---

# The implemented stamp records branch finish, not merge

The doc delta rides the same pull request as the code it describes, which is
what makes it reviewable alongside that code, but a stamp recording the merge
would have to be written after the merge - a second write to the default
branch, unreviewed, breaking the same-pull-request property to record a fact
the file's own location already implies. The stamp therefore records the
branch-finish event: the date the work was completed and the pull request it
was submitted in, with merge implied by the file's presence on the default
branch. The abandonment objection dissolves on inspection, because the stamp
lives in the spec file and an abandoned branch's stamp never reaches the
default branch, so no reader meets a false claim; a merged-then-reverted
change is covered because the revert takes the doc delta with it in the same
commit. Trade-off accepted: the date is branch finish, so a pull request that
sits for three days stamps three days early, and that is documented as the
definition rather than dressed up as an approximate merge date.
