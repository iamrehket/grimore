# Scenario: neither-restricted (nested bundle, restricted types)

"Neither" refers to instruction files, not to the fixture being unusual -
it is a normal committed repo, branch `main`, no remote. NEITHER
`CLAUDE.md` NOR `AGENTS.md` exists yet. One source file. Enabled component
types for this run: `["adr", "term", "usecase", "constraint"]` -
`nongoal` and `note` are disabled.

The load-bearing twist: for this scenario ONLY, the frozen cache bundle
(the skill source; see rubric.md's Bundle contract) is copied to a path
NESTED INSIDE the fixture's own working tree, after the fixture's initial
commit, untracked. The bundle carries no `.git` of its own, so
`git -C <skill-dir> rev-parse --show-toplevel` run from inside it walks up
past the bundle root and lands on the FIXTURE's own `.git` - a different
root than the bundle's. This is exactly the case the provenance identity
ladder's toplevel-verification rule exists to catch: a naive
`rev-parse HEAD` would silently stamp the fixture's own commit as if it
were grimore's. The correct behavior falls through to rung 2 (the bundle's
own `.claude-plugin/plugin.json`) and stamps `grimore plugin v0.2.0`.

## Fixture construction

```sh
FIXTURE_ROOT="$CLAUDE_JOB_DIR/tmp/adopt-docs-neither-restricted"
rm -rf "$FIXTURE_ROOT"
mkdir -p "$FIXTURE_ROOT"
cd "$FIXTURE_ROOT"
git init -q
git symbolic-ref HEAD refs/heads/main
git config user.name "Fixture Author"
git config user.email "fixture@example.invalid"
git config commit.gpgSign false

mkdir -p src
cat > src/label_printer.py <<'EOF'
"""Label printer stub - unrelated to doc components, fixture filler."""


def render_label(sku):
    return f"LABEL:{sku}"
EOF

git add src/label_printer.py
git commit -q -m "initial commit"

# Nest the frozen bundle inside the fixture's own tree, AFTER the initial
# commit, untracked - it never becomes part of the fixture's git history.
mkdir -p .grimore-cache
cp -R "$BUNDLE_ROOT"/. .grimore-cache/grimore/
```

`$BUNDLE_ROOT` is the frozen bundle directory built in Task 1 Step 1 (see
rubric.md). The skill under test is invoked with its source resolved from
`$FIXTURE_ROOT/.grimore-cache/grimore/adopt-docs`, not from any path outside
the fixture.

## Opening request

"Set up the doc-components system, but we only want ADRs, terms, use
cases, and constraints - no non-goals, no notes."

## Scripted user answers, in order

1. Asked to confirm the four default paths as one set: "Defaults are
   fine."
2. Asked which component types to enable: "Just adr, term, usecase, and
   constraint. Leave nongoal and note off."
3. Asked to confirm the detected default branch (`main`): "Yes."
4. Asked whether both `CLAUDE.md` and `AGENTS.md` should get the managed
   instructions (default both): "Both."
5. Asked whether to add the CI workflow: "Yes."
6. Asked for the first charter item: "Use case: a warehouse picker needs to
   reprint a damaged label without asking an engineer to run a script."
   When asked settled vs. speculative: "Settled, current."
   [usecase, status: current]
7. When the charter interview reaches the non-goals section: expect it to
   be skipped with a one-line statement, since `nongoal` is disabled. Before
   that skip statement is even delivered, or immediately after (whichever
   the flow allows), volunteer this unprompted: "For what it's worth, we're
   deliberately not going to support printing labels in bulk from this
   tool - people keep asking, we're saying no." This is volunteered
   material for a disabled type - it must be recorded (capture log / final
   summary) but never written as a component.
8. Asked if there is anything else for the charter: "That covers it. Don't
   ask anything else, don't write anything else."
9. After `lint --fix`, `render`, and `check` run clean and the rendered
   current view is shown, the skill ALWAYS offers to commit the adoption
   on a feature branch (declinable): "I'll commit this myself - don't
   create the commit." [the offer is declined; no remote exists here, so
   push/PR were never on the table regardless]

## Bounded interrupt rule

None - this scenario runs to its scripted end uninterrupted. If the
session has not reached a terminal response by 25 exchanges, end there and
record it as a harness timeout, not a scenario pass or fail.

## Expected observations

See rubric.md:
- NR-1: both `CLAUDE.md` and `AGENTS.md` are created (neither existed
  before), each with exactly one managed section, template-matching.
- NR-2: the non-goals charter section is skipped with a one-line
  statement naming it as disabled - a transcript observation.
- NR-3: the volunteered bulk-printing remark appears in the capture log
  and/or the final adoption summary message (transcript observation), but
  no `nongoal/` directory and no `nongoal-*` component file exist anywhere
  under the configured components dir.
- NR-4: the layout only creates directories for the four enabled types
  (`adr/`, `term/`, `usecase/`, `constraint/`) - no `nongoal/`, no `note/`.
- NR-5: the vendored `tools/grim.py` stamp line reads exactly
  `Source: grimore plugin v0.2.0` - NOT a bare commit SHA, and NOT the
  fixture's own initial-commit SHA under any label. This is the scenario's
  load-bearing assertion: it is a FAIL if the stamp contains any git commit
  hash at all.
- NR-6: `uv run <target>/tools/grim.py render --root <target>` (using the
  target's now-vendored copy) produces a non-empty
  `<current>/charter.md` containing the picker use case; `check --root
  <target>` exits 0.
- NR-7: the commit offer is made (transcript observation) and no commit
  is created beyond the fixture's own initial commit (`git log --oneline`
  in `$FIXTURE_ROOT` shows exactly one entry, the same SHA as right after
  the fixture construction's `git commit -q -m "initial commit"`).
- INV-1 through INV-11 apply, scoped to this scenario's scripted answers
  (default paths; types `adr, term, usecase, constraint` only; both
  instruction files; CI workflow present; one charter component,
  `usecase`, `current`).
