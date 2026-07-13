---
name: serve-skills-via-mcp
description: Expose Agent Skills (Claude Code, Cursor, VS Code/Copilot, Gemini, Goose, Codex, OpenCode skill directories) as MCP resources from a fastmcp server, and/or pull skills down from a remote MCP server into a local skills directory. Use this whenever the user wants to "share skills across tools", "serve skills over MCP", "install a skill via MCP", "download skills from a server", "sync skills", or asks how one AI tool's skills directory can be made available to another tool/client. Covers both the server side (SkillProvider / SkillsDirectoryProvider / vendor providers) and the client side (list_skills / download_skill / sync_skills) — this is the actual installation mechanism, not just a docs page.
---

# Serve and Install Agent Skills via MCP

Agent skills (Claude Code, Cursor, VS Code Copilot, etc.) are just directories: a main instruction file (`SKILL.md`) plus optional supporting files. Each of those tools keeps its skills in its own platform-specific directory (`~/.claude/skills/`, `~/.cursor/skills/`, ...), which makes cross-tool sharing manual — copy-paste or symlink. FastMCP's Skills Provider turns a skills directory into standard MCP resources so **any** MCP client can list, read, and download them, and ships client-side helpers that do the actual downloading.

This is two separate things:
1. **Serving** — expose a skills directory from your own fastmcp server (`fastmcp.server.providers.skills`).
2. **Installing / syncing** — pull skills from someone else's MCP server into a local directory (`fastmcp.utilities.skills`). This is the part that answers "how do I install a skill via MCP."

## Part 1 — Serving skills from a server

### Quick start

```python
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider

mcp = FastMCP("Skills Server")
mcp.add_provider(SkillsDirectoryProvider(roots=Path.home() / ".claude" / "skills"))
```

Every subdirectory containing a `SKILL.md` becomes a discoverable skill, exposed under the `skill://` URI scheme:

| Resource | Purpose |
|---|---|
| `skill://{name}/SKILL.md` | Main instruction file |
| `skill://{name}/_manifest` | Synthetic JSON resource listing every file in the skill with size + SHA256 hash |
| `skill://{name}/{path}` | Any supporting file (reference docs, examples, assets) |

Frontmatter's `description` field is used if present; otherwise the provider derives one from the first meaningful line/heading of the body.

### One skill vs. a whole directory

- **`SkillProvider(skill_path, main_file_name="SKILL.md", supporting_files="template")`** — exposes exactly *one* skill folder. Use this for fine-grained control over a single skill's config.

  ```python
  from fastmcp.server.providers.skills import SkillProvider
  mcp.add_provider(SkillProvider(Path.home() / ".claude" / "skills" / "pdf-processing"))
  ```

- **`SkillsDirectoryProvider(roots, reload=False, main_file_name="SKILL.md", supporting_files="template")`** — scans one or more root directories and creates a `SkillProvider` per valid skill folder (an `AggregateProvider` under the hood). Accepts a list of roots; if the same skill name appears in more than one, **the first root wins**:

  ```python
  mcp.add_provider(SkillsDirectoryProvider(roots=[
      Path.cwd() / ".claude" / "skills",   # project-level first
      Path.home() / ".claude" / "skills",  # user-level fallback
  ]))
  ```

### Vendor providers — one line per platform

Pre-configured `SkillsDirectoryProvider` subclasses pointing at each tool's default directory. All accept the same options as `SkillsDirectoryProvider` except `roots`, which is fixed:

| Provider | Default directory |
|---|---|
| `ClaudeSkillsProvider` | `~/.claude/skills/` |
| `CursorSkillsProvider` | `~/.cursor/skills/` |
| `VSCodeSkillsProvider` | `~/.copilot/skills/` |
| `CopilotSkillsProvider` | `~/.copilot/skills/` |
| `CodexSkillsProvider` | `/etc/codex/skills/` **and** `~/.codex/skills/` (system takes precedence) |
| `GeminiSkillsProvider` | `~/.gemini/skills/` |
| `GooseSkillsProvider` | `~/.config/agents/skills/` |
| `OpenCodeSkillsProvider` | `~/.config/opencode/skills/` |

```python
from fastmcp.server.providers.skills import ClaudeSkillsProvider
mcp.add_provider(ClaudeSkillsProvider())  # uses ~/.claude/skills/ automatically
```

### `supporting_files`: template vs. resources

Controls how a skill's non-main, non-manifest files show up to clients:

- `"template"` (default) — supporting files are hidden from `list_resources()`; clients read the `_manifest` first, then fetch specific files via a `ResourceTemplate`. Keeps the resource list compact for skills with many files.
- `"resources"` — every file in every skill is listed individually in `list_resources()`. Use this when a client needs full enumeration up front without an extra manifest round-trip.

### Reload mode

```python
SkillsDirectoryProvider(roots=..., reload=True)
```

Re-scans the directory on every `list_resources()`/`read_resource()` call — new/removed/edited skills show up immediately, no server restart. Adds per-request overhead, so use it while actively editing skills and turn it off in production.

## Part 2 — Installing skills from a server (the client side)

These are standalone async functions in `fastmcp.utilities.skills`, used against a connected `Client`. This is the actual mechanism for "installing a skill via MCP" — it downloads the skill's files from wherever the server's `skill://` resources live into a real local directory.

### Discover what's available

```python
from fastmcp import Client
from fastmcp.utilities.skills import list_skills

async with Client("http://skills-server/mcp") as client:
    for skill in await list_skills(client):
        print(f"{skill.name}: {skill.description}")  # skill.uri too
```

`list_skills` works by scanning `list_resources()` for URIs matching `skill://{name}/SKILL.md` — it doesn't require any special server-side support beyond the Skills Provider being mounted.

### Inspect before downloading

```python
from fastmcp.utilities.skills import get_skill_manifest

manifest = await get_skill_manifest(client, "pdf-processing")
for f in manifest.files:
    print(f.path, f.size, f.hash)
```

### Install one skill

```python
from fastmcp.utilities.skills import download_skill

skill_path = await download_skill(
    client, "pdf-processing", Path.home() / ".claude" / "skills",
)
```

Creates `{target_dir}/{skill_name}/` and writes every file the manifest lists (text via `read_resource` + `.text`, binary via base64-decoded `.blob`). Raises `FileExistsError` if the target already exists unless you pass `overwrite=True`. Path traversal is rejected on both the skill name and each file path.

### Install everything on a server

```python
from fastmcp.utilities.skills import sync_skills

paths = await sync_skills(client, Path.home() / ".claude" / "skills")
```

Lists all skills, then calls `download_skill` for each; existing skill directories are silently skipped unless `overwrite=True`.

## Putting it together: one tool's skills → another tool's directory

The common cross-tool workflow this whole feature exists for:

```python
# On the "source" side: serve Cursor's skills over MCP
from fastmcp import FastMCP
from fastmcp.server.providers.skills import CursorSkillsProvider

mcp = FastMCP("Cursor Skills Bridge")
mcp.add_provider(CursorSkillsProvider())
```

```python
# On the "destination" side: pull them into Claude Code's skills directory
from pathlib import Path
from fastmcp import Client
from fastmcp.utilities.skills import sync_skills

async with Client("http://localhost:8000/mcp") as client:
    await sync_skills(client, Path.home() / ".claude" / "skills")
```

That's the whole loop — no manual copy/symlink, and it works over a network, not just on one machine.

## Notes

- `.md` is force-registered as `text/markdown` in `mimetypes` at import time — relevant if you're debugging content-type surprises on non-Linux platforms (Windows sometimes lacks this mapping).
- Every skill's resource `_meta.fastmcp.skill` carries `{"name": ..., "is_manifest": ...}` — useful if you're writing middleware that needs to identify skill-origin resources.
- Full reference: `fastmcp/docs/servers/providers/skills.mdx`.
