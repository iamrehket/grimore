---
id: adr-plans-out-of-sync-loop
type: adr
status: current
date: 2026-07-24
---

# Plans stay out of the sync loop

Plan documents run to well over a thousand lines and are execution
scaffolding: they record how work was carried out, not what the project now
believes. Feeding them to the reconciliation pass would multiply its token
cost without adding anything the spec and the actual diff do not already
carry, so plans stay out of the sync loop entirely and participate only
through derived status banners inherited from their spec. The trade-off:
rationale recorded only in a plan and never in its spec is invisible to
reconciliation and will never become a component - accepted as the single
largest token saving available, with the spec template's Decisions block as
the place such rationale is meant to live.
