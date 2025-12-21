from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ..config import SESSIONS_DIR

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass
class Session:
	session_id: str
	created_at: datetime
	last_updated: datetime
	messages: List[Dict[str, str]] = field(default_factory=list)
	summary: str = ""
	file_path: Optional[Path] = None

	def to_dict(self) -> Dict[str, object]:
		return {
			"session_id": self.session_id,
			"created_at": timestamp_to_iso(self.created_at),
			"last_updated": timestamp_to_iso(self.last_updated),
			"messages": self.messages,
			"summary": self.summary,
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
		file_path=_session_path(session_id),
	)
	return session


def append_user_message(session: Session, text: str) -> None:
	session.messages.append({"role": "user", "content": text})
	session.last_updated = _now()
	
def append_assistant_message(session: Session, text: str) -> None:
    session.messages.append({"role": "assistant", "content": text})
    session.last_updated = _now()


def save_session(session: Session) -> Path:
	path = session.file_path or _session_path(session.session_id)
	path.write_text(json.dumps(session.to_dict(), indent=2))
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
		file_path=path,
	)
	return session


def _session_files() -> List[Path]:
	_ensure_sessions_dir()
	return sorted(SESSIONS_DIR.glob("session_*.json"), key=lambda p: p.stat().st_mtime)


def load_latest_session() -> Optional[Session]:
	files = _session_files()
	if not files:
		return None
	return load_session(files[-1])