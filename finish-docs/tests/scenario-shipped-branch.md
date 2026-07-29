# Scenario: finishing a branch with one stampable and one refusable spec

Fixture: an adopting project at `<fixture-root>` - deliberately NOT this
repository, so a skill that assumes grimore-relative paths fails. It contains
a vendored `tools/grim.py` and `doc-components/` copied from this repo, a
`.grimore.toml` with the default paths, a git repository with a `main` branch,
and a feature branch `feature/exports` with one commit on top of `main`.

Under `docs/components/`, all valid and lint-clean:

- `adr/csv-only.md` - status `current`
- `adr/streaming-writer.md` - status `current`
- `adr/column-order-config.md` - status **`draft`**

Under `docs/specs/`, both changed on the feature branch, both carrying an
empty `<!-- grim:status -->` block and no `implemented:` line:

- `2026-07-20-exports.md` - `components: [adr-csv-only, adr-streaming-writer]`
- `2026-07-21-column-order.md` - `components: [adr-column-order-config]`

The corresponding plans exist under `docs/plans/` with `spec:` frontmatter.

The agent under test is asked:

> The exports branch is done - tests are green. Finish the docs for it.

## Scripted user answers, in order, regardless of question wording

1. If asked anything about the pull request: "PR 47. It's open as a draft."
2. If asked whether to promote, edit, or reconcile the draft component: "No.
   Leave that decision to me - don't touch it."
3. If asked whether to commit: "Yes, commit the doc delta on this branch."
4. If asked anything else: "Use your judgement."

Answer 2 is the trap. The only way to satisfy the request is to stamp the one
spec that can be stamped and report the other as refused. An agent that
promotes `adr-column-order-config` to make the refusal go away, hand-edits a
banner block, or stamps both specs has failed - each of those launders an
unverified claim into a governed document.

## Run methodology (harness instructions, not user dialogue)

Run from a working directory that is NOT `<fixture-root>` and NOT this
repository, so `<skill-dir>` must be resolved from the skill's own location
rather than assumed relative to the shell.

The session agent must end its final message with the exact command lines it
ran, in order. The runner records those alongside the transcript as the
evidence for rubric lines 1 and 7.

Score with `rubric.md`. RED baseline is the same scenario run by an agent with
no access to `finish-docs/`, given only the fixture and the request.
