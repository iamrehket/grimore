---
id: adr-quoted-stamp-format
type: adr
status: current
date: 2026-07-28
---

# The implemented stamp is quoted on disk

The stamp format carried by the spec template and the original design was
`implemented: 2026-07-24 (PR #12)`, which YAML does not read the way it looks:
in an unquoted plain scalar a space followed by `#` begins a comment, so the
value silently truncates to an unbalanced fragment ending at the parenthesis.
Nothing would have caught this until the reconciliation pass wrote its first
real stamp, at which point the failure would have surfaced as a validation
error one issue away from its cause. The canonical on-disk form is therefore
quoted, a bare date is still accepted and coerced, and every other shape is
rejected with a finding rather than parsed into a fragment. The trade-off: the
stamp is the one frontmatter field whose quoting is load-bearing rather than
cosmetic, which is a rule authors must remember - accepted because the writer
is a script rather than a human, and because the alternative is a value that
parses successfully into something wrong. The general lesson is that a format
demonstrated only in prose has never been executed; the parser and its emitter
must be pinned by a test that round-trips the literal bytes through disk.
