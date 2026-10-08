"""MCP tools — search. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
import os

from src.auth import OAuthScope, require_scope
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Codebase Search (RAG)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def search_codebase(
    query: str,
    top_k: int = 8,
    kind: str | None = None,
) -> str:
    """Search source code, grandMA2 docs, and MCP SDK source using the RAG index.

    Three indexed knowledge sources (repo_refs):
    - "worktree"     — this server's Python source, tests, and docs
    - "ma2-help-docs" — ~1,043 grandMA2 help pages from help.malighting.com
    - "mcp-sdk"      — installed MCP SDK source (~110 files, types, server, tools)

    Works without any API key (text-search fallback). With GITHUB_MODELS_TOKEN
    set, results are ranked by semantic similarity.

    Args:
        query:  Natural language or keyword query (e.g. "navigate console",
                "store preset", "how to patch fixtures", "mcp tool context")
        top_k:  Number of results to return (default 8, max 20)
        kind:   Optional filter — one of: "source", "test", "doc", "config"

    Returns:
        JSON array of matching chunks with path, kind, lines, score, and text.
        Returns an error JSON if the RAG index has not been built yet.

    Examples:
        - Find command builders:   query="store preset", kind="source"
        - Find grandMA2 docs:      query="how to patch fixtures", kind="doc"
        - Find MCP SDK internals:  query="mcp tool decorator context"
        - Search everything:       query="effects engine"
        - Find test examples:      query="navigate_console", kind="test"
    """
    from pathlib import Path

    from rag.retrieve.query import rag_query

    db = Path(__file__).parent.parent / "rag" / "store" / "rag.db"
    if not db.exists():
        return json.dumps({
            "error": "RAG index not found. Build it first: uv run python scripts/rag_ingest.py",
            "blocked": True,
        }, indent=2)

    provider = None
    token = os.getenv("GITHUB_MODELS_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token:
        from rag.ingest.embed import GitHubModelsProvider
        provider = GitHubModelsProvider(token=token)

    want = min(top_k, 20)
    # When a kind filter is requested, over-fetch 10× so we have enough candidates
    # of the right kind after filtering (the DB has 4 kinds; web docs dominate).
    fetch_k = want * 10 if kind else want
    hits = rag_query(query, embedding_provider=provider, top_k=fetch_k, db_path=db)

    if kind:
        hits = [h for h in hits if h.kind == kind][:want]

    return json.dumps([
        {
            "path": hit.path,
            "kind": hit.kind,
            "lines": f"{hit.start_line}-{hit.end_line}",
            "score": round(hit.score, 4),
            "text": hit.text,
        }
        for hit in hits
    ], indent=2)
