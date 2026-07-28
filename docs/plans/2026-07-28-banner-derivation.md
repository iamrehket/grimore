---
spec: docs/specs/2026-07-28-banner-derivation.md
---

<!-- grim:status -->
> **Not yet implemented.**
<!-- /grim:status -->

# Banner Derivation (IAM-41) Implementation Plan

> **For implementation workers:** Execute task by task, keeping tests red
> before each behavioral change. Two traps in the existing code are called out
> below; both are silent failures rather than crashes, so neither shows up
> without a test that asserts the exit code or the written bytes.

**Goal:** `grim lint --fix` derives spec and plan banner blocks; `grim lint`
reports drift as an error; `grim check` fails on a stale banner.

## Task 1: Pin the stamp wire format

`doc-components/templates/spec.md:3` shows `implemented: <YYYY-MM-DD (PR #N)>`.
Unquoted, ` #` opens a YAML comment and the value truncates. Update the
template to the quoted form. Update `doc-components/SCHEMA.md` with the quoting
rule, the never-empty rule, and the advisory-wording caveat.

Editing `SCHEMA.md` trips the touched-path guard, because
`adr-agent-optimized-source` declares it. The ADR's content is not changing and
editing a current component in place is forbidden, so the commit carries:

```
Grim-Waive: adr-agent-optimized-source documenting banner behavior the ADR already governs
```

Do not resolve a red guard by editing the ADR.

## Task 2: Transitive successor resolution

Lift the successor map out of `check_edges` into a module-level helper and have
both callers use it. Add forward resolution to a current component with a
mandatory visited-set cycle guard.

The existing map keys only when the successor is current, so `a <- b <- c` with
`b` superseded leaves `a` with no entry. Naive reuse reports `abandoned` while a
live successor exists. Cycles reach this code: only self-supersede and missing
targets are rejected today.

## Task 3: Working-layer loader and stamp parser

One `WorkingDoc` loader over the specs and plans directories, reusing the
existing frontmatter regex. Fold the current plan check into this pass rather
than running two parsers over the same files; keep `W060` and its
whitespace-only-`spec:` behavior.

`_parse_implemented`: type guard accepting only `str` and `datetime.date`;
coerce dates with `.isoformat()` following the parse-side precedent in
`parse_component`, not the serializer; validate with the date regex *and* the
date parser, mirroring the schema check, since the regex is load-bearing.
Optional trailing ` (PR #N)`.

## Task 4: Derive the banner

Provenance line, then ordered qualifier clauses: empty list, drafts, partial
supersede, full supersede, abandoned. Never returns empty.

Plans inherit their spec's interior. Resolve `spec:` against the project root
with a containment guard mirroring the config loader; a target that escapes the
root is rejected unread. A target that is missing or ungoverned yields a status
line saying so rather than a blank block. A plan carrying its own
`implemented:` is an error.

Determinism: identifier lists sorted, pairs ordered by source then successor,
one trailing newline, no clock or locale input.

## Task 5: Findings and the write path

Add the `09x` codes. Write only between the delimiters; carry over the existing
symlink refusal.

**Trap 1.** The existing fix pass skips any file carrying an error. Reusing that
rule verbatim makes `--fix` a no-op on the exact file the drift error names. Use
a blocking set instead: spec-local errors plus store-level identifier and edge
errors, so a banner is never derived from a graph already known to be broken.

**Trap 2.** Findings are computed once and the exit code derives from that list.
Drift would be the first error the tool repairs in-run, so the fixing run would
exit non-zero carrying the error it just fixed - breaking `lint --fix && render`,
which the instruction files, the CI recipe, and the adoption skill all mandate,
and which is also the documented remedy for a banner merge conflict. Drop
repaired drift findings from the result and assert the exit code in a test.

## Task 6: Tests

Add spec and plan helpers that accept frontmatter verbatim, since several cases
need malformed input a dict-assembling helper cannot express.

Regression-critical: stamp round-trip through disk as literal bytes; fixing run
exits zero; stamped spec with a draft; empty component list; chained supersede
resolving past an intermediate; cycle termination; no write when the graph has
multiple live successors; `spec:` resolution including escape and absence;
non-string stamp types; plan-level stamp; symlink refusal.

Behavioral: idempotency, convergence from a mangled block, determinism under
reordered input, plan inheritance, the fix-skip distinction, the CI gate, and
the freeze rule.

## Task 7: Verify end to end

Run the suite, then lint, fix, render as a chained command, re-lint clean,
re-fix for idempotency, and check. Inspect the diff of the two pre-existing
working-layer files: only block interiors changed. Finally mangle a banner and
confirm check exits non-zero.
