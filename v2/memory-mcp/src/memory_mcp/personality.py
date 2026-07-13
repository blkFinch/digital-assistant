"""Personality loading, listing, and switching."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional


def get_active_personality_name(data_dir: Path) -> str:
    """Read the currently active personality name from state file.

    Returns empty string if no active personality is set (= use default).
    """
    state_file = data_dir / "active_personality.txt"
    if not state_file.exists():
        return ""
    return state_file.read_text(encoding="utf-8").strip()


def set_active_personality(data_dir: Path, name: str) -> str:
    """Set the active personality. Empty name = revert to default.

    Returns the name that was set (or empty string for default).
    """
    state_file = data_dir / "active_personality.txt"
    name = name.strip()

    if not name:
        # Revert to default
        if state_file.exists():
            state_file.unlink()
        return ""

    # Validate the personality file exists
    resolved = _resolve_personality_path(data_dir, name)
    if resolved is None:
        raise FileNotFoundError(
            f"Personality '{name}' not found. "
            f"Expected file at: {data_dir / 'personalities' / (name + '.md')}"
        )

    state_file.write_text(name, encoding="utf-8")
    return name


def load_personality(data_dir: Path, name: str = "") -> str:
    """Load a personality's markdown content.

    - name="" → load active personality (or default if none active)
    - name="pirate" → load personalities/pirate.md specifically
    """
    if name:
        resolved = _resolve_personality_path(data_dir, name)
        if resolved is None:
            raise FileNotFoundError(f"Personality '{name}' not found.")
        return resolved.read_text(encoding="utf-8")

    # No name specified — use active personality, fall back to default
    active = get_active_personality_name(data_dir)
    if active:
        resolved = _resolve_personality_path(data_dir, active)
        if resolved is not None:
            return resolved.read_text(encoding="utf-8")

    # Fall back to default personality.md
    default_path = data_dir / "personality.md"
    if default_path.exists():
        return default_path.read_text(encoding="utf-8")

    return ""


def list_personalities(data_dir: Path) -> List[Dict[str, str]]:
    """List all available personalities.

    Returns list of {name, path, active} dicts.
    """
    personalities_dir = data_dir / "personalities"
    if not personalities_dir.exists():
        return []

    active = get_active_personality_name(data_dir)
    results: List[Dict[str, str]] = []

    for md_file in sorted(personalities_dir.rglob("*.md")):
        try:
            rel = md_file.relative_to(personalities_dir)
        except ValueError:
            continue
        # Name without .md extension
        name = str(rel.with_suffix("")).replace("\\", "/")
        results.append({
            "name": name,
            "path": str(md_file),
            "active": "true" if name == active else "false",
        })

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_personality_path(data_dir: Path, name: str) -> Optional[Path]:
    """Resolve a personality name to its file path, with security checks.

    Returns None if the file doesn't exist or escapes the personalities dir.
    """
    personalities_dir = data_dir / "personalities"
    name_path = Path(name)

    if name_path.is_absolute():
        return None

    candidate = personalities_dir / name_path
    if candidate.suffix == "":
        candidate = candidate.with_suffix(".md")

    # Security: resolved path must stay inside personalities_dir
    try:
        resolved = candidate.resolve()
        resolved.relative_to(personalities_dir.resolve())
    except (ValueError, OSError):
        return None

    if not resolved.exists():
        return None

    return resolved
