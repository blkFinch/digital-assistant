from datetime import datetime
from .memory import session as session_module

def session(new_session: bool) -> session_module.Session:
	if new_session:
		session = session_module.create_new_session()
		return session

	session = session_module.load_latest_session()

	if session is None:
		session = session_module.create_new_session()
		
	return session

def get_output() -> str:
	return datetime.now().strftime("Assistant response at %Y-%m-%d %H:%M:%S")

def run_agent(*, new_session: bool, user_input: str) -> str:
	# loads or creates session -- created sessions are empty until user input is added
	current_session = session(new_session)
	
	output = get_output()

	session_module.append_user_message(current_session, user_input)
	session_module.append_assistant_message(current_session, output)
	session_module.save_session(current_session)

	return output