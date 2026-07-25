# Result: GREEN run, scenario-ingest-cache

Date: 2026-07-25. Sonnet subagent, align/SKILL.md as process instructions,
fresh fixture per run. 8 runs to PASS; runs 1-7 each surfaced one real gap,
fixed in SKILL.md (mirrored in the plan), never in the frozen scenario or
rubric.

## Failure modes and fixes

1. Extra unscripted components (usecase from the opening request, adr from
   the picked approach). Fix: capture fires only on the user's own explicit
   crystallization moment, not the assistant's proposing/recommending; the
   opening request is Problem-section framing, never a usecase trigger;
   approach picks stay in the spec body unless separately called out.
2. ADR slug added an assistant-coined noun ("window"). Fix: ban list of
   category nouns the user didn't say; draw the slug from the user's words.
3. ADR slug dropped the leading verb. Fix: require verb+adjective+number
   together, not just two of the three.
4. Usecase regression + nongoal slug regained a "-v1" suffix. Fix:
   reiterated the opening-request carve-out; drop the user's own
   release/scope qualifiers ("v1") since status: draft already scopes it.
5. Nongoal slug gained a redundant "no-" prefix. Fix: drop a leading
   negation word for nongoals - the type already signals exclusion.
6. ADR slug self-corrected away from the right form mid-session. Fix:
   anchor the slug's adjective on a label the user opened with
   ("Staleness: ...") when present.
7. ADR slug picked the adjective glued to the number ("24h old") over the
   standalone naming word used elsewhere ("stale"). Fix: distinguished
   quantity phrases from the user's standalone naming word; prefer the
   latter.

Run 8: all fixes composed cleanly, no new regressions.

## Rubric scoring, run 8 (PASS, 7/7)

1. PASS - term/fetch-record.md valid, draft, Fetch record definition,
   Avoid line names "cache entry".
2. PASS - adr/serve-stale-24h.md, draft, records cost-over-freshness.
3. PASS - nongoal/manual-purge.md, draft.
4. PASS - spec components: [term-fetch-record, adr-serve-stale-24h,
   nongoal-manual-purge]; Decisions indexes all 3, no restatement.
5. PASS - `uv run tools/grim.py lint --root <fixture>`: 0 errors, 1 benign
   warning (git merge-base, unrelated to content).
6. PASS - final message enumerated every write/edit paired with the
   scripted answer preceding it; all writes before answer 5, none after 6.
7. PASS - exactly the 3 scripted components exist; usecase/, constraint/,
   note/ dirs stayed empty.

## Answer-annotated write timeline (run 8, passing)

1. docs/components/term/fetch-record.md - after scripted answer 2
2. docs/components/adr/serve-stale-24h.md - after scripted answer 3
3. docs/components/nongoal/manual-purge.md - after scripted answer 4
4. docs/specs/2026-07-25-ingest-caching-layer.md - after scripted answer 5

No component file was written or edited after scripted answer 6; the
review pass came back clean with no fixes needed.

## Verdict: PASS (7/7), run 8 of 8
