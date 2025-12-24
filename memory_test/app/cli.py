# Simple CLI entry point that parses the MVP flags and delegates to the runner.
import argparse
import sys

from . import runner
from .utils.logger import configure_logging
from .utils.prompt_dumper import configure_prompt_dumper


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(prog="vision-agent")
	parser.add_argument(
		"--new-session",
		action="store_true",
		help="start a fresh short-term session",
	)
	parser.add_argument(
		"-i",
		"--input",
		dest="input_text",
		help="prompt string for the assistant",
	)
	parser.add_argument(
		"--session",
		dest="session_id",
		help="use a specific session id instead of the latest one",
	)
	parser.add_argument(
		"--debug",
		action="store_true",
		help="enable verbose logging output",
	)
	parser.add_argument(
		"--context",
		dest="context",
		help="capture screen context with the OCR tool",
	)
	return parser


def main() -> None:
	parser = build_parser()
	args = parser.parse_args()
	configure_logging(debug=args.debug)
	configure_prompt_dumper(debug=args.debug)
	if not args.input_text:
		print("Please provide input using -i/--input.")
		sys.exit(1)

	response = runner.run_agent(
		new_session=args.new_session,
		session_id=args.session_id,
		user_input=args.input_text,
	)
	print(response)


if __name__ == "__main__":
	main()