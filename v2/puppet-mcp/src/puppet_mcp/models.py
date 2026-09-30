"""Immutable state exchanged between the controller and renderers."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from numbers import Real
from typing import Literal


def _normalized_text(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError(f"{field} must not be blank")
    return normalized


@dataclass(frozen=True)
class PuppetState:
    puppet: str
    expression: str = "idle"
    intensity: float = 0.5

    def __post_init__(self) -> None:
        object.__setattr__(self, "puppet", _normalized_text(self.puppet, "puppet"))
        object.__setattr__(
            self, "expression", _normalized_text(self.expression, "expression")
        )
        if isinstance(self.intensity, bool) or not isinstance(self.intensity, Real):
            raise ValueError("intensity must be a number")
        intensity = float(self.intensity)
        if not math.isfinite(intensity) or not 0.0 <= intensity <= 1.0:
            raise ValueError("intensity must be finite and between 0.0 and 1.0")
        object.__setattr__(self, "intensity", intensity)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "PuppetState":
        return cls(
            puppet=value.get("puppet"),  # type: ignore[arg-type]
            expression=value.get("expression", "idle"),  # type: ignore[arg-type]
            intensity=value.get("intensity", 0.5),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class RendererStatus:
    backend: str
    status: Literal["starting", "ready", "stopped", "error"]
    error: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"starting", "ready", "stopped", "error"}:
            raise ValueError(f"Invalid renderer status '{self.status}'")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)