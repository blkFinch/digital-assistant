from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..core.contracts import SessionMessage

from ..config import SESSIONS_DIR, MAX_SCREEN_CONTEXTS

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass
class Session:
	session_id: str
	created_at: datetime
	last_updated: datetime
	messages: List[Dict[str, Any]] = field(default_factory=list)
	summary: str = ""
	file_path: Optional[Path] = None
	screen_contexts: List[Dict[str, Any]] = field(default_factory=list)
	active_screen_context_id: Optional[str] = None

	def to_dict(self) -> Dict[str, object]:
		return {
			"session_id": self.session_id,
			"created_at": timestamp_to_iso(self.created_at),
			"last_updated": timestamp_to_iso(self.last_updated),
			"messages": self.messages,
			"summary": self.summary,
			"screen_contexts": self.screen_contexts,
			"active_screen_context_id": self.active_screen_context_id,
		}


def timestamp_to_iso(value: datetime) -> str:
	return value.astimezone(timezone.utc).strftime(ISO_FORMAT)


def iso_to_datetime(value: str) -> datetime:
	return datetime.strptime(value, ISO_FORMAT).replace(tzinfo=timezone.utc)


def _ensure_sessions_dir() -> None:
	SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
	_ensure_sessions_dir()
	return SESSIONS_DIR / f"{session_id}.json"


def _now() -> datetime:
	return datetime.now(timezone.utc)


def create_new_session() -> Session:
	now = _now()
	session_id = f"session_{now.strftime('%Y%m%dT%H%M%SZ')}"
	messages = []
	session = Session(
		session_id=session_id,
		created_at=now,
		last_updated=now,
		messages=messages,
		summary="",
		screen_contexts=[],
		active_screen_context_id=None,
		file_path=_session_path(session_id),
	)
	return session

def append_message(session: Session, msg: SessionMessage) -> None:
    session.messages.append(msg.to_dict())
    session.last_updated = _now()


def append_user_message(session: Session, text: str, *, meta: Optional[Dict[str, Any]] = None) -> None:
    append_message(session, SessionMessage(role="user", content=text, meta=meta))

def append_screen_context(
    session: Session,
    *,
    text: str,
    source: str,
    created_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Append a new OCR screen context, cap history, and set it active.
    Returns the stored record.
    """
    created_at_dt = created_at or _now()
    record: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "created_at": timestamp_to_iso(created_at_dt),
        "source": source,
        "text": text,
    }

    session.screen_contexts.append(record)
    session.screen_contexts = _cap_screen_contexts(session.screen_contexts)

    # Set active to the newest record (unless you want different behavior)
    session.active_screen_context_id = record["id"]

    # If capping removed the previously-active context, ensure active still exists
    if session.active_screen_context_id not in {c.get("id") for c in session.screen_contexts}:
        session.active_screen_context_id = session.screen_contexts[-1]["id"]

    session.last_updated = _now()
    return record

def get_active_screen_context(session: Session) -> Optional[Dict[str, Any]]:
    """
    Return the active screen context if set and present; otherwise return the latest; otherwise None.
    """
    if session.screen_contexts:
        if session.active_screen_context_id:
            for c in session.screen_contexts:
                if c.get("id") == session.active_screen_context_id:
                    return c
        return session.screen_contexts[-1]
    return None


def set_active_screen_context(session: Session, context_id: str) -> bool:
    """
    Set active screen context by id. Returns True on success, False if id not found.
    """
    if any(c.get("id") == context_id for c in session.screen_contexts):
        session.active_screen_context_id = context_id
        session.last_updated = _now()
        return True
    return False


def clear_screen_contexts(session: Session) -> None:
    """
    Clear all stored screen contexts.
    """
    session.screen_contexts = []
    session.active_screen_context_id = None
    session.last_updated = _now()
    
def save_session(session: Session) -> Path:
	path = session.file_path or _session_path(session.session_id)
	try:
		path.write_text(json.dumps(session.to_dict(), indent=2))
	except Exception as e:
		raise RuntimeError(f"Failed to save session {session.session_id}: {e}") from e
	session.file_path = path
	return path


def load_session(path: Path) -> Session:
	raw = json.loads(path.read_text())
	session = Session(
		session_id=raw["session_id"],
		created_at=iso_to_datetime(raw["created_at"]),
		last_updated=iso_to_datetime(raw["last_updated"]),
		messages=raw.get("messages", []),
		summary=raw.get("summary", ""),
		screen_contexts=raw.get("screen_contexts", []),
		active_screen_context_id=raw.get("active_screen_context_id"),
		file_path=path,
	)
	return session

def _cap_screen_contexts(contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keep only the most recent MAX_SCREEN_CONTEXTS.
    If active id was pointing to a removed context, caller should handle.
    """
    if len(contexts) <= MAX_SCREEN_CONTEXTS:
        return contexts
    return contexts[-MAX_SCREEN_CONTEXTS:]

def _session_files() -> List[Path]:
	_ensure_sessions_dir()
	return sorted(SESSIONS_DIR.glob("session_*.json"), key=lambda p: p.stat().st_mtime)


def load_latest_session() -> Optional[Session]:
	files = _session_files()
	if not files:
		return None
	return load_session(files[-1])

def load_session_by_id(session_id: str) -> Optional[Session]:
    path = _session_path(session_id)
    if not path.exists():
        return None
    return load_session(path)