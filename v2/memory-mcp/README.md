# Memory MCP Server

Persistent memory and personality for any AI coding agent. Memories and personality carry across sessions, repos, and agents.

## Install

```bash
cd v2/memory-mcp
pip install -e .
```

## Register

**Codex CLI:**
```bash
codex mcp add memory -- memory-mcp
```

Or edit `~/.codex/config.toml`:
```toml
[mcp_servers.memory]
command = "memory-mcp"
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{ "mcpServers": { "memory": { "command": "memory-mcp" } } }
```

**Augment / Cursor:** Add `memory-mcp` as an MCP server in settings.

## Tools

| Tool | Description |
|------|-------------|
| `get_session_context` | Startup package with active personality, user profile, critical boundaries, communication preferences, and other high-priority memories |
| `read_memories` | Load memories by priority threshold. Use `min_priority=70` at startup for critical context only |
| `search_memories` | Keyword search with token budgeting. Returns summaries by default |
| `search_memories_tool` | Backward-compatible alias for `search_memories` |
| `get_memory` | Get full content of a single memory by ID |
| `write_memory` | Create a new memory (type, subject, content, confidence, priority, reason) |
| `update_memory` | Update or reinforce an existing memory |
| `delete_memory` | Remove a memory by ID |
| `get_personality` | Read active personality markdown |
| `list_personalities` | List available personality files |
| `set_personality` | Switch active personality |

## Data Directory

Defaults to `~/.ai-memory/`. Override with `MEMORY_MCP_DATA_DIR` env var.

```
~/.ai-memory/
├── ltm.json              # Long-term memory store
├── revision_log.jsonl    # Audit trail
├── personality.md        # Default personality
├── active_personality.txt
├── personalities/        # Named personalities (add .md files here)
└── prompts/
```

## Add a Personality

Drop a markdown file in `~/.ai-memory/personalities/`:

```markdown
# Pirate Assistant
You are a helpful coding assistant who speaks like a pirate.
```

Then call `set_personality("pirate")` or ask your agent to switch.

## AGENTS.md

Add to any repo to instruct your agent:

```markdown
## Memory & Personality

You have access to a Memory MCP server.

On startup:
1. Call `get_session_context()` and adopt the returned personality and communication preferences

During work:
- `search_memories(query="...")` before substantial decisions
- `write_memory(...)` when the user shares preferences or important info
- Set priority appropriately: 90+ for boundaries, 70-89 for key prefs, <70 for minor details
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MEMORY_MCP_DATA_DIR` | `~/.ai-memory/` | Data directory |
| `LTM_NAME` | _(empty)_ | Named memory store for full profile isolation |

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```
