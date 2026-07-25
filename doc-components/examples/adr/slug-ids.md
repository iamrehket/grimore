---
id: adr-slug-ids
type: adr
status: current
supersedes: [adr-sequential-ids]
date: 2026-07-24
---

# Slug IDs instead of sequential ADR numbers

Sequential adr-NNNN numbering assumes centralized allocation, but
concurrent branches each allocate "the next number" and collide only
after both merge. Component IDs are therefore slug-based for every type,
including ADRs; the filename is the slug and allocation is free of
coordination. Trade-off accepted: no human-friendly ordering by number —
ordering comes from the date field instead.
