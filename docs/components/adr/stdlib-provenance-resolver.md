---
id: adr-stdlib-provenance-resolver
type: adr
status: draft
paths: [adopt-docs/SKILL.md, adopt-docs/scripts/, tests/test_adopt_docs.py]
date: 2026-07-27
---

# Test adoption provenance in a standard-library resolver

Dual manifests add mismatch and malformed-metadata branches to adoption
provenance, and instruction text alone cannot prove those branches behave
safely. Grimore will put provenance identity resolution behind one small,
read-only helper and test it directly. The helper may use only the Python
standard library and the Git executable that adoption already requires; it
performs no package installation, network access, or file writes. It retains
the Git-first identity ladder, accepts legacy Claude-only bundles, requires
matching native names and versions before using dual-manifest metadata, and
falls back to unknown with a warning when the metadata is unusable. The
trade-off is one new executable surface in the adoption workflow, accepted
because it makes a release-stamping branch deterministic and testable. This
deliberately revises the earlier working-layer preference for no new adoption
runtime without changing that frozen historical plan. The earlier
model-driven bundle remains immutable historical evidence for the Claude-only
workflow; once the helper ships, it is retired as an executable acceptance
fixture rather than combined with a skill that now requires a file the bundle
does not contain.
