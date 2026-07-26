---
spec: docs/superpowers/specs/2026-07-24-doc-components-design.md
---

<!-- grim:status -->
<!-- /grim:status -->

# adopt-docs skill (IAM-43) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Revision 3 (2026-07-26). Round 1 review folded findings 2-9 in and split
Codex packaging to IAM-56. Round 2 review
(`.scratch/2026-07-26-adopt-docs-plan-review-round-2.md`) drove: adoption
state separated from grim health, durable instruction-file disposition,
real collision/idempotency scenarios, unique check name with deferred
protection, deterministic secondary scripts, and release metadata in Task 5.

**Goal:** Ship `adopt-docs/SKILL.md` — the Claude-packaged onboarding skill that writes instructions for both harness files (`CLAUDE.md` and `AGENTS.md`; Codex *packaging* is IAM-56 and the marketplace is not described as Codex-compatible until it lands). It safely (resumably, collision-aware) interviews for configuration, vendors grim and the doc-components schema/templates, creates the layout, writes `.grimore.toml`, installs the dual managed instruction sections, documents merge discipline (offering CI and — once the check has actually run — branch protection), and runs the charter-seeding interview whose components are born `current` if confirmed on the spot, `draft` if speculative.

**Architecture:** A skill directory at the repo root (`adopt-docs/`), following the `align/` convention: `SKILL.md` plus `tests/` holding the frozen pressure-test inputs (including a recording `gh` stub) and appended run evidence. New pytest module for static contracts only — no new adoption runtime.

**Tech Stack:** Markdown skill text; pressure tests dispatch subagents against scripted scenarios in fixture repos; `uv run tools/grim.py lint|render|check` validates outcomes; pytest asserts static contracts; a stub `gh` (shell script, part of the frozen inputs) fakes the GitHub API for the protection scenario.

**Verification model:** two layers, split by determinism.

- *Executable (pytest, `tests/test_adopt_docs.py`):* skill file exists with parseable frontmatter; manifest declares it; SKILL.md embeds the required note clauses and the exact `.grimore.toml` template (parses via tomllib, `[grimore]` table); the embedded CI workflow template parses as YAML — asserting the trigger key as `on` *or* YAML 1.1's coerced boolean-`True` key, whichever the loader yields — with `permissions: contents: read` and job id `grim-check` and no job `name:` override; `plugin.json` version equals the release value below and `marketplace.json`'s description names all three skills; SKILL.md's provenance-fallback instruction reads the version from the manifest rather than hardcoding a literal.
- *Pressure tests (frozen inputs, RED then GREEN, align discipline):* five scenarios below. Harness contract, fixed for every run: same model, tool permissions, cwd, source bundle, and scripted answers; fresh fixture repo **with an initial commit** and per-repo identity + `commit.gpgSign=false`; the skill supplied from a **cache-shaped source bundle** (repo tree without `.git`); every scenario file carries its **complete ordered answer script** and, where applicable, a **bounded interrupt rule**. The only RED/GREEN variable is whether the skill text is supplied. Runs record full answer/tool-call order so one-question-at-a-time, inline capture, and refusal behaviors are auditable from the transcript (the transcript is a legitimate rubric observation point).

Spec: docs/superpowers/specs/2026-07-24-doc-components-design.md (Skills / adopt-docs, Adoption and configuration, Merge discipline).
Requirements doc: doc-components/SCHEMA.md. Templates: doc-components/templates/. CI recipe: doc-components/CI.md. Sibling skill: align/SKILL.md. Linear: IAM-43. Related: IAM-55 (ask-per-adoption delivery), IAM-56 (Codex packaging), IAM-46 (dogfood), IAM-41 (banners).

## Global Constraints

- Branch: `aalbright/iam-43-adopt-docs-skill-onboarding`; this plan is its first commit, revised in place before implementation starts.
- **Stage named paths only** — never `git add .` / `-A` / `--all` in the grimore repo (fixture trees under `tmp_path` or `$CLAUDE_JOB_DIR/tmp` are exempt and never committed).
- **Frozen-test rule:** the frozen set is `scenario-*.md`, `rubric.md`, `baseline-red.md`, and `stub-gh`. Once Task 1 lands they are never edited to make a run pass; genuine defects require an operator ruling recorded in the ledger. `result-green.md` is ADDED later (Task 4) and is append-only afterward.
- **Marketplace manifest guard:** `.claude-plugin/plugin.json` must declare the new skill directory (Task 5) or `tests/test_marketplace.py` fails; CI (IAM-54) gates the merge on the suite.
- **Provisional banner wording:** IAM-41 has not landed. Banner descriptions use the spec's wording marked `(wording provisional until IAM-41 lands)` in an HTML comment beside them.
- No emojis in any output, skill text, or docs.
- Skill terminology must match SCHEMA.md exactly: component, draft/current/superseded, promote, abandon, supersede edge. No synonyms.
- Do not modify `align/`, `doc-components/`, or `tools/grim.py`. "No new Python" means no new *adoption runtime*; the pytest module and the test-harness `gh` stub are in scope.
- Nothing in the skill special-cases grimore; adopting grimore itself is IAM-46.

## Design decisions (spec left them open, or review rounds forced them)

- **Vendored delivery (operator, 2026-07-26):** copy `tools/grim.py` to `<target>/tools/grim.py`; copy `doc-components/SCHEMA.md`, `templates/`, `CI.md` to `<target>/doc-components/`. `examples/` is not copied. Ask-per-adoption delivery is IAM-55.
- **Source resolution and provenance:** copy sources resolve relative to the skill's own directory (`../tools/grim.py`, `../doc-components/`) — valid in a checkout and in the plugin cache. Vendored stamp: `# Vendored from iamrehket/grimore by adopt-docs on <YYYY-MM-DD>. Source: <identity>.` — identity ladder: (1) `git -C <skill-dir> rev-parse HEAD` when the skill's home is a checkout; (2) `grimore plugin v<version>` read from the bundle's `.claude-plugin/plugin.json`; (3) literal `unknown`. Never invented; never the adopting repo's HEAD. The cache-shaped GREEN runs exercise (2), which is meaningful because Task 5 bumps the version.
- **Adoption state is stable; health is separate (round 2 finding 1):**
  - **not adopted** — no recognizable adoption artifact (config, stamped vendored file, managed section, or layout dir);
  - **partial** — at least one recognizable adoption artifact, but the stable footprint below is incomplete;
  - **adopted** — the stable footprint is complete: `.grimore.toml` parses with a `[grimore]` table; recognized vendored payload (stamp line present; below-stamp bytes match the bundled source); layout dirs for enabled types; every file listed in the recorded instruction-file disposition carries the managed section;
  - **health** — only after classifying *adopted*, optionally run `lint`/`check` and report healthy/unhealthy. Health NEVER changes adoption state: an unhealthy adopted repo is handed to finish-docs / ordinary grim remediation, never to adoption repair.
  Partial → inventory per-artifact (exact match / absent / managed-stale / conflicting), preview a resume-repair plan, proceed only with consent. Malformed TOML is reported with the parse error, never overwritten without consent.
- **Never execute unverified target code:** classification and any preflight parsing use the *bundle's* `grim.py`, not the target's. `<target>/tools/grim.py` is executed only after its stamp and below-stamp bytes are verified against the bundled source; a conflicting file is reported without execution.
- **Instruction-file disposition is durable (round 2 finding 1):** the dual-file default writes an identical delimited managed section (`<!-- grimore:begin -->` ... `<!-- grimore:end -->`) to both `CLAUDE.md` and `AGENTS.md` — created if absent, appended if present, replaced-in-place idempotently when the section exists, all other content preserved. A user may explicitly decline a file; the choice is persisted as `instruction_files = [...]` under `[grimore]` in `.grimore.toml` (a key `load_config` ignores — verified: it validates only its known keys), so decline and absence are distinguishable forever and the *adopted* classification honors the recorded disposition. The skill states the consequence of a decline (that harness gets no instructions).
- **Collision policy, uniform for every mutation:** read-only inventory before any write; per target: exact match → keep; absent → create; recognizably managed but stale (older stamp, older managed section) → previewed update; unrelated or conflicting → stop and ask, never overwrite, never execute. Applies to vendored files, layout, instruction files, `.github/workflows/grim.yml`, and branch protection.
- **Prerequisites (round 2 finding 5, one contract):** `git` present; target is a non-bare work tree with a resolvable root; `uv` present (else stop with install pointer). **At least one commit is required: with no history the skill stops before any mutation and asks the user to establish the initial commit themselves.** No skill-created initial commit; no deferred-check mode — after the user commits, adoption proceeds and the rubric's `check` assertions hold unconditionally.
- **Order of operations:** inventory → vendor + layout → `.grimore.toml` → validate with the (just-verified-or-just-written) vendored linter → instruction sections → CI workflow → charter → finish.
- **Required-check identity (round 2 finding 3):** workflow `name: grim`, job id `grim-check`, no job `name:` override — the check-run context is exactly `grim-check` (unique, not the repo-common `check`), asserted verbatim in template, rubric, pytest, and the protection offer.
- **Branch protection is deferred until the check exists (round 2 finding 3):** the adoption session writes the workflow, but protection is mutated only if, within the session, the workflow has been committed AND pushed AND the exact `grim-check` check has completed successfully on the remote (GitHub requires a recent successful run for a required check to be satisfiable). Otherwise the skill prints a precise deferred command sequence (verify the check ran, then the exact `gh` invocation) in the adoption summary instead of mutating early. When it does mutate: read current classic-protection AND ruleset state (both APIs — this repo itself answers "not protected" on classic while an active ruleset carries required checks), preview a semantic diff, apply the minimal change preserving unrelated and stricter settings, read back and verify. If an active merge queue is detected, add `merge_group` to the workflow triggers; if the queue state cannot be established, decline the mutation with an explicit explanation. Declinable; degrades to documented-only with no remote, no `gh`, or no consent.
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
- Create: `adopt-docs/tests/scenario-protection-stub.md`
- Create: `adopt-docs/tests/stub-gh` (recording fake `gh`, shell script)
- Create: `adopt-docs/tests/rubric.md`
- Create: `adopt-docs/tests/baseline-red.md`

**Steps:**
- [ ] **Step 1: Harness contract preamble** (in `rubric.md`): fixed-variables list from the Verification model; every scenario embeds its complete ordered answer script; interrupt rules are bounded ("interrupt on X; if X has not occurred by the session's terminal response or 25 exchanges, end there" — RED runs may never reach X).
- [ ] **Step 2: Primary scenario** — fixture "widget-service": committed repo, BOTH `CLAUDE.md` and `AGENTS.md` with distinct unrelated content, one source file, branch `main`, no remote. Script: default paths except specs at `docs/design/specs`; all six types; confirm detected branch; accept the CI workflow; no remote → rubric asserts the deferred-protection command text appears in the adoption summary; charter: one usecase and one constraint confirmed-settled (`current`), one nongoal floated undecided (`draft`), one term settled with a rejected synonym (`current`, synonym on _Avoid_:); final message refuses further capture work.
- [ ] **Step 3: Resume scenario** — fixture with `AGENTS.md` only. Session A: full script, **interrupted immediately after the first managed instruction section is written** (bounded rule above). Session B re-invokes: expected to classify *partial*, inventory, preview repair, and finish with consent — the existing `AGENTS.md` section replaced-or-preserved without duplication, the missing `CLAUDE.md` created with its peer section, surrounding content intact. Rubric also asserts session A's end state alone fails the adopted classification.
- [ ] **Step 4: Restricted scenario** (`scenario-neither-restricted.md` — the fixture is a normal committed repo; "neither" refers to instruction files) — NEITHER instruction file, types `["adr", "term", "usecase", "constraint"]`. Script includes **one usecase confirmed-settled (`current`)** so render output is populated, plus volunteered nongoal material. Rubric: both instruction files created; nongoal section skipped with the one-line statement; the volunteered material appears in the capture log / final summary (transcript observation) and no `nongoal/` dir or component exists; render populated; `check` exit 0.
- [ ] **Step 5: Collision scenario** — fixture seeded with an **unrelated `tools/grim.py` that writes a sentinel file if executed** and an unrelated `.github/workflows/grim.yml`. Script: user, shown the inventory, chooses to stop. Rubric: adoption halts; both seeded files byte-unchanged; **sentinel absent** (the unrecognized script was never executed); no other artifact written; the inventory report names both conflicts.
- [ ] **Step 6: Protection scenario** — fixture with a local bare remote; `stub-gh` first on PATH. The stub returns canned payloads: classic-protection 404, a ruleset containing an existing stricter rule and an active merge queue, and a successful `grim-check` check-run; it records every invocation to a log. Script: consent to workflow, adoption commit, push, and protection. Rubric, from the stub's recorded requests: existing rules preserved; only the minimal change requested (required context exactly `grim-check`, require-up-to-date); `merge_group` added to the workflow triggers; a read-back query follows the mutation; and a decline sub-run (same fixture, scripted decline) records **zero** mutating requests.
- [ ] **Step 7: Rubric** — per-scenario assertions as above plus the invariants: `load_config(fixture_root)` succeeds and reflects scripted answers (including persisted `instruction_files`); layout dirs (enabled types only) + `.gitkeep`s; vendored `grim.py` byte-identical below the stamp, stamp matching the identity ladder (cache-shaped runs must yield the plugin-version form); `doc-components/` without `examples/`; managed sections identical across written files, prior content byte-intact; workflow matches the template (context `grim-check`); charter components with scripted statuses; `grim lint` exit 0; render populated; `check` exit 0.
- [ ] **Step 8: RED baselines.** Run every scenario (and the decline sub-run) with a subagent given fixture + request but not the skill; record honest per-line results. RED must discriminate; strengthen now or never. Freeze.
- [ ] **Step 9: Commit** (named paths).

### Task 2: SKILL.md — prerequisites, state classifier, interview, vendoring, layout, config

**Files:**
- Create: `adopt-docs/SKILL.md` (frontmatter name `adopt-docs`; description triggers on "adopt the doc system", "set up doc components", "onboard this repo to grimore")

**Steps:**
- [ ] **Step 1:** Prerequisite checks (single contract above) and the four-part state/health classifier, including bundle-side execution rule, stamp verification before target-side execution, malformed-TOML handling, and the resume-repair flow.
- [ ] **Step 2:** Configuration interview — one question at a time, AskUserQuestion-style: paths (the four `DEFAULTS` as one confirmable set with per-path override), enabled types (default all six; one line on what disabling means), default branch (detected via `git symbolic-ref refs/remotes/origin/HEAD`, fallback current branch; confirmed), instruction-file disposition (default both; explicit decline persisted, consequence stated).
- [ ] **Step 3:** Mutation sequence per the order-of-operations decision, with the exact `.grimore.toml` template:

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
- [ ] **Step 4: Commit; sonnet task review; fix loop.**

### Task 3: SKILL.md — instruction sections, merge discipline, CI workflow

**Steps:**
- [ ] **Step 1:** Managed-section template with configured paths substituted; clauses: read the current dir at session start; glossary governs terminology; plans carry `spec:`; superpowers spec/plan output redirected to configured dirs; merge discipline (the three CI.md rules); banner clause with provisional marker. Written per the disposition, idempotent replace-in-place keyed on the delimiters.
- [ ] **Step 2:** CI workflow offer: embedded template (CI.md recipe + `permissions: contents: read`, vendored path, confirmed branch, workflow `grim` / job `grim-check`), preview-then-consent, collision policy applies. `merge_group` trigger included when the protection flow (Task 4) detects a merge queue.
- [ ] **Step 3:** Deferred-protection text: the exact command sequence (verify `grim-check` succeeded on the remote, then the `gh` mutation, then read-back) emitted whenever the in-session gate cannot be met.
- [ ] **Step 4: Commit; sonnet task review; fix loop.**

### Task 4: SKILL.md — charter interview, finish, gated protection, GREEN evidence

**Steps:**
- [ ] **Step 1:** Charter interview: use cases, constraints, non-goals, terms — enabled types only, disabled-type behavior per design decision, one at a time, structured choices, settled-or-speculative asked per capture, self-contained capture procedure, capture log.
- [ ] **Step 2:** Finish: `lint --fix` + `render` + `check`; show the rendered view; offer the adoption commit + push; **only then**, if the gate holds (workflow pushed, `grim-check` completed successfully on the remote), offer the protection mutation per the design decision — else emit the deferred command sequence.
- [ ] **Step 3:** GREEN runs — all five scenarios plus the decline sub-run, from the cache-shaped bundle, full rubric each. Fix the skill (never the frozen inputs) until all pass; create `result-green.md` (run logs, per-line results, deviations). Append-only thereafter.
- [ ] **Step 4: Commit; sonnet task review; fix loop.**

### Task 5: Manifest, release metadata, executable tests, suite, whole-skill review

**Steps:**
- [ ] **Step 1:** `.claude-plugin/plugin.json`: add `"./adopt-docs"` to `skills`, update `description` to name all three skills, **bump `version` to `0.2.0`** (the provenance fallback must distinguish the bundle that contains adopt-docs). `.claude-plugin/marketplace.json`: update the plugin entry description likewise. No Codex-compatibility claims anywhere (IAM-56).
- [ ] **Step 2:** `tests/test_adopt_docs.py` — the executable layer from the Verification model, including the YAML `on`-key coercion handling and the version/description assertions.
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
