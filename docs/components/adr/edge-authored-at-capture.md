---
id: adr-edge-authored-at-capture
type: adr
status: current
date: 2026-08-07
---

# Supersede edges are authored at capture, activated at branch finish

Two consecutive branches followed opposite practice on who writes a
`supersedes:` edge - one let the reconciler write it, the next authored it on
the draft and had to strip it mid-branch - because align and finish-docs gave
contradictory instructions. The contract is now the schema's: the session
that reverses a live decision authors the edge on the new draft at the
crystallization moment, and the edge takes effect only at promotion, where an
explicit verdict must still name the target before anything flips. The edge
is the record of the decision; the verdict is the flip. This preserves the
reviewed branch-finish step that nongoal-semantic-drift-detection relies on -
banners and reconciliation still act only on explicit edges, and what moves
to capture time is authorship, not effect. Trade-off accepted: the
reconciler's own edge-writing path runs only for reversals decided at branch
finish, and an abandoned draft can carry a dead edge no one will ever
activate - taken because a reversal recorded only in prose is silent, while a
pre-authored edge makes promotion refuse until the flip is stated.
