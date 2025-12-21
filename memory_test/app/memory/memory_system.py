from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import SESSIONS_DIR


LTM_PATH = SESSIONS_DIR / "ltm.json"


def _now_iso() -> str:
	return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_memory_id() -> str:
	# Collision-resistant enough for local use; lexicographically sortable.
	return f"mem_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ%f')}"


@dataclass
class MemoryItem:
	id: str
	type: str
	subject: str
	content: str
	confidence: float
	reason: str
	created_at: str
	last_updated: str
	strength: int = 1

	def to_dict(self) -> Dict[str, Any]:
		return {
			"id": self.id,
			"type": self.type,
			"subject": self.subject,
			"content": self.content,
			"confidence": self.confidence,
			"reason": self.reason,
			"created_at": self.created_at,
			"last_updated": self.last_updated,
			"strength": self.strength,
		}


def load_ltm(path: Optional[Path] = None) -> List[Dict[str, Any]]:
	"""Load the long-term memory store.

	The file contains a JSON array of memory objects.
	"""
	store_path = path or LTM_PATH
	store_path.parent.mkdir(parents=True, exist_ok=True)
	if not store_path.exists() or store_path.stat().st_size == 0:
		return []
	try:
		data = json.loads(store_path.read_text(encoding="utf-8"))
	except json.JSONDecodeError:
		# If the file is corrupt, fail safe by starting fresh.
		return []
	return data if isinstance(data, list) else []


def save_ltm(items: List[Dict[str, Any]], path: Optional[Path] = None) -> Path:
	store_path = path or LTM_PATH
	store_path.parent.mkdir(parents=True, exist_ok=True)
	store_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
	return store_path


def _index_by_id(items: List[Dict[str, Any]]) -> Dict[str, int]:
	index: Dict[str, int] = {}
	for i, item in enumerate(items):
		if isinstance(item, dict) and isinstance(item.get("id"), str):
			index[item["id"]] = i
	return index


def apply_memory_updates(
	updates: Dict[str, Any],
	*,
	path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
	"""Apply reflection candidates + revisions into LTM and persist.

	Expected shape:
	{
	  "candidates": [...],
	  "revisions": [...]
	}
	"""
	items = load_ltm(path)
	idx = _index_by_id(items)
	changed = False

	candidates = updates.get("candidates", [])
	if isinstance(candidates, list):
		for cand in candidates:
			if not isinstance(cand, dict):
				continue
			action = cand.get("action")
			cand_type = str(cand.get("type", ""))
			subject = str(cand.get("subject", ""))
			content = str(cand.get("content", ""))
			reason = str(cand.get("reason", ""))
			try:
				confidence = float(cand.get("confidence", 0.0))
			except (TypeError, ValueError):
				confidence = 0.0

			if action == "create":
				mem = MemoryItem(
					id=_new_memory_id(),
					type=cand_type,
					subject=subject,
					content=content,
					confidence=confidence,
					reason=reason,
					created_at=_now_iso(),
					last_updated=_now_iso(),
					strength=1,
				)
				items.append(mem.to_dict())
				changed = True
			elif action == "reinforce":
				# Best-effort: reinforce the first matching item (same type/subject/content).
				matched_i: Optional[int] = None
				for i, existing in enumerate(items):
					if not isinstance(existing, dict):
						continue
					if (
						existing.get("type") == cand_type
						and existing.get("subject") == subject
						and existing.get("content") == content
					):
						matched_i = i
						break
				if matched_i is None:
					# If no match, create a new item (still gives it an ID for future revisions).
					mem = MemoryItem(
						id=_new_memory_id(),
						type=cand_type,
						subject=subject,
						content=content,
						confidence=confidence,
						reason=reason,
						created_at=_now_iso(),
						last_updated=_now_iso(),
						strength=1,
					)
					items.append(mem.to_dict())
					changed = True
				else:
					existing = items[matched_i]
					try:
						existing_strength = int(existing.get("strength", 1))
					except (TypeError, ValueError):
						existing_strength = 1
					existing["strength"] = existing_strength + 1
					existing["last_updated"] = _now_iso()
					# Keep the higher confidence if it increases.
					try:
						existing_conf = float(existing.get("confidence", 0.0))
					except (TypeError, ValueError):
						existing_conf = 0.0
					if confidence > existing_conf:
						existing["confidence"] = confidence
					changed = True

	revisions = updates.get("revisions", [])
	if isinstance(revisions, list):
		for rev in revisions:
			if not isinstance(rev, dict):
				continue
			target_id = rev.get("target_id")
			if not isinstance(target_id, str) or target_id not in idx:
				continue
			item = items[idx[target_id]]
			if not isinstance(item, dict):
				continue
			action = rev.get("action")
			try:
				new_conf = float(rev.get("new_confidence", item.get("confidence", 0.0)))
			except (TypeError, ValueError):
				continue
			if action in {"decrease_confidence", "increase_confidence"}:
				item["confidence"] = new_conf
				item["last_updated"] = _now_iso()
				changed = True
			elif action == "revise":
				# Optional: allow a content revision if provided.
				if isinstance(rev.get("content"), str):
					item["content"] = rev["content"]
				item["confidence"] = new_conf
				item["last_updated"] = _now_iso()
				changed = True

	if changed:
		save_ltm(items, path)
	return items