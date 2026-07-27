---
id: nongoal-semantic-drift-detection
type: nongoal
status: current
date: 2026-07-24
---

# Semantic drift detection beyond supersede edges

Status banners on specs and plans track explicit supersede edges only. A
decision reversed by a fresh component carrying no `supersedes:` edge fires no
banner, and grimore does not try to infer such reversals by comparing
component content. Excluded because that inference is a semantic judgment that
would be either unreliable or expensive, and edge-writing at branch finish is
a reviewed step precisely so the graph stays honest rather than guessed.
