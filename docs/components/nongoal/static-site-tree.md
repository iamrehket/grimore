---
id: nongoal-static-site-tree
type: nongoal
status: draft
date: 2026-08-01
---

# The static-site markdown tree

The site-ready markdown tree is deferred. Its shape - a file per component or
a file per render target, carrying frontmatter a generator will read or none
at all - is a decision worth making against a real publishing target rather
than guessing at one, and no such target exists yet. Deferred rather than
rejected: nongoal-static-site-generator-wiring fixes where the boundary sits
when the tree arrives, stopping short of wiring any particular generator.
