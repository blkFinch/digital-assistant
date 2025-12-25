from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..core.contracts import InitialResponseJson, PuppetDirective

import requests

from ..config import (
	DATA_DIR,
	OPENROUTER_API_KEY,
	OPENROUTER_APP_NAME,
	OPENROUTER_BASE_URL,
	OPENROUTER_DEFAULT_MODEL,
	OPENROUTER_REQUEST_TIMEOUT,
	OPENROUTER_SITE_URL,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OpenRouterError(RuntimeError):
	"""Raised when an OpenRouter request or response fails."""

def _parse_initial_response(text: str) -> InitialResponseJson:
	try:
		data = json.loads(text)
	except json.JSONDecodeError as exc:
		raise OpenRouterError("Initial response was not valid JSON") from exc

	if not isinstance(data, dict):
		raise OpenRouterError("Initial response JSON was not an object")

	for key in ("display_text", "spoken_text", "puppet"):
		if key not in data:
			raise OpenRouterError(f"Initial response JSON missing key: {key}")

	puppet = data.get("puppet")
	if not isinstance(puppet, dict):
		raise OpenRouterError('Initial response JSON field "puppet" must be an object')
	
	expression = str(puppet.get("expression", "idle"))
	intensity_val = puppet.get("intensity", 0.5)
	try:
		intensity = float(intensity_val)
	except (TypeError, ValueError):
		intensity = 0.5
	intensity = max(0.0, min(1.0, intensity))
	
	display_text = str(data.get("display_text", ""))
	spoken_text = str(data.get("spoken_text", ""))
	
	puppet_dir = PuppetDirective(
		expression=expression,
		intensity=intensity,
	)
 
	return InitialResponseJson(
		display_text=display_text,
		spoken_text=spoken_text,
		puppet=puppet_dir,
	)


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


def _build_payload(
	messages: List[Dict[str, str]],
	model: Optional[str],
	*,
	response_format: Optional[Dict[str, Any]] = None,
) -> Dict[str, object]:
	payload: Dict[str, object] = {
		"model": model or OPENROUTER_DEFAULT_MODEL,
		"messages": messages,
	}
	if response_format is not None:
		payload["response_format"] = response_format
	return payload


def _post_chat_completion(payload: Dict[str, object]) -> str:
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


def _load_json_file(path: Path) -> Dict[str, Any]:
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except FileNotFoundError as exc:
		raise OpenRouterError(f"Required JSON file not found: {path}") from exc
	except json.JSONDecodeError as exc:
		raise OpenRouterError(f"Invalid JSON in file: {path}") from exc


def generate_response(messages: List[Dict[str, str]], *, model: Optional[str] = None, path: Optional[Path] = None) -> InitialResponseJson:
	"""Send the chat history to OpenRouter and return the assistant reply."""
	path = path or (DATA_DIR / "initial_response_format.json")
	response_format = _load_json_file(path)
	payload = _build_payload(messages, model, response_format=response_format)
	raw_response = _post_chat_completion(payload)
	return _parse_initial_response(raw_response)


def generate_reflection_response(
	messages: List[Dict[str, str]],
	*,
	model: Optional[str] = None,
	response_format_path: Optional[Path] = None,
) -> str:
	"""Run the reflection query with a strict JSON schema response format.

	This is intended for the "2nd reflection" call where we want to enforce
	structured JSON output via the `response_format` request parameter.
	"""
	path = response_format_path or (DATA_DIR / "reflection_response_format.json")
	response_format = _load_json_file(path)
	payload = _build_payload(messages, model, response_format=response_format)
	return _post_chat_completion(payload)
