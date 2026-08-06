---
id: nongoal-static-site-generator-wiring
type: nongoal
status: current
supersedes: [nongoal-static-site-integration]
date: 2026-08-01
---

# Static-site generator wiring

Integration with a particular static-site generator - theme wiring, navigation
config, build hooks, deployment - is excluded. The boundary is that grim's
site-ready output stops at clean markdown, and whatever a project already uses
consumes it from there. Excluded because every generator wants its own
frontmatter and directory conventions, so adopting one would either force that
choice on every project or grow a plugin surface per generator.
