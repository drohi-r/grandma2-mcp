"""Abstract embedding interface, zero-vector stub, and GitHub Models provider."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    Implementations must supply model_name, dimensions, embed_one, and embed_many.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier for the embedding model."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Dimensionality of the embedding vectors."""
        ...

    @abstractmethod
    def embed_one(self, text: str) -> list[float]:
        """Embed a single text string."""
        ...

    @abstractmethod
    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple text strings."""
        ...


class ZeroVectorProvider(EmbeddingProvider):
    """Stub provider that returns zero vectors. For testing and development."""

    def __init__(self, dimensions: int = 1536) -> None:
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return "zero-vector-stub"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_one(self, text: str) -> list[float]:
        return [0.0] * self._dimensions

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self._dimensions for _ in texts]


class GitHubModelsProvider(EmbeddingProvider):
    """Embedding provider using GitHub Models (OpenAI-compatible endpoint).

    Default model: openai/text-embedding-3-small (1536 dimensions)
    Endpoint: https://models.github.ai/inference
    Auth: GitHub PAT with models:read scope.

    Rate-limit strategy:
    - inter_request_delay: proactive pause between API calls (default 4s)
      keeps throughput at ~15 req/min, avoiding per-minute 429s entirely.
    - batch_size=32: halves API calls vs the old 16 with no quality loss.
    - Dedup: identical texts in a batch are embedded once and reused.
    - Daily quota detection: retry-after > 1h raises immediately with a
      clear "come back tomorrow" message instead of burning retries.
    """

    GITHUB_MODELS_BASE_URL = "https://models.github.ai/inference"

    def __init__(
        self,
        token: str,
        model: str = "openai/text-embedding-3-small",
        dimensions: int = 1536,
        batch_size: int = 32,
        timeout: float = 60.0,
        inter_request_delay: float = 4.0,
    ) -> None:
        self._token = token
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._inter_request_delay = inter_request_delay
        self._client = httpx.Client(
            base_url=self.GITHUB_MODELS_BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_one(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embed texts with deduplication, pacing, and retry/backoff."""
        if not texts:
            return []

        # --- Change 4: chunk-level deduplication ---
        # Build ordered list of unique texts and a mapping back to original positions.
        unique_texts: list[str] = []
        unique_index: dict[str, int] = {}
        for text in texts:
            if text not in unique_index:
                unique_index[text] = len(unique_texts)
                unique_texts.append(text)

        dedup_savings = len(texts) - len(unique_texts)
        if dedup_savings:
            logger.info(
                "Dedup: skipped %d duplicate texts (%d unique of %d total)",
                dedup_savings, len(unique_texts), len(texts),
            )

        # Embed unique texts in batches
        unique_embeddings: list[list[float]] = []
        for i in range(0, len(unique_texts), self._batch_size):
            batch = unique_texts[i : i + self._batch_size]
            response = self._request_with_retry(batch)
            data = response.json()["data"]
            batch_embeddings = [
                item["embedding"]
                for item in sorted(data, key=lambda x: x["index"])
            ]
            unique_embeddings.extend(batch_embeddings)
            logger.debug(
                "Embedded batch %d-%d (%d texts)", i, i + len(batch), len(batch)
            )
            # --- Change 2: proactive inter-request pacing ---
            if self._inter_request_delay > 0 and i + self._batch_size < len(unique_texts):
                time.sleep(self._inter_request_delay)

        # Re-expand to original order (duplicates reuse the cached embedding)
        return [unique_embeddings[unique_index[text]] for text in texts]

    def _request_with_retry(
        self, batch: list[str], max_retries: int = 5
    ) -> httpx.Response:
        """POST embeddings request with pacing, exponential backoff on 429/5xx,
        and immediate failure on daily quota exhaustion."""
        delay = 2.0
        for attempt in range(max_retries + 1):
            response = self._client.post(
                "/embeddings",
                json={"input": batch, "model": self._model},
            )

            # Log rate-limit headers for observability (run with -v to see)
            rl_headers = {
                k: v for k, v in response.headers.items()
                if k.lower().startswith(("x-ratelimit", "x-ms-", "ratelimit"))
            }
            if rl_headers:
                logger.debug("Rate-limit headers: %s", rl_headers)

            if response.status_code == 429 or response.status_code >= 500:
                retry_after = response.headers.get("retry-after")

                # --- Change 1: detect daily quota vs per-minute limit ---
                if retry_after and float(retry_after) > 3600:
                    hours = float(retry_after) / 3600
                    raise RuntimeError(
                        f"GitHub Models daily quota exhausted "
                        f"(retry-after={float(retry_after):.0f}s, ~{hours:.1f}h). "
                        f"Resume tomorrow or use --provider zero as fallback."
                    )

                if attempt == max_retries:
                    response.raise_for_status()

                wait = min(float(retry_after), 120.0) if retry_after else delay
                logger.warning(
                    "Rate limited (%d), retrying in %.1fs (attempt %d/%d)",
                    response.status_code, wait, attempt + 1, max_retries,
                )
                time.sleep(wait)
                delay = min(delay * 2, 60.0)
                continue

            response.raise_for_status()
            return response
        return response  # unreachable, keeps type checker happy
