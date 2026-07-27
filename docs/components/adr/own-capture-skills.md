---
id: adr-own-capture-skills
type: adr
status: current
date: 2026-07-24
---

# Own the capture skills, not forks

Upstream superpowers and Pocock skills already cover brainstorming and
branch-finish workflows, so layering on or forking them was the cheaper start.
grimore instead builds its own capture skills - align and finish-docs - while
leaving upstream execution-middle skills (TDD, executing-plans,
subagent-driven-development, worktrees) untouched and in use. Forking would
have bought working capture immediately at the cost of owning an upstream
merge burden forever; owning the capture surface instead keeps inline
component capture a first-class concern rather than a patch grafted onto
someone else's interview flow.
