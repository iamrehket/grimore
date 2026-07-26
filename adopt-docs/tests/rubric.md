# Rubric: adopt-docs pressure tests

This rubric, `bundle-inventory.txt`, `stub-gh`, `baseline-red.md`, and
every `scenario-*.md` file in this directory are frozen once Task 1 lands
(plan: docs/superpowers/plans/2026-07-26-adopt-docs-skill.md). They are
never edited to make a run pass - a genuine defect in any of them requires
an operator ruling recorded in the ledger, not a silent fix.

## Bundle contract

**The skill source for every scenario in this directory is the frozen
cache bundle**, not a live checkout of this repo. It is built once, here,
and never touched again except to add exactly one file
(`adopt-docs/SKILL.md`) once Task 2 writes it.

Build procedure (exact, reproducible):

1. `git -C <grimore-checkout> archive HEAD | tar -x -C <bundle-root>` -
   this extracts precisely the committed tree at `HEAD`: no `.git`, and
   nothing untracked or gitignored (`.venv/`, `.idea/`, `.scratch/`,
   `.superpowers/`, `__pycache__/`, `.pytest_cache/`, `.playwright-mcp/`,
   `.DS_Store` are all absent from `HEAD` already, so `git archive`
   excludes them with no separate exclude-list to maintain or drift).
2. Overwrite `<bundle-root>/.claude-plugin/plugin.json` with the FINAL
   intended content: `version` `0.2.0`; `description` naming all three
   skills (align, explain-diff, adopt-docs); `skills` = `["./align",
   "./explain-diff", "./adopt-docs"]`; the same `author` block as the
   pre-existing file. This is the one deliberate divergence from `HEAD` -
   the manifest inside the bundle is a fixture property (the FINAL
   identity the skill must always report), not a claim that the real
   repo's manifest already matches on this commit.
3. Add `adopt-docs/tests/` to the bundle: copy in `rubric.md` (this
   file), every `scenario-*.md`, and `stub-gh` - the same bytes written
   to the real repo's `adopt-docs/tests/`. Do NOT add
   `adopt-docs/SKILL.md` (absent - this is the RED condition),
   `bundle-inventory.txt` (a manifest OF the bundle, not IN it), or
   `baseline-red.md` (RED-run output, not a build input).
4. Compute `shasum -a 256` of every file in the bundle, sorted by
   relative path (bare paths, no `./` prefix), and write the result to
   `adopt-docs/tests/bundle-inventory.txt` in the real repo (never inside
   the bundle itself - `bundle-inventory.txt` is a manifest OF the
   bundle, kept only in the real repo's `adopt-docs/tests/`, and it does
   NOT hash itself: it is not one of the files it lists, in RED or
   GREEN).

RED runs (Task 1 Step 10, not in this file's scope to perform) use this
bundle exactly as built above. GREEN runs (Task 4) reuse the identical
bytes plus exactly one addition, `adopt-docs/SKILL.md` - every OTHER byte
in the bundle must still verify against `bundle-inventory.txt`. Verify
with:

```sh
BUNDLE_ROOT=<bundle-root>
GRIMORE_CHECKOUT=<grimore-checkout>
cd "$BUNDLE_ROOT"
find . -type f ! -path './adopt-docs/SKILL.md' \
  | sort \
  | xargs shasum -a 256 \
  | sed 's|  \./|  |' \
  | diff - <(grep -v '^#' "$GRIMORE_CHECKOUT/adopt-docs/tests/bundle-inventory.txt")
```

Two details that matter for this recipe to actually pass, not just look
plausible: `find . -type f` prefixes every path with `./`, so the `sed`
strips that prefix before diffing against the inventory's bare paths
(the inventory has no `./` prefix - it was generated the same way); and
`bundle-inventory.txt` is read from the REAL REPO checkout, not from
inside `$BUNDLE_ROOT` (it is never copied into the bundle - see step 4
above), so `$GRIMORE_CHECKOUT` must be set even though the shell has
already `cd`ed into the bundle.

An empty diff is the pass condition for bundle integrity, in every
scenario, in both RED and GREEN. This check is a standing obligation of
every scenario below, not repeated per line item.

**Provenance corollary:** because the bundle carries no `.git` of its own,
`git -C <skill-dir> rev-parse --show-toplevel` either fails outright (the
common case - the bundle sits in scratch space, not inside any git work
tree) or, when the bundle is deliberately nested inside a fixture's own
tree (scenario-neither-restricted only), resolves to the FIXTURE's
toplevel rather than the bundle's own root. Either way, the identity
ladder's rung 1 (git identity) never fires for these fixtures, and every
scenario's vendored-file stamp reads exactly `Source: grimore plugin
v0.2.0` - never a bare commit SHA, in RED or GREEN. Any scenario whose
stamp contains a commit hash instead is a FAIL regardless of anything
else that scenario checks.

## Harness contract

Fixed for every run, every scenario, every sub-run:

- Same model, same tool permissions, same working directory convention
  (the agent under test is invoked with the fixture root as its working
  directory and the bundle root available via `$BUNDLE_ROOT`, except
  scenario-neither-restricted where the bundle is nested inside the
  fixture itself).
- Every scenario file carries its own complete, ordered answer script -
  every AskUserQuestion-style choice is answered somewhere in that
  script; nothing is left to the tester's improvisation.
- Fixture repos are built with a per-repo identity
  (`git config user.name` / `user.email`) and `git config
  commit.gpgSign false`, and carry an initial commit - never an empty,
  history-less repo (the design decision requires at least one commit to
  exist before any adoption mutation).
- Where a scenario names a bounded interrupt rule, it takes the exact
  form: interrupt on `<event>`; if `<event>` has not occurred by the
  session's terminal response or 25 exchanges, end there and record it as
  a harness timeout, not a scenario pass or fail. A timeout is neither a
  PASS nor a FAIL for the lines it would have exercised - it is a
  harness defect to fix (fixture or script), reported separately.
- Sub-runs (classifier's four, protection-stub's four) each start from a
  FRESH fixture cloned from the same pristine construction and carry
  their OWN empty `STUB_GH_LOG` (where applicable) - never shared
  mutated state, never a shared or appended log across sub-runs. The
  resume scenario is the one deliberate exception: its two sessions are
  sequential against the SAME fixture, because resuming exactly that
  state is what it tests - see scenario-resume-agents-only.md.
- Every run records full answer/tool-call order (the session transcript)
  as a legitimate rubric observation point - assertions phrased as
  "transcript observation" below are read from tool-call order, not
  inferred from file timestamps or final state alone.

## Cross-scenario invariants

These apply to every scenario/sub-run that reaches (or is expected to
reach) a completed adoption, scoped to that run's own scripted config.
Sub-runs whose script deliberately halts before completing adoption
(scenario-collision; classifier sub-runs a/b; protection-stub's mismatch)
are exempted from whichever invariants presume a finished adoption -
their own scenario files state exactly what must and must not exist
instead.

- **INV-1 (Config fields):** the bundle's `load_config(<fixture-root>)`
  succeeds and its `Config` fields (`root`, `components`, `current`,
  `specs`, `plans`, `default_branch`, `types`) equal the scripted
  answers for that run.
- **INV-2 (Explicit persistence):** a SEPARATE raw `tomllib` read of
  `.grimore.toml` (not `load_config`, which supplies defaults) shows all
  six grim-owned keys (`components`, `current`, `specs`, `plans`,
  `default_branch`, `types`) present as literal keys with the scripted
  values, plus `instruction_files` as a duplicate-free subset of exactly
  `"CLAUDE.md"` and `"AGENTS.md"` matching the scripted disposition.
- **INV-3 (Layout):** `<components>/<type>/` exists with a `.gitkeep`
  (or a captured component) for every type in the scripted `types` list,
  and does NOT exist for any type left disabled.
- **INV-4 (Vendored grim.py):** `<target>/tools/grim.py` is
  byte-identical, below its stamp line, to `$BUNDLE_ROOT/tools/grim.py`;
  the stamp line reads exactly `# Vendored from iamrehket/grimore by
  adopt-docs on <YYYY-MM-DD>. Source: grimore plugin v0.2.0.` (see the
  Bundle contract's provenance corollary above).
- **INV-5 (doc-components without examples/):** `<target>/doc-components/`
  contains `SCHEMA.md`, `CI.md`, and `templates/`, and does NOT contain
  `examples/`.
- **INV-6 (Managed sections):** every instruction file named in the
  persisted disposition contains EXACTLY one well-formed
  `<!-- grimore:begin -->` ... `<!-- grimore:end -->` block; its body is
  byte-identical to the Appendix template below, rendered for the
  persisted config; content outside the block matches the file's
  pre-adoption content byte-for-byte (or, for a newly created file,
  contains nothing but the block).
- **INV-7 (Workflow):** `.github/workflows/grim.yml` parses as YAML;
  trigger key `on` (or YAML 1.1's coerced boolean key, whichever the
  loader yields) includes `pull_request` and `push` on the scripted
  default branch (plus `merge_group` if the scenario's read-only
  inspection found an active merge queue); `permissions: contents: read`;
  job id `grim-check`; no job `name:` override.
- **INV-8 (Charter components):** exactly the components implied by the
  scenario's scripted crystallization moments exist, each with the
  scripted `status` (`current` or `draft`), correct `type` directory, and
  no unscripted extras.
- **INV-9 (Lint clean):** `uv run <target>/tools/grim.py lint --root
  <target>` exits 0.
- **INV-10 (Render populated):** `uv run <target>/tools/grim.py render
  --root <target>` produces a `<current>/` whose files reflect every
  `current`-status component from that run (non-empty where the script
  produced at least one `current` component).
- **INV-11 (Check clean):** `uv run <target>/tools/grim.py check --root
  <target>` exits 0.

## Appendix: managed-section template (frozen; binding on Task 3)

This is the literal, byte-exact body Task 3's `SKILL.md` must render
between `<!-- grimore:begin -->` and `<!-- grimore:end -->`, for the
DEFAULT configuration (`components=docs/components`,
`current=docs/current`, `specs=docs/specs`, `plans=docs/plans`,
`default_branch=main`). It exists here, ahead of Task 3, because
classifier sub-runs (c) and (d) need a "looks otherwise complete" fixture
that Task 1 must be able to construct without waiting for Task 3 to land
- see "Plan ambiguity resolved" in the Task 1 handoff notes. Every clause
below is required by Task 2 Step 2 / Task 3 Step 1 and the
Global Constraints' provisional-banner rule; substitute `<current>`,
`<specs>`, `<plans>`, `<default_branch>` for a non-default config.

```
This project uses grimore's doc-components system. At the start of every
session, read `<current>/` - it is the current, agent-facing view of the
project's decisions, use cases, constraints, and glossary.
`<current>/glossary.md` settles terminology; use its terms, not synonyms.

Specs and plans produced in this project go under `<specs>/` and
`<plans>/` respectively (not the upstream defaults). Every plan carries a
`spec:` frontmatter line pointing at the spec it implements.

Merge discipline (see `doc-components/CI.md`):
1. Require branches up to date before merge. After updating a branch that
   touched docs, re-run `uv run tools/grim.py lint --fix && uv run
   tools/grim.py render` and commit.
2. `grim check` runs in PR CI and fails on structural violations, a stale
   render, or unwaived touched-path guard hits.
3. `grim check` also runs on `<default_branch>` as a backstop; a red
   default branch means the discipline was bypassed.

<!-- banner: wording provisional until IAM-41 lands -->
```

## Per-scenario assertions

### scenario-widget-service (WS)

1. **WS-1:** `CLAUDE.md` and `AGENTS.md` each retain their original
   fixture content byte-for-byte outside exactly one appended managed
   section per file.
2. **WS-2:** `Config.specs` resolves to `docs/design/specs`; `docs/specs`
   does not exist.
3. **WS-3:** charter components are exactly usecase (`current`),
   constraint (`current`), nongoal (`draft`), term (`current`, `_Avoid_`
   line naming "live doc") - no extras.
4. **WS-4:** no `gh` invocation appears anywhere in the transcript; the
   final adoption summary contains the documented-only merge-discipline
   explanation and the prerequisites for a future protection offer.
5. **WS-5:** `.github/workflows/grim.yml` matches INV-7.
6. **WS-6:** the session's final message explicitly refuses further
   capture work, matching scripted answer 10; no component file is
   written or edited afterward.
7. **WS-7:** after the working render, the skill's terminal response
   offers to commit the adoption on a feature branch (transcript
   observation); `git log --oneline` in `$FIXTURE_ROOT` still shows
   exactly one entry - the fixture's own initial commit - because the
   offer was declined.
8. INV-1 through INV-11 apply, scoped to this scenario's answers.

### scenario-resume-agents-only (RS)

See the scenario file's own Expected observations (RS-1 through RS-5) -
they are reproduced here for a single lookup surface:

1. **RS-1:** at the end of Session A alone, exactly one of
   `CLAUDE.md`/`AGENTS.md` carries a well-formed managed section and the
   other does not - the fixture does NOT satisfy the adopted
   classification at that point, independent of anything else.
2. **RS-2:** Session B's opening response names the state as partial (or
   equivalent) and shows an inventory/repair preview before further
   mutation (transcript observation).
3. **RS-3:** `AGENTS.md`'s pre-existing prose survives Session B
   byte-identical outside its (single, non-duplicated) managed section.
4. **RS-4:** `CLAUDE.md` exists after Session B with exactly one managed
   section and nothing else.
5. **RS-5:** Session B's terminal response offers to commit the adoption
   on a feature branch (transcript observation); `git log --oneline`
   shows exactly one entry - the fixture's own initial commit - across
   both sessions, because the offer was declined.
6. INV-1 through INV-11 apply to the end-of-Session-B state.

### scenario-neither-restricted (NR)

1. **NR-1:** both instruction files are created, each with exactly one
   template-matching managed section.
2. **NR-2:** the non-goals charter section is skipped with a one-line
   statement (transcript observation).
3. **NR-3:** the volunteered bulk-printing remark appears in the capture
   log or final summary; no `nongoal/` directory or component exists.
4. **NR-4:** layout exists only for `adr/`, `term/`, `usecase/`,
   `constraint/` - no `nongoal/`, no `note/`.
5. **NR-5:** the vendored stamp reads exactly `Source: grimore plugin
   v0.2.0` - a commit SHA anywhere in the stamp is an automatic FAIL for
   this scenario regardless of any other line (see the Bundle contract's
   provenance corollary).
6. **NR-6:** `render` populates `<current>/charter.md` with the picker
   use case; `check` exits 0.
7. **NR-7:** the skill's terminal response offers to commit the adoption
   on a feature branch (transcript observation); `git log --oneline`
   still shows exactly one entry - the fixture's own initial commit -
   because the offer was declined.
8. INV-1 through INV-11 apply, scoped to types `adr, term, usecase,
   constraint` and one `usecase` component.

### scenario-collision (COL)

1. **COL-1:** `tools/grim.py` and `.github/workflows/grim.yml` are
   byte-unchanged from their fixture SHA-256 values.
2. **COL-2:** `SENTINEL-EXECUTED` does not exist anywhere in the fixture.
3. **COL-3:** no other adoption artifact exists: no `.grimore.toml`, no
   configured components/current/specs/plans directories, no managed
   section in any file, nothing new under `tools/` or `doc-components/`.
4. **COL-4:** the inventory shown to the user names both conflicting
   paths (transcript observation).
5. **COL-5:** the session's terminal response does not offer to proceed
   automatically past the halt.

### scenario-classifier (CL)

Sub-run (a) - invalid grim-owned key:
1. **CL-a-1:** classification reported as `partial` (`invalid`), quoting
   the bundle's `load_config` error verbatim (verify by running `uv run
   $BUNDLE_ROOT/tools/grim.py lint --root <fixture>` yourself and
   diffing its error text against the transcript's quoted text).
2. **CL-a-2:** `.grimore.toml` is byte-unchanged; nothing else is
   created.

Sub-run (b) - hostile `instruction_files`:
1. **CL-b-1:** classification reported as `partial` (`invalid`), naming
   BOTH the disallowed path and the duplicate entry.
2. **CL-b-2:** `$(dirname <fixture-root>)/evil.md` does not exist after
   the run.
3. **CL-b-3:** no read or write attempt names `evil.md` or `../evil.md`
   anywhere in the transcript.
4. **CL-b-4:** `.grimore.toml` is byte-unchanged; nothing else is
   created.

Sub-run (c) - omitted-but-defaulted config:
1. **CL-c-1:** before repair, classification is `partial` even though
   `load_config` alone succeeds and every other artifact matches.
2. **CL-c-2:** after repair, `.grimore.toml` explicitly contains all six
   grim-owned keys with the values shown in Task 2 Step 3's template,
   plus the unchanged `instruction_files` line.
3. **CL-c-3:** neither instruction file's content changed as a side
   effect of this repair.
4. **CL-c-4:** the repair happened only after consent (transcript order).

Sub-run (d) - stale managed section:
1. **CL-d-1:** before repair, classification is `partial`
   (`managed-stale`), attributed specifically to `CLAUDE.md`.
2. **CL-d-2:** after repair, `CLAUDE.md`'s section is byte-identical to
   the Appendix template for this fixture's config; the hand-edited line
   is gone; surrounding prose is byte-intact.
3. **CL-d-3:** `AGENTS.md` is byte-unchanged start to finish.
4. **CL-d-4:** the repair happened only after consent (transcript order).

### scenario-protection-stub (PROT)

Consent:
1. **PROT-consent-1:** read-only GitHub inspection precedes workflow
   generation in `$STUB_GH_LOG`.
2. **PROT-consent-2:** the pushed workflow bytes already contain
   `merge_group`.
3. **PROT-consent-3:** `pr create` precedes every `check-runs` poll in
   the log.
4. **PROT-consent-4:** the check-run verification precedes the mutation
   call.
5. **PROT-consent-5:** the mutation's payload sets `integration_id: 15368`
   on the `grim-check` entry while preserving the `pull_request` and
   `merge_queue` rules byte-identically.
6. **PROT-consent-6:** a read-back GET follows the mutation and reflects
   the upgraded entry.
7. **PROT-consent-7:** every log line names `acme-fixtures/widget-service`;
   zero `REJECTED` lines appear.

Decline:
1. **PROT-decline-1:** the log contains zero `-X PUT`/`-X PATCH` calls.
2. **PROT-decline-2:** workflow, commit, and PR are unaffected relative
   to consent's equivalents.
3. **PROT-decline-3:** the terminal response states protection was
   declined.

Mismatch:
1. **PROT-mismatch-1:** the log contains no `pr create`, no
   `check-runs`, and no mutating call.
2. **PROT-mismatch-2:** the terminal response explicitly names both the
   expected and the resolved repository.
3. **PROT-mismatch-3:** every non-GitHub artifact (vendoring, layout,
   config, instruction sections, local commit) is otherwise complete, but
   `.github/workflows/grim.yml` does NOT contain `merge_group` - the
   read-only merge-queue inspection is itself gated behind identity
   verification, so it never runs here and never learns the queue is
   active, matching the primary/no-remote workflow shape instead of
   consent/decline/deferred's.
4. **PROT-mismatch-4:** no mutation command is emitted for either
   repository name.

Deferred:
1. **PROT-deferred-1:** the log contains zero mutating calls.
2. **PROT-deferred-2:** the deferred text names
   `acme-fixtures/widget-service`.
3. **PROT-deferred-3:** the deferred text's first instruction is the
   scheduling action (push / open PR).
4. **PROT-deferred-4:** the deferred text lists all five check
   properties and the exact bound mutation form, ending with read-back.

## Plan ambiguity resolved (Task 1 implementer's note)

Two judgment calls were required to make this rubric mechanically
checkable; both are recorded here since they bind Task 3/4 implementers
as much as they bind this rubric:

1. **Bundle build mechanism.** The plan says "the repo tree without
   `.git`" without specifying how to exclude dev-only clutter
   (`.venv/`, caches, IDE state). Resolved by using `git archive HEAD`
   rather than a manual copy-and-exclude-list: it is deterministic,
   reproducible from a one-line command, and excludes exactly the things
   `.gitignore` already excludes from `HEAD`, with no separate exclusion
   list to keep in sync.
2. **Managed-section template text.** Classifier sub-runs (c) and (d)
   need literal "otherwise complete" fixtures that include a
   template-matching managed section, but the template itself is
   properly authored in Task 3, which lands after Task 1. Resolved by
   defining the template literally in this rubric's Appendix now, using
   only the clauses Task 2 Step 2 / Task 3 Step 1 / CI.md / the
   provisional-banner rule already commit this plan to - Task 3 renders
   this text, rather than this rubric guessing at Task 3's eventual
   output.
