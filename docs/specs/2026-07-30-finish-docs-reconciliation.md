---
components:
  - adr-implemented-stamp-branch-finish
  - adr-reconcile-verdict-explicit
  - adr-write-then-ask-grim
  - adr-waiver-mechanisms
  - term-path-waiver
---

<!-- grim:status -->
<!-- /grim:status -->

# Finish-docs Reconciliation - Design

Date: 2026-07-30

## Problem

No component has ever travelled draft to current in this project. All 48
current components were born current during the adoption backfill, because the
mechanism that would move one - reconciliation at branch finish - does not
exist. Phase A refuses any spec referencing a draft, correctly, and leaves the
operator with no supported way to resolve that refusal.

Two rules the schema states normatively had no implementation. The supersede
cascade was never performed or checked, so a promoted component could leave its
predecessor live and render both decisions into the consumer view as fact. The
drafts-only edit rule was unenforced, because the transition check compares only
status and the touched-path guard deliberately skips a component whose own file
changed.

Separately, the touched-path guard fires on every release for
adr-dual-plugin-manifests, whose declared paths contain a version string that
changes for reasons the decision does not govern.

## Approach

A reconcile pass that takes an explicit verdict per draft and executes it, with
the diff winning on disagreement. Judgement stays with the agent; the script
owns the transaction and the audit trail.

Two scored agent baselines shaped this. An unaided agent passed six of eight
rubric lines on discipline alone, and the skilled run added exactly the two
lines the tooling exists for. The instruction budget therefore goes to refusals,
routes and printed output rather than to prose about how to judge - and a rule
that lives only in skill prose is not enforced at all, which is why the
never-built case became a tool refusal rather than a documented convention.

The alternative considered for validation was checking the proposed graph before
writing it. That is how the stamping pass accumulated eleven divergences from
grim across two review rounds, so this writes first and asks grim after.

## Decisions

- What the stamp records: adr-implemented-stamp-branch-finish
- Verdicts are explicit arguments: adr-reconcile-verdict-explicit
- Validation by writing then asking: adr-write-then-ask-grim
- Two waiver mechanisms, scoped differently: adr-waiver-mechanisms
- What a waiver is: term-path-waiver

## Out of scope

Mandatory dispositions for every note-worklist group, and a declared fast-path
flag for no-spec branches. The worklist ships as information only; the
touched-path guard already covers documented areas, and only seven of 48
components declare paths, so requiring a disposition per group would tax every
run for a bound that is mostly empty today.

Semantic comparison of diff content against component text remains excluded by
nongoal-semantic-drift-detection.
