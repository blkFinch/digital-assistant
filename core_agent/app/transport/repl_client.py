from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
import threading
import time
import sys
if TYPE_CHECKING:
    from ..core.engine import AgentEngine


HELP = """
Commands:
  /help                 show this help
  /q                    quit (/quit, /exit also work)
  /new                  start a new session (switches to it)
  /session <id>         switch to an existing session id
  /status               show current session + toggles
  /context on|off       toggle OCR capture for each message
  /verbose on|off         toggle debug printing in the REPL (not logger config)
  /say <text>           send one message (same as typing normally)

Anything not starting with / is sent as a user message.
""".strip()


@dataclass
class ReplState:
    session_id: Optional[str] = None
    context_default: bool = False
    debug: bool = False


def _send(engine: AgentEngine, state: ReplState, text: str, *, new_session: bool = False) -> None:
    from ..core.contracts import RunOptions
    from .cli_adapter import run_options_to_event
    
    opts = RunOptions(
        new_session=new_session,
        session_id=state.session_id,
        user_input=text,
        context=state.context_default,
    )

    event = run_options_to_event(opts)
    engine.handle_event(event)

def _handle_command(engine: AgentEngine, state: ReplState, line: str) -> bool:
    parts = shlex.split(line)
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in ("/help", "/h", "/?"):
        print(HELP)
        return True

    if cmd in ("/exit", "/quit", "/q"):
        return False

    if cmd == "/status":
        print(f"session: {state.session_id or '(latest)'} | context_default: {state.context_default} | debug: {state.debug}")
        return True

    if cmd == "/new":
        # We still need a user_input to kick the pipeline; send a lightweight system-ish hello.
        # Alternative: implement a NEW_SESSION event type later.
        _send(engine, state, "start new session", new_session=True)
        return True

    if cmd == "/session":
        if not args:
            print("usage: /session <session_id>")
            return True
        state.session_id = args[0]
        print(f"switched to session: {state.session_id}")
        return True

    if cmd == "/context":
        if not args or args[0].lower() not in ("on", "off"):
            print("usage: /context on|off")
            return True
        state.context_default = args[0].lower() == "on"
        print(f"context_default = {state.context_default}")
        return True

    if cmd == "/verbose":
        if not args or args[0].lower() not in ("on", "off"):
            print("usage: /debug on|off")
            return True
        state.debug = args[0].lower() == "on"
        print(f"repl debug = {state.debug}")
        return True

    if cmd == "/say":
        if not args:
            print("usage: /say <text>")
            return True
        _send(engine, state, " ".join(args))
        return True

    print(f"unknown command: {cmd}  (try /help)")
    return True

def _boot_engine_with_spinner() -> AgentEngine:
    stop = threading.Event()

    def spin() -> None:
        frames = ["|", "/", "-", "\\"]
        i = 0
        while not stop.is_set():
            sys.stdout.write(f"\rLOADING AI Agent… {frames[i % len(frames)]}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)
        sys.stdout.write("\rLOADING AI Agent… done.\n")
        sys.stdout.flush()

    t = threading.Thread(target=spin, daemon=True)
    t.start()
    try:
        from ..core.engine import AgentEngine #deferred import
        engine = AgentEngine()
    finally:
        stop.set()
        t.join(timeout=1.0)
    return engine

# TODO enhance this with colors and styling and perhaps a little animation when awaiting a response
def main(engine: AgentEngine | None = None, *, subscribe_to_output: bool = True, on_quit: callable | None = None) -> None:
    if engine is None:
        engine = _boot_engine_with_spinner()

    state = ReplState()

    unsubscribe = None
    if subscribe_to_output:
        def on_output(out) -> None:
            if out.session_id and out.session_id != "unknown":
                state.session_id = out.session_id

            print(f"\nassistant: {out.display_text}")

            if state.debug:
                print(f"[debug] session_id={out.session_id} puppet={getattr(out, 'puppet', None)}")

        unsubscribe = engine.output_bus.subscribe(on_output)

    try:
        print("AI Vtuber REPL. Type /help for commands.")
        while True:
            try:
                prompt = state.session_id or "latest"
                line = input(f"[{prompt}] > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nbye")
                if on_quit:
                    on_quit()
                return

            if not line:
                continue

            if line.startswith("/"):
                if not _handle_command(engine, state, line):
                    if on_quit:
                        on_quit()
                    return
                continue

            _send(engine, state, line)

    finally:
        if unsubscribe:
            unsubscribe()


if __name__ == "__main__":
    main()
