---
components:
  - adr-dual-plugin-manifests
  - adr-stdlib-provenance-resolver
  - nongoal-host-abstraction-framework
implemented: "2026-07-27 (PR #14)"
---

<!-- grim:status -->
> **Implemented 2026-07-27 (PR #14).**
> References current.
<!-- /grim:status -->

# Cross-Compatible Plugin - Design

Date: 2026-07-27

## Problem

Grimore is a working Claude Code marketplace plugin, but Codex cannot consume
the repository as a complete plugin because its native manifest is absent.
The release gate, marketplace tests, provenance instructions, and operator
workflow also assume the Claude Code package alone. This contradicts the
project's standing requirement to work across agent consumers: the same three
skills should install from the same repository, retain one release identity,
and describe executable workflows in both Claude Code and Codex.

## Approach

Keep the repository root as the single plugin payload and retain the existing
skill directories and marketplace catalog. Add a native Codex manifest beside
the existing Claude Code manifest. The Claude Code manifest remains
authoritative for shared release metadata; tests require the Codex manifest
to mirror the plugin name, version, description, author, and ordered skill
paths, while allowing Codex-only presentation metadata. The version tool
reads its baseline from the authoritative manifest and updates both manifests
in one operation.

Codex already recognizes the existing marketplace catalog as a
legacy-compatible marketplace, and an isolated local probe confirmed that it
can install the repository-root payload when the Codex manifest is present.
Reusing that catalog avoids a second marketplace file and preserves the
installed shape already verified in Claude Code. The repository-wide payload
copy remains an accepted cost.

Targeted instruction edits remove assumptions that only one host provides a
particular interaction name, provenance file, or companion planning skill.
They preserve the workflows: structured choices remain structured choices,
the component-capture and review loops remain intact, and the existing
git-first provenance ladder remains intact. The edits express required
outcomes and explicit capability fallbacks in host-neutral terms rather than
introducing a framework for agent-harness differences.

Provenance resolution is the one targeted behavior moved out of instruction
prose. `adopt-docs` delegates it to a small read-only helper so legacy,
matching, mismatched, malformed, and missing manifest cases can be exercised
without a model-driven run. The helper uses only the Python standard library
and the Git executable already required by adoption. It installs no packages,
makes no network requests, and writes no files. This deliberately revises the
older adopt-docs working-layer plan's preference for no new adoption runtime;
the frozen plan remains historical evidence rather than a current constraint.

The conventional-layout alternative would move the skills under a shared
skills directory. It was rejected because it would invalidate runtime-relative
paths and the frozen adoption pressure-test bundle for no demonstrated host
requirement; the current Codex CLI successfully installs the explicit skill
paths. A dedicated packaged subtree was also rejected because it would add a
generated or duplicated payload and a new drift boundary merely to reduce the
already accepted cache size. A neutral metadata source was rejected because
it would add generation machinery when the established release authority can
drive an executable parity contract directly.

## Compatibility contract

- One repository-root payload is installed by both agent harnesses.
- Each harness receives its native plugin manifest.
- The existing marketplace catalog remains the shared discovery source.
- The Claude Code manifest is authoritative for shared release metadata.
- The Codex manifest mirrors shared identity, release, description, author,
  and skill-path fields; host-specific presentation fields may differ.
- Version check and print modes reject any shared-field drift. Apply mode
  rejects non-version drift, computes from the authoritative manifest's
  merge-base version, and writes the result to both manifests with restoration
  of both originals on any write failure. A successful apply never leaves only
  one version changed.
- On the bootstrap branch where the Codex manifest is absent at the
  merge-base, version computation reads the base version from the authoritative
  Claude Code manifest and requires both matching manifests at the branch
  head. Once both exist at the merge-base, either one being absent is an
  error.
- `Version-Waive` retains its existing precedence: it short-circuits before
  manifest comparison or version computation, and apply mode writes neither
  manifest for a waived range.
- The three current skills remain in their current directories and retain
  their existing names and trigger intent. Trigger descriptions may change
  only to remove host-specific terms without broadening their scope.
- Structured interviews ask one question at a time and offer two to four
  concrete choices. They use a host's structured-choice interaction when one
  is available and numbered plain text otherwise.
- When `align` runs outside an adopted repository, it uses an available
  general design workflow; if none exists, it conducts the same
  one-question-at-a-time interview without creating components.
- After a spec is signed off, `align` offers an available implementation-plan
  workflow; if none exists, it authors the configured plan from the
  doc-components plan template and project conventions.
- `adopt-docs` preserves its provenance ladder: a verified Grimore source
  commit first, the authoritative plugin version second, and `unknown` last.
  The version rung accepts an older Claude-only package, but when both native
  manifests are present it requires matching plugin names and versions;
  mismatch warns and falls through to `unknown`.
- `adopt-docs` obtains that identity from one deterministic helper rather than
  reimplementing the branch in agent reasoning. The helper receives the skill
  source and adopting-repository roots, performs no writes, and has no network
  behavior. Its successful standard output is exactly one stamp identity;
  mismatch and malformed-input warnings use standard error. Resolving to
  `unknown` is a successful safe fallback, while invalid invocation is an
  error.
- The provenance helper imports only the Python standard library and invokes
  only Git, which adoption already requires. It introduces no package,
  environment, or installation step.
- Installation, update, cache-refresh, and new-session expectations are
  documented separately for Claude Code and Codex.

## Acceptance criteria

The change is complete when deterministic validation proves all of the
following:

1. Repository tests validate each native manifest, shared-field parity,
   declared skill existence, frontmatter, and complete on-disk skill coverage.
2. Version-gate tests prove check, print, apply, idempotence, rollback on
   failure, waiver precedence, bootstrap from a merge-base without the Codex
   manifest, and mismatch behavior across both manifests.
3. Provenance resolver tests cover a verified Grimore Git source, refusal to
   stamp the adopting repository's commit, an older Claude-only bundle,
   matching dual manifests, mismatched names, mismatched versions, malformed
   JSON, missing metadata, warning routing, and the safe `unknown` fallback.
   The executable is also run with Python's isolated mode and site loading
   disabled, proving it does not depend on installed packages. These tests use
   fresh temporary fixtures. The frozen `0.2.0` pressure-test bundle and its
   inventory remain unchanged as historical evidence for the earlier
   Claude-only workflow; they are retired from current acceptance and are not
   rerun by combining the updated skill with that older bundle.
4. A static portability audit covers every shipped `SKILL.md`: the shared
   instructions contain no `AskUserQuestion` tool name or
   `superpowers:brainstorming` / `superpowers:writing-plans` dependency, and
   the adoption instructions invoke the provenance helper rather than
   restating its decision branch. Deliberate host names, manifest paths, and
   commands remain allowed in host-specific installation documentation.
5. An operator guide contains install, update, cache-refresh,
   uninstall, and new-session procedures for both agent harnesses, including
   the commands used by the recommended isolated smoke checks.
6. The existing full test suite and documentation checks pass.

Manifest, parity, version, and portability tests run in pull-request CI.

Model-driven executions are not part of this acceptance threshold. They are
nondeterministic, require credentials, and would test agent judgment beyond
the packaging and targeted instruction-portability change being made.

## Decisions

- One repository-root payload with two native manifests, with the Claude Code
  manifest retaining release authority: adr-dual-plugin-manifests
- A deterministic, standard-library-only provenance resolver instead of an
  instruction-only metadata branch: adr-stdlib-provenance-resolver
- Targeted portability fixes instead of a host-abstraction framework:
  nongoal-host-abstraction-framework

## Out of scope

Moving the skill directories, introducing a generated distribution subtree,
adding a second marketplace catalog, publishing to either host's public
directory, adding MCP servers or hooks, and redesigning the three workflows
around a generalized host API are excluded. Any adoption runtime beyond the
single provenance helper is also excluded, as are new third-party runtime
dependencies. Full model-driven evaluations in both hosts are excluded;
deterministic native installation smoke tests are recommended evidence rather
than a merge gate. Refreshing or rerunning the retired Claude-only pressure
bundle is also excluded.

## Verified premises

The packaging premise was checked on 2026-07-27 with Claude Code `2.1.220` and
Codex CLI `0.145.0`.

- `claude plugin validate .` validated the existing marketplace successfully.
- In an isolated `CODEX_HOME`, a repository snapshot with the current Claude
  Code manifest copied to the required Codex manifest location was added as a
  marketplace, installed as `grimore@grimore`, and listed as installed and
  enabled at version `1.0.0`. Codex resolved the existing
  `.claude-plugin/marketplace.json` and cached the repository-root payload.
- `codex plugin --help` in that version exposes add, list, remove, and
  marketplace commands but no standalone plugin validator.

The supporting product contract is current OpenAI documentation: every Codex
plugin has a `.codex-plugin/plugin.json`, and local hosts recognize
`.claude-plugin/marketplace.json` as a legacy-compatible marketplace
([Package your plugin](https://developers.openai.com/plugins/build/plugins)).
Claude Code documents the existing explicit skill-path and repository-root
marketplace behavior
([Plugins reference](https://code.claude.com/docs/en/plugins-reference),
[Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)).

## Recommended host smoke evidence

Before a release, run the operator guide's smoke procedure against locally
installed supported CLIs. It should record the date, both CLI versions,
commands, outcomes, and cleanup status; use isolated host state under a
temporary directory; validate the Claude Code marketplace; and exercise
marketplace discovery, install, list, and remove in both hosts. Preserve the
transcript in the pull request or release record when practical. This evidence
is advisory: it improves diagnosis of host drift but is not described as an
enforced merge gate.
