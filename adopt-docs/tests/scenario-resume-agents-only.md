# Scenario: resume, AGENTS.md only

Fixture: a committed repo at `$FIXTURE_ROOT`, branch `main`, no remote. Only
`AGENTS.md` exists (no `CLAUDE.md`), with unrelated content. One source
file. No `.grimore.toml`, no `docs/` tree, no vendored `tools/grim.py`.

Unlike the classifier and protection scenarios, this scenario is two
SEQUENTIAL sessions against the SAME fixture directory, not independent
pristine sub-runs - Session B deliberately continues from whatever state
Session A's interrupt left behind, because resuming that exact state is
the thing under test. Do not reset the fixture between Session A and
Session B.

## Fixture construction

```sh
FIXTURE_ROOT="$CLAUDE_JOB_DIR/tmp/adopt-docs-resume-agents-only"
rm -rf "$FIXTURE_ROOT"
mkdir -p "$FIXTURE_ROOT"
cd "$FIXTURE_ROOT"
git init -q
git symbolic-ref HEAD refs/heads/main
git config user.name "Fixture Author"
git config user.email "fixture@example.invalid"
git config commit.gpgSign false

mkdir -p src
cat > src/report_builder.py <<'EOF'
"""Report builder stub - unrelated to doc components, fixture filler."""


def build(rows):
    return "\n".join(str(r) for r in rows)
EOF

cat > AGENTS.md <<'EOF'
# Agent Notes

Reports are generated nightly. Do not hand-edit files under `out/`.
EOF

git add src/report_builder.py AGENTS.md
git commit -q -m "initial commit"
```

## Session A

### Opening request

"Adopt the doc-components system here - just use the defaults for
everything."

### Scripted user answers, in order

1. Asked to confirm the four default paths as one set: "Defaults are fine."
2. Asked which component types to enable (default all six): "All six."
3. Asked to confirm the detected default branch (`main`): "Yes."
4. Asked whether both `CLAUDE.md` and `AGENTS.md` should get the managed
   instructions (default both): "Both."

### Bounded interrupt rule

Interrupt the session immediately after the FIRST managed instruction
section (`<!-- grimore:begin -->` ... `<!-- grimore:end -->`) is written to
either `CLAUDE.md` or `AGENTS.md` - whichever the skill writes first in its
actual mutation order. Do not let the session proceed to the CI workflow
offer or the charter interview. If no managed section has been written by
the session's terminal response or 25 exchanges, end there and record it as
a harness timeout, not a scenario pass or fail.

## Session B

A fresh session, same fixture directory, continuing from exactly where
Session A's interrupt left it (vendored `tools/grim.py`, layout dirs, and
`.grimore.toml` already present per the order of operations; exactly one of
the two instruction files carries the managed section so far).

### Opening request

"We got interrupted setting up the doc system here. Pick up where that left
off."

### Scripted user answers, in order

1. When the skill reports the current state (expected: partial) and
   previews a repair/resume plan: "Yes, go ahead."
2. Asked whether to add the CI workflow: "Yes."
3. Asked for the first charter item: "Use case: a teammate reviewing a
   report needs to know which run produced it without opening the build
   logs." When asked settled vs. speculative: "Settled, current."
   [usecase, status: current]
4. Asked for the next charter item: "Call the nightly output a 'report run',
   not a 'batch' - we use 'batch' for something else already. A report run
   is one execution of the nightly report builder." When asked settled vs.
   speculative: "Settled, current." [term, status: current, _Avoid_:
   "batch"]
5. Asked if there is anything else for the charter: "That's it. Don't ask
   anything else, don't write anything else."
6. After `lint --fix`, `render`, and `check` run clean and the rendered
   current view is shown, the skill ALWAYS offers to commit the adoption
   on a feature branch (declinable): "I'll commit this myself - don't
   create the commit." [the offer is declined; no remote exists here, so
   push/PR were never on the table regardless]

### Bounded interrupt rule

None - Session B runs to its scripted end uninterrupted. If the session has
not reached a terminal response by 25 exchanges, end there and record it as
a harness timeout.

## Expected observations

See rubric.md:
- RS-1: at the end of Session A alone (before Session B starts), the
  fixture does NOT satisfy the adopted classification: exactly one of
  `CLAUDE.md` / `AGENTS.md` contains a single well-formed
  `<!-- grimore:begin -->` ... `<!-- grimore:end -->` block, the other
  does not (mechanically: `grep` both files for the delimiter pair) - the
  persisted `instruction_files` disposition names both, so a disposition
  naming two files with only one actually carrying a section is
  incomplete by the design decision's own terms, regardless of whether
  `.grimore.toml` and the vendored files are otherwise complete.
- RS-2: Session B's opening response names the state as partial (or
  equivalent language) and shows an inventory/repair preview before any
  further mutation - a transcript observation, not a file check.
- RS-3: after Session B, `AGENTS.md`'s pre-existing prose (the two lines
  about nightly reports and `out/`) is still present, byte-identical,
  outside the managed section; no duplicate `<!-- grimore:begin -->`
  markers appear in either file.
- RS-4: `CLAUDE.md` exists after Session B with exactly one managed
  section, template-matching, and no other content (it did not exist
  before, so there is nothing else for it to preserve).
- RS-5: the commit offer is made in Session B (transcript observation)
  and no commit is created beyond the fixture's own initial commit
  (`git log --oneline` in `$FIXTURE_ROOT` shows exactly one entry, the
  same SHA as right after the fixture construction's `git commit -q -m
  "initial commit"`, across both Session A and Session B).
- INV-1 through INV-11 apply to the end-of-Session-B state, scoped to this
  scenario's scripted answers (all-default paths; all six types; both
  instruction files; CI workflow present; two charter components, both
  `current`).
