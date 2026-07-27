---
id: constraint-single-file-cli
type: constraint
status: current
date: 2026-07-24
---

# grim is a single-file, uv-runnable script

grim ships as one Python file, runnable through uv with no install step, no
daemon, and no dependency heavier than a YAML parser; adopting projects vendor
that single file. The constraint keeps adoption to a copy rather than a
package install, and it is why path-level granularity inside grim is
unavailable - every verb lives in the same file, so a path glob cannot
distinguish them.
