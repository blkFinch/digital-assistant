"""Tests for memory_store module."""

import json
from pathlib import Path

import pytest

from memory_mcp.memory_store import (
    MemoryItem,
    create_memory,
    delete_memory,
    get_memory_by_id,
    load_ltm,
    load_revision_log,
    save_ltm,
    update_memory,
    load_sanitized_ltm,
    gate_memory_updates,
    _auto_summary,
)


@pytest.fixture
def data_dir(tmp_path):
    ltm_path = tmp_path / "ltm.json"
    ltm_path.write_text("[]", encoding="utf-8")
    return tmp_path


@pytest.fixture
def ltm_path(data_dir):
    return data_dir / "ltm.json"


@pytest.fixture
def rev_path(data_dir):
    return data_dir / "revision_log.jsonl"


# --- Load / Save ---

def test_load_empty(ltm_path):
    assert load_ltm(ltm_path) == []


def test_load_missing_file(tmp_path):
    assert load_ltm(tmp_path / "nonexistent.json") == []


def test_save_and_load(ltm_path):
    items = [{"id": "mem_1", "content": "hello"}]
    save_ltm(items, ltm_path)
    loaded = load_ltm(ltm_path)
    assert len(loaded) == 1
    assert loaded[0]["content"] == "hello"


def test_load_corrupt_json(ltm_path):
    ltm_path.write_text("not valid json", encoding="utf-8")
    assert load_ltm(ltm_path) == []


def test_load_sanitized_sorts_by_last_updated(ltm_path):
    items = [
        {"id": "old", "last_updated": "2025-01-01T00:00:00Z"},
        {"id": "new", "last_updated": "2026-06-01T00:00:00Z"},
    ]
    save_ltm(items, ltm_path)
    result = load_sanitized_ltm(ltm_path)
    assert result[0]["id"] == "new"


# --- CRUD ---

def test_create_memory(ltm_path, rev_path):
    item = create_memory(
        ltm_path=ltm_path,
        revision_log_path=rev_path,
        mem_type="preference",
        subject="user",
        content="Likes Python",
        confidence=0.9,
        priority=75,
        reason="User stated explicitly",
    )
    assert item["type"] == "preference"
    assert item["priority"] == 75
    assert item["strength"] == 1
    assert item["summary"]  # auto-generated
    assert item["id"].startswith("mem_")

    # Persisted
    loaded = load_ltm(ltm_path)
    assert len(loaded) == 1
    assert loaded[0]["id"] == item["id"]

    # Revision log written
    log = load_revision_log(rev_path)
    assert len(log) == 1
    assert log[0]["action"] == "create"


def test_update_memory(ltm_path, rev_path):
    item = create_memory(
        ltm_path=ltm_path, revision_log_path=rev_path,
        mem_type="preference", subject="user", content="Likes Python",
        confidence=0.8, priority=50, reason="test",
    )
    updated = update_memory(
        ltm_path=ltm_path, revision_log_path=rev_path,
        memory_id=item["id"],
        content="Loves Python and Rust",
        priority=80,
        reason="updated preference",
    )
    assert updated is not None
    assert updated["content"] == "Loves Python and Rust"
    assert updated["priority"] == 80
    assert updated["strength"] == 2  # bumped


def test_update_nonexistent(ltm_path, rev_path):
    result = update_memory(
        ltm_path=ltm_path, revision_log_path=rev_path,
        memory_id="mem_nonexistent", content="test",
    )
    assert result is None


def test_delete_memory(ltm_path, rev_path):
    item = create_memory(
        ltm_path=ltm_path, revision_log_path=rev_path,
        mem_type="habit", subject="user", content="test",
        confidence=0.5, priority=30, reason="test",
    )
    assert delete_memory(ltm_path=ltm_path, revision_log_path=rev_path, memory_id=item["id"])
    assert load_ltm(ltm_path) == []


def test_delete_nonexistent(ltm_path, rev_path):
    assert not delete_memory(ltm_path=ltm_path, revision_log_path=rev_path, memory_id="nope")


def test_get_memory_by_id(ltm_path, rev_path):
    item = create_memory(
        ltm_path=ltm_path, revision_log_path=rev_path,
        mem_type="identity", subject="user", content="Name is Galen",
        confidence=0.95, priority=90, reason="explicit",
    )
    found = get_memory_by_id(ltm_path, item["id"])
    assert found is not None
    assert found["content"] == "Name is Galen"
    assert get_memory_by_id(ltm_path, "nonexistent") is None


# --- Auto summary ---

def test_auto_summary_short():
    assert _auto_summary("Short text") == "Short text"


def test_auto_summary_long():
    long = "a" * 200
    result = _auto_summary(long)
    assert len(result) == 120
    assert result.endswith("...")


# --- Gating ---

def test_gate_filters_low_confidence():
    payload = {"candidates": [
        {"confidence": 0.8, "content": "keep"},
        {"confidence": 0.2, "content": "drop"},
    ]}
    gated, stats = gate_memory_updates(payload, min_confidence=0.5)
    assert stats["kept"] == 1
    assert stats["removed"] == 1
    assert len(gated["candidates"]) == 1
