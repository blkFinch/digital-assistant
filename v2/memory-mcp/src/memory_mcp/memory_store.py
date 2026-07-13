"""Long-term memory storage operations.

Ported from core_agent/app/memory/memory_system.py with:
- Updated schema: added `priority` and `summary` fields
- All functions take explicit Path args (no global config dependency)
- Revision log path passed explicitly
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class MemoryItem:
    id: str
    type: str          # preference | relationship | boundary | identity | habit | skill | decision | constraint | failed_approach
    subject: str       # user | assistant | other
    content: str
    confidence: float  # 0.0–1.0
    reason: str
    created_at: str
    last_updated: str
    priority: int = 50      # 0–100, retrieval importance (90+ = critical)
    summary: str = ""       # one-line compact version for search results
    strength: int = 1       # reinforcement count (NOT the same as priority)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "subject": self.subject,
            "content": self.content,
            "summary": self.summary,
            "confidence": self.confidence,
            "priority": self.priority,
            "reason": self.reason,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "strength": self.strength,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_memory_id() -> str:
    return f"mem_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ%f')}"


def _new_event_id() -> str:
    return f"evt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ%f')}"


def _safe_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _auto_summary(content: str) -> str:
    """Generate a simple summary by taking the first sentence / 120 chars."""
    first_line = content.split("\n")[0].strip()
    if len(first_line) <= 120:
        return first_line
    return first_line[:117] + "..."


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def load_ltm(path: Path) -> List[Dict[str, Any]]:
    """Load the long-term memory store from a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def load_sanitized_ltm(path: Path) -> List[Dict[str, Any]]:
    """Load LTM sorted by last_updated (newest first), dicts only."""
    items = load_ltm(path)
    valid = [i for i in items if isinstance(i, dict)]
    valid.sort(
        key=lambda i: (str(i.get("last_updated", "")), str(i.get("created_at", ""))),
        reverse=True,
    )
    return valid


def save_ltm(items: List[Dict[str, Any]], path: Path) -> Path:
    """Persist LTM items to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Revision log
# ---------------------------------------------------------------------------

def _append_revision_log(entry: Dict[str, Any], revision_log_path: Path) -> None:
    revision_log_path.parent.mkdir(parents=True, exist_ok=True)
    with revision_log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False))
        f.write("\n")


def load_revision_log(path: Path, last_n: int = 100) -> List[Dict[str, Any]]:
    """Load the last N entries from the revision log."""
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []
    return entries[-last_n:]


# ---------------------------------------------------------------------------
# Single-item CRUD (used by MCP tools directly)
# ---------------------------------------------------------------------------

def create_memory(
    *,
    ltm_path: Path,
    revision_log_path: Path,
    mem_type: str,
    subject: str,
    content: str,
    confidence: float,
    priority: int,
    reason: str,
    summary: str = "",
    source_session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a single new memory item. Returns the created item dict."""
    items = load_ltm(ltm_path)
    now = _now_iso()
    mem_id = _new_memory_id()

    if not summary:
        summary = _auto_summary(content)

    mem = MemoryItem(
        id=mem_id,
        type=mem_type,
        subject=subject,
        content=content,
        summary=summary,
        confidence=confidence,
        priority=_safe_int(priority, default=50),
        reason=reason,
        created_at=now,
        last_updated=now,
        strength=1,
    )
    item_dict = mem.to_dict()
    items.append(item_dict)
    save_ltm(items, ltm_path)

    log_entry = {
        "ts": now,
        "event_id": _new_event_id(),
        "source": {"source_session_id": source_session_id, "source_stage": "mcp_tool"},
        "action": "create",
        "target_id": mem_id,
        "before": None,
        "after": item_dict,
        "reason": reason,
    }
    _append_revision_log(log_entry, revision_log_path)

    return item_dict


def update_memory(
    *,
    ltm_path: Path,
    revision_log_path: Path,
    memory_id: str,
    content: Optional[str] = None,
    summary: Optional[str] = None,
    confidence: Optional[float] = None,
    priority: Optional[int] = None,
    reason: str = "",
    source_session_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update an existing memory by ID. Returns updated item or None if not found."""
    items = load_ltm(ltm_path)
    idx = _index_by_id(items)

    if memory_id not in idx:
        return None

    item = items[idx[memory_id]]
    if not isinstance(item, dict):
        return None

    before = dict(item)
    now = _now_iso()

    if content is not None:
        item["content"] = content
    if summary is not None:
        item["summary"] = summary
    if confidence is not None:
        item["confidence"] = confidence
    if priority is not None:
        item["priority"] = priority
    if reason:
        item["reason"] = reason

    # Always bump strength on update (reinforcement)
    item["strength"] = _safe_int(item.get("strength", 1), default=1) + 1
    item["last_updated"] = now

    save_ltm(items, ltm_path)

    log_entry = {
        "ts": now,
        "event_id": _new_event_id(),
        "source": {"source_session_id": source_session_id, "source_stage": "mcp_tool"},
        "action": "update",
        "target_id": memory_id,
        "before": before,
        "after": dict(item),
        "reason": reason,
    }
    _append_revision_log(log_entry, revision_log_path)

    return dict(item)


def delete_memory(
    *,
    ltm_path: Path,
    revision_log_path: Path,
    memory_id: str,
    source_session_id: Optional[str] = None,
) -> bool:
    """Delete a memory by ID. Returns True if found and deleted."""
    items = load_ltm(ltm_path)
    idx = _index_by_id(items)

    if memory_id not in idx:
        return False

    removed = items.pop(idx[memory_id])
    save_ltm(items, ltm_path)

    log_entry = {
        "ts": _now_iso(),
        "event_id": _new_event_id(),
        "source": {"source_session_id": source_session_id, "source_stage": "mcp_tool"},
        "action": "delete",
        "target_id": memory_id,
        "before": removed,
        "after": None,
        "reason": "deleted via MCP tool",
    }
    _append_revision_log(log_entry, revision_log_path)

    return True


def get_memory_by_id(ltm_path: Path, memory_id: str) -> Optional[Dict[str, Any]]:
    """Get a single memory by ID. Returns None if not found."""
    items = load_ltm(ltm_path)
    idx = _index_by_id(items)
    if memory_id not in idx:
        return None
    item = items[idx[memory_id]]
    return dict(item) if isinstance(item, dict) else None


# ---------------------------------------------------------------------------
# Gating (for batch reflection-style updates — preserved from V1)
# ---------------------------------------------------------------------------

def gate_memory_updates(
    payload: Dict[str, Any],
    *,
    min_confidence: float,
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Filter reflection candidates by confidence threshold.

    Returns (gated_payload, stats).
    """
    stats = {"kept": 0, "removed": 0}
    if not isinstance(payload, dict):
        return payload, stats

    candidates = payload.get("candidates", [])
    if not isinstance(candidates, list):
        return payload, stats

    kept: List[Dict[str, Any]] = []
    removed = 0
    for candidate in candidates:
        if not isinstance(candidate, dict):
            removed += 1
            continue
        conf = candidate.get("confidence", 0.0)
        try:
            conf_val = float(conf)
        except (TypeError, ValueError):
            removed += 1
            continue
        if conf_val >= min_confidence:
            kept.append(candidate)
        else:
            removed += 1

    payload["candidates"] = kept
    stats["kept"] = len(kept)
    stats["removed"] = removed
    return payload, stats


# ---------------------------------------------------------------------------
# Index helpers
# ---------------------------------------------------------------------------

def _index_by_id(items: List[Dict[str, Any]]) -> Dict[str, int]:
    index: Dict[str, int] = {}
    for i, item in enumerate(items):
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            index[item["id"]] = i
    return index
