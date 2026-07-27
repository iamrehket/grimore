---
id: adr-render-byte-compare
type: adr
status: current
date: 2026-07-24
---

# Verify renders by byte-compare, not by hash

A store hash stamped into each rendered file was the original verification
mechanism, but a hash over components alone cannot detect a renderer change, a
config change, or a change to the render mapping - any of which alters output
while every component stays byte-identical. grim check therefore re-renders
the store to a temporary tree and byte-compares it against the committed
rendered view, covering every input that affects output with no fingerprint
bookkeeping at all. The store hash is still stamped, but as provenance
metadata rather than the verification mechanism. The trade-off: verification
costs a full render on every CI run instead of a hash comparison - accepted
because a renderer or config change shipped without a re-render is precisely
the failure a hash could never catch.
