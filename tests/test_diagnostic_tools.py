"""
Tests for diagnostic tools: compare_cue_values, diagnose_no_output
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCompareCueValues:
    """Tests for the compare_cue_values MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_identical_cues(self, mock_get_client):
        from src.server import compare_cue_values

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Dimmer 100\nColor Red\n"
        )
        mock_get_client.return_value = mock_client

        result = await compare_cue_values(sequence_id=1, cue_a=1, cue_b=2)
        data = json.loads(result)

        assert data["identical"] is True
        assert data["sequence_id"] == 1
        assert data["cue_a"] == 1
        assert data["cue_b"] == 2
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_different_cues(self, mock_get_client):
        from src.server import compare_cue_values

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=[
                "Dimmer 100\nColor Red\n",
                "Dimmer 50\nColor Blue\n",
            ]
        )
        mock_get_client.return_value = mock_client

        result = await compare_cue_values(sequence_id=1, cue_a=1, cue_b=2)
        data = json.loads(result)

        assert data["identical"] is False
        assert len(data["only_in_cue_a"]) > 0
        assert len(data["only_in_cue_b"]) > 0


class TestDiagnoseNoOutput:
    """Tests for the diagnose_no_output MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_basic_checks_run(self, mock_get_client):
        from src.server import diagnose_no_output

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="$VERSION=3.9.60\n$SELECTEDFIXTURESCOUNT=0\n"
        )
        mock_get_client.return_value = mock_client

        result = await diagnose_no_output()
        data = json.loads(result)

        assert "checks" in data
        assert data["risk_tier"] == "SAFE_READ"
        assert data["overall_status"] in ("ok", "warning", "fail")

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_with_fixture_id(self, mock_get_client):
        from src.server import diagnose_no_output

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Fixture 5 - Generic Dimmer\n$SELECTEDFIXTURESCOUNT=1\n"
        )
        mock_get_client.return_value = mock_client

        result = await diagnose_no_output(fixture_id=5)
        data = json.loads(result)

        assert data["fixture_id"] == 5
        check_names = [c["check"] for c in data["checks"]]
        assert "park_status" in check_names
        assert "patch" in check_names

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_parked_fixture_detected(self, mock_get_client):
        from src.server import diagnose_no_output

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=[
                "$VERSION=3.9.60\n",  # listvar for grand master
                "$VERSION=3.9.60\n",  # listvar for blackout
                "Fixture 5 - PARKED\n",  # list fixture
                "Fixture 5 info\n",  # info fixture
                "$SELECTEDFIXTURESCOUNT=0\n",  # listvar for selection
            ]
        )
        mock_get_client.return_value = mock_client

        result = await diagnose_no_output(fixture_id=5)
        data = json.loads(result)

        park_check = next(c for c in data["checks"] if c["check"] == "park_status")
        assert park_check["status"] == "fail"
        assert "PARKED" in park_check["detail"]
