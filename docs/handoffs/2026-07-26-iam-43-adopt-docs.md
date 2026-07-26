# Handoff: IAM-43 adopt-docs skill (onboarding)

Date: 2026-07-26. Session: IAM-53 plugin marketplace shipped (PR #8) ->
this handoff. This doc points at artifacts; it does not restate them.
Delete it once its contents are absorbed (it is scratch, not
documentation).

## Read these first, in order

1. Mentat status heads: `recall(space="grimore", subject_prefix="grimore.roadmap")`
   — two live heads now: `grimore.roadmap.doc-components` (the chain this
   issue belongs to) and `grimore.roadmap.plugin-marketplace` (IAM-53,
   done; interacts with this issue, see Gotchas). Invoke the
   `using-mentat` skill before writing to either.
2. Linear IAM-43 — the requirements statement is in the issue body:
   `.grimore.toml` writer (paths, enabled types, default branch), layout
   creation, CLAUDE.md/AGENTS.md consumption note, merge-discipline
   documentation with offered GitHub configuration, then the
   charter-seeding interview (components born current if confirmed,
   draft if speculative — different from align, which only writes
   drafts).
3. Design spec (source of authority):
   `docs/superpowers/specs/2026-07-24-doc-components-design.md` —
   sections: Skills / adopt-docs, Adoption and configuration, Merge
   discipline. Do not re-litigate locked decisions without the operator.
4. Sibling skill for style and conventions: `align/` — the interview
   discipline, capture procedure, and its frozen pressure-test apparatus
   under `align/tests/` are the house pattern for skill construction and
   testing.
5. `doc-components/CI.md` — the grim-check CI recipe the adoption skill
   wires into adopting projects.

## State

- main at `5b77173` (PR #8 merge). 135 tests green; `grim lint --root .`
  clean; branch protection + CodeQL active on main.
- **Ordering caveat**: per the backlog edges IAM-43 sits behind IAM-41
  (banner derivation + working-layer conventions), which is unblocked
  and unstarted. The overlap is real but narrow: adopt-docs writes the
  consumption note describing working-layer behavior ("plans carry
  `spec:`", banner semantics) that IAM-41 defines. Starting IAM-43 first
  is an operator override — if taken, keep the consumption-note wording
  about banners provisional and reconcile when IAM-41 lands.
- **The motivating evidence, from the IAM-53 session**: align was
  consulted to run a design conversation in this very repo and excluded
  itself by its own rules — grimore has no `.grimore.toml` and no
  components directory, so the fallback was superpowers:brainstorming.
  The repo that ships the system cannot run it on itself. adopt-docs is
  the missing piece; actually running it on grimore is IAM-46's dogfood
  gate, not this issue — build the skill here, adopt there.

## Process expectations (what the operator has been getting)

- Per issue: superpowers `writing-plans` (plan committed as the branch's
  first commit) -> operator reviews the plan BEFORE implementation ->
  `subagent-driven-development` in a git worktree (branch named per
  Linear) -> per-task sonnet reviews with fix loops -> opus whole-branch
  review with ONE fix wave -> PR. Model routing per workspace CLAUDE.md.
- Ledger per plan at `.superpowers/sdd/<plan-basename>/progress.md`;
  archive to `.superpowers/sdd/progress-iam-NN-archived.md` before
  removing the worktree.
- Attach the PR to Linear via `links` on save_issue; issues
  auto-complete on merge.
- Note: IAM-53 ran as a light PR (no plan/SDD) by operator decision —
  that was config-scale work. IAM-43 is a full skill with interview
  logic; assume full process unless the operator says otherwise.

## Gotchas learned recently (do not relearn these)

- **The repo is now a plugin marketplace** (IAM-53): a new skill
  directory with a `SKILL.md` at repo root MUST be declared in
  `.claude-plugin/plugin.json` — `tests/test_marketplace.py` fails the
  suite otherwise (deliberate guard, not friction). Skills reach the
  operator's agents on merge to main + `/plugin marketplace update
  grimore`; pre-merge skill edits are invisible to installed agents.
- **No pytest CI exists**: branch protection requires only CodeQL, so
  the suite gates nothing until run locally. IAM-43 touches adoption-CI
  documentation anyway — folding a pytest workflow for this repo into
  its plan (or a micro-issue beside it) closes the gap; the operator
  has seen and acknowledged it.
- **Branch protection is already configured on grimore** — the adoption
  skill should offer to configure it on adopting repos, but for this
  repo the prior ruling stands: document, don't configure.
- **Stage named paths only** (standing rule; fixture repos under
  tmp_path exempt).
- **Host GPG signing breaks fixture-repo tests**: workaround
  `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgSign
  GIT_CONFIG_VALUE_0=false`; proper fix (make_repo per-fixture) is an
  open follow-up riding with IAM-46.
- **Merge convention drifted once**: PR #8 landed as a merge commit;
  #3-#7 were squashes. Operator's call which is canon going forward.
- align's frozen-test rule (`align/tests/` never edited to make a run
  pass) is the precedent adopt-docs' own test apparatus should follow.

## Carry-forward ideas (surface when their issue starts)

- IAM-43 (this issue): consumption note should direct superpowers
  spec/plan output into the configured dirs; charter-seeding interview
  uses AskUserQuestion-style structured choices (operator preference,
  consistent with align).
- IAM-44 (finish-docs): mis-slugged-draft rule in align ("delete and
  rewrite, not supersede") wants a matching SCHEMA.md "No deletion"
  clarification.
- IAM-46 (dogfood): run adopt-docs on grimore itself — closes the
  self-exclusion gap named above; inherits make_repo gpgsign hardening
  and a restricted-types pressure scenario for align.
- IAM-41 (if still unstarted when picked up): fold in the finding-code
  table and `_print_finding` extraction; banners share the output
  surface.
