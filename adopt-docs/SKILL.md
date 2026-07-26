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
2. Read-only GitHub inspection, when a verified GitHub remote exists -
   detailed under GitHub identity and branch protection, below.
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

(Task 3 - not yet written in this file.)

## Merge discipline and CI workflow

(Task 3 - not yet written in this file.)

## GitHub identity and branch protection

(Task 3 / Task 4 - not yet written in this file.)

## Charter interview

(Task 4 - not yet written in this file.)

## Finishing an adoption

(Task 4 - not yet written in this file.)
