---
spec: docs/superpowers/specs/2026-07-24-doc-components-design.md
---

<!-- grim:status -->
<!-- /grim:status -->

# adopt-docs skill (IAM-43) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `adopt-docs/SKILL.md` — the user-invoked, once-per-project onboarding skill that interviews for configuration, writes `.grimore.toml`, vendors grim and the doc-components schema/templates into the adopting repo, creates the layout, adds the consumption note to CLAUDE.md/AGENTS.md, documents merge discipline (offering CI + branch-protection configuration on GitHub), and runs the charter-seeding interview whose components are born `current` if confirmed on the spot, `draft` if speculative.

**Architecture:** A skill directory at the repo root (`adopt-docs/`), following the `align/` convention: `SKILL.md` plus `tests/` holding the frozen pressure-test scenario, rubric, RED baseline, and GREEN result. No new Python. The skill composes: a preflight check, a configuration interview (one question at a time, AskUserQuestion-style structured choices), a `.grimore.toml` writer matching `tools/grim.py`'s `load_config` contract exactly, file vendoring, consumption-note authoring, merge-discipline documentation with declinable configuration offers, and a charter-seeding capture interview that follows align's capture procedure but may write `status: current`.

**Tech Stack:** Markdown skill text; pressure tests run by dispatching subagents against a scripted scenario in a fixture repo; `uv run tools/grim.py lint|render|check` validates what the test session produces.

**Verification model (pressure-test discipline, per align precedent):** write the failing scenario first (RED — an agent without the skill, told to "set this repo up for the grimore doc system", produces config grim cannot load, no vendored tooling, no confirmed-vs-speculative status distinction), then the skill text that fixes it (GREEN — the same scripted session yields a loadable config, a complete layout, vendored files, the consumption note, and charter components with correct statuses). Assertions that survive automation: `load_config` on the fixture root succeeds and reflects the scripted answers; expected directories and files exist; vendored `grim.py` byte-matches the source below its stamp header; the consumption note contains each required clause; charter components lint clean with the scripted statuses; `grim render` succeeds and `grim check` exits 0 in the fixture.

Spec: docs/superpowers/specs/2026-07-24-doc-components-design.md (Skills / adopt-docs, Adoption and configuration, Merge discipline).
Requirements doc: doc-components/SCHEMA.md. Templates: doc-components/templates/. CI recipe: doc-components/CI.md. Sibling skill: align/SKILL.md. Linear: IAM-43.

## Global Constraints

- Branch: `aalbright/iam-43-adopt-docs-skill-onboarding`. This plan file is the branch's first commit.
- **Stage named paths only** — never `git add .` / `-A` / `--all` in the grimore repo (fixture trees under `tmp_path` or `$CLAUDE_JOB_DIR/tmp` are exempt and never committed).
- **Frozen-test rule (align precedent):** after Task 1 lands, `adopt-docs/tests/` is never edited to make a run pass. Later tasks fix the skill, not the test. Genuine scenario defects require an operator ruling, recorded in the ledger.
- **Marketplace manifest guard:** the new skill directory MUST be declared in `.claude-plugin/plugin.json` (Task 5) or `tests/test_marketplace.py` fails the suite. CI now runs the suite on every PR (IAM-54), so this gates the merge.
- **Provisional banner wording:** IAM-41 (banner derivation) has not landed. Everywhere the skill or consumption note describes status banners, use the spec's wording and mark it `(wording provisional until IAM-41 lands)` in an HTML comment beside it. Reconcile when IAM-41 merges; do not block on it.
- No emojis in any output, skill text, or docs.
- Skill terminology must match SCHEMA.md exactly: component, draft/current/superseded, promote, abandon, supersede edge. No synonyms.
- Do not modify `align/`, `doc-components/`, or `tools/grim.py`. The skill adapts by instruction text only.
- The skill must not assume this repo (grimore) is the adoption target. Running adopt-docs on grimore itself is IAM-46, not this issue — nothing in the skill special-cases grimore.

## Design decisions (local to this plan; spec left them open)

- **Vendored delivery (operator decision, 2026-07-26):** adoption copies `tools/grim.py` to `<target>/tools/grim.py` and `doc-components/SCHEMA.md`, `doc-components/templates/`, `doc-components/CI.md` to `<target>/doc-components/` — `examples/` is grimore's lint fixture and is NOT copied. The vendored `grim.py` gets a stamp comment under its shebang: `# Vendored from iamrehket/grimore@<commit> by adopt-docs on <date>.` Ask-per-adoption delivery (plugin-cache reference) is deferred to IAM-55.
- **Copy sources resolve relative to the skill's own directory** (`../tools/grim.py`, `../doc-components/` from `adopt-docs/`): correct both in a repo checkout and in the installed plugin cache, which carries the whole repo (plugin source is `./`).
- **`.grimore.toml` is written explicit and complete:** all five path/branch keys plus `types`, under the `[grimore]` table (`load_config` reads only that table), even when every answer is a default. A reader of the file learns the whole contract; implicit defaults hide it.
- **Preflight:** if `.grimore.toml` exists at the target root, the project is adopted — report the existing config, point at align/finish-docs, and stop. adopt-docs is once-per-project; there is no re-run/merge mode in v1.
- **Default branch is detected, then confirmed** (from `git symbolic-ref refs/remotes/origin/HEAD`, falling back to the current branch), never silently assumed.
- **Layout:** create the components dir with one subdirectory per *enabled* type only, plus the current/specs/plans dirs; `.gitkeep` in each empty leaf so the layout survives commit.
- **Consumption note placement:** append to CLAUDE.md if present, else AGENTS.md if present; if both exist, ask which (or both); if neither, offer to create CLAUDE.md. Append under a clearly-delimited heading — never rewrite existing content.
- **Confirmed vs speculative is asked, never inferred:** each charter capture ends with an explicit structured question — "settled now, or speculative?" — and that answer alone decides `current` vs `draft`. This is the one deliberate divergence from align (which only ever writes drafts): adopt-docs runs before any code exists to reconcile against, so user confirmation substitutes for finish-docs promotion. Everything else about capture (templates, slug discipline, one-line announcements, capture log) follows align/SKILL.md's procedure by reference.
- **Configuration offers are declinable and previewed:** the CI workflow file and branch-protection changes are written only after showing exactly what will be created/changed and getting explicit consent. Declining leaves the merge discipline documented but unconfigured (the grimore-repo ruling — document, don't configure — falls out of this naturally).
- **Adoption ends with a working render:** after charter seeding, run `uv run tools/grim.py lint --fix` then `render` in the target so `docs/current/` (or configured equivalent) exists from day one, then offer to commit the adoption on a branch per the just-documented merge discipline.

---

### Task 1: Pressure-test scenario, rubric, and RED baseline

**Files:**
- Create: `adopt-docs/tests/scenario-widget-service.md` (the scripted adoption session)
- Create: `adopt-docs/tests/rubric.md` (pass/fail assertions)
- Create: `adopt-docs/tests/baseline-red.md` (recorded RED result)

**Interfaces:**
- Produces: the frozen apparatus Tasks 2-4 build against and Task 5 records GREEN against.

- [ ] **Step 1: Write the scenario.** A fixture git repo (built under `tmp_path`-style scratch, per-fixture git identity and `commit.gpgSign=false` — see the IAM-54 lesson) for a fictional "widget-service" project containing: an existing `CLAUDE.md` with unrelated content (tests append-not-clobber), a `README.md`, one source file, on branch `main`, no remote. The scripted user:
  - accepts default paths EXCEPT specs, which they place at `docs/design/specs` (catches a writer that hardcodes defaults);
  - enables all six component types;
  - confirms the detected default branch;
  - accepts the CI workflow offer, declines the branch-protection offer (no remote exists; the skill must handle that gracefully rather than error);
  - in the charter interview: confirms one usecase and one constraint as settled (must be born `current`), floats one nongoal as "probably, but haven't decided" (must be born `draft`), and settles one glossary term with a rejected synonym (term component, `current`, synonym on the _Avoid_: line);
  - final message refuses further capture work (align's instrumentation: batch-pass capture writes nothing).
- [ ] **Step 2: Write the rubric.** Automatable assertions, each pass/fail: `load_config(fixture_root)` succeeds; `specs` resolves to `docs/design/specs`; all six types enabled; layout dirs + `.gitkeep`s exist; `tools/grim.py` present, byte-identical to source below the stamp line; `doc-components/` present without `examples/`; `CLAUDE.md` retains its prior content and gains the note containing each required clause (read-current-at-session-start, glossary governs terminology, plans carry `spec:`, superpowers spec/plan output redirected to configured dirs, merge discipline, provisional banner marker); `.github/workflows/grim.yml` exists and references the vendored path; four charter components exist with the scripted statuses; `grim lint` exit 0; `grim render` populates the current dir; `grim check` exit 0.
- [ ] **Step 3: Record RED.** Run the scenario with a subagent that has the fixture and the request but NOT the skill. Record the result honestly in `baseline-red.md` — which rubric lines fail and how. RED must discriminate: if an unskilled agent passes the full rubric, the rubric is too weak; revise before freezing (this is the only moment revision is allowed).
- [ ] **Step 4: Commit** (named paths). `adopt-docs/tests/` is now frozen.

### Task 2: SKILL.md — preflight, configuration interview, config writer, vendoring, layout

**Files:**
- Create: `adopt-docs/SKILL.md` (frontmatter: name `adopt-docs`; description triggers on "adopt the doc system", "set up doc components", "onboard this repo to grimore")

**Steps:**
- [ ] **Step 1: Preflight section** per the design decision above.
- [ ] **Step 2: Configuration interview.** One question at a time, AskUserQuestion-style with concrete options: paths (present the four defaults from grim's `DEFAULTS` as one confirmable set, with per-path override), enabled types (default all of `adr`, `term`, `usecase`, `constraint`, `nongoal`, `note`; explain in one line what disabling a type means — align records disabled-type decisions in spec bodies instead), default branch (detected, confirmed).
- [ ] **Step 3: Config writer.** Emit `.grimore.toml` — document the exact shape in the skill with a filled example:

```toml
[grimore]
components = "docs/components"
current = "docs/current"
specs = "docs/design/specs"
plans = "docs/plans"
default_branch = "main"
types = ["adr", "term", "usecase", "constraint", "nongoal", "note"]
```

  All paths repo-root-relative (grim rejects paths escaping the root). After writing, verify by running `uv run tools/grim.py lint --root <target>` (vendored copy; expect exit 0 on the empty store).
- [ ] **Step 4: Vendoring + layout** per the design decisions (copy list, stamp line, per-enabled-type subdirs, `.gitkeep`).
- [ ] **Step 5: Commit; sonnet task review; fix loop.**

### Task 3: SKILL.md — consumption note, merge discipline, configuration offers

**Steps:**
- [ ] **Step 1: Consumption note.** Draft text lives in the skill as a fill-in template with the configured paths substituted; clauses per the rubric (Task 1 Step 2 list). Placement per the design decision. Banner clause carries the provisional marker.
- [ ] **Step 2: Merge discipline.** Document the three rules (require-up-to-date, `grim check` on PR, `grim check` on default branch) in the note, sourced from `doc-components/CI.md` — the vendored copy the adopting repo now owns.
- [ ] **Step 3: Offers.** CI workflow: instantiate CI.md's recipe with the vendored script path and confirmed default branch into `.github/workflows/grim.yml`, preview-then-consent. Branch protection (GitHub remotes only): offer required `grim` check + require-up-to-date via `gh`, preview-then-consent; degrade gracefully (documented-only) when declined, when there is no remote, or when `gh` is absent/unauthenticated.
- [ ] **Step 4: Commit; sonnet task review; fix loop.**

### Task 4: SKILL.md — charter-seeding interview, finish, GREEN run

**Steps:**
- [ ] **Step 1: Charter interview.** Cover in order: use cases, constraints, non-goals, first glossary terms — one at a time, structured choices, following the user's energy (align's rule). Capture procedure by explicit reference to align/SKILL.md (templates, slug discipline, announcements, capture log), with the two divergences stated: the settled-or-speculative question deciding `current`/`draft`, and capture happening against the just-created empty store.
- [ ] **Step 2: Finish.** `lint --fix` + `render` + `check`; show the user their first rendered current view; offer the adoption commit on a branch per the documented discipline.
- [ ] **Step 3: GREEN run.** Dispatch the scenario against the completed skill; evaluate the full rubric. Fix the SKILL (never the tests) until GREEN; record the passing run in `adopt-docs/tests/result-green.md` (align's format: run log, rubric line results, deviations noted).
- [ ] **Step 4: Commit; sonnet task review; fix loop.**

### Task 5: Manifest, suite, whole-skill review

**Steps:**
- [ ] **Step 1:** Add `"./adopt-docs"` to `skills` in `.claude-plugin/plugin.json`.
- [ ] **Step 2:** Full suite (`uv run pytest`) green — with per-fixture git identity + gpgSign guards for any fixture work; `grim lint --root .` clean.
- [ ] **Step 3:** Whole-skill reviewer pass (align precedent): dispatch a reviewer subagent over `adopt-docs/` + this plan's requirements; Status / Issues / Recommendations; fix Issues, decide each Recommendation deliberately.
- [ ] **Step 4: Commit.**

## After the tasks (process, not tasks)

Opus whole-branch review with ONE fix wave; then PR titled `IAM-43: adopt-docs skill (onboarding)`, attached to Linear IAM-43 via `links` on save_issue (auto-completes on merge). Squash merge per convention. Ledger at `.superpowers/sdd/2026-07-26-adopt-docs-skill/progress.md`; archive to `.superpowers/sdd/progress-iam-43-archived.md` before cleanup.

## Out of scope

- Ask-per-adoption grim delivery — IAM-55.
- Running adoption on grimore itself, make_repo fixture hardening, restricted-types align scenario — IAM-46.
- Final banner semantics wording — reconciled when IAM-41 lands.
- finish-docs interplay beyond pointing at it — IAM-44.
