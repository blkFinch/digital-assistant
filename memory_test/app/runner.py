from datetime import datetime
from typing import Optional

from .logger import get_logger
from .memory import session as session_module

logger = get_logger(__name__)


def get_session(new_session: bool, session_id: Optional[str]) -> session_module.Session:
	if new_session:
		logger.info("Starting new session")
		return session_module.create_new_session()

	session = None
	if session_id:
		session = session_module.load_session_by_id(session_id)
		if session:
			logger.info("Loaded session %s by id", session_id)
		else:
			logger.warning("Requested session %s not found; falling back", session_id)

	if session is None:
		session = session_module.load_latest_session()
		if session:
			logger.info("Loaded latest session %s", session.session_id)

	if session is None:
		logger.info("No sessions found; starting new session")
		session = session_module.create_new_session()

	return session

def get_output() -> str:
	return datetime.now().strftime("Assistant response at %Y-%m-%d %H:%M:%S")

def append_messages_and_save(session: session_module.Session, user_input: str, output: str) -> None:
	session_module.append_user_message(session, user_input)
	session_module.append_assistant_message(session, output)
	session_module.save_session(session)


def run_agent(*, new_session: bool, session_id: Optional[str], user_input: str) -> str:
	# loads or creates session -- created sessions are empty until user input is added
	current_session = get_session(new_session, session_id)
	
	# placeholder for LLM + memory logic
	output = get_output()

	# keeping this atomic so that messages are only saved if both user and assistant messages are added
	append_messages_and_save(current_session, user_input, output)
	logger.info("Recorded turn for session %s", current_session.session_id)

	return output