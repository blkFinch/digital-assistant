from __future__ import annotations

from typing import Dict, List, Optional

import requests

from ..config import (
	OPENROUTER_API_KEY,
	OPENROUTER_APP_NAME,
	OPENROUTER_BASE_URL,
	OPENROUTER_DEFAULT_MODEL,
	OPENROUTER_REQUEST_TIMEOUT,
	OPENROUTER_SITE_URL,
)
from ..logger import get_logger

logger = get_logger(__name__)


class OpenRouterError(RuntimeError):
	"""Raised when an OpenRouter request or response fails."""


def _require_api_key() -> str:
	if not OPENROUTER_API_KEY:
		raise OpenRouterError(
			"OPENROUTER_API_KEY is not configured. Set it in the environment or .env file."
		)
	return OPENROUTER_API_KEY


def _build_headers() -> Dict[str, str]:
	headers = {
		"Authorization": f"Bearer {_require_api_key()}",
		"Content-Type": "application/json",
	}
	if OPENROUTER_SITE_URL:
		headers["HTTP-Referer"] = OPENROUTER_SITE_URL
	if OPENROUTER_APP_NAME:
		headers["X-Title"] = OPENROUTER_APP_NAME
	return headers


def _build_payload(messages: List[Dict[str, str]], model: Optional[str]) -> Dict[str, object]:
	return {
		"model": model or OPENROUTER_DEFAULT_MODEL,
		"messages": messages,
	}


def generate_response(messages: List[Dict[str, str]], *, model: Optional[str] = None) -> str:
	"""Send the chat history to OpenRouter and return the assistant reply."""
	payload = _build_payload(messages, model)
	logger.debug("Sending payload to OpenRouter: %s", payload)
	try:
		response = requests.post(
			OPENROUTER_BASE_URL,
			headers=_build_headers(),
			json=payload,
			timeout=OPENROUTER_REQUEST_TIMEOUT,
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		logger.error("OpenRouter request failed: %s", exc)
		raise OpenRouterError("OpenRouter request failed") from exc

	data = response.json()
	try:
		return data["choices"][0]["message"]["content"].strip()
	except (KeyError, IndexError, TypeError) as exc:
		logger.error("Malformed OpenRouter response: %s", data)
		raise OpenRouterError("OpenRouter response missing message content") from exc
