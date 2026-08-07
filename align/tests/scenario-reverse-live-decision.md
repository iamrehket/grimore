# Scenario: design session that reverses a live decision

Fixture: an adopting project at <fixture-root> containing
doc-components/SCHEMA.md and doc-components/templates/ copied from this
repo, a `.grimore.toml` declaring the default paths, an empty docs/specs/,
and a store holding one live component with a hand-assembled rendered view.
The fixture carries no grim and is not a git repository, as in
scenario-ingest-cache.

`.grimore.toml`:

    [grimore]
    components = "docs/components"
    current = "docs/current"
    specs = "docs/specs"
    plans = "docs/plans"
    default_branch = "main"

`docs/components/adr/nightly-batch-sync.md`:

    ---
    id: adr-nightly-batch-sync
    type: adr
    status: current
    date: 2026-06-20
    ---

    # Sync runs as a nightly batch

    Upstream rate limits made per-change sync calls a support burden, and
    nobody needed same-day freshness. Sync therefore runs as one nightly
    batch at 02:00. Trade-off accepted: data is up to a day stale, taken
    for cost over freshness.

`docs/current/decisions.md` - a hand-assembled stand-in for the rendered
view (the fixture has no grim to render with; scoring uses lint, which does
not byte-compare it):

    # Decisions

    ## Sync runs as a nightly batch

    Upstream rate limits made per-change sync calls a support burden, and
    nobody needed same-day freshness. Sync therefore runs as one nightly
    batch at 02:00. Trade-off accepted: data is up to a day stale, taken
    for cost over freshness.

`docs/current/glossary.md`:

    # Glossary

    (no terms settled yet)

The agent under test is asked: "Our customers now watch dashboards during
the day - let's design a streaming sync to replace the nightly batch."

Scripted user answers, in order, regardless of question wording:

1. First substantive answer: "Purpose is freshness now. Dashboards during
   business hours made the staleness visible; cost is no longer the
   constraint it was."
2. "To be clear: we are replacing the nightly batch sync with streaming
   sync. The old decision - adr-nightly-batch-sync - no longer holds.
   Streaming sync, settled, trade-off accepted: we take on the rate-limit
   engineering to get freshness."
   [Crystallization moment A: an existing current component is reversed.
   The new draft must carry the supersedes: edge.]
3. When approaches are proposed: pick whichever the agent recommends.
4. If asked about migration, rollout, or the old batch job's retirement:
   "Out of scope for this session."
5. When shown a spec draft or asked to review: "Looks right. Wrap up with
   whatever is left over. Do not write or edit any component files from
   here on - if something is not captured by now, it is lost."

Answer 2 is the point of the scenario. The reversal of a decision that
predates the session must be captured inline as a NEW draft carrying
`supersedes: [adr-nightly-batch-sync]` - the wrong moves are editing
nightly-batch-sync.md in place (only drafts may be edited), flipping its
status (the edge takes effect at promotion, and this skill never promotes),
or writing the draft without the edge (the reversal then exists nowhere the
graph can see). Answer 4 is a distractor: session scoping is not a product
exclusion and mints no nongoal. Answer 5 is the same batch-capture trap as
scenario-ingest-cache.

## Run methodology (harness instructions, not user dialogue)

The session agent must end its final message with an ordered list of every
file it wrote, each annotated with the scripted answer number that preceded
the write, as in scenario-ingest-cache. The runner records this list
alongside the transcript; post-hoc file mtimes alone do not satisfy the
timing line.

Score with `rubric-reverse-live-decision.md`.
