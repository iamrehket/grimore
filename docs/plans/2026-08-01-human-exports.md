---
spec: docs/specs/2026-08-01-human-exports.md
---

<!-- grim:status -->
> **Implemented 2026-08-06 (PR #18).**
> References current.
<!-- /grim:status -->

# Human Exports (IAM-45) Implementation Plan

> **For implementation workers:** the fixture apparatus lands first, because
> every later task asserts against it and because the hermeticity defect it
> fixes is already in the suite. Traps are called out inline; all of them are
> silent, and none surfaces as a failing test unless the test is written to
> look for it.

**Goal:** `grim render --digest --since <date>` and `grim render --bundle`,
both printing to standard output, both suppressing the committed write.

This branch is also the **IAM-46 lifecycle gate run** - see Task 11. The nine
drafts this spec produced are the only promote-path input in the store, and
three of them carry supersede edges, which is the criterion the gate could not
otherwise satisfy honestly.

## Task 0: Commit the inputs

Commit the spec, this plan, and the nine draft components before anything
else. `refuse_untracked` in the reconcile script is a hard refusal on
untracked files under the governed directories, so Task 11 fails on first
contact otherwise, and the branch diff that drives spec discovery cannot see
an untracked file either.

## Task 1: Fixture apparatus, and fix the hermeticity defect first

Fix `tests/test_touched_paths.py` before building anything new, so new
fixtures copy a correct pattern rather than the broken one.

`test_stale_local_default_branch_does_not_expand_waiver_range` and
`test_divergent_local_default_branch_is_ignored_when_origin_resolves` both
call `make_repo(upstream)`, then `git clone` into `clone/`, then `commit_all`
in the clone. Git config is per-repository and `git clone` does not copy it,
so those commits carry no configured identity.
`tests/test_adopt_docs.py:29-33` already has the correct shape; apply it after
every clone.

*Trap:* the obvious proof - remove the CI env block, watch the suite pass - is
vacuous. With no identity configured anywhere, git falls back past global
config to hostname auto-detection, which succeeds on any developer machine and
fails only where the hostname cannot be canonicalized. The suite therefore
passes locally whether or not the fix was applied. Reproduce the runner
condition explicitly instead, with a `GIT_CONFIG_GLOBAL` containing
`[user] useConfigOnly = true`. Under that config the failure is deterministic
and scoped: exactly the two tests above fail and everything else passes, which
is also the proof that no other test depends on the workaround.

Only then remove the env block at `.github/workflows/tests.yml:13-19`. It sets
four variables, not two - `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`,
`GIT_COMMITTER_NAME`, and `GIT_COMMITTER_EMAIL` - and removing only the author
pair leaves the workaround half in place.

Build the history-fixture helper on that foundation. It must produce: merge
landings and squash landings in one repository; a component created and
promoted in the same landed commit; several transitions of one component
inside a side branch; a commit dated earlier than its own parent; a commit
adding many components at once; **a commit whose committer offset puts it on a
different UTC day than its local day**; and **a component whose frontmatter
`date` disagrees with the date its history landed**.

*Trap:* `git clone --depth N <local path>` ignores depth and hardlinks the
object store. It does warn, but the tests' `git()` helper checks the return
code and discards stderr, so the warning is invisible in practice. Use a
`file://` URL, and assert `git rev-parse --is-shallow-repository` returns true
rather than assuming the clone worked.

## Task 2: The walker and the event model

First-parent traversal oldest commit first, extracting each component's
`status` across the diff and naming transitions per the spec's events table.
Write one RED test per table row, plus at least two transitions the table does
not contain, asserting they report as lifecycle violations rather than being
skipped or raising.

*Trap:* read the committer date as a Unix timestamp (`%ct`) and convert in
UTC. The reason is **not** that `%cd --date=short` varies by reader - it does
not; it renders in the commit's own recorded offset and is byte-identical
across machine timezones. The defect is subtler and worse: a commit made at
`+1300` just after local midnight reports the day *before* in UTC, so a
`--date=short` implementation lands events on the wrong day while passing
every determinism run in Task 8. The UTC-boundary fixture from Task 1 is the
only thing that catches it - assert the reported day is the UTC day, not the
committer's local day.

*Trap:* do not terminate the walk early on meeting a commit older than the
since-date. Git timestamps are not monotonic, so an older commit proves
nothing about its ancestors. Traverse the whole first-parent line and filter.
A test with a deliberately out-of-order commit is the only thing that catches
a "clever" early exit added later.

## Task 3: Boundary and completeness

`--since` inclusive of the named day, interpreted in UTC. Shallow detection
via `git rev-parse --is-shallow-repository`, and on a shallow clone answer
from the earliest available commit with the output labelled as covering only
available history.

Assert the frontmatter-versus-landing edge here: using the Task 1 fixture
where a component's `date` predates the commit that landed it, a digest whose
since-date falls between the two must still report the component, dated by the
landing.

*Trap:* the label is unconditional on a shallow clone, including when the
graft predates the since-date and the answer happens to be complete. Do not
write a test asserting "complete range implies no label" - that encodes the
bug the spec deliberately rejects, and the reason it is rejected is the same
non-monotonicity as Task 2.

*Trap:* no test may hardcode a since-date. Each locates its transition with
git plumbing directly - never by asking the digest, since a broken walk would
hand the test a boundary that conceals its own breakage - and derives the
boundary from that commit's own date, so a rebase moves both together.

The default-branch ref resolves the way `resolve_merge_base` already does it
(`tools/grim.py:444`): remote-tracking first, then local. Reuse it for the ref
only. It is **not** an incomplete-history detector - it fails when the ref
cannot resolve, which a deep-enough shallow clone does not trigger.

## Task 4: Provenance index

Reverse index from each spec's `components:` frontmatter. Emit repo-relative
paths and abbreviated hashes as plain text; consult no remote.

Three assertions, one per case the spec names: a component claimed by one
spec, a component claimed by none, and a component claimed by two. The
claimed-by-none case is the majority path - 41 of 52 live components - and
needs a named assertion rather than incidental coverage.

*Trap:* build the index only over the configured specs directory. The two
legacy design specs under `docs/superpowers/` carry no frontmatter at all, and
a builder that walks them and assumes a frontmatter block will crash on the
first one. `.grimore.toml` points `specs` elsewhere, so they are out of scope
by configuration - but assert that rather than relying on it.

## Task 5: Digest output

This task integrates Tasks 2, 3, and 4 into one serialized format, and it is
the only place that format is defined. Ordering alone is not enough to build
from - specify and commit to a shape.

Each line carries: the component id, the transition named by its endpoints,
the normative event label from the spec's table, the claiming spec references
when any exist, and the event commit. The shallow-history label, when it
applies, is placed once for the whole run rather than per line. Write a golden
example into the tests covering all six event labels, a lifecycle violation,
the one-spec and no-spec and two-spec provenance cases, and the shallow label,
and assert against it. Without a golden, two workers produce incompatible
layouts while both passing the ordering assertion, and Tasks 3 and 4 can end
up as unused intermediate data.

Commits oldest first, within a commit by component id ascending. Ordering is
by landing, not by component type - `usecase-catch-up-by-landing` is the
authority, and it replaces the wording that said otherwise.

*Trap:* ordering needs its own assertion against a commit touching many
components at once. The determinism test cannot catch an unspecified order,
because the same code emits the same arbitrary sequence on both runs - a
stable-but-unspecified ordering passes a byte-comparison while satisfying
nothing.

## Task 6: Bundle

Live store, ordered as the rendered view orders it, emitted as one
self-contained file carrying the store hash, the revision, and whether the
component store differs from that revision.

*Trap:* the divergence check covers the component store only, not the working
tree. Comparing the whole tree makes output change when an unrelated file is
edited, which contradicts `constraint-deterministic-human-exports` - the
bundle's declared inputs are the store, the configuration, and the revision.

## Task 7: CLI wiring

`--digest` with `--since`, and `--bundle`. Mutually exclusive. `--since`
without `--digest` is an error, not a silent no-op. An export flag suppresses
the compile of the committed rendered view.

*Trap:* assert write suppression by byte-comparing the rendered view before
and after an export run, not by asserting a function was not called. The
second passes if a later refactor moves the write.

## Task 8: Determinism suite

Generate each export twice and byte-compare, once per exclusion the constraint
names: wall clock advanced, machine timezone changed, store enumerated in a
different filesystem order, and **locale changed**. Locale is a separate run
from timezone - `constraint-deterministic-human-exports` names it separately,
and it reaches output through collation and case folding in any sort that is
not explicitly byte-ordered, which the id ordering in Task 5 must be.

*Trap:* the filesystem-order run has to actually vary enumeration order -
build the store in a different creation order in a fresh directory, or patch
the directory iteration. A test that changes nothing passes vacuously and
looks like coverage.

*Trap:* none of these runs can detect a wrong date basis, because a wrong
basis is stable across all of them. Task 2's UTC-boundary assertion is the
only cover; do not treat this suite as covering it.

## Task 9: Real-history assertions

Fixtures prove the walker handles cases someone thought of. These prove it
against history nobody designed.

`adr-payload-renderer-split` supplies both landing shapes on its own. It was
written on a side branch and entered the first-parent line at the pull request
#12 merge on 2026-07-27 - a merge-attribution case. Its promotion landed
squashed on 2026-07-31, a single commit with no merge to attribute it to. A
range covering that date reports the promotion against that commit; a range
starting after it reports no transition for the component at all.

Both assertions locate their commits with plumbing and derive their boundaries
from them, per Task 3's trap. Skip loudly rather than assert when the checkout
is shallow.

## Task 10: Remaining IAM-46 gate items

A restricted-types `.grimore.toml` scenario, as a pytest test rather than a
scenario document, exercising a config that enables a subset of component
types and asserting both exports behave under it.

A run of the full cycle through both plugin hosts per `docs/plugin-hosts.md`.
This one is manual, so it needs a recorded artifact to count as done: the two
host versions it was verified against and the commands run, appended to the
pull request. Without that there is nothing to distinguish a run from a claim.

*Trap:* do not treat this as blocking. `docs/plugin-hosts.md:113` states that
native smoke evidence is recommended release evidence, **not a merge gate** -
it depends on locally installed host CLIs, and a worker who has satisfied
every export requirement can still be unable to run it. Record what was
verified and what was not; do not hold the branch on a host CLI.

## Task 11: Branch finish - the gate itself

Run `finish-docs` rather than promoting by hand, in this order.

**Open the pull request first.** The stamp records its number and is written
once and never rewritten, so the number must exist at stamping time. Nothing
earlier in this plan creates it; open it as a draft before starting this task.

**Stage every governed artifact.** Reconciliation refuses on untracked files
under the components and specs directories. Task 0 committed the inputs, but
anything added since - new components, an amended draft - must be staged too.

**Run the survey.** No verdicts, so it writes nothing, prints the drafts in
scope with the reason each is there, offers a note worklist, and exits 4 -
"input required", not a failure. Rehearsed on 2026-08-06 against the committed
inputs: it found the spec from the branch diff, put all nine drafts in scope,
and confirmed the three live targets are **not** in scope on their own.

**Decide the note worklist.** The survey offers groups of changed files that
no live component claims, capped at five. The 2026-08-06 rehearsal offered two
- `tests/` and `.github/` - from Task 1 alone, and implementation will add
more. Decide deliberately per group whether a `note` component earns its
place; the default is no, since a note is a durable subsystem fact rather than
a record that files changed.

**Then supply a verdict for every component in scope**: the nine drafts, plus
each of the three live targets being replaced. The outcome vocabulary is
`promote`, `amend`, `supersede`, `drop`, `keep-draft` - use those words
exactly.

*Trap:* there is no cascade. Reconciliation deliberately refuses to flip a
live component that no verdict names - the comment on `check_edges_accounted`
is explicit that an auto-cascade "would flip a live decision without anyone
stating that it should be flipped, which is the whole failure this skill
exists to prevent." Each target needs
`--component <target> --verdict '<target>:supersede=<successor>:<why>'`, and
the successor drafts deliberately carry no hand-authored `supersedes:` edge
precisely so the verdict is what writes it. The writer only splices an edge
when the merged set differs from what is already there, so a hand-authored
edge would leave nothing for the tool to write.

The three replacements: `constraint-deterministic-render` by
`constraint-deterministic-rendered-view`, `nongoal-static-site-integration` by
`nongoal-static-site-generator-wiring`, and `usecase-catch-up-digest` by
`usecase-catch-up-by-landing`. All three targets render into `charter.md` or
`decisions.md`, so the flip changes the committed views.

**Dry run before applying anything.** Pass the full verdict set with
`--dry-run` first. It applies the writes, checks them against grim, and rolls
back, so it verifies as strongly as a real run while leaving the tree
untouched. Read the report - every promote, amend, supersede edge and target
flip - and only then run it for real. Reconciliation is the newest code in the
project and this branch is the largest thing it has ever been asked to do;
looking before writing costs one command.

**Then stamp, and verify with the full sequence** - `grim lint --fix`, then
`grim render`, then `grim check`. Check is not optional decoration here: it is
the only step that byte-compares the rendered view, so lint and render alone
can leave a stale view that CI catches instead.

**Re-run reconciliation and stamping once more before committing.** The gate
claims idempotency; nothing proves it unless the second run is actually
performed and reports SKIP rather than writing again.

Then commit the result.

Version: the PR title declares `feat:`. The manifest bump touches
`.claude-plugin/`, which `adr-dual-plugin-manifests` declares - covered by the
standing waiver in `.grimore.toml`, which grim reports as W073, a warning that
does not fail check. No `Grim-Waive` trailer is needed.

No live component declares `paths:` covering `tools/grim.py`, so the
implementation itself trips no touched-path guard. That is a consequence of
`constraint-single-file-cli`, not an oversight.

## Gate criteria, asserted rather than assumed

- a component promoted draft to current by finish-docs, not by hand
- three supersede edges written by finish-docs and shown for review, each with
  its target flipped in the same pass
- a non-empty derived banner on this spec and the inherited banner on this plan
- an `implemented:` stamp applied exactly once, idempotent on re-run
- `grim check` green with no manual edit to the rendered views
- the suite green under a `useConfigOnly` git config with the CI env block
  removed - the local-only form of that check proves nothing
