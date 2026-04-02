"""
Tests for Bitfocus Companion integration tools:
generate_companion_config, companion_button_press
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGenerateCompanionConfig:
    """Tests for the generate_companion_config MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.scan_page_executor_layout")
    @patch("src.server.get_client")
    async def test_generates_valid_config(self, mock_get_client, mock_scan):
        from src.server import generate_companion_config

        mock_get_client.return_value = MagicMock()
        mock_scan.return_value = json.dumps({
            "executors": [
                {"executor_id": 101, "label": "Front Wash", "sequence_id": 1, "assigned": True},
                {"executor_id": 102, "label": "Back Light", "sequence_id": 2, "assigned": True},
                {"executor_id": 103, "label": "Empty", "sequence_id": None, "assigned": False},
            ],
            "page": 1,
        })

        result = await generate_companion_config(page=1)
        data = json.loads(result)

        assert data["executor_count"] == 3
        assert data["ma2_page"] == 1
        assert data["risk_tier"] == "SAFE_READ"

        config = data["companion_config"]
        assert config["version"] == 4
        assert config["type"] == "page"
        assert "controls" in config["page"]

    @pytest.mark.asyncio
    @patch("src.server.scan_page_executor_layout")
    @patch("src.server.get_client")
    async def test_config_has_correct_commands(self, mock_get_client, mock_scan):
        from src.server import generate_companion_config

        mock_get_client.return_value = MagicMock()
        mock_scan.return_value = json.dumps({
            "executors": [
                {"executor_id": 101, "label": "Cue Go", "sequence_id": 1, "assigned": True},
            ],
            "page": 2,
        })

        result = await generate_companion_config(page=2)
        data = json.loads(result)
        config = data["companion_config"]

        # Check the button action sends the right MA2 command
        button = config["page"]["controls"]["0/0"]
        action = button["steps"]["0"]["action_sets"]["down"][0]
        assert action["actionId"] == "command"
        assert action["options"]["command"] == "Go+ Executor 2.101"

    @pytest.mark.asyncio
    @patch("src.server.scan_page_executor_layout")
    @patch("src.server.get_client")
    async def test_grid_layout_wraps_correctly(self, mock_get_client, mock_scan):
        from src.server import generate_companion_config

        mock_get_client.return_value = MagicMock()
        # 5 executors with grid_columns=3 should wrap to row 1
        mock_scan.return_value = json.dumps({
            "executors": [
                {"executor_id": i, "label": f"E{i}", "sequence_id": i, "assigned": True}
                for i in range(1, 6)
            ],
            "page": 1,
        })

        result = await generate_companion_config(page=1, grid_columns=3)
        data = json.loads(result)
        config = data["companion_config"]
        controls = config["page"]["controls"]

        # 5 buttons: row 0 has 3 (0/0, 0/1, 0/2), row 1 has 2 (1/0, 1/1)
        assert "0/0" in controls
        assert "0/2" in controls
        assert "1/0" in controls
        assert "1/1" in controls

    @pytest.mark.asyncio
    @patch("src.server.scan_page_executor_layout")
    @patch("src.server.get_client")
    async def test_error_when_scan_fails(self, mock_get_client, mock_scan):
        from src.server import generate_companion_config

        mock_get_client.return_value = MagicMock()
        mock_scan.return_value = json.dumps({
            "error": "Connection refused",
            "executors": [],
        })

        result = await generate_companion_config(page=1)
        data = json.loads(result)
        assert "error" in data


class TestCompanionButtonPress:
    """Tests for the companion_button_press MCP tool."""

    @pytest.mark.asyncio
    @patch("urllib.request.urlopen")
    async def test_successful_press(self, mock_urlopen):
        from src.server import companion_button_press

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = await companion_button_press(page=1, button=0)
        data = json.loads(result)

        assert data["status"] == "ok"
        assert data["http_status"] == 200
        assert "localhost" in data["url_called"]
        assert "/press/bank/1/0" in data["url_called"]

    @pytest.mark.asyncio
    @patch("urllib.request.urlopen")
    async def test_connection_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        from src.server import companion_button_press

        result = await companion_button_press(page=1, button=0)
        data = json.loads(result)

        assert data["status"] == "error"
        assert "Connection refused" in data["error"]
        assert "hint" in data

    @pytest.mark.asyncio
    @patch("urllib.request.urlopen")
    async def test_custom_host_port(self, mock_urlopen):
        from src.server import companion_button_press

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = await companion_button_press(
            page=3, button=7, host="192.168.1.50", port=9000
        )
        data = json.loads(result)

        assert "192.168.1.50:9000" in data["url_called"]
        assert "/press/bank/3/7" in data["url_called"]
