"""Load, save, and query the tool taxonomy JSON file.

The taxonomy stores clustering results + per-tool feature vectors so that
``get_similar_tools`` and ``suggest_tool_for_task`` can compute distances
without re-extracting features.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

DEFAULT_TAXONOMY_PATH = Path(__file__).parent / "taxonomy.json"


def save_taxonomy(
    path: str | Path,
    *,
    metadata: dict,
    categories: dict[str, dict],
    tool_features: dict[str, dict],
) -> None:
    """Persist taxonomy to a JSON file.

    Parameters
    ----------
    path : output file path
    metadata : clustering metadata (k, silhouette, provider, etc.)
    categories : ``{label: {id, tool_count, dominant_features, tools}}``
    tool_features : ``{tool_name: {structural, embedding, docstring_summary}}``
    """
    payload = {
        "metadata": {
            **metadata,
            "generated_at": datetime.now(UTC).isoformat(),
        },
        "categories": categories,
        "tool_features": tool_features,
    }
    Path(path).write_text(json.dumps(payload, indent=2))


def load_taxonomy(path: str | Path | None = None) -> dict:
    """Load taxonomy from JSON.  Returns the full dict."""
    if path is None:
        path = DEFAULT_TAXONOMY_PATH
    return json.loads(Path(path).read_text())


def get_tools_by_category(
    taxonomy: dict,
    category_name: str | None = None,
) -> dict[str, list[dict]]:
    """Return tools grouped by category.

    If *category_name* is given, filter to categories whose name contains
    the string (case-insensitive).
    """
    categories = taxonomy.get("categories", {})
    if category_name is None:
        return {name: cat.get("tools", []) for name, cat in categories.items()}

    needle = category_name.lower()
    return {
        name: cat.get("tools", [])
        for name, cat in categories.items()
        if needle in name.lower()
    }


def get_feature_matrix(
    taxonomy: dict,
) -> tuple[list[str], NDArray[np.float64]]:
    """Extract the per-tool combined feature vectors from taxonomy.

    Returns
    -------
    names : tool name list (same order as rows)
    matrix : (n_tools, d) numpy array
    """
    tf = taxonomy.get("tool_features", {})
    names: list[str] = []
    rows: list[list[float]] = []
    for tool_name, feat in tf.items():
        names.append(tool_name)
        structural = feat.get("structural", [])
        embedding = feat.get("embedding", [])
        rows.append(structural + embedding)
    return names, np.array(rows, dtype=np.float64)


def get_embedding_matrix(
    taxonomy: dict,
) -> tuple[list[str], NDArray[np.float64]]:
    """Extract only the embedding vectors from taxonomy.

    Returns
    -------
    names : tool name list
    matrix : (n_tools, d_embed) numpy array
    """
    tf = taxonomy.get("tool_features", {})
    names: list[str] = []
    rows: list[list[float]] = []
    for tool_name, feat in tf.items():
        names.append(tool_name)
        rows.append(feat.get("embedding", []))
    if not rows:
        return names, np.empty((0, 0), dtype=np.float64)
    return names, np.array(rows, dtype=np.float64)


def get_docstring_map(taxonomy: dict) -> dict[str, str]:
    """Return ``{tool_name: docstring_summary}`` from taxonomy."""
    tf = taxonomy.get("tool_features", {})
    return {name: feat.get("docstring_summary", "") for name, feat in tf.items()}
