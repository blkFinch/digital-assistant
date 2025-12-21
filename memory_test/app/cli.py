# Simple CLI entry point that parses the MVP flags and delegates to the runner.
import argparse
import sys

from . import runner


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(prog="memory-agent")
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
	return parser


def main() -> None:
	parser = build_parser()
	args = parser.parse_args()
	if not args.input_text:
		print("Please provide input using -i/--input.")
		sys.exit(1)

	response = runner.run_agent(
		new_session=args.new_session,
		user_input=args.input_text,
	)
	print(response)


if __name__ == "__main__":
	main()