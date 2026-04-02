"""
Tests for BPM sync tool: set_bpm
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSetBpm:
    """Tests for the set_bpm MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sets_bpm_on_speed_master_1(self, mock_get_client):
        from src.server import set_bpm

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await set_bpm(bpm=128)
        data = json.loads(result)

        assert data["bpm"] == 128
        assert data["speed_master"] == 1
        assert data["command_sent"] == "SpecialMaster 3.1 At 128"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sets_bpm_on_custom_speed_master(self, mock_get_client):
        from src.server import set_bpm

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await set_bpm(bpm=140.5, speed_master=3)
        data = json.loads(result)

        assert data["bpm"] == 140.5
        assert data["speed_master"] == 3
        assert data["command_sent"] == "SpecialMaster 3.3 At 140.5"

    @pytest.mark.asyncio
    async def test_rejects_bpm_out_of_range(self):
        from src.server import set_bpm

        result = await set_bpm(bpm=0)
        data = json.loads(result)
        assert "error" in data
        assert data["blocked"] is True

        result = await set_bpm(bpm=500)
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_rejects_invalid_speed_master(self):
        from src.server import set_bpm

        result = await set_bpm(bpm=120, speed_master=0)
        data = json.loads(result)
        assert "error" in data

        result = await set_bpm(bpm=120, speed_master=17)
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fractional_bpm(self, mock_get_client):
        from src.server import set_bpm

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await set_bpm(bpm=128.53)
        data = json.loads(result)
        assert "128.53" in data["command_sent"]
