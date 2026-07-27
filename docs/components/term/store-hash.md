---
id: term-store-hash
type: term
status: current
date: 2026-07-24
---

**Store hash**: a sha256 over the sorted current components, stamped as a
comment in each rendered file. It is provenance metadata recording which store
produced the output - not the verification mechanism, which is a byte-compare
against a fresh render.

_Avoid_: checksum.
