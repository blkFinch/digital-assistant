"""Prompt construction for main chat and reflection.

This module centralizes prompt-building logic so the runner stays focused on
session orchestration.
"""

from __future__ import annotations

from typing import Optional

from ..config import (
	MIN_MEMORY_CONFIDENCE,
	PERSONALITY_PATH,
	PROMPT_MESSAGE_LIMIT,
	REFLECTION_MESSAGE_LIMIT,
	REFLECTION_PROMPT_PATH,
)

from ..memory import memory_system
from ..memory import session as session_module


def get_personality() -> str:
	if PERSONALITY_PATH.exists():
		return PERSONALITY_PATH.read_text(encoding="utf-8")
	return ""


def get_memory_block() -> str:
	items = memory_system.load_ltm()
	if not items:
		return "MEMORY: none."

	def sort_key(item: dict) -> tuple:
		# Prefer recently updated memories first.
		return (str(item.get("last_updated", "")), str(item.get("created_at", "")))

	sorted_items = sorted(
		[item for item in items if isinstance(item, dict)],
		key=sort_key,
		reverse=True,
	)

	lines: list[str] = ["MEMORY:"]
	for item in sorted_items:
		try:
			confidence = float(item.get("confidence", 0.0))
		except (TypeError, ValueError):
			confidence = 0.0
		if confidence < MIN_MEMORY_CONFIDENCE:
			continue

		subject = str(item.get("subject", "")).strip() or "unknown"
		mem_type = str(item.get("type", "")).strip() or "unknown"
		content = str(item.get("content", "")).strip()
		if not content:
			continue

		subject_label = "User" if subject.lower() == "user" else subject.capitalize()
		lines.append(f"- {subject_label} {mem_type}: {content}")

	# If everything was empty/invalid, fall back.
	return "\n".join(lines) if len(lines) > 1 else "MEMORY: none."

def get_reflection_memory_block() -> str:
	items = memory_system.load_sanitized_ltm()
	if not items:
		return "MEMORY: none."

	lines: list[str] = ["MEMORY:"]
	
	for item in items:
		mem_id = str(item.get("id", "")).strip()
		subject = str(item.get("subject", "")).strip() or "unknown"
		mem_type = str(item.get("type", "")).strip() or "unknown"
		content = str(item.get("content", "")).strip()
		if not content:
			continue

		try:
			confidence = float(item.get("confidence", 0.0))
		except (TypeError, ValueError):
			confidence = 0.0

		#TODO replace with fuzzy memories
		if confidence < MIN_MEMORY_CONFIDENCE:
			continue

		id_part = f"[{mem_id}] " if mem_id else ""
		lines.append(
			f"- {id_part}({subject}.{mem_type}, conf={confidence:.1f}) {content}"
		)

	return "\n".join(lines) if len(lines) > 1 else "MEMORY: none."

def construct_system_message_content() -> str:
	personality = get_personality()
	memory_block = get_memory_block()
	return personality + "\n\n" + memory_block


def _construct_screen_context_system_message(session) -> Optional[dict[str, str]]:
	try:
		active_ctx = session_module.get_active_screen_context(session)
	except Exception:
		return None

	if not active_ctx:
		return None

	ctx_text = str(active_ctx.get("text", "")).strip()
	if not ctx_text:
		return None

	source = str(active_ctx.get("source", "")).strip()
	created_at = str(active_ctx.get("created_at", "")).strip()
	meta_parts = [p for p in [source, created_at] if p]
	meta = f" ({' | '.join(meta_parts)})" if meta_parts else ""
	return {
		"role": "system",
		"content": f"SCREEN CONTEXT (OCR){meta}:\n\n{ctx_text}",
	}


def construct_prompt(session, user_input: str) -> list:
	"""Build the main chat prompt for the assistant."""
	system_message = {"role": "system", "content": construct_system_message_content()}
	screen_context_message = _construct_screen_context_system_message(session)
	limit = max(PROMPT_MESSAGE_LIMIT, 0)
	recent_messages = session.messages[-limit:] if limit > 0 else []
	base = [system_message]
	if screen_context_message:
		base.append(screen_context_message)
	return base + recent_messages + [{"role": "user", "content": user_input}]


def construct_reflection_prompt(session) -> list:
	"""Build the reflection prompt used to propose long-term memory updates."""
	recent_messages = (
		session.messages[-REFLECTION_MESSAGE_LIMIT:]
		if len(session.messages) >= REFLECTION_MESSAGE_LIMIT
		else session.messages
	)

	messages_text = "\n".join(
		[f"{msg['role'].upper()}: {msg['content']}" for msg in recent_messages]
	)
	context_blob = (
		get_reflection_memory_block() + "\n\n" + "RECENT MESSAGES:\n\n" + messages_text
	)

	if not REFLECTION_PROMPT_PATH.exists():
		raise FileNotFoundError(f"Reflection prompt file not found: {REFLECTION_PROMPT_PATH}")

	reflection_prompt_text = REFLECTION_PROMPT_PATH.read_text(encoding="utf-8")
	return [
		{"role": "system", "content": reflection_prompt_text},
		{"role": "user", "content": context_blob},
	]