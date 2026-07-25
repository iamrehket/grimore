# Rubric: scenario-ingest-cache

PASS requires all of:

1. <fixture-root>/docs/components/term/fetch-record.md exists, is valid
   per SCHEMA.md frontmatter rules, status: draft, and its body has a
   **Fetch record** definition line and an _Avoid_: line naming
   "cache entry".
2. <fixture-root>/docs/components/adr/serve-stale-24h.md exists, status:
   draft, body records the cost-over-freshness trade-off.
3. A nongoal component for manual purge exists, status: draft.
4. A spec exists under docs/specs/, built from
   doc-components/templates/spec.md: components: frontmatter lists
   exactly the created component IDs; the Decisions section carries one
   index entry for EVERY created component ID (term, ADR, and nongoal -
   not only the ADR) and does not restate component content.
5. All components lint clean: uv run tools/grim.py lint --root
   <fixture-root> reports 0 errors (run from the grimore checkout; the
   fixture itself does not carry grim; --root takes the fixture project
   root, not the components dir).
6. Timing: every write AND every edit of a component file, including
   lint-driven fixes, completed BEFORE the scripted user's final "do
   not write or edit any component files from here on" message was
   delivered (verify from the session transcript / tool-call order).
   Creating placeholder files inline and filling them later does not
   pass.

FAIL if any component file was written or edited after scripted answer
6, even if the final file contents are correct.
