from datetime import datetime
from .memory import session as session_module

def get_session(new_session: bool) -> session_module.Session:
	if new_session:
		session = session_module.create_new_session()
		return session

	session = session_module.load_latest_session()

	if session is None:
		session = session_module.create_new_session()
		
	return session

def get_output() -> str:
	return datetime.now().strftime("Assistant response at %Y-%m-%d %H:%M:%S")

def append_messages_and_save(session: session_module.Session, user_input: str, output: str) -> None:
	session_module.append_user_message(session, user_input)
	session_module.append_assistant_message(session, output)
	session_module.save_session(session)

def run_agent(*, new_session: bool, user_input: str) -> str:
	# loads or creates session -- created sessions are empty until user input is added
	current_session = get_session(new_session)
	
	# placeholder for LLM + memory logic
	output = get_output()

	# keeping this atomic so that messages are only saved if both user and assistant messages are added
	append_messages_and_save(current_session, user_input, output)

	return output