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
