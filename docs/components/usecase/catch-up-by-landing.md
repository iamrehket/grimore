---
id: usecase-catch-up-by-landing
type: usecase
status: current
supersedes: [usecase-catch-up-digest]
date: 2026-08-02
---

# Catching up after time away

A contributor returning after days or weeks needs to know what changed. grim
render --digest --since answers it directly: every component added, promoted,
abandoned, or superseded since a given date, in the order the work landed,
each carrying the spec it came from or the commit that carried it - without
reading a single dated document end to end. The order follows the landings
rather than the component types, because a returning reader is reconstructing
a sequence of changes, and grouping by type scatters one pull request across
four separate places.
