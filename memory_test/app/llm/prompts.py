"""Prompt construction for main chat and reflection.

This module centralizes prompt-building logic so the runner stays focused on
session orchestration.
"""

from __future__ import annotations

from typing import Optional

from ..config import (
	PERSONALITY_PATH,
	PROMPT_MESSAGE_LIMIT,
	REFLECTION_MESSAGE_LIMIT,
	REFLECTION_PROMPT_PATH,
)


def get_personality() -> str:
	if PERSONALITY_PATH.exists():
		return PERSONALITY_PATH.read_text(encoding="utf-8")
	return ""


def get_memory_block() -> str:
	# Placeholder until the memory system is wired in.
	return "MEMORY: none."


def construct_system_message_content() -> str:
	personality = get_personality()
	memory_block = get_memory_block()
	return personality + "\n\n" + memory_block


def construct_prompt(session, user_input: str) -> list:
	"""Build the main chat prompt for the assistant."""
	system_message = {"role": "system", "content": construct_system_message_content()}
	limit = max(PROMPT_MESSAGE_LIMIT, 0)
	recent_messages = session.messages[-limit:] if limit > 0 else []
	return [system_message] + recent_messages + [{"role": "user", "content": user_input}]


def construct_reflection_prompt(session) -> Optional[list]:
	"""Build the reflection prompt used to propose long-term memory updates."""
	recent_messages = (
		session.messages[-REFLECTION_MESSAGE_LIMIT:]
		if len(session.messages) >= REFLECTION_MESSAGE_LIMIT
		else session.messages
	)

	messages_text = "\n".join(
		[f"{msg['role'].upper()}: {msg['content']}" for msg in recent_messages]
	)
	context_blob = get_memory_block() + "\n\n" + "RECENT MESSAGES:\n\n" + messages_text

	if not REFLECTION_PROMPT_PATH.exists():
		return None

	reflection_prompt_text = REFLECTION_PROMPT_PATH.read_text(encoding="utf-8")
	return [
		{"role": "system", "content": reflection_prompt_text},
		{"role": "user", "content": context_blob},
	]