---
name: build-mcp-app
description: Build interactive UIs (charts, tables, dashboards, forms) rendered directly inside an MCP conversation, using fastmcp's native Python Apps system (fastmcp[apps] + Prefab) rather than the TypeScript @modelcontextprotocol/ext-apps SDK. Use this whenever the user wants a FastMCP tool to return something visual instead of raw text/JSON, mentions "MCP app", "app=True", "Prefab", dashboards, interactive tool UIs, or forms that write back to the server — as long as the project is Python/fastmcp. If the user is building in Node/TypeScript instead, this skill does not apply; point them at the ext-apps SDK's own skills instead.
---

# Build a FastMCP App

A FastMCP app is a tool that returns an interactive UI instead of text — a chart, table, form, or dashboard rendered inline in the conversation, with working sort/search/tooltips/state. Under the hood it's built on the [MCP Apps extension](https://modelcontextprotocol.io/docs/extensions/apps) (the same protocol the `@modelcontextprotocol/ext-apps` JS SDK targets), but fastmcp gives you a Python-native path via [Prefab](https://prefab.prefect.io) — no JavaScript, no separate frontend build.

## Install

```bash
pip install "fastmcp[apps]"
```

This pulls in `prefab-ui`, the Python component library used to build app UIs. Prefab is pre-1.0 — pin the version once you've picked one, since components can shift between releases.

## Pick your path

Four patterns cover almost everything. Start at the top; only drop down when you hit that pattern's specific limit.

| Pattern | Reach for it when | Key API |
|---|---|---|
| **Interactive Tools** | Default starting point — charts, tables, dashboards, client-side interactivity (toggles, tabs, filtering) | `@mcp.tool(app=True)` returning a Prefab component |
| **FastMCPApp** | The UI needs to call back to the server — forms that save, buttons that trigger backend work, search hitting a database | `FastMCPApp`, `@app.ui()`, `@app.tool()`, `CallTool` |
| **Generative UI** | You want the LLM to design the UI at runtime instead of a fixed shape | `mcp.add_provider(GenerativeUI())` |
| **Custom HTML** | You need a framework, a map/3D viewer, or anything Prefab's component set doesn't cover | `AppConfig(resource_uri=...)` + hand-written HTML using the `ext-apps` JS SDK |

Reaching for Custom HTML means talking to the MCP Apps protocol directly — same mechanism the TypeScript SDK's `create-mcp-app` skill teaches, just wired from the Python side instead of a Node server.

## 1. Interactive Tools — the default

Add `app=True` to a tool and return a Prefab component instead of raw data:

```python
from prefab_ui.components import DataTable, DataTableColumn
from fastmcp import FastMCP

mcp = FastMCP("Directory")

@mcp.tool(app=True)
def team_directory() -> DataTable:
    """Browse the team directory."""
    employees = [
        {"name": "Alice Chen", "role": "Staff Engineer", "dept": "Platform"},
        {"name": "Bob Martinez", "role": "Lead Designer", "dept": "Design"},
    ]
    return DataTable(
        columns=[
            DataTableColumn(key="name", header="Name", sortable=True),
            DataTableColumn(key="role", header="Role", sortable=True),
            DataTableColumn(key="dept", header="Dept", sortable=True),
        ],
        rows=employees,
        search=True,
    )
```

`app=True` sets up the renderer resource, CSP, and metadata that tell the host "this tool returns a UI" — no wrapper class needed for a single component. FastMCP also infers `app=True` automatically when the return type is a Prefab type, even if you don't write it explicitly.

Charts follow the same shape — `BarChart`, `LineChart`, `AreaChart`, `PieChart`, `RadarChart`, `RadialChart` all take `data` (list of dicts) plus `ChartSeries(data_key=..., label=...)` per series to plot.

### Composing a dashboard

Use `PrefabApp` as the root when you need more than one component. `Column`/`Row`/`Grid` lay things out; `with` blocks establish nesting (indentation *is* the layout):

```python
from prefab_ui.app import PrefabApp
from prefab_ui.components import Column, Grid, DataTable, DataTableColumn
from prefab_ui.components.charts import PieChart

@mcp.tool(app=True)
def team_directory() -> PrefabApp:
    with PrefabApp() as app:
        with Column(gap=4, css_class="p-6"):
            with Grid(columns=[1, 2], gap=4):
                PieChart(data=office_counts, data_key="count", name_key="office", show_legend=True)
                DataTable(columns=[...], rows=members, search=True)
    return app
```

Any Prefab component can go inside a table cell — badges, progress bars, buttons — not just plain values.

### Making it reactive — no server round-trip

Prefab has client-side state: components read/write a key-value store in the browser, so the UI updates live without calling your server again.

```python
from prefab_ui.actions import SetState
from prefab_ui.rx import Rx, STATE
from prefab_ui.components.control_flow import If

with PrefabApp(state={"selected": None}) as app:
    with Column(gap=4, css_class="p-6"):
        DataTable(..., on_row_click=SetState("selected", Rx("$event")))
        with If(STATE.selected):
            Text(Rx("selected.name"))
```

- `state={...}` on `PrefabApp` sets initial values.
- `SetState(key, value)` writes to state; `Rx("$event")` is the clicked row/element's data.
- `Rx("path.to.value")` is a reactive reference — it compiles to a browser-side expression that re-evaluates whenever state changes. Supports arithmetic, comparisons, formatting pipes (`.currency()`, `.percent()`), and ternaries (`.then(a, b)`).
- `If(...)` conditionally renders its body based on a reactive condition.

### Giving the LLM context

By default the model only sees `"[Rendered Prefab UI]"` — it doesn't see the chart. If the model needs to reason about the data, return a `ToolResult` with both a text summary and the UI:

```python
from fastmcp.tools import ToolResult

@mcp.tool(app=True)
def sales_overview(year: int) -> ToolResult:
    data = get_sales_data(year)
    total = sum(row["revenue"] for row in data)
    with Column(gap=4, css_class="p-6") as view:
        BarChart(data=data, series=[ChartSeries(data_key="revenue")])
    return ToolResult(
        content=f"Total revenue for {year}: ${total:,} across {len(data)} quarters",
        structured_content=view,
    )
```

### Content Security Policy

Apps render in a sandboxed iframe with a strict default CSP — no external network access. If a tool loads external resources (embedded iframes, CDN scripts, API calls), declare the domains:

```python
from fastmcp.apps import PrefabAppConfig, ResourceCSP

@mcp.tool(app=PrefabAppConfig(csp=ResourceCSP(frame_domains=["https://example.com"])))
def dashboard_with_embed() -> PrefabApp:
    ...
```

`PrefabAppConfig()` with no args is equivalent to `app=True`.

## 2. FastMCPApp — when the UI calls back to the server

Plain `@mcp.tool(app=True)` can call server tools too (nothing stops you putting `CallTool("save_note")` inside it), but that only stays manageable for one or two tools. `FastMCPApp` exists for when the app grows: it decides which tools the model sees vs. which are UI-only, and keeps `CallTool` references valid even after the server gets mounted under a namespace (`save_contact` → `contacts_save_contact`).

```python
from prefab_ui.actions import SetState, ShowToast
from prefab_ui.actions.mcp import CallTool
from prefab_ui.app import PrefabApp
from prefab_ui.components import Column, Form, Input, Button, Heading, ForEach, Row, Badge, Text
from prefab_ui.rx import RESULT
from fastmcp import FastMCP, FastMCPApp

app = FastMCPApp("Notes")
notes_db: list[dict] = []

@app.tool()
def add_note(title: str, body: str) -> list[dict]:
    """Save a note and return all notes."""
    notes_db.append({"title": title, "body": body})
    return list(notes_db)

@app.ui()
def notes_app() -> PrefabApp:
    """Open the notes app."""
    with Column(gap=6, css_class="p-6") as view:
        Heading("Notes")
        with ForEach("notes") as note:
            with Row(gap=2, align="center"):
                Text(note.title, css_class="font-semibold")
                Badge(note.body)
        with Form(on_submit=CallTool(
            "add_note",
            on_success=[SetState("notes", RESULT), ShowToast("Note saved!", variant="success")],
            on_error=ShowToast("Failed to save", variant="error"),
        )):
            Input(name="title", label="Title", required=True)
            Input(name="body", label="Body", required=True)
            Button("Add Note")
    return PrefabApp(view=view, state={"notes": list(notes_db)})

mcp = FastMCP("Notes Server", providers=[app])
```

Key pieces:

- **`@app.ui()`** — entry points, model-visible by default (`visibility=["model"]`). The model calls these to open the UI.
- **`@app.tool()`** — backend tools, UI-only by default (`visibility=["app"]`). Pass `model=True` if a tool should be callable by both model and UI.
- **`CallTool(name_or_function, arguments=..., on_success=..., on_error=..., result_key=...)`** — how the UI invokes a backend tool. Prefer a function reference (`CallTool(save_contact)`) over a string name — it resolves to a stable global key that survives namespacing; a string name breaks once the server is mounted (`save_contact` → `contacts_save_contact`).
  - `RESULT` (inside `on_success`) / `ERROR` (inside `on_error`) are reactive references to the call's outcome.
  - `result_key="contacts"` is shorthand for `on_success=SetState("contacts", RESULT)`.
- **`Form.from_model(PydanticModel, on_submit=...)`** — generates a whole form (inputs, labels, validation) from a Pydantic model. `str` → text input, `Literal` → select, `bool` → checkbox.
- Mount with `providers=[app]` on `FastMCP(...)` or `mcp.add_provider(app)`. Multiple apps can coexist — each gets its own global keys, so a `save` tool in two different apps never collides.
- For standalone dev, `FastMCPApp` has `app.run()` which wraps itself in a temporary `FastMCP` server.

## 3. Generative UI — let the model design it

Register one provider and the model writes Prefab Python code tailored to the request, streamed into the UI as it's generated:

```python
from fastmcp.apps.generative import GenerativeUI

mcp.add_provider(GenerativeUI())
```

This registers `generate_prefab_ui` (executes model-written Prefab code in a Pyodide sandbox and renders it), `search_prefab_components` (lets the model discover available components before writing code), and a streaming renderer. Pass `data={...}` to `generate_prefab_ui` to make earlier-conversation data available as variables in the sandboxed code.

Needs `fastmcp[apps]` (for `prefab-ui`) plus Deno for server-side validation (installs automatically on first use). The sandbox only has the Python standard library and Prefab — no NumPy/pandas/requests etc.

## 4. Custom HTML — full control

Reach for this only when Prefab's component set genuinely isn't enough (a map library, a 3D viewer, your own JS framework). You're now talking to the MCP Apps protocol directly: a tool plus a `ui://` resource containing hand-written HTML that uses the `@modelcontextprotocol/ext-apps` JS SDK for host communication.

```python
from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP

mcp = FastMCP("My App Server")

@mcp.tool(app=AppConfig(resource_uri="ui://my-app/view.html"))
def generate_chart(data: list[float]) -> str:
    return json.dumps({"values": data})

@mcp.resource(
    "ui://my-app/view.html",
    app=AppConfig(csp=ResourceCSP(resource_domains=["https://unpkg.com"])),
)
def chart_view() -> str:
    return """<html>...
    <script type="module">
      import { App } from "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";
      const app = new App({ name: "My App", version: "1.0.0" });
      app.ontoolresult = ({ content }) => { /* render */ };
      await app.connect();
    </script></html>"""
```

`AppConfig` fields: `resource_uri` (tools only), `visibility` (`["model"]`/`["app"]`/both, tools only), `csp` (`ResourceCSP` with `connect_domains`/`resource_domains`/`frame_domains`/`base_uri_domains`), `permissions` (`ResourcePermissions`, e.g. `camera={}`), `domain`, `prefers_border`. On resources, only set `csp`/`permissions`/display settings — never `resource_uri`/`visibility`.

Check host support at runtime before assuming the extension is available:

```python
from fastmcp import Context
from fastmcp.apps import AppConfig, UI_EXTENSION_ID

@mcp.tool(app=AppConfig(resource_uri="ui://my-app/view.html"))
async def my_tool(ctx: Context) -> str:
    if ctx.client_supports_extension(UI_EXTENSION_ID):
        return rich_response()
    return plain_text_response()
```

## Preview locally

```bash
fastmcp dev apps server.py
```

Runs your MCP server plus a dev UI at `http://localhost:8080` with a picker page listing your app tools — no real MCP host needed. Auto-reloads on server code changes; relaunch the tool in the browser to see UI changes.

## Common mistakes

- **No text fallback for the model.** If the model needs to reason about the data, return `ToolResult(content=..., structured_content=...)` — otherwise it only sees `"[Rendered Prefab UI]"`.
- **Forgetting CSP for external resources.** Any network request from the iframe — even to `localhost` in Custom HTML apps — needs a `ResourceCSP`/`AppConfig(csp=...)` declaration; the sandbox denies by default.
- **String-based `CallTool` references breaking under namespacing.** Use a function reference (`CallTool(save_contact)`), not `CallTool("save_contact")`, once there's any chance the server gets mounted/composed elsewhere.
- **Reaching for `FastMCPApp` too early, or too late.** One or two UI→server calls: plain `@mcp.tool(app=True)` is fine. Once you're tracking which tools are model-visible vs. UI-only, or composing multiple apps on one server, switch to `FastMCPApp`.
- **Confusing this with the TypeScript ext-apps SDK.** Both implement the same MCP Apps extension, but fastmcp's Python path (`app=True` + Prefab) and the Node path (`registerAppTool`/`registerAppResource` + a Vite-built HTML bundle) are not interchangeable — don't mix guidance from one into a project using the other, except at the Custom HTML layer where they share the same underlying protocol.

## Next steps / reference

- Full Prefab component reference (100+ components, theming): https://prefab.prefect.io/docs/components
- `fastmcp/docs/apps/architecture.mdx` — the five-stage pipeline (Python components → JSON tree → `structuredContent` → renderer iframe → host UI), useful when something isn't rendering as expected
- `fastmcp/examples/apps/contacts/contacts_server.py` — a full runnable `FastMCPApp` example
