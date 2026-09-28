"""Startup context assembly for agent sessions."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from . import memory_store, personality, search


PROFILE_TYPES = {"identity", "relationship"}
PREFERENCE_TYPES = {"preference", "habit"}
BOUNDARY_TYPES = {"boundary", "constraint"}
COMMUNICATION_TERMS = {
    "address",
    "called",
    "communication",
    "concise",
    "emoji",
    "emoticon",
    "format",
    "formatting",
    "name",
    "preferred name",
    "style",
    "tone",
}


def build_session_context(
    *,
    data_dir: Path,
    ltm_path: Path,
    ltm_name: str = "",
    token_budget: int = 3000,
) -> Dict[str, Any]:
    """Build a compact startup context package for agents.

    This intentionally avoids loading the full LTM. Only high-priority memories
    are eligible for startup context; task-specific recall still belongs to
    search_memories.
    """
    personality_text = personality.load_personality(data_dir)
    active_name = personality.get_active_personality_name(data_dir) or "(default)"

    items = memory_store.load_sanitized_ltm(ltm_path)
    critical = [
        item for item in items
        if isinstance(item, dict) and _priority(item) >= 70
    ]
    critical.sort(
        key=lambda item: (
            _priority(item),
            str(item.get("last_updated", "")),
            str(item.get("created_at", "")),
        ),
        reverse=True,
    )

    memory_budget = max(1, token_budget - _estimate_tokens(personality_text))
    compact_memories, memory_tokens = search.apply_token_budget(
        [(item, 1.0) for item in critical],
        detail="summary",
        token_budget=memory_budget,
    )
    by_id = {item.get("id"): item for item in critical}

    user_identity: List[Dict[str, Any]] = []
    user_preferences: List[Dict[str, Any]] = []
    critical_boundaries: List[Dict[str, Any]] = []
    communication_preferences: List[Dict[str, Any]] = []
    other_critical_memories: List[Dict[str, Any]] = []

    for compact in compact_memories:
        original = by_id.get(compact.get("id"), {})
        mem_type = compact.get("type", "")
        subject = compact.get("subject", "")

        if mem_type in BOUNDARY_TYPES:
            critical_boundaries.append(compact)
        elif subject == "user" and mem_type in PROFILE_TYPES:
            user_identity.append(compact)
        elif subject == "user" and mem_type in PREFERENCE_TYPES:
            user_preferences.append(compact)
        else:
            other_critical_memories.append(compact)

        if _is_communication_memory(original):
            communication_preferences.append(compact)

    return {
        "personality": {
            "active_name": active_name,
            "content": personality_text,
        },
        "user_profile": {
            "preferred_name": _extract_preferred_name(critical),
            "identity": user_identity,
            "preferences": user_preferences,
        },
        "critical_boundaries": critical_boundaries,
        "communication_preferences": communication_preferences,
        "other_critical_memories": other_critical_memories,
        "metadata": {
            "ltm_name": ltm_name,
            "estimated_tokens": _estimate_tokens(personality_text) + memory_tokens,
            "total_available_memories": len(items),
            "startup_memory_candidates": len(critical),
        },
    }


def _priority(item: Dict[str, Any]) -> int:
    try:
        return int(item.get("priority", 50) or 50)
    except (TypeError, ValueError):
        return 50


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _is_communication_memory(item: Dict[str, Any]) -> bool:
    haystack = " ".join([
        str(item.get("content", "")),
        str(item.get("summary", "")),
        str(item.get("reason", "")),
    ]).lower()
    return any(term in haystack for term in COMMUNICATION_TERMS)


def _extract_preferred_name(items: List[Dict[str, Any]]) -> str:
    candidates: List[Tuple[int, str]] = []
    patterns = [
        re.compile(r"\bcalled\s+([A-Z][A-Za-z0-9_-]{1,40})\b"),
        re.compile(r"\bcall me\s+([A-Z][A-Za-z0-9_-]{1,40})\b", re.IGNORECASE),
        re.compile(r"\bname is\s+([A-Z][A-Za-z0-9_-]{1,40})\b", re.IGNORECASE),
        re.compile(r"\bpreferred name(?: is|:)?\s+([A-Z][A-Za-z0-9_-]{1,40})\b", re.IGNORECASE),
    ]

    for item in items:
        if item.get("subject") != "user":
            continue
        if item.get("type") not in PROFILE_TYPES | PREFERENCE_TYPES:
            continue
        text = " ".join([
            str(item.get("summary", "")),
            str(item.get("content", "")),
        ])
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                candidates.append((_priority(item), match.group(1)))
                break

    if not candidates:
        return ""

    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    return candidates[0][1]
