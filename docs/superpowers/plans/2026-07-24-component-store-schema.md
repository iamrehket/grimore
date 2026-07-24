# Component Store Schema + Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the doc-components schema reference, authoring templates, and worked example fixtures that every later grimore issue (IAM-38 lint, IAM-39 align, IAM-40 render) builds against.

**Architecture:** Pure documentation artifacts in a new `doc-components/` product directory — a schema reference (SCHEMA.md), one authoring template per component type plus spec/plan templates (`templates/`), and one worked example per type (`examples/`) that doubles as the fixture set for IAM-38's test suite. No Python code beyond throwaway verification one-liners.

**Tech Stack:** Markdown with YAML frontmatter; `uv run --with pyyaml` for verification commands (repo convention: uv-run single-file tooling).

**Linear:** IAM-37. **Spec:** `docs/superpowers/specs/2026-07-24-doc-components-design.md` — the Component store, Specs and plans, and Body formats sections are the requirements; on any disagreement the spec wins.

## Global Constraints

- Component types are exactly: `adr`, `term`, `usecase`, `constraint`, `nongoal`, `note`. No others.
- Statuses are exactly: `draft`, `current`, `superseded`. No others (`rejected` is deferred post-v1).
- IDs are `<type>-<slug>`, slug matching `[a-z0-9][a-z0-9-]*`; filename is `<slug>.md`; IDs never reused or renumbered.
- Legal transitions only: `draft -> current`, `draft -> superseded`, `current -> superseded`.
- "Live" means `status: current` only.
- Component bodies contain no file paths or code snippets in prose; machine-readable `paths:` frontmatter carries path references (note/adr only).
- Dates are ISO `YYYY-MM-DD`.
- Banner delimiters are exactly `<!-- grim:status -->` and `<!-- /grim:status -->`.
- All new files live under `doc-components/`; nothing in this plan touches `docs/current/` (that directory is created by grim render in IAM-40, not by hand).

---

### Task 1: Schema reference (SCHEMA.md)

**Files:**
- Create: `doc-components/SCHEMA.md`

**Interfaces:**
- Consumes: the design spec (read `docs/superpowers/specs/2026-07-24-doc-components-design.md` before writing).
- Produces: the normative schema document later tasks and issues cite. Section headings other artifacts link to: `## Directory layout`, `## Frontmatter`, `## Lifecycle`, `## Body formats`, `## Working layer`, `## Render mapping (informative)`.

- [ ] **Step 1: Create `doc-components/SCHEMA.md`**

```markdown
# Component Store Schema

Normative reference for the doc components system. Source of authority:
docs/superpowers/specs/2026-07-24-doc-components-design.md; on conflict the
spec wins and this file gets fixed.

A component is one small markdown file holding one documentation idea —
a decision, a term, a use case, a constraint, a non-goal, or a subsystem
fact — with YAML frontmatter carrying identity and lifecycle. Consumer
documentation is compiled from components; components are appended and
status-flipped, never surgically edited.

## Directory layout

Defaults; an adopting project overrides paths in `.grimore.toml`.

    docs/
      components/          # source of truth
        adr/<slug>.md
        term/<slug>.md
        usecase/<slug>.md
        constraint/<slug>.md
        nongoal/<slug>.md
        note/<slug>.md
      current/             # rendered agent view — written ONLY by grim render
      specs/               # working layer, dated session specs
      plans/               # working layer, dated implementation plans

## Frontmatter

| Field | Required | Rules |
|---|---|---|
| `id` | yes | `<type>-<slug>`; slug `[a-z0-9][a-z0-9-]*`; equals filename minus `.md`; unique across the store; never reused |
| `type` | yes | one of `adr`, `term`, `usecase`, `constraint`, `nongoal`, `note`; equals the parent directory name |
| `status` | yes | `draft`, `current`, or `superseded` |
| `supersedes` | no | list of component IDs this replaces; every target must exist in the store |
| `subsystem` | no | routes `note` (and optionally `adr`) into a render target |
| `paths` | no | `note`/`adr` only; list of path globs the component describes; drives the touched-path guard |
| `date` | yes | ISO `YYYY-MM-DD` creation date; never updated |

## Lifecycle

- **Live means `current`.** Drafts and superseded components are not live.
- Legal transitions: `draft -> current` (promotion), `draft -> superseded`
  (abandonment), `current -> superseded`. Nothing else. No deletion.
- A `supersedes:` edge is authored on the new component (usually while it
  is a draft) and **takes effect at promotion**: when the new component
  becomes `current`, each edge target flips to `superseded` in the same
  pass.
- Drafts are the only place in-place edits are allowed, and an amendment
  must never reverse a decision's substance — if the decision itself
  changed, abandon the draft and write a new component.
- **Reconcile error:** one component with two or more live successors is
  invalid; the branch that surfaces it must resolve which successor
  stands.
- Supersede targets must already exist in the branch's view of the store;
  reversing a decision in an unmerged sibling branch requires landing
  order.

## Body formats

- **adr** — record only decisions that are hard to reverse, surprising
  without context, and a real trade-off. One paragraph of
  context/decision/why; optional sections only when they add value.
- **term** — `**Term**: one-two sentence definition.` then
  `_Avoid_: rejected synonyms.` Opinionated; context-specific terms only.
- **usecase / constraint / nongoal** — `# Title` plus one terse prose
  paragraph. Non-goals state what is excluded and why.
- **note** — terse factual prose about one subsystem. No file paths or
  code snippets in prose; use `paths:` frontmatter.

## Working layer

Specs (session artifacts, frozen after implementation):

- Frontmatter: `components:` — list of component IDs the session created.
- Body includes a `## Decisions` section that references those IDs rather
  than restating them.
- `implemented:` stamp is added once by finish-docs; already-stamped
  specs are never re-stamped.
- The banner block delimited by `<!-- grim:status -->` and
  `<!-- /grim:status -->` is script-owned: grim lint --fix rewrites it;
  humans and agents never edit inside it. Everything outside the block is
  frozen after implementation.

Plans:

- Frontmatter: `spec:` — repo-relative path to the plan's spec. Lint
  warns when missing. Plans inherit their spec's banner.

## Render mapping (informative)

Implemented by grim render (IAM-40); recorded here so authors know where
a component surfaces. Only `status: current` components render.

| Output | Source |
|---|---|
| `current/charter.md` | usecase, constraint, nongoal |
| `current/decisions.md` | adr |
| `current/glossary.md` | term |
| `current/<subsystem>.md` | note with matching `subsystem:` |
| `current/general.md` | note without `subsystem:` |

Ordering within every output: (`date`, `id`) ascending.
```

- [ ] **Step 2: Verify the required sections exist**

Run:
```bash
grep -c '^## ' doc-components/SCHEMA.md && grep -q '## Directory layout' doc-components/SCHEMA.md && grep -q '## Frontmatter' doc-components/SCHEMA.md && grep -q '## Lifecycle' doc-components/SCHEMA.md && grep -q '## Body formats' doc-components/SCHEMA.md && grep -q '## Working layer' doc-components/SCHEMA.md && grep -q '## Render mapping (informative)' doc-components/SCHEMA.md && echo SECTIONS-OK
```
Expected: `6` then `SECTIONS-OK`.

- [ ] **Step 3: Commit**

```bash
git add doc-components/SCHEMA.md
git commit -m "feat(doc-components): component store schema reference (IAM-37)"
```

---

### Task 2: Component authoring templates

**Files:**
- Create: `doc-components/templates/adr.md`
- Create: `doc-components/templates/term.md`
- Create: `doc-components/templates/usecase.md`
- Create: `doc-components/templates/constraint.md`
- Create: `doc-components/templates/nongoal.md`
- Create: `doc-components/templates/note.md`

**Interfaces:**
- Consumes: field rules from Task 1's SCHEMA.md.
- Produces: the six files the align skill (IAM-39) and adopt-docs skill (IAM-43) copy when creating components. Placeholder convention: angle brackets `<like-this>`; every template's frontmatter must parse as YAML.

- [ ] **Step 1: Create the six template files**

`doc-components/templates/adr.md`:
```markdown
---
id: adr-<slug>
type: adr
status: draft
# supersedes: [adr-<older-slug>]
# subsystem: <render-target>
# paths: [<glob-the-decision-governs>/]
date: <YYYY-MM-DD>
---

# <Decision title>

<One paragraph: the context that forced a choice, the decision made, and
why — including the trade-off accepted. Record only if the decision is
hard to reverse, surprising without context, and a real trade-off.>
```

`doc-components/templates/term.md`:
```markdown
---
id: term-<slug>
type: term
status: draft
date: <YYYY-MM-DD>
---

**<Term>**: <one-two sentence definition of what it IS, not what it does.>

_Avoid_: <rejected synonyms, comma-separated.>
```

`doc-components/templates/usecase.md`:
```markdown
---
id: usecase-<slug>
type: usecase
status: draft
date: <YYYY-MM-DD>
---

# <Use case title>

<One terse paragraph: the actor, what they accomplish, and why the
project exists to serve it.>
```

`doc-components/templates/constraint.md`:
```markdown
---
id: constraint-<slug>
type: constraint
status: draft
date: <YYYY-MM-DD>
---

# <Constraint title>

<One terse paragraph: the requirement the system must always satisfy and
where it comes from.>
```

`doc-components/templates/nongoal.md`:
```markdown
---
id: nongoal-<slug>
type: nongoal
status: draft
date: <YYYY-MM-DD>
---

# <Non-goal title>

<One terse paragraph: what is deliberately excluded and why. The explicit
no is as valuable as the yes.>
```

`doc-components/templates/note.md`:
```markdown
---
id: note-<slug>
type: note
status: draft
subsystem: <render-target>
paths: [<globs-this-note-describes>/]
date: <YYYY-MM-DD>
---

<Terse factual prose about one subsystem fact. No file paths or code
snippets in prose — paths belong in the frontmatter above.>
```

- [ ] **Step 2: Verify every template's frontmatter parses as YAML with the right keys**

Run:
```bash
uv run --with pyyaml python - <<'EOF'
import pathlib, yaml
types = {"adr", "term", "usecase", "constraint", "nongoal", "note"}
files = sorted(pathlib.Path("doc-components/templates").glob("*.md"))
found = {p.stem for p in files} & types
assert found == types, f"missing templates: {types - found}"
for p in files:
    if p.stem not in types:
        continue
    fm = yaml.safe_load(p.read_text().split("---\n")[1])
    assert fm["type"] == p.stem, p
    assert str(fm["id"]).startswith(p.stem + "-"), p
    assert fm["status"] == "draft", p
    assert "date" in fm, p
print("TEMPLATES-OK")
EOF
```
Expected: `TEMPLATES-OK`.

- [ ] **Step 3: Commit**

```bash
git add doc-components/templates/
git commit -m "feat(doc-components): authoring templates for the six component types (IAM-37)"
```

---

### Task 3: Worked examples (fixture set)

**Files:**
- Create: `doc-components/examples/adr/slug-ids.md`
- Create: `doc-components/examples/term/component.md`
- Create: `doc-components/examples/usecase/catch-up-digest.md`
- Create: `doc-components/examples/constraint/single-file-cli.md`
- Create: `doc-components/examples/nongoal/multi-context-glossary.md`
- Create: `doc-components/examples/note/component-store.md`

**Interfaces:**
- Consumes: templates from Task 2; content drawn from real decisions in the design spec (so the examples are true, not lorem ipsum).
- Produces: the canonical valid-store fixture IAM-38's pytest suite loads (`doc-components/examples/` mirrors a `docs/components/` tree). Every file must satisfy every Global Constraint — lint tests will assert this tree is clean.

- [ ] **Step 1: Create the six example files**

`doc-components/examples/adr/slug-ids.md`:
```markdown
---
id: adr-slug-ids
type: adr
status: current
date: 2026-07-24
---

# Slug IDs instead of sequential ADR numbers

Sequential adr-NNNN numbering assumes centralized allocation, but
concurrent branches each allocate "the next number" and collide only
after both merge. Component IDs are therefore slug-based for every type,
including ADRs; the filename is the slug and allocation is free of
coordination. Trade-off accepted: no human-friendly ordering by number —
ordering comes from the date field instead.
```

`doc-components/examples/term/component.md`:
```markdown
---
id: term-component
type: term
status: current
date: 2026-07-24
---

**Component**: a small append-mostly markdown file holding exactly one
documentation idea, with frontmatter carrying its identity and lifecycle
status. Components are the source of truth; consumer docs are compiled
from them.

_Avoid_: fragment, doclet, entry.
```

`doc-components/examples/usecase/catch-up-digest.md`:
```markdown
---
id: usecase-catch-up-digest
type: usecase
status: current
date: 2026-07-24
---

# Human catches up after time away

A contributor returning after days or weeks asks what changed. The
renderer's digest mode lists components added, promoted, and superseded
since a date, grouped by type and linking the specs that produced them,
so catch-up does not require replaying session history.
```

`doc-components/examples/constraint/single-file-cli.md`:
```markdown
---
id: constraint-single-file-cli
type: constraint
status: current
date: 2026-07-24
---

# Tooling stays a single-file CLI

The grim tool remains one uv-runnable Python file with at most
PyYAML-class dependencies and no daemon, so adopting projects can copy or
reference it without a packaging step. Comes from the explain-diff
cost-model precedent: mechanical work belongs in a zero-token script that
is trivial to vendor.
```

`doc-components/examples/nongoal/multi-context-glossary.md`:
```markdown
---
id: nongoal-multi-context-glossary
type: nongoal
status: current
date: 2026-07-24
---

# No multi-context glossaries in v1

One glossary per repository. The bounded-context map pattern (multiple
per-context glossaries with declared relationships) is excluded until a
real adopting project needs it, because it multiplies render targets and
routing rules before the single-context economics are proven.
```

`doc-components/examples/note/component-store.md`:
```markdown
---
id: note-component-store
type: note
status: current
subsystem: store
paths: [doc-components/]
date: 2026-07-24
---

The component store is append-mostly: sessions add files and flip
statuses, and the only in-place edits allowed are amendments to drafts
before promotion. Consumer documentation is compiled from live components
by the renderer; superseded and draft components never reach consumers.
```

- [ ] **Step 2: Verify the example tree satisfies the schema invariants**

Run:
```bash
uv run --with pyyaml python - <<'EOF'
import pathlib, yaml
root = pathlib.Path("doc-components/examples")
types = {"adr", "term", "usecase", "constraint", "nongoal", "note"}
seen_types, ids = set(), set()
for p in sorted(root.rglob("*.md")):
    fm = yaml.safe_load(p.read_text().split("---\n")[1])
    assert fm["type"] == p.parent.name and fm["type"] in types, p
    assert fm["id"] == f'{fm["type"]}-{p.stem}', p
    assert fm["id"] not in ids, f"duplicate id {fm['id']}"
    ids.add(fm["id"])
    assert fm["status"] in ("draft", "current", "superseded"), p
    assert str(fm["date"]) == "2026-07-24", p
    seen_types.add(fm["type"])
assert seen_types == types, f"missing example types: {types - seen_types}"
print(f"EXAMPLES-OK ({len(ids)} components)")
EOF
```
Expected: `EXAMPLES-OK (6 components)`.

- [ ] **Step 3: Commit**

```bash
git add doc-components/examples/
git commit -m "feat(doc-components): worked example components, one per type (IAM-37)"
```

---

### Task 4: Spec and plan templates (working layer)

**Files:**
- Create: `doc-components/templates/spec.md`
- Create: `doc-components/templates/plan.md`

**Interfaces:**
- Consumes: Working layer rules from Task 1's SCHEMA.md (banner delimiters, `components:` and `spec:` keys, `implemented:` stamp semantics).
- Produces: the spec template align (IAM-39) fills in, and the plan frontmatter stub the adopt-docs CLAUDE.md note (IAM-43) instructs writing-plans to include. Keys downstream code depends on: `components` (list of IDs) in specs, `spec` (repo-relative path) in plans.

- [ ] **Step 1: Create `doc-components/templates/spec.md`**

```markdown
---
components: []            # component IDs created during the align session
# implemented: <YYYY-MM-DD (PR #N)>   — added once by finish-docs; never by hand
---

<!-- grim:status -->
<!-- /grim:status -->

# <Topic> - Design

Date: <YYYY-MM-DD>

## Problem

<What hurts, for whom, and why now. Terse prose.>

## Approach

<The chosen approach and the alternatives it beat, one paragraph each.>

## Decisions

<One line per decision, referencing the component that carries it —
"Slug IDs over sequential numbering: adr-slug-ids" — never restating the
component's content. The components are canonical; this section is an
index.>

## Out of scope

<What this design explicitly does not cover, and why.>
```

- [ ] **Step 2: Create `doc-components/templates/plan.md`**

```markdown
---
spec: <repo-relative path to the spec this plan implements>
---

<!-- grim:status -->
<!-- /grim:status -->

<Plan body follows the superpowers writing-plans format. Only the
frontmatter above and the banner block are doc-components conventions:
the spec: line lets the plan inherit its spec's derived status banner,
and the banner block is script-owned - grim lint --fix rewrites it,
nothing else touches it.>
```

- [ ] **Step 3: Verify both templates parse and carry the load-bearing keys**

Run:
```bash
uv run --with pyyaml python - <<'EOF'
import pathlib, yaml
spec = yaml.safe_load(pathlib.Path("doc-components/templates/spec.md").read_text().split("---\n")[1])
assert spec == {"components": []}, spec
plan_text = pathlib.Path("doc-components/templates/plan.md").read_text()
plan = yaml.safe_load(plan_text.split("---\n")[1])
assert "spec" in plan, plan
for t in ("spec.md", "plan.md"):
    body = pathlib.Path(f"doc-components/templates/{t}").read_text()
    assert "<!-- grim:status -->" in body and "<!-- /grim:status -->" in body, t
print("WORKING-LAYER-OK")
EOF
```
Expected: `WORKING-LAYER-OK`.

- [ ] **Step 4: Commit and close out**

```bash
git add doc-components/templates/spec.md doc-components/templates/plan.md
git commit -m "feat(doc-components): spec and plan working-layer templates (IAM-37)"
```

Then mark Linear IAM-37 Done (or In Review per team habit) with a comment linking the four commits.
