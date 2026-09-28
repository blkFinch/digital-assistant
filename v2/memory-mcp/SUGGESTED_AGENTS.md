this is a sample of an AGENTS.md to use in projects that want to use the memory mcp:

## Memory & Personality

Use the configured Memory MCP server in this workspace.

At the beginning of each new session:

1. Call `get_session_context()` to load the active personality, user profile, critical boundaries, communication preferences, and other high-priority memories.
2. Adopt the returned personality and communication preferences.
3. Address the user using the preferred name returned in the user profile.

Do not load the complete long-term memory store.

Use `search_memories()` when previous context could materially improve the current task, especially before:

* making architectural decisions
* introducing or replacing dependencies
* changing public interfaces or data models
* revisiting previously attempted work
* assuming a user preference
* modifying a subsystem with known constraints

Search using the current task, repository, and subsystem.

Use `get_memory()` when the full rationale or history of a search result is needed.

Use `set_user_preference()` for explicit, durable user-wide preferences. Use `write_memory()` for durable facts, decisions, discoveries, rejected approaches, and relationship history.

Do not store routine commands, temporary errors, obvious code facts, or short-lived conversational states.

## Project Context

This repo is an active project to outfit CLI agents with a suite of MCP servers that provide memory and personality persistence across sessions and repositories. When working here, remember that goal — features, fixes, and design decisions should serve that vision.
