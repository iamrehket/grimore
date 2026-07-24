# Doc Components System - Design

Date: 2026-07-24
Status: draft (revised after adversarial review, pending user review)
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
5. **Rendered docs are committed and hash-verified**, paired with a required
   merge discipline (below) so cross-branch invariants are enforced before
   they land, not discovered after.
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
    adr/render-hash.md
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
id: adr-render-hash     # <type>-<slug>; stable, unique, never reused
type: adr               # adr | term | usecase | constraint | nongoal | note
status: current         # draft | current | superseded
supersedes: [adr-patch-model]  # optional; see lifecycle rules
subsystem: renderer     # optional; routes into a render target
paths: [src/render/]    # optional, note/adr only; hook for later staleness lint
date: 2026-07-24        # creation date
---
```

IDs are `<type>-<slug>` for **all** types, including ADRs. Sequential
`adr-NNNN` numbering was rejected in review: two concurrent branches would
both allocate "the next number" and collide only after both merged. Slugs are
allocation-free and collision-resistant; the filename is the slug. Duplicate
IDs anywhere in the store are a lint error.

### Lifecycle rules

- Statuses: `draft`, `current`, `superseded`. **"Live" means `current` only**;
  drafts are not live.
- Legal transitions: `draft -> current` (promotion), `draft -> superseded`
  (abandonment), `current -> superseded`. No deletion; IDs never reused.
- A `supersedes:` edge is authored on the new component (usually while it is
  still a draft) but **takes effect at promotion**: when finish-docs promotes
  the new component to `current`, it flips each edge target to `superseded`
  in the same pass. Until promotion, the target stays current.
- Supersede targets must already exist in the branch's view of the store
  (lint error otherwise). Reversing a decision that lives in an unmerged
  sibling branch therefore requires landing order; this is accepted.
- Semantic merge conflict: one component with two or more **live** successors
  is a lint **error** ("reconcile"). Detection point: because merge discipline
  requires branches to be up to date before merge (below), the second branch's
  `grim check` sees the first branch's landed successor and fails pre-merge.
  `grim check` also runs on the default branch post-merge as a backstop.
- Transition legality is enforced by construction (only align and finish-docs
  write statuses) plus a **best-effort git check**: when
  `git merge-base HEAD <default-branch>` is resolvable, lint compares each
  component's status against its status at the merge-base and errors on
  illegal jumps (e.g. `superseded -> current`). When history is unavailable
  (shallow clone, squash, first commit), the check is skipped, not failed.

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

- `docs/current/*.md` - the agent view, committed to the repo.
- Human exports (not committed): single-file markdown bundle; static-site-ready
  markdown tree; `--digest --since <date>` catch-up summary (components
  added/promoted/superseded since the date, grouped by type, linking specs).

Render mapping (fixed in v1):

| Output | Source |
|---|---|
| `current/charter.md` | usecase, constraint, nongoal |
| `current/decisions.md` | adr |
| `current/glossary.md` | term |
| `current/<subsystem>.md` | note with matching `subsystem:` |
| `current/general.md` | note without `subsystem:` |

Ordering within every output: sort by (`date`, `id`) ascending - deterministic
and testable (byte-identical render for identical stores).

**Store hash**: sha256 over the sorted list of `(relative path, normalized
content)` pairs of `status: current` components only. Draft edits do not
change the hash, so in-flight work does not churn `grim check`. The hash is
stamped as a single comment line in each rendered file.

Draft and superseded components never appear in any consumer output. History
lives in the store and git.

## Merge discipline

Committed rendered aggregates and cross-branch invariants both require that
merges see a current view of the store. Adopting projects enable:

1. **Require branches up to date before merge** (branch protection / merge
   queue). After updating, a branch that touched docs re-runs
   `grim lint --fix && grim render` and commits - one command, mechanical.
   This serializes doc-touching merges; accepted for small teams, revisit if
   it becomes a bottleneck.
2. **`grim check` in PR CI** - fails on structural violations and stale
   rendered hash.
3. **`grim check` on the default branch** after merge, as a backstop; a red
   main here means discipline was bypassed, and the fix is
   `grim lint --fix && grim render` on a follow-up commit.

Trade-off accepted knowingly: review recommended not committing rendered
aggregates at all (render in CI instead) to eliminate this class entirely.
Committed renders were kept because zero-setup consumption (GitHub web view,
agents without a build step) is a hard requirement; the discipline above is
the price.

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
    `implemented: 2026-07-24 (PR #12)`. Already-stamped specs are skipped
    (idempotency guard).
  - `grim lint --fix` (re)writes a **banner block** at the top of each spec:
    a deterministic, delimiter-marked block (`<!-- grim:status -->` ...
    `<!-- /grim:status -->`) that is the only part of a spec the script ever
    touches. Content is computed from the component graph:
    - all referenced components current: "Implemented <date>. References
      current."
    - some superseded: "Superseded in part: adr-a -> adr-b, ..."
    - all superseded: "Superseded."
    - referenced component abandoned (superseded, no successor): listed as
      "abandoned" - there is no successor to point at.
  - Banner wording is deliberately advisory, not authoritative: banners track
    **explicit supersede edges only**. A decision reversed by a fresh
    component without an edge will not fire the banner; edge-writing at
    finish-docs is therefore a reviewed step, not a silent one.
  - Write-amplification is accepted explicitly: superseding one component
    rewrites the banner line of every spec referencing it. The rewrites are
    mechanical, deterministic, and ride the same PR; a banner merge conflict
    is resolved by re-running `grim lint --fix`.
  - Outside the banner block, spec content is frozen after implementation.
  - Plan banners: derived transitively from the plan's `spec:` line, same
    rules. (Review recommended cutting these for v1; kept because "is this
    plan still worth reading" was an explicit user requirement. They cost one
    graph lookup.)

## Skills

Three skills, plus templates shipped with them.

### adopt-docs (user-invoked, once per project)

Asks where docs and plans live (defaults above). Writes project config
(`.grimore.toml` at repo root) that the script reads. Creates the layout.
Adds the consumption note to CLAUDE.md/AGENTS.md: read `docs/current/` at
session start; glossary governs terminology; plans carry `spec:`; superpowers
spec/plan output paths point at the configured dirs. Documents the merge
discipline for the project (and, on GitHub, offers to configure branch
protection). Then a short interview to seed the charter: use cases,
constraints, non-goals, first glossary terms - each born as a component
(`current` if confirmed on the spot, `draft` if speculative).

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
finishing-a-development-branch.

**Spec discovery**: specs are files under the configured specs dir that were
added or modified in the branch diff and carry `components:` frontmatter.
Zero, one, or many; each discovered spec is processed independently.

**No-spec branches** (bugfixes, refactors, chores - the common case): steps
1, 2, and 4 are skipped. The skill asks one question - "did this branch
change anything a current component describes?" - and either supersedes/adds
components accordingly or runs step 5 alone. Cheap by design.

**Idempotency**: specs already stamped `implemented:` are skipped; re-running
finish-docs on a finished branch reconciles only what remains and is
otherwise a no-op.

Actions per discovered spec, in order:

1. Reconcile each referenced draft component against the diff - **the diff
   wins on disagreement** (specs are intent; code is reality):
   - built as designed: promote to `current`.
   - details differ but the decision stands: amend the draft in place
     (drafts are the only place in-place edits are allowed), then promote.
   - the decision itself changed: abandon the draft and write a new component
     reflecting reality, so the spec's banner fires and the discrepancy is
     visible. Amendment must never reverse a decision's substance.
   - not built: leave as `draft` (carries to a future branch) or abandon.
2. Write `supersedes:` edges from promoted components to older components the
   change invalidates. Edge-writing is shown to the user/reviewer, not silent.
3. Add `note` components for new subsystem facts - **bounded**: driven by the
   spec's declared subsystems and the diff's touched paths, not an open-ended
   read of the whole diff. On large branches (explain-diff precedent: cap and
   split), process per-subsystem and say what was skipped.
4. Stamp the spec `implemented`.
5. Run `grim lint --fix` and `grim render`; commit the doc delta on the same
   branch so it rides the same PR as the code.

Cost profile, stated honestly: steps 2-3 require reading the parts of the
diff that touch documented subsystems - that scales with diff size, not
component count. The bounding in step 3 and the no-spec fast path keep the
common case cheap; a giant branch pays proportionally, and the skill says so
rather than silently skimming.

## Tooling: `grim` (one script, three verbs)

Single-file Python CLI, `uv run`-able, stdlib + PyYAML-class dependencies at
most, no daemon. Lives in this repo; copied or referenced by adopting projects
via `.grimore.toml`.

- **`grim lint [--fix]`** - frontmatter schema validation; ID uniqueness and
  `<type>-<slug>` format; supersede-edge integrity (targets exist; no
  dual-live-successor conflicts); best-effort transition check against the
  merge-base (skipped when history is unavailable); glossary Avoid-term usage
  in component bodies (word-boundary, case-insensitive, with an inline escape
  marker); plans missing `spec:`. `--fix`: normalize formatting, rewrite
  banner blocks on specs and plans. IDs are never renumbered.
- **`grim render`** - compile `docs/current/` per the render mapping; emit
  human exports and digest on request; stamp store hash.
- **`grim check`** - CI entry point: lint (no fix) + rendered-hash
  verification. Runs in PR CI and on the default branch (merge discipline).

Exit codes and machine-readable (JSON) output so agents can consume results.

## Adoption and configuration

`.grimore.toml`: paths (components, current, specs, plans), enabled component
types, default branch name, render targets (v1: the fixed mapping above;
config reserves the key). The consumption note in CLAUDE.md/AGENTS.md is the
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
- Semantic drift detection beyond explicit supersede edges (banners are
  advisory; see Specs and plans).

## Testing

- `grim` is TDD'd with pytest: schema fixtures, lifecycle-transition cases,
  dual-successor conflict detection, merge-base check degradation, render
  determinism (byte-identical output for identical stores), store-hash
  stability under draft edits, hash verification, banner derivation including
  the abandonment case, Avoid-term word-boundary matching.
- Skills are pressure-tested per superpowers writing-skills discipline
  (failing scenario first, then the skill text that fixes it), with at least:
  align captures a term and an ADR inline in a scripted session; finish-docs
  supersedes correctly when the diff contradicts the spec; finish-docs
  no-spec fast path; finish-docs idempotent re-run.
- Dogfood gate: grimore itself passes `grim check` in CI before v1 is called
  done.

## References

- Predecessor triage: docs/triaging/2026-07-19-doc-reconciliation-triage.md
- Cost-model proof: explain-diff skill (this repo) - structured payload +
  zero-token renderer, hard size caps with explicit splitting.
- Survey sources: forks/superpowers (process discipline, reviewer-subagent
  loop, skill-authoring conventions), forks/skills / Matt Pocock
  (domain-modeling CONTEXT.md + ADR formats, lazy creation, inline capture,
  no-paths-in-prose rule, user-invoked skill philosophy).
- Mentat parallel: live/retired supersede chains; the dual-successor lint is
  mentat's M3 contradiction detection in miniature.
- Adversarial review 2026-07-24: 17 findings; blockers resolved (slug IDs,
  transition oracle, merged-state gate), majors incorporated (banner
  mechanics, finish-docs discovery/idempotency/bounding, hash definition,
  render mapping), two recommendations consciously declined (uncommitted
  renders, dropping plan banners) - rationale inline above.
