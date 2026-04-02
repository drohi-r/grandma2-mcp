"""ML-based unsupervised tool categorization system.

Extracts structural + semantic features from MCP tool definitions,
clusters them via K-Means, and produces a human-readable taxonomy.
"""

from src.categorization.clustering import find_optimal_k, kmeans, silhouette_score
from src.categorization.features import ToolFeatures, extract_tool_features
from src.categorization.labeling import generate_labels
from src.categorization.taxonomy import (
    get_feature_matrix,
    get_tools_by_category,
    load_taxonomy,
    save_taxonomy,
)

__all__ = [
    "ToolFeatures",
    "extract_tool_features",
    "find_optimal_k",
    "generate_labels",
    "get_feature_matrix",
    "get_tools_by_category",
    "kmeans",
    "load_taxonomy",
    "save_taxonomy",
    "silhouette_score",
]
