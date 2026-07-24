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
| `id` | yes | `<type>-<slug>`; slug `[a-z0-9][a-z0-9-]*` and equals the filename minus `.md`; unique across the store; never reused |
| `type` | yes | one of `adr`, `term`, `usecase`, `constraint`, `nongoal`, `note`; equals the parent directory name |
| `status` | yes | `draft`, `current`, or `superseded` |
| `supersedes` | no | list of component IDs this replaces; every target must exist in the store |
| `subsystem` | no | routes `note` into a render target |
| `paths` | no | `note`/`adr` only; list of path globs the component describes; drives the touched-path guard |
| `date` | yes | ISO `YYYY-MM-DD` creation date; never updated |

Frontmatter field order is not significant.

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
