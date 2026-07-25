# Baseline: RED run, scenario-ingest-cache

Date: 2026-07-25, re-scored same day after rubric tightening (not re-run). Sonnet subagent, no align skill, ran the scripted session
single-shot: 6 files, all before its final "stop" message - a constraint, a term, two ADRs, a nongoal, then one spec - after finding
doc-components/SCHEMA.md unprompted and using it for real inline capture.

## Rubric scoring (amended)

1. PASS - term/fetch-record.md valid, draft, correct body.
2. FAIL - wrote adr/fetch-record-staleness-window.md, not adr/serve-stale-24h.md. Content right, ID wrong.
3. FAIL - wrote nongoal/cache-invalidation-api.md, not nongoal/manual-purge.md. Content right, ID wrong.
4. PASS - spec components match created IDs; Decisions indexes all 5 without restating content.
5. PASS - `uv run tools/grim.py lint --root <fixture>`: 0 errors.
6. FAIL (evidence absent) - the run gave a file list plus narrative, not the amended line's required answer-paired final message.
7. FAIL (new) - 2 unscripted extras: constraint/cost-over-latency.md, adr/shared-fetch-record-store.md. Only 3 were scripted.

## Verdict: FAIL (rubric requires all 7)

Lines 2, 3, 6, 7 now fail (was line 2 alone) - closing the gaps this baseline exposed: a diligent agent can nearly pass on discipline alone.

Evidence honesty: all six files were captured inline, before the trap - this baseline does NOT show the never-batch thesis missing; what it
discriminates is slug/ID discipline and component-count restraint (lines 2, 3, 7). Line 6's FAIL is a harness artifact, not a timing failure:
this run's harness never requested the answer-annotated write list the amended rubric requires.
