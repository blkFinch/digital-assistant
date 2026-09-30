# Puppet MCP

A standalone stdio MCP server that displays a bundled PNG puppet in its own Tk
window. The MCP parent owns tools and state; a spawned child owns Tk and runs
`Tk.mainloop()` on the child's main thread.

## Requirements

- Python 3.10+
- MCP Python SDK `>=1.28.0,<2` (installed automatically; this release uses FastMCP 1.x)
- Tk/Tcl 8.6+ with native PNG support
- A graphical display (Linux may also need the OS package `python3-tk`)

Pillow is not required. Automated tests are headless and never construct Tk.

## Install

Editable checkout:

    cd v2/puppet-mcp
    python -m pip install -e .

Built wheel:

    python -m build
    python -m pip install dist/puppet_mcp-0.1.0-py3-none-any.whl

The installed command is `puppet-mcp`.

## Registration

Choose the puppet at registration time. Omit the environment setting for chibi.

Claude Desktop, Cursor, and JSON-based MCP clients use this server entry:

    {
      "mcpServers": {
        "puppet": {
          "command": "puppet-mcp",
          "env": { "PUPPET_MCP_PUPPET": "saki" }
        }
      }
    }

For Augment, add a stdio server in MCP settings with command `puppet-mcp` and
the same environment variable. For Claude Code or Codex, use their MCP add
command/UI to register `puppet-mcp` as a local stdio command and set the env on
that server registration. Configuration file locations and CLI flags vary by
client release; the command and environment contract do not.

Each registered server instance owns one headless broker child. Tk is imported
and the window is created lazily by the first `set_expression` call, so
registration alone does not open a window. Rendering from multiple registered
instances creates multiple windows with process-local state.

## Configuration

| Environment variable | Default | Meaning |
|---|---|---|
| `PUPPET_MCP_PUPPET` | `chibi` | Bundled pack: `chibi` or `saki` |
| `PUPPET_MCP_WINDOW_TITLE` | `AI Vtuber Puppet` | Non-blank window title |
| `PUPPET_MCP_STARTUP_TIMEOUT` | `5.0` | Positive finite startup seconds |
| `PUPPET_MCP_COMMAND_TIMEOUT` | `2.0` | Positive finite apply/shutdown seconds |

Invalid startup settings fail explicitly. Puppet selection does not change at
runtime; register a second instance to show the other pack.

## Tools

### `set_expression(expression: str, intensity: float = 0.5)`

Validates the expression and inclusive intensity range `[0.0, 1.0]`, waits for
the renderer acknowledgement, then commits state. Static PNGs do not visually
blend by intensity; the value is retained for future renderers.

    {
      "puppet": "chibi",
      "expression": "happy",
      "intensity": 0.8,
      "renderer": {
        "backend": "tk",
        "status": "ready",
        "error": null
      }
    }

### `get_current_state()`

Returns the same state shape without changing it. Renderer status is one of
`starting`, `ready`, `stopped`, or `error`.

### `list_expressions()`

    {
      "puppet": "chibi",
      "default_expression": "idle",
      "expressions": ["angry", "annoyed", "confused", "happy", "idle"]
    }

The actual list is complete and deterministically sorted.

| chibi | saki |
|---|---|
| angry | angry |
| annoyed | annoyed |
| confused | happy |
| happy | happy2 |
| idle | idle |
| laugh | laugh |
| sad | sad |
| smug | smug |
| surprised | surprised |
| thinking | thinking |

Unknown, blank, or path-like names are rejected rather than mapped to idle.
Booleans, non-finite intensities, and out-of-range values are also rejected.

## Process and window behavior

A headless child starts before the MCP request loop; Tk and its window start
lazily on the first `set_expression` call. `get_current_state` and
`list_expressions` do not open a window. Shutdown follows the stdio MCP process.
Closing the window leaves committed state unchanged, and the broker recreates
it on the next `set_expression`. A failed or timed-out render never reports
success and never commits the requested state.

Tk and image decode errors are sent back as tool/startup errors. Diagnostics go
to stderr because stdout is reserved for MCP protocol traffic.

## Troubleshooting

- **No module named tkinter:** install a Python distribution with Tk; on Debian
  or Ubuntu install the matching `python3-tk` OS package.
- **No display / couldn't connect to display:** run in a graphical desktop
  session and ensure the platform display environment is available.
- **PNG decode error:** verify Tk/Tcl 8.6+; the renderer intentionally uses
  native `tkinter.PhotoImage(file=...)` rather than Pillow.
- **Startup/apply timeout:** increase the corresponding timeout environment
  variable and inspect stderr. Values must remain finite and greater than zero.

## Development

Install test/build tooling separately, then run:

    python -m pytest tests -v
    python -m pytest tests/test_spawn_lifecycle.py -v
    python -m build

Manual smoke testing should render every listed expression at intensities 0,
0.5, and 1 for each pack, test window-close restart, and verify no child remains
after the MCP client exits.

Runtime puppet switching and viewer lifecycle tools are intentionally deferred.
They can be added later without changing these three baseline tools.