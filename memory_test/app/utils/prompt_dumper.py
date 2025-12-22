from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import LOGS_DIR


@dataclass
class PromptDumper:
	enabled: bool = False

	def dump_prompt(self, messages: list, session_id: Optional[str] = None) -> None:
		if not self.enabled:
			return
		self._dump(
			LOGS_DIR / "latest_prompt.txt",
			label="latest_prompt",
			messages=messages,
			session_id=session_id,
		)

	def dump_reflection_prompt(self, messages: list, session_id: Optional[str] = None) -> None:
		if not self.enabled:
			return
		self._dump(
			LOGS_DIR / "latest_reflection_prompt.txt",
			label="latest_reflection_prompt",
			messages=messages,
			session_id=session_id,
		)

	def _dump(self, path: Path, *, label: str, messages: list, session_id: Optional[str]) -> None:
		try:
			LOGS_DIR.mkdir(parents=True, exist_ok=True)
			lines: list[str] = []
			lines.append(f"# label: {label}")
			lines.append(f"# ts: {datetime.utcnow().isoformat()}Z")
			if session_id:
				lines.append(f"# session_id: {session_id}")
			lines.append(f"# messages: {len(messages)}")
			lines.append("")

			for i, msg in enumerate(messages):
				role = msg.get("role", "") if isinstance(msg, dict) else ""
				content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
				lines.append(f"[{i}] role={role}")
				lines.append("-----")
				lines.append(content)
				lines.append("=====")

			path.write_text("\n".join(lines), encoding="utf-8")
		except Exception:
			# Intentionally swallow dump failures: prompt dumping must never break the main flow.
			return


_PROMPT_DUMPER = PromptDumper(enabled=False)


def configure_prompt_dumper(*, debug: bool = False) -> None:
	"""Enable/disable prompt dumping for this process (CLI run)."""
	_PROMPT_DUMPER.enabled = bool(debug)


def get_prompt_dumper() -> PromptDumper:
	return _PROMPT_DUMPER
