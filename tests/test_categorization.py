"""Tests for the ML-based tool categorization system.

Covers feature extraction, K-Means clustering, silhouette scoring,
label generation, taxonomy I/O, and MCP tool wrappers.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.categorization.clustering import (
    combine_features,
    cosine_similarity,
    drop_zero_variance,
    euclidean_distance,
    find_optimal_k,
    kmeans,
    kmeans_plus_plus,
    normalize_minmax,
    silhouette_samples,
    silhouette_score,
)
from src.categorization.features import (
    ALL_MODULES,
    ACTION_VERBS,
    FUNCTION_MODULES,
    OBJECT_MODULES,
    ToolFeatures,
    extract_tool_features,
)
from src.categorization.labeling import generate_labels
from src.categorization.taxonomy import (
    get_feature_matrix,
    get_tools_by_category,
    load_taxonomy,
    save_taxonomy,
)

# Path to the real server.py
SERVER_PATH = Path(__file__).resolve().parent.parent / "src" / "server.py"


# ===========================================================================
# Feature Extraction Tests
# ===========================================================================


class TestFeatureExtraction:
    """Tests for AST-based feature extraction from server.py."""

    def test_extract_features_finds_tools(self):
        """AST extraction should find MCP tools from server.py."""
        tools = extract_tool_features(str(SERVER_PATH))
        # The project has 78+ tools; we just verify we get a substantial count
        assert len(tools) >= 70, f"Expected ≥70 tools, got {len(tools)}"

    def test_extract_features_names_unique(self):
        tools = extract_tool_features(str(SERVER_PATH))
        names = [t.name for t in tools]
        assert len(names) == len(set(names)), "Tool names must be unique"

    def test_extract_features_detects_destructive(self):
        """Tools with confirm_destructive param should be flagged."""
        tools = extract_tool_features(str(SERVER_PATH))
        destructive_tools = [t for t in tools if t.has_confirm_destructive]
        assert len(destructive_tools) >= 5, (
            f"Expected ≥5 destructive tools, got {len(destructive_tools)}"
        )
        # All destructive-param tools should have DESTRUCTIVE risk tier
        for t in destructive_tools:
            assert t.risk_tier == "DESTRUCTIVE", (
                f"{t.name} has confirm_destructive but risk_tier={t.risk_tier}"
            )

    def test_extract_features_docstrings_not_empty(self):
        tools = extract_tool_features(str(SERVER_PATH))
        for t in tools:
            assert t.docstring, f"Tool {t.name} has empty docstring"

    def test_extract_features_known_tools(self):
        """Spot-check that well-known tools are found."""
        tools = extract_tool_features(str(SERVER_PATH))
        names = {t.name for t in tools}
        for expected in [
            "send_raw_command",
            "set_intensity",
            "playback_action",
            "navigate_console",
            "search_codebase",
            "list_tool_categories",
        ]:
            assert expected in names, f"Missing expected tool: {expected}"

    def test_structural_vector_dimensions(self):
        tools = extract_tool_features(str(SERVER_PATH))
        expected_dim = ToolFeatures.structural_dim()
        for t in tools:
            vec = t.to_structural_vector()
            assert len(vec) == expected_dim, (
                f"{t.name}: vector dim {len(vec)} != expected {expected_dim}"
            )

    def test_structural_vector_values_in_range(self):
        """All binary/one-hot features should be 0 or 1; scalars ≥ 0."""
        tools = extract_tool_features(str(SERVER_PATH))
        for t in tools:
            vec = t.to_structural_vector()
            # First 8 dims are binary/one-hot
            for i in range(8):
                assert vec[i] in (0.0, 1.0), f"{t.name}[{i}]={vec[i]} not binary"
            # Param counts >= 0
            assert vec[8] >= 0
            assert vec[9] >= 0

    def test_safe_read_tools_detected(self):
        tools = extract_tool_features(str(SERVER_PATH))
        safe_read = [t for t in tools if t.risk_tier == "SAFE_READ"]
        assert len(safe_read) >= 3, f"Expected ≥3 SAFE_READ tools, got {len(safe_read)}"


# ===========================================================================
# K-Means Tests
# ===========================================================================


class TestKMeans:
    """Tests for K-Means clustering implementation."""

    def _make_blobs(self, n_per_cluster=30, k=3, d=2, seed=42):
        """Create well-separated Gaussian blobs for testing."""
        rng = np.random.default_rng(seed)
        centers = np.array([[i * 10, i * 10] for i in range(k)], dtype=np.float64)
        if d > 2:
            centers = np.hstack([centers, np.zeros((k, d - 2))])
        X = np.vstack([
            rng.normal(loc=centers[i], scale=0.5, size=(n_per_cluster, d))
            for i in range(k)
        ])
        true_labels = np.repeat(np.arange(k), n_per_cluster)
        return X, true_labels

    def test_kmeans_convergence(self):
        """K-Means should converge on well-separated blobs."""
        X, _ = self._make_blobs(k=3)
        labels, centroids, inertia = kmeans(X, 3)
        assert labels.shape == (90,)
        assert centroids.shape == (3, 2)
        assert inertia >= 0
        # Check that we get 3 distinct clusters
        assert len(np.unique(labels)) == 3

    def test_kmeans_plus_plus_distinct(self):
        """k-means++ should pick k distinct initial centroids."""
        X, _ = self._make_blobs(k=4)
        centroids = kmeans_plus_plus(X, 4, rng=np.random.default_rng(42))
        assert centroids.shape == (4, 2)
        # All centroids should be distinct
        for i in range(4):
            for j in range(i + 1, 4):
                assert not np.allclose(centroids[i], centroids[j]), (
                    f"Centroids {i} and {j} are identical"
                )

    def test_kmeans_single_cluster(self):
        """k=1 should assign all points to cluster 0."""
        X, _ = self._make_blobs(k=1, n_per_cluster=20)
        labels, centroids, _ = kmeans(X, 1)
        assert np.all(labels == 0)
        assert centroids.shape == (1, 2)

    def test_kmeans_k_equals_n(self):
        """When k == n, each point is its own cluster."""
        X = np.array([[0, 0], [10, 10], [20, 20]], dtype=np.float64)
        labels, centroids, inertia = kmeans(X, 3)
        assert len(np.unique(labels)) == 3
        assert inertia < 1e-6  # near-zero inertia

    def test_kmeans_raises_on_k_gt_n(self):
        X = np.array([[0, 0], [1, 1]], dtype=np.float64)
        with pytest.raises(ValueError, match="k=5 exceeds"):
            kmeans(X, 5)


# ===========================================================================
# Silhouette Tests
# ===========================================================================


class TestSilhouette:
    """Tests for silhouette coefficient computation."""

    def test_silhouette_perfect_clusters(self):
        """Well-separated clusters should have silhouette near 1.0."""
        rng = np.random.default_rng(42)
        X = np.vstack([
            rng.normal(loc=[0, 0], scale=0.1, size=(30, 2)),
            rng.normal(loc=[100, 100], scale=0.1, size=(30, 2)),
        ])
        labels = np.array([0] * 30 + [1] * 30, dtype=np.int64)
        score = silhouette_score(X, labels)
        assert score > 0.9, f"Expected >0.9 for perfect clusters, got {score:.4f}"

    def test_silhouette_random_labels(self):
        """Random labels on structured data should have low silhouette."""
        rng = np.random.default_rng(42)
        X = rng.normal(size=(60, 2))
        labels = rng.integers(0, 3, size=60).astype(np.int64)
        score = silhouette_score(X, labels)
        assert -0.5 < score < 0.5, f"Expected near 0 for random labels, got {score:.4f}"

    def test_silhouette_single_cluster(self):
        """Single cluster should return 0."""
        X = np.random.default_rng(42).normal(size=(20, 2))
        labels = np.zeros(20, dtype=np.int64)
        score = silhouette_score(X, labels)
        assert score == 0.0

    def test_silhouette_samples_shape(self):
        X = np.random.default_rng(42).normal(size=(20, 2))
        labels = np.array([0] * 10 + [1] * 10, dtype=np.int64)
        samples = silhouette_samples(X, labels)
        assert samples.shape == (20,)


# ===========================================================================
# Optimal-k Tests
# ===========================================================================


class TestOptimalK:
    def test_find_optimal_k(self):
        """find_optimal_k should return the k with highest silhouette."""
        rng = np.random.default_rng(42)
        # Create 4 well-separated clusters
        X = np.vstack([
            rng.normal(loc=[i * 20, i * 20], scale=0.5, size=(20, 2))
            for i in range(4)
        ])
        best_k, scores = find_optimal_k(X, k_range=range(2, 7))
        assert best_k in scores
        assert scores[best_k] == max(scores.values())
        # With well-separated clusters, optimal k should be 4
        assert best_k == 4, f"Expected k=4, got k={best_k}"

    def test_find_optimal_k_returns_all_scores(self):
        X = np.random.default_rng(42).normal(size=(30, 2))
        _, scores = find_optimal_k(X, k_range=range(2, 6))
        assert set(scores.keys()) == {2, 3, 4, 5}


# ===========================================================================
# Feature Combination Tests
# ===========================================================================


class TestFeatureCombination:
    def test_normalize_minmax(self):
        X = np.array([[1, 10], [5, 50], [3, 30]], dtype=np.float64)
        normed = normalize_minmax(X)
        assert normed.min() == 0.0
        assert normed.max() == 1.0

    def test_normalize_constant_column(self):
        """Constant columns should not cause division by zero."""
        X = np.array([[5, 1], [5, 2], [5, 3]], dtype=np.float64)
        normed = normalize_minmax(X)
        assert not np.any(np.isnan(normed))
        # Constant column maps to 0
        assert np.allclose(normed[:, 0], 0.0)

    def test_combine_features_zero_embeddings(self):
        """With zero embeddings, should return structural only."""
        structural = np.ones((5, 10), dtype=np.float64)
        embeddings = np.zeros((5, 384), dtype=np.float64)
        combined = combine_features(structural, embeddings, alpha=0.4)
        # Should drop embeddings and return structural
        assert combined.shape == (5, 10)

    def test_combine_features_with_embeddings(self):
        structural = np.ones((5, 10), dtype=np.float64)
        embeddings = np.ones((5, 384), dtype=np.float64)
        combined = combine_features(structural, embeddings, alpha=0.4)
        assert combined.shape == (5, 10 + 384)

    def test_cosine_similarity_identical(self):
        a = np.array([1.0, 2.0, 3.0])
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_euclidean_distance(self):
        a = np.array([0.0, 0.0])
        b = np.array([3.0, 4.0])
        assert euclidean_distance(a, b) == pytest.approx(5.0)


# ===========================================================================
# Label Generation Tests
# ===========================================================================


class TestLabeling:
    def test_generate_labels_unique(self):
        """All generated labels should be unique strings."""
        tools = [
            ToolFeatures(name=f"tool_{i}", action_verbs=["list"], risk_tier="SAFE_READ")
            for i in range(10)
        ]
        labels = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 2], dtype=np.int64)
        result = generate_labels(tools, labels)
        assert len(result) == 3
        assert len(set(result.values())) == 3, "Labels should be unique"

    def test_generate_labels_playback(self):
        tools = [
            ToolFeatures(name="go", action_verbs=["go", "goto"], command_modules=["playback"]),
            ToolFeatures(name="go_back", action_verbs=["go"], command_modules=["playback"]),
        ]
        labels = np.array([0, 0], dtype=np.int64)
        result = generate_labels(tools, labels)
        assert "Playback" in result[0]

    def test_generate_labels_empty_cluster(self):
        tools = [ToolFeatures(name="t1", action_verbs=["list"])]
        labels = np.array([0], dtype=np.int64)
        result = generate_labels(tools, labels)
        assert 0 in result

    def test_generate_labels_disambiguation(self):
        """When two clusters have the same dominant label, they get disambiguated."""
        tools = [
            ToolFeatures(name="list_a", action_verbs=["list", "info"], risk_tier="SAFE_READ"),
            ToolFeatures(name="list_b", action_verbs=["list", "info"], risk_tier="SAFE_READ"),
            ToolFeatures(name="list_c", action_verbs=["list", "info"], risk_tier="SAFE_READ", command_modules=["info"]),
            ToolFeatures(name="list_d", action_verbs=["list", "info"], risk_tier="SAFE_READ", command_modules=["variables"]),
        ]
        labels = np.array([0, 0, 1, 1], dtype=np.int64)
        result = generate_labels(tools, labels)
        assert len(set(result.values())) == 2, "Disambiguated labels should be unique"


# ===========================================================================
# Taxonomy I/O Tests
# ===========================================================================


class TestTaxonomy:
    def _sample_taxonomy(self) -> dict:
        return {
            "metadata": {
                "tool_count": 3,
                "k": 2,
                "silhouette_score": 0.5,
                "embedding_provider": "zero",
            },
            "categories": {
                "Playback": {
                    "id": 0,
                    "tool_count": 2,
                    "dominant_features": ["go"],
                    "tools": [
                        {"name": "playback_action", "confidence": 0.9},
                        {"name": "execute_sequence", "confidence": 0.8},
                    ],
                },
                "Queries": {
                    "id": 1,
                    "tool_count": 1,
                    "dominant_features": ["list"],
                    "tools": [{"name": "list_shows", "confidence": 1.0}],
                },
            },
            "tool_features": {
                "playback_action": {
                    "structural": [1.0, 0.0, 0.0],
                    "embedding": [0.1, 0.2],
                    "docstring_summary": "Execute playback",
                },
                "execute_sequence": {
                    "structural": [0.8, 0.1, 0.0],
                    "embedding": [0.1, 0.3],
                    "docstring_summary": "Execute sequence",
                },
                "list_shows": {
                    "structural": [0.0, 1.0, 0.0],
                    "embedding": [0.5, 0.0],
                    "docstring_summary": "List shows",
                },
            },
        }

    def test_taxonomy_roundtrip(self):
        """save → load should produce equivalent structure."""
        orig = self._sample_taxonomy()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        save_taxonomy(
            path,
            metadata=orig["metadata"],
            categories=orig["categories"],
            tool_features=orig["tool_features"],
        )
        loaded = load_taxonomy(path)

        assert loaded["metadata"]["tool_count"] == 3
        assert loaded["metadata"]["k"] == 2
        assert "Playback" in loaded["categories"]
        assert "Queries" in loaded["categories"]
        assert "generated_at" in loaded["metadata"]

    def test_taxonomy_schema(self):
        """Output JSON should have required top-level keys."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        save_taxonomy(
            path,
            metadata={"tool_count": 1, "k": 1},
            categories={"Cat1": {"id": 0, "tool_count": 1, "tools": []}},
            tool_features={"tool1": {"structural": [0.0], "embedding": [], "docstring_summary": ""}},
        )
        loaded = load_taxonomy(path)
        assert "metadata" in loaded
        assert "categories" in loaded
        assert "tool_features" in loaded

    def test_get_tools_by_category_all(self):
        taxonomy = self._sample_taxonomy()
        result = get_tools_by_category(taxonomy)
        assert len(result) == 2
        assert "Playback" in result
        assert "Queries" in result

    def test_get_tools_by_category_filter(self):
        taxonomy = self._sample_taxonomy()
        result = get_tools_by_category(taxonomy, "play")
        assert len(result) == 1
        assert "Playback" in result

    def test_get_tools_by_category_no_match(self):
        taxonomy = self._sample_taxonomy()
        result = get_tools_by_category(taxonomy, "nonexistent")
        assert len(result) == 0

    def test_get_feature_matrix(self):
        taxonomy = self._sample_taxonomy()
        names, matrix = get_feature_matrix(taxonomy)
        assert len(names) == 3
        assert matrix.shape[0] == 3
        # structural (3) + embedding (2) = 5 dims
        assert matrix.shape[1] == 5


# ===========================================================================
# End-to-End Pipeline Test
# ===========================================================================


class TestFullPipeline:
    def test_full_pipeline_zero_vector(self):
        """End-to-end: extract → embed(zero) → cluster → taxonomy."""
        # Extract features
        tools = extract_tool_features(str(SERVER_PATH))
        assert len(tools) >= 70

        # Build structural matrix
        structural = np.array([t.to_structural_vector() for t in tools], dtype=np.float64)
        structural_norm = normalize_minmax(structural)

        # Zero-vector embeddings
        n = len(tools)
        dim = 384
        embeddings = np.zeros((n, dim), dtype=np.float64)

        # Combine (should drop zero embeddings)
        combined = combine_features(structural_norm, embeddings, alpha=0.4)
        assert combined.shape[0] == n

        # Cluster
        best_k, scores = find_optimal_k(combined, k_range=range(3, 10))
        assert best_k >= 3
        labels, centroids, inertia = kmeans(combined, best_k)
        assert len(np.unique(labels)) == best_k

        # Labels
        cluster_labels = generate_labels(tools, labels)
        assert len(cluster_labels) == best_k
        assert len(set(cluster_labels.values())) == best_k  # unique

        # Taxonomy roundtrip
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        categories: dict[str, dict] = {}
        for cid, label in cluster_labels.items():
            cluster_tools = [t for t, lbl in zip(tools, labels, strict=False) if int(lbl) == cid]
            categories[label] = {
                "id": cid,
                "tool_count": len(cluster_tools),
                "dominant_features": [],
                "tools": [{"name": t.name, "confidence": 1.0} for t in cluster_tools],
            }

        tool_features_dict = {
            t.name: {
                "structural": structural_norm[i].tolist(),
                "embedding": embeddings[i].tolist(),
                "docstring_summary": t.docstring.split("\n")[0][:100],
            }
            for i, t in enumerate(tools)
        }

        save_taxonomy(
            path,
            metadata={"tool_count": n, "k": best_k, "silhouette_score": silhouette_score(combined, labels)},
            categories=categories,
            tool_features=tool_features_dict,
        )

        loaded = load_taxonomy(path)
        assert loaded["metadata"]["tool_count"] == n
        assert len(loaded["categories"]) == best_k
        assert len(loaded["tool_features"]) == n

        # Verify every tool appears in exactly one category
        all_tools_in_cats = set()
        for cat in loaded["categories"].values():
            for t in cat["tools"]:
                assert t["name"] not in all_tools_in_cats, f"Duplicate: {t['name']}"
                all_tools_in_cats.add(t["name"])
        assert all_tools_in_cats == {t.name for t in tools}


# ===========================================================================
# Module Auto-Discovery Tests
# ===========================================================================


class TestModuleAutoDiscovery:
    """Verify auto-discovery picks up all command submodules."""

    def test_matricks_in_function_modules(self):
        """matricks.py exists in src/commands/functions/ and should be discovered."""
        assert "matricks" in FUNCTION_MODULES

    def test_all_known_function_modules_present(self):
        """All expected function modules should be auto-discovered."""
        expected = {
            "assignment", "call", "edit", "helping", "importexport",
            "info", "labeling", "macro", "matricks", "navigation",
            "park", "playback", "selection", "store", "values", "variables",
        }
        assert expected.issubset(set(FUNCTION_MODULES))

    def test_all_known_object_modules_present(self):
        expected = {
            "attributes", "cues", "dmx", "executors", "fixtures",
            "groups", "layouts", "presets", "time",
        }
        assert expected == set(OBJECT_MODULES)

    def test_structural_dim_matches_modules(self):
        """structural_dim must equal 3 + 5 + 2 + len(ALL_MODULES) + len(ACTION_VERBS)."""
        expected = 3 + 5 + 2 + len(ALL_MODULES) + len(ACTION_VERBS)
        assert ToolFeatures.structural_dim() == expected

    def test_no_init_in_modules(self):
        """__init__.py should not appear in discovered modules."""
        assert "__init__" not in FUNCTION_MODULES
        assert "__init__" not in OBJECT_MODULES


# ===========================================================================
# MCP Tool Wrapper Tests
# ===========================================================================


class TestMCPToolWrappers:
    """Tests for the 4 categorization MCP tools in server.py."""

    @pytest.fixture(autouse=True)
    def _generate_taxonomy(self, tmp_path, monkeypatch):
        """Generate a taxonomy.json in a temp dir for all tests."""
        import sys

        _ROOT = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(_ROOT))

        from scripts.categorize_tools import run
        from src.categorization import taxonomy as tax_mod

        out_path = tmp_path / "taxonomy.json"
        run(provider_name="zero", output=str(out_path), server_path=str(SERVER_PATH))

        # Monkeypatch taxonomy module to use our temp file
        monkeypatch.setattr(tax_mod, "DEFAULT_TAXONOMY_PATH", out_path)

        # Also reset server module cache
        import src.server as server_mod
        monkeypatch.setattr(server_mod, "_taxonomy_cache", None)

        self.taxonomy_path = out_path
        self.taxonomy = tax_mod.load_taxonomy(out_path)

    def test_taxonomy_generated(self):
        """Pipeline should generate a valid taxonomy file."""
        assert self.taxonomy_path.exists()
        assert "metadata" in self.taxonomy
        assert "categories" in self.taxonomy
        assert "tool_features" in self.taxonomy
        assert self.taxonomy["metadata"]["tool_count"] >= 70

    def test_confidence_no_zero(self):
        """No tool should have confidence exactly 0.0 (silhouette-based)."""
        for cat_name, cat in self.taxonomy["categories"].items():
            for t in cat["tools"]:
                # Silhouette maps to [0, 1]; only a perfectly misclassified
                # tool would get 0.0, which shouldn't happen on real data.
                assert t["confidence"] > 0.0, (
                    f"Tool {t['name']} in {cat_name} has confidence 0.0"
                )

    def test_confidence_range(self):
        """All confidence values should be in [0, 1]."""
        for cat in self.taxonomy["categories"].values():
            for t in cat["tools"]:
                assert 0.0 <= t["confidence"] <= 1.0, (
                    f"Tool {t['name']} confidence {t['confidence']} out of range"
                )

    @pytest.mark.asyncio
    async def test_get_similar_tools_returns_results(self):
        """get_similar_tools should return ranked results."""
        import json

        import src.server as server_mod

        # Use a known tool name from the taxonomy
        first_tool = list(self.taxonomy["tool_features"].keys())[0]
        raw = await server_mod.get_similar_tools.__wrapped__(first_tool, top_n=3)
        result = json.loads(raw)
        assert isinstance(result, list)
        assert len(result) <= 3
        # Check similarity is in descending order
        sims = [r["similarity"] for r in result]
        assert sims == sorted(sims, reverse=True)

    @pytest.mark.asyncio
    async def test_get_similar_tools_unknown_tool(self):
        """get_similar_tools should return error for unknown tools."""
        import json

        import src.server as server_mod

        raw = await server_mod.get_similar_tools.__wrapped__("totally_fake_tool_xyz", top_n=3)
        result = json.loads(raw)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_suggest_tool_keyword_fallback(self):
        """suggest_tool_for_task with zero provider should use keyword matching."""
        import json

        import src.server as server_mod

        raw = await server_mod.suggest_tool_for_task.__wrapped__(
            "list all fixtures", top_n=3, provider="zero"
        )
        result = json.loads(raw)
        # With zero-vector provider, returns {"suggestions": [...], "warning": "..."}
        # With real embeddings, returns a bare list — handle both.
        suggestions = result if isinstance(result, list) else result.get("suggestions", [])
        assert len(suggestions) <= 3
        assert len(suggestions) > 0

    def test_alpha_validation(self):
        """Alpha out of [0, 1] should raise ValueError."""
        from scripts.categorize_tools import run

        with pytest.raises(ValueError, match="alpha must be in"):
            run(provider_name="zero", alpha=-0.5, server_path=str(SERVER_PATH))
        with pytest.raises(ValueError, match="alpha must be in"):
            run(provider_name="zero", alpha=1.5, server_path=str(SERVER_PATH))


# ===========================================================================
# Audit Tests — clustering quality, stability, and correctness
# ===========================================================================


class TestClusteringAudit:
    """Audit tests verifying clustering quality and robustness."""

    def _run_pipeline(self, seed=42, k_override=None):
        """Run the full pipeline and return (tools, combined, labels, sil)."""
        tools = extract_tool_features(str(SERVER_PATH))
        structural = np.array(
            [t.to_structural_vector() for t in tools], dtype=np.float64,
        )
        structural, _ = drop_zero_variance(structural)
        structural_norm = normalize_minmax(structural)
        embeddings = np.zeros((len(tools), 384), dtype=np.float64)
        combined = combine_features(structural_norm, embeddings, alpha=0.4)

        if k_override:
            labels, _, _ = kmeans(combined, k_override, seed=seed)
        else:
            best_k, _ = find_optimal_k(combined, seed=seed)
            labels, _, _ = kmeans(combined, best_k, seed=seed)

        sil = silhouette_score(combined, labels)
        return tools, combined, labels, sil

    def test_silhouette_above_random(self):
        """Global silhouette should be meaningfully above zero (random baseline)."""
        _, _, _, sil = self._run_pipeline()
        assert sil > 0.05, (
            f"Silhouette {sil:.4f} is near-random; clustering is not meaningful"
        )

    def test_no_mega_cluster(self):
        """No single cluster should contain >50% of all tools."""
        tools, _, labels, _ = self._run_pipeline()
        n = len(tools)
        unique, counts = np.unique(labels, return_counts=True)
        for cid, count in zip(unique, counts):
            assert count <= n * 0.5, (
                f"Cluster {cid} has {count}/{n} tools (>{50}%) — mega-cluster"
            )

    def test_few_small_clusters(self):
        """At most 1 cluster may have fewer than 3 tools (outlier tolerance)."""
        _, _, labels, _ = self._run_pipeline()
        unique, counts = np.unique(labels, return_counts=True)
        small = sum(1 for c in counts if c < 3)
        assert small <= 1, (
            f"{small} clusters have <3 tools — too many near-empty clusters"
        )

    def test_multi_restart_stability(self):
        """Multiple restarts should improve or match single-restart inertia."""
        tools = extract_tool_features(str(SERVER_PATH))
        structural = np.array(
            [t.to_structural_vector() for t in tools], dtype=np.float64,
        )
        structural, _ = drop_zero_variance(structural)
        structural_norm = normalize_minmax(structural)
        embeddings = np.zeros((len(tools), 384), dtype=np.float64)
        combined = combine_features(structural_norm, embeddings, alpha=0.4)

        _, _, inertia_multi = kmeans(combined, 5, seed=42, n_init=10)
        _, _, inertia_single = kmeans(combined, 5, seed=42, n_init=1)

        assert inertia_multi <= inertia_single + 1e-6, (
            f"Multi-restart inertia ({inertia_multi:.4f}) should be <= "
            f"single-restart ({inertia_single:.4f})"
        )

    def test_destructive_tools_mostly_not_in_read_cluster(self):
        """Most DESTRUCTIVE tools should not be in read-only categories.

        Unsupervised clustering may place a few DESTRUCTIVE tools in
        read-oriented clusters when they share structural features.
        We tolerate up to 20% misassignment.
        """
        tools, _, labels, _ = self._run_pipeline()
        cluster_labels = generate_labels(tools, labels)

        destructive = [(t, int(lbl)) for t, lbl in zip(tools, labels)
                       if t.risk_tier == "DESTRUCTIVE"]
        misassigned = [
            t.name for t, cid in destructive
            if cluster_labels[cid] == "Inspection & Queries"
        ]
        ratio = len(misassigned) / len(destructive) if destructive else 0.0
        assert ratio <= 0.2, (
            f"{len(misassigned)}/{len(destructive)} ({ratio:.0%}) DESTRUCTIVE tools "
            f"in read-only clusters: {misassigned}"
        )

    def test_verb_detection_no_false_matches(self):
        """Verb detection should not match substrings like 'unclear' → 'clear'."""
        from src.categorization.features import _detect_action_verbs

        # "unclear" should NOT match "clear"
        verbs = _detect_action_verbs("This is unclear behavior", "pass")
        assert "clear" not in verbs, "'unclear' false-matched as 'clear'"

        # "information" should NOT match "info"
        verbs = _detect_action_verbs("Provide information about", "pass")
        assert "info" not in verbs, "'information' false-matched as 'info'"

        # Actual verb usage should still match
        verbs = _detect_action_verbs("Clear the programmer", "clear()")
        assert "clear" in verbs, "'clear' should match when used as a word"

    def test_per_sample_silhouette_no_extreme_negatives(self):
        """No tool should have silhouette < -0.5 (severely misassigned)."""
        _, combined, labels, _ = self._run_pipeline()
        samples = silhouette_samples(combined, labels)
        worst = float(samples.min())
        assert worst > -0.5, (
            f"Worst per-sample silhouette is {worst:.4f} — severely misassigned tool"
        )

    def test_label_uniqueness_in_pipeline(self):
        """All category labels in a real pipeline run should be unique."""
        tools, _, labels, _ = self._run_pipeline()
        cluster_labels = generate_labels(tools, labels)
        label_values = list(cluster_labels.values())
        assert len(label_values) == len(set(label_values)), (
            f"Duplicate labels: {label_values}"
        )

    def test_verb_normalization(self):
        """Verb sub-vector should be L2-normalised (unit norm when verbs present)."""
        t = ToolFeatures(
            name="test_tool",
            action_verbs=["list", "info", "store", "delete"],
        )
        vec = t.to_structural_vector()
        dim = ToolFeatures.structural_dim()
        # Verb dims are the last len(ACTION_VERBS) entries
        verb_start = dim - len(ACTION_VERBS)
        verb_vec = np.array(vec[verb_start:])
        l2_norm = float(np.linalg.norm(verb_vec))
        assert l2_norm == pytest.approx(1.0, abs=1e-6), (
            f"Verb sub-vector L2 norm should be 1.0, got {l2_norm}"
        )

    def test_verb_normalization_no_verbs(self):
        """Tools with no verbs should have zero verb sub-vector."""
        t = ToolFeatures(name="test_tool", action_verbs=[])
        vec = t.to_structural_vector()
        dim = ToolFeatures.structural_dim()
        verb_start = dim - len(ACTION_VERBS)
        verb_vec = vec[verb_start:]
        assert all(v == 0.0 for v in verb_vec)

    def test_zero_variance_columns_dropped(self):
        """drop_zero_variance should remove constant columns."""
        X = np.array([
            [1, 5, 0, 3],
            [2, 5, 0, 4],
            [3, 5, 0, 5],
        ], dtype=np.float64)
        filtered, mask = drop_zero_variance(X)
        # Columns 1 and 2 are constant → dropped
        assert filtered.shape == (3, 2), f"Expected (3, 2), got {filtered.shape}"
        assert mask.tolist() == [True, False, False, True]
        np.testing.assert_array_equal(filtered[:, 0], [1, 2, 3])
        np.testing.assert_array_equal(filtered[:, 1], [3, 4, 5])

    def test_zero_variance_on_real_features(self):
        """Real tool features should have some zero-variance dims to drop."""
        tools = extract_tool_features(str(SERVER_PATH))
        structural = np.array(
            [t.to_structural_vector() for t in tools], dtype=np.float64,
        )
        filtered, mask = drop_zero_variance(structural)
        dropped = structural.shape[1] - filtered.shape[1]
        assert dropped >= 5, (
            f"Expected ≥5 zero-variance dims dropped, only dropped {dropped}"
        )
        assert filtered.shape[1] < structural.shape[1]
