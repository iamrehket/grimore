---
id: adr-compile-dont-patch
type: adr
status: current
date: 2026-07-24
---

# Compile canonical docs, do not patch them

Canonical documentation that is patched in place drifts: concurrent branches
edit the same aggregate file, merges conflict semantically, and the reason a
statement changed survives only in the diff. grimore compiles canonical docs
from small lifecycle-statused components instead - sessions append components
and flip statuses, nothing is surgically edited in place, and superseded
components simply stop rendering into consumer output. The trade-off: the
store accumulates files that are never deleted, and readers must consult the
rendered view rather than the source, in exchange for clean concurrent merges
and a decision history that lives in the store rather than only in git.
