"""Tests for busking MCP tools: modulate_effect, clear_effects_on_page,
normalize_page_faders, classify_show_mode.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestModulateEffectTool:
    """Tests for modulate_effect."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_rate_mode_sends_correct_command(self, mock_get_client):
        from src.server import modulate_effect

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await modulate_effect(mode="rate", value=150)
        data = json.loads(result)

        assert data["mode"] == "rate"
        assert data["value"] == 150
        assert "EffectRate" in data["command"] or "effectrate" in data["command"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_speed_mode_sends_correct_command(self, mock_get_client):
        from src.server import modulate_effect

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await modulate_effect(mode="speed", value=120)
        data = json.loads(result)

        assert data["mode"] == "speed"
        assert data["value"] == 120
        assert "EffectSpeed" in data["command"] or "effectspeed" in data["command"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_response_included_in_output(self, mock_get_client):
        from src.server import modulate_effect

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="Acknowledged")
        mock_get_client.return_value = mock_client

        result = await modulate_effect(mode="rate", value=100)
        data = json.loads(result)

        assert data["response"] == "Acknowledged"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_rate_normal_value_100(self, mock_get_client):
        from src.server import modulate_effect

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="")
        mock_get_client.return_value = mock_client

        result = await modulate_effect(mode="rate", value=100)
        data = json.loads(result)

        assert data["value"] == 100
        assert "100" in data["command"]


class TestClearEffectsOnPageTool:
    """Tests for clear_effects_on_page."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_default_range_returns_20_commands(self, mock_get_client):
        from src.server import clear_effects_on_page

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await clear_effects_on_page(page=1)
        data = json.loads(result)

        assert data["command_count"] == 20
        assert data["page"] == 1

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_custom_range(self, mock_get_client):
        from src.server import clear_effects_on_page

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await clear_effects_on_page(page=3, start_exec=5, end_exec=10)
        data = json.loads(result)

        assert data["command_count"] == 6  # 10 - 5 + 1
        assert data["page"] == 3

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_response_forwarded(self, mock_get_client):
        from src.server import clear_effects_on_page

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="Cleared")
        mock_get_client.return_value = mock_client

        result = await clear_effects_on_page(page=2)
        data = json.loads(result)

        assert data["response"] == "Cleared"


class TestNormalizePageFadersTool:
    """Tests for normalize_page_faders."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_zeroed_flag_set(self, mock_get_client):
        from src.server import normalize_page_faders

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await normalize_page_faders(page=1)
        data = json.loads(result)

        assert data["zeroed"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_default_range_20_commands(self, mock_get_client):
        from src.server import normalize_page_faders

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await normalize_page_faders(page=2)
        data = json.loads(result)

        assert data["command_count"] == 20
        assert data["page"] == 2

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_custom_exec_range(self, mock_get_client):
        from src.server import normalize_page_faders

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await normalize_page_faders(page=1, start_exec=1, end_exec=5)
        data = json.loads(result)

        assert data["command_count"] == 5


class TestClassifyShowModeTool:
    """Tests for classify_show_mode."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_empty_show_classified_as_empty(self, mock_get_client):
        from src.server import classify_show_mode

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(return_value="[EffectLibrary]")
        mock_get_client.return_value = mock_client

        result = await classify_show_mode()
        data = json.loads(result)

        assert data["mode"] == "empty"
        assert data["evidence"]["effects"] == 0
        assert data["evidence"]["macros"] == 0

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_mostly_effects_classified_as_busking(self, mock_get_client):
        from src.server import classify_show_mode

        effect_response = "\n".join(["effect1", "effect2", "effect3", "effect4", "effect5"])
        macro_response = "macro1"

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(side_effect=[effect_response, macro_response])
        mock_get_client.return_value = mock_client

        result = await classify_show_mode()
        data = json.loads(result)

        assert data["mode"] == "busking"
        assert data["evidence"]["effects"] == 5
        assert data["evidence"]["macros"] == 1

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_mostly_macros_classified_as_sequence(self, mock_get_client):
        from src.server import classify_show_mode

        effect_response = "effect1"
        macro_response = "\n".join(["macro1", "macro2", "macro3", "macro4", "macro5"])

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(side_effect=[effect_response, macro_response])
        mock_get_client.return_value = mock_client

        result = await classify_show_mode()
        data = json.loads(result)

        assert data["mode"] == "sequence"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_equal_mix_classified_as_hybrid(self, mock_get_client):
        from src.server import classify_show_mode

        effect_response = "\n".join(["e1", "e2", "e3"])
        macro_response = "\n".join(["m1", "m2", "m3"])

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(side_effect=[effect_response, macro_response])
        mock_get_client.return_value = mock_client

        result = await classify_show_mode()
        data = json.loads(result)

        assert data["mode"] == "hybrid"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_bracket_lines_excluded_from_count(self, mock_get_client):
        from src.server import classify_show_mode

        # Lines starting with [ are header/footer lines and should be excluded
        effect_response = "[EffectLibrary]\neffect1\neffect2"
        macro_response = "[MacroLibrary]"

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock(side_effect=[effect_response, macro_response])
        mock_get_client.return_value = mock_client

        result = await classify_show_mode()
        data = json.loads(result)

        assert data["evidence"]["effects"] == 2
        assert data["evidence"]["macros"] == 0
