# Baseline: RED run, scenario-ingest-cache

Date: 2026-07-25, re-scored same day after rubric tightening (not
re-run). Sonnet subagent, no align skill, ran the scripted session
single-shot: 6 files, all before its final "stop" message - a
constraint, a term, two ADRs, a nongoal, then one spec - after finding
doc-components/SCHEMA.md unprompted and using it for real inline
capture.

## Rubric scoring (amended)

1. PASS - term/fetch-record.md valid, draft, correct body.
2. FAIL - wrote adr/fetch-record-staleness-window.md, not
   adr/serve-stale-24h.md. Content right, ID wrong.
3. PASS - nongoal/cache-invalidation-api.md, draft, on-topic.
4. PASS - spec components match created IDs; Decisions indexes all 5
   without restating content.
5. PASS - `uv run tools/grim.py lint --root <fixture>`: 0 errors.
6. INSUFFICIENT - amended line needs the run's own final message to
   pair each write with its answer number; this run gave a separate
   file list plus narrative instead. Mtimes no longer qualify alone.
7. FAIL (new) - 2 unscripted extras: constraint/cost-over-latency.md,
   adr/shared-fetch-record-store.md. Only 3 were scripted.

## Verdict: FAIL (rubric requires all 7)

Lines 2, 6, 7 now fail (was line 2 alone) - closing the gap this
baseline exposed: a diligent agent can nearly pass on discipline alone.
