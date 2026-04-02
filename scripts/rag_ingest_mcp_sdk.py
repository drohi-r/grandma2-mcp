"""Ingest the installed MCP SDK source into the RAG index.

Adds a third repo_ref ("mcp-sdk") alongside "worktree" and "ma2-help-docs".
This lets search_codebase find how @mcp.tool(), Context, types, and
server primitives work without leaving the project.

Usage:
    # Zero-vector (fast, no API key needed):
    python scripts/rag_ingest_mcp_sdk.py

    # Real embeddings (requires GITHUB_MODELS_TOKEN):
    python scripts/rag_ingest_mcp_sdk.py --provider github

The script auto-detects the MCP SDK install path via importlib.
Re-run after upgrading the mcp package to refresh the index.
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.ingest.embed import GitHubModelsProvider, ZeroVectorProvider
from rag.ingest.index import ingest

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_REPO_REF = "mcp-sdk"
_DEFAULT_DB = Path(__file__).parent.parent / "rag" / "store" / "rag.db"


def _find_mcp_sdk_path() -> Path:
    """Return the root directory of the installed mcp package."""
    spec = importlib.util.find_spec("mcp")
    if spec is None or spec.origin is None:
        raise RuntimeError(
            "mcp package not found. Install it: pip install mcp>=1.21.0"
        )
    return Path(spec.origin).parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest MCP SDK source into RAG index")
    parser.add_argument(
        "--provider",
        choices=["github", "zero"],
        default=None,
        help="Embedding provider. Defaults to 'github' if GITHUB_MODELS_TOKEN is set, else 'zero'.",
    )
    parser.add_argument(
        "--db",
        default=str(_DEFAULT_DB),
        help=f"Path to RAG database (default: {_DEFAULT_DB})",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    sdk_path = _find_mcp_sdk_path()
    logger.info("MCP SDK path: %s", sdk_path)

    # Resolve provider
    token = os.getenv("GITHUB_MODELS_TOKEN") or os.getenv("GITHUB_TOKEN")
    provider_name = args.provider or ("github" if token else "zero")

    if provider_name == "github":
        if not token:
            logger.error(
                "No GITHUB_MODELS_TOKEN found. Set it or use --provider zero."
            )
            sys.exit(1)
        provider = GitHubModelsProvider(token=token)
        logger.info("Embedding provider: %s (%d dims)", provider.model_name, provider.dimensions)
    else:
        provider = ZeroVectorProvider()
        logger.info("Embedding provider: zero-vector-stub (no API key needed)")

    result = ingest(
        root_dir=sdk_path,
        repo_ref=_REPO_REF,
        embedding_provider=provider,
        db_path=args.db,
    )

    print(f"\nIngest complete:")
    print(f"  Provider:        {provider.model_name}")
    print(f"  Repo ref:        {_REPO_REF}")
    print(f"  Files processed: {result.files_processed}")
    print(f"  Files skipped:   {result.files_skipped}")
    print(f"  Chunks created:  {result.chunks_created}")


if __name__ == "__main__":
    main()
