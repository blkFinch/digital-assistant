"""Keyword search over memories with token budgeting and detail levels."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token (good enough for budgeting)."""
    return max(1, len(text) // 4)


def _estimate_item_tokens(item: Dict[str, Any], detail: str) -> int:
    """Estimate token count for a single result item."""
    if detail == "summary":
        # id + summary + type + subject + priority + relevance
        parts = [
            str(item.get("id", "")),
            str(item.get("summary", "")),
            str(item.get("type", "")),
            str(item.get("subject", "")),
            str(item.get("priority", "")),
        ]
        return _estimate_tokens(" ".join(parts)) + 10  # overhead for JSON structure
    else:
        # Full item serialization
        import json
        return _estimate_tokens(json.dumps(item))


# ---------------------------------------------------------------------------
# Keyword search
# ---------------------------------------------------------------------------

def keyword_search(
    memories: List[Dict[str, Any]],
    query: str,
    type_filter: str = "",
    subject_filter: str = "",
) -> List[Tuple[Dict[str, Any], float]]:
    """Search memories by keyword matching. Returns (memory, relevance_score) pairs.

    Scoring:
    - Each query token that appears in the memory's searchable fields adds to the score
    - Score is normalized to 0.0–1.0 based on how many tokens matched
    - Priority gives a mild boost (not an override)
    """
    tokens = query.lower().split()
    if not tokens:
        return []

    scored: List[Tuple[Dict[str, Any], float]] = []

    for mem in memories:
        if not isinstance(mem, dict):
            continue
        if type_filter and mem.get("type") != type_filter:
            continue
        if subject_filter and mem.get("subject") != subject_filter:
            continue

        searchable = " ".join([
            str(mem.get("content", "")),
            str(mem.get("summary", "")),
            str(mem.get("type", "")),
            str(mem.get("subject", "")),
            str(mem.get("reason", "")),
        ]).lower()

        match_count = sum(1 for t in tokens if t in searchable)
        if match_count == 0:
            continue

        match_score = match_count / len(tokens)
        # Priority gives a mild boost but never dominates keyword relevance.
        # Scale match_score to 0.0–0.8 range, priority to 0.0–0.2 range.
        priority_boost = (mem.get("priority", 50) or 50) / 100 * 0.2
        final_score = match_score * 0.8 + priority_boost

        scored.append((mem, round(final_score, 3)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Result formatting with token budgeting
# ---------------------------------------------------------------------------

def _to_summary(mem: Dict[str, Any], relevance: float) -> Dict[str, Any]:
    """Format a memory as a compact summary record."""
    return {
        "id": mem.get("id", ""),
        "summary": mem.get("summary", "") or mem.get("content", "")[:120],
        "type": mem.get("type", ""),
        "subject": mem.get("subject", ""),
        "priority": mem.get("priority", 50),
        "relevance": relevance,
    }


def _to_full(mem: Dict[str, Any], relevance: float) -> Dict[str, Any]:
    """Format a memory as a full record with relevance score."""
    result = dict(mem)
    result["relevance"] = relevance
    return result


def apply_token_budget(
    scored: List[Tuple[Dict[str, Any], float]],
    *,
    detail: str = "summary",
    token_budget: int = 4000,
) -> Tuple[List[Dict[str, Any]], int]:
    """Apply token budgeting to scored results.

    Returns (results, estimated_tokens_used).
    """
    formatter = _to_summary if detail == "summary" else _to_full
    results: List[Dict[str, Any]] = []
    tokens_used = 0

    for mem, relevance in scored:
        formatted = formatter(mem, relevance)
        item_tokens = _estimate_item_tokens(formatted, detail)

        if tokens_used + item_tokens > token_budget and results:
            # Already have some results; stop before exceeding budget
            break

        results.append(formatted)
        tokens_used += item_tokens

    return results, tokens_used


# ---------------------------------------------------------------------------
# Public search API
# ---------------------------------------------------------------------------

def search_memories(
    memories: List[Dict[str, Any]],
    query: str,
    *,
    type_filter: str = "",
    subject_filter: str = "",
    detail: str = "summary",
    token_budget: int = 4000,
) -> Dict[str, Any]:
    """Full search pipeline: keyword match → rank → budget → format.

    Returns {results: [...], estimated_tokens: int, total_matches: int}.
    """
    scored = keyword_search(memories, query, type_filter, subject_filter)
    results, tokens_used = apply_token_budget(
        scored, detail=detail, token_budget=token_budget,
    )
    return {
        "results": results,
        "estimated_tokens": tokens_used,
        "total_matches": len(scored),
    }
