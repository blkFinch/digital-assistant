from datetime import datetime
from typing import Optional
from .config import PERSONALITY_PATH, PROMPT_MESSAGE_LIMIT
from .logger import get_logger
from .memory import session as session_module
from .llm import llm_router

logger = get_logger(__name__)

# SESSION MANAGEMENT
def get_session(new_session: bool, session_id: Optional[str]) -> session_module.Session:
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

def append_messages_and_save(session: session_module.Session, user_input: str, output: str) -> None:
	session_module.append_user_message(session, user_input)
	session_module.append_assistant_message(session, output)
	session_module.save_session(session)

# PROMPT CONSTRUCTION
def get_personality() -> str:
	if PERSONALITY_PATH.exists():
		return PERSONALITY_PATH.read_text(encoding="utf-8")
	return ""

def get_memory_block() -> str:
	placeholder = "MEMORY: none."
	return placeholder

def construct_system_message_content() -> str:
	personality = get_personality()
	memory_block = get_memory_block()
	content = personality + "\n\n" + memory_block

	return content

def construct_prompt(session: session_module.Session, user_input: str) -> list:
	system_message = {"role": "system", "content": construct_system_message_content()}
	limit = max(PROMPT_MESSAGE_LIMIT, 0)
	recent_messages = session.messages[-limit:] if limit > 0 else []
	messages = [system_message] + recent_messages + [{"role": "user", "content": user_input}]
	return messages

def run_agent(*, new_session: bool, session_id: Optional[str], user_input: str) -> str:
	# loads or creates session -- created sessions are empty until user input is added
	current_session = get_session(new_session, session_id)

	prompt = construct_prompt(current_session, user_input)
	logger.info("Constructed prompt with %d messages", len(prompt))
	logger.debug("Prompt messages: %s", prompt)
	
	try:
		output = llm_router.generate_response(prompt)
		logger.info("Received response from OpenRouter")
		append_messages_and_save(current_session, user_input, output)
	except llm_router.OpenRouterError as exc:
		output = fallback_response(str(exc))

	# keeping this atomic so that messages are only saved if both user and assistant messages are added
	logger.info("Recorded turn for session %s", current_session.session_id)

	return output