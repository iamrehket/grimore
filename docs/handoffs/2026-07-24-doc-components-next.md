# Handoff: doc-components system — next segments (IAM-38 / IAM-39)

Date: 2026-07-24. Session: brainstorm -> spec -> backlog -> IAM-37 shipped.
This doc points at artifacts; it does not restate them. Delete it once its
contents are absorbed (it is scratch, not documentation).

## Read these first, in order

1. Mentat status head: `recall(space="grimore", subject_prefix="grimore.roadmap.doc-components")`
   — one live head, superseded on every state change. Invoke the
   `using-mentat` skill before writing to it.
2. Design spec (source of authority): `docs/superpowers/specs/2026-07-24-doc-components-design.md`
   — survived two adversarial reviews (opus 17-finding, Codex 3-finding);
   declined recommendations are documented inline. Do not re-litigate locked
   decisions without the operator.
3. Shipped foundation: `doc-components/` — `SCHEMA.md` (normative),
   `templates/` (six types + spec/plan working-layer), `examples/` (clean
   fixture tree; the lint suite must pass it).
4. Backlog: Linear project "grimore" (team IAM), IAM-37..IAM-47 with blocking
   edges. IAM-37 is Done.

## State

- IAM-37 merged to main (`fb08057`) on private GitHub repo `iamrehket/grimore`.
- IAM-38 (grim lint) and IAM-39 (align skill) are unblocked and independent —
  parallelizable. IAM-39 needs only `doc-components/` content, not tooling.
- Everything else in the chain is blocked behind IAM-38/40.

## Process expectations (what the operator has been getting)

- Per issue: superpowers `writing-plans` (plan to `docs/superpowers/plans/`,
  committed) -> `subagent-driven-development` on a feature branch named per
  Linear (`aalbright/iam-NN-...`) -> final whole-branch review on opus ->
  PR to main. Model routing per workspace CLAUDE.md (haiku for transcription
  implementers, sonnet reviewers, opus final review).
- SDD ledger convention: `.superpowers/sdd/progress.md`, rotated per plan
  (archived ledgers sit beside it).
- Verification one-liners run via `uv run --with pyyaml python - <<EOF` (repo
  has no installed test env yet; IAM-38 introduces pytest properly).

## Gotchas learned this session (do not relearn these)

- **Fix/implementer subagents must stage named paths only.** A broad `git add`
  swept untracked `.idea/` and `tools/grype_enrich.py` into a commit. The
  operator wants `.idea/` out of the repo everywhere (now gitignored;
  offending refs deleted). grype_enrich.py stays tracked (operator choice).
- **Main's history was flattened**: a duplicate PR (#2, misclick) squash-merged
  over PR #1, so the six spec/plan commits exist on origin main only inside
  squash `5a6c8a7`. Commit SHAs referenced in the plan file and archived
  ledger (a0eccba..c12e364, 08a0bad..f926a6d) are NOT in origin main history.
  File paths, not SHAs, are the stable references.
- **Linear auto-completes issues when their attached PR merges** (GitHub
  integration is live). Don't fight it; attach PRs via `links` on save_issue.
- **Linear state changes can be blocked by the permission classifier** in auto
  mode; if blocked, tell the operator rather than working around it.
- **Branch protection / merge discipline from the spec is NOT configured yet**
  on the GitHub repo — it arrives with adopt-docs (IAM-43) / dogfood (IAM-46).
  Until then, remind the operator not to double-merge (see PR #2 incident).
- The operator prefers no emojis in deliverables, substance-first prose, and
  AskUserQuestion-style structured choices during brainstorming.

## Carry-forward ideas (surface when their issue starts)

- IAM-44 (finish-docs skill): bake in "stage only named paths" — the .idea
  sweep is the motivating incident.
- IAM-46 (dogfood): the PR #2 squash incident is live evidence for the spec's
  merge-discipline section; cite it.
- IAM-38: SCHEMA.md is the requirements doc; `doc-components/examples/` must
  lint clean; slug/id rule was reworded after review — the slug equals the
  filename, the id is `<type>-` + slug.
