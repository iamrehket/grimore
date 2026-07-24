# Triage: spec/plan reconciliation into current-state docs

Date: 2026-07-19
Status: resolved 2026-07-24 — superseded by
docs/superpowers/specs/2026-07-24-doc-components-design.md (survey completed,
design approved, backlog IAM-37..IAM-47 in Linear grimore project). The
custom-workflows-from-scratch direction held.

## Problem

Multi-contributor project using superpowers brainstorming/writing-plans. Pain
points, in no particular order:

- Specs and plans accumulate (append-only, dated) but nothing reconciles them
  into a canonical current-state doc set after a build session completes.
- No mechanism for tracking big architectural changes or decisions (ADRs);
  concurrent sessions by different team members drift out of sync.
- Token budget rules out "rebuild the specs from scratch" passes at the end of
  a development cycle.
- Rough solution instinct: templated doc system / schema for docs + ADRs that
  supports a cheap final pass after design/plan, producing docs that then
  drive agents working the codebase.

## Framing that held up in discussion

Specs/plans are an append-only event log; the missing piece is the
materialized view (current-state docs). You never rebuild a materialized view
from the full log — you apply the delta. The finish-time pass should read only
the branch's spec plus the actual diff, and emit targeted patches to
schema'd, stable-section-ID docs. Token cost then scales with the change, not
the corpus. The explain-diff skill in this repo is the working proof of the
cost model: agent authors a small structured payload; a zero-token script does
all mechanical assembly.

## Concerns raised (ordered by expected pain)

1. **Deriving docs from specs bakes in drift.** Specs are design-time intent;
   implementation deviates (see the post-plan fix commits on explain-diff).
   Sync pass needs two inputs — spec (why) + actual branch diff (what) — and
   the diff wins on disagreement.
2. **Multi-user sync is a merge problem, not a generation problem.** Doc
   patches must ride the same PR as the code, generated at branch-finish time
   (natural hook: finishing-a-development-branch, after tests, before the
   merge/PR menu). Many small per-subsystem doc files, not one ARCHITECTURE.md,
   so concurrent branches merge cleanly.
3. **ADR capture timing.** Format is solved (numbered files, MADR-style,
   status: proposed/accepted/superseded-by, append-only). The failure mode is
   retroactive mining from finished sessions — expensive and lossy because
   rationale lived in dead conversation context. Capture at decision time
   (brainstorm/plan phase) via a structured Decisions block in the spec that
   the finish pass mechanically promotes to ADR files.
4. **Silent staleness.** Derived layer rots when someone merges without the
   pass. Zero-token tripwire: each doc section declares the code paths it
   describes; CI lint flags PRs touching those paths without touching the doc.
   Same trick as explain-diff's write-hashes.
5. **Mentat overlap.** ADRs are durable decisions; CLAUDE.md routes durable
   knowledge to mentat. Leaning repo-canonical (agents working the code read
   them cheaply; versioned and PR-reviewed with the code) with mentat holding
   pointers. Not yet decided.
6. **Keep plans out of the loop.** Plan docs (1400+ lines) are execution
   scaffolding; never feed them to the sync pass. Spec + diff carries
   everything. Probably the single largest token saving.

## Decisions locked in this session

- **Audience: agents first.** Derived docs optimized for coding-agent context
  loading — strict schema, stable section IDs, terse factual prose,
  front-matter metadata. Humans read them tersely.
- **Deliverable shape: reusable skill in grimore** (doc-sync skill + doc/ADR
  templates + mechanical lint script) that any project adopts, rather than a
  one-repo process or skill+CI bundle.

## Open questions (where the session parked)

- How decision capture integrates with whatever workflow replaces/wraps the
  upstream skills. Options discussed before parking: (a) convention via
  CLAUDE.md requiring a structured Decisions block in specs, (b) purely
  additive extraction from spec prose at finish time (token-heavier, lossier),
  (c) fork the brainstorming/writing-plans skills (reliable capture, owns the
  upstream merge burden). Building custom workflows from scratch dissolves
  this — the Decisions block just goes in our own spec template.
- Repo-canonical ADRs with mentat pointers, or mentat-canonical? (See concern 5.)
- Exact hook point and whether the staleness lint ships in v1 or later.
- Which external skill repos have patterns worth adopting (survey in progress
  as of parking).

## Pointers

- Existing artifacts: docs/superpowers/specs/2026-07-13-explain-diff-skill-design.md
  (157 lines) and docs/superpowers/plans/2026-07-13-explain-diff-skill.md
  (1471 lines) — representative of the spec/plan size asymmetry.
- explain-diff skill (this repo) — reference implementation of the
  payload+renderer token-economics split.
- Upstream baseline: https://github.com/obra/superpowers/tree/main/skills
