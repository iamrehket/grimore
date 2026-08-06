---
components:
  - adr-digest-reads-git-history
  - adr-digest-walks-first-parent
  - adr-exports-print-to-stdout
  - constraint-deterministic-human-exports
  - constraint-deterministic-rendered-view
  - nongoal-static-site-generator-wiring
  - nongoal-static-site-tree
  - usecase-bundle-without-code-access
  - usecase-catch-up-by-landing
---

<!-- grim:status -->
> **Not yet implemented.**
> Not fully realized: adr-digest-reads-git-history, adr-digest-walks-first-parent, adr-exports-print-to-stdout, constraint-deterministic-human-exports, constraint-deterministic-rendered-view, nongoal-static-site-generator-wiring, nongoal-static-site-tree, usecase-bundle-without-code-access, usecase-catch-up-by-landing still draft.
<!-- /grim:status -->

# Human Exports - Design

Date: 2026-08-01

## Problem

`grim render` writes the committed rendered view and nothing else - its only
options are `--json` and `--root`. Two readers are unserved by that.

A contributor returning after weeks on other projects has no way to ask what
changed. `usecase-catch-up-digest` is live and states the requirement, naming
the invocation directly; the capability behind it has never been built. Its
wording also describes output "grouped by type", which this design does not
produce - see `usecase-catch-up-by-landing`, which supersedes it.

A reader with no checkout - an agent drafting release notes, a reviewer handed
a file in a ticket, a subagent with no filesystem access - cannot reach the
store at all. The rendered view answers the question, but only for someone who
can read the repository.

The site-ready markdown tree, the third export named in the original design,
has no comparable present demand and is excluded here.

## Approach

The digest replays git history. A component's `date` is its creation date and
is never updated, so the store cannot say when a draft became live or when a
live component was superseded - and those two transitions are most of what a
returning contributor wants. The digest walks the first-parent line of the
default branch, oldest commit first, tracks each component's `status` across
the diff, and emits a transition wherever it changes.

Naming that line is what makes the answer consistent. This repository's
history is mixed across adjacent stretches - pull requests #8 and #10 through
#13 landed as merge commits, #14 through #17 landed squashed, and merges
appear earlier still. On a squashed landing, first-parent and a full walk
return the same thing; on a merge, they diverge, and only first-parent makes
the pull request a single event rather than a scatter of intra-branch churn.

The line itself is the configured default branch, resolved the way grim
already resolves it everywhere else - the remote-tracking ref first, then the
local one - so the digest inherits the existing failure behavior when neither
resolves rather than growing a second opinion about what the default branch
is.

Two alternatives lost. A per-file history lookup - find the changed
components, then query each file's own timeline - scales with components
changed rather than commits in range, which wins on a wide range over a busy
repository, but it costs one git invocation per file, loses on the common
narrow range, and has to merge per-file timelines back into one deterministic
sequence. A snapshot diff of the store at the range start against HEAD is far
cheaper and much simpler, but it reports net change rather than history: a
draft promoted and later abandoned inside the window reads as a lone
abandonment, and a component created and superseded in-window disappears
entirely. That is a silent wrong answer, not a missing feature, and it also
cannot attribute an event to a commit.

The bundle needs no walk. It reads the live store, orders it the way the
rendered view does, and emits one self-contained file carrying the store hash
and the revision it was produced from. Because it reads the working tree
rather than a committed revision, it also records whether the component store
differs from the revision it stamps - a fact derivable from those two declared
inputs alone, so a reader is never told a revision describes bytes it does
not. Edits elsewhere in the tree are invisible to the bundle and do not change
its output.

## Events

Every digest line is one transition of one component at one commit, named by
its endpoints. First-parent walking routinely collapses several real
transitions into one landed commit, so the table is normative rather than
derivable - an implementation cannot infer from `absent -> current` whether to
say "added", "promoted", or both.

| From | To | Reported as |
|---|---|---|
| absent | draft | added, draft |
| absent | current | added, live |
| absent | superseded | added, already superseded |
| draft | current | promoted |
| draft | superseded | abandoned |
| current | superseded | superseded |

One line per component per commit, never two. The cost is that a component
born live is indistinguishable from one that spent a week as a draft on a
branch, which `adr-digest-walks-first-parent` had already discarded; the
digest is faithful to what landed rather than to what happened.

Any transition not in the table above - a component disappearing, a live one
returning to draft, a superseded one coming back - is reported as a lifecycle
violation naming both endpoints, rather than skipped. The schema forbids them,
which is exactly why observing one is worth saying: it means a history
rewrite, a hand-edit, or a branch that bypassed lint. This is stated as a rule
against the table rather than as further rows so that a transition nobody
anticipated still has defined behavior.

The digest reads history rather than the governed store, so it reports a
component whose type the project has not enabled. The bundle, compiled from
the store, omits it. That asymmetry is deliberate: a component in a disabled
type directory is a lint error, and a catch-up report that stayed silent about
it would hide the very change that broke lint. It is the same posture as the
violation rule above - say what happened, including what should not have.

Output ordering is commits oldest first, and within a commit by component id
ascending. Within-commit order matters more than it looks: a squashed adoption
commit adds tens of components at once, and without a rule their order would
be whatever the diff happened to yield.
`constraint-deterministic-human-exports` requires byte-identical output, and
an ordering that is merely stable rather than specified would satisfy every
test while remaining undefined for the next implementer. The digest orders by
id alone rather than by date then id as the rendered view does, because a
component's date is its creation date and says nothing about the event being
reported.

## Boundary semantics

The since-date resolves against **committer** date, not author date - the
digest reports what landed, and committer date is when it landed, which is
also what first-parent attribution means. Dates are interpreted in UTC so the
answer does not depend on the machine's timezone, which
`constraint-deterministic-human-exports` requires. `--since` is inclusive: a
transition on the named day is reported.

The walk does not stop early when it meets a commit older than the
since-date. Git timestamps are not monotonic - rebases, cherry-picks, and
clock skew all break the ordering - so an older commit proves nothing about
its ancestors. The walk traverses the whole first-parent line and filters by
date, which costs a full traversal and buys an answer that does not depend on
history being tidy.

Completeness is therefore a property of the clone, not of the walk. The
digest asks the repository directly whether it is shallow. On a truncated
clone it still answers, from the earliest commit available, and labels the
output as covering only the available history - a visibly degraded result,
never a partial one presented as complete. That label is unconditional on a
shallow clone, even when the graft point predates the since-date and the
answer is in fact complete: because timestamps are not monotonic, the digest
cannot prove the truncated region held nothing in range. Over-labelling is the
deliberate choice, and it is the conservative direction.

## Interface

`grim render --digest --since <date>` and `grim render --bundle`, both
printing to standard output.

An export flag suppresses the compile of the committed rendered view, so
neither export mutates the working tree. Only a bare `grim render` writes.
The two export flags are mutually exclusive, and `--since` without `--digest`
is an error rather than a silent no-op.

## Provenance

Each digest line carries two references, and they answer different questions:
the spec whose `components:` frontmatter claims the component, which is where
the component came from, and the commit the event occurred at, which is where
this transition happened. Both appear when both exist.

References are repo-relative paths and abbreviated commit hashes, as plain
text. No remote is consulted, so the export works on a checkout that was never
pushed, and the remote never becomes a determinism input. The cost falls on
the no-checkout reader, who receives a reference they must resolve rather than
a link they can open.

The commit reference is the majority path, not an edge - 41 of 52 live
components are referenced by no spec, because the adoption backfill created
them directly and the two legacy design specs carry no frontmatter at all.
Without it, roughly four fifths of a wide-range digest would carry no
provenance. This is recorded here rather than as a component: the trade-off is
real - a commit is weaker provenance than a spec, and always having one
softens the pressure to govern the legacy tree - but the output format is
cheap to reverse and supersedes nothing, so it sits below the ADR bar.

Where several specs claim one component, all are listed, sorted by filename.
Nothing in lint forbids it and no component is doubly claimed today, but the
schema describes `components:` as the IDs a session created, so two claims on
one component is a store defect rather than a normal case. The rule exists to
keep the output deterministic when one occurs, not because it is expected.

## Acceptance

Four criteria, all executable.

**Fixture coverage.** A synthetic-history fixture exercises every row of the
events table, including the collapsed `absent -> current` case that
first-parent produces from a squashed branch, and at least two schema-forbidden
transitions to confirm both are reported rather than skipped or fatal. Two
further edges matter. First, a component whose `date` disagrees with the
history that carries it: the adoption backfill backdated `date:` to when each
decision was made, so `usecase-catch-up-digest` reads 2026-07-24 while the
commit that wrote it lands on 2026-07-27, and under first-parent the event is
attributed to the merge that carried it. A digest whose since-date falls
between the two must still report it, under the landing date. Second,
non-monotonic timestamps - a commit dated earlier than its own parent -
asserting that the walk still reports transitions older in the graph but newer
by date.

**Real history, both landing shapes.** The history is mixed, so both shapes
need a real assertion, and one component supplies both.
`adr-payload-renderer-split` was written on a side branch and entered the
first-parent line at the pull request #12 merge on 2026-07-27 - a genuine
merge-attribution case. Its promotion landed squashed on 2026-07-31, as a
single commit with no merge to attribute it to. A range covering that date
reports the promotion against that commit; a range starting after it reports
no transition for the component at all.

**Truncation and rewriting.** On a shallow clone the digest answers from the
earliest available commit and labels the output as partial - asserted by
cloning the fixture to a fixed depth and checking both the label and that the
visible events are correct, including the case where the graft predates the
since-date and the label is deliberately conservative. Because a rebase
rewrites the dates the boundary resolves against, no test hardcodes a
since-date: each locates its transition with git plumbing directly, never with
the digest, since a broken walk would otherwise produce a boundary concealing
its own breakage.

**Determinism and provenance.** Each export is generated twice and
byte-compared, with the wall clock advanced, the machine timezone changed, and
the store enumerated in a different filesystem order between runs - one run
per exclusion `constraint-deterministic-human-exports` names, since a repeat
under identical conditions would detect none of them. Ordering gets its own
assertion against a commit touching many components at once, because a stable
but unspecified order passes a repeat-comparison while satisfying nothing.
Provenance gets three cases: a component claimed by one spec, one claimed by
none, and one claimed by two.

## Decisions

- The digest derives lifecycle events from git history rather than the store:
  adr-digest-reads-git-history
- The walk follows the first-parent line, making a pull request one event:
  adr-digest-walks-first-parent
- Both exports are render flags printing to standard output, and selecting one
  suppresses the committed write: adr-exports-print-to-stdout
- Human exports guarantee determinism over inputs enumerated per export:
  constraint-deterministic-human-exports
- The byte-determinism guarantee is scoped to the committed rendered view
  rather than to the render command: constraint-deterministic-rendered-view
- Reading the project's decisions with no code access is a use case the
  project serves: usecase-bundle-without-code-access
- The catch-up digest orders by landing rather than by component type:
  usecase-catch-up-by-landing
- Generator wiring stays excluded, stated as a limit rather than a
  description: nongoal-static-site-generator-wiring
- The site-ready markdown tree is deferred: nongoal-static-site-tree

Three supersessions ride along. Two fix a scope statement rather than change a
decision; the third corrects a description this design contradicts.

None of the three drafts carries a `supersedes:` edge in its frontmatter. The
replacement each one intends is recorded here, and the edge itself is written
at branch finish by an explicit verdict naming the target - reconciliation
refuses a cascade nobody stated, and it will not write an edge that was
hand-authored ahead of it. Recording the intent in prose and letting the tool
write the graph keeps the two in agreement.

`usecase-catch-up-by-landing` supersedes `usecase-catch-up-digest` because the
older text describes output "grouped by type", and this design orders by
landing instead - a returning reader is reconstructing a sequence, and
grouping by type scatters one pull request across four places. The invocation
that component pinned is unchanged, and so is the need it records. Nothing in
lint reads component prose, so without this the store would carry a live use
case describing output the shipped feature does not produce.

`nongoal-static-site-generator-wiring` supersedes
`nongoal-static-site-integration` because the older text opened by asserting
that grim emits site-ready markdown, which describes a capability rather than
fixing a boundary. The exclusion itself is unchanged.

`constraint-deterministic-rendered-view` supersedes
`constraint-deterministic-render` because the older text reads as governing
the render command - "rendering the same store twice" - while this design
makes that same command print human exports that read history the store does
not carry. Scoping the guarantee to the committed artifact resolves it without
weakening anything: every clause of the original survives, and only the scope
sentence is new.

## Out of scope

The site-ready markdown tree, for the reasons in `nongoal-static-site-tree` -
its shape is a decision better made against a real publishing target.

Recording transition dates in component frontmatter. It would make the digest
git-free and fast, but the rule that a live component may change nothing but
its status is load-bearing, and every component predating the change would
carry no history at all.

An end boundary. The only range boundary in this design is the since-date;
nothing here introduces an until-date, and the acceptance criteria are written
to need none.

Remote resolution and clickable links, with the cost stated under Provenance.
Adding them later is additive - a flag, not a change to the default form.

Writing exports to a path. `adr-exports-print-to-stdout` accepts no output
path, so grim never chooses a location and no gitignore handling arises.

Gating exports in CI. No gate compares a human export, by design - the
determinism guarantee is held by tests, and exists to make output reproducible
for a reader.
