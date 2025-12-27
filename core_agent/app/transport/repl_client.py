from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
import threading
import time
import sys
from ..tts.factory import make_tts_subscriber

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    class Fore:
        CYAN = ""
        GREEN = ""
        YELLOW = ""
        RED = ""
        MAGENTA = ""
    class Style:
        RESET_ALL = ""

if TYPE_CHECKING:
    from ..core.engine import AgentEngine


def colorize(text: str, color: str = "") -> str:
    """Wrap text with colorama color code and reset. Gracefully handles missing colorama."""
    if not color:
        return text
    return f"{color}{text}{Style.RESET_ALL}"


HELP = """
Commands:
  /help                 show this help
  /q                    quit (/quit, /exit also work)
  /new                  start a new session (switches to it)
  /session <id>         switch to an existing session id
  /status               show current session + toggles
  /context on|off       toggle OCR capture for each message
  /verbose on|off       toggle debug printing in the REPL (not logger config)
  /say <text>           send one message (same as typing normally)
  /tts on|off|flush     toggles tts

Anything not starting with / is sent as a user message.
""".strip()


@dataclass
class ReplState:
    session_id: Optional[str] = None
    context_default: bool = False
    debug: bool = False
    tts_enabled: bool = False
    tts_sub: object | None = None


def _send(engine: AgentEngine, state: ReplState, text: str, *, new_session: bool = False) -> None:
    from ..core.contracts import RunOptions
    from .cli_adapter import run_options_to_event

    # Default behavior: if the REPL hasn't selected a session yet, start a fresh
    # one on the first user message instead of attaching to the latest session.
    if state.session_id is None and not new_session:
        new_session = True
    
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
        print(f"{colorize('session', Fore.CYAN)}: {state.session_id or '(latest)'} | {colorize('context_default', Fore.CYAN)}: {state.context_default} | {colorize('debug', Fore.CYAN)}: {state.debug}")
        return True

    if cmd == "/new":
        # Force a brand-new session regardless of any previously selected session.
        state.session_id = None
        # We still need a user_input to kick the pipeline; send a lightweight system-ish hello.
        # Alternative: implement a NEW_SESSION event type later.
        _send(engine, state, "start new session", new_session=True)
        return True

    if cmd == "/session":
        if not args:
            print(colorize("usage: /session <session_id>", Fore.RED))
            return True
        state.session_id = args[0]
        print(colorize(f"switched to session: {state.session_id}", Fore.GREEN))
        return True

    if cmd == "/context":
        if not args or args[0].lower() not in ("on", "off"):
            print(colorize("usage: /context on|off", Fore.RED))
            return True
        state.context_default = args[0].lower() == "on"
        print(colorize(f"context_default = {state.context_default}", Fore.YELLOW))
        return True

    if cmd == "/verbose":
        if not args or args[0].lower() not in ("on", "off"):
            print(colorize("usage: /debug on|off", Fore.RED))
            return True
        state.debug = args[0].lower() == "on"
        print(colorize(f"repl debug = {state.debug}", Fore.YELLOW))
        
        # Sync the global prompt dumper with the REPL's debug state
        from ..utils.prompt_dumper import configure_prompt_dumper
        configure_prompt_dumper(debug=state.debug)
        
        return True

    if cmd == "/say":
        if not args:
            print(colorize("usage: /say <text>", Fore.RED))
            return True
        _send(engine, state, " ".join(args))
        return True
    
    if cmd == "/tts":
        if not args or args[0].lower() not in ("on", "off", "flush"):
            print(colorize("usage: /tts on|off|toggle|flush", Fore.RED))
            return True

        if state.tts_sub is None:
            print(colorize("tts not configured", Fore.RED))
            return True

        action = args[0].lower()

        if action == "flush":
            if hasattr(state.tts_sub, "flush"):
                state.tts_sub.flush()
            print(colorize("tts flushed", Fore.GREEN))
            return True

        state.tts_enabled = (action == "on")
        if hasattr(state.tts_sub, "set_enabled"):
            state.tts_sub.set_enabled(state.tts_enabled)
        print(colorize(f"tts = {state.tts_enabled}", Fore.YELLOW))
        return True

        #toggle tts

    print(colorize(f"unknown command: {cmd}  (try /help)", Fore.RED))
    return True

def _boot_engine_with_spinner() -> AgentEngine:
    stop = threading.Event()

    def spin() -> None:
        frames = ["|", "/", "-", "\\"]
        i = 0
        while not stop.is_set():
            sys.stdout.write(f"\r{colorize(f'LOADING AI Agent… {frames[i % len(frames)]}', Fore.MAGENTA)}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)
        sys.stdout.write(f"\r{colorize('LOADING AI Agent… done.', Fore.GREEN)}\n")
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
    
    tts_sub = make_tts_subscriber()
    unsub_tts = engine.output_bus.subscribe(tts_sub)
    state.tts_sub = tts_sub

    unsubscribe = None
    if subscribe_to_output:
        def on_output(out) -> None:
            if out.session_id and out.session_id != "unknown":
                state.session_id = out.session_id

            print(f"\n{colorize('assistant', Fore.GREEN)}: {out.display_text}")

            if state.debug:
                print(f"{colorize('[debug]', Fore.YELLOW)} session_id={out.session_id} puppet={getattr(out, 'puppet', None)}")

        unsubscribe = engine.output_bus.subscribe(on_output)

    try:
        print("AI Vtuber REPL. Type /help for commands.")
        while True:
            try:
                prompt = state.session_id or "latest"
                line = input(f"{colorize(f'[{prompt}]', Fore.CYAN)} > ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{colorize('bye', Fore.YELLOW)}")
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
        if subscribe_to_output and 'unsub_tts' in locals():
            unsub_tts()


if __name__ == "__main__":
    main()
