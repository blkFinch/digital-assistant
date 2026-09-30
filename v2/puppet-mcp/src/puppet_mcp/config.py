"""Environment-backed startup configuration."""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass

from .assets import AssetCatalog


@dataclass(frozen=True)
class Settings:
    puppet: str = "chibi"
    window_title: str = "AI Vtuber Puppet"
    startup_timeout: float = 5.0
    command_timeout: float = 2.0


def _positive_float(value: str, variable: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{variable} must be a number") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError(f"{variable} must be finite and greater than zero")
    return parsed


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if environ is None else environ
    puppet = env.get("PUPPET_MCP_PUPPET", "chibi").strip().lower()
    available = AssetCatalog().list_puppets()
    if puppet not in available:
        raise ValueError(
            f"PUPPET_MCP_PUPPET must be one of: {', '.join(available)}"
        )

    title = env.get("PUPPET_MCP_WINDOW_TITLE", "AI Vtuber Puppet").strip()
    if not title:
        raise ValueError("PUPPET_MCP_WINDOW_TITLE must not be blank")

    startup = _positive_float(
        env.get("PUPPET_MCP_STARTUP_TIMEOUT", "5.0"),
        "PUPPET_MCP_STARTUP_TIMEOUT",
    )
    command = _positive_float(
        env.get("PUPPET_MCP_COMMAND_TIMEOUT", "2.0"),
        "PUPPET_MCP_COMMAND_TIMEOUT",
    )
    return Settings(puppet, title, startup, command)