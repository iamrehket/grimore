---
id: adr-digest-walks-first-parent
type: adr
status: current
date: 2026-08-01
---

# The digest walks the first-parent line only

Some pull requests land as a merge commit and some as a single squashed
commit, and a repository's history routinely contains both, so a walk that
does not name its parent line returns inconsistent answers over one range -
the same kind of change reported two different ways depending on how it
happened to land. The digest follows the first-parent line of the default
branch. Where a pull request landed squashed that is the same answer a full
walk would give; where it landed as a merge it makes the pull request one
event and hides what happened inside, so a draft amended several times across
a branch and then promoted reads as one promotion.

Accepted cost: on merge-landed work a transition that occurred only inside
the branch never appears at all, and its event carries the date the branch
merged rather than the date the decision was made, so a long-lived branch
reports late. A second and larger invisibility comes with it: the walk follows
the default branch, so the digest says nothing about the branch its caller is
standing on. Every other check resolves against the merge-base and honors the
branch's own view of the store, which the schema makes normative; the digest
departs from that deliberately, because a catch-up report answers what the
project has accepted rather than what is still in flight. Attributing each
event to its original branch commit would fix the dates, but it would emit
events dated before the range start whenever a long branch
merges inside the window, destroying the since-date as a clean boundary.
