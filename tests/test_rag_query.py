"""Tests for the RAG query pipeline."""

import pytest

from rag.ingest.embed import ZeroVectorProvider
from rag.retrieve.query import rag_query
from rag.store.sqlite import RagStore
from rag.types import Chunk, DocumentRecord


@pytest.fixture
def populated_db(tmp_path):
    """Create a temporary RAG database with sample data."""
    db_path = tmp_path / "test_rag.db"
    store = RagStore(db_path)
    store.init_db()

    doc = DocumentRecord(
        doc_id="d1", repo_ref="test", path="src/commands/store.py",
        language="python", kind="source", file_hash="h1",
    )
    store.upsert_document(doc)

    provider = ZeroVectorProvider(dimensions=3)

    chunks = [
        Chunk(
            chunk_id="c1", doc_id="d1", path="src/commands/store.py",
            kind="source", language="python",
            text="def store_cue(cue_id): return f'store cue {cue_id}'",
            start_line=1, end_line=1, symbols=["store_cue"], chunk_hash="ch1",
        ),
        Chunk(
            chunk_id="c2", doc_id="d1", path="src/commands/store.py",
            kind="source", language="python",
            text="def store_group(group_id): return f'store group {group_id}'",
            start_line=10, end_line=15, symbols=["store_group"], chunk_hash="ch2",
        ),
    ]

    embeddings = provider.embed_many([c.text for c in chunks])
    store.upsert_chunks(chunks, embeddings=embeddings, embedding_model="zero-vector-stub", repo_ref="test")
    store.close()

    return db_path


class TestRagQuery:
    def test_text_search(self, populated_db):
        hits = rag_query("store_cue", db_path=populated_db)
        assert len(hits) >= 1
        assert any("store_cue" in h.text for h in hits)

    def test_text_search_no_results(self, populated_db):
        hits = rag_query("nonexistent_function_xyz", db_path=populated_db)
        assert hits == []

    def test_top_k_limit(self, populated_db):
        hits = rag_query("store", top_k=1, db_path=populated_db)
        assert len(hits) <= 1

    def test_returns_rag_hits(self, populated_db):
        hits = rag_query("store", db_path=populated_db)
        for hit in hits:
            assert hit.path == "src/commands/store.py"
            assert hit.kind == "source"
            assert hit.start_line >= 1
