---
id: nongoal-multi-context-glossary
type: nongoal
status: current
date: 2026-07-24
---

# Multi-context glossaries

One glossary per repository. The CONTEXT-MAP pattern, where a word carries
different definitions in different bounded contexts, is excluded from v1: it
would require every term to declare a context, every consumer to know which
context it reads in, and the Avoid-term lint to become context-aware. Excluded
because a repository whose glossary genuinely needs two conflicting
definitions of one word has a naming problem the glossary should force it to
resolve, not a tooling gap.
