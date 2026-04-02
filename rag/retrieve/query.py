"""Top-K retrieval from the RAG store."""

from __future__ import annotations

import logging
from pathlib import Path

from rag.config import DEFAULT_TOP_K, RAG_DB_PATH
from rag.ingest.embed import EmbeddingProvider
from rag.retrieve.rerank import rerank
from rag.store.sqlite import RagStore
from rag.types import RagHit

logger = logging.getLogger(__name__)


def rag_query(
    query: str,
    *,
    embedding_provider: EmbeddingProvider | None = None,
    top_k: int = DEFAULT_TOP_K,
    db_path: str | Path = RAG_DB_PATH,
) -> list[RagHit]:
    """Query the RAG index and return the top-K most relevant chunks.

    If an embedding_provider is given, uses vector similarity search.
    Falls back to text-based keyword search if no provider is given or
    if a dimension mismatch is detected.
    """
    store = RagStore(db_path)
    store.init_db()

    try:
        if embedding_provider is not None:
            query_embedding = embedding_provider.embed_one(query)
            # Over-fetch 2x so the reranker has candidates to reorder before truncating.
            # Dimension-mismatched chunks (e.g. zero-vector-stub) are skipped transparently.
            hits = store.search_by_embedding(query_embedding, top_k=top_k * 2)
        else:
            hits = store.search_by_text(query, top_k=top_k * 2)

        # Apply reranking (currently a passthrough stub)
        hits = rerank(hits, query)

        return hits[:top_k]
    finally:
        store.close()
