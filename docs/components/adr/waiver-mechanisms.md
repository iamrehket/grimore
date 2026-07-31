---
id: adr-waiver-mechanisms
type: adr
status: current
supersedes: [adr-minimal-touched-path-guard]
date: 2026-07-30
---

# Two waiver mechanisms, scoped differently on purpose

The touched-path guard is right to fire when a decision's declared paths move,
and wrong when a declared path churns for reasons the decision does not govern
- a version string, a generated manifest - where the commit trailer has to be
rewritten on every release forever. A standing waiver, declared in
`.grimore.toml` against one component and a named subset of its paths, answers
that case; the per-branch trailer stays the answer when a specific change
happens not to affect the decision. Rejected alternatives: an in-file marker,
because the motivating files are JSON and have no comments, and because it
lets a watched file excuse itself; per-component frontmatter, because only
drafts may be edited in place, so narrowing a glob would cost a supersede of
the very component being narrowed; and inspecting diff content to ignore
changes confined to declared keys, which is precise but is excluded by
nongoal-semantic-drift-detection. Trade-off accepted, and it is the sharp one:
a standing waiver is permanently deaf for the paths it names, so a genuine
restructure of a standing-waived file fires nothing, where a trailer is deaf
once and makes its author re-justify the next bypass. Both are echoed in lint
output so a reviewer sees what is being ignored; the list is kept short.
