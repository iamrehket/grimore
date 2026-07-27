---
id: adr-agent-optimized-source
type: adr
status: current
paths: [doc-components/SCHEMA.md]
date: 2026-07-24
---

# Agent-optimized source, rendered views

Spec- and plan-driven agent workflows produce sprawling dated documents that
agents keep loading long after they go stale. The component store is therefore
written as structured, agent-optimized source - uniform frontmatter, one idea
per file - and a zero-token script renders consumer views for both agents and
humans, rather than optimizing the source for human reading. The trade-off
accepted: authors write to a schema instead of prose, and the rendered layer
must be regenerated rather than edited, in exchange for token cost that scales
with analysis rather than presentation.
