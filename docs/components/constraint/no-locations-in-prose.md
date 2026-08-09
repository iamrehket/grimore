---
id: constraint-no-locations-in-prose
type: constraint
status: current
supersedes: [constraint-no-paths-in-prose]
date: 2026-08-09
---

# Prose names no locations and no code, in any component type

Component prose, in every type, never names a file path as the location of
what the component describes, and never embeds code snippets: a location in
prose goes quietly stale when the file moves, and a snippet the moment the
code changes. Notes and ADRs carry location in machine-readable paths
frontmatter instead, where the touched-path guard can act on it and a rename
shows up as a visible frontmatter change rather than a quietly wrong
sentence; the other types have no substitute carrier, and the location
simply stays out.

Naming a file that is itself the subject of a component's own statement is
legal - so term-path-waiver may name `.grimore.toml`, where the standing
waiver it defines is declared, and adr-commit-type-version-gate may name
`plugin.json`, whose version its gate writes: that name is part of the
statement, and changing it is a loud interface change rather than a silent
move.
