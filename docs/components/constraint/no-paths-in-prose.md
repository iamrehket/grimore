---
id: constraint-no-paths-in-prose
type: constraint
status: current
date: 2026-07-24
---

# No file paths or code in component prose

Note bodies state subsystem facts in prose and never name file paths or embed
code snippets, both of which rot silently when files move. The
machine-readable paths frontmatter carries that information instead, where the
touched-path guard can act on it and a rename shows up as a visible
frontmatter change rather than a quietly wrong sentence.
