---
id: adr-payload-renderer-split
type: adr
status: current
paths: [explain-diff/]
date: 2026-07-13
---

# explain-diff authors a payload, not a page

A skill producing a rich HTML guide could have the agent write the markup, but
presentation boilerplate - CSS, JavaScript, print styles, a vendored diagram
runtime - would be retyped every invocation, and token cost would scale with
page size rather than analysis. explain-diff splits the work instead: static
assets are authored once at skill-construction time, each invocation produces
only a structured JSON payload whose prose fields are markdown, and a build
script does schema validation, hunk extraction from git, markdown conversion,
asset inlining, and file writing at zero token cost. The trade-off: the
payload must satisfy a schema and the renderer becomes a maintained artifact
with its own tests - in exchange for the cost model the doc-components system
later adopted wholesale.
