"""Data directory and path resolution for the Memory MCP server."""

from __future__ import annotations

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Resolve the root data directory.

    Precedence:
    1. MEMORY_MCP_DATA_DIR env var
    2. ~/.ai-memory/
    """
    env = (os.getenv("MEMORY_MCP_DATA_DIR") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".ai-memory"


def get_ltm_name() -> str:
    """Return the LTM_NAME env var (empty string = default store)."""
    return (os.getenv("LTM_NAME") or "").strip()


def get_ltm_path(data_dir: Path, ltm_name: str = "") -> Path:
    """Resolve the path to ltm.json.

    - No ltm_name: data_dir / ltm.json
    - With ltm_name: data_dir / ltm / <ltm_name> / ltm.json
    """
    if not ltm_name:
        return data_dir / "ltm.json"

    name_path = Path(ltm_name)
    if name_path.is_absolute():
        raise RuntimeError(
            "Invalid LTM_NAME: must be a relative name like 'yuki' (no absolute paths)."
        )

    candidate = (data_dir / "ltm" / name_path).resolve()
    root = (data_dir / "ltm").resolve()
    try:
        candidate.relative_to(root)
    except ValueError as e:
        raise RuntimeError(
            f"Invalid LTM_NAME '{ltm_name}': resolved path must be inside {root}"
        ) from e

    return candidate / "ltm.json"


def get_revision_log_path(data_dir: Path, ltm_name: str = "") -> Path:
    """Resolve the path to revision_log.jsonl (parallel to ltm.json)."""
    ltm = get_ltm_path(data_dir, ltm_name)
    return ltm.parent / "revision_log.jsonl"


def get_personalities_dir(data_dir: Path) -> Path:
    """Return the personalities directory."""
    return data_dir / "personalities"


def get_active_personality_path(data_dir: Path) -> Path:
    """Return the path to the active_personality.txt state file."""
    return data_dir / "active_personality.txt"


def get_default_personality_path(data_dir: Path) -> Path:
    """Return the path to the default personality.md file."""
    return data_dir / "personality.md"


def get_reflection_prompt_path(data_dir: Path) -> Path:
    """Return the path to the reflection prompt template."""
    return data_dir / "prompts" / "reflection_prompt.txt"


def bootstrap_data_dir(data_dir: Path) -> None:
    """Create the data directory structure with sensible defaults if missing."""
    data_dir.mkdir(parents=True, exist_ok=True)

    ltm_path = data_dir / "ltm.json"
    if not ltm_path.exists():
        ltm_path.write_text("[]", encoding="utf-8")

    personality_path = data_dir / "personality.md"
    if not personality_path.exists():
        personality_path.write_text(
            "# Default Personality\n\n"
            "You are a helpful, friendly assistant.\n",
            encoding="utf-8",
        )

    personalities_dir = data_dir / "personalities"
    personalities_dir.mkdir(exist_ok=True)

    prompts_dir = data_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)
