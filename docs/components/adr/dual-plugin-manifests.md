---
id: adr-dual-plugin-manifests
type: adr
status: draft
paths: [.claude-plugin/, .codex-plugin/, .github/scripts/check_version_bump.py, tests/test_marketplace.py, tests/test_version_bump.py]
date: 2026-07-27
---

# One payload, two native plugin manifests

Claude Code and Codex package skills through different manifest locations,
but the skills and their supporting files are already one coherent payload.
Grimore will keep that payload at the repository root and give each agent
harness its own native manifest, with executable checks keeping shared
identity, version, description, author, and skill declarations equivalent. This
avoids moving the skills or introducing a generated distribution tree and
preserves the existing marketplace installation shape. The established Claude
Code manifest remains the authority for shared release metadata, and the
versioning path computes from that authority and writes the resulting version
to both manifests as one rollback-protected operation. Other shared fields are
edited deliberately and parity-checked rather than synchronized implicitly.
The trade-off is that two manifests must change together and every release
path must prove their parity rather than deriving both from a new
platform-neutral metadata file. Moving release authority to another manifest
later is a new migration decision: it must update the merge-base version
anchor, parity contract, and bootstrap behavior together rather than changing
which file wins implicitly.
