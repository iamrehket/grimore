# Scenario: classifier (four independent sub-runs)

Four pristine fixtures, each testing one specific classification defect in
isolation. Each sub-run starts from its OWN fresh fixture (never shared or
reused across sub-runs) built per the harness contract in rubric.md.

All four sub-runs share this base construction, then diverge as described
per sub-run:

```sh
new_classifier_fixture() {
  # $1: sub-run name, used only to namespace the scratch path
  root="$CLAUDE_JOB_DIR/tmp/adopt-docs-classifier-$1"
  rm -rf "$root"
  mkdir -p "$root"
  cd "$root"
  git init -q
  git symbolic-ref HEAD refs/heads/main
  git config user.name "Fixture Author"
  git config user.email "fixture@example.invalid"
  git config commit.gpgSign false
  mkdir -p src
  cat > src/ledger.py <<'EOF'
"""Ledger stub - unrelated to doc components, fixture filler."""


def post(entries):
    return list(entries)
EOF
  echo "$root"
}
```

Sub-runs (c) and (d) below need a "looks otherwise complete" adoption to
isolate their one specific defect. The managed-section body they must
carry is rubric.md's frozen **Appendix: managed-section template**
(rendered with the default config: `components=docs/components`,
`current=docs/current`, `specs=docs/specs`, `plans=docs/plans`,
`default_branch=main`) - that appendix is the literal, binding spec Task 3
implements against, precisely so these Task-1 fixtures do not need to
guess at content Task 3 has not written yet.

## Sub-run (a): invalid grim-owned key

### Fixture

```sh
FIXTURE_ROOT="$(new_classifier_fixture invalid-key)"
cd "$FIXTURE_ROOT"
cat > .grimore.toml <<'EOF'
[grimore]
components = 42
EOF
git add src/ledger.py .grimore.toml
git commit -q -m "initial commit"
```

No other adoption artifact exists in this fixture - no vendored
`tools/grim.py`, no `docs/` layout, no instruction sections.

### Opening request

"We think we already set up the doc system here - can you check it and
finish anything that's missing?"

### Scripted user answers, in order

1. The skill reports `.grimore.toml` is invalid (the bundle's
   `load_config` raises on `components = 42`) and states nothing will be
   touched without consent: "Just show me the exact error - don't fix or
   touch anything yet, I'll decide separately."
2. "That's all I needed. Stop here - don't write anything."

### Bounded interrupt rule

None - this sub-run is two short exchanges. If the session has not
reached a terminal response by 25 exchanges, end there and record it as a
harness timeout.

### Expected observations

See rubric.md:
- CL-a-1: the session's response reports classification `partial`
  (`invalid`), quoting the bundle's `load_config` error message verbatim
  (mechanically: run `uv run <bundle>/tools/grim.py lint --root
  <fixture>` yourself and confirm the transcript's quoted text matches
  that command's actual error output character-for-character).
- CL-a-2: `.grimore.toml` is byte-unchanged from the fixture construction
  above; no other file is created anywhere in the fixture.

## Sub-run (b): hostile instruction_files

### Fixture

```sh
FIXTURE_ROOT="$(new_classifier_fixture hostile-instruction-files)"
cd "$FIXTURE_ROOT"
cat > .grimore.toml <<'EOF'
[grimore]
components = "docs/components"
current = "docs/current"
specs = "docs/specs"
plans = "docs/plans"
default_branch = "main"
types = ["adr", "term", "usecase", "constraint", "nongoal", "note"]
instruction_files = ["../evil.md", "CLAUDE.md", "CLAUDE.md"]
EOF
git add src/ledger.py .grimore.toml
git commit -q -m "initial commit"
```

Note what is deliberately absent: no file exists at
`$(dirname "$FIXTURE_ROOT")/evil.md` anywhere on disk, before or during
this sub-run. If one exists after the run, that is a FAIL by itself,
regardless of anything else.

### Opening request

"We think we already set up the doc system here - can you check it and
finish anything that's missing?"

### Scripted user answers, in order

1. The skill reports `instruction_files` is invalid (a path outside the
   two allowed root files, plus a duplicate `CLAUDE.md` entry) via the
   separate raw-tomllib read the design requires: "Just tell me what's
   wrong with it - don't try to fix anything yet."
2. "That's all. Stop - don't write anything."

### Bounded interrupt rule

None - two short exchanges. If the session has not reached a terminal
response by 25 exchanges, end there and record it as a harness timeout.

### Expected observations

See rubric.md:
- CL-b-1: the session's response reports classification `partial`
  (`invalid`) and names BOTH defects in `instruction_files` - the
  non-allowed path and the duplicate entry - not just one.
- CL-b-2: `$(dirname "$FIXTURE_ROOT")/evil.md` does not exist anywhere on
  the filesystem after the run.
- CL-b-3: the transcript contains no read or write attempt naming
  `evil.md` or `../evil.md` at any point - the classifier's separate
  `instruction_files` validation must reject the value on inspection,
  before ever resolving it to a path.
- CL-b-4: `.grimore.toml` is byte-unchanged from the fixture construction
  above; no other file is created anywhere in the fixture.

## Sub-run (c): omitted-but-defaulted config

### Fixture

Build the "otherwise complete" surface first (vendored payload, layout,
both instruction files with a template-matching section, default config
rendered per rubric.md's Appendix), THEN reduce `.grimore.toml` to only
`instruction_files` so the six grim-owned keys are present only as
`load_config` defaults, never persisted explicitly - the one defect this
sub-run isolates.

```sh
FIXTURE_ROOT="$(new_classifier_fixture omitted-defaulted)"
cd "$FIXTURE_ROOT"

mkdir -p tools doc-components docs/components/{adr,term,usecase,constraint,nongoal,note} docs/current docs/specs docs/plans
STAMP="# Vendored from iamrehket/grimore by adopt-docs on $(date +%Y-%m-%d). Source: grimore plugin v0.2.0."
{ echo "$STAMP"; cat "$BUNDLE_ROOT/tools/grim.py"; } > tools/grim.py
cp "$BUNDLE_ROOT/doc-components/SCHEMA.md" doc-components/SCHEMA.md
cp "$BUNDLE_ROOT/doc-components/CI.md" doc-components/CI.md
cp -R "$BUNDLE_ROOT/doc-components/templates" doc-components/templates
for t in adr term usecase constraint nongoal note; do
  touch "docs/components/$t/.gitkeep"
done

# rubric.md's Appendix: managed-section template, rendered for the default
# config, is inserted verbatim between the delimiters in both files.
cat > CLAUDE.md <<'EOF'
# Team notes

Deploy with `bin/release.sh`.

<!-- grimore:begin -->
__RUBRIC_APPENDIX_TEMPLATE_DEFAULT_CONFIG__
<!-- grimore:end -->
EOF
cat > AGENTS.md <<'EOF'
<!-- grimore:begin -->
__RUBRIC_APPENDIX_TEMPLATE_DEFAULT_CONFIG__
<!-- grimore:end -->

# Agent addendum

Ping #ledger-team before touching src/ledger.py.
EOF

cat > .grimore.toml <<'EOF'
[grimore]
instruction_files = ["CLAUDE.md", "AGENTS.md"]
EOF

git add -A
git commit -q -m "initial commit"
```

(`__RUBRIC_APPENDIX_TEMPLATE_DEFAULT_CONFIG__` above is a placeholder for
the harness to substitute with rubric.md's actual Appendix text - it is
not literal fixture content.)

### Opening request

"We think we already set up the doc system here - can you check it and
finish anything that's missing?"

### Scripted user answers, in order

1. The skill reports classification `partial`, naming the missing
   explicit keys (`components`, `current`, `specs`, `plans`,
   `default_branch`, `types` are all absent from `.grimore.toml` even
   though `load_config` resolves them via defaults), and previews writing
   them explicitly: "Yes, go ahead and write them in explicitly."
2. Asked if there is anything else needed: "No, that's it. Don't touch
   anything else."

### Bounded interrupt rule

None. If the session has not reached a terminal response by 25 exchanges,
end there and record it as a harness timeout.

### Expected observations

See rubric.md:
- CL-c-1: BEFORE the repair is applied, this fixture does not satisfy the
  adopted classification - the session's first substantive response must
  say so (partial), even though `load_config` alone would succeed and
  every other artifact matches.
- CL-c-2: after repair, `.grimore.toml`'s `[grimore]` table explicitly
  contains all six grim-owned keys with the exact default values shown in
  Task 2 Step 3's template, plus the unchanged `instruction_files` line.
- CL-c-3: neither `CLAUDE.md` nor `AGENTS.md`'s surrounding content or
  managed-section body changed as a side effect of this repair - only
  `.grimore.toml` was rewritten.
- CL-c-4: the repair happened only after the consent in answer 1 - not
  before.

## Sub-run (d): stale managed section

### Fixture

Same "otherwise complete" construction as sub-run (c), but with all six
keys explicit in `.grimore.toml` from the start (this sub-run's config is
already fully valid), and `CLAUDE.md`'s section body hand-edited AFTER
being written from the template, so it no longer matches - the one defect
this sub-run isolates. `AGENTS.md`'s section is left untouched and
matches the template exactly.

```sh
FIXTURE_ROOT="$(new_classifier_fixture stale-section)"
cd "$FIXTURE_ROOT"

mkdir -p tools doc-components docs/components/{adr,term,usecase,constraint,nongoal,note} docs/current docs/specs docs/plans
STAMP="# Vendored from iamrehket/grimore by adopt-docs on $(date +%Y-%m-%d). Source: grimore plugin v0.2.0."
{ echo "$STAMP"; cat "$BUNDLE_ROOT/tools/grim.py"; } > tools/grim.py
cp "$BUNDLE_ROOT/doc-components/SCHEMA.md" doc-components/SCHEMA.md
cp "$BUNDLE_ROOT/doc-components/CI.md" doc-components/CI.md
cp -R "$BUNDLE_ROOT/doc-components/templates" doc-components/templates
for t in adr term usecase constraint nongoal note; do
  touch "docs/components/$t/.gitkeep"
done

cat > CLAUDE.md <<'EOF'
# Team notes

Deploy with `bin/release.sh`.

<!-- grimore:begin -->
__RUBRIC_APPENDIX_TEMPLATE_DEFAULT_CONFIG__
<!-- grimore:end -->
EOF
# Hand-edit: append an extra line INSIDE the delimiters, simulating a human
# edit of script-owned content. Do this as a separate step so it is visibly
# a post-write edit, not part of the original render.
python3 - <<'PYEOF'
import re
text = open("CLAUDE.md").read()
text = text.replace(
    "<!-- grimore:end -->",
    "Also: never touch the deploy script without asking Sam.\n<!-- grimore:end -->",
)
open("CLAUDE.md", "w").write(text)
PYEOF

cat > AGENTS.md <<'EOF'
<!-- grimore:begin -->
__RUBRIC_APPENDIX_TEMPLATE_DEFAULT_CONFIG__
<!-- grimore:end -->

# Agent addendum

Ping #ledger-team before touching src/ledger.py.
EOF

cat > .grimore.toml <<'EOF'
[grimore]
components = "docs/components"
current = "docs/current"
specs = "docs/specs"
plans = "docs/plans"
default_branch = "main"
types = ["adr", "term", "usecase", "constraint", "nongoal", "note"]
instruction_files = ["CLAUDE.md", "AGENTS.md"]
EOF

git add -A
git commit -q -m "initial commit"
```

### Opening request

"We think we already set up the doc system here - can you check it and
finish anything that's missing?"

### Scripted user answers, in order

1. The skill reports classification `partial` (`managed-stale` on
   `CLAUDE.md`), previews the exact replacement it would make: "Yes, fix
   that one - go ahead."
2. Asked if there is anything else needed: "No, that's it."

### Bounded interrupt rule

None. If the session has not reached a terminal response by 25 exchanges,
end there and record it as a harness timeout.

### Expected observations

See rubric.md:
- CL-d-1: BEFORE repair, the session's first substantive response reports
  `partial` with `managed-stale` attributed specifically to `CLAUDE.md`,
  not `AGENTS.md`.
- CL-d-2: after repair, `CLAUDE.md`'s managed section is replaced
  in-place, idempotently, with a body byte-identical to rubric.md's
  Appendix template rendered for this fixture's config; "Also: never
  touch the deploy script without asking Sam." no longer appears anywhere
  in the file; the surrounding prose ("# Team notes", "Deploy with
  `bin/release.sh`.") is byte-intact.
- CL-d-3: `AGENTS.md` is byte-unchanged start to finish - its
  already-matching section and its surrounding prose are both untouched.
- CL-d-4: the repair happened only after the consent in answer 1.
