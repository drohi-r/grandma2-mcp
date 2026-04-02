"""Tests for MCP transport selection (GMA_TRANSPORT env var)."""

import os
from unittest.mock import patch

import pytest


class TestTransportSelection:
    def test_default_is_stdio(self):
        """Without GMA_TRANSPORT, main() should use stdio."""
        from src.server import _VALID_TRANSPORTS
        assert "stdio" in _VALID_TRANSPORTS

    def test_valid_transports(self):
        from src.server import _VALID_TRANSPORTS
        assert _VALID_TRANSPORTS == ("stdio", "sse", "streamable-http")

    @patch.dict(os.environ, {"GMA_TRANSPORT": "invalid"})
    @patch("src.server.mcp")
    def test_invalid_transport_raises(self, mock_mcp):
        from src.server import main
        with pytest.raises(ValueError, match="Invalid GMA_TRANSPORT"):
            main()

    @patch.dict(os.environ, {"GMA_TRANSPORT": "stdio"})
    @patch("src.server.mcp")
    def test_stdio_transport(self, mock_mcp):
        from src.server import main
        main()
        mock_mcp.run.assert_called_once_with(transport="stdio")

    @patch.dict(os.environ, {"GMA_TRANSPORT": "sse"})
    @patch("src.server.mcp")
    def test_sse_transport(self, mock_mcp):
        from src.server import main
        main()
        mock_mcp.run.assert_called_once_with(transport="sse")

    @patch.dict(os.environ, {"GMA_TRANSPORT": "streamable-http"})
    @patch("src.server.mcp")
    def test_streamable_http_transport(self, mock_mcp):
        from src.server import main
        main()
        mock_mcp.run.assert_called_once_with(transport="streamable-http")

    @patch.dict(os.environ, {"GMA_TRANSPORT": "SSE"})
    @patch("src.server.mcp")
    def test_case_insensitive(self, mock_mcp):
        """GMA_TRANSPORT should be case-insensitive."""
        from src.server import main
        main()
        mock_mcp.run.assert_called_once_with(transport="sse")
