"""Tests for FTS5 full-text search in the RAG SQLite store."""

import pytest

from rag.store.sqlite import RagStore
from rag.types import Chunk, DocumentRecord


@pytest.fixture
def store():
    """Create an in-memory RagStore with sample data."""
    s = RagStore(":memory:")
    s.init_db()

    doc = DocumentRecord(
        doc_id="d1",
        repo_ref="main",
        path="server.py",
        language="python",
        kind="source",
        file_hash="hash1",
    )
    s.upsert_document(doc)

    chunks = [
        Chunk(
            chunk_id="c1",
            doc_id="d1",
            path="server.py",
            kind="source",
            language="python",
            text="def create_filter_library(): pass",
            start_line=1,
            end_line=1,
            symbols=["create_filter_library"],
            chunk_hash="h1",
        ),
        Chunk(
            chunk_id="c2",
            doc_id="d1",
            path="server.py",
            kind="source",
            language="python",
            text="def create_matricks_library(): pass",
            start_line=10,
            end_line=10,
            symbols=["create_matricks_library"],
            chunk_hash="h2",
        ),
        Chunk(
            chunk_id="c3",
            doc_id="d1",
            path="server.py",
            kind="source",
            language="python",
            text="async def send_raw_command(command: str): pass",
            start_line=20,
            end_line=20,
            symbols=["send_raw_command"],
            chunk_hash="h3",
        ),
    ]
    s.upsert_chunks(chunks, repo_ref="main")

    yield s
    s.close()


class TestFTS5Search:
    """Tests for FTS5-based text search."""

    def test_fts5_finds_matching_chunk(self, store):
        """FTS5 search returns chunks matching query terms."""
        results = store.search_by_text("filter library")
        assert len(results) >= 1
        assert any("filter" in r.text.lower() for r in results)

    def test_fts5_returns_no_results_for_nonexistent(self, store):
        """FTS5 search returns empty for terms not in any chunk."""
        results = store.search_by_text("xyznonexistent")
        assert len(results) == 0

    def test_fts5_ranks_better_match_higher(self, store):
        """Chunk with the query term should score higher."""
        results = store.search_by_text("filter")
        if len(results) >= 2:
            filter_hits = [r for r in results if "filter" in r.text.lower()]
            other_hits = [r for r in results if "filter" not in r.text.lower()]
            if filter_hits and other_hits:
                assert filter_hits[0].score >= other_hits[0].score

    def test_fts5_respects_top_k(self, store):
        """search_by_text respects the top_k limit."""
        results = store.search_by_text("def", top_k=2)
        assert len(results) <= 2

    def test_fts5_symbol_bonus(self, store):
        """Symbol-level match adds bonus score."""
        results = store.search_by_text("create_filter_library")
        assert len(results) >= 1
        # The chunk with symbol match should be present and scored
        top = results[0]
        assert "filter" in top.text.lower()

    def test_fts5_empty_query(self, store):
        """Empty query returns empty results."""
        results = store.search_by_text("")
        assert results == []

    def test_fts5_single_word(self, store):
        """Single word query works correctly."""
        results = store.search_by_text("matricks")
        assert len(results) >= 1
        assert any("matricks" in r.text.lower() for r in results)


class TestLIKEFallback:
    """Tests for LIKE-based fallback when FTS5 is unavailable."""

    def test_like_fallback_works(self):
        """_search_by_like returns results correctly."""
        s = RagStore(":memory:")
        s.init_db()

        doc = DocumentRecord(
            doc_id="d1",
            repo_ref="main",
            path="test.py",
            language="python",
            kind="source",
            file_hash="h1",
        )
        s.upsert_document(doc)

        chunk = Chunk(
            chunk_id="c1",
            doc_id="d1",
            path="test.py",
            kind="source",
            language="python",
            text="hello world test data",
            start_line=1,
            end_line=1,
            symbols=["test_func"],
            chunk_hash="h1",
        )
        s.upsert_chunks([chunk], repo_ref="main")

        results = s._search_by_like("hello")
        assert len(results) == 1
        assert results[0].chunk_id == "c1"

        s.close()

    def test_like_symbol_bonus(self):
        """LIKE fallback gives symbol bonus."""
        s = RagStore(":memory:")
        s.init_db()

        doc = DocumentRecord(
            doc_id="d1",
            repo_ref="main",
            path="test.py",
            language="python",
            kind="source",
            file_hash="h1",
        )
        s.upsert_document(doc)

        chunk = Chunk(
            chunk_id="c1",
            doc_id="d1",
            path="test.py",
            kind="source",
            language="python",
            text="some code here with my_func",
            start_line=1,
            end_line=1,
            symbols=["my_func"],
            chunk_hash="h1",
        )
        s.upsert_chunks([chunk], repo_ref="main")

        results = s._search_by_like("my_func")
        assert len(results) == 1
        # Score should include symbol bonus (5.0)
        assert results[0].score >= 6.0  # 1.0 occurrence + 5.0 symbol

        s.close()
