"""Spawned-process Tk renderer; importing this module never imports Tk."""

from __future__ import annotations

import logging
import multiprocessing
import queue
import sys
import time
import uuid
from importlib.resources import as_file
from threading import RLock
from typing import Any

from .models import PuppetState, RendererStatus
from .renderer import RendererUnavailableError

_LOG = logging.getLogger(__name__)


def _safe_error(exc: BaseException) -> str:
    detail = " ".join(str(exc).split())[:300]
    suffix = f" ({type(exc).__name__}: {detail})" if detail else f" ({type(exc).__name__})"
    return (
        "Tk renderer failed; Tk/Tcl 8.6+ with native PNG support and a graphical "
        f"display is required{suffix}"
    )


def run_tk_renderer(config: dict, command_queue: Any, event_queue: Any) -> None:
    """Spawn target that owns Tk and runs its mainloop on the child main thread."""
    try:
        import tkinter as tk

        from .assets import AssetCatalog

        catalog = AssetCatalog()
        state = PuppetState.from_dict(config["initial_state"])
        root = tk.Tk()
        root.title(config["window_title"])
        root.resizable(False, False)
        label = tk.Label(root)
        label.pack()
        current_photo: Any = None
        closed_sent = False

        def load_photo(next_state: PuppetState) -> Any:
            resource = catalog.resolve_png(next_state.puppet, next_state.expression)
            with as_file(resource) as png_path:
                return tk.PhotoImage(file=str(png_path))

        def send_closed() -> None:
            nonlocal closed_sent
            if not closed_sent:
                closed_sent = True
                event_queue.put({"type": "closed"})

        def close_window() -> None:
            send_closed()
            root.destroy()

        current_photo = load_photo(state)
        label.configure(image=current_photo)
        root.protocol("WM_DELETE_WINDOW", close_window)
        event_queue.put({"type": "ready"})

        def poll_commands() -> None:
            nonlocal current_photo
            try:
                while True:
                    command = command_queue.get_nowait()
                    command_type = command.get("type")
                    if command_type == "shutdown":
                        close_window()
                        return
                    if command_type != "set_state":
                        raise ValueError(f"Unknown renderer command '{command_type}'")
                    request_id = command.get("request_id")
                    try:
                        next_state = PuppetState.from_dict(command["state"])
                        next_photo = load_photo(next_state)
                        label.configure(image=next_photo)
                        current_photo = next_photo
                        event_queue.put(
                            {"type": "applied", "request_id": request_id}
                        )
                    except Exception as exc:
                        event_queue.put(
                            {
                                "type": "error",
                                "request_id": request_id,
                                "error": _safe_error(exc),
                            }
                        )
            except queue.Empty:
                root.after(25, poll_commands)

        root.after(25, poll_commands)
        root.mainloop()
    except Exception as exc:
        logging.basicConfig(stream=sys.stderr)
        _LOG.error("%s", _safe_error(exc))
        try:
            event_queue.put({"type": "error", "error": _safe_error(exc)})
        except Exception:
            pass


class TkProcessRenderer:
    """Parent-side manager for the spawn-isolated Tk child."""

    def __init__(
        self,
        window_title: str = "AI Vtuber Puppet",
        startup_timeout: float = 5.0,
        command_timeout: float = 2.0,
    ) -> None:
        self._window_title = window_title
        self._startup_timeout = startup_timeout
        self._command_timeout = command_timeout
        self._context = multiprocessing.get_context("spawn")
        self._process: Any = None
        self._command_queue: Any = None
        self._event_queue: Any = None
        self._status = RendererStatus("tk", "stopped")
        self._lock = RLock()

    def start(self, initial_state: PuppetState) -> RendererStatus:
        with self._lock:
            if self._process is not None and self._process.is_alive():
                if self._status.status == "ready":
                    return self._status
                self.close()
            self._dispose_process()
            self._command_queue = self._context.Queue()
            self._event_queue = self._context.Queue()
            config = {
                "window_title": self._window_title,
                "initial_state": initial_state.to_dict(),
            }
            self._process = self._context.Process(
                target=run_tk_renderer,
                args=(config, self._command_queue, self._event_queue),
                daemon=True,
                name="puppet-mcp-tk",
            )
            self._status = RendererStatus("tk", "starting")
            self._process.start()
            try:
                self._wait_for("ready", None, self._startup_timeout)
            except Exception:
                self.close()
                raise
            self._status = RendererStatus("tk", "ready")
            return self._status

    def apply(self, state: PuppetState) -> RendererStatus:
        with self._lock:
            if self._process is None or not self._process.is_alive():
                self._status = RendererStatus("tk", "stopped")
                raise RendererUnavailableError("Tk renderer process is not running")
            request_id = uuid.uuid4().hex
            self._command_queue.put(
                {
                    "type": "set_state",
                    "request_id": request_id,
                    "state": state.to_dict(),
                }
            )
            self._wait_for("applied", request_id, self._command_timeout)
            self._status = RendererStatus("tk", "ready")
            return self._status

    def get_status(self) -> RendererStatus:
        with self._lock:
            if (
                self._process is not None
                and not self._process.is_alive()
                and self._status.status in {"starting", "ready"}
            ):
                self._status = RendererStatus("tk", "stopped")
            return self._status

    def close(self) -> None:
        with self._lock:
            process = self._process
            if process is not None and process.is_alive():
                try:
                    self._command_queue.put({"type": "shutdown"})
                    process.join(self._command_timeout)
                except (OSError, ValueError):
                    pass
                if process.is_alive():
                    process.terminate()
                    process.join(self._command_timeout)
            self._status = RendererStatus("tk", "stopped")
            self._dispose_process()

    def _wait_for(
        self, event_type: str, request_id: str | None, timeout: float
    ) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                if self._process is None or not self._process.is_alive():
                    self._status = RendererStatus("tk", "stopped")
                    raise RendererUnavailableError("Tk renderer process exited")
                raise RuntimeError(f"Tk renderer timed out waiting for {event_type}")
            try:
                event = self._event_queue.get(timeout=remaining)
            except queue.Empty as exc:
                if self._process is None or not self._process.is_alive():
                    self._status = RendererStatus("tk", "stopped")
                    raise RendererUnavailableError("Tk renderer process exited") from exc
                raise RuntimeError(
                    f"Tk renderer timed out waiting for {event_type}"
                ) from exc
            kind = event.get("type")
            if kind == "closed":
                self._status = RendererStatus("tk", "stopped")
                raise RendererUnavailableError("Tk renderer window was closed")
            if kind == "error" and (
                event.get("request_id") in {None, request_id}
            ):
                message = event.get("error") or "Unknown Tk renderer error"
                self._status = RendererStatus("tk", "error", str(message))
                raise RuntimeError(str(message))
            if kind == event_type and event.get("request_id") == request_id:
                return event

    def _dispose_process(self) -> None:
        for ipc_queue in (self._command_queue, self._event_queue):
            if ipc_queue is not None:
                try:
                    ipc_queue.close()
                    ipc_queue.cancel_join_thread()
                except (OSError, ValueError):
                    pass
        self._process = None
        self._command_queue = None
        self._event_queue = None