---
id: adr-never-empty-banner
type: adr
status: current
date: 2026-07-28
---

# A banner block always carries content

The design spec defined banner wording only for implemented specs, which left
the common mid-branch case - a spec with no `implemented:` stamp - rendering
nothing, and an empty block is indistinguishable from a block no script has
ever touched. That ambiguity is not hypothetical: banner derivation was
recorded as shipped for a day and a half while every spec in this repository
carried an empty block that looked exactly like correct output. An unstamped
spec therefore renders "Not yet implemented." rather than nothing, and every
other state renders at least a provenance line, so a populated block is
positive evidence that the deriver ran. The trade-off: the block is never a
silent no-op, so every spec and plan gains a line it did not have before, and
adopting projects see a diff on first run - in exchange for a signal whose
absence is meaningful rather than merely undefined. The rule generalizes to
any script-owned delimiter block: emptiness must never be a valid output,
because no check can distinguish it from a tool that never executed.
