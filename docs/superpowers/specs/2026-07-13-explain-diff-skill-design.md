# explain-diff skill — design

Date: 2026-07-13
Status: approved pending user review of this document

## Purpose

A skill that turns a code diff into a rich, self-contained HTML guide (with
markdown as a second render target) so a human and an agent reach shared
understanding of a change before the next iteration loop. The guide explains
what changed, why, which design decisions are load-bearing, and what remains
open — and actively helps the user compose their response back to the agent.

This skill explains intent and implications. It does not judge code or hunt
for bugs; that is code review's job.

## Token economics (core constraint)

The agent never types boilerplate. The template (CSS, JS, print styles) and a
vendored Mermaid runtime are static assets written once during skill
construction. Per invocation, the agent authors only a structured JSON payload
whose prose fields are markdown. A build script (`render.py`) does everything
mechanical at zero token cost: schema validation, extracting hunk code from
git, markdown-to-HTML, inlining assets, writing the final file. Tokens scale
with analysis, not presentation.

## Scope

- **Warm diffs** (primary): the change the agent just made in this session —
  working tree, staged, or branch vs base. Rationale comes from conversation
  context and is labeled `provenance: stated`.
- **Cold diffs**: an arbitrary git range, a teammate's branch, or a PR
  (fetched via `gh`). The agent reverse-engineers intent by reading the code
  and labels rationale `provenance: inferred`. The page displays a
  "live session" vs "cold read" badge in the header.

## Skill anatomy

```
explain-diff/
├── SKILL.md              # analysis method + payload authoring guide
├── schema.json           # JSON Schema for the payload
├── render.py             # uv single-file script: payload -> html | md
├── assets/
│   ├── template.html     # page shell: CSS, composer JS, print CSS
│   └── mermaid.min.js    # vendored; inlined only when payload has diagrams
└── examples/
    └── payload.example.json
```

Lives in the grimore skills collection; servable via serve-skills-via-mcp.

## Pipeline

1. **Resolve the diff.** Determine mode (warm/cold) and the git ref range.
2. **Author `explanation.json`.** The only token-bearing step.
3. **Render.** `render.py explanation.json --format html|md [--open]`
   validates, extracts hunks, merges template, writes a self-contained file
   (default into the session scratch dir unless the user wants it kept),
   and opens the browser with `--open`.

Print output comes free: `@media print` CSS in the HTML hides the composer
and chrome, expands collapsed sections, and prints diagrams as rendered SVG.

## Analysis method (the heart of SKILL.md)

1. **Verdict first** — one sentence: what does the system do now that it
   didn't before.
2. **Group by intent, not files** — a change is 2-5 "moves"; mechanical
   fallout (renames, import shuffles) is acknowledged in one collapsed
   `fallout` section, never narrated.
3. **Load-bearing decisions** — operational definition: a decision is
   load-bearing if reversing it later would cost more than re-doing this
   diff, or if other parts of the change silently assume it. Each carries
   `provenance` and `reversal_cost: low | medium | high`, plus alternatives
   rejected.
4. **Implications** — mental-model updates: new invariants, edge-behavior
   changes, operational consequences (migrations, config, perf).
5. **Open questions** — genuine decision points, each phrased so an answer
   unblocks the next loop. These feed the feedback composer.

Guidance caps embedded hunks at ~6; the guide is a lens, not an archive.

## Payload schema — section vocabulary

Top level: `title`, `verdict`, `mode` (warm/cold), `diff` (ref range or
working-tree marker), `sections[]`.

| Type | Fields (beyond `heading`) | Purpose |
|---|---|---|
| `narrative` | `md` | Prose under a heading |
| `diagram` | `mermaid`, optional `links` (node id -> section anchor) | Mermaid diagram, interactive |
| `decision` | `id`, `provenance`, `reversal_cost`, `md`, `alternatives` | Load-bearing choice card |
| `hunk` | `file`, `lines`, `ref`, `md` | Annotated code pulled by render.py |
| `comparison` | `before_md`, `after_md` | Two-column before/after |
| `question` | `id`, `md` | Open question, feeds composer |
| `fallout` | `items[]` | Collapsed mechanical-change list |

Working-tree hunks have no stable ref: render.py extracts from disk at render
time and records a content hash; re-rendering after further edits warns that
hunks may have drifted.

## Page design

- Single scrolling page: sticky header (title, verdict, diff stats,
  provenance badge), mini table of contents, sections in payload order.
- Decision and question cards visually distinct, reversal-cost color accent.
- Hunks: syntax-highlighted code with annotation alongside (annotation is the
  point; code is the evidence).
- Theme-aware (light/dark). Self-contained: no external requests.
- **No emojis anywhere** — plain text labels only. This is a hard constraint
  on the template and on SKILL.md's authoring guidance.

### Interactive diagrams (template-side, zero marginal tokens)

- Click-through: `links` map makes Mermaid nodes clickable, jumping to the
  section that explains them; linked nodes get a visible affordance.
- Pan/zoom on diagrams larger than their container.
- Hover cross-highlight: hovering a decision card highlights diagram nodes
  linked to it.

### Feedback composer

Every decision and question card gets plain-text controls — Approve /
Discuss / Change — plus an optional note field. A sticky footer tallies
responses; "Copy as prompt" assembles structured text referencing section
ids for pasting back into the agent session. State persists in localStorage
keyed by payload hash.

## Rendering targets

- `html` — rich interactive page (canonical).
- `md` — plain markdown for PR descriptions/docs: diagrams as fenced mermaid
  blocks, hunks as fenced code, composer omitted, questions as a checklist.
- print — via print CSS in the html target, not a separate renderer.

## Error handling

`render.py` fails loudly and actionably on: schema violations, hunk refs that
do not resolve, duplicate or dangling section ids, and Mermaid blocks that
fail a pre-parse sanity check (otherwise they fail silently in the browser).
Drift warning on re-render of working-tree hunks (content hash mismatch).

## Testing

- pytest suite for render.py: schema validation cases, hunk extraction
  against a fixture git repo, markdown-renderer golden files.
- End-to-end: render `examples/payload.example.json`; assert output is
  self-contained (no external URLs) and composer JS is present.
- SKILL.md verified per superpowers:writing-skills before deployment.

## Out of scope (YAGNI)

- Bug-finding or review judgments.
- Hosted publishing (Claude Artifacts) — could be added later as an optional
  note, but local HTML is canonical.
- Multi-diff comparisons, history timelines, PDF generation beyond print CSS.
