---
name: finish-docs
description: Use at branch finish, after tests pass and before opening a pull request, to sync the doc-components store with what the branch actually built. Phase A covers spec discovery and writing the implemented stamp; it refuses specs whose components are still draft, because reconciling drafts against the diff is not built yet.
---

# Finish-docs: Branch-Finish Sync

Runs at branch finish - after tests pass, before the merge or pull-request
step. It reconciles what a branch's spec *intended* against what the branch
actually built, then records that the spec is done.

**This skill is incomplete by design.** Phase A, described here, discovers
specs and writes the `implemented:` stamp. Reconciliation - promoting drafts,
amending them, abandoning and replacing them, writing supersede edges, and
adding note components - is phase B and is **not implemented**. Phase A
refuses any spec it cannot honestly stamp rather than guessing. Read
"What this skill will not do yet" before using it.

## The one boundary that matters

`grim` derives status banners and never writes the stamp. This skill writes
the stamp and never authors banner text.

The banner is a pure function of the component graph, so it is derived,
deterministic, and costs no tokens. The stamp records an event - this branch
finished, on this date, in this pull request - which only the branch-finish
pass witnesses. Neither side may write the other's artifact. If you find
yourself hand-editing text inside a `<!-- grim:status -->` block, stop: the
boundary has been violated and the next `grim lint --fix` will overwrite you
anyway.

## When to run

After the suite is green, and **after the pull request exists** - not before.

The stamp records the pull request number, and it is written once and never
rewritten. So the number has to be known at stamping time. If the pull request
is not open yet, open it as a **draft** first; the documentation delta is then
pushed to that same pull request, riding alongside the code it describes.

Stamping before the pull request exists leaves a stamp with no number, and
nothing in this skill will correct it afterwards.

## Procedure

### 1. Confirm the branch is finished and the pull request exists

Tests pass. The work is complete. Do not run this on a branch still in flight;
the stamp asserts the spec was implemented.

Note the pull request number. Open a draft pull request now if there is none.

### 2. Stamp the specs this branch finished

Resolve `<skill-dir>` from this skill's own location - the plugin installs it
outside the target repository, so a path relative to the working directory will
not find it. Then run:

```bash
uv run --no-project <skill-dir>/scripts/stamp_spec.py \
  --root <target> --branch-diff --date <YYYY-MM-DD> --pr <N>
```

`--branch-diff` discovers every file under the configured specs directory that
the branch added or modified and that carries `components:` frontmatter. Zero,
one, or many; each is handled independently.

`--date` is the day the work landed and `--pr` its pull-request number, digits
only. Pass `--dry-run` first if you want to see what would happen.

Discovery reads the branch diff, which reports **tracked paths only**. A spec
written but never `git add`ed is invisible to it. Stage new specs before
running, or name them with `--spec`.

To stamp a spec the branch diff will never surface - a historical spec that
shipped before this tooling existed - name it explicitly:

```bash
uv run --no-project <skill-dir>/scripts/stamp_spec.py \
  --root <target> --spec docs/specs/<file>.md --date <YYYY-MM-DD> --pr <N>
```

`--spec` is resolved against `--root` and must name a file under the configured
specs directory; anything else is rejected rather than written to.

The script reports one of three outcomes per spec:

- **STAMPED** - written. All referenced components were `current` or
  `superseded`.
- **SKIP** - already stamped. Re-running is a no-op; the stamp is written once
  and never rewritten.
- **REFUSED** - not stamped, with the reason on stderr. Exit code 1.

### 3. Re-derive the banners and commit

```bash
uv run tools/grim.py lint --fix && uv run tools/grim.py render
```

The stamp is an input to banner derivation, so a stamped spec's banner changes
from "Not yet implemented." to "Implemented \<date\> (PR #N)." plus whatever
the component graph says about supersession. Commit the whole delta on the same
branch.

Both commands must succeed as a chain. If `lint --fix` exits non-zero after
fixing, something is wrong beyond the banners - read the findings rather than
re-running.

## Refusals, and what to do about them

A refusal is the skill declining to assert something it cannot verify. Each has
one honest resolution.

**"still draft, so nothing justifies an implemented claim"** - the spec
references a component that was never promoted. Promoting it means deciding
whether the code matches what the draft describes, which is reconciliation, and
reconciliation is phase B. Until then: promote the component by hand after
checking it against the diff, or leave the spec unstamped. Do not stamp around
it.

**"components not in the store, cannot verify"** - the spec names an identifier
no component file carries. Usually a typo or a component that was renamed.
Fix the reference.

**"components: is not a list of strings"** - malformed frontmatter. Fix it;
`grim lint` reports the same problem as `E094`.

**"frontmatter is missing or unparseable"** - the file is not a governed spec.
Either it should not be under the specs directory, or its frontmatter needs
repair.

## What this skill will not do yet

Phase B, tracked on the parent issue, adds the reconciliation half:

- Reconciling each referenced draft against the diff, where **the diff wins on
  disagreement** - specs are intent, code is reality. Built as designed:
  promote. Details differ but the decision stands: amend the draft in place,
  then promote. The decision itself changed: abandon the draft and write a new
  component reflecting reality, so the spec's banner fires and the discrepancy
  is visible. Not built: leave as draft or abandon.
- Writing `supersedes:` edges from promoted components to the older components
  a change invalidates, shown to the reviewer rather than written silently.
- Adding `note` components for new subsystem facts, bounded by the spec's
  declared subsystems and the diff's touched paths rather than an open-ended
  read of the whole diff.
- The no-spec fast path for bugfix, refactor, and chore branches - one question,
  backed deterministically by the touched-path guard.

Until phase B lands, a branch that created draft components still needs a human
to reconcile them. The skill will tell you so rather than pretend otherwise.

## Why the refusal matters

A tool that stamps "implemented" over unverified work is worse than no tool: it
launders a guess into a governed document, and the next reader has no way to
tell a checked claim from an unchecked one. Phase A handles the case it can
prove and declines the case it cannot, which is what makes shipping half of
this skill honest rather than expedient.
