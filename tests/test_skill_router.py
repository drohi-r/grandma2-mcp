"""Skill router — rank skills against natural-language intent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.skill_router import rank_skills


def test_rank_returns_top_k():
    """rank_skills returns at most top_k results, sorted by score descending."""
    results = rank_skills(intent="make me a color picker", top_k=3,
                          method="keyword")
    assert len(results) <= 3
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_rank_picks_color_skill_for_color_intent():
    """For an obvious color intent, a color-related skill is in top-2."""
    results = rank_skills(intent="make me a color picker layout", top_k=3,
                          method="keyword")
    top_names = {r["name"] for r in results[:2]}
    assert any("color" in n.lower() or "color" in r["why"].lower()
               for n, r in zip(top_names, results[:2]))


def test_rank_picks_macro_skill_for_macro_intent():
    results = rank_skills(intent="make me a song-change macro for songs", top_k=3,
                          method="keyword")
    top_names = " ".join(r["name"].lower() for r in results[:2])
    assert "macro" in top_names


def test_rank_returns_required_fields():
    results = rank_skills(intent="busking template for rock band", top_k=1,
                          method="keyword")
    assert results
    r = results[0]
    for field in ("name", "version", "score", "why", "first_decision",
                  "safety_scope", "tags", "prerequisites", "estimated_tokens"):
        assert field in r, f"missing field: {field}"


def test_rank_returns_empty_list_for_unmatched_intent():
    results = rank_skills(intent="zzzzzzz nonsense gibberish quibble", top_k=3,
                          method="keyword")
    assert results == []


@pytest.mark.asyncio
async def test_suggest_skills_for_task_returns_json_envelope():
    """The registered MCP tool returns a JSON-encoded SuggestSkillsResponse."""
    from src.server import suggest_skills_for_task
    raw = await suggest_skills_for_task(
        intent="make a color picker", top_k=3, prefer_semantic=False,
    )
    data = json.loads(raw)
    assert data["intent"] == "make a color picker"
    assert data["method"] in ("keyword", "semantic", "hybrid")
    assert isinstance(data["suggestions"], list)
    assert len(data["suggestions"]) <= 3


def test_index_md_exists_and_covers_every_skill():
    """Every directory in .claude/skills/ must be listed in INDEX.md."""
    skills_dir = Path(".claude/skills")
    index_path = skills_dir / "INDEX.md"
    assert index_path.exists(), "INDEX.md must exist in .claude/skills/"
    index_text = index_path.read_text(encoding="utf-8")
    for skill_path in sorted(skills_dir.iterdir()):
        if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
            assert skill_path.name in index_text, (
                f"INDEX.md is missing entry for {skill_path.name}"
            )
