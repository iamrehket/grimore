---
spec: docs/superpowers/specs/2026-07-24-doc-components-design.md
---

<!-- grim:status -->
<!-- /grim:status -->

# adopt-docs skill (IAM-43) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Revision 2 (2026-07-26), incorporating the operator's plan review
(`.scratch/2026-07-26-adopt-docs-plan-review.md`, findings 2-9; finding 1
split out to Linear IAM-56 by operator decision — Codex packaging is a
separate repo-wide effort, not part of this issue).

**Goal:** Ship `adopt-docs/SKILL.md` — the user-invoked onboarding skill that safely (resumably, collision-aware) interviews for configuration, writes `.grimore.toml`, vendors grim and the doc-components schema/templates into the adopting repo, creates the layout, writes equivalent consumption-note managed sections into BOTH `CLAUDE.md` and `AGENTS.md`, documents merge discipline (offering CI + branch-protection configuration on GitHub), and runs the charter-seeding interview whose components are born `current` if confirmed on the spot, `draft` if speculative.

**Architecture:** A skill directory at the repo root (`adopt-docs/`), following the `align/` convention: `SKILL.md` plus `tests/` holding the frozen pressure-test inputs and (appended later) run evidence. New pytest module for the static contracts only — no new adoption runtime: everything the adopting user runs is agent-followed skill text plus the vendored `grim.py`.

**Tech Stack:** Markdown skill text; pressure tests dispatch subagents against scripted scenarios in fixture repos; `uv run tools/grim.py lint|render|check` validates outcomes; pytest asserts the static contracts.

**Verification model:** two layers, split by determinism.

- *Executable (pytest, `tests/test_adopt_docs.py`):* skill file exists with parseable frontmatter; `.claude-plugin/plugin.json` declares it (parity guard already exists in `test_marketplace.py`); the SKILL.md embeds the required consumption-note clauses and the exact `.grimore.toml` template; the embedded CI workflow template parses as YAML, carries `permissions: contents: read`, and its job produces the exact required-check context the skill's protection offer names.
- *Pressure tests (frozen inputs, RED then GREEN, align discipline):* scripted scenarios below. Harness contract, fixed for every run: same model, same tool permissions, same cwd, same scripted answers, fresh fixture repo **with an initial commit** (strict `grim check` needs a resolvable HEAD), and the skill supplied from a **cache-shaped source bundle** — a copy of the repo tree without `.git` — so nothing accidentally depends on git metadata in the skill's own home. The only variable between RED and GREEN is whether the skill text is supplied. Runs record the full answer/tool-call order so one-question-at-a-time and inline capture are auditable.

Spec: docs/superpowers/specs/2026-07-24-doc-components-design.md (Skills / adopt-docs, Adoption and configuration, Merge discipline).
Requirements doc: doc-components/SCHEMA.md. Templates: doc-components/templates/. CI recipe: doc-components/CI.md. Sibling skill: align/SKILL.md. Linear: IAM-43. Related: IAM-55 (ask-per-adoption delivery), IAM-56 (Codex packaging), IAM-46 (dogfood), IAM-41 (banners).

## Global Constraints

- Branch: `aalbright/iam-43-adopt-docs-skill-onboarding`; this plan is its first commit, revised in place before implementation starts.
- **Stage named paths only** — never `git add .` / `-A` / `--all` in the grimore repo (fixture trees under `tmp_path` or `$CLAUDE_JOB_DIR/tmp` are exempt and never committed).
- **Frozen-test rule (scoped per review finding 4):** the frozen set is `scenario-*.md`, `rubric.md`, and `baseline-red.md`. Once Task 1 lands they are never edited to make a run pass; genuine defects require an operator ruling recorded in the ledger. `result-green.md` is expected to be ADDED later (Task 4) and is append-only afterward: new runs append, old evidence is never rewritten.
- **Marketplace manifest guard:** `.claude-plugin/plugin.json` must declare the new skill directory (Task 5) or `tests/test_marketplace.py` fails; CI (IAM-54) gates the merge on the suite.
- **Provisional banner wording:** IAM-41 has not landed. Wherever the skill or note text describes status banners, use the spec's wording marked `(wording provisional until IAM-41 lands)` in an HTML comment beside it.
- **Fixture hygiene:** every fixture repo sets per-repo `user.name`, `user.email`, and `commit.gpgSign=false` at creation (IAM-54 lesson; do not rely on the workflow env block).
- No emojis in any output, skill text, or docs.
- Skill terminology must match SCHEMA.md exactly: component, draft/current/superseded, promote, abandon, supersede edge. No synonyms.
- Do not modify `align/`, `doc-components/`, or `tools/grim.py`. "No new Python" means no new *adoption runtime*; the pytest module for static contracts is in scope.
- Nothing in the skill special-cases grimore; adopting grimore itself is IAM-46.

## Design decisions (local to this plan; spec left them open, or review round 1 forced them)

- **Vendored delivery (operator, 2026-07-26):** copy `tools/grim.py` to `<target>/tools/grim.py`; copy `doc-components/SCHEMA.md`, `doc-components/templates/`, `doc-components/CI.md` to `<target>/doc-components/`. `examples/` is grimore's lint fixture and is not copied. Ask-per-adoption delivery is IAM-55.
- **Source resolution and provenance (review findings 1-carryover, 7):** copy sources resolve relative to the skill's own directory (`../tools/grim.py`, `../doc-components/` from `adopt-docs/`) — valid in a checkout and in the plugin cache (plugin source is `./`). The vendored stamp is `# Vendored from iamrehket/grimore by adopt-docs on <YYYY-MM-DD>. Source: <identity>.` where `<identity>` resolves in order: (1) `git -C <skill-dir> rev-parse HEAD` when the skill's home is a git checkout; (2) `grimore plugin v<version>` read from the bundle's `.claude-plugin/plugin.json` when it is not; (3) the literal `unknown`. Never invent a hash; never stamp the *adopting* repo's HEAD. The cache-shaped GREEN run exercises path (2).
- **Tri-state preflight; no premature completion marker (finding 2):** classify the target as **not adopted** (no `.grimore.toml` and no configured/default components dir), **partially adopted** (config present — including malformed — or layout fragments present, but the completion contract below unmet), or **complete** (all of: `.grimore.toml` loads via the vendored `grim.py lint --root` exit 0; layout dirs exist; vendored files present; both instruction files carry the managed section; render output current — `grim check` exit 0). Complete: report and stop, pointing at align/finish-docs. Partial: inventory per-artifact state (exact match / absent / conflicting), preview a resume-repair plan, proceed only with consent. Malformed TOML is reported with the parse error and never overwritten without consent. Completion is *derived* from the verified artifact set — there is no separate marker file, and `.grimore.toml`'s existence alone is never treated as done.
- **Collision policy, uniform for every mutation (finding 5):** read-only inventory before any write; per target: exact match → keep; absent → create; recognizably managed but stale (older vendored stamp, older managed section) → previewed update; unrelated or conflicting content → stop and ask, never overwrite. Applies to vendored files, layout, instruction files, `.github/workflows/grim.yml`, and branch protection.
- **Dual instruction files (finding 3, minus the Codex-packaging premise):** the consumption note is a delimited managed section (`<!-- grimore:begin -->` ... `<!-- grimore:end -->`) written **identically to both `CLAUDE.md` and `AGENTS.md` by default** — created if absent, appended if present, replaced-in-place idempotently if the managed section already exists, all other content preserved byte-for-byte. The user may explicitly decline one file; the skill states the consequence (that harness gets no instructions) rather than silently offering a one-file choice.
- **Prerequisites before any mutation (finding 8):** `git` present; target is a non-bare work tree with a resolvable root and **at least one commit** (else: offer `git init`+initial commit, or stop; strict `check` is deferred with an explicit statement when history is insufficient); `uv` present (else stop with install pointer — CI installs its own via setup-uv, local adoption does not). Order of operations after the interview: vendor + create layout FIRST, then write `.grimore.toml`, then validate with the vendored linter — the verifier must exist before the step that uses it.
- **Required-check identity (finding 5):** the generated workflow is `name: grim`, job id `check`, no job `name:` override — the check-run context is exactly `check`, and that exact string is what the branch-protection offer configures and the rubric asserts. The workflow adds `permissions: contents: read` and `fetch-depth: 0` per CI.md.
- **Branch protection offer (finding 5):** GitHub remotes only; read current protection/ruleset state first; preview a semantic diff; apply the minimal change (add required `check` context, enable require-up-to-date) preserving unrelated and stricter existing settings; read back and confirm. Declinable; degrade to documented-only with no remote, no `gh`, or no consent.
- **Disabled charter types (finding 9):** the charter interview covers only enabled types; a disabled type's section is skipped with a one-line statement, and if the user volunteers material for a disabled type it is recorded in the adoption summary (not as a component) — grim rejects disabled-type components, and the charter script never assumes a type exists. The four charter sections map: usecase, constraint, nongoal, term.
- **Confirmed vs speculative is asked, never inferred:** each capture ends with an explicit structured question — settled now, or speculative? — deciding `current` vs `draft`. This is the deliberate divergence from align (which only writes drafts); adopt-docs runs before there is code to reconcile against, so user confirmation substitutes for finish-docs promotion.
- **Capture rules are self-contained:** SKILL.md carries the essential capture procedure (template use, slug discipline essentials, one-line announcements, capture log) in its own text; align is cited for rationale only, never as a load-bearing runtime dependency.
- **Adoption ends with a working render:** `lint --fix`, `render`, then `check` (or its deferred-history statement); show the first rendered current view; offer the adoption commit on a branch per the just-documented discipline.

---

### Task 1: Frozen pressure-test inputs and RED baselines

**Files:**
- Create: `adopt-docs/tests/scenario-widget-service.md` (primary)
- Create: `adopt-docs/tests/scenario-resume-agents-only.md`
- Create: `adopt-docs/tests/scenario-bare-restricted.md`
- Create: `adopt-docs/tests/rubric.md`
- Create: `adopt-docs/tests/baseline-red.md`

**Steps:**
- [ ] **Step 1: Harness contract preamble** (in `rubric.md`): the fixed-variables list from the Verification model, including the cache-shaped source bundle and the committed fixture, and the answer/tool-call-order recording requirement.
- [ ] **Step 2: Primary scenario** — fixture "widget-service": git repo with initial commit, per-repo identity + gpgSign off, BOTH `CLAUDE.md` and `AGENTS.md` present with distinct unrelated content, one source file, branch `main`, no remote. Scripted user: default paths except specs at `docs/design/specs`; all six types; confirms detected branch; accepts the CI workflow offer; the protection offer must be handled gracefully absent a remote; charter round scripts one usecase and one constraint confirmed-settled (born `current`), one nongoal floated as undecided (born `draft`), one term settled with a rejected synonym (`current`, synonym on the _Avoid_: line); final message refuses further capture work (batch-pass capture writes nothing).
- [ ] **Step 3: Resume scenario** — fixture with `AGENTS.md` only. Session A is scripted to be cut off immediately after `.grimore.toml` is written (partial vendoring, no instruction files). Session B re-invokes the skill: expected to classify partial, inventory, preview repair, and finish to the full contract with consent — no duplicated managed sections, no clobbered `AGENTS.md` content. Rubric asserts the end state after B and that A alone fails the completion contract.
- [ ] **Step 4: Restricted scenario** — fixture with NEITHER instruction file, types restricted to `["adr", "term", "usecase", "constraint"]`. Rubric: both instruction files created; nongoal charter section skipped with the one-line statement; volunteered nongoal material lands in the adoption summary, not as a component; no `nongoal/` subdir exists. (Placement matrix per finding 3: both-files = primary, AGENTS-only = resume, neither = restricted; CLAUDE-only is symmetric to AGENTS-only and consciously not scripted — noted in the rubric.)
- [ ] **Step 5: Rubric** — per-scenario automatable assertions: `load_config(fixture_root)` succeeds and reflects scripted answers (specs at `docs/design/specs` in primary); layout dirs (enabled types only) + `.gitkeep`s; `tools/grim.py` byte-identical to source below the stamp line, stamp matching the identity rules (cache-shaped run must yield the plugin-version form); `doc-components/` present without `examples/`; both instruction files carry one identical managed section each, prior content intact; workflow file matches the template with context `check`; charter components with scripted statuses; `grim lint` exit 0; `render` populates the current dir; `check` exit 0.
- [ ] **Step 6: RED baselines.** Run each scenario with a subagent given the fixture and request but not the skill; record honest per-rubric-line results in `baseline-red.md`. RED must discriminate — if an unskilled agent passes, strengthen the rubric now (the only moment revision is allowed), then freeze.
- [ ] **Step 7: Commit** (named paths). The frozen set is now frozen.

### Task 2: SKILL.md — prerequisites, tri-state preflight, interview, vendoring, layout, config

**Files:**
- Create: `adopt-docs/SKILL.md` (frontmatter name `adopt-docs`; description triggers on "adopt the doc system", "set up doc components", "onboard this repo to grimore")

**Steps:**
- [ ] **Step 1:** Prerequisite checks and tri-state preflight per the design decisions (including malformed-TOML reporting and the resume-repair flow).
- [ ] **Step 2:** Configuration interview — one question at a time, AskUserQuestion-style: paths (the four `DEFAULTS` as one confirmable set with per-path override), enabled types (default all six; one line on what disabling means), default branch (detected via `git symbolic-ref refs/remotes/origin/HEAD`, falling back to the current branch; confirmed).
- [ ] **Step 3:** Mutation sequence: read-only inventory → collision policy per target → vendor (with stamp identity rules) → layout (enabled-type subdirs, `.gitkeep`) → write `.grimore.toml` (exact template below, `[grimore]` table — `load_config` reads only that table) → validate with `uv run tools/grim.py lint --root <target>` (the now-vendored copy; expect exit 0 on the empty store).

```toml
[grimore]
components = "docs/components"
current = "docs/current"
specs = "docs/design/specs"
plans = "docs/plans"
default_branch = "main"
types = ["adr", "term", "usecase", "constraint", "nongoal", "note"]
```

- [ ] **Step 4: Commit; sonnet task review; fix loop.**

### Task 3: SKILL.md — dual instruction files, merge discipline, external configuration offers

**Steps:**
- [ ] **Step 1:** Managed-section template with configured paths substituted; clauses: read the current dir at session start; glossary governs terminology; plans carry `spec:`; superpowers spec/plan output redirected to configured dirs; merge discipline (the three CI.md rules); banner clause with provisional marker. Dual-file write per the design decision, idempotent replace-in-place keyed on the delimiters.
- [ ] **Step 2:** CI workflow offer: instantiate the embedded template (from CI.md's recipe + `permissions` block, vendored path, confirmed branch, context `check`), preview-then-consent, collision policy applies.
- [ ] **Step 3:** Branch protection offer per the design decision (read, semantic diff, minimal change, preserve stricter settings, read back, verify). Graceful degradation paths stated.
- [ ] **Step 4: Commit; sonnet task review; fix loop.**

### Task 4: SKILL.md — charter interview, finish, GREEN evidence

**Steps:**
- [ ] **Step 1:** Charter interview: use cases, constraints, non-goals, terms — enabled types only, disabled-type behavior per design decision, one at a time, structured choices, settled-or-speculative asked per capture, self-contained capture procedure, capture log.
- [ ] **Step 2:** Finish: `lint --fix` + `render` + `check` (or deferred-history statement); show the rendered view; offer the adoption commit.
- [ ] **Step 3:** GREEN runs — all three scenarios, from the cache-shaped bundle, full rubric each. Fix the skill (never the frozen inputs) until all pass; create `adopt-docs/tests/result-green.md` recording run logs, per-line rubric results, and deviations. Append-only thereafter.
- [ ] **Step 4: Commit; sonnet task review; fix loop.**

### Task 5: Manifest, executable tests, suite, whole-skill review

**Steps:**
- [ ] **Step 1:** Add `"./adopt-docs"` to `skills` in `.claude-plugin/plugin.json`; update the plugin `description` to name all three skills (current text lists only align and explain-diff).
- [ ] **Step 2:** `tests/test_adopt_docs.py` — the executable layer from the Verification model (frontmatter parse, embedded `.grimore.toml` template parses via tomllib with the `[grimore]` table, embedded workflow template parses as YAML with `permissions` + context `check`, required note clauses present, frozen-test files exist).
- [ ] **Step 3:** Full suite green; `grim lint --root .` clean.
- [ ] **Step 4:** Whole-skill reviewer pass (align precedent): Status / Issues / Recommendations over `adopt-docs/` + this plan; fix Issues, decide each Recommendation deliberately.
- [ ] **Step 5: Commit.**

## After the tasks (process, not tasks)

Opus whole-branch review with ONE fix wave; PR `IAM-43: adopt-docs skill (onboarding)` attached to Linear IAM-43 via `links` (auto-completes on merge); squash merge per convention. Ledger at `.superpowers/sdd/2026-07-26-adopt-docs-skill/progress.md`; archive to `.superpowers/sdd/progress-iam-43-archived.md` before cleanup.

## Out of scope

- Codex plugin packaging, dual-host manifests, canonical layout change — IAM-56.
- Ask-per-adoption grim delivery — IAM-55.
- Running adoption on grimore itself; make_repo fixture hardening; restricted-types align scenario — IAM-46.
- Final banner semantics wording — reconciled when IAM-41 lands.
- finish-docs interplay beyond pointing at it — IAM-44.
