---
id: adr-digest-reads-git-history
type: adr
status: draft
date: 2026-08-01
---

# The catch-up digest derives lifecycle events from git history

A component records the date it was created and never updates it, so the store
cannot say when a draft became live or when a live component was superseded -
and those two transitions are most of what a returning contributor needs. The
digest therefore reads git history over the component store and detects each
transition from the frontmatter change that made it, rather than from the
dates a component carries. Accepted cost: the digest becomes the one grim verb
that needs real history depth, so on a truncated clone it must detect the
graft and label its answer as covering only the history available rather than
presenting a partial result as complete; it is slower than every other verb;
and its since-a-date boundary resolves against committer dates, which a rebase
rewrites.
The alternatives were worse - reporting creation dates alone cannot answer the
question the digest exists to answer, and stamping transition dates into
frontmatter would loosen the rule that a live component may change nothing but
its status.
