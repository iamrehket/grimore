---
spec: docs/superpowers/specs/2026-07-24-doc-components-design.md
---

<!-- grim:status -->
<!-- /grim:status -->

# Touched-path guard + Grim-Waive (IAM-42) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the minimal deterministic staleness guard inside `grim lint`: when the branch diff touches paths a `current` note/adr declares in `paths:`, the component must change in the same branch or carry a recorded `Grim-Waive: <component-id> <reason>` commit-trailer waiver, echoed in lint output.

**Architecture:** All in `tools/grim.py`. A shared `resolve_merge_base()` helper is extracted from `check_transitions` (which grew an `origin/<default_branch>` fallback in IAM-40) so the transition check and the new `check_touched_paths()` resolve the base once, in `run_lint`, and merge-base findings are emitted exactly once. `collect_waivers()` parses `Grim-Waive:` trailers from `git log <base>..HEAD`. The guard produces `E070` (unwaived hit), `W071` (waived hit, echoed for reviewers), and `E072`/`W072` (diff computation failed: error under strict, warning locally). No CLI changes — the guard runs inside `lint` and therefore inside `check`.

**Tech Stack:** Python >= 3.11, PyYAML, stdlib `fnmatch`; pytest.

**Sequencing precondition:** this plan is written against `tools/grim.py` as it stands after IAM-40 merges (origin-fallback merge-base, `run_check` calling `run_lint(strict=True)`). Branch from main only after the IAM-40 PR lands. If line numbers or surrounding code differ, the function names named per task are the anchors.

Spec: docs/superpowers/specs/2026-07-24-doc-components-design.md (Decisions item 6, Tooling, finish-docs no-spec fast path).
Requirements doc: doc-components/SCHEMA.md (`paths` row). Linear: IAM-42.

## Global Constraints

- `tools/grim.py` stays a **single file**; runtime deps **stdlib + PyYAML only**.
- Branch: `aalbright/iam-42-touched-path-guard-grim-waive`. Commit this plan file as the branch's first commit.
- **Stage named paths only** in the grimore repo; `git add -A` allowed only inside throwaway fixture repos under `tmp_path`.
- No emojis in any output, code, or docs.
- Test command: `uv run pytest -q`.
- Out of scope: coverage reporting and path-hygiene tooling (stale/renamed `paths:` globs) — deferred full tripwire (IAM-47); banner blocks (IAM-41); any render changes.
- All existing tests stay green; the `check_transitions` refactor must not change any observable behavior.
- Reference files by path, never by commit SHA.

## Design decisions (local to this plan; spec left them open)

- **Which components gate:** `status: current` note/adr components with a non-empty `paths:` list. Drafts and superseded components never gate (not live). Schema already restricts `paths:` to note/adr (E018).
- **Diff basis:** `git diff --name-only -z <merge-base>` — merge-base against the working tree, so uncommitted edits to **tracked** files count both as hits and as component changes. Untracked files are invisible to the guard locally; in CI everything is committed, so the guarantee that matters (nothing merges unguarded) holds. Documented as "tracked changes" — not oversold as all local edits.
- **Glob semantics:** a pattern ending in `/` is a directory prefix match; anything else goes through `fnmatch.fnmatchcase` (case-sensitive on every platform) on the git-root-relative posix path. `*` crosses `/` in fnmatch — documented in SCHEMA.md, acceptable for v1. Path frame: `paths:` globs are git-root-relative, matching the spec's `paths: [src/render/]` example.
- **Waiver scope:** trailers are read from commit messages in `<base>..HEAD`. A waiver names one component id; reasons are free text to end of line. Multiple waivers per commit and per component are allowed; all reasons are echoed. Uncommitted work cannot carry a waiver (there is no commit to hold the trailer) — the guard then reports E070 until the waiver commit exists; accepted.
- **Merge-base findings are emitted once:** `run_lint` resolves the base a single time and passes it to both consumers; when unresolvable, existing E042/W042 semantics are preserved (strict fails closed, local skips with a warning) and the guard silently skips alongside the transition check — one finding, not two.
- **Finding codes:** `E070` unwaived hit (error), `W071` waived hit (warning echo), `E072`/`W072` diff-computation failure (strict/local — the guard never silently skips in CI). One hit finding per gating component, naming the first hit path (deterministic: lexicographically smallest), not one per touched file — keeps output bounded on big branches.

---

### Task 1: Extract resolve_merge_base and thread it through run_lint

Pure refactor: no behavior change, all existing tests stay green.

**Files:**
- Modify: `tools/grim.py` (`check_transitions`, new `resolve_merge_base`, `run_lint`)
- Test: `tests/test_transitions.py` (update call sites only)

**Interfaces:**
- Produces: `resolve_merge_base(cfg: Config, strict: bool) -> tuple[str | None, list[Finding]]` — returns (merge-base sha, []) on success; (None, [E042]) under strict; (None, [W042]) otherwise; (None, []) when the components dir does not exist and there is nothing to report (preserving today's early-return). `check_transitions(store: Store, cfg: Config, base: str | None, strict: bool) -> list[Finding]` — `base` replaces the internal resolution (`base is None` means "already reported, skip"), but `strict` is **retained**: the function's second E042/W042 pair (the `ls-tree`-at-merge-base failure case) still chooses error-vs-warning by mode. Task 3 consumes both.

- [ ] **Step 1: Move the resolution block.** Lift the top/merge-base/fallback logic (the block from `top = _git(...)` through the E042/W042 emission, including the missing-components-dir early return) out of `check_transitions` into:

```python
def resolve_merge_base(cfg: Config, strict: bool) -> tuple[str | None, list[Finding]]:
    top = _git(cfg, "rev-parse", "--show-toplevel")
    refs_tried = [cfg.default_branch, f"origin/{cfg.default_branch}"]
    base = None
    if top.returncode == 0:
        for ref in refs_tried:
            mb = _git(cfg, "merge-base", "HEAD", ref)
            if mb.returncode == 0:
                base = mb.stdout.strip()
                break
    if base is not None:
        return base, []
    if not cfg.components.is_dir():
        return None, []
    if strict:
        return None, [error("E042", ".", f"cannot resolve git merge-base with any of {refs_tried}; failing closed (fix CI: fetch-depth: 0)")]
    return None, [warning("W042", ".", f"cannot resolve git merge-base with any of {refs_tried}; skipping transition and touched-path checks")]
```

`check_transitions(store, cfg, base, strict)` now starts with `if base is None: return []` and drops its own resolution — but keeps `strict`: its second E042/W042 pair (the `ls-tree`-at-merge-base failure case) still needs it to choose error versus warning, and that branch is otherwise unchanged. It still re-derives `git_root` via `rev-parse --show-toplevel` for path relativization.

In `run_lint`:

```python
    base, mb_findings = resolve_merge_base(cfg, strict)
    findings += mb_findings
    findings += check_transitions(store, cfg, base, strict)
```

- [ ] **Step 2: Update test call sites.** In `tests/test_transitions.py`, change the `transitions()` helper to route through the new seam so every existing scenario still exercises resolution + check:

```python
def transitions(root, strict=False):
    cfg = grim.load_config(root)
    store = grim.load_store(cfg)
    base, findings = grim.resolve_merge_base(cfg, strict)
    return findings + grim.check_transitions(store, cfg, base, strict)
```

- [ ] **Step 3: Run the full suite** — `uv run pytest -q`, everything green with zero test-expectation changes (the W042 message text change from "skipping transition check" to "skipping transition and touched-path checks" may require updating one message assertion if a test pins it; adjust that assertion only).

- [ ] **Step 4: Commit**

```bash
git add tools/grim.py tests/test_transitions.py
git commit -m "IAM-42: extract resolve_merge_base, resolve once per lint run"
```

---

### Task 2: collect_waivers — Grim-Waive trailer parsing

**Files:**
- Modify: `tools/grim.py`
- Test: `tests/test_touched_paths.py` (new file)

**Interfaces:**
- Consumes: `_git`.
- Produces: `WAIVE_RE` and `collect_waivers(cfg: Config, base: str) -> dict[str, list[str]]` mapping component id -> list of waiver reasons, ordered oldest commit first. Task 3 consumes it.

- [ ] **Step 1: Write the failing tests** in new `tests/test_touched_paths.py` (copy the `git`/`make_repo`/`commit_all` helpers from `tests/test_check.py`, same throwaway-fixture-repo caveat):

```python
import subprocess

import grim
from helpers import write_component


def git(root, *args):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def make_repo(root):
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")


def commit_all(root, msg):
    # Broad add is fine here: throwaway fixture repo under tmp_path.
    git(root, "add", "-A")
    git(root, "commit", "-m", msg)


def base_of(root):
    return git(root, "merge-base", "HEAD", "main").strip()


def test_collect_waivers_parses_trailers(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "a.txt").write_text("a")
    commit_all(tmp_path, "init")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "b.txt").write_text("b")
    commit_all(tmp_path, "change\n\nGrim-Waive: note-renderer just a comment tweak")
    (tmp_path / "c.txt").write_text("c")
    commit_all(
        tmp_path,
        "more\n\nGrim-Waive: note-renderer second reason\nGrim-Waive: adr-render-hash separate id",
    )
    cfg = grim.load_config(tmp_path)
    waivers = grim.collect_waivers(cfg, base_of(tmp_path))
    assert waivers == {
        "note-renderer": ["just a comment tweak", "second reason"],
        "adr-render-hash": ["separate id"],
    }


def test_collect_waivers_ignores_base_side_and_malformed(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "a.txt").write_text("a")
    commit_all(tmp_path, "init\n\nGrim-Waive: note-old on the base, out of range")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "b.txt").write_text("b")
    commit_all(tmp_path, "change\n\nGrim-Waive:\nGrim-Waive: lone-id-no-reason")
    cfg = grim.load_config(tmp_path)
    assert grim.collect_waivers(cfg, base_of(tmp_path)) == {}


def test_body_mention_outside_trailer_block_is_not_a_waiver(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "a.txt").write_text("a")
    commit_all(tmp_path, "init")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "b.txt").write_text("b")
    # The line starts exactly with "Grim-Waive:" but sits in a NON-final
    # paragraph, so it is not part of the git trailer block. A naive
    # multiline ^Grim-Waive: regex would match it (this test must fail such
    # an implementation); git trailer parsing must not.
    commit_all(
        tmp_path,
        "docs: explain waivers\n\n"
        "Grim-Waive: note-renderer some reason\n"
        "is the trailer format reviewers use to bypass the guard.\n\n"
        "This final paragraph makes the paragraph above body prose, not trailers.",
    )
    cfg = grim.load_config(tmp_path)
    assert grim.collect_waivers(cfg, base_of(tmp_path)) == {}
```

- [ ] **Step 2: Run, confirm failure** — `uv run pytest tests/test_touched_paths.py -q`, AttributeError on `collect_waivers`.

- [ ] **Step 3: Implement**

```python
WAIVE_VALUE_RE = re.compile(r"^(\S+)\s+(\S.*?)\s*$")


def collect_waivers(cfg: Config, base: str) -> dict[str, list[str]]:
    # Let git identify the trailer block: %(trailers:key=...) only reads the
    # final trailer paragraph, so a "Grim-Waive:" quoted or discussed in the
    # commit body prose is NOT a waiver.
    log = _git(
        cfg, "log", "--reverse",
        "--format=%(trailers:key=Grim-Waive,valueonly=true)%x00",
        f"{base}..HEAD",
    )
    waivers: dict[str, list[str]] = {}
    if log.returncode != 0:
        return waivers
    for block in log.stdout.split("\0"):
        for line in block.splitlines():
            m = WAIVE_VALUE_RE.match(line.strip())
            if m:
                waivers.setdefault(m.group(1), []).append(m.group(2))
    return waivers
```

A trailer value with an id but no reason does not match (`\S.*?` requires at least one non-space reason character) — a waiver without a reason is not a recorded waiver. `%(trailers)` with `key=` requires git >= 2.22; acceptable floor.

- [ ] **Step 4: Run the full suite** — green.

- [ ] **Step 5: Commit**

```bash
git add tools/grim.py tests/test_touched_paths.py
git commit -m "IAM-42: parse Grim-Waive commit trailers"
```

---

### Task 3: check_touched_paths — the guard

**Files:**
- Modify: `tools/grim.py` (new check + wiring in `run_lint`)
- Test: `tests/test_touched_paths.py`

**Interfaces:**
- Consumes: `resolve_merge_base` output (`base` threaded by `run_lint`), `collect_waivers`, `_git`.
- Produces: `check_touched_paths(store: Store, cfg: Config, base: str | None, strict: bool) -> list[Finding]` emitting `E070` (unwaived hit), `W071` (waived hit echo), and `E072`/`W072` (git failure while computing the diff: error under strict, warning locally — the guard must not silently skip in CI); wired into `run_lint` after `check_transitions`. `grim check` inherits the guard automatically (its lint is strict, so an unresolvable base already fails closed before the guard matters).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_touched_paths.py`):

```python
def lint_codes(root, strict=False):
    result = grim.run_lint(root, strict=strict)
    return [f.code for f in result.findings]


def guarded_repo(tmp_path):
    """main: a note declaring paths: [src/render/] plus src/render/x.py; then a feature branch."""
    make_repo(tmp_path)
    write_component(
        tmp_path, "note", "renderer",
        extra={"subsystem": "renderer", "paths": "[src/render/]"},
    )
    src = tmp_path / "src" / "render"
    src.mkdir(parents=True)
    (src / "x.py").write_text("x = 1\n")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    return src


def test_hit_without_component_change_is_e070(tmp_path):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak renderer")
    # Exact list: this fixture produces no unrelated findings.
    assert lint_codes(tmp_path) == ["E070"]
    [finding] = [f for f in grim.run_lint(tmp_path).findings if f.code == "E070"]
    assert "Grim-Waive: note-renderer" in finding.message  # tells the operator the exact trailer


def test_hit_with_component_change_is_clean(tmp_path):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    write_component(
        tmp_path, "note", "renderer", body="Updated fact.",
        extra={"subsystem": "renderer", "paths": "[src/render/]"},
    )
    commit_all(tmp_path, "tweak renderer and its note")
    assert "E070" not in lint_codes(tmp_path)


def test_hit_with_waiver_is_w071_echo(tmp_path):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak\n\nGrim-Waive: note-renderer comment-only change")
    # Exact list: this fixture produces no unrelated findings.
    assert lint_codes(tmp_path) == ["W071"]
    [finding] = [f for f in grim.run_lint(tmp_path).findings if f.code == "W071"]
    assert "comment-only change" in finding.message  # reason echoed for reviewers


def test_waiver_for_other_component_does_not_apply(tmp_path):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak\n\nGrim-Waive: note-other wrong id")
    assert "E070" in lint_codes(tmp_path)


def test_draft_component_does_not_gate(tmp_path):
    # A fresh repo whose gating note is draft from the start: flipping an
    # existing current component to draft would itself be an illegal
    # transition (E040), which would pollute this test's assertion.
    make_repo(tmp_path)
    write_component(tmp_path, "note", "renderer", status="draft", extra={"paths": "[src/render/]"})
    src = tmp_path / "src" / "render"
    src.mkdir(parents=True)
    (src / "x.py").write_text("x = 1\n")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak")
    assert "E070" not in lint_codes(tmp_path)


def test_uncommitted_working_tree_changes_count(tmp_path):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")  # not committed
    assert "E070" in lint_codes(tmp_path)


def test_fnmatch_glob_without_trailing_slash(tmp_path):
    make_repo(tmp_path)
    write_component(tmp_path, "adr", "render-hash", extra={"paths": "[src/*.py]"})
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("m = 1\n")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "src" / "m.py").write_text("m = 2\n")
    commit_all(tmp_path, "tweak")
    assert "E070" in lint_codes(tmp_path)


def test_paths_on_non_gating_type_never_fires_guard(tmp_path):
    # A usecase with paths: is an E018 schema error; the guard itself must
    # not also fire on it (only current note/adr gate).
    make_repo(tmp_path)
    write_component(tmp_path, "usecase", "u", extra={"paths": "[src/]"})
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text("m = 1\n")
    commit_all(tmp_path, "baseline")
    git(tmp_path, "checkout", "-b", "feature")
    (tmp_path / "src" / "m.py").write_text("m = 2\n")
    commit_all(tmp_path, "tweak")
    codes = lint_codes(tmp_path)
    assert "E018" in codes and "E070" not in codes


def test_e070_fails_grim_check(tmp_path):
    # Integration: an unwaived hit must fail the CI entry point end to end.
    src = guarded_repo(tmp_path)
    grim.main(["render", "--root", str(tmp_path)])  # store is clean pre-hit
    commit_all(tmp_path, "commit rendered view")
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak renderer without touching the note")
    result = grim.run_check(tmp_path)
    assert "E070" in [f.code for f in result.lint.errors]
    assert result.exit_code == 1


def test_no_merge_base_skips_guard_with_single_warning(tmp_path):
    # No commits at all: resolve_merge_base already emits one W042; the guard
    # must not add another finding.
    write_component(tmp_path, "note", "renderer", extra={"paths": "[src/]"})
    result = grim.run_lint(tmp_path)
    assert [f.code for f in result.findings] == ["W042"]


def _failing_diff_git(real_git):
    def wrapper(cfg, *args):
        r = real_git(cfg, *args)
        if args and args[0] == "diff":
            r.returncode = 128
        return r
    return wrapper


def test_diff_failure_fails_closed_in_strict(tmp_path, monkeypatch):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak")
    monkeypatch.setattr(grim, "_git", _failing_diff_git(grim._git))
    result = grim.run_lint(tmp_path, strict=True)
    codes = [f.code for f in result.findings]
    assert "E072" in codes and "E070" not in codes  # failed closed, not silently green


def test_diff_failure_warns_locally(tmp_path, monkeypatch):
    src = guarded_repo(tmp_path)
    (src / "x.py").write_text("x = 2\n")
    commit_all(tmp_path, "tweak")
    monkeypatch.setattr(grim, "_git", _failing_diff_git(grim._git))
    result = grim.run_lint(tmp_path, strict=False)
    codes = [f.code for f in result.findings]
    assert "W072" in codes and "E070" not in codes and "E072" not in codes
```

(The monkeypatched `_git` only degrades `diff` calls; `rev-parse`, `merge-base`, `ls-tree`, `show`, and `log` behave normally, so only the guard's diff step fails.)

- [ ] **Step 2: Run, confirm the new tests fail** — no `check_touched_paths`, and `run_lint` emits nothing guard-related.

- [ ] **Step 3: Implement**

```python
def _glob_hit(path: str, globs: list) -> bool:
    for g in globs:
        if g.endswith("/"):
            if path.startswith(g):
                return True
        elif fnmatch.fnmatchcase(path, g):
            # fnmatchcase, not fnmatch: no platform-dependent case folding.
            return True
    return False


def check_touched_paths(store: Store, cfg: Config, base: str | None, strict: bool) -> list[Finding]:
    out: list[Finding] = []
    gating = [
        c for c in store.components
        if c.status == "current"
        and isinstance(c.cid, str)
        and c.ctype in PATHS_TYPES
        and isinstance(c.fm.get("paths"), list)
        and c.fm["paths"]
        and all(isinstance(g, str) for g in c.fm["paths"])
        # anything shaped otherwise is already E018/E019 territory in check_schema
    ]
    if base is None or not gating:
        return out
    top = _git(cfg, "rev-parse", "--show-toplevel")
    diff = _git(cfg, "diff", "--name-only", "-z", base)
    if top.returncode != 0 or diff.returncode != 0:
        # Do not silently skip: in CI a skipped guard is a bypassed guard.
        if strict:
            return [error("E072", ".", "touched-path guard could not compute the branch diff; failing closed")]
        return [warning("W072", ".", "touched-path guard could not compute the branch diff; skipping")]
    git_root = Path(top.stdout.strip()).resolve()
    touched = {name for name in diff.stdout.split("\0") if name}
    waivers = collect_waivers(cfg, base)
    for c in gating:
        own = c.path.resolve().relative_to(git_root).as_posix()
        hits = sorted(p for p in touched if _glob_hit(p, c.fm["paths"]))
        if not hits or own in touched:
            continue
        if c.cid in waivers:
            reasons = "; ".join(waivers[c.cid])
            out.append(warning(
                "W071", c.rel,
                f"touched-path hit on {hits[0]!r} waived: {reasons}", c.cid,
            ))
        else:
            out.append(error(
                "E070", c.rel,
                f"branch touches {hits[0]!r}, declared in this component's paths:, "
                f"without changing the component; update it or record a waiver with "
                f"commit trailer 'Grim-Waive: {c.cid} <reason>'", c.cid,
            ))
    return out
```

Add `import fnmatch` to the top imports. Wire into `run_lint` directly after the transition check:

```python
    findings += check_transitions(store, cfg, base, strict)
    findings += check_touched_paths(store, cfg, base, strict)
```

- [ ] **Step 4: Run the full suite** — `uv run pytest -q`, green (including all IAM-40 render/check tests: `grim check` now enforces the guard through its strict lint).

- [ ] **Step 5: Commit**

```bash
git add tools/grim.py tests/test_touched_paths.py
git commit -m "IAM-42: touched-path guard with Grim-Waive trailer waivers (E070, W071)"
```

---

### Task 4: Documentation

**Files:**
- Modify: `doc-components/SCHEMA.md` (`paths` row + new subsection), `doc-components/CI.md`

**Interfaces:** none new.

- [ ] **Step 1: SCHEMA.md.** Extend the `paths` row's rule text to: "`note`/`adr` only; list of git-root-relative path globs the component describes; a trailing `/` matches the directory prefix, otherwise case-sensitive fnmatch, where `*` matches across `/`. Drives the touched-path guard: a branch that touches a matching path must change this component or record a `Grim-Waive: <id> <reason>` commit trailer (the trailer must sit in the commit's trailer block, and the reason is mandatory)." Add a short "Touched-path guard" subsection under Lifecycle stating: only `current` components gate; the guard sees tracked changes vs the merge-base; waivers are echoed in lint output (`W071`) so reviewers see every bypass; coverage grows as `paths:` get declared.

- [ ] **Step 2: CI.md.** In the merge-discipline section, replace "(from IAM-42 on)" phrasing with present tense: unwaived touched-path hits fail `grim check`; waivers appear in lint output as `W071` warnings for reviewer visibility.

- [ ] **Step 3: Verify docs lint clean** — `uv run tools/grim.py lint --root .` exits 0; `uv run pytest -q` green.

- [ ] **Step 4: Commit**

```bash
git add doc-components/SCHEMA.md doc-components/CI.md
git commit -m "IAM-42: document the touched-path guard and Grim-Waive"
```

---

## Final gate (before PR)

- Full suite green; repo lints clean.
- Whole-branch review on opus (per process), fix wave if needed.
- PR to main titled "IAM-42: touched-path guard + Grim-Waive", attached to Linear IAM-42. Single merge only.
