---
name: adopt-docs
description: Use when the user asks to adopt the doc system, set up doc components, or onboard this repo to grimore. Interviews for configuration one question at a time, vendors grim and doc-components into the target, writes .grimore.toml, installs the managed CLAUDE.md/AGENTS.md instruction sections, and (in later steps of this same skill) offers CI and a charter-seeding interview - safely, resumably, and collision-aware.
---

# Adopt-docs: Onboarding a Repo onto grimore's Doc-Components System

This skill turns a repo that has never seen grimore's doc-components
system into one that has: a validated `.grimore.toml`, a vendored copy of
`tools/grim.py` and `doc-components/`, a component layout for the enabled
types, and managed instruction sections in `CLAUDE.md` and/or `AGENTS.md`.
Later steps of this same skill (not yet written as of this section) cover
the managed-section body itself, the CI workflow offer, merge discipline,
the charter-seeding interview, and the final commit/PR offer.

Requirements doc: `doc-components/SCHEMA.md`. Templates:
`doc-components/templates/`. CI recipe: `doc-components/CI.md`. Sibling
skill: `align/SKILL.md` (the interview style below follows its
one-question-at-a-time, AskUserQuestion-style discipline). Nothing here
special-cases grimore's own repo - adopting grimore onto itself is a
separate exercise, not this skill's job to detect or shortcut.

When the repo is already `adopted` and merely unhealthy (lint/check
failing), this is the wrong skill - hand it to finish-docs or ordinary
`grim lint --fix` / `grim render` remediation instead. Adoption repair
(the resume-repair flow below) exists for incomplete or invalid adoption
footprints, never for a complete footprint that has drifted out of lint
cleanliness.

## Prerequisites

Check these, in order, before anything else - including before
classifying the repo's state. A repo that fails any of them cannot be
classified or mutated safely.

1. **`git` is present** and the working directory is a non-bare work tree
   with a resolvable root (`git -C <target> rev-parse --show-toplevel`
   succeeds and does not report a bare repository). Stop otherwise.
2. **At least one commit exists** (`git -C <target> log -1` succeeds). A
   repo with no history has no fixed point for the adoption commit, the
   feature-branch offer, or the provenance ladder's toplevel checks. If
   there is no commit, **stop before any mutation** and ask the user to
   create the initial commit themselves. This skill never creates one -
   not as a courtesy, not as a deferred step to revisit later. There is
   no deferred-check mode for this: the check runs, and blocks, every
   time.
3. **`uv` is present** (`command -v uv`). Stop with a plain install
   pointer if it is not - every verb this skill runs (`lint`, `render`,
   `check`) goes through `uv run tools/grim.py ...`.

## Classifying the current state

State and health are two different questions. State asks "is the
adoption footprint here, complete, and valid?" Health asks "given a
complete footprint, does it currently lint and check clean?" Never
conflate them: an incomplete or invalid footprint is `partial` regardless
of how clean the pieces that do exist happen to be, and a complete,
valid footprint that fails lint is still `adopted` - just unhealthy.

### State: not adopted / partial / adopted

- **not adopted** - no recognizable adoption artifact anywhere: no
  `.grimore.toml`, no stamped vendored `tools/grim.py`, no managed
  section in either root instruction file, no configured layout
  directory.
- **partial** - at least one recognizable adoption artifact exists, but
  the stable footprint below is incomplete, invalid, or stale.
- **adopted** - every one of the following holds:
  - `.grimore.toml`'s `[grimore]` table **explicitly contains all six
    grim-owned keys with the expected types**: `components`, `current`,
    `specs`, `plans`, `default_branch`, `types`. Check this by an
    explicit-presence read of the raw table's keys, not just by calling
    `load_config` - `load_config` fills in defaults for anything omitted,
    so a config that never persisted the interview's actual answers
    still "succeeds" without being adopted. Presence is necessary but not
    sufficient on its own either: the bundle's `load_config(root)` must
    also succeed against those values (semantic validity - types are
    strings/lists of the right shape, types are all recognized component
    types, paths resolve inside the root).
  - `instruction_files` (read and validated separately - see below)
    validates.
  - The vendored payload is recognized: the stamp line is present on
    `tools/grim.py` and every byte below it matches the bundled source
    (see Bundle-side execution and stamp verification below).
  - Layout directories exist for every enabled type.
  - Every file named in the validated `instruction_files` disposition
    carries **exactly one** well-formed managed section, and that
    section's body **matches the current template rendered for the
    persisted config and disposition** (the template itself is defined
    under Managed instruction sections, below - not yet written in this
    file as of this section, but the match rule is binding now: a
    missing, duplicate, malformed, or stale/hand-edited section means
    the file's disposition is `managed-stale`, not adopted, full stop).
  A missing, duplicate, malformed, or stale managed section always
  classifies the repo `partial`, never `adopted` - the stale-repair path
  described below must stay reachable, and it can only be reached from
  `partial`.

### `instruction_files`: a separate, stricter read

`instruction_files` is not a grim-owned key - `load_config` ignores it
entirely and `Config` never exposes it. Read it with its **own raw
`tomllib` parse** of `.grimore.toml` (do not derive it from
`load_config`'s output) and validate it as: a **duplicate-free subset of
exactly the two literal strings `"CLAUDE.md"` and `"AGENTS.md"`** - no
other names, no paths, no case variants. **The empty list is illegal** -
a fully-declined disposition is refused at interview time (see the
interview below), so a persisted `[]`, or any list containing anything
outside that two-element set, or containing a duplicate, classifies
`partial` (`invalid`) and names every defect found (not just the first
one). A hostile value (a path-traversal-shaped string, an absolute path,
anything not literally `"CLAUDE.md"` or `"AGENTS.md"`) is a validation
failure to report, never a path to open, read, or write - reject on
inspection of the string itself, before ever attempting to resolve it as
a filesystem path. The classifier reads and writes instruction content
only at these two allowed root files, never at any derived or
alternate path.

### Bundle-side execution and stamp verification

Never execute unverified target code. Classification and any preflight
parsing of `.grimore.toml` or a target's `tools/grim.py` run through
**this skill's own bundled `tools/grim.py`** (the copy shipped alongside
this SKILL.md, resolved at `../tools/grim.py` relative to this skill's
own directory) - never a target repository's pre-existing copy, no
matter how plausible it looks. A target's `tools/grim.py` is executed
only after both of the following pass:

1. Its first line matches the stamp pattern exactly (see Vendoring,
   below) - `# Vendored from iamrehket/grimore by adopt-docs on
   <YYYY-MM-DD>. Source: <identity>.`
2. Every byte after that first line is byte-identical to this skill's
   own bundled `tools/grim.py`.

If either check fails, report the file as `conflicting` in the inventory
and never execute it, never overwrite it without consent, and never treat
its presence as adoption progress.

This bundle-side rule governs *existing, untrusted* target content. It
does not apply to a `tools/grim.py` this same session just wrote during
vendoring (below) - that file's bytes are known-good by construction (the
session wrote them from the bundle a moment earlier), so the mutation
sequence's own validation step runs the target's own freshly-vendored
copy directly, exactly as shown in the mutation sequence below.

### Per-artifact inventory and dispositions

Before any write, inventory every artifact this skill could touch and
classify each with one of:

- **exact match** - already correct; keep, do not rewrite.
- **absent** - safe to create.
- **managed-stale** - recognizably ours (matching stamp, or a
  well-formed but outdated/hand-edited managed section) but not current;
  safe to update only after a preview and explicit consent.
- **conflicting** - present, unrelated or hostile content, not
  recognizably ours; stop and ask, never overwrite, never execute.
- **invalid** - present, recognizably an attempt at this artifact, but
  fails validation (malformed TOML, semantically invalid config,
  hostile `instruction_files`); report the **verbatim** parse or
  validation error and stop - never silently repair, never overwrite
  without consent.

This taxonomy applies uniformly to every mutation target this skill
manages: `.grimore.toml`, the vendored `tools/grim.py` and
`doc-components/` payload, layout directories, the instruction-file
managed sections, and (in a later step of this skill) the CI workflow
file and branch protection. Malformed TOML is always reported with its
parse error, never silently overwritten.

### Resume and repair

When the state classifies `partial`, the session may be resuming a prior,
interrupted adoption, or repairing a hand-made attempt. Either way:

1. Build the full per-artifact inventory above.
2. Present it to the user along with a preview of exactly what a repair
   would change (which files, which keys, which sections - not just "I'll
   fix it").
3. Proceed with the repair only after explicit consent. Never repair
   silently, never repair as a side effect of an unrelated answer.
4. A repair touches only what is missing, invalid, or stale - it never
   rewrites an artifact already at exact match, and it never has side
   effects on unrelated files (e.g., fixing `.grimore.toml`'s explicit
   keys never touches instruction-file content, and vice versa).

   Worked example: if only `CLAUDE.md`'s managed section is stale (hand-
   edited, no longer matching the template) and `AGENTS.md`'s section is
   already at exact match, the repair rewrites `CLAUDE.md`'s section only
   - `AGENTS.md` is left byte-untouched.

### Health (only after `adopted`)

Once - and only once - the state classifies `adopted`, optionally run
`uv run tools/grim.py lint --root <target>` and `check --root <target>`
and report healthy or unhealthy. Health never changes the state
classification: an `adopted` repo that fails lint or check is still
`adopted`, just unhealthy, and belongs to ordinary grim remediation (or
finish-docs), never to this skill's adoption-repair flow.

## Configuration interview

The interview is not skippable and its answers are not something to
infer from the opening request. Ask one question at a time,
AskUserQuestion-style (2-4 concrete options where the choice is
enumerable) - never a wall of questions in one message, and never proceed
past a question without an explicit answer from the user. Cover, in this
order:

1. **Paths.** Present the four `DEFAULTS` (`components`, `current`,
   `specs`, `plans`) as one confirmable set, with the option to override
   any individual one. Do not ask about each path separately unless the
   user wants to change one - the default framing is "these four, as a
   set, or tell me which to change."
2. **Enabled types.** Default: all six (`adr`, `term`, `usecase`,
   `constraint`, `nongoal`, `note`). State in one line what disabling a
   type means: crystallization moments of that type get skipped later
   (recorded, never captured as a component) rather than refused
   outright.
3. **Default branch.** Detect via `git symbolic-ref
   refs/remotes/origin/HEAD` (strip the `refs/remotes/origin/` prefix);
   if that fails (no remote, or the symbolic ref is unset), fall back to
   the current branch (`git rev-parse --abbrev-ref HEAD`). Ask the user
   to confirm the detected value - never persist a detected branch
   without confirmation.
4. **Instruction-file disposition.** Default: both `CLAUDE.md` and
   `AGENTS.md`. At most one may be declined - never both, since a fully
   empty disposition is illegal (see `instruction_files` validation
   above). State the consequence of declining plainly: the declined
   harness gets no instructions from this adoption. Persist the result
   as `instruction_files` under `[grimore]`.

The written `.grimore.toml` always contains all six grim-owned keys
explicitly - even when every answer was the default. "The user picked
the default" and "the key was never asked about" must remain
distinguishable in the persisted file; only the interview, not omission,
produces a default value in the config.

## Mutation sequence

Order of operations, this skill's full scope (later steps below are not
yet written in this file as of this section, so their place in the
sequence is named here and detailed when they land):

1. Inventory (per the classifier above).
2. Read-only GitHub inspection (classic branch protection, rulesets, and
   the merge-queue state derived from that same read), when a verified
   GitHub remote exists - detailed under GitHub identity and branch
   protection, below.
3. Vendor + layout.
4. Write `.grimore.toml`.
5. Validate with the vendored linter.
6. Instruction sections - detailed under Managed instruction sections,
   below.
7. CI workflow - detailed under Merge discipline and CI workflow, below.
8. Charter - detailed under Charter interview, below.
9. Finish - detailed under Finishing an adoption, below.

This section covers steps 1, 3, 4, and 5 in full; step 2 is named here
for sequencing but detailed under GitHub identity and branch protection.

### `.grimore.toml`

Write exactly this template, substituting the interview's answers for
every value (this is the default-answers rendering; override any line
whose interview answer differed):

```toml
[grimore]
components = "docs/components"
current = "docs/current"
specs = "docs/specs"
plans = "docs/plans"
default_branch = "main"
types = ["adr", "term", "usecase", "constraint", "nongoal", "note"]
instruction_files = ["CLAUDE.md", "AGENTS.md"]
```

All six grim-owned keys appear explicitly, plus `instruction_files`. No
key is ever omitted in reliance on `load_config`'s defaults.

### Vendoring

Copy, resolved relative to this skill's own directory (`../tools/grim.py`
and `../doc-components/` - valid both in a live checkout and inside a
packaged plugin cache):

- `tools/grim.py` -> `<target>/tools/grim.py`
- `doc-components/SCHEMA.md` -> `<target>/doc-components/SCHEMA.md`
- `doc-components/templates/` -> `<target>/doc-components/templates/`
- `doc-components/CI.md` -> `<target>/doc-components/CI.md`

`doc-components/examples/` is never copied.

Write the vendored `tools/grim.py` as a stamp line followed by the
bundled file's bytes unchanged:

```
# Vendored from iamrehket/grimore by adopt-docs on <YYYY-MM-DD>. Source: <identity>.
```

`<YYYY-MM-DD>` is today's date. `<identity>` comes from this ladder,
tried in order, first rung that fires wins:

1. **Git identity** - accepted *only* when `git -C <skill-dir>
   rev-parse --show-toplevel` (run from this skill's own directory)
   succeeds, the resolved root itself carries a
   `.claude-plugin/plugin.json` whose `name` is `"grimore"`, and that
   root is different from the adopting target's own root (`git -C
   <target> rev-parse --show-toplevel`). When all three hold, the
   identity is the commit at that verified root (`git -C <verified-root>
   rev-parse HEAD`). **Never resolve identity by running `git -C
   <skill-dir> rev-parse HEAD` without the toplevel-and-manifest
   verification first** - an unqualified `git -C <dir> rev-parse HEAD`
   resolves through parent directories when `<dir>` has no `.git` of its
   own, so a bundle nested inside the target repo's tree, with no `.git`
   of its own, would otherwise silently resolve to and stamp the
   *target's own* commit as if it were grimore's. That is exactly the
   failure this rung exists to prevent.
2. **Bundle manifest** - when rung 1 does not fire (typically: the
   bundle carries no `.git` at all, the common packaged-plugin case),
   read `<skill-dir>/../.claude-plugin/plugin.json`'s `version` field and
   stamp `grimore plugin v<version>`.
3. **Unknown** - when neither rung above produces a usable value, stamp
   the literal `unknown`.

The identity is never invented and never the adopting repository's own
HEAD under any circumstance - rungs 1 and 2 are the only two sources of
a real identity, and rung 1's toplevel-and-manifest gate is what keeps a
nested, `.git`-less bundle from ever being confused with the target.

### Layout

For every enabled type, create `<components>/<type>/` with a `.gitkeep`
placeholder if the directory would otherwise be empty. Disabled types get
no directory at all - do not pre-create a directory "in case it gets
enabled later."

### Validate

Run `uv run tools/grim.py lint --root <target>` (using the target's own,
now-vendored copy, since this session just wrote it and its bytes are
known-good). Exit 0 is expected on the still-empty store - a clean lint
here confirms the config and layout are structurally sound before moving
on to instruction sections, CI, and the charter.

## Managed instruction sections

Write the identical delimited section below to every file named in the
validated `instruction_files` disposition (default: both `CLAUDE.md` and
`AGENTS.md`; never a file the disposition excludes). This is the single
artifact the state classifier's managed-section match rule (above) checks
against - render it exactly, do not paraphrase any clause, and do not add
or drop a line:

```
This project uses grimore's doc-components system. At the start of every
session, read `<current>/` - it is the current, agent-facing view of the
project's decisions, use cases, constraints, and glossary.
`<current>/glossary.md` settles terminology; use its terms, not synonyms.

Specs and plans produced in this project go under `<specs>/` and
`<plans>/` respectively (not the upstream defaults). Every plan carries a
`spec:` frontmatter line pointing at the spec it implements.

Merge discipline (see `doc-components/CI.md`):
1. Require branches up to date before merge. After updating a branch that
   touched docs, re-run `uv run tools/grim.py lint --fix && uv run
   tools/grim.py render` and commit.
2. `grim check` runs in PR CI and fails on structural violations, a stale
   render, or unwaived touched-path guard hits.
3. `grim check` also runs on `<default_branch>` as a backstop; a red
   default branch means the discipline was bypassed.

<!-- banner: wording provisional until IAM-41 lands -->
```

`<current>`, `<specs>`, `<plans>`, and `<default_branch>` are substitution
slots - fill each with the interview's actual value for that path or
branch (`components` never appears in this text; the session-start read
points at `<current>/`, not the raw components tree). For the
all-defaults answer set (`current=docs/current`, `specs=docs/specs`,
`plans=docs/plans`, `default_branch=main`), substituting those four
values into the block above is the byte-exact body every classifier
fixture and rubric assertion under `adopt-docs/tests/` treats as "the
template" - do not re-derive or re-word it from the clause notes below;
render the block, substitute, done.

Each clause exists for a reason worth knowing when something looks wrong
later, but the reason itself is not part of the rendered text:

- The session-start read of `<current>/` is what makes the doc-components
  system load-bearing rather than decorative - an agent that never opens
  it gets no benefit from the adoption.
- The glossary clause restates SCHEMA.md's terminology-governs-synonyms
  rule for the harness file, rather than leaving it implicit.
- The `spec:` frontmatter clause and the specs/plans redirect keep this
  project's superpowers-produced planning artifacts inside the adopted
  layout instead of the upstream tool's own default paths.
- The three merge-discipline rules are `doc-components/CI.md`'s recipe,
  restated verbatim (see Merge discipline and CI workflow, below, for the
  workflow file that makes rule 2 and rule 3 true).
- The banner clause is the one piece of this text whose final wording is
  not yet settled (IAM-41). The HTML comment marks it provisional in
  place rather than either silently shipping wording that will need to
  change again, or omitting the clause and losing the marker entirely.

### Write rules

Per the validated `instruction_files` disposition (never both files
declined - see `instruction_files` validation, above):

- **Absent** - create the file containing nothing but the delimited
  section.
- **Present, no existing section** - append the section, separated from
  existing content by a blank line; every byte of the file's prior
  content is preserved, in place, unchanged.
- **Present, existing well-formed section** - replace only the text
  between `<!-- grimore:begin -->` and `<!-- grimore:end -->` (inclusive
  of the delimiters, exclusive of everything outside them) with the
  freshly rendered body. This is idempotent - writing the identical
  config over an already-exact section produces no diff - and it is the
  mechanism the resume-repair and stale-section repair flows (above) use
  to fix a `managed-stale` file without touching anything else in it.
- Both files are written by default; a declined file (per the interview)
  gets no section and is otherwise left untouched.
- Never write more than one section to a file, never write a section to
  any file outside the two allowed root files, and never touch content
  outside the delimiters for any reason other than the create/append
  cases above.

## Merge discipline and CI workflow

Offer the CI workflow after the instruction sections are written (mutation
sequence step 7, above). Preview the rendered file - full text, path and
branch already substituted - and proceed only with explicit consent, the
same discipline as every other mutation this skill makes.

The collision policy (above) applies to `.github/workflows/grim.yml`
exactly as it applies to every other target, using the same taxonomy:

- **exact match** - keep, no rewrite.
- **absent** - create.
- **managed-stale** - recognizably a prior grim workflow but out of date
  (an older vendored path, a branch that no longer matches, or a merge
  queue that has since become active - see Late detection, below);
  preview the diff, proceed only with consent.
- **conflicting** - unrelated or hand-written workflow content; stop and
  ask, never overwrite, never merge in a rule the user did not see.
- **invalid** - present, recognizably an attempt at this workflow file,
  but fails to parse (malformed YAML, or YAML that does not parse to a
  mapping); report the verbatim parse error and stop - never silently
  repair, never overwrite without consent, same as an invalid
  `.grimore.toml` (Per-artifact inventory and dispositions, above).

Embedded template (`doc-components/CI.md`'s recipe, with `permissions`
added and the required-check identity pinned):

```yaml
name: grim
on:
  pull_request:
  push:
    branches: [<default_branch>]
permissions:
  contents: read
jobs:
  grim-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # required: grim check fails closed without full history
      - uses: astral-sh/setup-uv@v5
      - run: uv run tools/grim.py check
```

`<default_branch>` is the interview's confirmed value (Configuration
interview, above); `tools/grim.py` is the path this session's own
vendoring step just wrote (Vendoring, above) - never a guessed or
alternate path. The workflow name is `grim` and the job id is
`grim-check`, with no job `name:` override - the check-run context GitHub
reports for this job is therefore exactly `grim-check`, the identity every
later branch-protection step (GitHub identity and branch protection,
below) verifies and eventually binds against. `fetch-depth: 0` is
required - `grim check`'s transition validation fails closed when the
merge-base is unresolvable, which a shallow checkout guarantees.

**`merge_group`:** include a bare `merge_group:` trigger key (no filters
of its own), inserted immediately after `push`, if and only if the early
read-only GitHub inspection (mutation sequence step 2; reads classic
branch protection AND the repository's rulesets - see Early read-only
inspection, under GitHub identity and branch protection, below) found an
active merge-queue rule on either surface BEFORE this file was generated.
Omit the key entirely otherwise. This decision is made once, at
generation time, precisely so the workflow's first committed-and-pushed
bytes already contain `merge_group` when a queue exists - never added as
an afterthought once protection is already in view.

**Late detection:** if the merge-queue state was not knowable at
generation time (no verified GitHub remote existed yet, the inspection
had not run, or a queue is created mid-session after the workflow already
shipped) and it later turns out an active queue does exist, run this
sub-sequence in order, never skipping or reordering a step:

1. Amend the already-committed workflow to add `merge_group`.
2. Commit the amendment (amending the existing commit, not stacking an
   unrelated one).
3. Push again.
4. Re-record the triggering event: the PR now points at the new head, so
   re-note the PR number (unchanged) and the NEW head SHA (changed) - the
   previously recorded SHA is no longer the one anything verifies
   against.
5. Re-poll for the check run against the NEW SHA.
6. The gate (below) verifies its five properties against that NEW SHA -
   a `grim-check` success recorded against the prior, pre-amend SHA never
   satisfies it, because the pushed bytes it ran against no longer match
   what would actually be merged.
7. Only then does the bound-mutation step (below) proceed.

## GitHub identity and branch protection

### Identity verification (gates everything below)

Before anything GitHub-shaped happens - the early read-only inspection,
offering to push a branch and open a PR, polling for a check run, or
mutating branch protection - derive `owner/repo` from the `origin`
remote's fetch URL, and only when that URL is GitHub-shaped
(`https://github.com/<owner>/<repo>[.git]`, `git@github.com:<owner>/<repo>[.git]`,
or the `ssh://` equivalent). Then confirm an independent `gh` call (e.g.
`gh repo view <owner>/<repo> --json nameWithOwner`) resolves to the SAME
`owner/repo` - not merely that the command succeeds.

Any disagreement - a mismatched `nameWithOwner`, or a fetch URL that is
not GitHub-shaped in the first place - fails closed: no mutation, no
emitted `gh` command of any kind, no PR creation, nothing GitHub-shaped
happens for the rest of this adoption. State the disagreement plainly,
naming both the expected repository (from the fetch URL) and what `gh`
actually resolved. Because the early read-only inspection (below) is
itself gated behind this same identity check, a failed check also means
that inspection never runs and never learns whether a merge queue is
active - the generated workflow's trigger shape in that case matches the
no-remote case exactly (no `merge_group`), never a partial or
best-effort guess.

### Early read-only inspection

Once identity is verified - and before anything else in this section, in
particular before the CI workflow file is generated (mutation sequence
step 2, above; this precedes vendoring, layout, and every later step) -
read the target repository's branch-protection state through BOTH APIs:
classic branch protection (`gh api
repos/<owner>/<repo>/branches/<default_branch>/protection`) and rulesets
(`gh api repos/<owner>/<repo>/rulesets`, then each ruleset's detail).
Neither surface is skipped because the other answered - a repository can
be governed by classic protection, by rulesets, by both, or by neither.

Merge-queue state is derived from this same read, not a separate call: an
active merge-queue rule found on either surface is what makes
`merge_group` belong in the workflow generated in the next step (`merge_group`,
under Merge discipline and CI workflow, above).

This inspection is read-only - nothing is mutated here, and nothing about
existing protection is changed. It runs once, at this point in the
sequence, to decide the workflow's trigger shape. The bound-mutation step
(below) rereads (or reuses, if nothing has changed since) the same two
surfaces again immediately before mutating - this early read establishes
the fact the workflow needs; it is not a substitute for the fresh read the
mutation step takes before writing anything.

### No remote, or a non-GitHub remote

Merge discipline is documented, never executed against a guess. Write the
same merge-discipline explanation the managed section already states
(above), plus the prerequisites a future protection offer would need: a
GitHub remote whose identity `gh` can independently confirm, the workflow
merged to the default branch, and at least one recorded PR whose
`grim-check` run has actually completed. Never emit a runnable `gh`
command in this path - there is no verified target to run it against, and
guessing one is worse than saying so plainly.

### Verified remote: the pinned lifecycle

A push to a feature branch alone schedules nothing - the workflow only
triggers on `pull_request` and a push to the default branch (plus
`merge_group` when applicable). The adoption therefore follows one pinned
lifecycle, matching the merge discipline it just documented:

1. Commit the adoption on a feature branch (consent - see Finishing an
   adoption, below).
2. Push it.
3. Open the adoption pull request (`gh pr create`, consent).
4. Record the triggering event - the PR number and the pushed commit's
   SHA - BEFORE polling for anything. The gate below only ever accepts a
   check run that belongs to this recorded event and SHA, never merely
   "the most recent `grim-check` run."
5. Only then poll for the check run.

### The gate: five check properties

A branch-protection mutation is only ever attempted when every one of the
following holds, verified within THIS session, against the recorded
event:

1. **Name** - `grim-check` (the job id from Merge discipline and CI
   workflow, above; never a renamed context).
2. **Conclusion** - `success`.
3. **`head_sha`** - equal to the pushed adoption commit (the current head
   SHA - the amended one, if the late-detection path above fired).
4. **Event association** - the check run belongs to the recorded PR from
   step 4 above, not merely some other commit that happens to share a
   SHA.
5. **Source** - the GitHub Actions app, not an arbitrary third-party
   integration reporting a same-named context.

Missing any one of the five - including the common case of not enough
time having passed for the run to finish - means the gate does not hold.

### When the gate holds: the bound mutation

Reread (or reuse, if nothing has changed since the early read-only
inspection above) the current protection state through BOTH APIs -
classic branch protection AND the repository's rulesets - immediately
before touching anything; time may have passed since the early
inspection, so this is a fresh confirmation, not a re-derivation of a
fact already established. Preview the semantic diff - which rule, which
entry, what changes - and mutate only after consent (see Finishing an
adoption, below). Declining here is handled the same way as any other
declined mutation: state plainly that protection was declined and left
alone, do not silently skip past it, and make no mutating call.

The mutation carries the verified integration identity into the stored
rule, not just the context string, so no other integration can later
satisfy `grim-check` by coincidence of name:

- **Classic protection** - `checks: [{context: "grim-check", app_id:
  <verified GitHub Actions app id>}]`.
- **Ruleset** - the required-status-checks entry gets `integration_id:
  <verified GitHub Actions app id>` alongside `context: "grim-check"`.

If a `grim-check` entry already exists with no source binding (any-source
- satisfied by any integration reporting that context), upgrade it
minimally: same context, add the verified app/integration id, and change
nothing else - every other rule (an existing stricter approval
requirement, an active merge queue rule, anything unrelated) is preserved
byte-for-byte in the request body.

After the mutation, read the rule back and assert BOTH properties hold in
the response - the context AND the binding - not just that the request
returned success.

### When the gate does not hold: the deferred sequence

Emit this sequence as text, in this order, and only for a verified GitHub
remote (the no-remote path above already covers the alternative):

1. **The scheduling action first** - push the branch, open the PR - not
   "wait for the check," since nothing schedules the check to run at all
   until that happens. If the branch and PR already exist (adoption
   already reached that point this session), name that they're done and
   move straight to naming what remains.
2. **The five check properties** the gate above requires, named
   explicitly: name `grim-check`, conclusion `success`, `head_sha` equal
   to the pushed commit, association with the recorded PR, GitHub Actions
   app as source.
3. **The exact bound mutation form** - `context` plus `app_id` for
   classic protection, `context` plus `integration_id` for a ruleset -
   never a context-only example, which would silently document a weaker
   rule than the one this skill would actually install.
4. **Read-back** - confirm both the context and the binding after
   applying it.

## Charter interview

(Task 4 - not yet written in this file.)

## Finishing an adoption

(Task 4 - not yet written in this file.)
