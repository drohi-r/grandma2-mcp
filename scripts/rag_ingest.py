"""CLI script to ingest the repository into the RAG index.

Usage:
    uv run python scripts/rag_ingest.py [--root .] [--ref worktree] [--db rag/store/rag.db]
    uv run python scripts/rag_ingest.py --provider github   # use GitHub Models embeddings
    uv run python scripts/rag_ingest.py --provider github --embed-delay 4.0 --embed-batch-size 32
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import RAG_DB_PATH
from rag.ingest.embed import (
    EmbeddingProvider,
    GitHubModelsProvider,
    ZeroVectorProvider,
)
from rag.ingest.index import ingest

logger = logging.getLogger(__name__)


def make_provider(
    choice: str | None,
    inter_request_delay: float = 4.0,
    batch_size: int = 32,
) -> EmbeddingProvider:
    """Build an embedding provider from --provider flag and env vars."""
    token = os.environ.get("GITHUB_MODELS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    model = os.environ.get("RAG_EMBED_MODEL", "openai/text-embedding-3-small")
    dimensions = int(os.environ.get("RAG_EMBED_DIMENSIONS", "1536"))

    if choice == "github":
        if not token:
            print(
                "Error: --provider github requires GITHUB_MODELS_TOKEN or GITHUB_TOKEN env var.",
                file=sys.stderr,
            )
            sys.exit(1)
        return GitHubModelsProvider(
            token=token,
            model=model,
            dimensions=dimensions,
            batch_size=batch_size,
            inter_request_delay=inter_request_delay,
        )

    if choice == "zero":
        return ZeroVectorProvider()

    # Auto-detect: use GitHub Models if token is set, otherwise zero-vector
    if token:
        logger.info("Auto-detected GITHUB_MODELS_TOKEN, using GitHub Models provider")
        return GitHubModelsProvider(
            token=token,
            model=model,
            dimensions=dimensions,
            batch_size=batch_size,
            inter_request_delay=inter_request_delay,
        )

    logger.warning("No embedding API token found — using zero-vector stub (no semantic search)")
    return ZeroVectorProvider()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest repository into the RAG index")
    parser.add_argument("--root", default=".", help="Repository root directory (default: .)")
    parser.add_argument("--ref", default="worktree", help="Repo reference label (default: worktree)")
    parser.add_argument("--db", default=str(RAG_DB_PATH), help=f"SQLite database path (default: {RAG_DB_PATH})")
    parser.add_argument(
        "--provider",
        choices=["github", "zero"],
        default=None,
        help="Embedding provider (default: auto-detect from env vars)",
    )
    parser.add_argument(
        "--embed-delay",
        type=float,
        default=4.0,
        metavar="SECS",
        help="Seconds between embedding API calls (default: 4.0). Prevents per-minute rate limits.",
    )
    parser.add_argument(
        "--embed-batch-size",
        type=int,
        default=32,
        metavar="N",
        help="Texts per embedding API request (default: 32).",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Ensure the database directory exists
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    provider = make_provider(
        args.provider,
        inter_request_delay=args.embed_delay,
        batch_size=args.embed_batch_size,
    )
    logger.info("Using embedding provider: %s", provider.model_name)

    result = ingest(
        root_dir=args.root,
        repo_ref=args.ref,
        embedding_provider=provider,
        db_path=db_path,
    )

    print("\nIngest complete:")
    print(f"  Provider:        {provider.model_name}")
    print(f"  Files processed: {result.files_processed}")
    print(f"  Files skipped:   {result.files_skipped}")
    print(f"  Chunks created:  {result.chunks_created}")


if __name__ == "__main__":
    main()
