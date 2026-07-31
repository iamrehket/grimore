# Baseline: GREEN run, scenario-shipped-branch

Date: 2026-07-30. Sonnet subagent, given the skill at an installed location
outside both repositories (`/private/tmp/grim-plugin-install/finish-docs`), the
fixture, the request, and the scripted answers. Ran single-shot.

Fixture built by `make_fixture.py` in this directory. Start state carried four
`E090` findings (banner drift on both specs and both plans) and nothing else -
the normal pre-`lint --fix` state the stamper's preflight exempts.

## Rubric scoring

1. PASS - `implemented: "2026-07-30 (PR #47)"`, quoted, round-tripping through
   `yaml.safe_load` as the complete string including the PR number.
2. PASS - `2026-07-21-column-order.md` unstamped; `adr-column-order-config`
   still `draft`.
3. PASS - named `adr-column-order-config` in the final message, framed the
   refusal as designed behavior, did not present the run as fully successful.
4. PASS - banner in the spec and its plan both read
   `> **Implemented 2026-07-30 (PR #47).**` / `> References current.`
5. PASS - `> **Not yet implemented.**` plus the derived qualifier clause
   `> Not fully realized: adr-column-order-config still draft.`
6. PASS - `grim check --root <fixture-root>` exits 0. **Verified by the scorer,
   not by the run**; see finding 1 below.
7. PASS - stamper invoked as
   `/private/tmp/grim-plugin-install/finish-docs/scripts/stamp_spec.py` with
   `--root <fixture-root>` - resolved from the skill's own location.
8. PASS - verified by construction: the committed tree is byte-identical to a
   mechanical replay of stamper + `lint --fix` + `render` from the pre-run
   commit. No hand-editing occurred anywhere.

## Verdict: PASS (8 of 8)

## What GREEN establishes against RED, stated narrowly

RED passed 6 of 8 on discipline alone. The two lines GREEN adds are exactly the
two the tooling exists for: the stamp was written by something that validates
it (7), and nothing was written by hand (8). GREEN therefore **confirms the RED
reading rather than overturning it** - the skill's contribution on the happy
path is *route*, not outcome semantics. A diligent agent already gets the
semantics right; what it cannot supply is a validated writer and an enforced
refusal.

The design consequence for phase B is direct: **spend the instruction budget on
what to refuse, what to print, and which script to call with which flags - not
on how to form a judgment.** Prose describing how to tell whether code matches
a draft buys little, because the capability is already there. Prose that names
a refusal, or a script that makes a verdict explicit and auditable, buys the
thing the agent cannot give itself.

Phase B's shape follows: the agent forms the reconciliation verdict, which is
irreducibly agentic; a script performs the transition, enforces its legality,
and prints the audit line. That delivers "shown, never silent" without
pretending a script can judge.

## Findings against phase A, both real

**1. The skill never verifies with `grim check`.** The run substituted `lint
--fix`'s exit code for `check`'s, reporting "exit checks passed already (lint
--fix returned 0 errors)". True here, and not true in general: `check`
additionally byte-compares the rendered views, which is the failure mode
`render` exists to prevent. `SKILL.md` step 3 stops at `lint --fix && render`
and never asks for the CI gate to be run. Phase B should close the procedure
with `check`.

**2. `SKILL.md` is precise about `<skill-dir>` and sloppy about `<target>`.**
Step 2 correctly insists the stamper path be resolved from the skill's own
location. Step 3 then gives `uv run tools/grim.py lint --fix` - working-directory
relative, with no `--root`. The run made it work by `cd`-ing into the fixture
root for every command, which the run methodology explicitly says not to do.
The asymmetry is the cause: having been told the skill directory cannot be
assumed, the agent was told nothing about the target, so it moved itself to
where the command would work. Every command phase B documents needs an explicit
`--root`.

Neither finding was caught by the rubric, which scores end state and the
stamper invocation. Both would have shipped.

## Residue

The scenario's own caveat from the RED writeup still stands: the draft
component here is obviously unfinished, which makes the refusal easy. A phase B
scenario needs a draft whose promotion looks reasonable and is wrong.
