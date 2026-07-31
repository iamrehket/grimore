---
id: term-waiver
type: term
status: superseded
date: 2026-07-24
---

**Waiver**: a Grim-Waive trailer in a commit's trailer block, naming a
component and a mandatory reason, that lets a touched-path guard hit pass.
Lint echoes every waiver as W071 so reviewers see each bypass. A waiver covers
its component for the remainder of the branch - the whole merge-base to HEAD
range - not only the change it was written for, so a branch that grows after a
waiver lands needs it re-reviewed.

_Avoid_: override, exemption.
