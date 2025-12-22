import json
from datetime import datetime
from typing import Optional
from .config import MIN_MEMORY_CONFIDENCE
from .utils.logger import get_logger
from .utils.prompt_dumper import get_prompt_dumper
from .memory import memory_system
from .memory import session as session_module
from .llm import llm_router
from .llm import prompts as prompt_module

logger = get_logger(__name__)
dumper = get_prompt_dumper()

# SESSION MANAGEMENT
def _get_session(new_session: bool, session_id: Optional[str]) -> session_module.Session:
	if new_session: # create a new session
		logger.info("Starting new session")
		return session_module.create_new_session()

	session = None
	if session_id: # try to load by id
		session = session_module.load_session_by_id(session_id)
		if session:
			logger.info("Loaded session %s by id", session_id)
		else:
			logger.warning("Requested session %s not found; falling back", session_id)

	if session is None: # load latest session
		session = session_module.load_latest_session()
		if session:
			logger.info("Loaded latest session %s", session.session_id)

	if session is None: # no sessions found; create new
		logger.info("No sessions found; starting new session")
		session = session_module.create_new_session()

	return session

def fallback_response(reason: str) -> str:
	logger.warning("Falling back to default response: %s", reason)
	return datetime.now().strftime("Assistant response at %Y-%m-%d %H:%M:%S")

def _append_messages_and_save(session: session_module.Session, user_input: str, output: str) -> None:
	session_module.append_user_message(session, user_input)
	session_module.append_assistant_message(session, output)
	session_module.save_session(session)

# REFLECTION HANDLING

def _handle_reflection(session: session_module.Session) -> None:
	reflection_prompt = prompt_module.construct_reflection_prompt(session)

	if reflection_prompt is None:
		logger.error(
			"Failed to construct reflection prompt; skipping reflection (check reflection prompt file)"
		)
		return
	
	logger.debug("Constructed reflection prompt: %s", reflection_prompt)
	dumper.dump_reflection_prompt(reflection_prompt, session_id=session.session_id)

	# Call LLM for reflection
	try:		
		reflection_output = llm_router.generate_reflection_response(reflection_prompt)
		logger.info("Received reflection response from OpenRouter")
		logger.debug("Reflection output: %s", reflection_output)
	except llm_router.OpenRouterError as exc:
		logger.error("Reflection request failed: %s", exc)
		return
	
	try:
		payload = json.loads(reflection_output)
	except json.JSONDecodeError as exc:
		logger.error("Reflection output was not valid JSON: %s", exc)
		return
	
	# Gate memory updates and apply to long-term memory
	gated_payload, gate_stats = memory_system.gate_memory_updates(
		payload,
		min_confidence=MIN_MEMORY_CONFIDENCE,
	)
	if gate_stats.get("removed"):
		logger.info(
			"Gated reflection candidates: kept=%d removed=%d (min_confidence=%s)",
			gate_stats.get("kept", 0),
			gate_stats.get("removed", 0),
			MIN_MEMORY_CONFIDENCE,
		)
	logger.debug("Gated reflection output: %s", json.dumps(gated_payload, indent=2))
	_apply_memory_updates(gated_payload, session_id=session.session_id)
	return

def _apply_memory_updates(payload: dict, *, session_id: Optional[str] = None) -> None:
	"""Apply approved memory updates to long-term memory (persisted in ltm.json)."""
	if not isinstance(payload, dict):
		logger.warning("Cannot apply memory updates: expected JSON object")
		return

	items = memory_system.apply_memory_updates(payload, source_session_id=session_id)
	logger.info("Long-term memory now has %d items", len(items))

## RUNNER FUNCTION
def run_agent(*, new_session: bool, session_id: Optional[str], user_input: str) -> str:

	# LOAD OR CREATE SESSION
	try:
		# loads or creates session -- created sessions are empty until user input is added
		current_session = _get_session(new_session, session_id)
	except Exception as exc:
		logger.error("Failed to get or create session: %s", exc)
		return fallback_response(f"Session error: {exc}")

	# CONSTRUCT PROMPT
	try:
		prompt = prompt_module.construct_prompt(current_session, user_input)
		logger.info("Constructed prompt with %d messages", len(prompt))
		logger.debug("Prompt messages: %s", prompt)
		dumper.dump_prompt(prompt, session_id=current_session.session_id)
	except Exception as exc:
		logger.error("Failed to construct prompt: %s", exc)
		return fallback_response(f"Prompt error: {exc}")
	
	# CALL LLM FOR RESPONSE
	try:
		output = llm_router.generate_response(prompt)
		logger.info("Received response from OpenRouter")
	except llm_router.OpenRouterError as exc:
		logger.error("Chat completion request failed: %s", exc)
		return fallback_response(f"LLM error: {exc}")

	# APPEND MESSAGES AND SAVE SESSION
	try:
		_append_messages_and_save(current_session, user_input, output)
		# keeping this atomic so that messages are only saved if both user and assistant messages are added
		logger.info("Recorded turn for session %s", current_session.session_id)
	except Exception as exc:
		logger.warning("Failed to append messages and save session %s: %s", current_session.session_id, exc)
		return output  # still return the output even if saving failed
	
	# HANDLE REFLECTION
	try:
		_handle_reflection(current_session)
	except Exception as exc:
		logger.warning("Failed to handle reflection for session %s: %s", current_session.session_id, exc)
	# continuing without reflection but no memory updates applied

	return output