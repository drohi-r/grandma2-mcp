"""
Tests for batch operation tools: batch_label, bulk_executor_assign, auto_number_cues
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBatchLabel:
    """Tests for the batch_label MCP tool."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import batch_label

        result = await batch_label(object_type="group", items='[{"id":1,"name":"Test"}]')
        data = json.loads(result)
        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["risk_tier"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_labels_multiple_objects(self, mock_get_client):
        from src.server import batch_label

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        items = json.dumps([
            {"id": 1, "name": "Front Wash"},
            {"id": 2, "name": "Back Light"},
            {"id": 3, "name": "Side Fill"},
        ])
        result = await batch_label(
            object_type="group", items=items, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["labels_applied"] == 3
        assert data["total_items"] == 3
        assert len(data["commands"]) == 3
        assert data["errors"] == []
        assert data["blocked"] is False

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_skips_invalid_items(self, mock_get_client):
        from src.server import batch_label

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        items = json.dumps([
            {"id": 1, "name": "Valid"},
            {"id": 2},  # missing name
            {"name": "No ID"},  # missing id
        ])
        result = await batch_label(
            object_type="group", items=items, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["labels_applied"] == 1
        assert len(data["errors"]) == 2

    @pytest.mark.asyncio
    async def test_invalid_json_returns_error(self):
        from src.server import batch_label

        result = await batch_label(
            object_type="group", items="not valid json", confirm_destructive=True
        )
        data = json.loads(result)
        assert "error" in data
        assert "Invalid items JSON" in data["error"]


class TestBulkExecutorAssign:
    """Tests for the bulk_executor_assign MCP tool."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import bulk_executor_assign

        result = await bulk_executor_assign(executor_id=101, sequence_id=1)
        data = json.loads(result)
        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["risk_tier"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_only(self, mock_get_client):
        from src.server import bulk_executor_assign

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await bulk_executor_assign(
            executor_id=101, sequence_id=1, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["executor"] == "1.101"
        assert data["sequence_id"] == 1
        assert len(data["commands_sent"]) == 1
        assert "assign" in data["commands_sent"][0].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_full_setup(self, mock_get_client):
        from src.server import bulk_executor_assign

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await bulk_executor_assign(
            executor_id=101,
            sequence_id=1,
            trigger="go",
            priority="high",
            fader_function="master",
            label="Main Wash",
            confirm_destructive=True,
        )
        data = json.loads(result)

        # assign + trigger + priority + fader + label = 5 commands
        assert len(data["commands_sent"]) == 5
        assert data["options_applied"]["trigger"] == "go"
        assert data["options_applied"]["priority"] == "high"
        assert data["options_applied"]["label"] == "Main Wash"


class TestAutoNumberCues:
    """Tests for the auto_number_cues MCP tool."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import auto_number_cues

        result = await auto_number_cues(sequence_id=1)
        data = json.loads(result)
        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["risk_tier"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_renumbers_cues(self, mock_get_client):
        from src.server import auto_number_cues

        mock_client = MagicMock()
        # First call: list cues → return mock cue listing
        # Subsequent calls: move cue → return Ok
        mock_client.send_command_with_response = AsyncMock(
            side_effect=[
                "1     Cue 1\n3     Cue 3\n7     Cue 7\n",  # list
                "Ok",  # move cue 7 → 30
                "Ok",  # move cue 3 → 20
                "Ok",  # move cue 1 → 10
            ]
        )
        mock_get_client.return_value = mock_client

        result = await auto_number_cues(
            sequence_id=1, start=10, spacing=10, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["cues_renumbered"] == 3
        assert len(data["old_to_new"]) == 3
        assert len(data["commands"]) == 3

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_empty_sequence_returns_error(self, mock_get_client):
        from src.server import auto_number_cues

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="NO OBJECTS FOUND")
        mock_get_client.return_value = mock_client

        result = await auto_number_cues(
            sequence_id=99, confirm_destructive=True
        )
        data = json.loads(result)
        assert "error" in data
