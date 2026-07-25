# Baseline: RED run, scenario-ingest-cache

Date: 2026-07-25. Subagent (sonnet, no align skill) ran the scripted
session single-shot against the fixture, self-regulating turns.

## What it produced

6 files, all timestamped before its final "stop" message: a constraint,
a term, two ADRs, a nongoal, then one spec. It found doc-components/
SCHEMA.md unprompted and used it for real inline capture, not batching.

## Rubric scoring

1. PASS - term/fetch-record.md valid, draft, correct body.
2. FAIL - wrote adr/fetch-record-staleness-window.md, not
   adr/serve-stale-24h.md. Content right, ID wrong.
3. PASS - nongoal/cache-invalidation-api.md, draft, on-topic.
4. PASS - spec components: matches created IDs; Decisions indexes all
   5 without restating content.
5. PASS - `uv run tools/grim.py lint --root <fixture>`: 0 errors.
6. PASS (weak) - mtimes show writes finished ~44s pre-terminal message;
   no true multi-turn transcript, this was single-shot self-regulation.

## Verdict: FAIL (rubric requires all 6)

Concern: narrower FAIL than expected - only line 2 fails outright, not
missing/batched capture. Agent also over-captured 2 components beyond
the 3 scripted moments. A rerun could plausibly pass by luck on naming;
worth align skill authors' attention.
