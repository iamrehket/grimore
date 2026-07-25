---
spec: docs/superpowers/specs/2026-07-24-doc-components-design.md
---

<!-- grim:status -->
<!-- /grim:status -->

# align skill (IAM-39) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `align/SKILL.md` — the brainstorm/alignment skill that interviews one question at a time and captures doc components inline at crystallization moments, outputting a spec whose Decisions block references the created component IDs.

**Architecture:** A skill directory at the repo root (`align/`), following the `explain-diff/` convention: `SKILL.md` plus `tests/` holding the pressure-test scenario and its rubric. No Python. The skill composes: superpowers-brainstorming-style interviewing, Pocock-style grilling/domain-modeling, inline component capture against `doc-components/templates/`, spec authoring from `doc-components/templates/spec.md`, an advisory spec-reviewer subagent loop, and a handoff to upstream `superpowers:writing-plans`.

**Tech Stack:** Markdown skill text; pressure tests run by dispatching subagents against a scripted scenario; `uv run tools/grim.py lint` validates the components the test session produces.

**Verification model (pressure-test discipline, per superpowers:writing-skills):** write the failing scenario first (RED — an agent without the skill does not capture inline), then the skill text that fixes it (GREEN — the same scripted session produces a term and an ADR the moment they settle, plus a spec referencing them). Assertions that survive automation: which files exist at end of session, their lint-validity, and the spec's references. "Inline vs batch" is asserted by instrumenting the scenario: the scripted user's final message refuses further capture work, so components that only get written in a final batch pass never get written at all.

Spec: docs/superpowers/specs/2026-07-24-doc-components-design.md (Skills / align, Component store, Specs and plans).
Requirements doc: doc-components/SCHEMA.md. Templates: doc-components/templates/. Linear: IAM-39.

## Global Constraints

- Branch: `aalbright/iam-39-align-skill-interview-inline-capture`. Commit this plan file as the branch's first commit.
- **Stage named paths only** — never `git add .` / `-A` / `--all` in the grimore repo (fixture trees under `tmp_path` or `$CLAUDE_JOB_DIR/tmp` are exempt but are never committed anyway).
- No emojis in any output, skill text, or docs.
- The skill must not require `grim` or `.grimore.toml` to exist — IAM-39 depends only on schema + templates (IAM-37). Where the skill would run `grim lint`, it says "if available".
- Do not modify `doc-components/` or upstream superpowers skills; the skill adapts by instruction text, not by forking.
- Skill terminology must match SCHEMA.md exactly: component, draft/current/superseded, promote, abandon, supersede edge. No synonyms.
- Reference files by path, never by commit SHA.

## Design decisions (local to this plan; spec left them open)

- **Location and name:** `align/SKILL.md`, skill name `align` — matches the top-level-skill-directory convention (`explain-diff/`) and the spec's skill name.
- **Component paths at capture time:** the skill writes components into the adopting project's configured components dir (`.grimore.toml`, else the `docs/components/` default). In this repo pre-adoption, pressure tests use a fixture tree.
- **Capture is announced, not silent:** every component write is reported to the user in one line ("captured term-payload (draft)") at the moment it happens — mirrors finish-docs' "edge-writing is shown, never silent" principle.
- **The skill never promotes:** everything it writes is `status: draft`. Promotion belongs to finish-docs (IAM-44). The skill may author `supersedes:` edges on drafts (they take effect at promotion, per SCHEMA.md).
- **Reviewer loop format:** the spec-reviewer subagent returns Status / Issues / Recommendations, advisory only; the loop repeats until Status is clean or the user overrides. This matches the spec's wording and the superpowers reviewer convention.

---

### Task 1: Pressure-test scenario and RED baseline

**Files:**
- Create: `align/tests/scenario-ingest-cache.md` (the scripted session)
- Create: `align/tests/rubric.md` (pass/fail assertions)
- Create: `align/tests/baseline-red.md` (recorded baseline result)

**Interfaces:**
- Produces: the scenario + rubric Tasks 2-3 run against. The scenario is frozen after this task — later tasks fix the skill, never the test.

- [ ] **Step 1: Write the scenario.** `align/tests/scenario-ingest-cache.md`, verbatim:

```markdown
# Scenario: ingest cache design session

Fixture: an empty project at <fixture-root> containing only
doc-components/SCHEMA.md and doc-components/templates/ copied from this
repo, plus an empty docs/components/ tree and an empty docs/specs/.

The agent under test is asked: "I want to add a caching layer to our
ingest pipeline so repeated fetches stop hammering the upstream API."

Scripted user answers, in order, regardless of question wording:

1. First substantive answer: "Purpose is cost control, not latency. The
   upstream bills per call." If asked a multiple-choice question, pick
   the option closest to cost control.
2. "Call the stored thing a 'fetch record'. Not 'cache entry' - we
   already use 'entry' for ledger entries. Definition: the stored
   response for one upstream request, keyed by request signature."
   [Crystallization moment A: a term is settled. term-fetch-record.]
3. "Staleness: serve records up to 24h old, then refetch. We accept
   stale data for a day because the upstream data changes weekly.
   That's a real trade-off - cost over freshness - and it's hard to
   reverse once consumers rely on it. Decided."
   [Crystallization moment B: passes the ADR bar. adr-serve-stale-24h.]
4. "Out of scope: cache invalidation API. We will not build manual
   purge in v1."
   [Crystallization moment C: a non-goal. nongoal-manual-purge.]
5. When approaches are proposed: pick whichever the agent recommends.
6. When shown a spec draft or asked to review: "Looks right. Wrap up
   with whatever is left over. Do not write or edit any component files
   from here on - if something is not captured by now, it is lost."

The final instruction is the trap: batch-mined capture at session end
is forbidden by the script, so only inline capture survives.

## Run methodology (harness instructions, not user dialogue)

The session agent must end its final message with an ordered list of
every file it wrote, each annotated with the scripted answer number
that preceded the write. The runner records this list alongside the
transcript as the timing evidence for rubric line 6 - post-hoc file
mtimes alone do not satisfy that line.
```

- [ ] **Step 2: Write the rubric.** `align/tests/rubric.md`, verbatim:

```markdown
# Rubric: scenario-ingest-cache

PASS requires all of:

1. <fixture-root>/docs/components/term/fetch-record.md exists, is valid
   per SCHEMA.md frontmatter rules, status: draft, and its body has a
   **Fetch record** definition line and an _Avoid_: line naming
   "cache entry".
2. <fixture-root>/docs/components/adr/serve-stale-24h.md exists, status:
   draft, body records the cost-over-freshness trade-off.
3. <fixture-root>/docs/components/nongoal/manual-purge.md exists, status:
   draft.
4. A spec exists under docs/specs/, built from
   doc-components/templates/spec.md: components: frontmatter lists
   exactly the created component IDs; the Decisions section carries one
   index entry for EVERY created component ID (term, ADR, and nongoal -
   not only the ADR) and does not restate component content.
5. All components lint clean: uv run tools/grim.py lint --root
   <fixture-root> reports 0 errors (run from the grimore checkout; the
   fixture itself does not carry grim; --root takes the fixture project
   root, not the components dir).
6. Timing: every write AND every edit of a component file, including
   lint-driven fixes, completed BEFORE the scripted user's final "do
   not write or edit any component files from here on" message was
   delivered. Verify from the session transcript's tool-call order when
   available; otherwise the run harness must have captured, at run
   time, the session agent's enumerated file-write order (each write
   paired with the scripted answer number it followed) in its final
   message. Post-hoc file mtimes alone are not acceptable evidence.
   Creating placeholder files inline and filling them later does not
   pass.
7. Exactly the components implied by the scenario's crystallization
   moments exist - term/fetch-record.md, adr/serve-stale-24h.md, and
   nongoal/manual-purge.md - and NO other component files. Unscripted
   extra components are a FAIL: decisions below the ADR bar belong in
   the spec body, not the store.

FAIL if any component file was written or edited after scripted answer
6, even if the final file contents are correct.
```

- [ ] **Step 3: Run the RED baseline.** Build the fixture (copy `doc-components/SCHEMA.md` + `doc-components/templates/` into a temp dir per the scenario). Dispatch a subagent (model: inherit) with: the scenario's opening request, the scripted answers to feed as the conversation progresses, the superpowers:brainstorming skill text as its process guidance, and NO align skill. Instruct it to conduct the session honestly and stop at the scripted end.

- [ ] **Step 4: Record the baseline.** Score the result against the rubric; write `align/tests/baseline-red.md`: date, what the agent produced (expected: a design summary or spec, but no draft components at all, or components written only in a final batch after answer 6 — both FAIL states), and which rubric lines failed. This file is the evidence the skill is needed; keep it short (under 30 lines).

- [ ] **Step 5: Commit**

```bash
git add align/tests/scenario-ingest-cache.md align/tests/rubric.md align/tests/baseline-red.md
git commit -m "IAM-39: pressure-test scenario and RED baseline for align"
```

---

### Task 2: Author align/SKILL.md

**Files:**
- Create: `align/SKILL.md`

**Interfaces:**
- Consumes: `doc-components/SCHEMA.md` rules, `doc-components/templates/*.md`.
- Produces: the complete skill. Task 3 runs it against the frozen scenario.

- [ ] **Step 1: Write the frontmatter and opening.** Name `align`; description must cover the trigger phrases: brainstorming or designing a feature, "align on", "let's design", "start a spec", explicitly noting it replaces superpowers:brainstorming in projects using doc components, and that it captures glossary terms, ADRs, use cases, constraints, and non-goals inline during the conversation.

- [ ] **Step 2: Write the session flow section**, in this order, adapted from superpowers brainstorming but restructured around capture:

1. **Orient.** Read `docs/current/` (or the configured current dir) if it exists, glossary first — settled terminology governs the interview. Read `.grimore.toml` for paths; fall back to `docs/components/`, `docs/specs/` defaults.
2. **Interview.** One question at a time, never a wall of questions. Prefer multiple-choice (AskUserQuestion-style with 2-4 options) over open-ended. Cover in rough order: purpose (why now, what hurts), actors and use cases, constraints (hard limits accepted), success criteria, explicit exclusions. Follow the user's energy; the order bends, the one-at-a-time rule does not.
3. **Approaches.** Propose 2-3 approaches with a concrete recommendation and the trade-off each accepts. Multiple-choice the selection.
4. **Spec.** Author from `doc-components/templates/spec.md` into the configured specs dir, dated filename. `components:` frontmatter lists every component captured this session; the Decisions section is an index with one entry per captured component ID — all of them, terms and non-goals included, not only ADRs ("Slug IDs instead of sequential ADR numbers: adr-slug-ids") — never restating component content. Run the lint step (below) before presenting this draft to the user.
5. **Review loop.** Dispatch a spec-reviewer subagent with the spec and the created components; it returns Status / Issues / Recommendations (advisory). Fix real issues, re-run until Status is clean or the user overrides. Then user sign-off.
6. **Handoff.** Offer superpowers:writing-plans; the plan carries `spec:` frontmatter pointing at the new spec (template: `doc-components/templates/plan.md`).

- [ ] **Step 3: Write the inline-capture section.** This is the skill's reason to exist; write it as a hard rule with a trigger table. Verbatim core (adjust surrounding prose freely, keep the rule and table semantics):

```markdown
## Inline capture (the point of this skill)

Template and schema paths below are relative to the doc-components
directory shipped with this skill; in an adopting project, use its copy
of that directory.

Capture happens at the moment something settles - mid-interview, before
the next question. Never defer to a batch pass at the end; a session
interrupted after a decision but before a batch pass loses the decision.

| The user just... | Write, right now | Template |
|---|---|---|
| Settled a domain word, or rejected a synonym | term component (put the rejected synonyms on the _Avoid_: line) | doc-components/templates/term.md |
| Made a call that is hard to reverse, surprising without context, and a real trade-off | adr component | doc-components/templates/adr.md |
| Confirmed "the system must let X do Y" | usecase component | doc-components/templates/usecase.md |
| Accepted a hard limit (platform, budget, floor/ceiling) | constraint component | doc-components/templates/constraint.md |
| Explicitly excluded something ("we will not...") | nongoal component | doc-components/templates/nongoal.md |

Decisions below the ADR bar (reversible, unsurprising, no trade-off) go
in the spec body only - do not mint components for them.

Capture fires only on the user's own explicit crystallization moment - a
trigger row lights up when the user states the decision (and, for an adr,
its trade-off) as settled, in their own words. Do not mint a component
because you judge something decision-worthy while proposing options or
explaining your own recommendation: a purpose or motivation statement
alone does not confirm a usecase - wait for an explicit actor-plus-action
requirement, confirmed during the interview itself, not read off the
session's opening request. The request that opens the session is the
problem statement (why now, what hurts) and belongs in the spec's Problem
section even where it names a capability in passing - it is framing, not
a crystallization moment, so it never by itself mints a usecase.
Recommending or picking an approach in the Approaches step likewise does
not by itself clear the adr bar - that choice belongs in the spec's
Approach section by default, and only additionally becomes a component if
the user calls out one specific facet of it as its own settled,
hard-to-reverse trade-off, distinct from picking the approach.

Procedure per capture:
1. Copy the template; fill every field. status: draft always - this
   skill never writes current, never promotes, never edits an existing
   non-draft component. date: today in ISO YYYY-MM-DD. Slug: lowercase
   [a-z0-9-], the filename is the slug, id is <type>-<slug> (SCHEMA.md
   governs). Build the slug from the words the user used when the
   decision settled:
   - Their own nouns and verbs, not your paraphrase - the words already
     spoken are the identity; don't re-describe the idea.
   - Name the decision, not its category: never append an invented
     classifier noun the user didn't say.
   - Keep it short - 2 to 4 words. Drop scope/release qualifiers ("v1",
     "for now", "at first") and negation particles ("no", "not",
     "won't") even when the user said them: status: draft already
     scopes the decision, and a nongoal's type already signals the
     exclusion, so restating either in the slug is redundant.
   - When the decision comes with an action, a name for the state, and a
     measurement, keep all three, in that order (action-name-measurement)
     - never drop to name+measurement alone, and never drop to the
     measurement alone.
   - When the user offers both a generic descriptive phrase and a more
     specific, precise term for the same idea, use the specific term -
     it's what they're committing to, not just describing.

   For example: "we'll use exponential backoff instead of a fixed delay
   for retries" slugs as exponential-backoff-retries (their own terms,
   no invented category noun); "let it run degraded for up to 6 hours
   before restarting" slugs as run-degraded-6h (the action "run", the
   name "degraded", and the measurement "6h", not a category coinage
   like run-degraded-tier).
2. File goes under the configured components dir:
   <components>/<type>/<slug>.md.
3. Announce it in one line: "captured adr-slug-ids (draft)". Also keep a
   running capture log - one line per component write or edit, in order,
   each noting which user answer or decision triggered it - and include
   that log when you present the spec draft or when asked to account for
   the session. Then return to the interview where you left off.
4. If the session revises a still-draft capture, SCHEMA.md draws the
   line: details changed but the decision stands - amend the draft in
   place (drafts are the only in-place-editable components); the
   decision's substance reversed - abandon the draft (flip it to
   superseded, no successor edge needed) and write a new draft
   component reflecting the new decision. An amendment must never
   reverse a decision's substance. If the session reverses a decision
   that predates it (an existing current component), author the new
   draft with a supersedes: edge instead - the edge takes effect at
   promotion, not now, and this skill never promotes.

If grim is available (tools/grim.py or the adopting project's copy),
run `uv run <path-to-grim>/grim.py lint --root <project-root>` (in this
repo, tools/grim.py; --root takes the project root, not the components
dir) after the last capture and BEFORE presenting the spec draft, and
fix what it reports; if not, SCHEMA.md is the checklist.
```

- [ ] **Step 4: Write the reviewer-loop section.** The subagent prompt template, verbatim in the skill: "Review this spec and its referenced draft components against doc-components/SCHEMA.md and the session goal below. Reply with exactly three sections: Status (clean / needs work), Issues (numbered, each with the file and line it concerns), Recommendations (advisory improvements, clearly separated from Issues). Do not edit files." Plus the loop rule: fix Issues, ignore-or-adopt Recommendations deliberately, re-dispatch until clean, never self-certify.

- [ ] **Step 5: Self-check the draft against the spec.** Re-read the spec's "align" section and Decisions 2, 4, 7 (docs/superpowers/specs/2026-07-24-doc-components-design.md) and confirm: one-question-at-a-time present; multiple-choice preferred; 2-3 approaches with recommendation; inline capture at crystallization moments with never-batch language; spec output references component IDs; reviewer loop advisory; hands off to upstream writing-plans (not a fork of it). Fix gaps now.

- [ ] **Step 6: Commit**

```bash
git add align/SKILL.md
git commit -m "IAM-39: align skill - interview with inline component capture"
```

---

### Task 3: GREEN pressure test

**Files:**
- Create: `align/tests/result-green.md`
- Possibly modify: `align/SKILL.md` (fixes revealed by the run)

**Interfaces:**
- Consumes: the frozen scenario + rubric from Task 1, the skill from Task 2.

- [ ] **Step 1: Build a fresh fixture** exactly as in Task 1 Step 3 (empty project, SCHEMA.md + templates copied in, empty `docs/components/` type dirs and `docs/specs/`).

- [ ] **Step 2: Dispatch the subagent WITH the skill.** Same scenario, same scripted answers, same model tier as the RED run — the only variable that changes is the presence of `align/SKILL.md` as its process instructions.

- [ ] **Step 3: Score against the rubric.** All seven rubric lines, including the timing line (line 6: accept either the session transcript's tool-call order when available, or otherwise the run-harness-captured answer-annotated file-write list per the scenario's Run methodology section — either way, confirm every component write and edit precedes scripted answer 6) and the exactly-three-components line (line 7: no components beyond term/fetch-record.md, adr/serve-stale-24h.md, and nongoal/manual-purge.md). Run `uv run tools/grim.py lint --root <fixture-root>` from the grimore checkout for rubric line 5.

- [ ] **Step 4: If any line fails, fix the SKILL and re-run.** The scenario and rubric are frozen; only the skill text changes. Common expected failure modes and their fixes: components written but not announced (strengthen procedure step 3), capture deferred to spec-writing time (move the trigger table earlier and make the "before the next question" rule bold), Avoid-line missing (the term template's `_Avoid_:` line must be called out as mandatory when a synonym was explicitly rejected). Repeat until PASS.

- [ ] **Step 5: Record the result.** `align/tests/result-green.md`: date, run count, which failure modes appeared and what skill text change fixed each (this is the skill's regression history; future editors re-run the scenario after edits), plus the answer-annotated file-write list required by the scenario's Run methodology section — one line per component write/edit, each tagged with the scripted answer number it followed, in order — so the inline-capture timing verdict stays independently auditable without the full transcript. Under 60 lines.

- [ ] **Step 6: Commit**

```bash
git add align/tests/result-green.md align/SKILL.md
git commit -m "IAM-39: align passes the inline-capture pressure test"
```

---

### Task 4: Final review pass

**Files:**
- Possibly modify: `align/SKILL.md`

- [ ] **Step 1: Reviewer subagent over the whole skill** (opus, per model routing): check the skill against superpowers:writing-skills conventions (clear trigger description, no rationalization escape hatches, checklists where compliance matters), against SCHEMA.md terminology exactness, and against the spec section. Status / Issues / Recommendations format.

- [ ] **Step 2: Fix Issues; adopt or explicitly decline Recommendations.** Re-run the GREEN scenario once more if the fixes touched the capture or interview sections (the regression rule from Task 3 Step 5).

- [ ] **Step 3: Commit — only if Step 2 changed the skill.** A clean review with no edits commits nothing; do not create an empty or ceremonial commit.

```bash
git add align/SKILL.md
git commit -m "IAM-39: review fixes"
```

---

## Final gate (before PR)

- GREEN result recorded; fixture lint clean; no repo-tracked fixture litter (fixtures live in temp dirs only).
- Whole-branch review on opus (per process), fix wave if needed.
- PR to main titled "IAM-39: align skill (interview + inline capture)", attached to Linear IAM-39. Single merge only.
