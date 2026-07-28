---
id: adr-stamp-refuses-unreconciled
type: adr
status: current
date: 2026-07-28
---

# Stamping refuses what it cannot verify

Shipping the branch-finish pass in two slices put the stamp ahead of the
reconciliation that is supposed to justify it, and the expedient reading would
have let the first slice stamp every discovered spec and leave the drafts for
later. It does the opposite: a spec whose referenced components include a draft
is refused, named, and left unstamped, because the stamp asserts the spec was
implemented and nothing in that slice compares a draft against the diff to
support the claim. Superseded components do not block a stamp - a decision that
has since been replaced was still implemented - and an already-stamped spec is
skipped rather than rewritten. The trade-off: a branch that created drafts
still needs a human to reconcile them, and the tool that was supposed to
automate branch finish will visibly decline the most interesting case until the
second slice lands. Bought in exchange: a stamp always means someone or
something checked, so a reader never has to ask whether a governed claim was
verified or merely asserted. The same reasoning generalizes - a tool that
launders a guess into a governed document is worse than no tool, because the
guess becomes indistinguishable from a fact the moment it is written down.
