# Doc Components System - Design

Date: 2026-07-24
Status: draft (pending user review)
Predecessor: docs/triaging/2026-07-19-doc-reconciliation-triage.md (parked triage;
this design resolves its open questions)

## Problem

Spec/plan-driven agent workflows (superpowers-style) produce append-only, dated
documents that sprawl over weeks and months. Obsolete decisions linger in files
agents still load, confusing or breaking sessions guided by them. Nothing
reconciles session artifacts into a canonical current-state doc set; nothing
captures architecture decisions, use cases, constraints, or non-goals in a
structured way; nothing validates that documentation matches project
conventions or current reality. Multi-session and multi-contributor work makes
all of this worse.

## Decisions (locked during brainstorm, 2026-07-24)

1. **Audience**: structured agent-optimized source; a zero-token script renders
   views for both agents and humans. (Refines the 2026-07-19 "agents first"
   decision.)
2. **Own capture skills**: build our own brainstorm/alignment and finish skills
   rather than layering on or forking upstream superpowers/Pocock skills.
   Upstream execution-middle skills (TDD, executing-plans,
   subagent-driven-development, worktrees) remain in use, untouched.
3. **Repo-canonical decisions**: ADRs and other components live in the repo,
   versioned and PR-reviewed with the code. Mentat holds pointer/status
   memories, not the canonical content.
4. **Compile, don't patch**: canonical docs are compiled from small
   lifecycle-statused components. Sessions append components and flip
   statuses; nothing is surgically edited in place. Superseded components stop
   rendering into consumer output.
5. **Rendered docs are committed and hash-verified** so any consumer reads them
   with zero setup and CI catches stale renders.
6. **v1 validation**: structural lint + format with `--fix`; the
   code-path staleness tripwire is deferred (but its schema hook ships in v1).
7. **Plans stay out of the sync loop**: plans are execution scaffolding. They
   participate only via derived status banners.

## Architecture overview

Three layers per adopting project:

- **Component store** (source of truth): small append-mostly files, one idea
  each, uniform frontmatter with lifecycle status.
- **Working layer**: dated specs and plans produced by sessions. Frozen after
  the branch finishes; self-labeling via derived status banners.
- **Rendered layer**: compiled consumer docs (agent view committed in-repo;
  human exports) generated from `status: current` components only.

Two flows write to the store: `align` (capture at decision time, as drafts)
and `finish-docs` (reconcile against the real diff at branch finish, promote
or supersede). One script (`grim`) does all mechanical work: lint, fix,
render, verify.

## Component store

Layout (paths configurable at adoption; defaults shown):

```
docs/
  components/
    adr/0007-render-hash.md
    term/component.md
    usecase/catch-up-digest.md
    constraint/py312-floor.md
    nongoal/multi-context-glossary.md
    note/renderer-pipeline.md
  current/                  # rendered agent view (committed, hash-stamped)
    charter.md              # use cases + constraints + non-goals
    decisions.md            # current ADRs
    glossary.md
    <subsystem>.md          # compiled from note components
  specs/                    # working layer, dated
  plans/                    # working layer, dated
```

### Frontmatter schema (all component types)

```yaml
---
id: adr-0007            # stable, unique, never reused
type: adr               # adr | term | usecase | constraint | nongoal | note
status: current         # draft | current | superseded
supersedes: [adr-0003]  # optional; targets must exist
subsystem: renderer     # optional; routes into a render target
paths: [src/render/]    # optional, note/adr only; hook for later staleness lint
date: 2026-07-24        # creation date
---
```

IDs: `adr-NNNN` (sequential), all other types `<type>-<slug>`.

### Lifecycle rules

- Legal transitions: `draft -> current`, `draft -> superseded` (abandoned),
  `current -> superseded`. No other transitions; no deletion; IDs never reused.
- A component becomes `superseded` only via a `supersedes:` edge from a live
  component or an explicit abandonment during `finish-docs`.
- Semantic merge conflict: one component superseded by two or more live
  components is a lint **error** ("reconcile"). Git merges the files cleanly;
  the lint catches the contradiction git cannot see.
- `rejected` status (decided-against options kept findable): deferred, tracked
  in backlog.

### Body formats

- **adr**: Pocock-bar ADRs - record only decisions that are hard to reverse,
  surprising without context, and a real trade-off. Body is a paragraph of
  context/decision/why; optional sections only when they add value.
- **term**: `**Term**: one-two sentence definition` + `_Avoid_: rejected
  synonyms`. Opinionated; context-specific terms only.
- **usecase / constraint / nongoal**: title + terse prose paragraph. Non-goals
  state what is excluded and why.
- **note**: terse factual prose about a subsystem. No file paths or code
  snippets in prose (they rot); machine-readable `paths:` frontmatter instead.

## Rendered views

`grim render` compiles, from `status: current` components only:

- `docs/current/*.md` - the agent view. Terse, deterministic ordering,
  committed to the repo. Each file stamped with a hash of the component store
  so `grim check` can detect staleness.
- Human exports: single-file markdown bundle; static-site-ready markdown tree;
  `--digest --since <date>` catch-up summary (components added/promoted/
  superseded since the date, grouped by type, linking specs).

Draft and superseded components never appear in any consumer output. History
lives in the store and git.

## Specs and plans (working layer)

- Specs are produced by `align` from our own template: problem, approach,
  **Decisions block referencing the draft component IDs created during the
  session**, out-of-scope, and a `components: [...]` frontmatter list.
- Plans carry one thin convention: `spec: <path>` frontmatter. The adoption
  note in CLAUDE.md/AGENTS.md requests it; lint warns when missing. Upstream
  writing-plans is otherwise unchanged (its output path is redirected via the
  same CLAUDE.md preference mechanism it already honors).
- **Status inheritance is derived, never hand-maintained.**
  - `finish-docs` stamps the spec once with a fact:
    `implemented: 2026-07-24 (PR #12)`.
  - Every `grim lint --fix` recomputes a status banner from the component
    graph: referenced components superseded in part -> banner lists the edges
    ("adr-0003 -> adr-0007"); all referenced components superseded -> the spec
    is banner-labeled superseded. Plans inherit their spec's banner via the
    `spec:` line.
  - Spec content is frozen. The banner does not keep the spec true; it says
    that it is not, and points at the current components that are.

## Skills

Three skills, plus templates shipped with them.

### adopt-docs (user-invoked, once per project)

Asks where docs and plans live (defaults above). Writes project config
(`.grimore.toml` at repo root) that the script reads. Creates the layout.
Adds the consumption note to CLAUDE.md/AGENTS.md: read `docs/current/` at
session start; glossary governs terminology; plans carry `spec:`; superpowers
spec/plan output paths point at the configured dirs. Then a short interview to
seed the charter: use cases, constraints, non-goals, first glossary terms -
each born as a component (`current` if confirmed on the spot, `draft` if
speculative).

### align (the brainstorm/alignment skill)

Adapted from superpowers brainstorming + Pocock grilling/domain-modeling.
One question at a time; multiple-choice preferred; explores purpose,
constraints, success criteria; proposes 2-3 approaches with a recommendation.
The structural difference: **capture happens inline at crystallization
moments** - when a term is settled, write the draft term component right
then; when a decision passes the ADR bar, write the draft ADR right then;
same for use cases, constraints, non-goals surfaced along the way. Never
batch-mined afterward. Output: a spec (template above) whose Decisions block
references the created component IDs. Spec-reviewer subagent loop
(Status / Issues / Recommendations, advisory) before user sign-off. Hands off
to upstream writing-plans.

### finish-docs (the sync pass)

Runs at branch finish - after tests pass, before the merge/PR step of
finishing-a-development-branch. Inputs: the branch's spec and the actual
branch diff; **the diff wins on disagreement** (specs are intent; code is
reality). Actions, in order:

1. Reconcile each draft component against the diff: promote to `current`,
   amend the draft to match what was really built (drafts are the one place
   in-place edits are allowed), or mark abandoned (`superseded`).
2. Write `supersedes:` edges from promoted components to older components the
   change invalidates.
3. Add `note` components for new subsystem facts the diff introduces.
4. Stamp the spec `implemented`.
5. Run `grim lint --fix` and `grim render`; commit the doc delta on the same
   branch so it rides the same PR as the code.

Token cost scales with the change: the agent authors small component files and
status flips; the script does all assembly.

## Tooling: `grim` (one script, three verbs)

Single-file Python CLI, `uv run`-able, stdlib + PyYAML-class dependencies at
most, no daemon. Lives in this repo; copied or referenced by adopting projects
via `.grimore.toml`.

- **`grim lint [--fix]`** - frontmatter schema validation; ID uniqueness and
  format; legal status transitions (vs git history of the file or prior
  state); supersede-edge integrity (targets exist; no dual-live-successor
  conflicts); glossary Avoid-term usage inside component bodies; plans missing
  `spec:`. `--fix`: normalize formatting, renumber nothing (IDs are stable),
  rewrite derived status banners on specs and plans.
- **`grim render`** - compile `docs/current/` + human exports + digest; stamp
  store hash.
- **`grim check`** - CI entry point: lint (no fix) + rendered-hash
  verification. A merged branch that skipped finish-docs fails CI visibly.

Exit codes and machine-readable (JSON) output so agents can consume results.

## Adoption and configuration

`.grimore.toml`: paths (components, current, specs, plans), enabled component
types, render targets. The consumption note in CLAUDE.md/AGENTS.md is the
only per-agent-harness surface; everything else is files and the script.
This repo (grimore) adopts the system itself once v1 lands (dogfood; this
spec and the triage doc become the first status-bannered working-layer docs).

## Non-goals (v1)

- Code-path staleness tripwire (flagging PRs that touch `paths:` without
  touching the component). Schema hook ships in v1; the check is a later
  slice.
- `rejected` component status.
- Multi-context glossaries (Pocock CONTEXT-MAP pattern). One glossary per
  repo in v1.
- Automatic mentat pointer writes from finish-docs. Session-level habit for
  now; revisit after v1.
- Static-site generator integration beyond emitting site-ready markdown.
- Replacing upstream execution skills or writing-plans.

## Testing

- `grim` is TDD'd with pytest: schema fixtures, lifecycle-transition cases,
  dual-successor conflict detection, render determinism (byte-identical
  output for identical stores), hash verification, banner derivation.
- Skills are pressure-tested per superpowers writing-skills discipline
  (failing scenario first, then the skill text that fixes it), with at least:
  align captures a term and an ADR inline in a scripted session; finish-docs
  supersedes correctly when the diff contradicts the spec.
- Dogfood gate: grimore itself passes `grim check` in CI before v1 is called
  done.

## References

- Predecessor triage: docs/triaging/2026-07-19-doc-reconciliation-triage.md
- Cost-model proof: explain-diff skill (this repo) - structured payload +
  zero-token renderer.
- Survey sources: forks/superpowers (process discipline, reviewer-subagent
  loop, skill-authoring conventions), forks/skills / Matt Pocock
  (domain-modeling CONTEXT.md + ADR formats, lazy creation, inline capture,
  no-paths-in-prose rule, user-invoked skill philosophy).
- Mentat parallel: live/retired supersede chains; the dual-successor lint is
  mentat's M3 contradiction detection in miniature.
