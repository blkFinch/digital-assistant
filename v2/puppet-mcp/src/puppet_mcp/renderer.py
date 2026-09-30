"""Renderer boundary and IPC event contracts."""

from __future__ import annotations

from typing import Protocol

from .models import PuppetState, RendererStatus


class RendererUnavailableError(RuntimeError):
    """Raised when a renderer must be restarted before applying state."""


class Renderer(Protocol):
    def start(self, initial_state: PuppetState) -> RendererStatus: ...

    def apply(self, state: PuppetState) -> RendererStatus: ...

    def get_status(self) -> RendererStatus: ...

    def close(self) -> None: ...