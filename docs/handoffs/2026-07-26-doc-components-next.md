# Handoff: doc-components system — next segments (IAM-41 and beyond)

Date: 2026-07-26. Session: plans for IAM-39/40/42 -> parallel SDD in
worktrees -> three PRs merged in one day. This doc points at artifacts;
it does not restate them. Delete it once its contents are absorbed (it
is scratch, not documentation).

## Read these first, in order

1. Mentat status head: `recall(space="grimore", subject_prefix="grimore.roadmap.doc-components")`
   — one live head, superseded on every state change. Invoke the
   `using-mentat` skill before writing to it.
2. Design spec (source of authority): `docs/superpowers/specs/2026-07-24-doc-components-design.md`.
   Do not re-litigate locked decisions without the operator.
3. Shipped since the last handoff: `tools/grim.py` (lint / render /
   check verbs, touched-path guard, Grim-Waive trailers),
   `doc-components/CI.md`, `align/` (the align skill + its frozen
   pressure-test apparatus under `align/tests/`). 131 tests green.
4. Plans for the merged work (working layer, frozen):
   `docs/superpowers/plans/2026-07-25-{grim-render-check,touched-path-guard,align-skill}.md`.
5. Archived SDD ledgers: `.superpowers/sdd/progress-iam-{37,39,40,42}-archived.md`
   — each ends with recorded follow-up candidates and rulings.
6. Backlog: Linear project "grimore" (team IAM). IAM-37/38/39/40/42 are
   Done. IAM-41 is unblocked. IAM-43..46 sit behind it per the edges;
   IAM-47 is the post-v1 umbrella.

## State

- main at `7062f25` (plus PR #7, which carries this handoff and deletes
  the absorbed 2026-07-24 one). All suites green; `grim lint --root .`
  clean.
- **Branch protection is now ACTIVE on main**: PRs required, CodeQL
  runs per commit, direct pushes rejected. The double-merge risk class
  is closed; stop reminding the operator about it.
- IAM-41 (banner derivation + working-layer conventions) is the next
  issue: it needed render + lint on main, both are there now.

## Process expectations (what the operator has been getting)

- Per issue: superpowers `writing-plans` (plan committed as the
  branch's first commit) -> operator reviews the plan BEFORE
  implementation -> `subagent-driven-development` in a git worktree
  (branch named per Linear) -> per-task sonnet reviews with fix loops
  -> opus whole-branch review with ONE fix wave -> PR. Model routing
  per workspace CLAUDE.md (haiku transcription implementers, sonnet
  reviewers, opus final).
- Ledger per plan at `.superpowers/sdd/<plan-basename>/progress.md`;
  archive to `.superpowers/sdd/progress-iam-NN-archived.md` in the main
  checkout before removing the worktree.
- Attach PRs to Linear via `links` on save_issue; issues auto-complete
  on merge.
- Adversarial plan review before implementation caught real defects all
  three times; keep it. Opus branch reviews should live-probe (that is
  what caught the symlink write-through and the rename bypass).

## Gotchas learned this session (do not relearn these)

- **Stage named paths only** in this repo (standing rule; fixture repos
  under tmp_path exempt).
- **Host GPG signing breaks fixture-repo tests**: a machine with global
  `commit.gpgSign=true` fails ~37 tests. Workaround:
  `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgSign GIT_CONFIG_VALUE_0=false`.
  Proper fix (follow-up): `make_repo` helpers set it per-fixture.
- **align's test apparatus is frozen**: `align/tests/scenario-*.md` and
  `rubric.md` are never edited to make a run pass — fix the skill.
  SKILL.md must stay scenario-blind (grep for the scenario's domain
  strings) and its shared verbatim blocks stay byte-identical with the
  plan's fenced copies.
- **Guard semantics that surprised reviewers**: merge-base resolves
  origin/<default_branch> FIRST (origin is the PR target; local ref is
  a repo-without-remote fallback); waivers are branch-permanent;
  untracked files are invisible locally; a stale locally-fetched origin
  is a silent local bypass — CI with fetch-depth: 0 is the enforcement
  point.
- **grim check is lint-gated**: any lint error skips the byte-compare
  (exit 1 either way). E070 therefore suppresses E080 reporting until
  fixed — one extra CI round-trip, known and accepted.
- Reviewer output can arrive stale (ran against a pre-push snapshot):
  before acting on a finding, verify the cited code still exists at the
  current head.

## Carry-forward ideas (surface when their issue starts)

- IAM-41 plan: fold in the finding-code table (SCHEMA/CI docs) and the
  `_print_finding` extraction + render-warnings-in-human-mode decision —
  banners touch the same output surface.
- IAM-43 (adopt-docs) / IAM-46 (dogfood): branch protection + CodeQL
  already exist on this repo; the adoption doc should document, not
  configure, them here. Dogfood also inherits the make_repo gpgsign
  hardening and a restricted-types pressure scenario for align.
- IAM-44 (finish-docs): the mis-slugged-draft rule now in align
  ("delete and rewrite, not supersede") wants a matching SCHEMA.md
  clarification — its "No deletion" reads as absolute.
- IAM-47: stale-origin-fetch residual, non-ancestor merge-base edge,
  path-hygiene tooling, coverage reporting.
