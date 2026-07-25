---
name: align
description: Use when brainstorming or designing a feature, or when someone says "align on", "let's design", or "start a spec". In a project adopting doc components, this replaces superpowers:brainstorming: it interviews one question at a time and captures glossary terms, ADRs, use cases, constraints, and non-goals inline - as draft components - the moment each one settles, then produces a spec that indexes what was captured.
---

# Align: Interview With Inline Capture

Turn an idea into a spec through one-question-at-a-time dialogue, the same
way superpowers:brainstorming does - but in a project that stores its
decisions as components, capture cannot wait for a write-up at the end. It
happens the instant something settles, mid-conversation, or it doesn't
happen at all.

## Session flow

1. **Orient.** Before asking anything, look at what already exists. If
   `docs/current/` (or whatever the project's `.grimore.toml` configures as
   the current dir) exists, read it - glossary first: settled terminology
   in `current/glossary.md` governs the words used for the rest of the
   interview and for anything captured during it. Read `.grimore.toml` for
   the project's configured paths (components dir, specs dir); with no
   config, fall back to the defaults, `docs/components/` and `docs/specs/`.

2. **Interview.** Ask one question at a time - never a wall of questions in
   a single message. Prefer multiple-choice (2-4 concrete options,
   AskUserQuestion-style) over open-ended; a decision is easier to make
   from options than from a blank prompt. Cover, in rough order: purpose
   (why now, what hurts), actors and use cases, constraints (hard limits
   accepted), success criteria, and explicit exclusions. The order is a
   guide, not a script - follow the user's energy; if they volunteer a
   constraint while answering a purpose question, take it there. The
   one-question-at-a-time rule does not bend, even when the order does.

3. **Approaches.** Once purpose, constraints, and success criteria are
   reasonably clear, propose 2-3 concrete approaches. Make a recommendation
   and name the trade-off each one accepts - don't hand over a menu without
   an opinion. Let the user choose via another multiple-choice question.

4. **Spec.** Copy `doc-components/templates/spec.md` into the project's
   configured specs dir under a dated filename. The `components:`
   frontmatter lists every component captured this session. The Decisions
   section is an index: one line per captured component ID, covering all
   of them - terms and non-goals included, not only ADRs (for example,
   "Slug IDs instead of sequential ADR numbers: adr-slug-ids") - and never
   restating what the component says; the component is canonical, this
   section only points at it. Run the lint step described under Inline
   capture below before presenting this draft to the user.

5. **Review loop.** Dispatch a spec-reviewer subagent with the spec and the
   components it references; see Spec review loop below. Fix real issues
   and re-run until it comes back clean or the user overrides, then get the
   user's sign-off on the spec.

6. **Handoff.** Offer superpowers:writing-plans to turn the signed-off spec
   into an implementation plan. The plan is authored from
   `doc-components/templates/plan.md` and carries `spec:` frontmatter
   pointing at the spec just written; align does not author the plan
   itself.

## Inline capture (the point of this skill)

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
     classifier noun the user didn't say ("window", "policy", "limit",
     "mode", "config" and the like).
   - Keep it short - 2 to 4 words. Drop scope/release qualifiers ("v1",
     "for now", "at first") and negation particles ("no", "not",
     "won't") even when the user said them: status: draft already
     scopes the decision, and a nongoal's type already signals the
     exclusion, so restating either in the slug is redundant.
   - When the user gives both a measurement and a name for the state,
     the name wins - use it, with the measurement following, not a
     measurement-only slug.

   For example: "we'll use exponential backoff instead of a fixed delay
   for retries" slugs as exponential-backoff-retries (their own terms,
   no invented category noun); "let it run degraded for up to 6 hours
   before restarting" slugs as run-degraded-6h (the name "degraded" plus
   the measurement "6h" that follows it, not degraded-mode-6h or
   6h-degraded-window).
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
run `uv run tools/grim.py lint --root <project-root>` (the project
root, not the components dir) after the last capture and BEFORE
presenting the spec draft, and fix what it reports; if not, SCHEMA.md
is the checklist.

## Spec review loop

Before asking the user to sign off on the spec, dispatch a subagent -
give it the spec, the draft components it references, and the session
goal - with this prompt:

> Review this spec and its referenced draft components against
> doc-components/SCHEMA.md and the session goal below. Reply with exactly
> three sections: Status (clean / needs work), Issues (numbered, each with
> the file and line it concerns), Recommendations (advisory improvements,
> clearly separated from Issues). Do not edit files.

The reviewer is advisory, not a gate you can pass by ignoring it: fix every
Issue. For each Recommendation, decide deliberately - adopt it or leave it
- rather than silently doing either. Re-dispatch the reviewer after fixes
and repeat until Status reads clean, or the user explicitly overrides.
Never self-certify - the agent running the interview does not get to
declare its own spec clean; that judgment belongs to the subagent. Only
after a clean status, or an explicit user override, does the spec move to
the user for sign-off.
