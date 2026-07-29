# Baseline: RED run, scenario-shipped-branch

Date: 2026-07-29. Sonnet subagent, no access to `finish-docs/`, given only the
fixture and the request. Ran single-shot, asked no questions, and used the
scripted answers as supplied in the prompt.

## Rubric scoring

1. PASS - wrote `implemented: "2026-07-29 (PR #47)"`, quoted. It found the
   YAML-comment truncation gotcha by reading `doc-components/SCHEMA.md`
   unprompted and cited it as the reason for quoting.
2. PASS - left `2026-07-21-column-order.md` unstamped and did not touch
   `adr-column-order-config`.
3. PASS - named the draft component in its final message and explicitly framed
   the spec as not done.
4. PASS - banners in the spec and its plan produced by `grim lint --fix`.
5. PASS - `2026-07-21-column-order.md` derived correctly.
6. PASS - `grim check` exits 0.
7. **FAIL** - no stamper was invoked; there is none without the skill.
8. **FAIL** - the `implemented:` line was written by hand, which
   `doc-components/SCHEMA.md` forbids ("added once by finish-docs; never by
   hand").

## Verdict: FAIL (rubric requires all 8)

## What this baseline actually establishes, which is not what was expected

A diligent agent with no skill got the **semantics** right: it read the schema,
quoted the stamp correctly, refused the draft spec for the right reason,
reported the refusal, and let the deriver write the banners. Six of eight lines
passed on discipline alone.

The two failures are both "wrong route to a right answer" - it hand-wrote a
stamp the schema reserves for a tool. That matters, but it is a narrower claim
than "the skill is necessary."

So the honest reading is that this skill's marginal value on the happy path is
**modest**, and concentrated in three places:

- The stamp is written by something that validates it, rather than by an agent
  that happened to read carefully. This run got the quoting right; nothing in
  the run would have caught a calendar-invalid date, a non-numeric PR number,
  a component whose status is not a real status, or an existing malformed
  stamp - all of which the stamper now refuses via its grim preflight.
- The refusal is enforced rather than discretionary. This agent chose well, and
  said it would have refused "regardless of instructions". A less careful one
  facing pressure to finish has nothing stopping it.
- The idempotency and ordering rules are stated once rather than rediscovered.

The scenario should be hardened before it is treated as a real gate: the draft
component here is obviously unfinished, which makes the refusal easy. A harder
scenario would make stamping the refusable spec look reasonable.

## Unscripted finding worth keeping

The baseline agent raised a question the skill does not answer: it stamped
while PR 47 was still an unmerged draft, and flagged that if the project's
convention is `implemented` == merged, the stamp is premature. Neither
`SKILL.md` nor `doc-components/SCHEMA.md` says which event the stamp records -
work complete, pull request opened, or merged. That ambiguity is real and
currently resolved by whoever runs the tool.

## Not yet run

The GREEN run - same scenario, same rubric, agent with the skill - has not been
performed. Until it has, this apparatus records what an unaided agent does and
does not yet demonstrate that the skill changes the outcome.
