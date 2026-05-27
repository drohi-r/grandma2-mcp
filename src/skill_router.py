"""Skill router — semantic + keyword ranking over the skill registry.

Mirrors src/server.py:suggest_tool_for_task patterns for consistency.
Pure module — no network I/O, no telnet client; reads SKILL.md files
via the existing SkillRegistry filesystem fallback.

Public API:
    rank_skills(intent, *, top_k, method, include_destructive, registry)
        → list[SkillSuggestion]
"""

from __future__ import annotations

from typing import Literal, TypedDict

from src.skill import Skill, SkillRegistry, _list_filesystem_skills


class SkillSuggestion(TypedDict):
    """The shape of a single ranking result.

    Matches the spec's Appendix A.1 SkillSuggestion TypedDict.
    """

    name: str
    version: str
    score: float
    why: str
    first_decision: str | None
    safety_scope: str
    tags: list[str]
    prerequisites: list[str]
    estimated_tokens: int


_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with",
    "me", "my", "i", "is", "are", "be", "this", "that", "make", "build",
    "create", "do", "it", "as", "at", "by",
})


def _tokenize(text: str) -> set[str]:
    """Split text into normalised non-stopword tokens."""
    tokens = (
        text.lower()
        .replace("-", " ")
        .replace("_", " ")
        .replace(".", " ")
        .replace(",", " ")
        .replace("/", " ")
        .split()
    )
    return {t for t in tokens if t not in _STOPWORDS and len(t) > 1}


def _extract_first_decision(body: str) -> str | None:
    """Extract a 'First decision' line/section header from a skill body, if any."""
    lower_lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        low = stripped.lower()
        if low.startswith(("first decision", "**first decision",
                            "## first decision")):
            return stripped
        lower_lines.append(low)
    return None


def _keyword_score(intent_tokens: set[str], text_tokens: set[str]) -> float:
    """Normalised overlap score in [0.0, 1.0]."""
    if not intent_tokens:
        return 0.0
    overlap = intent_tokens & text_tokens
    return len(overlap) / len(intent_tokens)


def _to_suggestion(skill: Skill, score: float) -> SkillSuggestion:
    return SkillSuggestion(
        name=skill.name,
        version=str(skill.version),
        score=round(score, 4),
        why=(skill.description or "")[:120],
        first_decision=_extract_first_decision(skill.body or ""),
        safety_scope=skill.safety_scope,
        # tags / prerequisites populated by enrichment elsewhere; defaults here.
        tags=[],
        prerequisites=[],
        estimated_tokens=max(1, len(skill.body or "") // 4),
    )


def rank_skills(
    intent: str,
    *,
    top_k: int = 3,
    method: Literal["semantic", "keyword", "hybrid"] = "keyword",
    include_destructive: bool = True,
    registry: SkillRegistry | None = None,
) -> list[SkillSuggestion]:
    """Rank skills against an intent string.

    Args:
        intent: Natural-language description of the operator's goal.
        top_k: Max number of suggestions to return.
        method: Ranking algorithm. ``keyword`` is the only fully wired option
            in Path A; ``semantic`` and ``hybrid`` fall back to keyword with no
            error (the caller's outer wrapper records a warning where applicable).
        include_destructive: When False, drop un-approved DESTRUCTIVE skills.
        registry: Optional SkillRegistry to source DB skills. Filesystem skills
            are always read from .claude/skills/ via the registry's fallback.

    Returns:
        Up to ``top_k`` matching suggestions, sorted by descending score.
    """
    corpus: list[Skill] = []
    if registry is not None:
        corpus.extend(registry.list_all(limit=200))
    fs_skills = _list_filesystem_skills()
    seen_ids = {s.id for s in corpus}
    corpus.extend(s for s in fs_skills if s.id not in seen_ids)

    if not include_destructive:
        corpus = [s for s in corpus if s.is_usable()]

    intent_tokens = _tokenize(intent)
    scored: list[tuple[float, Skill]] = []
    for s in corpus:
        text = " ".join([
            s.name or "",
            s.description or "",
            s.applicable_context or "",
            (s.body or "")[:2000],
        ])
        score = _keyword_score(intent_tokens, _tokenize(text))
        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: -x[0])
    return [_to_suggestion(s, score) for score, s in scored[:top_k]]


__all__ = ["rank_skills", "SkillSuggestion"]
