from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
import time
import sys

import tkinter as tk

#deffered for loading
if TYPE_CHECKING:
    from .core.engine import AgentEngine

from .core.contracts import AgentOutput
from .puppet.png_viewer import PngViewer, PuppetPaths, default_puppet_dir
from .transport.repl_client import main as repl_main


@dataclass
class ViewerUpdate:
    emotion: Optional[str] = None


def _emotion_from_output(out: AgentOutput) -> Optional[str]:
    """
    Extract an emotion string from AgentOutput.
    Adjust this to match your PuppetDirective shape.
    """
    puppet = getattr(out, "puppet", None)
    if puppet is None:
        return None

    # dict-like support
    if isinstance(puppet, dict):
        return (puppet.get("expression"))

    # pydantic / object support
    for attr in ("expression","emotion", "state", "mood"):
        if hasattr(puppet, attr):
            val = getattr(puppet, attr)
            if val:
                return str(val)

    return None

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
        from .core.engine import AgentEngine #deferred import
        engine = AgentEngine()
    finally:
        stop.set()
        t.join(timeout=1.0)
    return engine

def run() -> None:
    # Shared engine for the whole cockpit
    engine = _boot_engine_with_spinner()
    puppet = "chibi"
    # Viewer UI must live on the main thread
    root = tk.Tk()
    puppets = PuppetPaths(base_dir=default_puppet_dir(puppet), default_emotion="idle")
    viewer = PngViewer(root=root, puppets=puppets)

    # Thread-safe channel from bus -> Tk loop
    q: queue.Queue[ViewerUpdate] = queue.Queue()

    def on_output(out: AgentOutput) -> None:
        emotion = _emotion_from_output(out)
        q.put(ViewerUpdate(emotion=emotion))

    engine.output_bus.subscribe(on_output)

    def pump_queue() -> None:
        try:
            while True:
                msg = q.get_nowait()
                # If no emotion in output, revert to idle
                viewer.set_emotion(msg.emotion or "idle")
        except queue.Empty:
            pass

        root.after(50, pump_queue)  # ~20 FPS polling is plenty

    root.after(50, pump_queue)

    # Run REPL in a background thread
    def repl_thread() -> None:
        # REPL uses shared engine instance
        repl_main(engine, subscribe_to_output=True, on_quit=root.quit)

    t = threading.Thread(target=repl_thread, daemon=True)
    t.start()

    # Close behavior: if viewer window closes, exit whole program
    def on_close() -> None:
        root.quit()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Start viewer loop (main thread)
    root.mainloop()


if __name__ == "__main__":
    run()
