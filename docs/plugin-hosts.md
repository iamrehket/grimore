# Operating Grimore in Claude Code and Codex

Grimore ships one repository-root plugin payload. Claude Code reads
`.claude-plugin/plugin.json`; Codex reads `.codex-plugin/plugin.json`; both
discover the payload through `.claude-plugin/marketplace.json`. The Claude
Code manifest is authoritative for shared metadata, and the Codex manifest
must carry the same name, version, description, author, and ordered skill
paths.

The commands below were verified on 2026-07-27 with Claude Code `2.1.220` and
Codex CLI `0.145.0`. They use the repository marketplace name `grimore` and
the plugin selector `grimore@grimore`. They install no helper packages; the
host CLIs, Git, and standard shell archive tools are the only prerequisites.

## Release and cache rules

A release uses one shared semantic version in both native manifests. Run the
repository version tool; do not hand-increment either file. Never append a
Codex-only cachebuster or otherwise give one host a different version.

Plugin hosts cache installed payloads. Updating the marketplace catalog alone
does not prove the installed copy changed: follow the host-specific update
steps below, verify the listed version, and start a new agent session. Local
unreleased checks use a temporary snapshot and isolated host state rather
than altering normal user configuration.

## Claude Code

### Discover and install

Register the GitHub repository at user scope, confirm the marketplace, and
install Grimore:

```bash
claude plugin marketplace add iamrehket/grimore --scope user
claude plugin marketplace list
claude plugin install grimore@grimore --scope user
claude plugin list --json
```

Start a new Claude Code session after installation so the installed skills
are loaded. The interactive `/reload-plugins` command may be useful during
development, but a new session is the release smoke expectation.

### Update and refresh the cache

Refresh the Git marketplace, update the installed plugin, and verify it:

```bash
claude plugin marketplace update grimore
claude plugin update grimore@grimore --scope user
claude plugin list --json
```

Start a new Claude Code session after an update. If an unreleased local
snapshot must replace a prior snapshot, remove and reinstall the plugin from
the new isolated snapshot instead of inventing a manifest version.

### Uninstall and remove the marketplace

```bash
claude plugin uninstall grimore@grimore --scope user
claude plugin marketplace remove grimore --scope user
claude plugin marketplace list
```

## Codex

### Discover and install

Register the GitHub repository, install Grimore, and inspect the installed
entry:

```bash
codex plugin marketplace add iamrehket/grimore
codex plugin marketplace list
codex plugin add grimore@grimore
codex plugin list --json
```

Start a new Codex session after installation so the cached skills are loaded.

### Update and refresh the cache

Codex CLI `0.145.0` refreshes Git marketplace snapshots but has no separate
plugin-update command. Upgrade the marketplace, then remove and reinstall the
plugin to replace its cached payload:

```bash
codex plugin marketplace upgrade grimore
codex plugin remove grimore@grimore
codex plugin add grimore@grimore
codex plugin list --json
```

Start a new Codex session after the reinstall. Use the same remove-and-add
sequence for a newer isolated local snapshot; never change only the Codex
manifest to force a refresh.

### Uninstall and remove the marketplace

```bash
codex plugin remove grimore@grimore
codex plugin marketplace remove grimore
codex plugin marketplace list
```

Codex CLI `0.145.0` has no standalone plugin validator. Its native smoke
evidence is therefore the isolated marketplace add, plugin add, list, remove,
and marketplace cleanup lifecycle below.

## Recommended isolated native smoke

Native smoke evidence is recommended release evidence, not a merge gate. It
depends on locally installed host CLIs and complements, rather than replaces,
the deterministic CI suite.

Run from a clean Grimore checkout. Create a committed source snapshot and
redirect both hosts away from normal user state:

```bash
GRIMORE_SMOKE_ROOT="$(mktemp -d)"
mkdir -p \
  "$GRIMORE_SMOKE_ROOT/source" \
  "$GRIMORE_SMOKE_ROOT/claude" \
  "$GRIMORE_SMOKE_ROOT/codex"
git archive --format=tar HEAD |
  tar -xf - -C "$GRIMORE_SMOKE_ROOT/source"
export CLAUDE_CONFIG_DIR="$GRIMORE_SMOKE_ROOT/claude"
export CODEX_HOME="$GRIMORE_SMOKE_ROOT/codex"
```

Exercise the Claude Code lifecycle against that local snapshot:

```bash
claude plugin validate "$GRIMORE_SMOKE_ROOT/source"
claude plugin marketplace add "$GRIMORE_SMOKE_ROOT/source" --scope user
claude plugin install grimore@grimore --scope user
claude plugin list --json
claude plugin uninstall grimore@grimore --scope user
claude plugin marketplace remove grimore --scope user
```

Exercise the Codex lifecycle against the same snapshot:

```bash
codex plugin marketplace add "$GRIMORE_SMOKE_ROOT/source"
codex plugin add grimore@grimore
codex plugin list --json
codex plugin remove grimore@grimore
codex plugin marketplace remove grimore
```

Confirm both isolated host directories contain no state that still needs
inspection, then remove only the printed temporary root:

```bash
printf '%s\n' "$GRIMORE_SMOKE_ROOT"
rm -rf "$GRIMORE_SMOKE_ROOT"
```

Record the date, both CLI versions, source commit, commands, outcomes, and
cleanup status in the pull request or release record. A useful record also
notes the manifest version observed by each host and any stderr warnings.

## References

- [Claude Code: discover and install plugins](https://code.claude.com/docs/en/discover-plugins)
- [Claude Code: create and distribute a marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [OpenAI: package a plugin](https://developers.openai.com/plugins/build/plugins)
