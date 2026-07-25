# Scenario: ingest cache design session

Fixture: an empty project at <fixture-root> containing only
doc-components/SCHEMA.md and doc-components/templates/ copied from this
repo, plus an empty docs/components/ tree and an empty docs/specs/.

The agent under test is asked: "I want to add a caching layer to our
ingest pipeline so repeated fetches stop hammering the upstream API."

Scripted user answers, in order, regardless of question wording:

1. First substantive answer: "Purpose is cost control, not latency. The
   upstream bills per call." If asked a multiple-choice question, pick
   the option closest to cost control.
2. "Call the stored thing a 'fetch record'. Not 'cache entry' - we
   already use 'entry' for ledger entries. Definition: the stored
   response for one upstream request, keyed by request signature."
   [Crystallization moment A: a term is settled. term-fetch-record.]
3. "Staleness: serve records up to 24h old, then refetch. We accept
   stale data for a day because the upstream data changes weekly.
   That's a real trade-off - cost over freshness - and it's hard to
   reverse once consumers rely on it. Decided."
   [Crystallization moment B: passes the ADR bar. adr-serve-stale-24h.]
4. "Out of scope: cache invalidation API. We will not build manual
   purge in v1."
   [Crystallization moment C: a non-goal. nongoal-manual-purge.]
5. When approaches are proposed: pick whichever the agent recommends.
6. When shown a spec draft or asked to review: "Looks right. Wrap up
   with whatever is left over. Do not write or edit any component files
   from here on - if something is not captured by now, it is lost."

The final instruction is the trap: batch-mined capture at session end
is forbidden by the script, so only inline capture survives.

## Run methodology

The session agent must end its final message with an ordered list of
every file it wrote, each annotated with the scripted answer number
that preceded the write. The runner records this list alongside the
transcript as the timing evidence for rubric line 6 - post-hoc file
mtimes alone do not satisfy that line.
