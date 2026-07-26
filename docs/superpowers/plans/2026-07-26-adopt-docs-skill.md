---
spec: docs/superpowers/specs/2026-07-24-doc-components-design.md
---

<!-- grim:status -->
<!-- /grim:status -->

# adopt-docs skill (IAM-43) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Revision 4 (2026-07-26). Round 1 folded findings 2-9 in and split Codex
packaging to IAM-56. Round 2 separated adoption state from health, added
collision/protection scenarios, and deferred protection. Round 3
(`.scratch/2026-07-26-review-main-to-3169760.md`) drove: config
validation split between grim-owned keys (bundle-side `load_config`) and
`instruction_files` (separate tomllib read), a GitHub-shaped protection
fixture with the check bound to the pushed SHA and the Actions app,
merge-queue inspection before workflow generation, the manifest bump
moved ahead of the GREEN runs, documented-only no-remote behavior,
pristine per-sub-run protection fixtures, and toplevel-verified git
provenance.

**Goal:** Ship `adopt-docs/SKILL.md` — the Claude-packaged onboarding skill that writes instructions for both harness files (`CLAUDE.md` and `AGENTS.md`; Codex *packaging* is IAM-56 and the marketplace is not described as Codex-compatible until it lands). It safely (resumably, collision-aware) interviews for configuration, vendors grim and the doc-components schema/templates, creates the layout, writes `.grimore.toml`, installs the dual managed instruction sections, documents merge discipline (offering CI and — once the check has verifiably run on the pushed commit — branch protection), and runs the charter-seeding interview whose components are born `current` if confirmed on the spot, `draft` if speculative.

**Architecture:** A skill directory at the repo root (`adopt-docs/`), following the `align/` convention: `SKILL.md` plus `tests/` holding the frozen pressure-test inputs (including a recording `gh` stub) and appended run evidence. New pytest module for static contracts only — no new adoption runtime.

**Tech Stack:** Markdown skill text; pressure tests dispatch subagents against scripted scenarios in fixture repos; `uv run tools/grim.py lint|render|check` validates outcomes; pytest asserts static contracts; a stub `gh` (shell script, part of the frozen inputs) fakes the GitHub API for the protection scenario and asserts the repository it is asked about.

**Verification model:** two layers, split by determinism.

- *Executable (pytest, `tests/test_adopt_docs.py`):* skill file exists with parseable frontmatter; manifest declares it; SKILL.md embeds the required note clauses and the exact `.grimore.toml` template (parses via tomllib, `[grimore]` table); the embedded CI workflow template parses as YAML — asserting the trigger key as `on` *or* YAML 1.1's coerced boolean-`True` key, whichever the loader yields — with `permissions: contents: read` and job id `grim-check` and no job `name:` override; `plugin.json` version equals `0.2.0` and `marketplace.json`'s description names all three skills; SKILL.md's provenance instructions match the identity ladder below (toplevel verification, manifest fallback, no hardcoded version literal).
- *Pressure tests (frozen inputs, RED then GREEN, align discipline):* six scenarios below. Harness contract, fixed for every run: same model, tool permissions, cwd, source bundle, and scripted answers; fresh fixture repo **with an initial commit** and per-repo identity + `commit.gpgSign=false`; the skill supplied from a **cache-shaped source bundle** (repo tree without `.git`); every scenario file carries its **complete ordered answer script** and, where applicable, a **bounded interrupt rule**. Scenarios with sub-runs start **each sub-run from a fresh fixture cloned from the same pristine template, with its own empty stub log** — sub-runs never share mutated state or logs. The only RED/GREEN variable is whether the skill text is supplied. Runs record full answer/tool-call order so one-question-at-a-time, inline capture, and refusal behaviors are auditable from the transcript (the transcript is a legitimate rubric observation point).

Spec: docs/superpowers/specs/2026-07-24-doc-components-design.md (Skills / adopt-docs, Adoption and configuration, Merge discipline).
Requirements doc: doc-components/SCHEMA.md. Templates: doc-components/templates/. CI recipe: doc-components/CI.md. Sibling skill: align/SKILL.md. Linear: IAM-43. Related: IAM-55 (ask-per-adoption delivery), IAM-56 (Codex packaging), IAM-46 (dogfood), IAM-41 (banners).

## Global Constraints

- Branch: `aalbright/iam-43-adopt-docs-skill-onboarding`; this plan is its first commit, revised in place before implementation starts.
- **Stage named paths only** — never `git add .` / `-A` / `--all` in the grimore repo (fixture trees under `tmp_path` or `$CLAUDE_JOB_DIR/tmp` are exempt and never committed).
- **Frozen-test rule:** the frozen set is `scenario-*.md`, `rubric.md`, `baseline-red.md`, and `stub-gh`. Once Task 1 lands they are never edited to make a run pass; genuine defects require an operator ruling recorded in the ledger. `result-green.md` is ADDED later (Task 4) and is append-only afterward.
- **Marketplace manifest guard:** `.claude-plugin/plugin.json` must declare the new skill directory (Task 2, once `SKILL.md` exists) or `tests/test_marketplace.py` fails; CI (IAM-54) gates the merge on the suite.
- **Provisional banner wording:** IAM-41 has not landed. Banner descriptions use the spec's wording marked `(wording provisional until IAM-41 lands)` in an HTML comment beside them.
- No emojis in any output, skill text, or docs.
- Skill terminology must match SCHEMA.md exactly: component, draft/current/superseded, promote, abandon, supersede edge. No synonyms.
- Do not modify `align/`, `doc-components/`, or `tools/grim.py`. "No new Python" means no new *adoption runtime*; the pytest module and the test-harness `gh` stub are in scope.
- Nothing in the skill special-cases grimore; adopting grimore itself is IAM-46.

## Design decisions (spec left them open, or review rounds forced them)

- **Vendored delivery (operator, 2026-07-26):** copy `tools/grim.py` to `<target>/tools/grim.py`; copy `doc-components/SCHEMA.md`, `templates/`, `CI.md` to `<target>/doc-components/`. `examples/` is not copied. Ask-per-adoption delivery is IAM-55.
- **Source resolution and provenance (round 3 finding 7):** copy sources resolve relative to the skill's own directory (`../tools/grim.py`, `../doc-components/`) — valid in a checkout and in the plugin cache. Vendored stamp: `# Vendored from iamrehket/grimore by adopt-docs on <YYYY-MM-DD>. Source: <identity>.` — identity ladder: (1) git identity, accepted ONLY when `git -C <skill-dir> rev-parse --show-toplevel` resolves to the recognized grimore source root (the skill directory's own parent, carrying `.claude-plugin/plugin.json` with name `grimore`) AND that root differs from the adopting repository's root — `rev-parse HEAD` walks parent directories, so a bundle nested under the target without its own `.git` would otherwise stamp the *target's* commit; (2) `grimore plugin v<version>` read from the bundle's `.claude-plugin/plugin.json`; (3) literal `unknown`. Never invented; never the adopting repo's HEAD. The nested-bundle case is part of the frozen contract (restricted scenario), and GREEN evidence exercises the final `v0.2.0` stamp because the manifest bump lands in Task 2, before the GREEN runs.
- **Adoption state is stable; health is separate (rounds 2-3):**
  - **not adopted** — no recognizable adoption artifact (config, stamped vendored file, managed section, or layout dir);
  - **partial** — at least one recognizable adoption artifact, but the stable footprint below is incomplete or invalid;
  - **adopted** — the stable footprint is complete: the **bundle's `load_config(root)` succeeds** (grim-owned keys present-or-defaulted AND semantically valid — a TOML-parseable `components = 42` is *partial/invalid*, not adopted); `instruction_files` (read separately, below) validates; recognized vendored payload (stamp line present; below-stamp bytes match the bundled source); layout dirs for enabled types; every file listed in the validated disposition carries the managed section;
  - **health** — only after classifying *adopted*, optionally run `lint`/`check` and report healthy/unhealthy. Health NEVER changes adoption state: an unhealthy adopted repo is handed to finish-docs / ordinary grim remediation, never to adoption repair.
  Partial → inventory per-artifact (exact match / absent / managed-stale / conflicting / invalid, with the exact parse or validation error), preview a resume-repair plan, proceed only with consent. Malformed TOML is reported with the parse error, never overwritten without consent.
- **`instruction_files` is not a grim key (round 3 finding 1):** `load_config` ignores it and `grim.Config` never exposes it. The skill reads it with a **separate raw tomllib parse** of `.grimore.toml` and validates it as a **duplicate-free subset of exactly `"CLAUDE.md"` and `"AGENTS.md"`** — no paths, no other names, and **the empty list is illegal** (an adoption that instructs neither harness is not an adoption; a fully-declined disposition is refused at interview time, and a persisted `[]` or any invalid value classifies as partial/invalid). The classifier reads and writes instruction content only at the two allowed root files, never derived paths.
- **Never execute unverified target code:** classification and any preflight parsing use the *bundle's* `grim.py`, not the target's. `<target>/tools/grim.py` is executed only after its stamp and below-stamp bytes are verified against the bundled source; a conflicting file is reported without execution.
- **Instruction-file disposition is durable:** the dual-file default writes an identical delimited managed section (`<!-- grimore:begin -->` ... `<!-- grimore:end -->`) to both root files — created if absent, appended if present, replaced-in-place idempotently when the section exists, all other content preserved. A user may explicitly decline ONE file (never both); the choice is persisted as `instruction_files` under `[grimore]`, so decline and absence are distinguishable forever, and the *adopted* classification honors the validated disposition. The skill states the consequence of a decline (that harness gets no instructions).
- **Collision policy, uniform for every mutation:** read-only inventory before any write; per target: exact match → keep; absent → create; recognizably managed but stale (older stamp, older managed section) → previewed update; unrelated or conflicting → stop and ask, never overwrite, never execute. Applies to vendored files, layout, instruction files, `.github/workflows/grim.yml`, and branch protection.
- **Prerequisites (one contract):** `git` present; target is a non-bare work tree with a resolvable root; `uv` present (else stop with install pointer). **At least one commit is required: with no history the skill stops before any mutation and asks the user to establish the initial commit themselves.** No skill-created initial commit; no deferred-check mode.
- **Order of operations:** inventory → **read-only GitHub inspection when a verified GitHub remote exists (protection, rulesets, merge-queue state)** → vendor + layout → `.grimore.toml` → validate with the vendored linter → instruction sections → CI workflow (already merge-queue-aware, see below) → charter → finish.
- **Required-check identity:** workflow `name: grim`, job id `grim-check`, no job `name:` override — the check-run context is exactly `grim-check`, asserted verbatim in template, rubric, pytest, and the protection offer.
- **GitHub identity is verified before anything GitHub-shaped happens (round 3 findings 2, 5):** the skill derives `owner/repo` from the `origin` fetch URL only when it is GitHub-shaped, and confirms `gh` resolves the same repository; any disagreement fails closed (no mutation, no emitted commands). **With no remote or a non-GitHub remote, behavior is documented-only**: the merge-discipline text plus the *prerequisites* for a future protection offer — never a runnable `gh` command, which would require guessing a target.
- **Merge-queue handling precedes workflow generation (round 3 finding 3):** the early read-only inspection (order of operations above) determines whether an active merge queue exists BEFORE the workflow is generated, so `merge_group` is in the workflow's committed-and-pushed bytes from the start. If queue state only becomes known late (inspection impossible earlier), the skill must amend the workflow, repeat commit + push, and re-verify a successful `grim-check` on the NEW head SHA before any protection mutation. The protection scenario's recorded ordering proves the pushed workflow bytes contain `merge_group` before the protection request.
- **Branch protection is deferred until the check verifiably ran (rounds 2-3):** protection is mutated only if, within the session: the workflow (final bytes) has been committed AND pushed, and a check-run exists with name `grim-check`, conclusion `success`, **`head_sha` equal to the just-pushed adoption commit**, and **the GitHub Actions app as its source** — a name-and-conclusion match alone would accept a stale run from another commit or app. Otherwise the skill emits the deferred sequence (verify those same four properties, then the exact `gh` mutation, then read-back) — and only for a verified GitHub remote. When it does mutate: read current classic-protection AND ruleset state (both APIs — this repo itself answers "not protected" on classic while an active ruleset carries required checks), preview a semantic diff, apply the minimal change preserving unrelated and stricter settings, read back and verify. Declinable; degrades to documented-only per the identity decision above.
- **Disabled charter types:** the charter covers only enabled types; a disabled section is skipped with a one-line statement; volunteered disabled-type material is recorded in the capture log and the final adoption summary message (the recorded transcript is the rubric's observation point), never as a component.
- **Confirmed vs speculative is asked, never inferred:** each capture ends with an explicit structured question — settled now, or speculative? — deciding `current` vs `draft` (the deliberate divergence from align, which only writes drafts).
- **Capture rules are self-contained** in SKILL.md (template use, slug essentials, one-line announcements, capture log); align is cited for rationale only.
- **Adoption ends with a working render:** `lint --fix`, `render`, `check`; show the first rendered current view; offer the adoption commit on a branch per the just-documented discipline.

---

### Task 1: Frozen pressure-test inputs, stub gh, and RED baselines

**Files:**
- Create: `adopt-docs/tests/scenario-widget-service.md` (primary)
- Create: `adopt-docs/tests/scenario-resume-agents-only.md`
- Create: `adopt-docs/tests/scenario-neither-restricted.md`
- Create: `adopt-docs/tests/scenario-collision.md`
- Create: `adopt-docs/tests/scenario-invalid-config.md`
- Create: `adopt-docs/tests/scenario-protection-stub.md`
- Create: `adopt-docs/tests/stub-gh` (recording fake `gh`, shell script)
- Create: `adopt-docs/tests/rubric.md`
- Create: `adopt-docs/tests/baseline-red.md`

**Steps:**
- [ ] **Step 1: Harness contract preamble** (in `rubric.md`): fixed-variables list from the Verification model; every scenario embeds its complete ordered answer script; interrupt rules are bounded ("interrupt on X; if X has not occurred by the session's terminal response or 25 exchanges, end there"); sub-runs always start from a pristine fixture clone with an empty stub log.
- [ ] **Step 2: Primary scenario** — fixture "widget-service": committed repo, BOTH `CLAUDE.md` and `AGENTS.md` with distinct unrelated content, one source file, branch `main`, **no remote**. Script: default paths except specs at `docs/design/specs`; all six types; confirm detected branch; accept the CI workflow; charter: one usecase and one constraint confirmed-settled (`current`), one nongoal floated undecided (`draft`), one term settled with a rejected synonym (`current`, synonym on _Avoid_:); final message refuses further capture work. Rubric (no-remote path): the adoption summary contains the **documented-only** merge-discipline explanation and the prerequisites for a future protection offer — and **no runnable `gh` command anywhere** (there is no verified target to name).
- [ ] **Step 3: Resume scenario** — fixture with `AGENTS.md` only. Session A: full script, **interrupted immediately after the first managed instruction section is written** (bounded rule above). Session B re-invokes: expected to classify *partial*, inventory, preview repair, and finish with consent — the existing `AGENTS.md` section replaced-or-preserved without duplication, the missing `CLAUDE.md` created with its peer section, surrounding content intact. Rubric also asserts session A's end state alone fails the adopted classification.
- [ ] **Step 4: Restricted scenario** (`scenario-neither-restricted.md` — the fixture is a normal committed repo; "neither" refers to instruction files) — NEITHER instruction file, types `["adr", "term", "usecase", "constraint"]`. **The cache-shaped skill bundle for this scenario is placed nested inside the target repository's tree (no bundle `.git`)** — the provenance rubric line requires the manifest-version stamp, proving the toplevel rule rejects the target's HEAD (round 3 finding 7). Script includes one usecase confirmed-settled (`current`) so render output is populated, plus volunteered nongoal material. Rubric: both instruction files created; nongoal section skipped with the one-line statement; the volunteered material appears in the capture log / final summary (transcript observation) and no `nongoal/` dir or component exists; render populated; `check` exit 0; stamp reads `Source: grimore plugin v0.2.0`.
- [ ] **Step 5: Collision scenario** — fixture seeded with an **unrelated `tools/grim.py` that writes a sentinel file if executed** and an unrelated `.github/workflows/grim.yml`. Script: user, shown the inventory, chooses to stop. Rubric: adoption halts; both seeded files byte-unchanged; **sentinel absent** (the unrecognized script was never executed); no other artifact written; the inventory report names both conflicts.
- [ ] **Step 6: Invalid-config scenario** — two sub-runs from pristine fixtures (round 3 finding 1): (a) `.grimore.toml` with a semantically invalid grim-owned key (`components = 42`) — must classify partial/invalid, report the bundle-side `load_config` error verbatim, and mutate nothing without consent; (b) `.grimore.toml` with hostile `instruction_files` (`["../evil.md", "CLAUDE.md", "CLAUDE.md"]`) — must classify partial/invalid, report the validation failure (non-allowed name, duplicate), and read/write NO path outside the two allowed root files (rubric: `../evil.md` does not exist afterward and appears in no write attempt in the transcript).
- [ ] **Step 7: Protection scenario** — the pristine fixture template has an `origin` whose **fetch URL is GitHub-shaped for a fixed test identity (`github.com/acme-fixtures/widget-service`)** and whose **`pushurl` points at a local bare repo**, so pushes stay offline while the repository identity is real-shaped (round 3 finding 2). `stub-gh` (first on PATH) **asserts every invocation names `acme-fixtures/widget-service` and fails the run otherwise**; it returns canned payloads — classic-protection 404, a ruleset containing an existing stricter rule and an **active merge queue**, and a `grim-check` check-run with conclusion `success`, **`head_sha` read from the bare remote's current head**, and the **GitHub Actions app** as its source — and records every invocation. Four sub-runs, each from a pristine fixture clone with its own empty log:
  - **consent:** full flow. Rubric, from recorded ordering: the early read-only inspection precedes workflow generation; the pushed workflow bytes (read from the bare remote at mutation time) already contain `merge_group`; the skill's verification queries (name, conclusion, head_sha equal to the pushed commit, Actions app) precede the mutation; existing rules preserved; only the minimal change requested (required context exactly `grim-check`, require-up-to-date); a read-back query follows the mutation.
  - **decline:** scripted decline at the protection offer. Rubric: zero mutating requests in this run's log; workflow and adoption commit unaffected.
  - **mismatch:** the stub's repository resolution reports a different repo than the remote URL. Rubric: fail closed — no mutation, no emitted `gh` mutation command, explicit explanation.
  - **deferred:** the stub returns no completed `grim-check` run for the pushed SHA. Rubric: no mutation; the emitted deferred sequence names the verified `acme-fixtures/widget-service`, requires all four check properties, and ends with read-back.
- [ ] **Step 8: Rubric** — per-scenario assertions as above plus the invariants: the bundle's `load_config(fixture_root)` succeeds and reflects the scripted answers **for its `Config` fields only** (root, components, current, specs, plans, default_branch, types — specs at `docs/design/specs` in primary); **a separate raw tomllib read** of `.grimore.toml` reflects the persisted `instruction_files`; layout dirs (enabled types only) + `.gitkeep`s; vendored `grim.py` byte-identical below the stamp, stamp matching the identity ladder (cache-shaped runs yield `Source: grimore plugin v0.2.0`); `doc-components/` without `examples/`; managed sections identical across written files, prior content byte-intact; workflow matches the template (context `grim-check`); charter components with scripted statuses; `grim lint` exit 0; render populated; `check` exit 0.
- [ ] **Step 9: RED baselines.** Run every scenario and sub-run with a subagent given fixture + request but not the skill; record honest per-line results (consent and decline recorded independently). RED must discriminate; strengthen now or never. Freeze.
- [ ] **Step 10: Commit** (named paths).

### Task 2: SKILL.md — prerequisites, state classifier, interview, vendoring, layout, config; manifest + release metadata

**Files:**
- Create: `adopt-docs/SKILL.md` (frontmatter name `adopt-docs`; description triggers on "adopt the doc system", "set up doc components", "onboard this repo to grimore")
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

**Steps:**
- [ ] **Step 1:** Prerequisite checks (single contract above) and the four-part state/health classifier: bundle-side `load_config` for grim-owned keys, separate tomllib read + validation for `instruction_files`, bundle-side execution rule, stamp verification before target-side execution, malformed/invalid handling with verbatim errors, and the resume-repair flow.
- [ ] **Step 2:** Configuration interview — one question at a time, AskUserQuestion-style: paths (the four `DEFAULTS` as one confirmable set with per-path override), enabled types (default all six; one line on what disabling means), default branch (detected via `git symbolic-ref refs/remotes/origin/HEAD`, fallback current branch; confirmed), instruction-file disposition (default both; at most one may be declined; consequence stated; persisted).
- [ ] **Step 3:** Mutation sequence per the order-of-operations decision (including the early read-only GitHub inspection when a verified GitHub remote exists), with the exact `.grimore.toml` template:

```toml
[grimore]
components = "docs/components"
current = "docs/current"
specs = "docs/design/specs"
plans = "docs/plans"
default_branch = "main"
types = ["adr", "term", "usecase", "constraint", "nongoal", "note"]
instruction_files = ["CLAUDE.md", "AGENTS.md"]
```

  then validate with `uv run tools/grim.py lint --root <target>` (exit 0 on the empty store).
- [ ] **Step 4:** Manifest + release metadata (moved ahead of the GREEN runs, round 3 finding 4): add `"./adopt-docs"` to `skills`, update `plugin.json` `description` to name all three skills, **bump `version` to `0.2.0`**; update `marketplace.json`'s plugin-entry description likewise. No Codex-compatibility claims (IAM-56). The suite's marketplace guard passes from this commit on.
- [ ] **Step 5: Commit; sonnet task review; fix loop.**

### Task 3: SKILL.md — instruction sections, merge discipline, CI workflow

**Steps:**
- [ ] **Step 1:** Managed-section template with configured paths substituted; clauses: read the current dir at session start; glossary governs terminology; plans carry `spec:`; superpowers spec/plan output redirected to configured dirs; merge discipline (the three CI.md rules); banner clause with provisional marker. Written per the validated disposition, idempotent replace-in-place keyed on the delimiters.
- [ ] **Step 2:** CI workflow offer: embedded template (CI.md recipe + `permissions: contents: read`, vendored path, confirmed branch, workflow `grim` / job `grim-check`), preview-then-consent, collision policy applies. `merge_group` included at generation time when the early inspection found an active queue; the late-detection amend/re-push/re-verify path stated.
- [ ] **Step 3:** GitHub-identity verification and the documented-only degradation (no remote / non-GitHub remote / mismatch), plus the deferred-sequence text (verified remote only; all four check properties; read-back).
- [ ] **Step 4: Commit; sonnet task review; fix loop.**

### Task 4: SKILL.md — charter interview, finish, gated protection, GREEN evidence

**Steps:**
- [ ] **Step 1:** Charter interview: use cases, constraints, non-goals, terms — enabled types only, disabled-type behavior per design decision, one at a time, structured choices, settled-or-speculative asked per capture, self-contained capture procedure, capture log.
- [ ] **Step 2:** Finish: `lint --fix` + `render` + `check`; show the rendered view; offer the adoption commit + push; **only then**, if the gate holds (final workflow bytes pushed; `grim-check` succeeded on that exact SHA from the Actions app; repository identity verified), offer the protection mutation per the design decisions — else emit the deferred sequence (verified GitHub remote) or documented-only text (otherwise).
- [ ] **Step 3:** GREEN runs — all six scenarios including every protection and invalid-config sub-run, each from its pristine fixture, from the cache-shaped bundle, full rubric each. The manifest already carries `0.2.0` (Task 2), so provenance evidence asserts `Source: grimore plugin v0.2.0`. Fix the skill (never the frozen inputs) until all pass; create `result-green.md` (run logs, per-line results, deviations; consent and decline recorded independently). Append-only thereafter.
- [ ] **Step 4: Commit; sonnet task review; fix loop.**

### Task 5: Executable tests, suite, whole-skill review

**Steps:**
- [ ] **Step 1:** `tests/test_adopt_docs.py` — the executable layer from the Verification model, including the YAML `on`-key coercion handling, the `0.2.0` version and description assertions, and an assertion that SKILL.md's provenance text carries the toplevel-verification rule (no bare `rev-parse HEAD`).
- [ ] **Step 2:** Full suite green; `grim lint --root .` clean.
- [ ] **Step 3:** Whole-skill reviewer pass (align precedent): Status / Issues / Recommendations over `adopt-docs/` + this plan; fix Issues, decide each Recommendation deliberately.
- [ ] **Step 4: Commit.**

## After the tasks (process, not tasks)

Opus whole-branch review with ONE fix wave; PR `IAM-43: adopt-docs skill (onboarding)` attached to Linear IAM-43 via `links` (auto-completes on merge); squash merge per convention. Ledger at `.superpowers/sdd/2026-07-26-adopt-docs-skill/progress.md`; archive to `.superpowers/sdd/progress-iam-43-archived.md` before cleanup.

## Out of scope

- Codex plugin packaging, dual-host manifests, canonical layout change — IAM-56.
- Ask-per-adoption grim delivery — IAM-55.
- Running adoption on grimore itself; make_repo fixture hardening; restricted-types align scenario — IAM-46.
- Final banner semantics wording — reconciled when IAM-41 lands.
- finish-docs interplay beyond pointing at it — IAM-44.
