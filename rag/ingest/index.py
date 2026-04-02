"""Ingest orchestrator: crawl → chunk → embed → store."""

from __future__ import annotations

import logging
from pathlib import Path

from rag.config import RAG_DB_PATH
from rag.ingest.chunk import chunk_file
from rag.ingest.crawl_repo import crawl_repo
from rag.ingest.embed import EmbeddingProvider
from rag.store.sqlite import RagStore
from rag.types import DocumentRecord, IngestResult, RepoFile
from rag.utils.hash import sha256

logger = logging.getLogger(__name__)


def ingest(
    root_dir: str | Path | None = None,
    repo_ref: str = "worktree",
    embedding_provider: EmbeddingProvider | None = None,
    db_path: str | Path = RAG_DB_PATH,
    files: list[RepoFile] | None = None,
    max_new: int = 0,
) -> IngestResult:
    """Ingest a repository (or pre-crawled files) into the RAG store.

    1. Crawl all files in *root_dir* (or use pre-crawled *files*)
    2. For each file, check if it has changed (hash-based dedup)
    3. Chunk the file
    4. Optionally compute embeddings
    5. Store documents and chunks in SQLite

    If *max_new* > 0, stop after embedding that many new files (useful for
    staying within free-tier API rate limits across multiple runs).
    """
    store = RagStore(db_path)
    store.init_db()

    result = IngestResult()

    try:
        if files is None:
            if root_dir is None:
                raise ValueError("Either root_dir or files must be provided")
            files = crawl_repo(root_dir)

        for file in files:
            doc_id = sha256(f"{repo_ref}:{file.path}")

            # Hash-based deduplication
            existing_hash = store.get_document_hash(repo_ref, file.path)
            if existing_hash == file.hash:
                result.files_skipped += 1
                logger.debug("Skipped (unchanged): %s", file.path)
                continue

            # Upsert document
            doc = DocumentRecord(
                doc_id=doc_id,
                repo_ref=repo_ref,
                path=file.path,
                language=file.language,
                kind=file.kind,
                file_hash=file.hash,
            )
            store.upsert_document(doc)

            # Remove old chunks for this document
            store.delete_chunks_for_doc(doc_id)

            # Chunk the file
            chunks = chunk_file(file, doc_id)

            if not chunks:
                result.files_processed += 1
                continue

            # Compute embeddings
            embeddings: list[list[float]] | None = None
            model_name: str | None = None
            if embedding_provider is not None:
                texts = [c.text for c in chunks]
                embeddings = embedding_provider.embed_many(texts)
                assert len(embeddings) == len(chunks), (
                    f"Embedding count mismatch: {len(embeddings)} embeddings "
                    f"for {len(chunks)} chunks"
                )
                model_name = embedding_provider.model_name

            # Store chunks
            store.upsert_chunks(chunks, embeddings=embeddings, embedding_model=model_name, repo_ref=repo_ref)

            result.files_processed += 1
            result.chunks_created += len(chunks)
            logger.info("Indexed %s \u2192 %d chunks", file.path, len(chunks))

            if max_new and result.files_processed >= max_new:
                logger.info("Batch limit reached (%d files). Re-run to continue.", max_new)
                break

    finally:
        store.close()

    logger.info(
        "Ingest complete: %d processed, %d skipped, %d chunks",
        result.files_processed,
        result.files_skipped,
        result.chunks_created,
    )
    return result
