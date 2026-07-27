---
id: adr-commit-type-version-gate
type: adr
status: current
paths: [.github/scripts/check_version_bump.py]
date: 2026-07-27
---

# Commit type gates the version bump

The plugin ships as the whole repository, so plugin.json's version is the only
signal a consumer has that anything changed - and an adoption once shipped
with the version untouched, leaving the plugin manager nothing to report. CI
now derives a required bump from Conventional Commit types in the pull request
title and every non-merge commit, and fails a consumer-facing change declaring
no type at all rather than reading absence as permission. The baseline moved
to 1.0.0 because pre-1.0 semver cannot express three distinct magnitudes; the
conventional shift collapses feat and fix into one bump. The trade-off: every
consumer-facing pull request now edits the same line of the same file, so
concurrent branches conflict and the second must rebase - the same
serialization already accepted for committed renders - and 1.0 implies a
stability the skills have not yet earned.

The same computation also writes the version rather than only judging it, so a
separate calculator cannot drift from the checker. It applies the level to the
version at the merge-base rather than incrementing the current value, making
the result a pure function of the commit range: idempotent, and willing to
lower a version raised beyond what the commits justify. A deliberate baseline
reset is the one thing no commit type can express, and it survives only behind
a waiver.

The pull request title must declare at least the highest type in the branch. A
squash-merge keeps only the title, so a title that under-declares would leave
the merged history justifying a smaller bump than the one that shipped;
requiring dominance makes the computed version identical before and after a
squash. The cost is a failure mode that reads as pedantic - raise your title
because a commit says feat - in exchange for a version that never depends on
how the branch was merged.
