"""CLI script to query the RAG index.

Usage:
    uv run python scripts/rag_query.py "query text" [--top-k 12] [--db rag/store/rag.db]
    uv run python scripts/rag_query.py "store cue" --provider github   # semantic search
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import DEFAULT_TOP_K, RAG_DB_PATH
from rag.ingest.embed import (
    EmbeddingProvider,
    GitHubModelsProvider,
    ZeroVectorProvider,
)
from rag.retrieve.query import rag_query

logger = logging.getLogger(__name__)


def make_provider(choice: str | None) -> EmbeddingProvider | None:
    """Build an embedding provider from --provider flag and env vars.

    Returns None when no provider is selected (text-only search).
    """
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
        return GitHubModelsProvider(token=token, model=model, dimensions=dimensions)

    if choice == "zero":
        return ZeroVectorProvider()

    # Auto-detect: use GitHub Models if token is set, otherwise text search
    if token:
        logger.info("Auto-detected GITHUB_MODELS_TOKEN, using GitHub Models provider")
        return GitHubModelsProvider(token=token, model=model, dimensions=dimensions)

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the RAG index")
    parser.add_argument("query", help="Search query text")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help=f"Number of results (default: {DEFAULT_TOP_K})")
    parser.add_argument("--db", default=str(RAG_DB_PATH), help=f"SQLite database path (default: {RAG_DB_PATH})")
    parser.add_argument(
        "--provider",
        choices=["github", "zero"],
        default=None,
        help="Embedding provider (default: auto-detect from env, falls back to text search)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}. Run rag_ingest.py first.", file=sys.stderr)
        sys.exit(1)

    provider = make_provider(args.provider)
    if provider:
        logger.info("Using embedding provider: %s (vector search)", provider.model_name)
    else:
        logger.info("No embedding provider — using text-based keyword search")

    hits = rag_query(args.query, embedding_provider=provider, top_k=args.top_k, db_path=db_path)

    if not hits:
        print("No results found.")
        return

    search_mode = "vector" if provider else "text"
    print(f"\nTop {len(hits)} results for: {args.query!r}  ({search_mode} search)\n")
    for i, hit in enumerate(hits, start=1):
        print(f"  {i}. {hit.path}:{hit.start_line}-{hit.end_line}  [{hit.kind}]  score={hit.score:.3f}")
        # Show first 120 chars of the chunk text
        preview = hit.text[:120].replace("\n", " ").strip()
        print(f"     {preview}...")
        print()


if __name__ == "__main__":
    main()
