---
id: constraint-deterministic-rendered-view
type: constraint
status: draft
date: 2026-08-01
---

# The committed rendered view is byte-deterministic

Compiling the rendered view twice from the same store must produce
byte-identical output. Ordering within every rendered file is by date then id
ascending, and nothing in that output may depend on filesystem order, locale,
or the time of the run. Verification rests on this: grim check re-renders and
byte-compares, so any nondeterminism would turn the check into a random
failure. The guarantee is scoped to the committed artifact rather than to the
command that writes it, because that command may also emit output which is not
the committed view, is compiled from more than the store, and carries its own
weaker guarantee.
