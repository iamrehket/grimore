---
id: adr-exports-print-to-stdout
type: adr
status: draft
date: 2026-08-01
---

# Human exports are render flags that print to standard output

A live use case fixes how the digest is invoked, naming it as a flag on render
rather than a verb of its own, so introducing a separate export command would
mean superseding a current component in order to reword it. That is the
hard-to-reverse half of this decision: the digest's home is pinned by a live
component, and the bundle joins it there for symmetry rather than because
anything live requires it. Both write only to standard output and neither
accepts an output path, so grim never chooses or manages a location and
nothing it emits reaches the tree unless a caller redirects it there
deliberately.

An export flag also suppresses the compile of the committed rendered view, so
selecting one makes the command genuinely read-only rather than merely
appearing so. Accepted cost: one verb now carries two disjoint behaviours
selected by flag, and a reader of the command line has to know that the flag
changes what the command does rather than adding to it. Adding an output path
later would be purely additive; moving the exports off render would not.
