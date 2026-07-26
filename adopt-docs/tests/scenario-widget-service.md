# Scenario: widget-service (primary)

Fixture: a committed repo at `$FIXTURE_ROOT`, branch `main`, no remote. Both
`CLAUDE.md` and `AGENTS.md` already exist with distinct, unrelated content
(neither mentions grimore or doc components). One source file. No
`.grimore.toml`, no `docs/` tree, no vendored `tools/grim.py`.

## Fixture construction

```sh
FIXTURE_ROOT="$CLAUDE_JOB_DIR/tmp/adopt-docs-widget-service"
rm -rf "$FIXTURE_ROOT"
mkdir -p "$FIXTURE_ROOT"
cd "$FIXTURE_ROOT"
git init -q
git symbolic-ref HEAD refs/heads/main
git config user.name "Fixture Author"
git config user.email "fixture@example.invalid"
git config commit.gpgSign false

mkdir -p src
cat > src/widget_queue.py <<'EOF'
"""Widget queue worker - unrelated to doc components, just fixture filler."""


def drain(queue):
    while queue:
        yield queue.pop(0)
EOF

cat > CLAUDE.md <<'EOF'
# Widget Service Notes

Run tests with `make test`. Deploy via the `deploy.sh` script in `bin/`.
Do not touch `legacy/` without asking in #widget-service.
EOF

cat > AGENTS.md <<'EOF'
# Agent Notes (widget-service)

This service owns the widget queue. Prefer small PRs. CI runs on every push.
EOF

git add src/widget_queue.py CLAUDE.md AGENTS.md
git commit -q -m "initial commit"
```

The skill source for this run is the frozen cache bundle (see rubric.md's
Bundle contract) invoked from outside `$FIXTURE_ROOT` - not nested inside it.

## Opening request

"We want to start using grimore's doc system in this repo. Set it up."

## Scripted user answers, in order

1. Asked to confirm the four default paths as one set (components, current,
   specs, plans), with the option to override any of them: "Those are fine,
   except put specs under `docs/design/specs` instead of the default."
2. Asked which component types to enable (default all six): "Keep all six
   enabled."
3. Asked to confirm the detected default branch (`main`): "Yes, main is
   right."
4. Asked whether both `CLAUDE.md` and `AGENTS.md` should get the managed
   instructions (default both, at most one may be declined): "Both, please -
   we use both harnesses."
5. Asked whether to add the CI workflow: "Yes, add it."
6. Asked for the first charter item: "Use case: an on-call engineer needs to
   see why the widget queue backed up last night without reading source."
   When asked whether that is settled now or still speculative: "Settled -
   ship it as a current use case, not a draft." [usecase, status: current]
7. Asked for the next charter item: "Constraint: this doc system must never
   require a network call to build - offline-only, full stop." When asked
   settled vs. speculative: "That's a hard limit we're committing to right
   now. Settled, current." [constraint, status: current]
8. Asked for the next charter item: "One more, though I'm not sure yet - we
   might exclude auto-generated API reference pages from this system.
   Still kicking that around." When asked settled vs. speculative: "Don't
   lock that in - speculative, draft." [nongoal, status: draft]
9. Asked for the next charter item: "Let's call the rendered output a
   'current view', not a 'live doc' - we already use 'live' for something
   else. A current view is the rendered, agent-facing snapshot of what's
   true right now." When asked settled vs. speculative: "Settled, current."
   [term, status: current, _Avoid_: "live doc"]
10. Asked if there is anything else for the charter: "That's everything.
    Don't ask me anything else and don't write anything else - we're done."
    [final message; refuses further capture work]
11. After `lint --fix`, `render`, and `check` run clean and the rendered
    current view is shown, the skill ALWAYS offers to commit the adoption
    on a feature branch (declinable): "I'll commit this myself - don't
    create the commit." [the offer is declined; no remote exists here, so
    push/PR were never on the table regardless]

## Bounded interrupt rule

None - this scenario runs to its scripted end uninterrupted. If the
session has not reached a terminal response by 25 exchanges, end the run
there and record it as a harness timeout, not a scenario pass or fail.

## Expected observations

No GitHub remote exists, so the entire merge-discipline / branch-protection
surface must degrade to documented-only per the design decision: no `gh`
invocation of any kind should appear anywhere in the transcript for this
scenario, and every `gh`-invoking code path is unreachable by construction
here (no `stub-gh` is placed on `PATH` for this scenario - if anything tries
to run `gh`, it will fail with a plain "command not found", which itself is
evidence the skill did not gate on remote absence correctly).

See rubric.md:
- INV-1 through INV-11 apply in full, scoped to this scenario's scripted
  answers (specs at `docs/design/specs`; all six types enabled; both
  instruction files; CI workflow present).
- WS-1 through WS-7 (this scenario's specific assertions, below).
