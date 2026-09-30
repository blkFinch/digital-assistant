"""Thread-safe puppet state orchestration independent of a UI backend."""

from __future__ import annotations

from threading import RLock

from .assets import AssetCatalog
from .models import PuppetState, RendererStatus
from .renderer import Renderer, RendererUnavailableError


class PuppetController:
    def __init__(
        self,
        catalog: AssetCatalog,
        renderer: Renderer,
        initial_state: PuppetState,
    ) -> None:
        self._catalog = catalog
        self._renderer = renderer
        self._state = initial_state
        self._lock = RLock()
        self._closed = False
        self._validate_state(initial_state)

    def start(self) -> RendererStatus:
        with self._lock:
            self._closed = False
            status = self._renderer.start(self._state)
            return self._require_ready(status, "start")

    def set_expression(self, expression: str, intensity: float = 0.5) -> dict:
        with self._lock:
            if self._closed:
                raise RuntimeError("Puppet controller is closed")
            candidate = PuppetState(self._state.puppet, expression, intensity)
            self._validate_state(candidate)
            try:
                status = self._renderer.apply(candidate)
                if status.status == "stopped":
                    raise RendererUnavailableError("Renderer is stopped")
                self._require_ready(status, "apply state")
            except RendererUnavailableError:
                self._renderer.close()
                self._require_ready(self._renderer.start(self._state), "restart")
                status = self._renderer.apply(candidate)
                self._require_ready(status, "apply state after restart")
            self._state = candidate
            return self._state_with_renderer(status)

    def get_current_state(self) -> dict:
        with self._lock:
            return self._state_with_renderer(self._renderer.get_status())

    def list_expressions(self) -> dict:
        with self._lock:
            return {
                "puppet": self._state.puppet,
                "default_expression": "idle",
                "expressions": list(
                    self._catalog.list_expressions(self._state.puppet)
                ),
            }

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._renderer.close()

    def _validate_state(self, state: PuppetState) -> None:
        if state.puppet not in self._catalog.list_puppets():
            raise ValueError(f"Unknown puppet '{state.puppet}'")
        if state.expression not in self._catalog.list_expressions(state.puppet):
            raise ValueError(
                f"Unknown expression '{state.expression}' for puppet '{state.puppet}'"
            )

    @staticmethod
    def _require_ready(status: RendererStatus, action: str) -> RendererStatus:
        if status.status != "ready":
            detail = f": {status.error}" if status.error else ""
            raise RuntimeError(f"Renderer could not {action} ({status.status}){detail}")
        return status

    def _state_with_renderer(self, status: RendererStatus) -> dict:
        result = self._state.to_dict()
        result["renderer"] = status.to_dict()
        return result