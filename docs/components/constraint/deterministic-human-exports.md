---
id: constraint-deterministic-human-exports
type: constraint
status: draft
date: 2026-08-01
---

# Human exports are deterministic in their declared inputs

A human export must be byte-identical when regenerated from the same declared
inputs, and nothing outside them - filesystem order, locale, or the time of
the run - may reach the output. The bundle's inputs are the live store, the
configuration governing ordering and render mapping, and the revision it
stamps. The digest's are all of those plus the resolved default-branch
revision, the since-date, and the index of which specs claim which components.
They are enumerated separately because the two exports read different things,
and a guarantee naming only the store would be false for both.

This is weaker than the guarantee the committed rendered view carries, which
grim check enforces by byte-comparing a fresh render. No gate compares an
export, so this constraint is held by tests rather than by a check, and it
exists to make output reproducible for a reader rather than to keep a gate
honest.
