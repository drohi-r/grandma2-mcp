"""Tests for the RAG embedding interface."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from rag.ingest.embed import EmbeddingProvider, GitHubModelsProvider, ZeroVectorProvider


class TestZeroVectorProvider:
    def test_model_name(self):
        p = ZeroVectorProvider()
        assert p.model_name == "zero-vector-stub"

    def test_default_dimensions(self):
        p = ZeroVectorProvider()
        assert p.dimensions == 1536  # matches GitHubModelsProvider default

    def test_custom_dimensions(self):
        p = ZeroVectorProvider(dimensions=128)
        assert p.dimensions == 128

    def test_embed_one_returns_zeros(self):
        p = ZeroVectorProvider(dimensions=3)
        result = p.embed_one("hello world")
        assert result == [0.0, 0.0, 0.0]

    def test_embed_one_correct_length(self):
        p = ZeroVectorProvider(dimensions=256)
        result = p.embed_one("test")
        assert len(result) == 256

    def test_embed_many(self):
        p = ZeroVectorProvider(dimensions=3)
        results = p.embed_many(["a", "b", "c"])
        assert len(results) == 3
        for r in results:
            assert r == [0.0, 0.0, 0.0]

    def test_embed_many_empty(self):
        p = ZeroVectorProvider(dimensions=3)
        results = p.embed_many([])
        assert results == []


class TestEmbeddingProviderABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            EmbeddingProvider()  # type: ignore[abstract]

    def test_subclass_must_implement_all(self):
        class PartialProvider(EmbeddingProvider):
            @property
            def model_name(self) -> str:
                return "partial"

            @property
            def dimensions(self) -> int:
                return 10

            # Missing embed_one and embed_many

        with pytest.raises(TypeError):
            PartialProvider()  # type: ignore[abstract]


def _mock_embedding_response(embeddings: list[list[float]]) -> httpx.Response:
    """Build a mock httpx.Response with OpenAI-compatible embedding data."""
    data = [{"index": i, "embedding": emb} for i, emb in enumerate(embeddings)]
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.headers = {}
    resp.json.return_value = {"data": data, "model": "openai/text-embedding-3-small"}
    resp.raise_for_status = MagicMock()
    return resp


class TestGitHubModelsProvider:
    def test_properties(self):
        p = GitHubModelsProvider(token="ghp_test123")
        assert p.model_name == "openai/text-embedding-3-small"
        assert p.dimensions == 1536

    def test_custom_properties(self):
        p = GitHubModelsProvider(
            token="ghp_test123",
            model="openai/text-embedding-3-large",
            dimensions=3072,
        )
        assert p.model_name == "openai/text-embedding-3-large"
        assert p.dimensions == 3072

    @patch.object(httpx.Client, "post")
    def test_embed_one(self, mock_post: MagicMock):
        mock_post.return_value = _mock_embedding_response([[0.1, 0.2, 0.3]])

        p = GitHubModelsProvider(token="ghp_test123", dimensions=3)
        result = p.embed_one("hello world")

        assert result == [0.1, 0.2, 0.3]
        mock_post.assert_called_once_with(
            "/embeddings",
            json={"input": ["hello world"], "model": "openai/text-embedding-3-small"},
        )

    @patch.object(httpx.Client, "post")
    def test_embed_many(self, mock_post: MagicMock):
        mock_post.return_value = _mock_embedding_response(
            [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        )

        p = GitHubModelsProvider(token="ghp_test123", dimensions=2)
        result = p.embed_many(["a", "b", "c"])

        assert len(result) == 3
        assert result[0] == [0.1, 0.2]
        assert result[2] == [0.5, 0.6]

    @patch.object(httpx.Client, "post")
    def test_embed_many_empty(self, mock_post: MagicMock):
        p = GitHubModelsProvider(token="ghp_test123")
        result = p.embed_many([])

        assert result == []
        mock_post.assert_not_called()

    @patch.object(httpx.Client, "post")
    def test_embed_many_batching(self, mock_post: MagicMock):
        """150 texts with batch_size=64 should produce 3 API calls."""

        def _response_for_batch(*args, **kwargs):
            batch = kwargs["json"]["input"]
            return _mock_embedding_response([[0.1] * 3 for _ in range(len(batch))])

        mock_post.side_effect = _response_for_batch

        p = GitHubModelsProvider(token="ghp_test123", dimensions=3, batch_size=64, inter_request_delay=0.0)
        texts = [f"text_{i}" for i in range(150)]
        result = p.embed_many(texts)

        assert mock_post.call_count == 3
        # First batch: 64 texts, second: 64, third: 22
        calls = mock_post.call_args_list
        assert len(calls[0].kwargs["json"]["input"]) == 64
        assert len(calls[1].kwargs["json"]["input"]) == 64
        assert len(calls[2].kwargs["json"]["input"]) == 22
        assert len(result) == 150

    @patch.object(httpx.Client, "post")
    def test_result_ordering(self, mock_post: MagicMock):
        """API may return embeddings out of order — provider must sort by index."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.headers = {}
        resp.json.return_value = {
            "data": [
                {"index": 2, "embedding": [0.5, 0.6]},
                {"index": 0, "embedding": [0.1, 0.2]},
                {"index": 1, "embedding": [0.3, 0.4]},
            ],
            "model": "openai/text-embedding-3-small",
        }
        resp.raise_for_status = MagicMock()
        mock_post.return_value = resp

        p = GitHubModelsProvider(token="ghp_test123", dimensions=2)
        result = p.embed_many(["a", "b", "c"])

        assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

    @patch.object(httpx.Client, "post")
    def test_http_error_raises(self, mock_post: MagicMock):
        """HTTP errors should propagate as httpx.HTTPStatusError."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 401
        resp.headers = {}
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=resp
        )
        mock_post.return_value = resp

        p = GitHubModelsProvider(token="bad_token")
        with pytest.raises(httpx.HTTPStatusError):
            p.embed_one("hello")
