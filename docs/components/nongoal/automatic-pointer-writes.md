---
id: nongoal-automatic-pointer-writes
type: nongoal
status: current
date: 2026-07-24
---

# Automatic external-store pointer writes

finish-docs does not write pointer or status records into external knowledge
and tracking stores automatically; keeping such a store in sync remains a
session-level habit. Excluded because automatic writes would couple the
reconciliation pass to a specific external tool that not every adopting
project has, and that coupling is hard to undo once workflows depend on it.
Revisit after v1, once the manual habit has shown what is actually worth
writing.
