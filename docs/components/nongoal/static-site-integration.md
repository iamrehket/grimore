---
id: nongoal-static-site-integration
type: nongoal
status: superseded
date: 2026-07-24
---

# Static-site generator integration

grim emits static-site-ready markdown and stops there. Integration with a
particular generator - theme wiring, navigation config, build hooks,
deployment - is excluded. Excluded because every generator wants its own
frontmatter and directory conventions, so adopting one would either force that
choice on every project or grow a plugin surface per generator; emitting clean
markdown lets a project wire up whatever it already uses.
