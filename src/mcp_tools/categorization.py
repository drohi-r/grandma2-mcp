"""MCP tools — categorization. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
import os

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.server import (
    _handle_errors,
    _invalidate_taxonomy_cache,
    mcp,
)

# ============================================================
# Server Startup
# ============================================================


# ============================================================
# Tools 83–86 — ML-Based Tool Categorization
# ============================================================

# Module-level cache for the taxonomy to avoid repeated disk reads.
_taxonomy_cache: dict | None = None


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_tool_categories(category: str | None = None) -> str:
    """
    List auto-discovered tool categories (SAFE_READ).

    Returns the ML-generated taxonomy of all MCP tools grouped by
    functional similarity.  Categories are discovered via unsupervised
    K-Means clustering over hybrid features (structural metadata +
    docstring embeddings).

    Args:
        category: Optional category name filter (case-insensitive partial match).

    Returns:
        str: JSON with categories, tool lists, and clustering metadata.
    """
    taxonomy = _srv._load_taxonomy_cached()
    from src.categorization.taxonomy import get_tools_by_category

    filtered = get_tools_by_category(taxonomy, category)
    return json.dumps(
        {
            "metadata": taxonomy.get("metadata", {}),
            "categories": filtered,
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def recluster_tools(
    provider: str = "zero",
    k: int | None = None,
    alpha: float = 0.4,
) -> str:
    """
    Trigger re-clustering of all MCP tools (SAFE_READ).

    Runs the full ML pipeline: extract features from tool definitions,
    embed docstrings, cluster via K-Means, and regenerate the taxonomy.

    Args:
        provider: Embedding provider — "zero" (fast stub) or "github"
                  (real embeddings, requires GITHUB_MODELS_TOKEN).
        k: Override number of clusters.  None = auto-select via silhouette.
        alpha: Structural feature weight (0–1). Embedding weight = 1 − alpha.

    Returns:
        str: JSON summary with categories, silhouette score, and tool assignments.
    """
    import importlib
    from pathlib import Path

    # Import lazily to avoid circular imports at module load time.
    mod = importlib.import_module("scripts.categorize_tools")
    server_path = str(Path(__file__).resolve())

    result = mod.run(
        provider_name=provider,
        k_override=k,
        alpha=alpha,
        server_path=server_path,
    )
    _invalidate_taxonomy_cache()

    return json.dumps(
        {
            "metadata": result["metadata"],
            "category_count": len(result["categories"]),
            "categories": {
                name: {
                    "tool_count": cat["tool_count"],
                    "tools": [t["name"] for t in cat["tools"]],
                }
                for name, cat in result["categories"].items()
            },
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_similar_tools(tool_name: str, top_n: int = 5) -> str:
    """
    Find the most similar MCP tools to a given tool (SAFE_READ).

    Uses Euclidean distance in the combined feature space (structural +
    embedding) from the last clustering run.

    Args:
        tool_name: Name of the reference tool (e.g. "playback_action").
        top_n: Number of similar tools to return (default 5).

    Returns:
        str: JSON array of similar tools ranked by distance, with category.
    """

    from src.categorization.clustering import euclidean_distance
    from src.categorization.taxonomy import get_feature_matrix

    taxonomy = _srv._load_taxonomy_cached()
    names, matrix = get_feature_matrix(taxonomy)

    if tool_name not in names:
        return json.dumps(
            {"error": f"Tool '{tool_name}' not found in taxonomy. Available: {names[:10]}...", "blocked": True},
            indent=2,
        )

    idx = names.index(tool_name)
    ref_vec = matrix[idx]

    # Compute distances to all other tools
    distances: list[tuple[str, float]] = []
    for i, name in enumerate(names):
        if i == idx:
            continue
        dist = euclidean_distance(ref_vec, matrix[i])
        distances.append((name, dist))

    distances.sort(key=lambda x: x[1])
    top = distances[:top_n]

    # Find categories for each tool
    categories = taxonomy.get("categories", {})
    tool_to_category: dict[str, str] = {}
    for cat_name, cat_data in categories.items():
        for t in cat_data.get("tools", []):
            tool_to_category[t["name"]] = cat_name

    max_dist = top[-1][1] if top else 1.0
    return json.dumps(
        [
            {
                "name": name,
                "similarity": round(1.0 - (dist / max_dist) if max_dist > 0 else 1.0, 4),
                "distance": round(dist, 6),
                "category": tool_to_category.get(name, "unknown"),
            }
            for name, dist in top
        ],
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def suggest_tool_for_task(
    task_description: str,
    top_n: int = 3,
    provider: str = "zero",
    prefer_semantic: bool = True,
) -> str:
    """
    Suggest MCP tools for a natural-language task description (SAFE_READ).

    Embeds the task description and finds the closest tools by cosine
    similarity against stored docstring embeddings.  Falls back to keyword
    matching when using the zero-vector provider or when no embedding token
    is available.

    Args:
        task_description: What you want to accomplish (e.g. "fade out all fixtures").
        top_n: Number of suggestions to return (default 3).
        provider: Embedding provider — "zero" (keyword fallback) or "github".
            Overridden by ``prefer_semantic`` when a token is available.
        prefer_semantic: When True (default), automatically use embedding-based
            search if GITHUB_MODELS_TOKEN is set in the environment.  Falls back
            to keyword matching with a ``warning`` field when no token is present.
            Set to False to force keyword matching regardless of token availability.

    Returns:
        str: JSON array of suggested tools with scores and descriptions.
             Includes a top-level ``warning`` key when semantic search was
             requested but fell back to keyword matching.
    """
    import numpy as np

    from src.categorization.clustering import cosine_similarity
    from src.categorization.taxonomy import get_docstring_map, get_embedding_matrix

    taxonomy = _srv._load_taxonomy_cached()

    # Find category map
    categories = taxonomy.get("categories", {})
    tool_to_category: dict[str, str] = {}
    for cat_name, cat_data in categories.items():
        for t in cat_data.get("tools", []):
            tool_to_category[t["name"]] = cat_name

    docstrings = get_docstring_map(taxonomy)

    # Resolve effective provider: prefer_semantic promotes "zero" → "github"
    # when a token is available; records a warning when it cannot.
    semantic_warning: str | None = None
    effective_provider = provider
    if prefer_semantic and provider == "zero":
        if os.environ.get("GITHUB_MODELS_TOKEN", ""):
            effective_provider = "github"
        else:
            semantic_warning = (
                "prefer_semantic=True but GITHUB_MODELS_TOKEN is not set; "
                "using keyword matching. Set GITHUB_MODELS_TOKEN for semantic search."
            )

    def _keyword_scores() -> list[tuple[str, float]]:
        task_words = set(task_description.lower().split())
        result: list[tuple[str, float]] = []
        for name, doc in docstrings.items():
            tool_words = set(name.replace("_", " ").lower().split()) | set(doc.lower().split())
            overlap = len(task_words & tool_words)
            if overlap > 0:
                result.append((name, float(overlap) / max(len(task_words), 1)))
        result.sort(key=lambda x: -x[1])
        return result

    if effective_provider == "zero":
        scores: list[tuple[str, float]] = _keyword_scores()
    else:
        # Embed task and compare via cosine similarity
        names, emb_matrix = get_embedding_matrix(taxonomy)
        if emb_matrix.size == 0 or np.allclose(emb_matrix, 0.0):
            # Fall back to keyword matching
            scores = _keyword_scores()
            semantic_warning = (
                (semantic_warning or "")
                + " Embedding matrix is empty (zero-vector store); using keyword matching."
            ).strip()
        else:
            from rag.ingest.embed import GitHubModelsProvider

            token = os.environ.get("GITHUB_MODELS_TOKEN", "")
            if not token:
                return json.dumps(
                    {"error": "GITHUB_MODELS_TOKEN not set. Use provider='zero' for keyword matching."},
                    indent=2,
                )
            emb_provider = GitHubModelsProvider(token=token)
            task_vec = np.array(emb_provider.embed_one(task_description), dtype=np.float64)

            scores = []
            for i, name in enumerate(names):
                sim = cosine_similarity(task_vec, emb_matrix[i])
                scores.append((name, sim))
            scores.sort(key=lambda x: -x[1])

    # Only suggest tools this client can actually call (GMA_TOOL_PROFILE).
    visible = set(_srv.mcp._tool_manager._tools)
    scores = [(name, score) for name, score in scores if name in visible]
    top = scores[:top_n]
    result: dict = {
        "suggestions": [
            {
                "name": name,
                "score": round(score, 4),
                "category": tool_to_category.get(name, "unknown"),
                "description": docstrings.get(name, ""),
            }
            for name, score in top
        ]
    }
    if semantic_warning:
        result["warning"] = semantic_warning
    return json.dumps(result, indent=2)
