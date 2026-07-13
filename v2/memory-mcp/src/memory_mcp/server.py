"""Memory MCP Server — tools and resources for persistent memory + personality."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import config, memory_store, personality, search

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

DATA_DIR = config.get_data_dir()
LTM_NAME = config.get_ltm_name()
config.bootstrap_data_dir(DATA_DIR)

LTM_PATH = config.get_ltm_path(DATA_DIR, LTM_NAME)
REVISION_LOG_PATH = config.get_revision_log_path(DATA_DIR, LTM_NAME)

mcp = FastMCP("memory-mcp", json_response=True)


# ===================================================================
# Tools — Memory CRUD
# ===================================================================

@mcp.tool()
def read_memories(
    min_priority: int = 0,
    type_filter: str = "",
    subject_filter: str = "",
    token_budget: int = 4000,
) -> str:
    """Retrieve memories by priority threshold.

    Use at startup with min_priority=70 to load only critical context.
    Use min_priority=0 to get everything (subject to token_budget).
    """
    items = memory_store.load_sanitized_ltm(LTM_PATH)

    # Filter by priority
    if min_priority > 0:
        items = [m for m in items if (m.get("priority", 50) or 50) >= min_priority]

    # Filter by type/subject
    if type_filter:
        items = [m for m in items if m.get("type") == type_filter]
    if subject_filter:
        items = [m for m in items if m.get("subject") == subject_filter]

    # Apply token budgeting (return summaries)
    scored = [(m, 1.0) for m in items]  # all equally relevant for read
    results, tokens_used = search.apply_token_budget(
        scored, detail="summary", token_budget=token_budget,
    )
    return json.dumps({
        "memories": results,
        "estimated_tokens": tokens_used,
        "total": len(items),
    }, indent=2)


@mcp.tool()
def search_memories_tool(
    query: str,
    type_filter: str = "",
    subject_filter: str = "",
    detail: str = "summary",
    token_budget: int = 4000,
) -> str:
    """Search memories by keyword. Returns ranked results.

    Use before making substantial decisions to find relevant context.
    detail: "summary" (default, compact) or "full" (complete content).
    """
    items = memory_store.load_sanitized_ltm(LTM_PATH)
    result = search.search_memories(
        items, query,
        type_filter=type_filter,
        subject_filter=subject_filter,
        detail=detail,
        token_budget=token_budget,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def get_memory(memory_id: str) -> str:
    """Get full content of a single memory by ID.

    Use after search_memories returns a summary you want to read in full.
    """
    item = memory_store.get_memory_by_id(LTM_PATH, memory_id)
    if item is None:
        return json.dumps({"error": f"Memory '{memory_id}' not found"})
    return json.dumps(item, indent=2)


@mcp.tool()
def write_memory(
    type: str,
    subject: str,
    content: str,
    confidence: float,
    priority: int,
    reason: str,
    summary: str = "",
) -> str:
    """Create a new memory item.

    type: preference|relationship|boundary|identity|habit|skill|decision|constraint|failed_approach
    subject: user|assistant|other
    priority: 0-100 (90+ for critical boundaries, 70-89 for key preferences, below 70 for minor details)
    """
    item = memory_store.create_memory(
        ltm_path=LTM_PATH,
        revision_log_path=REVISION_LOG_PATH,
        mem_type=type,
        subject=subject,
        content=content,
        confidence=confidence,
        priority=priority,
        reason=reason,
        summary=summary,
    )
    return json.dumps(item, indent=2)


@mcp.tool()
def update_memory(
    memory_id: str,
    content: str = "",
    summary: str = "",
    confidence: float = -1,
    priority: int = -1,
    reason: str = "",
) -> str:
    """Update or reinforce an existing memory by ID.

    Only provide fields you want to change. Strength is auto-incremented.
    """
    item = memory_store.update_memory(
        ltm_path=LTM_PATH,
        revision_log_path=REVISION_LOG_PATH,
        memory_id=memory_id,
        content=content if content else None,
        summary=summary if summary else None,
        confidence=confidence if confidence >= 0 else None,
        priority=priority if priority >= 0 else None,
        reason=reason,
    )
    if item is None:
        return json.dumps({"error": f"Memory '{memory_id}' not found"})
    return json.dumps(item, indent=2)


@mcp.tool()
def delete_memory(memory_id: str) -> str:
    """Remove a memory by ID."""
    deleted = memory_store.delete_memory(
        ltm_path=LTM_PATH,
        revision_log_path=REVISION_LOG_PATH,
        memory_id=memory_id,
    )
    if not deleted:
        return json.dumps({"error": f"Memory '{memory_id}' not found"})
    return json.dumps({"deleted": memory_id})


# ===================================================================
# Tools — Personality
# ===================================================================

@mcp.tool()
def get_personality(name: str = "") -> str:
    """Read personality markdown. Empty name = active/default personality."""
    try:
        text = personality.load_personality(DATA_DIR, name)
        return text if text else "(no personality configured)"
    except FileNotFoundError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_personalities() -> str:
    """List available personality files."""
    items = personality.list_personalities(DATA_DIR)
    return json.dumps(items, indent=2)


@mcp.tool()
def set_personality(name: str) -> str:
    """Switch active personality. Empty name = revert to default."""
    try:
        result = personality.set_active_personality(DATA_DIR, name)
        if result:
            return json.dumps({"active_personality": result})
        return json.dumps({"active_personality": "(default)"})
    except FileNotFoundError as e:
        return json.dumps({"error": str(e)})


# ===================================================================
# Resources
# ===================================================================

@mcp.resource("memory://ltm")
def ltm_resource() -> str:
    """Current LTM contents as JSON."""
    items = memory_store.load_sanitized_ltm(LTM_PATH)
    return json.dumps(items, indent=2)


@mcp.resource("memory://personality")
def personality_resource() -> str:
    """Active personality text."""
    return personality.load_personality(DATA_DIR)


@mcp.resource("memory://revision-log")
def revision_log_resource() -> str:
    """Audit trail (last 100 entries)."""
    entries = memory_store.load_revision_log(REVISION_LOG_PATH, last_n=100)
    return json.dumps(entries, indent=2)


@mcp.resource("memory://reflection-prompt")
def reflection_prompt_resource() -> str:
    """Reflection prompt template for agents that want it."""
    prompt_path = config.get_reflection_prompt_path(DATA_DIR)
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return "(no reflection prompt configured)"


# ===================================================================
# Entry point
# ===================================================================

def main():
    mcp.run(transport="stdio")
