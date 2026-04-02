"""Keyword-overlap reranker for RAG retrieval results.

Reranks hits by combining their original score with a keyword-overlap
bonus — the fraction of query terms appearing in the chunk text.
No external dependencies required.
"""

from __future__ import annotations

import re

from rag.types import RagHit

# Minimum word length to consider as a keyword (skip "a", "is", etc.)
_MIN_TERM_LENGTH = 2


def rerank(hits: list[RagHit], query: str) -> list[RagHit]:
    """Rerank retrieval results using keyword overlap scoring.

    For each hit, computes the fraction of query terms found in the
    chunk text (case-insensitive) and adds it as a bonus to the
    original score. Hits are re-sorted by the combined score.
    """
    if not hits or not query.strip():
        return hits

    query_terms = _extract_terms(query)
    if not query_terms:
        return hits

    reranked: list[RagHit] = []
    for hit in hits:
        overlap = _keyword_overlap(query_terms, hit.text)
        reranked.append(RagHit(
            chunk_id=hit.chunk_id,
            path=hit.path,
            kind=hit.kind,
            start_line=hit.start_line,
            end_line=hit.end_line,
            score=hit.score + overlap,
            text=hit.text,
        ))

    reranked.sort(key=lambda h: h.score, reverse=True)
    return reranked


def _extract_terms(text: str) -> list[str]:
    """Extract lowercase terms from text, filtering short words."""
    return [
        w.lower()
        for w in re.findall(r"[a-zA-Z0-9_]+", text)
        if len(w) >= _MIN_TERM_LENGTH
    ]


def _keyword_overlap(query_terms: list[str], chunk_text: str) -> float:
    """Return fraction of query terms found in chunk text (0.0 to 1.0)."""
    chunk_lower = chunk_text.lower()
    matches = sum(1 for term in query_terms if term in chunk_lower)
    return matches / len(query_terms)
