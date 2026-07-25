# Result: GREEN run, scenario-ingest-cache

Date: 2026-07-25. Sonnet subagent, align/SKILL.md as process instructions,
fresh fixture per run. 8 runs to first PASS (run 8); a confirmation run on
generalized guidance (below) also passed 7/7.

## Failure modes and fixes (runs 1-7, one line each)

1. Extra unscripted components - fix: capture fires only on explicit
   crystallization moments, never the assistant's own framing/recommending.
2. ADR slug added an invented noun ("window") - fix: no category label
   the user didn't say.
3. ADR slug dropped the leading verb ("stale-24h") - fix: keep verb,
   naming word, and measurement together.
4. Usecase regression + nongoal regained "-v1" - fix: reinforced the
   opening-request carve-out; drop the user's own scope/version words.
5. Nongoal slug gained a "no-" prefix - fix: drop negation particles for
   nongoals, the type already signals exclusion.
6. ADR slug self-corrected away from the right form - fix (later
   generalized away): anchor on a colon-label if present.
7. ADR slug picked "old" (glued to the number) over "stale" (the state's
   own name) - fix (later generalized away): prefer the standalone name.
   Traceability, 5->6: fix 2's "no invented noun" rule was already active,
   so this error couldn't repeat as an invented noun - it shifted to
   picking the wrong one of two real user words instead.

## Generalization pass (post-review)

Runs 6-7's fixes were shape-matched to this scenario's sentence shape.
Replaced them, plus the run 1-2 ban-list/template, with four principles:
own nouns/verbs over paraphrase; name the decision not its category; keep
2-4 words, dropping scope/version words and negation particles; when both
a measurement and a name are given, the name wins. Two scenario-blind
examples (no number; with a measurement) replace five overfit ones. Plan
mirror stayed byte-identical; grep for fetch-record/serve-stale/
manual-purge/ingest/cache/rubric/scenario/"pressure test" over SKILL.md
stayed at zero throughout.

## Confirmation run (generalized text): PASS 7/7 (n=1, overfit rules gone)

1. PASS - fetch-record.md valid, draft, definition + Avoid line.
2. PASS - adr/serve-stale-24h.md, draft, cost-over-freshness recorded.
3. PASS - nongoal/manual-purge.md, draft.
4. PASS - spec lists exactly the 3 IDs; Decisions indexes all 3, no
   restatement.
5. PASS - lint: 0 errors, 1 benign unrelated warning.
6. PASS - final message enumerates every write/edit with its answer; all
   writes before answer 5, none after 6.
7. PASS - exactly 3 components; usecase/, constraint/, note/ empty.

## Answer-annotated write timeline (confirmation run)

1. docs/components/term/fetch-record.md - after answer 2
2. docs/components/adr/serve-stale-24h.md - after answer 3
3. docs/components/nongoal/manual-purge.md - after answer 4
4. docs/specs/2026-07-25-ingest-fetch-record-cache.md - after answer 5
(no component file written or edited after scripted answer 6)

## Verdict: PASS (7/7), confirmed on generalized text
