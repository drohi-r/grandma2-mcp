"""K-Means clustering and silhouette scoring — pure numpy, no scikit-learn.

Implements:
- k-means++ initialisation
- Lloyd's K-Means algorithm
- Silhouette coefficient (per-sample and mean)
- Optimal-k search over a range
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# K-Means
# ---------------------------------------------------------------------------


def kmeans_plus_plus(
    X: NDArray[np.float64],
    k: int,
    rng: np.random.Generator | None = None,
) -> NDArray[np.float64]:
    """Select *k* initial centroids using k-means++ seeding.

    Parameters
    ----------
    X : (n, d) array
    k : number of clusters
    rng : optional random generator for reproducibility
    """
    if rng is None:
        rng = np.random.default_rng()
    n = X.shape[0]
    centroids = np.empty((k, X.shape[1]), dtype=X.dtype)

    # First centroid: random sample
    idx = rng.integers(n)
    centroids[0] = X[idx]

    for c in range(1, k):
        # Squared distances to nearest existing centroid
        dists = np.min(
            np.sum((X[:, np.newaxis, :] - centroids[np.newaxis, :c, :]) ** 2, axis=2),
            axis=1,
        )
        # Probability proportional to D²
        probs = dists / dists.sum()
        idx = rng.choice(n, p=probs)
        centroids[c] = X[idx]

    return centroids


def _kmeans_single(
    X: NDArray[np.float64],
    k: int,
    *,
    max_iter: int = 300,
    tol: float = 1e-4,
    rng: np.random.Generator,
) -> tuple[NDArray[np.int64], NDArray[np.float64], float]:
    """Single run of Lloyd's K-Means algorithm (internal)."""
    n, d = X.shape
    centroids = kmeans_plus_plus(X, k, rng)
    labels = np.zeros(n, dtype=np.int64)

    for _ in range(max_iter):
        # Assignment step
        dists = _pairwise_sq_dist(X, centroids)  # (n, k)
        new_labels = np.argmin(dists, axis=1)

        # Update step
        new_centroids = np.empty_like(centroids)
        for c in range(k):
            members = X[new_labels == c]
            if len(members) == 0:
                # Re-seed empty cluster
                new_centroids[c] = X[rng.integers(n)]
            else:
                new_centroids[c] = members.mean(axis=0)

        # Convergence check
        shift = np.sqrt(np.sum((new_centroids - centroids) ** 2, axis=1)).max()
        centroids = new_centroids
        labels = new_labels
        if shift < tol:
            break

    inertia = float(np.sum(np.min(_pairwise_sq_dist(X, centroids), axis=1)))
    return labels, centroids, inertia


def kmeans(
    X: NDArray[np.float64],
    k: int,
    *,
    max_iter: int = 300,
    tol: float = 1e-4,
    seed: int | None = 42,
    n_init: int = 10,
) -> tuple[NDArray[np.int64], NDArray[np.float64], float]:
    """Run K-Means clustering with multiple restarts.

    Runs *n_init* independent initialisations and returns the result with
    the lowest inertia (sum of squared distances to assigned centroid).

    Parameters
    ----------
    n_init : number of independent runs (default 10).  Higher values
        reduce sensitivity to random initialisation at the cost of runtime.

    Returns
    -------
    labels : (n,) cluster assignments
    centroids : (k, d) final centroids
    inertia : sum of squared distances to assigned centroid
    """
    X = np.asarray(X, dtype=np.float64)
    n, d = X.shape

    if k > n:
        raise ValueError(f"k={k} exceeds sample count n={n}")

    best_labels: NDArray[np.int64] | None = None
    best_centroids: NDArray[np.float64] | None = None
    best_inertia = np.inf

    base_rng = np.random.default_rng(seed)
    for _ in range(n_init):
        # Derive a child RNG for each restart so results are deterministic
        child_rng = np.random.default_rng(base_rng.integers(0, 2**63))
        labels, centroids, inertia = _kmeans_single(
            X, k, max_iter=max_iter, tol=tol, rng=child_rng,
        )
        if inertia < best_inertia:
            best_labels = labels
            best_centroids = centroids
            best_inertia = inertia

    assert best_labels is not None  # at least one run completed
    return best_labels, best_centroids, best_inertia  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Silhouette
# ---------------------------------------------------------------------------


def silhouette_samples(
    X: NDArray[np.float64],
    labels: NDArray[np.int64],
) -> NDArray[np.float64]:
    """Compute per-sample silhouette coefficients.

    Parameters
    ----------
    X : (n, d) feature matrix
    labels : (n,) cluster labels

    Returns
    -------
    (n,) silhouette values in [-1, 1].
    """
    X = np.asarray(X, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    n = X.shape[0]
    unique_labels = np.unique(labels)
    k = len(unique_labels)

    if k <= 1 or k >= n:
        return np.zeros(n, dtype=np.float64)

    # Full pairwise distance matrix
    dist_matrix = _pairwise_dist_full(X)

    sil = np.zeros(n, dtype=np.float64)
    for i in range(n):
        own_label = labels[i]
        own_mask = labels == own_label
        own_count = own_mask.sum()

        # a(i) = mean intra-cluster distance
        if own_count > 1:
            a_i = dist_matrix[i, own_mask].sum() / (own_count - 1)
        else:
            a_i = 0.0

        # b(i) = min mean distance to any other cluster
        b_i = np.inf
        for lbl in unique_labels:
            if lbl == own_label:
                continue
            other_mask = labels == lbl
            mean_dist = dist_matrix[i, other_mask].mean()
            if mean_dist < b_i:
                b_i = mean_dist

        denom = max(a_i, b_i)
        sil[i] = (b_i - a_i) / denom if denom > 0 else 0.0

    return sil


def silhouette_score(
    X: NDArray[np.float64],
    labels: NDArray[np.int64],
) -> float:
    """Mean silhouette coefficient across all samples."""
    return float(np.mean(silhouette_samples(X, labels)))


# ---------------------------------------------------------------------------
# Optimal-k search
# ---------------------------------------------------------------------------


def find_optimal_k(
    X: NDArray[np.float64],
    k_range: range | None = None,
    seed: int = 42,
) -> tuple[int, dict[int, float]]:
    """Try each *k* in *k_range* and return the one with highest silhouette.

    Returns
    -------
    best_k : int
    scores : dict mapping k → silhouette score
    """
    X = np.asarray(X, dtype=np.float64)
    n = X.shape[0]
    if k_range is None:
        # For 90 tools, explore up to ~sqrt(n) clusters (~9-10) but cap at 20
        upper = min(max(int(n ** 0.5) + 5, 13), n)
        k_range = range(3, upper)

    scores: dict[int, float] = {}
    for k in k_range:
        if k >= n or k < 2:
            continue
        labels, _, _ = kmeans(X, k, seed=seed)
        score = silhouette_score(X, labels)
        scores[k] = score

    if not scores:
        return 2, {2: 0.0}

    best_k = max(scores, key=scores.get)  # type: ignore[arg-type]
    return best_k, scores


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def drop_zero_variance(
    X: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
    """Remove columns with zero variance (constant across all samples).

    Returns
    -------
    filtered : (n, d') array with only non-constant columns
    kept_mask : (d,) boolean mask of which original columns were kept
    """
    X = np.asarray(X, dtype=np.float64)
    variances = X.var(axis=0)
    mask = variances > 0
    return X[:, mask], mask


def normalize_minmax(X: NDArray[np.float64]) -> NDArray[np.float64]:
    """Min-max normalise each column to [0, 1]."""
    X = np.asarray(X, dtype=np.float64)
    mins = X.min(axis=0)
    maxs = X.max(axis=0)
    rng = maxs - mins
    rng[rng == 0] = 1.0  # avoid division by zero for constant columns
    return (X - mins) / rng


def combine_features(
    structural: NDArray[np.float64],
    embeddings: NDArray[np.float64],
    alpha: float = 0.4,
) -> NDArray[np.float64]:
    """Weighted concatenation of structural and embedding features.

    Parameters
    ----------
    structural : (n, d_s) normalised structural features
    embeddings : (n, d_e) embedding vectors (already unit-normalised by provider)
    alpha : weight for structural features; embedding weight = 1 - alpha

    Returns
    -------
    (n, d_s + d_e) combined matrix
    """
    beta = 1.0 - alpha
    # Check if embeddings are all-zero (ZeroVectorProvider)
    if np.allclose(embeddings, 0.0):
        # Structural-only mode
        return structural

    return np.hstack([alpha * structural, beta * embeddings])


def cosine_similarity(
    a: NDArray[np.float64],
    b: NDArray[np.float64],
) -> float:
    """Cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def euclidean_distance(
    a: NDArray[np.float64],
    b: NDArray[np.float64],
) -> float:
    """Euclidean distance between two vectors."""
    return float(np.linalg.norm(a - b))


# ---------------------------------------------------------------------------
# Internal distance helpers
# ---------------------------------------------------------------------------


def _pairwise_sq_dist(
    A: NDArray[np.float64],
    B: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Squared Euclidean distance between each row of A and each row of B.

    Returns (n_A, n_B) matrix.
    """
    # ||a - b||² = ||a||² + ||b||² - 2·a·b
    A_sq = np.sum(A ** 2, axis=1, keepdims=True)  # (n_A, 1)
    B_sq = np.sum(B ** 2, axis=1, keepdims=True)  # (n_B, 1)
    return A_sq + B_sq.T - 2 * A @ B.T


def _pairwise_dist_full(X: NDArray[np.float64]) -> NDArray[np.float64]:
    """Full pairwise Euclidean distance matrix for X (n, d)."""
    sq = _pairwise_sq_dist(X, X)
    np.maximum(sq, 0.0, out=sq)  # numerical safety
    return np.sqrt(sq)
