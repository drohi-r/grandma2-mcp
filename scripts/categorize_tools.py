#!/usr/bin/env python3
"""CLI: extract features from MCP tools, embed, cluster, and write taxonomy.

Usage:
    uv run python scripts/categorize_tools.py                        # zero-vector (fast, no API)
    uv run python scripts/categorize_tools.py --provider github      # real embeddings
    uv run python scripts/categorize_tools.py --k 7                  # override k
    uv run python scripts/categorize_tools.py --alpha 0.3            # structural weight
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

# Ensure project root is on sys.path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.categorization.clustering import (
    combine_features,
    find_optimal_k,
    kmeans,
    normalize_minmax,
    silhouette_score,
)
from src.categorization.features import ToolFeatures, extract_tool_features
from src.categorization.labeling import dominant_features, generate_labels
from src.categorization.taxonomy import DEFAULT_TAXONOMY_PATH, save_taxonomy


def _get_provider(name: str):
    """Instantiate the requested embedding provider."""
    from rag.ingest.embed import GitHubModelsProvider, ZeroVectorProvider

    if name == "zero":
        return ZeroVectorProvider(dimensions=384)
    if name == "github":
        token = os.environ.get("GITHUB_MODELS_TOKEN", "")
        if not token:
            print("ERROR: GITHUB_MODELS_TOKEN not set. Use --provider zero for testing.", file=sys.stderr)
            sys.exit(1)
        return GitHubModelsProvider(token=token)
    raise ValueError(f"Unknown provider: {name!r}")


def run(
    *,
    provider_name: str = "zero",
    output: str | None = None,
    k_override: int | None = None,
    alpha: float = 0.4,
    server_path: str | None = None,
) -> dict:
    """Execute the full categorization pipeline and return the taxonomy dict."""
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")

    server_file = Path(server_path) if server_path else _ROOT / "src" / "server.py"
    out_path = Path(output) if output else DEFAULT_TAXONOMY_PATH

    # --- Step 1: Extract features ---
    print(f"[1/6] Extracting features from {server_file.name} ...")
    tools = extract_tool_features(str(server_file))
    print(f"       Found {len(tools)} tools")

    # --- Step 2: Build structural matrix ---
    print("[2/6] Building structural feature matrix ...")
    structural = np.array([t.to_structural_vector() for t in tools], dtype=np.float64)
    structural_norm = normalize_minmax(structural)

    # --- Step 3: Embed docstrings ---
    print(f"[3/6] Embedding docstrings (provider={provider_name}) ...")
    provider = _get_provider(provider_name)
    docstrings = [t.docstring[:2000] for t in tools]  # trim long docs
    embeddings = np.array(provider.embed_many(docstrings), dtype=np.float64)

    # --- Step 4: Combine & cluster ---
    print("[4/6] Combining features and clustering ...")
    combined = combine_features(structural_norm, embeddings, alpha=alpha)

    if k_override is not None:
        labels, centroids, inertia = kmeans(combined, k_override)
        sil = silhouette_score(combined, labels)
        best_k = k_override
        all_scores = {k_override: sil}
        print(f"       k={best_k} (override), silhouette={sil:.4f}")
    else:
        best_k, all_scores = find_optimal_k(combined)
        labels, centroids, inertia = kmeans(combined, best_k)
        sil = silhouette_score(combined, labels)
        print(f"       Optimal k={best_k}, silhouette={sil:.4f}")
        print(f"       All scores: {json.dumps({k: round(s, 4) for k, s in sorted(all_scores.items())})}")

    # --- Step 5: Generate labels ---
    print("[5/6] Generating category labels ...")
    cluster_labels = generate_labels(tools, labels)

    # --- Step 6: Build & save taxonomy ---
    print(f"[6/6] Saving taxonomy to {out_path} ...")

    metadata = {
        "tool_count": len(tools),
        "k": best_k,
        "silhouette_score": round(sil, 6),
        "inertia": round(inertia, 4),
        "embedding_provider": provider_name,
        "embedding_dimensions": provider.dimensions,
        "feature_weights": {"structural": alpha, "embedding": 1 - alpha},
        "k_scores": {str(k): round(s, 6) for k, s in sorted(all_scores.items())},
    }

    # Build categories dict
    categories: dict[str, dict] = {}
    for cid, label in sorted(cluster_labels.items()):
        cluster_tools = [
            (t, i) for i, (t, l) in enumerate(zip(tools, labels)) if int(l) == cid
        ]
        # Confidence = 1 - (distance to centroid / max distance in cluster)
        cluster_indices = [i for _, i in cluster_tools]
        cluster_vecs = combined[cluster_indices]
        centroid = centroids[cid]
        dists = np.sqrt(np.sum((cluster_vecs - centroid) ** 2, axis=1))
        max_dist = dists.max() if dists.max() > 0 else 1.0

        dom = dominant_features([t for t, _ in cluster_tools])
        categories[label] = {
            "id": cid,
            "tool_count": len(cluster_tools),
            "dominant_features": dom["verbs"][:3] + dom["modules"][:3],
            "tools": [
                {
                    "name": t.name,
                    "confidence": max(1e-4, round(float(1.0 - d / max_dist), 4)) if max_dist > 0 else 1.0,
                }
                for (t, _), d in zip(cluster_tools, dists)
            ],
        }

    # Build tool_features dict
    tool_features_dict: dict[str, dict] = {}
    for i, t in enumerate(tools):
        tool_features_dict[t.name] = {
            "structural": [round(v, 6) for v in structural_norm[i].tolist()],
            "embedding": [round(v, 6) for v in embeddings[i].tolist()],
            "docstring_summary": t.docstring.split("\n")[0][:200] if t.docstring else "",
        }

    save_taxonomy(
        out_path,
        metadata=metadata,
        categories=categories,
        tool_features=tool_features_dict,
    )

    # Print summary
    print("\n" + "=" * 60)
    print(f"  Tool Categorization -- {len(tools)} tools -> {best_k} categories")
    print(f"  Silhouette score: {sil:.4f}")
    print(f"  Provider: {provider_name}")
    print("=" * 60)
    for label, cat in sorted(categories.items(), key=lambda x: x[1]["id"]):
        tool_names = [t["name"] for t in cat["tools"]]
        print(f"\n  [{cat['id']}] {label} ({cat['tool_count']} tools)")
        for tn in tool_names:
            print(f"      - {tn}")
    print()

    return {"metadata": metadata, "categories": categories, "tool_features": tool_features_dict}


def main() -> None:
    parser = argparse.ArgumentParser(description="Categorize MCP tools via unsupervised clustering")
    parser.add_argument("--provider", choices=["github", "zero"], default="zero", help="Embedding provider")
    parser.add_argument("--output", type=str, default=None, help="Output taxonomy JSON path")
    parser.add_argument("--k", type=int, default=None, help="Override number of clusters")
    parser.add_argument("--alpha", type=float, default=0.4, help="Structural feature weight (0-1)")
    parser.add_argument("--server", type=str, default=None, help="Path to server.py")
    args = parser.parse_args()

    run(
        provider_name=args.provider,
        output=args.output,
        k_override=args.k,
        alpha=args.alpha,
        server_path=args.server,
    )


if __name__ == "__main__":
    main()
