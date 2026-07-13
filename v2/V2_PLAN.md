# AI Vtuber V2 — MCP Server Decomposition Plan

## Vision

V1 (`core_agent/`) is a monolithic Python app where the LLM, memory, TTS, and puppet display are all wired together in one process. V2 decomposes it into **standalone MCP servers** — small, focused peripherals that any coding agent (Claude, Augment, Codex, Cursor) can use. The agent itself becomes the "brain"; the MCP servers provide capabilities.

```
┌─────────────────────────────────────────────────┐
│  Any Coding Agent (Claude, Augment, Codex, ...) │
│  ┌───────────┐  ┌───────────┐  ┌─────────────┐ │
│  │ Memory MCP│  │ Puppet MCP│  │  TTS MCP    │ │
│  │  (stdio)  │  │  (stdio)  │  │  (stdio)    │ │
│  └─────┬─────┘  └─────┬─────┘  └──────┬──────┘ │
└────────┼───────────────┼───────────────┼────────┘
         │               │               │
   ~/.ai-memory/    PNG assets      Audio APIs
```

## User Story

1. Install the Memory MCP server (`pip install -e ./v2/memory-mcp`)
2. Register it in your agent's MCP config (Claude Desktop, Cursor, Augment, etc.)
3. Add a line to `AGENTS.md` in any repo telling the agent to use personality + memory tools
4. The agent adopts the personality voice, remembers your preferences across sessions
5. Move to a different repo — same personality, same memories, zero setup

---

## Architecture: Memories & Personalities

### Data Directory Layout

All data lives in a single, user-global directory (default `~/.ai-memory/`), configurable via `MEMORY_MCP_DATA_DIR` env var:

```
~/.ai-memory/
├── ltm.json                      # Default long-term memory store
├── revision_log.jsonl            # Audit trail for all memory changes
├── personality.md                # Default personality (active by default)
├── active_personality.txt        # Name of the currently active personality
├── personalities/                # User-created personalities
│   ├── yuki.md
│   ├── professional.md
│   └── pirate.md
├── prompts/
│   └── reflection_prompt.txt     # Template agents can use for memory extraction
└── ltm/                          # Named LTM stores (for multi-profile isolation)
    └── yuki/
        ├── ltm.json
        └── revision_log.jsonl
```

### How Memories Work

Memories are JSON objects stored in `ltm.json`. Each memory has:

```json
{
  "id": "mem_20260712T153000Z123456",
  "type": "preference",
  "subject": "user",
  "content": "Wants to be called Galen",
  "summary": "User prefers to be called Galen",
  "confidence": 0.9,
  "priority": 80,
  "reason": "User explicitly asked",
  "created_at": "2026-07-12T15:30:00Z",
  "last_updated": "2026-07-12T15:30:00Z",
  "strength": 1
}
```

| Field | Purpose |
|-------|---------|
| `type` | Category: `preference`, `relationship`, `boundary`, `identity`, `habit`, `skill`, `decision`, `constraint`, `failed_approach` |
| `subject` | Who this is about: `user`, `assistant`, `other` |
| `content` | Full memory text — rationale, context, alternatives considered |
| `summary` | One-line summary for compact retrieval (auto-generated from content if omitted) |
| `confidence` | 0.0–1.0 — how certain we are this is accurate |
| `priority` | 0–100 — retrieval importance. Critical boundaries get 90+, minor preferences get 20–40 |
| `strength` | Incremented each time the memory is reinforced. **Not the same as priority** — a frequently repeated minor preference should not outrank a critical security constraint |
| `reason` | Why this memory was created or updated |

#### Priority vs Strength

These are intentionally separate concepts:

- **Priority** = how important is this memory? Should it surface automatically? A security boundary like "never send screen contents to cloud services without confirmation" is priority 95 even if it's only been stated once.
- **Strength** = how often has this been reinforced? A minor formatting preference might have strength 10 from repeated mentions, but priority 20.

Memories with `priority >= 70` are considered **critical** and are auto-loaded at startup without needing a search match. Everything else requires relevance matching via `search_memories`.

#### Two-Stage Retrieval Model

The agent does **not** load all memories at startup. Instead:

**1. Startup retrieval** — fetch only critical context:
- Active personality (`get_personality()`)
- High-priority memories (`read_memories(min_priority=70)`) — user identity, security boundaries, key constraints
- This is a small, stable set that rarely changes

**2. Task-specific retrieval** — search when doing real work:
- Before making substantial decisions, the agent calls `search_memories()` with a query relevant to the task
- This is far more accurate than trying to predict everything relevant at startup
- The AGENTS.md instructs the agent to search before decisions, not just once at the beginning

The calling agent is responsible for deciding what to remember. It calls `write_memory()` when the user shares something worth persisting. There is no built-in LLM reflection call — the agent IS the LLM.

Memories persist across all sessions, all repos, all agents. They are **global to the user**.

#### Memories Are Shared Across Personalities

Switching personalities does **not** change which memories are visible. Your name, your preferences, your boundaries — those are facts about *you*, not about the assistant's persona. Whether the agent is speaking as "Yuki" or as "Pirate Assistant," it still knows your name and your tech stack.

This is by design: personality defines *how* the agent talks, memories define *what* it knows. They are orthogonal.

#### LTM_NAME: Full Profile Isolation (Advanced)

The `LTM_NAME` env var exists for a separate use case: **complete memory isolation between profiles.** This is not per-personality — it's for scenarios like keeping "work" and "personal" contexts fully separated.

| | Default LTM (`ltm.json`) | `LTM_NAME=work` (`ltm/work/ltm.json`) |
|--|--|--|
| **Default personality** | Shared memories, default voice | Work-only memories, default voice |
| **`set_personality("pirate")`** | Shared memories, pirate voice | Work-only memories, pirate voice |

`LTM_NAME` is set at MCP registration time via env var, not at runtime:

```json
// Normal — one global memory store shared by all personalities
{ "command": "memory-mcp" }

// Isolated — separate memory silo for work context
{ "command": "memory-mcp", "env": { "LTM_NAME": "work" } }
```

**Most users will never use `LTM_NAME`.** The default is one shared memory store, all personalities see the same memories, and that's the recommended setup.

### How Personalities Work

A personality is a **markdown file** that gets injected into the agent's system prompt. It defines voice, tone, mannerisms, and behavioral rules.

#### Resolution Order

1. If `active_personality.txt` contains a name → load `personalities/<name>.md`
2. Otherwise → load `personality.md` (the default)

#### Adding a New Personality

Create a markdown file in `~/.ai-memory/personalities/`:

```markdown
# Pirate Assistant

You are a helpful coding assistant who speaks like a pirate.
- Use nautical metaphors for technical concepts
- Call the user "captain"
- Stay technically accurate despite the persona
- Keep it fun but not annoying
```

Then activate it: the agent calls `set_personality("pirate")`.

Every agent session in every repo will now use the pirate voice until you switch again.

#### Setting a New Default

**Option A**: Edit `~/.ai-memory/personality.md` directly — this is the fallback used when no named personality is active.

**Option B**: Create a personality in `personalities/`, then call `set_personality("name")` to make it active. The original `personality.md` remains as a fallback if you ever call `set_personality("")`.

#### Personality + Memory Interaction

The agent loads BOTH personality AND memories into context each session:

- **Personality** defines *how* the agent behaves (voice, tone, rules)
- **Memories** define *what* the agent knows (user preferences, facts, relationships)
- Switching personalities never causes amnesia about the user
- Together they create a consistent, personalized experience across sessions and repos

---

## Phase 1: Memory MCP Server (`v2/memory-mcp/`)

### Package Structure

```
v2/memory-mcp/
├── pyproject.toml              # name="memory-mcp", entry point: memory-mcp
├── src/memory_mcp/
│   ├── __init__.py
│   ├── server.py               # MCP server — tool/resource registration, main()
│   ├── memory_store.py         # LTM operations (ported from memory_system.py)
│   ├── search.py               # Keyword search over memories
│   ├── personality.py          # Personality load/list/switch
│   └── config.py               # Data directory resolution
└── tests/
    ├── test_memory_store.py
    ├── test_search.py
    └── test_server.py
```

### Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `read_memories` | `min_priority?`, `type_filter?`, `subject_filter?`, `token_budget?` | Retrieve memories by priority threshold. Use at startup with `min_priority=70` for critical context |
| `search_memories` | `query`, `type_filter?`, `subject_filter?`, `detail?`, `token_budget?` | Keyword search for task-relevant memories. Default returns summaries |
| `get_memory` | `memory_id` | Get full content of a single memory by ID |
| `write_memory` | `type`, `subject`, `content`, `summary?`, `confidence`, `priority`, `reason` | Create a new memory item |
| `update_memory` | `memory_id`, `content?`, `summary?`, `confidence?`, `priority?`, `reason?` | Update or reinforce an existing memory |
| `delete_memory` | `memory_id` | Remove a memory by ID |
| `get_personality` | `name?` | Read personality markdown (empty = active/default) |
| `list_personalities` | — | List available personality files |
| `set_personality` | `name` | Switch active personality (empty = revert to default) |

### Search & Retrieval

#### Two-Stage API: Summaries First, Full Content Second

`search_memories` returns **compact summary records** by default:

```json
{
  "id": "mem_123",
  "summary": "MCP is the control plane; OutputBus handles live events.",
  "type": "decision",
  "priority": 75,
  "relevance": 0.94
}
```

The agent calls `get_memory(memory_id)` only when it needs full rationale, alternatives considered, or source details. This prevents a few long memories from consuming the entire context budget.

The `detail` parameter controls this:
- `detail="summary"` (default) — compact records with `id`, `summary`, `type`, `subject`, `priority`, `relevance`
- `detail="full"` — complete memory objects including full `content`

#### Token Budgeting (Server-Side)

Instead of a naive `limit=20` (where 10 memories might be tiny and 1 enormous), both `read_memories` and `search_memories` support `token_budget`:

```python
search_memories(query="auth architecture", token_budget=2000)
```

The server:
1. Ranks candidates by relevance (search) or priority (read)
2. Adds results in rank order
3. Stops before exceeding the budget
4. Returns estimated token count in the response metadata
5. Prefers summaries where full content won't fit

This makes behavior consistent across Claude, Codex, Augment, and local agents regardless of their context window sizes.

When `token_budget` is not specified, falls back to a reasonable default (e.g. 4000 tokens).

#### Keyword Search Implementation

Case-insensitive token matching against memory `content`, `summary`, `type`, `subject`, and `reason` fields. The query is split into tokens; each memory is scored by how many tokens match across its fields, with a boost from `priority`. Results are ranked by combined score.

```python
def search(
    memories: list[dict],
    query: str,
    type_filter: str = "",
    subject_filter: str = "",
) -> list[tuple[dict, float]]:
    """Keyword search across memory fields. Returns (memory, relevance_score) pairs."""
    tokens = query.lower().split()
    scored = []
    for mem in memories:
        if type_filter and mem.get("type") != type_filter:
            continue
        if subject_filter and mem.get("subject") != subject_filter:
            continue
        searchable = " ".join([
            mem.get("content", ""),
            mem.get("summary", ""),
            mem.get("type", ""),
            mem.get("subject", ""),
            mem.get("reason", ""),
        ]).lower()
        match_score = sum(1 for t in tokens if t in searchable) / len(tokens)
        if match_score > 0:
            # Priority gives a mild boost, not an override
            priority_boost = mem.get("priority", 50) / 100 * 0.2
            scored.append((mem, match_score + priority_boost))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
```

Token budgeting and detail level are applied after ranking, in the server tool handler.

> **Future**: Semantic search via embeddings (e.g. `sentence-transformers/all-MiniLM-L6-v2`) can be layered in later as an optional dependency. The tool interface stays the same — only the ranking logic changes.

### Resources

| URI | Description |
|-----|-------------|
| `memory://ltm` | Current LTM contents as JSON |
| `memory://personality` | Active personality text |
| `memory://revision-log` | Audit trail (last 100 entries) |
| `memory://reflection-prompt` | Reflection prompt template for agents that want it |

### What Gets Ported from V1

| New File | Source | Changes |
|----------|--------|---------|
| `memory_store.py` | `core_agent/app/memory/memory_system.py` | Remove config import, all functions take explicit `Path` args |
| `personality.py` | `core_agent/app/config.py` + `core_agent/app/llm/prompts.py` | Extract personality loading/listing |
| `config.py` | New | Standalone data dir resolution |
| `server.py` | New | MCP wiring |

### Installation & Registration

```bash
cd v2/memory-mcp
pip install -e .
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp",
      "env": { "LTM_NAME": "yuki" }
    }
  }
}
```

**Augment**: Add to MCP server settings in VS Code with the same command.

**AGENTS.md** (drop into any repo):
```markdown
## Memory & Personality

You have access to a Memory MCP server.

### On startup:
1. Call `get_personality()` and adopt that voice and tone for the session
2. Call `read_memories(min_priority=70)` to load critical context — user identity, security
   boundaries, key constraints. Do NOT load all memories.

### During work:
- Before making substantial decisions, search for relevant memories:
  `search_memories(query="relevant terms for the current task")`
- Use `get_memory(id)` only when you need full rationale behind a search result
- When the user shares preferences, facts, or constraints, persist them with `write_memory()`
- Set priority appropriately: 90+ for security/boundaries, 70-89 for key preferences,
  below 70 for minor details

### Do NOT:
- Dump all memories into context at startup
- Treat every piece of information as equally important
- Skip searching before architectural or design decisions
```

---

## Phase 2: Puppet MCP Server (`v2/puppet-mcp/`)

Controls the avatar display. Spawns a Tk viewer on a background thread; MCP tools send commands via thread-safe queue.

### Tools
- `set_expression(expression, intensity)` — control avatar emotion
- `get_current_state()` — current expression + intensity
- `list_expressions()` — available expressions from PNG assets

### Ported From
- `core_agent/app/png_viewer.py` → `viewer.py`
- Queue pattern from `core_agent/app/dev_cockpit.py`

---

## Phase 3: TTS MCP Server (`v2/tts-mcp/`)

Text-to-speech synthesis and audio playback.

### Tools
- `speak(text, voice?)` — synthesize + play audio
- `stop()` — halt current playback
- `set_voice(voice)` / `list_voices()` / `set_provider(provider)`

### Ported From
- `core_agent/app/tts/openai_client.py`
- `core_agent/app/tts/elevenlabs_client.py`
- `core_agent/app/tts/audio_player.py`

---

## Phase 4: Retire `core_agent/` (Future, Optional)

Once all three MCP servers are working, `core_agent/` can be retired or converted to an MCP client that orchestrates the servers. No work needed now — V1 stays fully functional throughout.

---

## Rollback

All V2 work is additive under `v2/`. Delete the directory to revert. Zero changes to `core_agent/`.
