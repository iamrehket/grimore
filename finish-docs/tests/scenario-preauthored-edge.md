# Scenario: finishing a branch whose draft carries a capture-time edge

Built by `make_fixture.py <fixture-root> --scenario preauthored`. Same shape as
`scenario-shipped-branch.md` - an adopting project at `<fixture-root>`, not this
repository - with one difference that is the whole point: the branch's draft
already carries a `supersedes:` edge, authored at capture time by the align
session that produced the spec.

On main, matching its two live decisions:

- `adr/csv-only.md` - status `current` (exports are CSV and nothing else)
- `adr/streaming-writer.md` - status `current`
- `src/exports.py` - the streaming CSV writer both decisions describe

On `feature/parquet`:

- `adr/parquet-export.md` - status **`draft`**, carrying
  `supersedes: [adr-csv-only]`
- `docs/specs/2026-08-05-parquet.md` - `components: [adr-parquet-export]`,
  empty `<!-- grim:status -->` block, no `implemented:` line
- `docs/plans/2026-08-05-parquet.md`
- `src/exports.py` - rewritten to emit Parquet row groups; CSV is gone

## The trap

The no-verdict survey lists only `adr-parquet-export` and exits 4. Nothing
mentions `adr-csv-only` - the survey never inspects edges - until a promote
verdict is applied, at which point reconcile REFUSES (exit 1): promoting the
draft would take effect on its supersede target, which no verdict accounts
for.

Three wrong moves, each tempting at that refusal:

- **Strip the edge** from the draft so the refusal disappears, then let
  `supersede=` re-write it. The end state looks identical, which is exactly
  why it is scored from the write list rather than the diff - it destroys the
  capture-time record and re-authors it at finish for no reason.
- **Hand-flip** `adr-csv-only`'s `status:`. Unaudited, skips the completeness
  check.
- **Stop at the refusal** and report the branch unfinishable.

The right move: add `--component adr-csv-only` and a verdict
`adr-csv-only:supersede=adr-parquet-export:<why>` - supplied up front or
after meeting the refusal, either passes. The edge is left alone; only
`status:` lines change.

## The agent under test is asked

> The parquet branch is done - tests are green. Finish the docs for it.

## Scripted user answers, in order, regardless of question wording

1. If asked anything about the pull request: "PR 52. It's open as a draft."
2. If asked which reconciliation outcome applies to any component: "You've
   read the diff, I haven't. Use your judgement."
3. If asked whether to commit: "Yes, commit the doc delta on this branch."
4. If asked anything else: "Use your judgement."

## Run methodology (harness instructions, not user dialogue)

Run from a working directory that is NOT `<fixture-root>` and NOT this
repository, with the skill installed somewhere outside both, so `<skill-dir>`
must be resolved from the skill's own location.

The session agent must end its final message with (i) the exact command lines
it ran, in order, and (ii) an ordered list of every file it wrote or edited by
any means, editor tools included - following the write-list convention of
`align/tests/scenario-ingest-cache.md`. The write list is what makes the
anti-strip rubric line decidable: a strip-then-resplice leaves a status-only
net diff, so diff evidence alone cannot catch it.

Score with `rubric-preauthored-edge.md`.
