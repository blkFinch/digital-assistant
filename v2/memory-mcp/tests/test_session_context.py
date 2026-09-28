"""Tests for session context assembly."""

from memory_mcp import memory_store
from memory_mcp.session_context import build_session_context


def test_build_session_context_buckets_high_priority_memories(tmp_path):
    (tmp_path / "personality.md").write_text("# Test\nBe concise.", encoding="utf-8")
    ltm_path = tmp_path / "ltm.json"
    rev_path = tmp_path / "revision_log.jsonl"
    ltm_path.write_text("[]", encoding="utf-8")

    memory_store.create_memory(
        ltm_path=ltm_path,
        revision_log_path=rev_path,
        mem_type="identity",
        subject="user",
        content="User wants to be called Galen.",
        summary="User wants to be called Galen",
        confidence=0.95,
        priority=90,
        reason="explicit",
    )
    memory_store.create_memory(
        ltm_path=ltm_path,
        revision_log_path=rev_path,
        mem_type="boundary",
        subject="user",
        content="Never expose secrets.",
        summary="Never expose secrets",
        confidence=0.95,
        priority=95,
        reason="security",
    )
    memory_store.create_memory(
        ltm_path=ltm_path,
        revision_log_path=rev_path,
        mem_type="preference",
        subject="user",
        content="Prefers retro emoticons in communication.",
        summary="Prefers retro emoticons",
        confidence=0.9,
        priority=75,
        reason="user preference",
    )
    memory_store.create_memory(
        ltm_path=ltm_path,
        revision_log_path=rev_path,
        mem_type="habit",
        subject="user",
        content="Likes dark mode.",
        summary="Likes dark mode",
        confidence=0.7,
        priority=25,
        reason="minor preference",
    )

    result = build_session_context(data_dir=tmp_path, ltm_path=ltm_path)

    assert result["personality"]["active_name"] == "(default)"
    assert result["personality"]["content"].startswith("# Test")
    assert result["user_profile"]["preferred_name"] == "Galen"
    assert len(result["user_profile"]["identity"]) == 1
    assert len(result["user_profile"]["preferences"]) == 1
    assert len(result["critical_boundaries"]) == 1
    assert len(result["communication_preferences"]) == 2
    assert result["metadata"]["total_available_memories"] == 4
    assert result["metadata"]["startup_memory_candidates"] == 3


def test_build_session_context_keeps_other_critical_memories(tmp_path):
    (tmp_path / "personality.md").write_text("# Test\nBe useful.", encoding="utf-8")
    ltm_path = tmp_path / "ltm.json"
    rev_path = tmp_path / "revision_log.jsonl"
    ltm_path.write_text("[]", encoding="utf-8")

    memory_store.create_memory(
        ltm_path=ltm_path,
        revision_log_path=rev_path,
        mem_type="decision",
        subject="assistant",
        content="Architecture uses MCP for peripherals.",
        summary="MCP architecture decision",
        confidence=0.9,
        priority=80,
        reason="project direction",
    )

    result = build_session_context(
        data_dir=tmp_path,
        ltm_path=ltm_path,
        ltm_name="work",
    )

    assert result["metadata"]["ltm_name"] == "work"
    assert len(result["other_critical_memories"]) == 1
    assert result["other_critical_memories"][0]["summary"] == "MCP architecture decision"
