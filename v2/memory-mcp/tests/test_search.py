"""Tests for search module."""

import json

import pytest

from memory_mcp.search import keyword_search, search_memories, apply_token_budget


@pytest.fixture
def sample_memories():
    return [
        {"id": "m1", "type": "preference", "subject": "user", "content": "Likes Python and TypeScript", "summary": "Prefers Python and TS", "priority": 75, "reason": "stated"},
        {"id": "m2", "type": "boundary", "subject": "user", "content": "Never send screen contents to cloud without confirmation", "summary": "No cloud screen sharing", "priority": 95, "reason": "security"},
        {"id": "m3", "type": "identity", "subject": "user", "content": "User wants to be called Galen", "summary": "Name: Galen", "priority": 90, "reason": "explicit"},
        {"id": "m4", "type": "habit", "subject": "user", "content": "Prefers dark mode in all editors", "summary": "Dark mode preference", "priority": 25, "reason": "observed"},
        {"id": "m5", "type": "decision", "subject": "assistant", "content": "Architecture uses MCP for all peripherals", "summary": "MCP architecture decision", "priority": 70, "reason": "design"},
    ]


# --- Keyword Search ---

def test_basic_keyword_match(sample_memories):
    results = keyword_search(sample_memories, "Python")
    assert len(results) >= 1
    assert results[0][0]["id"] == "m1"


def test_multi_token_query(sample_memories):
    results = keyword_search(sample_memories, "Python TypeScript")
    assert results[0][0]["id"] == "m1"
    assert results[0][1] > 0.5  # high relevance


def test_no_matches(sample_memories):
    results = keyword_search(sample_memories, "quantum computing")
    assert len(results) == 0


def test_type_filter(sample_memories):
    results = keyword_search(sample_memories, "user", type_filter="boundary")
    ids = [r[0]["id"] for r in results]
    assert "m2" in ids
    assert "m1" not in ids


def test_subject_filter(sample_memories):
    results = keyword_search(sample_memories, "MCP", subject_filter="assistant")
    assert len(results) == 1
    assert results[0][0]["id"] == "m5"


def test_empty_query(sample_memories):
    results = keyword_search(sample_memories, "")
    assert len(results) == 0


def test_priority_boost():
    """High-priority items should score slightly higher for equal keyword matches."""
    # Two memories with identical keyword relevance, different priorities
    memories = [
        {"id": "low", "type": "preference", "subject": "user", "content": "test fact", "summary": "", "priority": 20, "reason": "minor"},
        {"id": "high", "type": "preference", "subject": "user", "content": "test fact", "summary": "", "priority": 95, "reason": "critical"},
    ]
    results = keyword_search(memories, "test fact")
    assert len(results) == 2
    # Higher priority item should rank first when keyword match is equal
    assert results[0][0]["id"] == "high"
    assert results[0][1] > results[1][1]


# --- Token Budgeting ---

def test_summary_detail(sample_memories):
    scored = [(m, 0.9) for m in sample_memories]
    results, tokens = apply_token_budget(scored, detail="summary", token_budget=10000)
    assert len(results) == len(sample_memories)
    # Summary results should have limited fields
    assert "relevance" in results[0]
    assert "content" not in results[0]


def test_full_detail(sample_memories):
    scored = [(m, 0.9) for m in sample_memories]
    results, tokens = apply_token_budget(scored, detail="full", token_budget=10000)
    assert "content" in results[0]
    assert "relevance" in results[0]


def test_budget_limits_results(sample_memories):
    scored = [(m, 0.9) for m in sample_memories]
    # Very small budget — should return fewer items
    results, tokens = apply_token_budget(scored, detail="full", token_budget=50)
    assert len(results) < len(sample_memories)
    assert tokens <= 50 or len(results) == 1  # at least one result always returned


# --- Full Pipeline ---

def test_search_memories_returns_structure(sample_memories):
    result = search_memories(sample_memories, "Galen")
    assert "results" in result
    assert "estimated_tokens" in result
    assert "total_matches" in result
    assert result["total_matches"] >= 1


def test_search_memories_summary_default(sample_memories):
    result = search_memories(sample_memories, "Python")
    # Default detail is summary
    assert "content" not in result["results"][0]
    assert "summary" in result["results"][0]


def test_search_memories_full_detail(sample_memories):
    result = search_memories(sample_memories, "Python", detail="full")
    assert "content" in result["results"][0]
