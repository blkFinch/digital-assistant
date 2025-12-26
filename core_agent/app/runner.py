import json
from .core.contracts import RunOptions, InitialResponseJson
from typing import Callable, Optional, TypeVar
from .config import MIN_MEMORY_CONFIDENCE
from .utils.logger import get_logger
from .utils.prompt_dumper import get_prompt_dumper
from .memory import memory_system
from .memory import session as session_module
from .llm import llm_router
from .llm import prompts as prompt_module
from .ocr.ocr_tool import capture_and_ocr, EasyOcrEngine

logger = get_logger(__name__)
dumper = get_prompt_dumper()

T = TypeVar("T")
# TODO find a place for Runner to live - is it in core?
# ERROR HANDLING UTILITIES
class FatalStepError(Exception):
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


def _fatal_step(label: str, fn: Callable[[], T], *, fallback_prefix: str) -> T:
    try:
        return fn()
    except llm_router.OpenRouterError as exc:
        logger.error("%s failed request: %s", label, exc)
        raise FatalStepError(f"{fallback_prefix}: {exc}") from exc
    except Exception as exc:
        logger.error("%s failed: %s", label, exc)
        raise FatalStepError(f"{fallback_prefix}: {exc}") from exc



def _nonfatal_step(label: str, fn: Callable[[], None]) -> None:
	"""Run a step that should not fail the main response."""
	try:
		fn()
	except json.JSONDecodeError as exc:
		logger.warning("%s skipped: invalid JSON (%s)", label, exc)
	except llm_router.OpenRouterError as exc:
		logger.warning("%s skipped: %s", label, exc)
	except FileNotFoundError as exc:
		logger.warning("%s skipped: %s", label, exc)
	except Exception as exc:
		logger.warning("%s failed: %s", label, exc)

def fallback_response(reason: str) -> tuple[InitialResponseJson, str]:
	text = "Falling back to default response: %s", reason
	logger.warning(text)

	fallback = InitialResponseJson(
		display_text=text,
		spoken_text=text,
		puppet={"expression": "confused", "intensity": 0.6},
	)
	return fallback, "unknown"


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

def _append_messages_and_save(session: session_module.Session, user_input: str, agent_output: InitialResponseJson, context_added: bool = False) -> None:
	if context_added:
		user_input += f"\n[system note: fresh screen context was captured for this message]"
  
	session_module.append_user_message(session, user_input)
	session_module.append_message(session, agent_output.to_session_message())
	session_module.save_session(session)
	logger.info("Recorded turn for session %s", session.session_id)
	

# PROMPT CONSTRUCTION

def _build_prompt(current_session: session_module.Session, user_input: str) -> list[dict[str, str]]:
	prompt = prompt_module.construct_prompt(current_session, user_input)
	logger.info("Constructed prompt with %d messages", len(prompt))
	logger.debug("Prompt messages: %s", prompt)
	dumper.dump_prompt(prompt, session_id=current_session.session_id)
	return prompt

	
# REFLECTION HANDLING

def _handle_reflection(session: session_module.Session) -> None:
	reflection_prompt = prompt_module.construct_reflection_prompt(session)

	logger.debug("Constructed reflection prompt: %s", reflection_prompt)
	dumper.dump_reflection_prompt(reflection_prompt, session_id=session.session_id)

	# Call LLM for reflection
	reflection_output = llm_router.generate_reflection_response(reflection_prompt)
	logger.info("Received reflection response from OpenRouter")
	logger.debug("Reflection output: %s", reflection_output)
	
	payload = json.loads(reflection_output)
	
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
	memory_system.apply_memory_updates(gated_payload, source_session_id=session.session_id)
	return

## SCREEN CAPTURE

def _capture_and_store_screen_context(session: session_module.Session) -> None:
	"""
	Capture screen context using OCR tool.

	Raises:
		RuntimeError: if screen capture or OCR fails.
	"""

	logger.info("Capturing screen context")
	try:
		engine = EasyOcrEngine(languages=["en"], gpu=True)
	except Exception:
		logger.info("EasyOCR GPU init failed; retrying with gpu=False")
		engine = EasyOcrEngine(languages=["en"], gpu=False)
	ctx = capture_and_ocr(engine)
	
	if not ctx.text.strip():
		raise RuntimeError("OCR capture succeeded but produced no text")

	session_module.append_screen_context(session, text=ctx.text, source=ctx.source)
	session_module.save_session(session)
	logger.info("Stored screen context for session %s", session.session_id)

## RUNNER FUNCTION

def run_agent(opts: RunOptions) -> tuple[InitialResponseJson, str]:
	try:
		# Load/create session
		current_session = _fatal_step(
			"Session init",
			lambda: _get_session(opts.new_session, opts.session_id),
			fallback_prefix="Session error",
		)
	
		# Grab Screen Context
		if opts.context:
			_nonfatal_step(
				"Screen context capture",
				lambda: _capture_and_store_screen_context(current_session),
			)
	
	
		# Construct prompt
		prompt = _fatal_step(
			"Prompt construction",
			lambda: _build_prompt(current_session, opts.user_input),
			fallback_prefix="Prompt error",
		)

		# Call LLM for response
		output = _fatal_step(
			"LLM response",
			lambda: llm_router.generate_response(prompt),
			fallback_prefix="LLM error",
		)

	except FatalStepError as exc:
		# Single place where you decide what user sees
		return fallback_response(exc.user_message)

	# Non-fatal Save turn and reflection
	_nonfatal_step("Save turn", lambda: _append_messages_and_save(current_session, opts.user_input, output))
	_nonfatal_step("Reflection", lambda: _handle_reflection(current_session))

	return output, current_session.session_id