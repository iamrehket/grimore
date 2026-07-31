---
name: finish-docs
description: Use at branch finish, after tests pass and before opening a pull request, to sync the doc-components store with what the branch actually built. Reconciles each draft component against the diff, writes supersede edges, and records the implemented stamp - refusing any claim it cannot verify rather than guessing.
---

# Finish-docs: Branch-Finish Sync

Runs at branch finish - after tests pass, before the merge or pull-request
step. It reconciles what a branch's spec *intended* against what the branch
actually built, then records that the spec is done.

**The diff wins on disagreement.** Specs are intent; code is reality.

## The one boundary that matters

`grim` derives status banners and never writes the stamp. This skill writes the
stamp and the component statuses, and never authors banner text.

The banner is a pure function of the component graph, so it is derived,
deterministic, and costs no tokens. The stamp records an event - this branch
finished, on this date, in this pull request - which only the branch-finish
pass witnesses. Neither side may write the other's artifact. If you find
yourself hand-editing text inside a `<!-- grim:status -->` block, stop: the
boundary has been violated and the next `grim lint --fix` will overwrite you
anyway.

The same rule governs component status. **Never hand-edit `status:`** - the
scripts write it, prove the result legal against grim, and print what changed.
A hand-flip is unaudited and skips the completeness check.

## When to run

After the suite is green, and **after the pull request exists** - not before.

The stamp records the pull request number, and it is written once and never
rewritten, so the number has to be known at stamping time. If the pull request
is not open yet, open it as a **draft** first; the documentation delta is then
pushed to that same pull request, riding alongside the code it describes.

The stamp records the **branch-finish event**, not the merge. Merge is implied
by the file's presence on the default branch.

## Before you start

Resolve `<skill-dir>` from this skill's own location - the plugin installs it
outside the target repository, so a path relative to the working directory will
not find it. `<target>` is the project root. **Every command below passes
`--root <target>` explicitly**; do not rely on the working directory being the
target, and do not `cd` into it to make a shorter command work.

Then, in this order:

1. **`git add` every new spec, plan and component.** The branch diff reports
   tracked paths only, so an unstaged spec is invisible to discovery.
   Reconciliation refuses to run while untracked files sit under the components
   or specs directories, because a completeness check that cannot see a file
   cannot vouch for it.
2. **Commit any `Grim-Waive:` trailers before reconciling.** Waivers are read
   from committed trailers while the guard reads the working tree, so an
   uncommitted waiver does not exist yet.
3. Note the pull request number.

## Procedure

### 1. Survey

```bash
uv run --no-project <skill-dir>/scripts/reconcile.py \
  --root <target> --branch-diff
```

With no verdicts this writes nothing. It prints the drafts in scope, why each
is in scope, and a bounded note worklist, then exits **4** - "input required",
not "something broke". Exit 4 is the normal first step.

A draft reaches the required set three ways: referenced by a spec the branch
changed, created on the branch and referenced by nothing, or named with
`--component`. Every one of them needs a verdict; there is no way to skip one
by staying silent.

### 2. Decide, then reconcile

Read the diff for each draft and pick one outcome. This is the judgement the
tooling cannot make for you.

| Outcome | When |
|---|---|
| `promote` | built as designed |
| `amend` | details differ, the decision stands - edit the draft body first, then pass `amend` |
| `supersede=<new-id>` | the decision itself changed, or an older decision was replaced |
| `drop` | never built, and not worth carrying forward |
| `keep-draft` | not built yet, carries to a future branch |

**An amendment must never reverse a decision's substance.** If it would, that
is not an amendment: write a new component and use `supersede=` instead.

```bash
uv run --no-project <skill-dir>/scripts/reconcile.py \
  --root <target> --branch-diff \
  --verdict 'adr-thing:promote:the writer streams rows exactly as the draft describes' \
  --verdict 'adr-old-way:supersede=adr-thing:replaced by the streaming writer'
```

Every verdict carries evidence - one line, saying why. It is mandatory for all
five outcomes and it lands in the transcript, which is the audit trail.

To reconcile a component no spec references - a backfilled draft recording a
decision the code already implements - name it explicitly:

```bash
uv run --no-project <skill-dir>/scripts/reconcile.py \
  --root <target> --component <id> --verdict '<id>:promote:<why>'
```

`--dry-run` applies the writes, checks them against grim, and rolls back, so it
verifies exactly as strongly as a real run.

### 3. Stamp

```bash
uv run --no-project <skill-dir>/scripts/stamp_spec.py \
  --root <target> --branch-diff --date <YYYY-MM-DD> --pr <N>
```

`--branch-diff` discovers every spec under the configured specs directory that
the branch added or modified and that carries `components:` frontmatter. To
stamp a spec the branch diff will never surface - a historical one that shipped
before this tooling existed - name it with `--spec <path>` instead.

Outcomes per spec: **STAMPED**, **SKIP** (already stamped; re-running is a
no-op), or **REFUSED** with the reason on stderr.

### 4. Re-derive the banners, then verify

```bash
uv run tools/grim.py lint --fix --root <target> \
  && uv run tools/grim.py render --root <target> \
  && uv run tools/grim.py check --root <target>
```

Finish with `check`. It is the CI gate and it does something the first two do
not: byte-compare the rendered views against a fresh render. `lint --fix`
exiting 0 is not evidence that `check` will.

Commit the whole delta on the same branch so it rides the same pull request as
the code.

## The no-spec fast path

Bugfix, refactor and chore branches have no spec, and `--branch-diff` refuses
rather than reporting a completeness it did not check. Run the survey with
`--component` naming nothing, or skip reconciliation entirely, and ask one
question:

> Did this branch change anything a current component describes?

The touched-path guard backs the answer deterministically: a diff touching a
component's declared `paths:` without changing that component fails `grim
check` until a component change or a recorded waiver lands. A missed answer
cannot ship silently. If the answer is yes, write the component and supersede
what it replaces; then run step 4 alone.

## Refusals, and what to do about them

A refusal is the skill declining to assert something it cannot verify. Each has
one honest resolution.

**"untracked files under the governed directories"** - `git add` them. Until
then they are invisible to the branch diff and any completeness claim would be
a guess.

**"--branch-diff discovered no specs"** - either stage the spec, name
components with `--component`, or take the no-spec fast path.

**"conflicting intents for X"** - two verdicts disagree about what X becomes,
usually because a `supersede=` promotes a successor that also carries its own
verdict. Decide which one stands.

**"no verdict accounts for target Y"** - the component being promoted already
carries a `supersedes:` edge naming Y. Promoting it would flip Y silently. Add
`--component Y --verdict 'Y:supersede=<promoted>:<why>'` so the flip is stated.
Do not author `supersedes:` by hand; let `supersede=` write the edge.

**"still draft, so nothing justifies an implemented claim"** - reconcile the
draft before stamping. That is step 2.

**"every component this spec created was abandoned"** - the spec's work was
never built, so it cannot be stamped implemented. Leave it unstamped; the
banner will say it is not implemented, which is true.

**"grim reports N error(s)"** - the store is broken in a way reconciliation
cannot help. Read the findings and fix them first. Nothing was written.

**"grim lint could not evaluate the store"** - grim itself failed to run.
Nothing was written. Fix the environment or the config.

## E070, and the three legal remedies

The touched-path guard fires when a branch changes a path a `current` component
declares without changing that component. **Amending the component is not a
remedy** - only drafts may be edited in place. The three legal answers:

- **Supersede** it with a new component, when the decision genuinely changed.
- **`Grim-Waive:` trailer**, when this branch's change does not affect the
  decision. The trailer must sit in the commit's **final trailer block**,
  with no blank line between it and any other trailer - git parses only the
  last paragraph, so a waiver one line too high is silently not a waiver.
- **`[[grimore.standing_waiver]]`** in `.grimore.toml`, when the path churns
  permanently for reasons the decision does not govern. Scoped to a component
  and a path subset, and permanently deaf for those paths - where a trailer is
  deaf once and makes you re-justify it. Keep the list short.

## Why the refusals matter

A tool that stamps "implemented" over unverified work is worse than no tool: it
launders a guess into a governed document, and the next reader has no way to
tell a checked claim from an unchecked one. The same goes for a draft promoted
when the decision had actually changed - it leaves a `current` component
asserting something false, passing `grim check`, rendering into the agent-facing
view as fact.

Everything here is recoverable from git. What is not recoverable is a reader's
trust that a governed document was checked. So every promote, amend, abandon and
supersede edge is reported before or alongside the write, and an ambiguous case
is refused rather than guessed.
