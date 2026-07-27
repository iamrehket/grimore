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
