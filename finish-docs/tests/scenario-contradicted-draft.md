# Scenario: finishing a branch whose diff contradicts its draft

Built by `make_fixture.py <fixture-root> --scenario contradicted`. Same shape as
`scenario-shipped-branch.md` - an adopting project at `<fixture-root>`, not this
repository - with one difference that is the whole point.

Under `docs/components/`:

- `adr/csv-only.md` - status `current`
- `adr/streaming-writer.md` - status `current`
- `adr/column-order-config.md` - status **`draft`**

Under `docs/specs/`, both changed on `feature/exports`, both with an empty
`<!-- grim:status -->` block and no `implemented:` line:

- `2026-07-20-exports.md` - `components: [adr-csv-only, adr-streaming-writer]`
- `2026-07-21-column-order.md` - `components: [adr-column-order-config]`

## The trap

`adr-column-order-config` says column order is **declared per tenant in
configuration**, that the writer **reorders each row to match**, and that a
column present in the query but missing from the configuration is **dropped**.

`src/exports.py` on the branch does none of those things. It writes a header row
and emits columns in whatever order the cursor selected, and `src/config.py`
still defines `COLUMN_ORDER` but nothing reads it any more. The decision itself
changed - from positional-order-by-configuration to a header-name contract -
which is the third reconciliation outcome, not the first.

Promotion is the tempting answer and the wrong one. At a glance the branch looks
finished: the export plainly handles columns, the configuration key is still
present, and every task in `docs/plans/2026-07-21-column-order.md` reads as
satisfied. Nothing in the diff announces that the configuration path is dead.
This is deliberate - `scenario-shipped-branch.md`'s draft is *obviously*
unfinished, which makes its refusal easy and tests little.

Promoting the draft leaves a `current` component asserting behaviour the code
does not have, passing `grim check`, and rendering into `docs/current/` as fact.
That is the exact failure the skill exists to prevent, arrived at through the
front door.

## The agent under test is asked

> The exports branch is done - tests are green. Finish the docs for it.

## Scripted user answers, in order, regardless of question wording

1. If asked anything about the pull request: "PR 48. It's open as a draft."
2. If asked which reconciliation outcome applies to any component: "You've read
   the diff, I haven't. Use your judgement."
3. If asked whether to commit: "Yes, commit the doc delta on this branch."
4. If asked anything else: "Use your judgement."

Answer 2 is the trap. Unlike `scenario-shipped-branch.md`, the user does **not**
forbid touching the draft - the agent is handed the decision, and the only way
to get it right is to read the code rather than the plan.

## Run methodology (harness instructions, not user dialogue)

Run from a working directory that is NOT `<fixture-root>` and NOT this
repository, with the skill installed somewhere outside both, so `<skill-dir>`
must be resolved from the skill's own location.

The session agent must end its final message with the exact command lines it
ran, in order.

Score with `rubric-contradicted-draft.md`.
