"""Tests for the keyword-overlap reranker."""

import pytest

from rag.retrieve.rerank import _extract_terms, _keyword_overlap, rerank
from rag.types import RagHit


def _make_hit(chunk_id: str, text: str, score: float = 1.0) -> RagHit:
    """Helper to create a RagHit for testing."""
    return RagHit(
        chunk_id=chunk_id,
        path="test.py",
        kind="source",
        start_line=1,
        end_line=1,
        score=score,
        text=text,
    )


class TestExtractTerms:
    """Tests for _extract_terms helper."""

    def test_basic_extraction(self):
        terms = _extract_terms("hello world")
        assert terms == ["hello", "world"]

    def test_filters_short_words(self):
        terms = _extract_terms("a I the big cat")
        assert "a" not in terms
        assert "i" not in terms  # single char, filtered out
        assert "big" in terms
        assert "cat" in terms

    def test_lowercased(self):
        terms = _extract_terms("Hello World")
        assert terms == ["hello", "world"]

    def test_handles_special_chars(self):
        terms = _extract_terms("create_filter_library()")
        assert "create_filter_library" in terms

    def test_empty_string(self):
        assert _extract_terms("") == []


class TestKeywordOverlap:
    """Tests for _keyword_overlap helper."""

    def test_full_overlap(self):
        score = _keyword_overlap(["hello", "world"], "hello world test")
        assert score == 1.0

    def test_partial_overlap(self):
        score = _keyword_overlap(["hello", "world", "foo"], "hello world test")
        assert abs(score - 2.0 / 3.0) < 0.01

    def test_no_overlap(self):
        score = _keyword_overlap(["xyz", "abc"], "hello world")
        assert score == 0.0

    def test_case_insensitive(self):
        score = _keyword_overlap(["hello"], "HELLO WORLD")
        assert score == 1.0


class TestRerank:
    """Tests for the rerank function."""

    def test_reranks_by_keyword_overlap(self):
        """Hit with more query terms should rank higher after reranking."""
        hits = [
            _make_hit("c1", "send raw command to console", score=1.0),
            _make_hit("c2", "create filter library with color data", score=1.0),
        ]
        result = rerank(hits, "filter library")
        assert result[0].chunk_id == "c2"

    def test_preserves_empty_list(self):
        assert rerank([], "query") == []

    def test_preserves_with_empty_query(self):
        hits = [_make_hit("c1", "test")]
        result = rerank(hits, "")
        assert len(result) == 1

    def test_adds_overlap_to_existing_score(self):
        hits = [_make_hit("c1", "filter library data", score=5.0)]
        result = rerank(hits, "filter library")
        # Original score 5.0 + overlap 1.0 (both terms match)
        assert result[0].score > 5.0

    def test_does_not_modify_original_hits(self):
        hits = [_make_hit("c1", "hello world", score=1.0)]
        original_score = hits[0].score
        rerank(hits, "hello")
        assert hits[0].score == original_score

    def test_multiple_hits_sorted_correctly(self):
        """Hits sorted by combined score descending."""
        hits = [
            _make_hit("c1", "no match here at all", score=10.0),
            _make_hit("c2", "filter library color preset data", score=1.0),
            _make_hit("c3", "filter something else", score=5.0),
        ]
        result = rerank(hits, "filter library color preset")
        # c2 has highest overlap (4/4 = 1.0) + 1.0 = 2.0
        # c3 has partial overlap (1/4 = 0.25) + 5.0 = 5.25
        # c1 has no overlap (0/4 = 0.0) + 10.0 = 10.0
        assert result[0].chunk_id == "c1"  # highest total score
        assert result[1].chunk_id == "c3"
        assert result[2].chunk_id == "c2"
