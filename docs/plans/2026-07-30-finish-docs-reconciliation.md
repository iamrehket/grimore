---
spec: docs/specs/2026-07-30-finish-docs-reconciliation.md
---

<!-- grim:status -->
> **Implemented 2026-07-31 (PR #17).**
> References current.
<!-- /grim:status -->

# Finish-docs Reconciliation (IAM-44) Implementation Plan

> **For implementation workers:** the enforcement changes land before the
> script that depends on them, because reconcile's validation is grim's lint.
> Two traps are called out inline; both are silent, and neither surfaces as a
> failing test unless the test is written to look for it.

1. **Run the GREEN baseline for phase A first.** Its result decides how much of
   phase B is prose and how much is refusal. Running it afterwards wastes it.

2. **grim enforcement.** E032 for an un-cascaded promotion; E043 for an
   in-place edit to a component that was not draft at the merge-base; E095 for
   a stamped spec whose components were all abandoned; standing waivers with
   W073 and E073; the E070 message, which must keep the literal
   `Grim-Waive: <cid>` substring an existing test asserts.

   *Trap:* E043 must compare parsed frontmatter and the newline-stripped body,
   never raw bytes. `lint --fix` reorders fields and re-spaces bodies, so a byte
   comparison reports every normalized file as an illegal edit - all 48 of them.

3. **reconcile.py.** Five outcomes, one intent per component computed before any
   write, cycles rejected, edges merged as sets. Completeness over drafts
   referenced by in-scope specs, drafts created on the branch, and drafts named
   with `--component`; untracked files under the governed directories are a hard
   refusal because the branch diff cannot see them.

   *Trap:* the post-write gate must roll back unless grim exited 0, or exited 1
   with parseable JSON whose only errors are E090. grim writes nothing to
   standard output when config loading fails, so a gate phrased as "did any
   error appear in the report" reads that silence as success.

4. **stamp_spec.** Refuse a spec whose components were all abandoned, using
   grim's reachability helper rather than a local rule.

5. **Skill and schema.** Both phases in SKILL.md, every command with an explicit
   `--root`, and the procedure ending with `grim check`. Schema records the
   stamp definition, the standing-waiver shape, and the codes now enforcing the
   cascade and drafts-only rules.

6. **Second fixture scenario**, added rather than substituted, so the phase A
   baselines stay replayable.

7. **Reconcile this branch with its own tool**, including the backfilled
   adr-payload-renderer-split. That promotion is the acceptance criterion, and
   it is the only one on this branch the transition check actually validates -
   components created here are new at the merge-base, where any initial status
   is legal.
