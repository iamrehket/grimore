---
spec: docs/specs/2026-07-27-cross-compatible-plugin.md
---

<!-- grim:status -->
> **Not yet implemented.**
<!-- /grim:status -->

# Cross-Compatible Plugin (IAM-56) Implementation Plan

> **For implementation workers:** Execute this plan task by task. Keep the
> tests red before each behavioral change, use named paths when staging, and
> do not turn the advisory native-host smoke checks into a claimed CI gate.

**Goal:** Make the repository-root Grimore plugin installable in both Claude
Code and Codex with one release identity, deterministic manifest and
provenance checks, host-neutral skill instructions, and an operator guide for
both plugin managers.

**Architecture:** Keep the existing repository-root payload and Claude Code
marketplace. Add a Codex-native manifest as a parity-checked mirror while the
Claude Code manifest remains authoritative. Extend the existing version
checker to understand both manifests and update their versions together. Move
adoption provenance resolution into one read-only standard-library helper.
Keep all other portability work in skill instructions rather than creating a
host-abstraction layer.

**Tech stack:** JSON manifests; Markdown skills and operator documentation;
Python 3.11 standard library for the version and provenance helpers; Git CLI;
pytest and the repository's existing PyYAML development dependency for tests.
The provenance helper itself has no PyYAML or other third-party dependency.

**References:**

- Spec: `docs/specs/2026-07-27-cross-compatible-plugin.md`
- Components: `adr-dual-plugin-manifests`,
  `adr-stdlib-provenance-resolver`,
  `nongoal-host-abstraction-framework`
- Tracking: Linear issue IAM-56
- Mentat context: `grimore.roadmap.plugin-marketplace` records the live
  marketplace state; IAM-56 does not yet have a dedicated Mentat head
- Verified native baselines: Claude Code `2.1.220`, Codex CLI `0.145.0`,
  checked 2026-07-27

## Global constraints

- Do not move `align/`, `explain-diff/`, or `adopt-docs/`.
- Do not create a generated plugin subtree or a second marketplace catalog.
- `.claude-plugin/plugin.json` is authoritative for shared metadata.
  `.codex-plugin/plugin.json` mirrors `name`, `version`, `description`,
  `author`, and the ordered `skills` list.
- Do not add apps, MCP servers, hooks, assets, or presentation metadata merely
  to fill optional Codex manifest fields.
- The provenance helper may import only the Python standard library and may
  invoke only Git. It performs no writes, package installation, project
  environment discovery, or network requests.
- The frozen adopt-docs pressure runs are retired as executable acceptance
  evidence. Preserve their inputs, inventory, and recorded results unchanged
  as history for the earlier Claude-only release. Do not run the updated
  `SKILL.md` against that old bundle: it cannot contain the new helper by
  construction. New provenance behavior uses ordinary temporary fixtures.
- Preserve each skill's frontmatter name and trigger intent. Portability edits
  may replace host-specific vocabulary but must not broaden when the skill
  activates.
- Native host smoke checks are recommended release evidence, not an enforced
  acceptance gate. CI gates only deterministic pytest and grim checks.
- Do not use a Codex-only SemVer build suffix as a cachebuster. It would make
  the native manifests disagree and bypass the shared release identity.
- No emoji in code, tests, skills, documentation, or command output.
- Stage named paths only in this repository. Broad staging is allowed only
  inside throwaway test repositories.

## Contract-to-enforcement map

| Contract | Authoritative source | Deterministic enforcement |
| --- | --- | --- |
| Shared plugin metadata | Claude Code manifest | Marketplace tests and version checker |
| Release version | Claude Code merge-base manifest | Version-checker tests and PR workflow |
| Codex package shape | Codex manifest | Marketplace tests; advisory native install |
| Adoption provenance | Provenance helper | Isolated subprocess tests |
| Host-neutral workflow wording | Shipped skill files | Static portability audit |
| Operator lifecycle | Plugin host guide | Documentation contract tests |

---

### Task 0: Preserve the signed-off design before implementation

**Files:**

- Add: `docs/specs/2026-07-27-cross-compatible-plugin.md`
- Add: `docs/plans/2026-07-27-cross-compatible-plugin.md`
- Add: `docs/components/adr/dual-plugin-manifests.md`
- Add: `docs/components/adr/stdlib-provenance-resolver.md`
- Add: `docs/components/nongoal/host-abstraction-framework.md`

- [ ] **Step 1: Establish the feature branch.** Confirm the current branch
  before committing:

  ```bash
  git branch --show-current
  ```

  The expected branch is
  `aalbright/iam-56-cross-compatible-plugin-spec-plan`. If still on `main`,
  create or switch to that feature branch first. If an unrelated branch is
  active, stop and resolve the branch target rather than committing across
  scopes. Never commit this work directly to protected `main`.

- [ ] **Step 2: Run the documentation authoring checks.**

  ```bash
  uv run tools/grim.py lint --fix
  uv run tools/grim.py render
  git diff --check
  ```

- [ ] **Step 3: Commit only the signed-off working layer and draft
  components.** Do not stage `.scratch/` or unrelated handoff files.

  ```bash
  git add \
    docs/specs/2026-07-27-cross-compatible-plugin.md \
    docs/plans/2026-07-27-cross-compatible-plugin.md \
    docs/components/adr/dual-plugin-manifests.md \
    docs/components/adr/stdlib-provenance-resolver.md \
    docs/components/nongoal/host-abstraction-framework.md
  git commit -m "docs(plugin): specify cross-host plugin compatibility"
  ```

---

### Task 1: Add the Codex manifest and executable parity contract

**Files:**

- Create: `.codex-plugin/plugin.json`
- Modify: `tests/test_marketplace.py`

**Interfaces:**

- `CLAUDE_PLUGIN` and `CODEX_PLUGIN` identify the two native manifests.
- `SHARED_FIELDS = ("name", "version", "description", "author", "skills")`
  defines the ordered parity surface.
- `declared_skill_dirs()` continues to read the authoritative Claude Code
  manifest after parity has been established.

- [ ] **Step 1: Write failing manifest tests.** Refactor
  `tests/test_marketplace.py` to load both native manifests and add assertions
  for:

  - both files exist and contain JSON objects;
  - every shared field is present in both;
  - the five shared values are equal, including exact author structure and
    skill ordering;
  - both names match the existing marketplace plugin name;
  - each skill path is plugin-root-relative, exists, has valid frontmatter,
    and the root-level skill inventory is complete.

  Keep host-specific Codex presentation fields outside `SHARED_FIELDS` so a
  later UI enhancement does not accidentally make them Claude requirements.

- [ ] **Step 2: Confirm RED.**

  ```bash
  uv run pytest tests/test_marketplace.py -q
  ```

  Expected failure: `.codex-plugin/plugin.json` is absent.

- [ ] **Step 3: Add the Codex-native manifest.** Create
  `.codex-plugin/plugin.json` with the current authoritative values:
  `grimore`, the current authoritative version, the existing three-skill
  description, Adam Albright's author object, and the ordered paths `./align`,
  `./explain-diff`, `./adopt-docs`. Do not add optional fields or change the
  existing marketplace schema.

- [ ] **Step 4: Run the focused tests.**

  ```bash
  uv run pytest tests/test_marketplace.py -q
  ```

- [ ] **Step 5: Commit the manifest seam.**

  ```bash
  git add .codex-plugin/plugin.json tests/test_marketplace.py
  git commit -m "feat(plugin): add the Codex native manifest"
  ```

- [ ] **Step 6: Immediately restore a green version gate.** Do not push the
  transient manifest commit by itself. Run the current authoritative checker
  as soon as the consumer-facing commit exists:

  ```bash
  PR_TITLE="feat: support Claude Code and Codex plugin hosts" \
    BASE_REF=main \
    python3 .github/scripts/check_version_bump.py --apply
  ```

  At this point Task 2's dual writer does not exist yet, so the current
  checker updates only the authoritative Claude Code manifest. Copy that exact
  computed version into the new Codex manifest without independently
  calculating or incrementing it. This is the one bootstrap synchronization;
  after Task 2, apply mode owns both writes.

  Run `uv run pytest tests/test_marketplace.py -q` and the checker in normal
  mode, then commit both manifest versions before any push:

  ```bash
  git add .claude-plugin/plugin.json .codex-plugin/plugin.json
  git commit -m "feat(plugin): apply the shared release version"
  ```

---

### Task 2: Make version validation dual-manifest and rollback-protected

**Files:**

- Modify: `.github/scripts/check_version_bump.py`
- Modify: `tests/test_version_bump.py`

**Interfaces:**

- `CLAUDE_MANIFEST` is the merge-base and release authority.
- `CODEX_MANIFEST` is the required head mirror.
- `load_manifest(path)` returns raw text plus parsed JSON and fails with the
  path in its diagnostic.
- `shared_drift(claude, codex, include_version)` reports shared fields that
  differ in deterministic field order.
- `write_versions_atomically(updates)` stages both rewritten files and either
  replaces both or restores both original byte sequences before failing.

- [ ] **Step 1: Upgrade the fixture helpers.** Change the default fixture
  repository to create matching Claude Code and Codex manifests at the base.
  Replace the one-host `set_version()` and `version_of()` helpers with
  host-aware helpers, while keeping all existing Conventional Commit
  scenarios intact.

  Add an explicit `codex_at_base=False` fixture mode for the one bootstrap
  case. Do not make all legacy tests bootstrap cases.

- [ ] **Step 2: Write failing parity and bootstrap tests.** Add subprocess
  tests proving:

  - normal check rejects name, description, author, skill-order, and version
    drift;
  - `--print` also rejects all shared-field drift;
  - `--apply` rejects every non-version drift before writing;
  - `--apply` accepts version-only drift and writes the computed target to
    both manifests;
  - a base with no Codex manifest computes from the base Claude Code version
    and succeeds when the head contains a matching pair;
  - after the base contains both manifests, either head manifest being absent
    fails;
  - an exempt-only change still fails manifest drift;
  - `Version-Waive` remains the first short circuit, so a waived range neither
    compares nor writes either manifest;
  - apply remains idempotent and preserves each file's unrelated formatting.

- [ ] **Step 3: Write the failing rollback test.** Load the checker module
  through `importlib`, call the write seam directly, and monkeypatch the second
  replace operation to raise `OSError`. Assert both files contain their exact
  original bytes afterward and the operation fails loudly. Keep all
  end-to-end behavior tests subprocess-driven.

- [ ] **Step 4: Confirm RED.**

  ```bash
  uv run pytest tests/test_version_bump.py -q
  ```

- [ ] **Step 5: Implement manifest loading and parity.** In
  `.github/scripts/check_version_bump.py`:

  1. retain commit collection and `Version-Waive` handling first;
  2. load both head manifests;
  3. reject all shared drift in check and print modes;
  4. reject non-version drift in apply mode;
  5. only then evaluate exempt paths and Conventional Commit levels.

  JSON errors, missing files, missing fields, and wrong top-level types must be
  path-specific failures rather than tracebacks.

- [ ] **Step 6: Implement authoritative merge-base behavior.** Always read
  the base version from `.claude-plugin/plugin.json`. Discriminate Codex
  manifest absence with:

  ```bash
  git ls-tree --full-tree <merge-base> -- .codex-plugin/plugin.json
  ```

  Interpret exit zero plus empty stdout as absent and therefore bootstrap
  mode; exit zero plus non-empty stdout as present; and any nonzero exit as a
  fatal Git or revision failure. Only use `git show` to read the base Codex
  manifest after `ls-tree` proves it exists. Then enforce:

  - absent at base means bootstrap mode;
  - present at base means both head manifests are mandatory;
  - the head pair must exist and satisfy the mode-specific parity rule in
    either case.

- [ ] **Step 7: Implement rollback-protected apply.** Compute both rewritten
  byte sequences before mutation. Stage temporary files next to their
  destinations, replace in a fixed order, and on any failure restore both
  captured originals. Clean staged files in `finally`. If restoration itself
  fails, report the original write failure and every restoration failure.

- [ ] **Step 8: Run the focused suite and preserve legacy behavior.**

  ```bash
  uv run pytest tests/test_version_bump.py -q
  ```

  Every pre-existing version test must still pass with the default dual-host
  fixture.

- [ ] **Step 9: Commit the release gate.**

  ```bash
  git add .github/scripts/check_version_bump.py tests/test_version_bump.py
  git commit -m "feat(plugin): enforce dual-manifest release parity"
  ```

---

### Task 3: Build and wire the dependency-free provenance resolver

**Files:**

- Create: `adopt-docs/scripts/resolve_provenance.py`
- Create: `tests/test_adopt_docs.py`
- Modify: `adopt-docs/SKILL.md`

**Command interface:**

```text
uv run --no-project python -I -S \
  <skill-dir>/scripts/resolve_provenance.py \
  --skill-dir <skill-dir> \
  --target <adopting-repository>
```

- Successful stdout is exactly one identity line: a verified Git commit,
  `grimore plugin v<version>`, or `unknown`.
- Metadata warnings go to stderr.
- `unknown` is a successful safe fallback with exit code zero.
- Invalid arguments or an unexpected internal execution failure are nonzero.
- The helper is read-only.

- [ ] **Step 1: Create the isolated test driver.** In
  `tests/test_adopt_docs.py`, invoke the resolver with
  `sys.executable -I -S`, not through the repository's pytest environment.
  Capture stdout, stderr, and the exit code. Build all source and target
  layouts under `tmp_path`.

- [ ] **Step 2: Write failing provenance cases.** Cover:

  - a standalone Grimore Git source with a different target root returns its
    exact source commit;
  - a Git-less bundle nested inside the target refuses the target's commit and
    uses its manifest version instead;
  - a valid older Claude-only bundle returns its version;
  - matching native names and versions return the authoritative version;
  - mismatched native names warn and return `unknown`;
  - mismatched native versions warn and return `unknown`;
  - malformed Claude JSON, malformed Codex JSON, a missing authoritative
    manifest, missing fields, and non-object JSON warn and return `unknown`;
  - unexpected extra Codex-only fields do not affect the result;
  - stdout always contains one identity line and warnings never contaminate
    it;
  - invalid CLI invocation is nonzero.

- [ ] **Step 3: Confirm RED.**

  ```bash
  uv run pytest tests/test_adopt_docs.py -q
  ```

- [ ] **Step 4: Implement the helper using only stdlib.** Use `argparse`,
  `json`, `pathlib`, `subprocess`, and `sys`. The Git rung must verify all of:

  1. the skill directory resolves to a Git top level;
  2. that top level's authoritative manifest identifies `grimore`;
  3. that top level differs from the adopting repository's resolved root;
  4. the commit resolves at that verified source root.

  If that rung does not fire, load the authoritative manifest version. A
  missing Codex manifest is the supported legacy case. If the Codex manifest
  exists, require matching `grimore` names and matching non-empty version
  strings. Any unusable metadata emits a concise warning and resolves
  `unknown`.

- [ ] **Step 5: Wire `adopt-docs` to the helper.** Replace the detailed
  agent-executed provenance algorithm in the Vendoring section with:

  - resolution of the helper relative to the skill directory;
  - the exact `uv run --no-project python -I -S` command;
  - capture of the single stdout identity;
  - display of any stderr warning;
  - continuation on `unknown`;
  - a stop on nonzero execution;
  - the invariant that target HEAD is never used as source identity.

  Keep the stamp format unchanged. Do not duplicate the helper's manifest
  branch in prose, because that would create a second implementation.

- [ ] **Step 6: Prove packaging and dependency isolation.**

  ```bash
  uv run pytest tests/test_adopt_docs.py tests/test_marketplace.py -q
  ```

  The marketplace test proves `adopt-docs` remains declared; the repository
  root payload ensures its script is cached with the skill. The retired frozen
  pressure scenarios are not run against the updated skill, rebuilt, or
  altered; their existing bundle and recorded results remain historical
  evidence only.

- [ ] **Step 7: Commit the resolver.**

  ```bash
  git add adopt-docs/scripts/resolve_provenance.py adopt-docs/SKILL.md tests/test_adopt_docs.py
  git commit -m "feat(adopt-docs): resolve provenance deterministically"
  ```

---

### Task 4: Remove host-specific workflow dependencies from shipped skills

**Files:**

- Create: `tests/test_skill_portability.py`
- Modify: `align/SKILL.md`
- Modify: `adopt-docs/SKILL.md`
- Inspect without expected edits: `explain-diff/SKILL.md`

- [ ] **Step 1: Write the static portability audit.** Discover every
  root-level directory containing `SKILL.md` and assert none contains:

  - `AskUserQuestion`;
  - `superpowers:brainstorming`;
  - `superpowers:writing-plans`.

  Add focused assertions that `align` contains the three negotiated
  fallbacks:

  - structured-choice interaction when available, numbered plain text
    otherwise;
  - an available general design workflow outside adopted repositories,
    otherwise its own one-question interview without components;
  - an available implementation-plan workflow after sign-off, otherwise
    authoring the configured plan from the doc-components template.

- [ ] **Step 2: Confirm RED.**

  ```bash
  uv run pytest tests/test_skill_portability.py -q
  ```

- [ ] **Step 3: Make `align` host-neutral.**

  - Preserve its name, design/brainstorm trigger intent, one-question rhythm,
    component-capture flow, reviewer loop, and user sign-off gate.
  - Describe structured choices by capability, with two to four concrete
    options, and use numbered plain text when the host lacks a structured
    interaction.
  - Outside an adopted repository, delegate to an available general design
    workflow. If there is none, conduct the same interview itself and do not
    create components.
  - After spec sign-off, delegate to an available implementation-plan
    workflow. If there is none, author the configured plan using
    `doc-components/templates/plan.md` and the project's conventions.

- [ ] **Step 4: Make `adopt-docs` host-neutral.** Replace all three
  `AskUserQuestion-style` references with the same capability/fallback
  language. Replace explanatory references to
  "superpowers-produced planning artifacts" with host-neutral agent workflow
  language. Do not change the interview order, option count, explicit-answer
  requirement, or adoption behavior.

- [ ] **Step 5: Run portability and marketplace tests.**

  ```bash
  uv run pytest tests/test_skill_portability.py tests/test_marketplace.py -q
  ```

- [ ] **Step 6: Commit the instruction changes.**

  ```bash
  git add align/SKILL.md adopt-docs/SKILL.md tests/test_skill_portability.py
  git commit -m "feat(skills): add host-neutral workflow fallbacks"
  ```

---

### Task 5: Document both operator lifecycles and advisory smoke evidence

**Files:**

- Create: `docs/plugin-hosts.md`
- Create: `tests/test_plugin_host_docs.py`

- [ ] **Step 1: Write failing documentation contract tests.** Require the
  guide to contain separately labelled Claude Code and Codex procedures for:

  - marketplace discovery or registration;
  - install;
  - update and cache refresh;
  - list or verification;
  - uninstall and marketplace cleanup;
  - starting a new session after installation or update.

  Also require the verified date and CLI versions, isolation guidance, the
  expected smoke-evidence fields, and explicit wording that native smoke
  evidence is recommended rather than a merge gate.

- [ ] **Step 2: Confirm RED.**

  ```bash
  uv run pytest tests/test_plugin_host_docs.py -q
  ```

- [ ] **Step 3: Author `docs/plugin-hosts.md`.** Explain the shared
  repository-root payload and legacy-compatible Claude marketplace once, then
  give host-specific command sequences. Verify every command against
  `claude plugin --help` or `codex plugin --help` at implementation time
  before recording it.

  The update guidance must preserve manifest parity:

  - released updates use the shared semantic version and normal
    marketplace reinstall/update path;
  - local unreleased checks use isolated temporary host state;
  - never add a Codex-only cachebuster suffix to one manifest;
  - start a new agent session after install or update so the refreshed skills
    are loaded.

- [ ] **Step 4: Document the recommended smoke record.** Include date, both
  CLI versions, source commit, commands, outcomes, and cleanup status. The
  procedure uses a temporary repository snapshot and isolated host homes,
  validates the Claude Code marketplace, and exercises marketplace add,
  plugin add, list, remove, and marketplace cleanup where each verified CLI
  supports them.

  State plainly that Codex `0.145.0` has no standalone plugin validator, so
  its native evidence is an isolated install lifecycle rather than a
  validation command.

- [ ] **Step 5: Run the documentation tests.**

  ```bash
  uv run pytest tests/test_plugin_host_docs.py -q
  ```

- [ ] **Step 6: Commit the operator guide.**

  ```bash
  git add docs/plugin-hosts.md tests/test_plugin_host_docs.py
  git commit -m "docs(plugin): document Claude Code and Codex operations"
  ```

---

### Task 6: Set the release version, validate the whole branch, and publish the decisions

**Files:**

- Modify: `.claude-plugin/plugin.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `docs/components/adr/dual-plugin-manifests.md`
- Modify: `docs/components/adr/stdlib-provenance-resolver.md`
- Modify: `docs/components/nongoal/host-abstraction-framework.md`
- Generated by grim: `docs/current/decisions.md`,
  `docs/current/charter.md`

- [ ] **Step 1: Run all targeted deterministic checks.**

  ```bash
  uv run pytest \
    tests/test_marketplace.py \
    tests/test_version_bump.py \
    tests/test_adopt_docs.py \
    tests/test_skill_portability.py \
    tests/test_plugin_host_docs.py \
    -q
  ```

- [ ] **Step 2: Apply the computed shared release version.** Run the existing
  checker in apply mode with the actual branch base and PR title environment.
  Do not hand-calculate or independently edit either version.

  ```bash
  PR_TITLE="feat: support Claude Code and Codex plugin hosts" \
    BASE_REF=main \
    python3 .github/scripts/check_version_bump.py --apply
  ```

  If the branch base is available only as a SHA, use `BASE_SHA` instead.
  Assert both manifests carry the same computed version, then rerun the
  marketplace and version tests.

- [ ] **Step 3: Run the full automated suite.**

  ```bash
  uv run pytest -q
  ```

- [ ] **Step 4: Run recommended native smoke checks when the pinned CLIs are
  available.** Use isolated temporary state and the exact operator-guide
  procedure:

  ```bash
  claude plugin validate .
  claude --version
  codex --version
  ```

  Continue with each host's marketplace install/list/remove lifecycle. Record
  the transcript in the pull request or release record when practical. A
  missing CLI or host regression is reported honestly; it is not represented
  as a CI failure that the repository cannot enforce.

- [ ] **Step 5: Promote the implemented components.** Change the three
  components referenced by the spec from `draft` to `current`. Update their
  `paths:` frontmatter if implementation placed an enforcing file outside the
  paths already declared. Manually cross-check the three ids against the
  spec's `components:` list: grim does not currently validate that list. Do
  not edit component prose merely to restate code.

- [ ] **Step 6: Regenerate and verify documentation.**

  ```bash
  uv run tools/grim.py lint --fix
  uv run tools/grim.py render
  uv run tools/grim.py check
  git diff --check
  ```

  The empty `grim:status` blocks remain in place as template-owned
  placeholders. Current grim does not derive working-layer banners, so do not
  fill them manually or claim that this task generated them.

- [ ] **Step 7: Re-run the release gate in check mode.**

  ```bash
  PR_TITLE="feat: support Claude Code and Codex plugin hosts" \
    BASE_REF=main \
    python3 .github/scripts/check_version_bump.py
  ```

- [ ] **Step 8: Commit the release and component publication.**

  ```bash
  git add \
    .claude-plugin/plugin.json \
    .codex-plugin/plugin.json \
    docs/components/adr/dual-plugin-manifests.md \
    docs/components/adr/stdlib-provenance-resolver.md \
    docs/components/nongoal/host-abstraction-framework.md \
    docs/current \
    docs/specs/2026-07-27-cross-compatible-plugin.md \
    docs/plans/2026-07-27-cross-compatible-plugin.md
  git commit -m "feat(plugin): publish cross-host compatibility contract"
  ```

## Completion criteria

- Both native manifests exist and match on every shared field.
- Check and print modes reject any shared drift; apply rejects non-version
  drift and updates both versions with tested rollback.
- Bootstrap and `Version-Waive` behavior are explicit and tested.
- Adoption provenance is resolved by the isolated standard-library helper,
  including safe mismatch and malformed-metadata fallback.
- Every shipped skill passes the static portability audit.
- The operator guide covers both host lifecycles and labels native smoke
  evidence advisory.
- The full pytest suite, version gate, `grim check`, and diff check pass.
- The three components are current and their rendered views are committed.

## Out of scope

- Moving skill directories or creating a conventional `skills/` subtree.
- A generated package payload or separate Codex marketplace catalog.
- A generalized API for host interactions.
- Public marketplace publication.
- MCP servers, apps, hooks, icons, or other presentation work.
- New third-party runtime dependencies.
- Mutating the frozen adopt-docs pressure-test bundle.
- Rerunning the retired pressure scenarios with the updated skill.
- Implementing working-layer banner derivation.
- Treating manually recorded native-host smoke checks as an enforced merge
  condition.
