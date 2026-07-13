"""Tests for personality module."""

import pytest

from memory_mcp.personality import (
    get_active_personality_name,
    set_active_personality,
    load_personality,
    list_personalities,
)


@pytest.fixture
def data_dir(tmp_path):
    # Create default personality
    (tmp_path / "personality.md").write_text("# Default\nYou are helpful.", encoding="utf-8")

    # Create named personalities
    personalities_dir = tmp_path / "personalities"
    personalities_dir.mkdir()
    (personalities_dir / "pirate.md").write_text("# Pirate\nYe be a pirate.", encoding="utf-8")
    (personalities_dir / "formal.md").write_text("# Formal\nSpeak formally.", encoding="utf-8")

    return tmp_path


# --- Active personality state ---

def test_no_active_by_default(data_dir):
    assert get_active_personality_name(data_dir) == ""


def test_set_and_get_active(data_dir):
    set_active_personality(data_dir, "pirate")
    assert get_active_personality_name(data_dir) == "pirate"


def test_revert_to_default(data_dir):
    set_active_personality(data_dir, "pirate")
    set_active_personality(data_dir, "")
    assert get_active_personality_name(data_dir) == ""
    assert not (data_dir / "active_personality.txt").exists()


def test_set_nonexistent_raises(data_dir):
    with pytest.raises(FileNotFoundError):
        set_active_personality(data_dir, "nonexistent")


# --- Load personality ---

def test_load_default(data_dir):
    text = load_personality(data_dir)
    assert "Default" in text


def test_load_named(data_dir):
    text = load_personality(data_dir, "pirate")
    assert "pirate" in text.lower()


def test_load_active(data_dir):
    set_active_personality(data_dir, "pirate")
    text = load_personality(data_dir)  # no name = use active
    assert "pirate" in text.lower()


def test_load_active_falls_back_to_default(data_dir):
    # Active personality file points to something that no longer exists
    (data_dir / "active_personality.txt").write_text("deleted", encoding="utf-8")
    text = load_personality(data_dir)
    assert "Default" in text


def test_load_nonexistent_raises(data_dir):
    with pytest.raises(FileNotFoundError):
        load_personality(data_dir, "nonexistent")


# --- List personalities ---

def test_list_personalities(data_dir):
    items = list_personalities(data_dir)
    names = [p["name"] for p in items]
    assert "pirate" in names
    assert "formal" in names


def test_list_shows_active(data_dir):
    set_active_personality(data_dir, "pirate")
    items = list_personalities(data_dir)
    pirate = next(p for p in items if p["name"] == "pirate")
    formal = next(p for p in items if p["name"] == "formal")
    assert pirate["active"] == "true"
    assert formal["active"] == "false"


def test_list_empty_dir(tmp_path):
    assert list_personalities(tmp_path) == []


# --- Security ---

def test_path_traversal_blocked(data_dir):
    with pytest.raises(FileNotFoundError):
        load_personality(data_dir, "../../etc/passwd")


def test_absolute_path_blocked(data_dir):
    with pytest.raises(FileNotFoundError):
        load_personality(data_dir, "/etc/passwd")
