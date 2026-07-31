---
id: adr-reconcile-verdict-explicit
type: adr
status: draft
date: 2026-07-30
---

# The agent judges, the script executes and proves

Deciding whether a branch built what its draft describes is irreducibly a
judgement, and two scored agent baselines showed that an unaided agent already
makes it well - what it cannot supply is a validated writer, a refusal it
cannot talk itself out of, and an audit line that survives losing the
transcript. Reconciliation therefore takes the judgement as an explicit
command-line verdict per component, each carrying mandatory one-line evidence,
and the script performs the transition, proves the result legal, and prints
what changed; it never infers a verdict and never proceeds without one for
every draft in scope. Trade-off accepted: the invocation is verbose and a
branch with six drafts needs six verdicts, in exchange for the property that
silence can never stand in for a decision - the failure this replaces was a
draft skipped because nobody had to say anything about it.
