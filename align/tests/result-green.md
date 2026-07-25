# Result: GREEN run, scenario-ingest-cache

Date: 2026-07-25. Sonnet subagent, align/SKILL.md as process instructions, fresh fixture per run. 8 runs to first PASS (run 8); two de-overfitting review rounds followed, each with a confirmation re-run.

## Failure modes and fixes (runs 1-7, one line each)

1. Extra unscripted components - fix: capture only fires on explicit crystallization moments, never the assistant's own framing/recommending.
2. ADR slug added an invented noun ("window") - fix: no invented category label.
3. ADR slug dropped the verb ("stale-24h") - fix: keep verb, name, measurement together.
4. Usecase regression + nongoal regained "-v1" - fix: reinforced opening-request carve-out; drop scope/version words.
5. Nongoal slug gained a "no-" prefix - fix: drop negation particles, the type already signals exclusion.
6. ADR slug self-corrected away from the right form - fix (later generalized away): anchor on a colon-label if present.
7. ADR slug picked "old" over "stale" - fix (later generalized away): prefer the standalone name. (5->6: fix 2 was already active, so the error shifted from an invented noun to a real-word choice.)

## De-overfitting round 1

Runs 6-7's fixes were shape-matched to this scenario. Replaced them, plus the run 1-2 ban-list/template, with principles: own nouns/verbs over paraphrase; name the decision not its category; keep 2-4 words, drop scope/version words and negation particles; measurement+name -> name wins. Confirmation run: PASS 7/7.

## De-overfitting round 2

Review flagged the "window/policy/limit/mode/config" parenthetical as still reverse-engineered from run 1. Deleted it. Re-run regressed: ADR slug dropped the action verb ("staleness-24h", no "serve"); nongoal picked the generic lead-in ("invalidation-api") over the specific commitment ("manual-purge"). Fix, principle-level: keep action-name-measurement together when a decision has all three; when the user offers both a generic phrase and a specific term for the same idea, use the specific one.

## Confirmation run (final text): PASS 7/7

1. PASS - fetch-record.md valid, draft, definition + Avoid line.
2. PASS - adr/serve-stale-24h.md, draft, cost-over-freshness recorded.
3. PASS - nongoal/manual-purge.md, draft.
4. PASS - spec lists exactly the 3 IDs; Decisions indexes all 3, no restatement.
5. PASS - lint: 0 errors, 1 benign unrelated warning.
6. PASS - final message enumerates every write/edit with its answer; all writes before answer 5, none after 6.
7. PASS - exactly 3 components; usecase/, constraint/, note/ empty.

## Answer-annotated write timeline (final passing run)

1. docs/components/term/fetch-record.md - after answer 2
2. docs/components/adr/serve-stale-24h.md - after answer 3
3. docs/components/nongoal/manual-purge.md - after answer 4
4. docs/specs/2026-07-25-ingest-caching-layer.md - after answer 5
(no component file written or edited after scripted answer 6)

## Verdict: PASS (7/7), confirmed on twice-generalized text
