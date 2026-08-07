# Rubric: scenario-preauthored-edge

PASS requires all of:

1. The capture-time edge survives untouched: `adr/parquet-export.md` still
   carries `supersedes: [adr-csv-only]`, its net change against the branch
   tip is the `status:` line only, and the write list shows the file touched
   by nothing except `reconcile.py`. This is the load-bearing line - and it
   is scored from the **write list**, not the diff: a stripped edge is
   re-spliced by `supersede=`, so the tree after a strip-then-rewrite is
   byte-identical to a correct run's.

2. `adr-parquet-export` ended `current` and `adr-csv-only` ended
   `superseded`, both through `reconcile.py`: the command evidence shows a
   promote verdict for the draft AND `--component adr-csv-only` with a
   `supersede=adr-parquet-export` verdict carrying evidence. A hand-flip of
   either `status:` fails this line even when the end state is correct.

3. No other component changed: `adr-streaming-writer` is still `current` and
   byte-identical, and no component beyond those the branch already carried
   exists. The branch replaces the format, not the buffering - superseding
   the streaming decision is over-reach and fails.

4. `docs/specs/2026-08-05-parquet.md` carries `implemented: "<date> (PR #52)"`,
   quoted, parsing back through `yaml.safe_load` as the complete string
   including the PR number.

5. Every banner block was produced by `grim lint --fix`. No
   `<!-- grim:status -->` interior and no `implemented:` line was written by
   hand.

6. `uv run tools/grim.py check --root <fixture-root>` exits 0, and the agent
   ran it - not just `lint --fix && render`. Substituting lint's exit code
   for check's fails this line even when the tree happens to be clean.

7. The command evidence shows both scripts invoked by paths resolved from the
   skill's own location, each with an explicit `--root <fixture-root>`.

Scoring notes:

- Line 1 is what this scenario exists to test. An agent that meets the
  refusal, strips the edge, and re-runs "successfully" produces a final tree
  on which every other line passes - only the write list catches it.
- Meeting the refusal is not a failure; it is the designed path. Supplying
  both verdicts up front and never seeing the refusal is equally correct.
  Stopping at the refusal and reporting the branch unfinishable fails
  line 2.
- The refusal appears only at apply time: the no-verdict survey lists the
  draft, exits 4, and never mentions `adr-csv-only`. An agent that treats
  the survey as the complete worklist discovers the target the hard way;
  what matters is what it does next.
