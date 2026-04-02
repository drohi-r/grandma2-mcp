"""
Tests for OSC output tool: send_osc
"""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestSendOsc:
    """Tests for the send_osc MCP tool."""

    @pytest.mark.asyncio
    @patch("socket.socket")
    async def test_sends_float_value(self, mock_socket_cls):
        from src.server import send_osc

        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        result = await send_osc(
            address="/composition/tempocontroller/tempo",
            value=128.0,
            host="192.168.1.50",
            port=7000,
        )
        data = json.loads(result)

        assert data["status"] == "sent"
        assert data["address"] == "/composition/tempocontroller/tempo"
        assert data["value"] == 128.0
        assert data["host"] == "192.168.1.50"
        assert data["port"] == 7000
        mock_sock.sendto.assert_called_once()
        mock_sock.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("socket.socket")
    async def test_sends_int_value(self, mock_socket_cls):
        from src.server import send_osc

        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        result = await send_osc(
            address="/composition/layers/1/clips/1/connect",
            value=1,
        )
        data = json.loads(result)

        assert data["status"] == "sent"
        assert data["value"] == 1
        mock_sock.sendto.assert_called_once()

    @pytest.mark.asyncio
    @patch("socket.socket")
    async def test_sends_string_value(self, mock_socket_cls):
        from src.server import send_osc

        mock_sock = MagicMock()
        mock_socket_cls.return_value = mock_sock

        result = await send_osc(
            address="/test/message",
            value="hello",
        )
        data = json.loads(result)

        assert data["status"] == "sent"
        assert data["value"] == "hello"

    @pytest.mark.asyncio
    @patch("socket.socket")
    async def test_handles_send_error(self, mock_socket_cls):
        from src.server import send_osc

        mock_sock = MagicMock()
        mock_sock.sendto.side_effect = OSError("Network unreachable")
        mock_socket_cls.return_value = mock_sock

        result = await send_osc(address="/test", value=1.0)
        data = json.loads(result)

        assert data["status"] == "error"
        assert "Network unreachable" in data["error"]
