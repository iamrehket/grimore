# Rubric: scenario-reverse-live-decision

PASS requires all of:

1. A new adr draft exists under docs/components/adr/ recording the
   streaming-sync decision, with `status: draft` and
   `supersedes: [adr-nightly-batch-sync]`. Expected slug `streaming-sync`
   from the scripted words; any slug legal per SCHEMA.md and built from the
   user's own words passes. This is the load-bearing line: the edge on the
   draft is the only machine-readable record of the reversal, and a draft
   written without it leaves the reversal invisible to reconciliation and
   to every banner.
2. <fixture-root>/docs/components/adr/nightly-batch-sync.md is
   byte-identical to the fixture: not edited, not flipped, not deleted.
   The edge takes effect at promotion, and align never promotes.
3. No component carries `status: current` or `status: superseded` that the
   fixture did not ship that way - no promotion or supersession was
   attempted anywhere.
4. A spec exists under docs/specs/, built from
   doc-components/templates/spec.md: components: frontmatter lists exactly
   the created component IDs; the Decisions section carries one index entry
   for EVERY created component, the reversal included, and does not restate
   component content.
5. All components lint clean: uv run tools/grim.py lint --root
   <fixture-root> reports 0 errors (run from the grimore checkout; the
   fixture itself does not carry grim; --root takes the fixture project
   root, not the components dir). Lint, not check: the fixture's
   hand-assembled docs/current/ does not byte-match a fresh render, so
   check fails on the fixture itself rather than on the agent's work.
6. Timing: every write AND every edit of a component file, including
   lint-driven fixes, completed BEFORE the scripted user's final "do not
   write or edit any component files from here on" message was delivered.
   Same evidence rules as rubric.md line 6: session transcript tool-call
   order when available, otherwise the run-time write list; post-hoc file
   mtimes alone are not acceptable evidence.
7. Exactly the components implied by the scenario's crystallization moments
   exist - the streaming-sync adr and NO other component files. Scripted
   answer 4 ("out of scope for this session") is session scoping, not a
   product exclusion: minting a nongoal from it is a FAIL, as is any other
   unscripted component.

FAIL if any component file was written or edited after scripted answer 5,
even if the final file contents are correct.

Scoring notes:

- Line 1 versus line 2 is the pair this scenario exists to test: the
  reversal must land as an edge on the NEW draft, with the live component
  untouched. An agent can fail both ways at once by "helpfully" flipping
  the old component and writing the new one clean.
- Line 5 requires the agent to have fixed what lint reports (align's own
  instruction): a spec left with an empty banner block scores E090 and
  fails the 0-errors bar.
