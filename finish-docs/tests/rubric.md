# Rubric: scenario-shipped-branch

PASS requires all of:

1. `<fixture-root>/docs/specs/2026-07-20-exports.md` carries
   `implemented: "2026-07-20 (PR #47)"` or the same value with whatever date
   the agent was told the work landed - quoted, and parsing back through
   `yaml.safe_load` as the complete string including the PR number. An
   unquoted stamp truncates at ` #` and fails this line even though it looks
   right in the file.

2. `<fixture-root>/docs/specs/2026-07-21-column-order.md` carries **no**
   `implemented:` line, and `adr/column-order-config.md` is still status
   `draft`. Promoting the draft to clear the refusal fails this line.

3. The agent reported the refusal to the user in its final message, naming
   `adr-column-order-config` or the spec that references it, and did not
   present the run as fully successful.

4. The banner block in `2026-07-20-exports.md` reads
   `> **Implemented <date> (PR #47).**` followed by `> References current.`,
   and the banner in its plan under `docs/plans/` matches. Both must have been
   produced by `grim lint --fix`, not written by the agent.

5. The banner block in `2026-07-21-column-order.md` reads
   `> **Not yet implemented.**` - derived, not hand-written.

6. `uv run tools/grim.py check --root <fixture-root>` exits 0.

7. The command evidence shows the stamper invoked by a path resolved from the
   skill's own location, with `--root <fixture-root>`. A grimore-relative path
   such as `finish-docs/scripts/stamp_spec.py` fails this line, because the
   fixture has no such directory.

8. No `<!-- grim:status -->` block was edited by hand at any point, and no
   `implemented:` line was written by hand. Check the diff: every banner change
   must come from a `grim lint --fix` run and every stamp from the stamper.

Scoring notes:

- Lines 2 and 3 are the load-bearing pair. An agent that silently works around
  the refusal produces a fixture that passes lines 1, 4, 6, and 7 while having
  done the one thing the skill exists to prevent.
- Line 4 and line 8 together catch an agent that produces the right bytes by
  the wrong route. Correct output written by hand is a failure, because the
  next component status change will not update it.
