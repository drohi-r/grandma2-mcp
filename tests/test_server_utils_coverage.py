"""Tests for server utility MCP tools with no existing coverage:
  - set_executor_priority
  - get_similar_tools
  - discover_filter_attributes
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSetExecutorPriority:
    """Tests for set_executor_priority."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_valid_priority_sends_command(self, mock_get_client):
        from src.server import set_executor_priority

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await set_executor_priority(executor_id=201, priority="high")
        data = json.loads(result)

        assert "command_sent" in data
        assert "201" in data["command_sent"]
        assert "high" in data["command_sent"]
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_normal_priority(self, mock_get_client):
        from src.server import set_executor_priority

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await set_executor_priority(executor_id=1, priority="normal")
        data = json.loads(result)

        assert "normal" in data["command_sent"]
        assert data.get("error") is None

    @pytest.mark.asyncio
    async def test_invalid_priority_returns_error(self):
        from src.server import set_executor_priority

        result = await set_executor_priority(executor_id=1, priority="invalid_prio")
        data = json.loads(result)

        assert data.get("blocked") is True
        assert "error" in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_super_priority(self, mock_get_client):
        from src.server import set_executor_priority

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await set_executor_priority(executor_id=100, priority="super")
        data = json.loads(result)

        assert "command_sent" in data
        assert data.get("blocked") is not True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_raw_response_forwarded(self, mock_get_client):
        from src.server import set_executor_priority

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Priority set")
        mock_get_client.return_value = mock_client

        result = await set_executor_priority(executor_id=5, priority="low")
        data = json.loads(result)

        assert data["raw_response"] == "Priority set"


class TestGetSimilarTools:
    """Tests for get_similar_tools."""

    def _make_taxonomy(self):
        """Minimal taxonomy with 5 tools for testing."""
        tools = ["list_cues", "list_groups", "store_cue", "playback_action", "set_intensity"]
        categories = {
            "queries": {"tools": [{"name": n} for n in ["list_cues", "list_groups"]]},
            "playback": {"tools": [{"name": n} for n in ["playback_action", "store_cue", "set_intensity"]]},
        }
        tool_features = {}
        for i, name in enumerate(tools):
            structural = [float(j == i % 3) for j in range(3)]
            tool_features[name] = {
                "structural": structural,
                "embedding": [],
                "docstring_summary": f"Summary for {name}",
            }
        return {
            "metadata": {"k": 2},
            "categories": categories,
            "tool_features": tool_features,
        }

    @pytest.mark.asyncio
    @patch("src.server._load_taxonomy_cached")
    async def test_returns_ranked_similar_tools(self, mock_load):
        from src.server import get_similar_tools

        mock_load.return_value = self._make_taxonomy()

        result = await get_similar_tools(tool_name="list_cues", top_n=3)
        data = json.loads(result)

        assert isinstance(data, list)
        assert len(data) <= 3
        # Each entry has required keys
        for entry in data:
            assert "name" in entry
            assert "distance" in entry
            assert "similarity" in entry
            assert "category" in entry

    @pytest.mark.asyncio
    @patch("src.server._load_taxonomy_cached")
    async def test_unknown_tool_returns_error(self, mock_load):
        from src.server import get_similar_tools

        mock_load.return_value = self._make_taxonomy()

        result = await get_similar_tools(tool_name="nonexistent_tool")
        data = json.loads(result)

        assert "error" in data
        assert data.get("blocked") is True

    @pytest.mark.asyncio
    @patch("src.server._load_taxonomy_cached")
    async def test_top_n_respected(self, mock_load):
        from src.server import get_similar_tools

        mock_load.return_value = self._make_taxonomy()

        result = await get_similar_tools(tool_name="playback_action", top_n=2)
        data = json.loads(result)

        assert isinstance(data, list)
        assert len(data) <= 2

    @pytest.mark.asyncio
    @patch("src.server._load_taxonomy_cached")
    async def test_results_sorted_by_distance(self, mock_load):
        from src.server import get_similar_tools

        mock_load.return_value = self._make_taxonomy()

        result = await get_similar_tools(tool_name="list_cues", top_n=10)
        data = json.loads(result)

        distances = [entry["distance"] for entry in data]
        assert distances == sorted(distances), "Results should be sorted by ascending distance"


class TestDiscoverFilterAttributes:
    """Tests for discover_filter_attributes MCP tool wrapper."""

    @pytest.mark.asyncio
    @patch("src.server._discover_filter_attributes")
    async def test_returns_attributes_and_total(self, mock_discover):
        from src.server import discover_filter_attributes

        mock_discover.return_value = {
            "dimmer": ["DIMMER", "STROBE"],
            "color": ["R", "G", "B", "CTC"],
            "position": ["PAN", "TILT"],
        }

        result = await discover_filter_attributes()
        data = json.loads(result)

        assert "attributes" in data
        assert data["total_attributes"] == 2 + 4 + 2  # 8 entries from the mock
        assert data["risk_tier"] == "SAFE_READ"
        assert "note" in data

    @pytest.mark.asyncio
    @patch("src.server._discover_filter_attributes")
    async def test_empty_show_returns_empty_dict(self, mock_discover):
        from src.server import discover_filter_attributes

        mock_discover.return_value = {}

        result = await discover_filter_attributes()
        data = json.loads(result)

        assert data["total_attributes"] == 0
        assert data["attributes"] == {}

    @pytest.mark.asyncio
    @patch("src.server._discover_filter_attributes")
    async def test_delegates_to_internal_function(self, mock_discover):
        from src.server import discover_filter_attributes

        mock_discover.return_value = {"dimmer": ["DIMMER"]}
        await discover_filter_attributes()

        mock_discover.assert_called_once()
