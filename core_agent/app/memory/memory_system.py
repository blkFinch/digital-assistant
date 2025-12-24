from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..config import REVISION_LOG_PATH, SESSIONS_DIR


LTM_PATH = SESSIONS_DIR / "ltm.json"

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


def gate_memory_updates(
	payload: Dict[str, Any],
	*,
	min_confidence: float,
) -> Tuple[Dict[str, Any], Dict[str, int]]:
	"""Filter reflection candidates before applying to long-term memory.

	This is intentionally pure (no logging) so callers can decide how to report.

	Returns:
	- gated_payload: the updated payload with candidates filtered
	- stats: {"kept": int, "removed": int}
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
		confidence = candidate.get("confidence", 0.0)
		try:
			confidence_value = float(confidence)
		except (TypeError, ValueError):
			removed += 1
			continue
		if confidence_value >= min_confidence:
			kept.append(candidate)
		else:
			removed += 1

	payload["candidates"] = kept
	stats["kept"] = len(kept)
	stats["removed"] = removed
	return payload, stats


def _now_iso() -> str:
	return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_memory_id() -> str:
	# Collision-resistant enough for local use; lexicographically sortable.
	return f"mem_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ%f')}"


def _new_event_id() -> str:
	return f"evt_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ%f')}"


def _append_revision_log(entry: Dict[str, Any]) -> None:
	REVISION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
	with REVISION_LOG_PATH.open("a", encoding="utf-8", newline="\n") as f:
		f.write(json.dumps(entry, ensure_ascii=False))
		f.write("\n")





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

def load_sanitized_ltm(path: Optional[Path] = None) -> List[Dict[str, Any]]:
	items = load_ltm(path)
	
	def sort_key(item: dict) -> tuple:
		return (str(item.get("last_updated", "")), str(item.get("created_at", "")))

	sorted_items = sorted(
		[item for item in items if isinstance(item, dict)],
		key=sort_key,
		reverse=True,
	)
	
    ## TODO remove deactivated items here
	return sorted_items

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


def _safe_float(value: Any, *, default: float) -> float:
	try:
		return float(value)
	except (TypeError, ValueError):
		return default


def _find_exact_match_index(
	items: List[Dict[str, Any]],
	*,
	cand_type: str,
	subject: str,
	content: str,
) -> Optional[int]:
	for i, existing in enumerate(items):
		if not isinstance(existing, dict):
			continue
		if (
			existing.get("type") == cand_type
			and existing.get("subject") == subject
			and existing.get("content") == content
		):
			return i
	return None


def _append_memory_item(
	items: List[Dict[str, Any]],
	*,
	cand_type: str,
	subject: str,
	content: str,
	confidence: float,
	reason: str,
) -> str:
	created_id = _new_memory_id()
	mem = MemoryItem(
		id=created_id,
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
	return created_id


def _log_create(
	*,
	log_entries: List[Dict[str, Any]],
	source_session_id: Optional[str],
	created_id: str,
	cand_type: str,
	subject: str,
	content: str,
	confidence: float,
	reason: str,
) -> None:
	log_entries.append(
		{
			"ts": _now_iso(),
			"event_id": _new_event_id(),
			"source": {
				"source_session_id": source_session_id,
				"source_stage": "reflection_apply",
			},
			"action": "create",
			"target_id": created_id,
			"before": None,
			"after": {
				"type": cand_type,
				"subject": subject,
				"content": content,
				"confidence": confidence,
				"strength": 1,
			},
			"reason": reason,
			"candidate_confidence": confidence,
		}
	)


def _log_reinforce(
	*,
	log_entries: List[Dict[str, Any]],
	source_session_id: Optional[str],
	matched: bool,
	target_id: str,
	cand_type: str,
	subject: str,
	content: str,
	confidence: float,
	reason: str,
	before: Optional[Dict[str, Any]],
	after: Optional[Dict[str, Any]],
) -> None:
	log_entries.append(
		{
			"ts": _now_iso(),
			"event_id": _new_event_id(),
			"source": {
				"source_session_id": source_session_id,
				"source_stage": "reflection_apply",
			},
			"action": "reinforce",
			"match": {
				"strategy": "exact_type_subject_content",
				"matched": matched,
			},
			"target_id": target_id,
			"before": before,
			"after": after,
			"reason": reason,
			"candidate_confidence": confidence,
		}
	)


def _log_revision_confidence_change(
	*,
	log_entries: List[Dict[str, Any]],
	source_session_id: Optional[str],
	action: str,
	target_id: str,
	before_confidence: Any,
	new_confidence: float,
	last_updated: str,
	reason: str,
) -> None:
	log_entries.append(
		{
			"ts": _now_iso(),
			"event_id": _new_event_id(),
			"source": {
				"source_session_id": source_session_id,
				"source_stage": "reflection_apply",
			},
			"action": action,
			"target_id": target_id,
			"before": {"confidence": before_confidence},
			"after": {
				"confidence": new_confidence,
				"last_updated": last_updated,
			},
			"reason": reason,
			"new_confidence": new_confidence,
		}
	)


def _log_revision_revise(
	*,
	log_entries: List[Dict[str, Any]],
	source_session_id: Optional[str],
	target_id: str,
	before_confidence: Any,
	before_content: Any,
	new_confidence: float,
	after_content: Any,
	last_updated: str,
	reason: str,
) -> None:
	log_entries.append(
		{
			"ts": _now_iso(),
			"event_id": _new_event_id(),
			"source": {
				"source_session_id": source_session_id,
				"source_stage": "reflection_apply",
			},
			"action": "revise",
			"target_id": target_id,
			"before": {"confidence": before_confidence, "content": before_content},
			"after": {
				"confidence": new_confidence,
				"content": after_content,
				"last_updated": last_updated,
			},
			"reason": reason,
			"new_confidence": new_confidence,
		}
	)


def _apply_create_candidate(
	*,
	items: List[Dict[str, Any]],
	log_entries: List[Dict[str, Any]],
	source_session_id: Optional[str],
	cand_type: str,
	subject: str,
	content: str,
	confidence: float,
	reason: str,
) -> bool:
	created_id = _append_memory_item(
		items,
		cand_type=cand_type,
		subject=subject,
		content=content,
		confidence=confidence,
		reason=reason,
	)
	_log_create(
		log_entries=log_entries,
		source_session_id=source_session_id,
		created_id=created_id,
		cand_type=cand_type,
		subject=subject,
		content=content,
		confidence=confidence,
		reason=reason,
	)
	return True


def _apply_reinforce_candidate(
	*,
	items: List[Dict[str, Any]],
	log_entries: List[Dict[str, Any]],
	source_session_id: Optional[str],
	cand_type: str,
	subject: str,
	content: str,
	confidence: float,
	reason: str,
) -> bool:
	matched_i = _find_exact_match_index(items, cand_type=cand_type, subject=subject, content=content)
	if matched_i is None:
		created_id = _append_memory_item(
			items,
			cand_type=cand_type,
			subject=subject,
			content=content,
			confidence=confidence,
			reason=reason,
		)
		_log_reinforce(
			log_entries=log_entries,
			source_session_id=source_session_id,
			matched=False,
			target_id=created_id,
			cand_type=cand_type,
			subject=subject,
			content=content,
			confidence=confidence,
			reason=reason,
			before=None,
			after={
				"type": cand_type,
				"subject": subject,
				"content": content,
				"confidence": confidence,
				"strength": 1,
			},
		)
		return True

	existing = items[matched_i]
	if not isinstance(existing, dict):
		return False

	existing_id = str(existing.get("id", ""))
	before_confidence = existing.get("confidence")
	before_strength = existing.get("strength")

	existing_strength = _safe_float(existing.get("strength", 1), default=1.0)
	# Preserve existing behavior: strength stored as int.
	existing["strength"] = int(existing_strength) + 1
	existing["last_updated"] = _now_iso()

	# Keep the higher confidence if it increases.
	existing_conf = _safe_float(existing.get("confidence", 0.0), default=0.0)
	if confidence > existing_conf:
		existing["confidence"] = confidence

	_log_reinforce(
		log_entries=log_entries,
		source_session_id=source_session_id,
		matched=True,
		target_id=existing_id,
		cand_type=cand_type,
		subject=subject,
		content=content,
		confidence=confidence,
		reason=reason,
		before={
			"confidence": before_confidence,
			"strength": before_strength,
		},
		after={
			"confidence": existing.get("confidence"),
			"strength": existing.get("strength"),
			"last_updated": existing.get("last_updated"),
		},
	)
	return True


def _apply_candidates(
	*,
	items: List[Dict[str, Any]],
	candidates: List[Any],
	log_entries: List[Dict[str, Any]],
	source_session_id: Optional[str],
) -> bool:
	changed = False
	for cand in candidates:
		if not isinstance(cand, dict):
			continue
		action = cand.get("action")
		cand_type = str(cand.get("type", ""))
		subject = str(cand.get("subject", ""))
		content = str(cand.get("content", ""))
		reason = str(cand.get("reason", ""))
		confidence = _safe_float(cand.get("confidence", 0.0), default=0.0)

		if action == "create":
			changed |= _apply_create_candidate(
				items=items,
				log_entries=log_entries,
				source_session_id=source_session_id,
				cand_type=cand_type,
				subject=subject,
				content=content,
				confidence=confidence,
				reason=reason,
			)
		elif action == "reinforce":
			changed |= _apply_reinforce_candidate(
				items=items,
				log_entries=log_entries,
				source_session_id=source_session_id,
				cand_type=cand_type,
				subject=subject,
				content=content,
				confidence=confidence,
				reason=reason,
			)
	return changed


def _apply_revisions(
	*,
	items: List[Dict[str, Any]],
	idx: Dict[str, int],
	revisions: List[Any],
	log_entries: List[Dict[str, Any]],
	source_session_id: Optional[str],
) -> bool:
	changed = False
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
		new_conf_raw = rev.get("new_confidence", item.get("confidence", 0.0))
		try:
			new_conf = float(new_conf_raw)
		except (TypeError, ValueError):
			continue

		if action in {"decrease_confidence", "increase_confidence"}:
			before_confidence = item.get("confidence")
			item["confidence"] = new_conf
			item["last_updated"] = _now_iso()
			_log_revision_confidence_change(
				log_entries=log_entries,
				source_session_id=source_session_id,
				action=str(action),
				target_id=target_id,
				before_confidence=before_confidence,
				new_confidence=new_conf,
				last_updated=str(item.get("last_updated", "")),
				reason=str(rev.get("reason", "")),
			)
			changed = True
		elif action == "revise":
			before_confidence = item.get("confidence")
			before_content = item.get("content")
			if isinstance(rev.get("content"), str):
				item["content"] = rev["content"]
			item["confidence"] = new_conf
			item["last_updated"] = _now_iso()
			_log_revision_revise(
				log_entries=log_entries,
				source_session_id=source_session_id,
				target_id=target_id,
				before_confidence=before_confidence,
				before_content=before_content,
				new_confidence=new_conf,
				after_content=item.get("content"),
				last_updated=str(item.get("last_updated", "")),
				reason=str(rev.get("reason", "")),
			)
			changed = True

	return changed


def apply_memory_updates(
	updates: Dict[str, Any],
	*,
	path: Optional[Path] = None,
	source_session_id: Optional[str] = None,
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
	log_entries: List[Dict[str, Any]] = []

	candidates = updates.get("candidates", [])
	if isinstance(candidates, list):
		changed |= _apply_candidates(
			items=items,
			candidates=candidates,
			log_entries=log_entries,
			source_session_id=source_session_id,
		)

	revisions = updates.get("revisions", [])
	if isinstance(revisions, list):
		changed |= _apply_revisions(
			items=items,
			idx=idx,
			revisions=revisions,
			log_entries=log_entries,
			source_session_id=source_session_id,
		)

	if changed:
		save_ltm(items, path)
		for entry in log_entries:
			_append_revision_log(entry)
	return items