"""
MCP Tools Tests

Tests for high-level MCP tools functionality. These are tools that AI can call.
Uses mocks to simulate Telnet connections and avoid actual network calls.

The MCP tool functions are defined in src/server.py with @mcp.tool() decorators.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCreateFixtureGroupTool:
    """Tests for the create fixture group MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_create_fixture_group_basic(self, mock_get_client):
        """Test creating a basic fixture group."""
        from src.server import create_fixture_group

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock()
        mock_get_client.return_value = mock_client

        result = await create_fixture_group(start_fixture=1, end_fixture=10, group_id=1, confirm_destructive=True)

        calls = mock_client.send_command.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "selfix fixture 1 thru 10"
        assert calls[1][0][0] == "store group 1"

        assert "Group 1" in result
        assert "Fixtures 1" in result
        assert "10" in result

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_create_fixture_group_with_label(self, mock_get_client):
        """Test creating a fixture group with a label."""
        from src.server import create_fixture_group

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock()
        mock_get_client.return_value = mock_client

        await create_fixture_group(
            start_fixture=1, end_fixture=10, group_id=1, group_name="Front Wash", confirm_destructive=True
        )

        calls = mock_client.send_command.call_args_list
        assert len(calls) == 3
        assert calls[0][0][0] == "selfix fixture 1 thru 10"
        assert calls[1][0][0] == "store group 1"
        assert calls[2][0][0] == 'label group 1 "Front Wash"'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_create_fixture_group_with_custom_name(self, mock_get_client):
        """Test creating a fixture group with a custom name."""
        from src.server import create_fixture_group

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock()
        mock_get_client.return_value = mock_client

        await create_fixture_group(
            start_fixture=1, end_fixture=10, group_id=1, group_name="Front Stage Wash", confirm_destructive=True
        )

        calls = mock_client.send_command.call_args_list
        assert calls[2][0][0] == 'label group 1 "Front Stage Wash"'


class TestExecuteSequenceTool:
    """Tests for the execute sequence MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_execute_sequence_go(self, mock_get_client):
        """Test executing a sequence (go)."""
        from src.server import execute_sequence

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock()
        mock_get_client.return_value = mock_client

        await execute_sequence(sequence_id=1, action="go")

        mock_client.send_command.assert_called_once_with("go+ sequence 1")

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_execute_sequence_pause(self, mock_get_client):
        """Test pausing a sequence."""
        from src.server import execute_sequence

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock()
        mock_get_client.return_value = mock_client

        await execute_sequence(sequence_id=1, action="pause")

        mock_client.send_command.assert_called_once_with("pause sequence 1")

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_execute_sequence_goto(self, mock_get_client):
        """Test jumping to a specific cue."""
        from src.server import execute_sequence

        mock_client = MagicMock()
        mock_client.send_command = AsyncMock()
        mock_get_client.return_value = mock_client

        await execute_sequence(sequence_id=1, action="goto", cue_id=5)

        mock_client.send_command.assert_called_once_with("goto cue 5 sequence 1")


class TestSendRawCommandTool:
    """Tests for the send raw command MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_send_safe_write_command(self, mock_get_client):
        """Test sending a SAFE_WRITE command (selfix) — should be allowed."""
        import json

        from src.server import send_raw_command

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await send_raw_command("selfix fixture 1 thru 10")
        data = json.loads(result)

        mock_client.send_command_with_response.assert_called_once_with(
            "selfix fixture 1 thru 10"
        )
        assert data["command_sent"] == "selfix fixture 1 thru 10"
        assert data["blocked"] is False

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_block_destructive_command(self, mock_get_client):
        """Test that destructive commands are blocked without confirm_destructive."""
        import json

        from src.server import send_raw_command

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = await send_raw_command("delete cue 1 thru 9999")
        data = json.loads(result)

        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"
        assert data["command_sent"] is None
        # Client should NOT have been called
        mock_client.send_command_with_response.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_allow_destructive_with_confirm(self, mock_get_client):
        """Test that destructive commands pass with confirm_destructive=True."""
        import json

        from src.server import send_raw_command

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await send_raw_command("store cue 1", confirm_destructive=True)
        data = json.loads(result)

        assert data["blocked"] is False
        assert data["command_sent"] == "store cue 1"
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    async def test_block_command_injection(self):
        """Test that commands with line breaks are rejected."""
        import json

        from src.server import send_raw_command

        result = await send_raw_command("list\r\ndelete cue 1")
        data = json.loads(result)

        assert data["blocked"] is True
        assert "line breaks" in data["error"]
        assert data["command_sent"] is None

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_safe_read_always_allowed(self, mock_get_client):
        """Test that SAFE_READ commands (list, info, cd) are always allowed."""
        import json

        from src.server import send_raw_command

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[Fixture]>")
        mock_get_client.return_value = mock_client

        result = await send_raw_command("list")
        data = json.loads(result)

        assert data["blocked"] is False
        assert data["risk_tier"] == "SAFE_READ"


class TestErrorHandling:
    """Tests for the _handle_errors decorator on MCP tools."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_connection_error_returns_json(self, mock_get_client):
        """Test that ConnectionError is caught and returned as JSON."""
        from src.server import set_intensity

        mock_get_client.side_effect = ConnectionError("Unable to connect to 127.0.0.1:30000")

        result = await set_intensity(target_type="fixture", target_id=1, level=50)
        data = json.loads(result)

        assert "error" in data
        assert "Connection failed" in data["error"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_runtime_error_returns_json(self, mock_get_client):
        """Test that RuntimeError (e.g. dropped connection) is caught."""
        from src.server import get_object_info

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=RuntimeError("Connection not established")
        )
        mock_get_client.return_value = mock_client

        result = await get_object_info(object_type="group", object_id=3)
        data = json.loads(result)

        assert "error" in data
        assert "Runtime error" in data["error"]


class TestSetIntensityTool:
    """Tests for the set_intensity MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fixture_at_50(self, mock_get_client):
        """Test setting a single fixture to 50%."""
        from src.server import set_intensity

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_intensity(target_type="fixture", target_id=1, level=50)
        data = json.loads(result)

        assert data["command_sent"] == "fixture 1 at 50"
        mock_client.send_command_with_response.assert_called_once_with("fixture 1 at 50")

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_group_at_full(self, mock_get_client):
        """Test setting a group to full."""
        from src.server import set_intensity

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_intensity(target_type="group", target_id=3, level=100)
        data = json.loads(result)

        assert data["command_sent"] == "group 3 at 100"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_channel_range(self, mock_get_client):
        """Test setting a channel range."""
        from src.server import set_intensity

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_intensity(
            target_type="channel", target_id=1, level=75, end_id=10
        )
        data = json.loads(result)

        assert data["command_sent"] == "channel 1 thru 10 at 75"

    @pytest.mark.asyncio
    async def test_invalid_target_type(self):
        """Test that an invalid target type returns an error."""
        from src.server import set_intensity

        result = await set_intensity(target_type="lamp", target_id=1, level=50)
        data = json.loads(result)

        assert "error" in data
        assert "lamp" in data["error"]


class TestApplyPresetTool:
    """Tests for the apply_preset MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_apply_color_preset(self, mock_get_client):
        """Test applying a color preset to current selection."""
        from src.server import apply_preset

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await apply_preset(preset_type="color", preset_id=3)
        data = json.loads(result)

        assert data["commands_sent"] == ["call preset 4.3"]
        mock_client.send_command_with_response.assert_called_once_with("call preset 4.3")

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_apply_preset_with_group(self, mock_get_client):
        """Test applying a preset after selecting a group."""
        from src.server import apply_preset

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await apply_preset(preset_type="position", preset_id=1, group_id=2)
        data = json.loads(result)

        calls = mock_client.send_command_with_response.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "group 2"
        assert calls[1][0][0] == "call preset 2.1"
        assert data["commands_sent"] == ["group 2", "call preset 2.1"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_apply_preset_with_fixture_range(self, mock_get_client):
        """Test applying a preset after selecting a fixture range."""
        from src.server import apply_preset

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await apply_preset(
            preset_type="gobo", preset_id=5, fixture_id=1, fixture_end=10
        )
        json.loads(result)

        calls = mock_client.send_command_with_response.call_args_list
        assert calls[0][0][0] == "selfix fixture 1 thru 10"
        assert calls[1][0][0] == "call preset 3.5"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_apply_preset_numeric_type(self, mock_get_client):
        """Test applying a preset using numeric type string."""
        from src.server import apply_preset

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await apply_preset(preset_type="4", preset_id=2)
        data = json.loads(result)

        assert data["commands_sent"] == ["call preset 4.2"]


class TestStoreCueTool:
    """Tests for the store_current_cue MCP tool."""

    @pytest.mark.asyncio
    async def test_store_cue_blocked_without_confirm(self):
        """confirm_destructive gate blocks without the flag."""
        from src.server import store_current_cue
        result = await store_current_cue(cue_number=5)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_basic_cue(self, mock_get_client):
        """Test storing a simple cue."""
        from src.server import store_current_cue

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await store_current_cue(cue_number=5, confirm_destructive=True)
        data = json.loads(result)

        assert data["commands_sent"] == ["store cue 5"]
        mock_client.send_command_with_response.assert_called_once_with("store cue 5")

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_cue_with_sequence(self, mock_get_client):
        """Test storing a cue into a specific sequence."""
        from src.server import store_current_cue

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await store_current_cue(cue_number=3, sequence_id=2, confirm_destructive=True)
        data = json.loads(result)

        assert data["commands_sent"] == ["store cue 3 sequence 2"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_cue_with_label(self, mock_get_client):
        """Test storing a cue with a label."""
        from src.server import store_current_cue

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await store_current_cue(cue_number=3, label="Opening Look", confirm_destructive=True)
        json.loads(result)

        calls = mock_client.send_command_with_response.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "store cue 3"
        assert calls[1][0][0] == 'label cue 3 "Opening Look"'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_cue_merge(self, mock_get_client):
        """Test storing a cue with merge option."""
        from src.server import store_current_cue

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await store_current_cue(cue_number=1, merge=True, confirm_destructive=True)
        data = json.loads(result)

        assert data["commands_sent"] == ["store cue 1 /merge"]


class TestGetObjectInfoTool:
    """Tests for the get_object_info MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_info_group(self, mock_get_client):
        """Test querying info on a group."""
        from src.server import get_object_info

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Group 3 info")
        mock_get_client.return_value = mock_client

        result = await get_object_info(object_type="group", object_id=3)
        data = json.loads(result)

        assert data["command_sent"] == "info group 3"
        assert data["raw_response"] == "Group 3 info"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_info_preset_dot_notation(self, mock_get_client):
        """Test querying info on a preset with dot notation."""
        from src.server import get_object_info

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Preset info")
        mock_get_client.return_value = mock_client

        result = await get_object_info(object_type="preset", object_id="2.1")
        data = json.loads(result)

        assert data["command_sent"] == "info preset 2.1"


class TestClearProgrammerTool:
    """Tests for the clear_programmer MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_clear_all(self, mock_get_client):
        """Test clearing entire programmer."""
        from src.server import clear_programmer

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await clear_programmer(mode="all")
        data = json.loads(result)

        assert data["command_sent"] == "clearall"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_clear_selection(self, mock_get_client):
        """Test clearing selection only."""
        from src.server import clear_programmer

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await clear_programmer(mode="selection")
        data = json.loads(result)

        assert data["command_sent"] == "clearselection"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_clear_active(self, mock_get_client):
        """Test clearing active values only."""
        from src.server import clear_programmer

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await clear_programmer(mode="active")
        data = json.loads(result)

        assert data["command_sent"] == "clearactive"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_clear_sequential(self, mock_get_client):
        """Test sequential clear mode."""
        from src.server import clear_programmer

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await clear_programmer(mode="clear")
        data = json.loads(result)

        assert data["command_sent"] == "clear"

    @pytest.mark.asyncio
    async def test_clear_invalid_mode(self):
        """Test that an invalid mode returns an error."""
        from src.server import clear_programmer

        result = await clear_programmer(mode="invalid")
        data = json.loads(result)

        assert "error" in data
        assert "invalid" in data["error"]


class TestSetNodePropertyTool:
    """Tests for the set_node_property MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.set_property")
    @patch("src.server.get_client")
    async def test_set_property_basic(self, mock_get_client, mock_set_property):
        """Test setting a property on a node."""
        from src.navigation import SetPropertyResult
        from src.server import set_node_property

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_set_property.return_value = SetPropertyResult(
            path="3.1",
            commands_sent=["cd /", "cd 3", 'assign 1/Telnet="Login Disabled"', "cd /"],
            raw_responses=["[Root]>", "[Settings]>", "Ok", "[Root]>"],
            success=True,
            verified_value="Login Disabled",
        )

        result = await set_node_property(
            path="3.1", property_name="Telnet", value="Login Disabled", confirm_destructive=True
        )
        data = json.loads(result)

        assert data["success"] is True
        assert data["verified_value"] == "Login Disabled"
        assert data["property_name"] == "Telnet"
        assert data["path"] == "3.1"
        mock_set_property.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.server.set_property")
    @patch("src.server.get_client")
    async def test_set_property_failure(self, mock_get_client, mock_set_property):
        """Test property set that fails verification."""
        from src.navigation import SetPropertyResult
        from src.server import set_node_property

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_set_property.return_value = SetPropertyResult(
            path="3.1",
            commands_sent=["cd /", "cd 3", 'assign 1/Telnet="Bad"', "cd /"],
            raw_responses=["[Root]>", "[Settings]>", "Error", "[Root]>"],
            success=False,
            error="Verification failed",
        )

        result = await set_node_property(
            path="3.1", property_name="Telnet", value="Bad", confirm_destructive=True
        )
        data = json.loads(result)

        assert data["success"] is False
        assert data["error"] == "Verification failed"


class TestSetAttributeTool:
    """Tests for the set_attribute MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_set_pan(self, mock_get_client):
        """Test setting Pan attribute."""
        from src.server import set_attribute

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_attribute(attribute_name="Pan", value=120)
        data = json.loads(result)

        assert data["commands_sent"] == ['attribute "Pan" at 120']

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_set_attribute_with_group(self, mock_get_client):
        """Test setting attribute after selecting a group."""
        from src.server import set_attribute

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_attribute(attribute_name="Tilt", value=50, group_id=2)
        json.loads(result)

        calls = mock_client.send_command_with_response.call_args_list
        assert calls[0][0][0] == "group 2"
        assert calls[1][0][0] == 'attribute "Tilt" at 50'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_set_attribute_with_fixture_range(self, mock_get_client):
        """Test setting attribute after selecting fixtures."""
        from src.server import set_attribute

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_attribute(
            attribute_name="Zoom", value=80, fixture_id=1, fixture_end=10
        )
        json.loads(result)

        calls = mock_client.send_command_with_response.call_args_list
        assert calls[0][0][0] == "selfix fixture 1 thru 10"
        assert calls[1][0][0] == 'attribute "Zoom" at 80'


class TestParkFixtureTool:
    """Tests for the park_fixture and unpark_fixture MCP tools."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_park_fixture(self, mock_get_client):
        """Test parking a fixture."""
        from src.server import park_fixture

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await park_fixture(target="fixture 1")
        data = json.loads(result)

        assert data["command_sent"] == "park fixture 1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_park_dmx_with_value(self, mock_get_client):
        """Test parking DMX at a specific value."""
        from src.server import park_fixture

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await park_fixture(target="dmx 101", value=128)
        data = json.loads(result)

        assert data["command_sent"] == "park dmx 101 at 128"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_unpark_fixture(self, mock_get_client):
        """Test unparking a fixture."""
        from src.server import unpark_fixture

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await unpark_fixture(target="fixture 1")
        data = json.loads(result)

        assert data["command_sent"] == "unpark fixture 1"


class TestRunMacroTool:
    """Tests for the run_macro MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_run_macro(self, mock_get_client):
        """Test executing a macro."""
        from src.server import run_macro

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await run_macro(macro_id=1)
        data = json.loads(result)

        assert data["command_sent"] == "go macro 1"


class TestDeleteObjectTool:
    """Tests for the delete_object MCP tool."""

    @pytest.mark.asyncio
    async def test_delete_blocked_without_confirm(self):
        """Test that delete is blocked without confirmation."""
        from src.server import delete_object

        result = await delete_object(object_type="cue", object_id=5)
        data = json.loads(result)

        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["error"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_delete_cue_with_confirm(self, mock_get_client):
        """Test deleting a cue with confirmation."""
        from src.server import delete_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await delete_object(
            object_type="cue", object_id=5, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["blocked"] is False
        assert data["command_sent"] == "delete cue 5 /noconfirm"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_delete_group_with_confirm(self, mock_get_client):
        """Test deleting a generic object type."""
        from src.server import delete_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await delete_object(
            object_type="group", object_id=3, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["blocked"] is False
        assert "delete group 3" in data["command_sent"]


class TestCopyOrMoveObjectTool:
    """Tests for the copy_or_move_object MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_copy_group(self, mock_get_client):
        """Test copying a group."""
        from src.server import copy_or_move_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await copy_or_move_object(
            action="copy", object_type="group", source_id=1, target_id=5, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["command_sent"] == "copy group 1 at 5"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_move_macro(self, mock_get_client):
        """Test moving a macro."""
        from src.server import copy_or_move_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await copy_or_move_object(
            action="move", object_type="macro", source_id=3, target_id=10, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["command_sent"] == "move macro 3 at 10"

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        """Test that invalid action returns error."""
        from src.server import copy_or_move_object

        result = await copy_or_move_object(
            action="cut", object_type="group", source_id=1, target_id=5, confirm_destructive=True
        )
        data = json.loads(result)

        assert "error" in data


class TestStoreNewPresetTool:
    """Tests for the store_new_preset MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_color_preset(self, mock_get_client):
        """Test storing a color preset."""
        from src.server import store_new_preset

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await store_new_preset(preset_type="color", preset_id=5, confirm_destructive=True)
        data = json.loads(result)

        assert data["command_sent"] == "store preset 4.5"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_preset_with_merge(self, mock_get_client):
        """Test storing a preset with merge option."""
        from src.server import store_new_preset

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await store_new_preset(
            preset_type="position", preset_id=3, merge=True, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["command_sent"] == "store preset 2.3 /merge"

    @pytest.mark.asyncio
    async def test_store_preset_requires_confirm_destructive(self):
        """Test that store_new_preset blocks without confirm_destructive=True."""
        from src.server import store_new_preset

        result = await store_new_preset(preset_type="color", preset_id=5)
        data = json.loads(result)

        assert "error" in data


class TestNavigateConsoleTool:
    """Tests for the navigate_console MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.navigate")
    @patch("src.server.get_client")
    async def test_navigate_to_root(self, mock_get_client, mock_navigate):
        """Test navigating to root."""
        from src.prompt_parser import ConsolePrompt
        from src.server import navigate_console

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_result = MagicMock()
        mock_result.command_sent = "cd /"
        mock_result.raw_response = "[Root]>"
        mock_result.success = True
        mock_result.parsed_prompt = ConsolePrompt(
            raw_response="[Root]>",
            prompt_line="[Root]>",
            location="Root",
            object_type="Root",
            object_id=None,
        )
        mock_navigate.return_value = mock_result

        result = await navigate_console(destination="/")
        data = json.loads(result)

        assert data["command_sent"] == "cd /"
        assert data["success"] is True
        assert data["parsed_prompt"]["location"] == "Root"

    @pytest.mark.asyncio
    @patch("src.server.navigate")
    @patch("src.server.get_client")
    async def test_navigate_with_object_id(self, mock_get_client, mock_navigate):
        """Test navigating with dot notation."""
        from src.prompt_parser import ConsolePrompt
        from src.server import navigate_console

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_result = MagicMock()
        mock_result.command_sent = "cd Group.1"
        mock_result.raw_response = "[Group 1]>"
        mock_result.success = True
        mock_result.parsed_prompt = ConsolePrompt(
            raw_response="[Group 1]>",
            prompt_line="[Group 1]>",
            location="Group 1",
            object_type="Group",
            object_id="1",
        )
        mock_navigate.return_value = mock_result

        result = await navigate_console(destination="Group", object_id=1)
        data = json.loads(result)

        assert data["success"] is True
        assert data["parsed_prompt"]["object_type"] == "Group"
        assert data["parsed_prompt"]["object_id"] == "1"


class TestGetConsoleLocationTool:
    """Tests for the get_console_location MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_current_location")
    @patch("src.server.get_client")
    async def test_get_location(self, mock_get_client, mock_get_location):
        """Test querying current location."""
        from src.prompt_parser import ConsolePrompt
        from src.server import get_console_location

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_result = MagicMock()
        mock_result.command_sent = ""
        mock_result.raw_response = "[channel]>"
        mock_result.success = True
        mock_result.parsed_prompt = ConsolePrompt(
            raw_response="[channel]>",
            prompt_line="[channel]>",
            location="channel",
            object_type="channel",
            object_id=None,
        )
        mock_get_location.return_value = mock_result

        result = await get_console_location()
        data = json.loads(result)

        assert data["success"] is True
        assert data["parsed_prompt"]["location"] == "channel"


class TestListConsoleDestinationTool:
    """Tests for the list_console_destination MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.get_client")
    async def test_list_destination(self, mock_get_client, mock_list_dest):
        """Test listing objects at current destination."""
        from src.prompt_parser import ListEntry, ListOutput
        from src.server import list_console_destination

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_result = MagicMock()
        mock_result.command_sent = "list"
        mock_result.raw_response = "Group.1  Front Wash\nGroup.2  Back"
        mock_result.parsed_list = ListOutput(
            raw_response="Group.1  Front Wash\nGroup.2  Back",
            entries=(
                ListEntry(object_type="Group", object_id="1", name="Front Wash"),
                ListEntry(object_type="Group", object_id="2", name="Back"),
            ),
        )
        mock_list_dest.return_value = mock_result

        result = await list_console_destination()
        data = json.loads(result)

        assert data["entry_count"] == 2
        assert data["entries"][0]["object_type"] == "Group"
        assert data["entries"][0]["name"] == "Front Wash"
        assert data["entries"][1]["object_id"] == "2"


# ============================================================
# New Composite Tool Tests
# ============================================================


class TestQueryObjectListTool:
    """Tests for the query_object_list MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_cue(self, mock_get_client):
        """Test listing cues."""
        from src.server import query_object_list

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Cue 1\nCue 2")
        mock_get_client.return_value = mock_client

        result = await query_object_list(object_type="cue")
        data = json.loads(result)

        assert data["command_sent"] == "list cue"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_cue_with_sequence(self, mock_get_client):
        """Test listing cues in a specific sequence."""
        from src.server import query_object_list

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Cue list")
        mock_get_client.return_value = mock_client

        result = await query_object_list(object_type="cue", sequence_id=2)
        data = json.loads(result)

        assert "sequence 2" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_group(self, mock_get_client):
        """Test listing groups."""
        from src.server import query_object_list

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Group list")
        mock_get_client.return_value = mock_client

        result = await query_object_list(object_type="group")
        data = json.loads(result)

        assert data["command_sent"] == "list group"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_preset(self, mock_get_client):
        """Test listing presets by type."""
        from src.server import query_object_list

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Preset list")
        mock_get_client.return_value = mock_client

        result = await query_object_list(object_type="preset", preset_type="color")
        data = json.loads(result)

        assert "preset" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_attribute(self, mock_get_client):
        """Test listing attributes."""
        from src.server import query_object_list

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Attr list")
        mock_get_client.return_value = mock_client

        result = await query_object_list(object_type="attribute")
        data = json.loads(result)

        assert data["command_sent"] == "list attribute"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_messages(self, mock_get_client):
        """Test listing messages."""
        from src.server import query_object_list

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Messages")
        mock_get_client.return_value = mock_client

        result = await query_object_list(object_type="messages")
        data = json.loads(result)

        assert data["command_sent"] == "list messages"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_generic(self, mock_get_client):
        """Test listing a generic object type."""
        from src.server import query_object_list

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Seq list")
        mock_get_client.return_value = mock_client

        result = await query_object_list(object_type="sequence")
        data = json.loads(result)

        assert data["command_sent"] == "list sequence"


class TestListSystemVariablesTool:
    """Tests for the list_system_variables MCP tool."""

    # Real format from grandMA2 telnet: "$Global : $VARNAME = VALUE"
    LISTVAR_RESPONSE = (
        "$Global : $VERSION = 3.9.60.65\r\n"
        "$Global : $TIME = 19h26m52.284s\r\n"
        "$Global : $SELECTEDEXEC = 1.1.1\r\n"
        "$Global : $SELECTEDEXECCUE = NONE\r\n"
        "$Global : $FADERPAGE = 1\r\n"
        " [Channel]>\r\n"
    )

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_parses_key_value_pairs(self, mock_get_client):
        from src.server import list_system_variables

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=self.LISTVAR_RESPONSE)
        mock_get_client.return_value = mock_client

        result = await list_system_variables()
        data = json.loads(result)

        assert data["variable_count"] == 5
        assert data["variables"]["$VERSION"] == "3.9.60.65"
        assert data["variables"]["$TIME"] == "19h26m52.284s"
        assert data["variables"]["$FADERPAGE"] == "1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_filter_prefix(self, mock_get_client):
        from src.server import list_system_variables

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=self.LISTVAR_RESPONSE)
        mock_get_client.return_value = mock_client

        result = await list_system_variables(filter_prefix="SELECTED")
        data = json.loads(result)

        assert all("SELECTED" in k.upper() for k in data["variables"])
        assert "$TIME" not in data["variables"]
        assert data["variable_count"] == 2

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_strips_scope_prefix(self, mock_get_client):
        from src.server import list_system_variables

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="$Global : $HOSTNAME = console1\r\n [Channel]>\r\n"
        )
        mock_get_client.return_value = mock_client

        result = await list_system_variables()
        data = json.loads(result)

        assert "$HOSTNAME" in data["variables"]
        assert data["variables"]["$HOSTNAME"] == "console1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_empty_response(self, mock_get_client):
        from src.server import list_system_variables

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=" [Channel]>\r\n")
        mock_get_client.return_value = mock_client

        result = await list_system_variables()
        data = json.loads(result)

        assert data["variable_count"] == 0
        assert data["variables"] == {}


class TestGetVariableEchoAction:
    """Tests for get_variable with action='echo' (system variable reads via ListVar)."""

    LISTVAR_RESPONSE = (
        "$Global : $VERSION = 3.9.60.65\r\n"
        "$Global : $TIME = 19h26m52.284s\r\n"
        "$Global : $FADERPAGE = 1\r\n"
        " [Channel]>\r\n"
    )

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_echo_no_dollar(self, mock_get_client):
        from src.server import get_variable

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=self.LISTVAR_RESPONSE)
        mock_get_client.return_value = mock_client

        result = await get_variable(action="echo", var_name="VERSION")
        data = json.loads(result)

        assert data["command_sent"] == "ListVar"
        assert data["variable"] == "$VERSION"
        assert data["value"] == "3.9.60.65"
        assert data["found"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_echo_strips_dollar(self, mock_get_client):
        from src.server import get_variable

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value=self.LISTVAR_RESPONSE)
        mock_get_client.return_value = mock_client

        result = await get_variable(action="echo", var_name="$TIME")
        data = json.loads(result)

        assert data["variable"] == "$TIME"
        assert data["value"] == "19h26m52.284s"
        assert data["found"] is True

    @pytest.mark.asyncio
    async def test_echo_blocked_without_var_name(self):
        from src.server import get_variable

        result = await get_variable(action="echo")
        data = json.loads(result)
        assert data["blocked"] is True


class TestPlaybackActionTool:
    """Tests for the playback_action MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_go_executor(self, mock_get_client):
        """Test go on executor."""
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(
            action="go", object_type="executor", object_id=1
        )
        data = json.loads(result)

        assert "go" in data["command_sent"].lower()
        assert "executor" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_go_back(self, mock_get_client):
        """Test go back."""
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(action="go_back")
        data = json.loads(result)

        assert "goback" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_goto_cue(self, mock_get_client):
        """Test goto specific cue."""
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(action="goto", cue_id=5)
        data = json.loads(result)

        assert "goto" in data["command_sent"].lower()
        assert "5" in data["command_sent"]

    @pytest.mark.asyncio
    async def test_goto_without_cue_id(self):
        """Test that goto requires cue_id."""
        from src.server import playback_action

        result = await playback_action(action="goto")
        data = json.loads(result)

        assert "error" in data
        assert "cue_id" in data["error"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fast_forward(self, mock_get_client):
        """Test fast forward."""
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(action="fast_forward")
        data = json.loads(result)

        assert data["command_sent"] == ">>>"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fast_back(self, mock_get_client):
        """Test fast back."""
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(action="fast_back")
        data = json.loads(result)

        assert data["command_sent"] == "<<<"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_def_go(self, mock_get_client):
        """Test go on selected executor."""
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(action="def_go")
        data = json.loads(result)

        assert data["command_sent"] == "defgoforward"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_def_pause(self, mock_get_client):
        """Test pause selected executor."""
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(action="def_pause")
        data = json.loads(result)

        assert data["command_sent"] == "defgopause"

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        """Test that an invalid action returns an error."""
        from src.server import playback_action

        result = await playback_action(action="rewind")
        data = json.loads(result)

        assert "error" in data
        assert "rewind" in data["error"]


class TestManageVariableTool:
    """Tests for the manage_variable MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_set_global_var(self, mock_get_client):
        """Test setting a global variable."""
        from src.server import manage_variable

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await manage_variable(
            action="set", scope="global", var_name="myvar", value=42
        )
        data = json.loads(result)

        assert data["command_sent"] == "setvar $myvar = 42"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_set_user_var(self, mock_get_client):
        """Test setting a user variable."""
        from src.server import manage_variable

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await manage_variable(
            action="set", scope="user", var_name="speed", value=100
        )
        data = json.loads(result)

        assert data["command_sent"] == "setuservar $speed = 100"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_add_global_var(self, mock_get_client):
        """Test adding to a global variable."""
        from src.server import manage_variable

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await manage_variable(
            action="add", scope="global", var_name="counter", value=1
        )
        data = json.loads(result)

        assert data["command_sent"] == "addvar $counter = 1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_add_user_var(self, mock_get_client):
        """Test adding to a user variable."""
        from src.server import manage_variable

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await manage_variable(
            action="add", scope="user", var_name="counter", value=1
        )
        data = json.loads(result)

        assert data["command_sent"] == "adduservar $counter = 1"

    @pytest.mark.asyncio
    async def test_add_without_value(self):
        """Test that add without value returns error."""
        from src.server import manage_variable

        result = await manage_variable(
            action="add", scope="global", var_name="counter"
        )
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        """Test that invalid action returns error."""
        from src.server import manage_variable

        result = await manage_variable(
            action="multiply", scope="global", var_name="x", value=2
        )
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_scope(self):
        """Test that invalid scope returns error."""
        from src.server import manage_variable

        result = await manage_variable(
            action="set", scope="session", var_name="x", value=1
        )
        data = json.loads(result)

        assert "error" in data


class TestLabelOrAppearanceTool:
    """Tests for the label_or_appearance MCP tool."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        """Test that label/appearance is blocked without confirmation."""
        from src.server import label_or_appearance

        result = await label_or_appearance(
            action="label", object_type="group", object_id=3, name="Test"
        )
        data = json.loads(result)

        assert data["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_label_group(self, mock_get_client):
        """Test labeling a group."""
        from src.server import label_or_appearance

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await label_or_appearance(
            action="label", object_type="group", object_id=3,
            name="Front Wash", confirm_destructive=True
        )
        data = json.loads(result)

        assert data["command_sent"] == 'label group 3 "Front Wash"'
        assert data["blocked"] is False

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_label_preset(self, mock_get_client):
        """Test labeling a preset with preset_type."""
        from src.server import label_or_appearance

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await label_or_appearance(
            action="label", object_type="preset", object_id=1,
            preset_type="color", name="Red", confirm_destructive=True
        )
        data = json.loads(result)

        assert "preset" in data["command_sent"].lower()
        assert "Red" in data["command_sent"]

    @pytest.mark.asyncio
    async def test_label_without_name(self):
        """Test that label without name returns error."""
        from src.server import label_or_appearance

        result = await label_or_appearance(
            action="label", object_type="group", object_id=3,
            confirm_destructive=True
        )
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_appearance_with_color(self, mock_get_client):
        """Test setting appearance with hex color."""
        from src.server import label_or_appearance

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await label_or_appearance(
            action="appearance", object_type="group", object_id=1,
            color="FF0000", confirm_destructive=True
        )
        data = json.loads(result)

        assert "appearance" in data["command_sent"].lower()
        assert "FF0000" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_appearance_with_rgb(self, mock_get_client):
        """Test setting appearance with RGB components."""
        from src.server import label_or_appearance

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await label_or_appearance(
            action="appearance", object_type="group", object_id=1,
            red=100, green=0, blue=0, confirm_destructive=True
        )
        data = json.loads(result)

        assert "appearance" in data["command_sent"].lower()
        assert "/r=100" in data["command_sent"]


class TestAssignObjectTool:
    """Tests for the assign_object MCP tool."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        """Test that assign is blocked without confirmation."""
        from src.server import assign_object

        result = await assign_object(
            mode="assign", source_type="sequence", source_id=1,
            target_type="executor", target_id=6
        )
        data = json.loads(result)

        assert data["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_sequence_to_executor(self, mock_get_client):
        """Test assigning a sequence to an executor."""
        from src.server import assign_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await assign_object(
            mode="assign", source_type="sequence", source_id=1,
            target_type="executor", target_id=6, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["blocked"] is False
        assert "assign" in data["command_sent"].lower()
        assert "sequence" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_function(self, mock_get_client):
        """Test assigning a function to an executor."""
        from src.server import assign_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await assign_object(
            mode="function", function="Toggle",
            target_type="executor", target_id=101, confirm_destructive=True
        )
        data = json.loads(result)

        assert "toggle" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_fade(self, mock_get_client):
        """Test assigning a fade time to a cue."""
        from src.server import assign_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await assign_object(
            mode="fade", fade_time=3, cue_id=5, confirm_destructive=True
        )
        data = json.loads(result)

        assert "fade" in data["command_sent"].lower()
        assert "3" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_to_layout(self, mock_get_client):
        """Test assigning an object to a layout."""
        from src.server import assign_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await assign_object(
            mode="layout", source_type="group", source_id=1,
            layout_id=1, x=5, y=2, confirm_destructive=True
        )
        data = json.loads(result)

        assert "layout" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_empty(self, mock_get_client):
        """Test emptying an executor."""
        from src.server import assign_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await assign_object(
            mode="empty", target_type="executor", target_id=1,
            confirm_destructive=True
        )
        data = json.loads(result)

        assert "empty" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_temp_fader(self, mock_get_client):
        """Test assigning temp fader to an executor."""
        from src.server import assign_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await assign_object(
            mode="temp_fader", target_type="executor", target_id=1,
            confirm_destructive=True
        )
        data = json.loads(result)

        assert "tempfader" in data["command_sent"].lower()

    @pytest.mark.asyncio
    async def test_assign_missing_source(self):
        """Test that assign mode without source returns error."""
        from src.server import assign_object

        result = await assign_object(
            mode="assign", target_type="executor", target_id=1,
            confirm_destructive=True
        )
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_mode(self):
        """Test that invalid mode returns error."""
        from src.server import assign_object

        result = await assign_object(
            mode="patch", confirm_destructive=True
        )
        data = json.loads(result)

        assert "error" in data


class TestEditObjectTool:
    """Tests for the edit_object MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_edit_cue(self, mock_get_client):
        """Test editing a cue (SAFE_WRITE, no confirm needed)."""
        from src.server import edit_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[Edit Cue]>")
        mock_get_client.return_value = mock_client

        result = await edit_object(action="edit", object_type="cue", object_id=1)
        data = json.loads(result)

        assert data["command_sent"] == "edit cue 1"

    @pytest.mark.asyncio
    async def test_cut_blocked_without_confirm(self):
        """Test that cut is blocked without confirmation."""
        from src.server import edit_object

        result = await edit_object(
            action="cut", object_type="preset", object_id="4.1"
        )
        data = json.loads(result)

        assert data["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_cut_with_confirm(self, mock_get_client):
        """Test cutting an object with confirmation."""
        from src.server import edit_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await edit_object(
            action="cut", object_type="preset", object_id="4.1",
            confirm_destructive=True
        )
        data = json.loads(result)

        assert data["command_sent"] == "cut preset 4.1"
        assert data["blocked"] is False

    @pytest.mark.asyncio
    async def test_paste_blocked_without_confirm(self):
        """Test that paste is blocked without confirmation."""
        from src.server import edit_object

        result = await edit_object(
            action="paste", object_type="group", target_id=5
        )
        data = json.loads(result)

        assert data["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_paste_with_confirm(self, mock_get_client):
        """Test pasting with confirmation."""
        from src.server import edit_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await edit_object(
            action="paste", object_type="group", target_id=5,
            confirm_destructive=True
        )
        data = json.loads(result)

        assert "paste" in data["command_sent"].lower()

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        """Test that invalid action returns error."""
        from src.server import edit_object

        result = await edit_object(action="merge", confirm_destructive=True)
        data = json.loads(result)

        assert "error" in data


class TestRemoveContentTool:
    """Tests for the remove_content MCP tool."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        """Test that remove is blocked without confirmation."""
        from src.server import remove_content

        result = await remove_content(object_type="selection")
        data = json.loads(result)

        assert data["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_remove_selection(self, mock_get_client):
        """Test removing selection."""
        from src.server import remove_content

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await remove_content(
            object_type="selection", confirm_destructive=True
        )
        data = json.loads(result)

        assert data["command_sent"] == "remove selection"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_remove_fixture(self, mock_get_client):
        """Test removing a fixture."""
        from src.server import remove_content

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await remove_content(
            object_type="fixture", object_id=1, confirm_destructive=True
        )
        data = json.loads(result)

        assert "remove" in data["command_sent"].lower()
        assert "fixture" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_remove_fixture_with_filter(self, mock_get_client):
        """Test removing a fixture with if_filter."""
        from src.server import remove_content

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await remove_content(
            object_type="fixture", object_id=1,
            if_filter="PresetType 1", confirm_destructive=True
        )
        data = json.loads(result)

        assert "if PresetType 1" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_remove_effect(self, mock_get_client):
        """Test removing an effect."""
        from src.server import remove_content

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await remove_content(
            object_type="effect", object_id=1, confirm_destructive=True
        )
        data = json.loads(result)

        assert "remove" in data["command_sent"].lower()
        assert "effect" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_remove_preset_type(self, mock_get_client):
        """Test removing a preset type."""
        from src.server import remove_content

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await remove_content(
            object_type="presettype", object_id="position",
            confirm_destructive=True
        )
        data = json.loads(result)

        assert "remove" in data["command_sent"].lower()
        assert "presettype" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_remove_generic(self, mock_get_client):
        """Test generic remove."""
        from src.server import remove_content

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await remove_content(
            object_type="cue", object_id=1, confirm_destructive=True
        )
        data = json.loads(result)

        assert "remove" in data["command_sent"].lower()


class TestStoreObjectTool:
    """Tests for the store_object MCP tool."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        """Test that store is blocked without confirmation."""
        from src.server import store_object

        result = await store_object(object_type="macro", object_id=5)
        data = json.loads(result)

        assert data["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_macro(self, mock_get_client):
        """Test storing a macro."""
        from src.server import store_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await store_object(
            object_type="macro", object_id=5, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["command_sent"] == "store macro 5"
        assert data["blocked"] is False

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_with_name(self, mock_get_client):
        """Test storing with a name."""
        from src.server import store_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await store_object(
            object_type="effect", object_id=1, name="Rainbow",
            confirm_destructive=True
        )
        data = json.loads(result)

        assert "effect" in data["command_sent"].lower()
        assert "Rainbow" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_with_merge(self, mock_get_client):
        """Test storing with merge option."""
        from src.server import store_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await store_object(
            object_type="sequence", object_id=3, merge=True,
            confirm_destructive=True
        )
        data = json.loads(result)

        assert "/merge" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_with_overwrite(self, mock_get_client):
        """Test storing with overwrite option."""
        from src.server import store_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await store_object(
            object_type="sequence", object_id=3, overwrite=True,
            confirm_destructive=True
        )
        data = json.loads(result)

        assert "/overwrite" in data["command_sent"]


class TestSearchCodebaseTool:
    """Tests for the search_codebase MCP tool (tool #29)."""

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists", return_value=False)
    async def test_missing_db_returns_error(self, _mock_exists):
        """Returns an error JSON when the RAG index has not been built."""
        from src.server import search_codebase

        result = await search_codebase(query="navigate")
        data = json.loads(result)

        assert "error" in data
        assert "rag_ingest" in data["error"]

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists", return_value=True)
    @patch("rag.retrieve.query.rag_query")
    async def test_text_search_returns_hits(self, mock_rag_query, _mock_exists):
        """Returns formatted hits from the RAG index using text search."""
        from rag.types import RagHit
        from src.server import search_codebase

        mock_rag_query.return_value = [
            RagHit(
                chunk_id="c1", path="src/navigation.py", kind="source",
                start_line=1, end_line=15, score=1.0, text="def navigate(): ..."
            )
        ]

        result = await search_codebase(query="navigate", top_k=5)
        hits = json.loads(result)

        assert len(hits) == 1
        assert hits[0]["path"] == "src/navigation.py"
        assert hits[0]["kind"] == "source"
        assert hits[0]["lines"] == "1-15"
        assert hits[0]["score"] == 1.0
        assert "navigate" in hits[0]["text"]

    @pytest.mark.asyncio
    @patch("pathlib.Path.exists", return_value=True)
    @patch("rag.retrieve.query.rag_query")
    async def test_kind_filter(self, mock_rag_query, _mock_exists):
        """Filters results to the requested kind."""
        from rag.types import RagHit
        from src.server import search_codebase

        mock_rag_query.return_value = [
            RagHit(chunk_id="c1", path="src/nav.py", kind="source",
                   start_line=1, end_line=5, score=1.0, text="source chunk"),
            RagHit(chunk_id="c2", path="tests/test_nav.py", kind="test",
                   start_line=1, end_line=5, score=1.0, text="test chunk"),
        ]

        result = await search_codebase(query="navigate", kind="source")
        hits = json.loads(result)

        assert len(hits) == 1
        assert hits[0]["kind"] == "source"


# ============================================================
# Tests for New Tools 30–44
# ============================================================


class TestSetExecutorLevelTool:
    """Tests for the set_executor_level MCP tool (tool #30)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_set_executor_level_basic(self, mock_get_client):
        """Test setting executor level to a valid value."""
        from src.server import set_executor_level

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_executor_level(executor_id=1, level=75.0)
        data = json.loads(result)

        assert "command_sent" in data
        assert data["risk_tier"] == "SAFE_WRITE"
        mock_client.send_command_with_response.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_set_executor_level_with_page(self, mock_get_client):
        """Test setting executor level with page qualifier."""
        from src.server import set_executor_level

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_executor_level(executor_id=5, level=50.0, page=2)
        data = json.loads(result)

        assert "2" in data["command_sent"]
        assert "5" in data["command_sent"]

    @pytest.mark.asyncio
    async def test_set_executor_level_invalid_level_high(self):
        """Test that level > 100 returns an error."""
        from src.server import set_executor_level

        result = await set_executor_level(executor_id=1, level=101.0)
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_set_executor_level_invalid_level_negative(self):
        """Test that level < 0 returns an error."""
        from src.server import set_executor_level

        result = await set_executor_level(executor_id=1, level=-1.0)
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_set_executor_level_invalid_executor_id(self):
        """Test that executor_id < 1 returns an error."""
        from src.server import set_executor_level

        result = await set_executor_level(executor_id=0, level=50.0)
        data = json.loads(result)

        assert "error" in data


class TestNavigatePageTool:
    """Tests for the navigate_page MCP tool (tool #31)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_navigate_page_goto(self, mock_get_client):
        """Test navigating to an absolute page."""
        from src.server import navigate_page

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await navigate_page(action="goto", page_number=3)
        data = json.loads(result)

        assert data["command_sent"] == "page 3"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_navigate_page_next(self, mock_get_client):
        """Test navigating to the next page."""
        from src.server import navigate_page

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await navigate_page(action="next")
        data = json.loads(result)

        assert "page +" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_navigate_page_previous(self, mock_get_client):
        """Test navigating to the previous page."""
        from src.server import navigate_page

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await navigate_page(action="previous")
        data = json.loads(result)

        assert "page -" in data["command_sent"]

    @pytest.mark.asyncio
    async def test_navigate_page_goto_missing_page_number(self):
        """Test that goto without page_number returns an error."""
        from src.server import navigate_page

        result = await navigate_page(action="goto")
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_navigate_page_invalid_action(self):
        """Test that invalid action returns an error."""
        from src.server import navigate_page

        result = await navigate_page(action="jump")
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_navigate_page_next_with_steps(self, mock_get_client):
        """Test navigating forward by multiple steps."""
        from src.server import navigate_page

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await navigate_page(action="next", steps=3)
        data = json.loads(result)

        assert "3" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_navigate_page_create_if_missing(self, mock_get_client):
        """Test that create_if_missing sends Store Page before Page N."""
        from src.server import navigate_page

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await navigate_page(action="goto", page_number=5, create_if_missing=True)
        data = json.loads(result)

        assert data["command_sent"] == "page 5"
        assert len(data["steps"]) == 2
        assert "Store Page 5" in data["steps"][0]["command"]
        assert data["steps"][1]["command"] == "page 5"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_navigate_page_no_create_by_default(self, mock_get_client):
        """Test that create_if_missing=False sends only Page N."""
        from src.server import navigate_page

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await navigate_page(action="goto", page_number=3)
        data = json.loads(result)

        assert data["command_sent"] == "page 3"
        assert len(data["steps"]) == 1


class TestSelectFeatureTool:
    """Tests for the select_feature MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_feature_zoom(self, mock_get_client):
        """Test selecting the Zoom feature bank."""
        from src.server import select_feature

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await select_feature(feature_name="Zoom")
        data = json.loads(result)

        assert data["command_sent"] == "Feature Zoom"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_feature_color(self, mock_get_client):
        """Test selecting the Color feature bank."""
        from src.server import select_feature

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await select_feature(feature_name="Color")
        data = json.loads(result)

        assert data["command_sent"] == "Feature Color"


class TestSelectPresetTypeTool:
    """Tests for the select_preset_type MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_preset_type_by_number(self, mock_get_client):
        """Test selecting a preset type by number."""
        from src.server import select_preset_type

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await select_preset_type(preset_type=4)
        data = json.loads(result)

        assert data["command_sent"] == "PresetType 4"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_preset_type_by_name(self, mock_get_client):
        """Test selecting a preset type by name."""
        from src.server import select_preset_type

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await select_preset_type(preset_type="Color")
        data = json.loads(result)

        assert data["command_sent"] == 'PresetType "Color"'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_preset_type_control(self, mock_get_client):
        """Test selecting Control preset type (type 7, $FEATURE=MSPEED)."""
        from src.server import select_preset_type

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await select_preset_type(preset_type="CONTROL")
        data = json.loads(result)

        assert data["command_sent"] == 'PresetType "CONTROL"'


class TestBrowsePresetTypeTool:
    """Tests for the browse_preset_type MCP tool."""

    FEATURE_LIST_RAW = (
        "Executing : List\n"
        "          LibraryName  ScreenName  IdentifiedAs\n"
        "Feature 20 SHUTTER      Shutter     Beam -> Shutter   (2)\n"
        "Feature 21 BEAM1        Beam        Beam -> Beam      (4)\n"
        "LiveSetup/PresetTypes/BEAM 5 >\n"
    )
    ATTR_LIST_RAW = (
        "Executing : List\n"
        "             LibraryName   ScreenName\n"
        "Attribute 22 SHUTTER       Shutter    (9)\n"
        "Attribute  0 STROBE_RATIO  StrobeDutyCycle  (1)\n"
        "LiveSetup/PresetTypes/BEAM 5/SHUTTER 20 >\n"
    )
    EMPTY_RAW = "Executing : List\nWARNING, NO OBJECTS FOUND FOR LIST\n[Fixture]>\n"

    @pytest.mark.asyncio
    @patch("src.server.navigate")
    @patch("src.server.list_destination")
    @patch("src.server.get_client")
    async def test_browse_depth1_returns_features(self, mock_get_client, mock_list_dest, mock_navigate):
        """depth=1 returns feature list for given preset type."""
        from unittest.mock import MagicMock

        from src.server import browse_preset_type

        mock_get_client.return_value = MagicMock()
        mock_navigate.return_value = MagicMock()

        mock_ld = MagicMock()
        mock_ld.raw_response = self.FEATURE_LIST_RAW
        mock_list_dest.return_value = mock_ld

        result = await browse_preset_type(preset_type_id=5, depth=1)
        data = json.loads(result)

        assert data["preset_type_id"] == 5
        assert data["cd_path"] == "10.2.5"
        assert data["risk_tier"] == "SAFE_READ"
        assert len(data["features"]) == 2
        assert data["features"][0]["library_name"] == "SHUTTER"
        assert data["features"][1]["library_name"] == "BEAM1"

    @pytest.mark.asyncio
    async def test_browse_invalid_preset_type_id(self):
        """preset_type_id outside 1-9 returns error."""
        from src.server import browse_preset_type

        result = await browse_preset_type(preset_type_id=10, depth=1)
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_browse_invalid_depth(self):
        """depth outside 1-3 returns error."""
        from src.server import browse_preset_type

        result = await browse_preset_type(preset_type_id=5, depth=4)
        data = json.loads(result)
        assert "error" in data


class TestModifySelectionTool:
    """Tests for the modify_selection MCP tool (tool #32)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_modify_selection_add(self, mock_get_client):
        """Test adding a fixture to the selection."""
        from src.server import modify_selection

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await modify_selection(action="add", fixture_ids=[5])
        data = json.loads(result)

        assert "+ 5" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_modify_selection_remove(self, mock_get_client):
        """Test removing a fixture from the selection."""
        from src.server import modify_selection

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await modify_selection(action="remove", fixture_ids=[3])
        data = json.loads(result)

        assert "- 3" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_modify_selection_clear(self, mock_get_client):
        """Test clearing the selection."""
        from src.server import modify_selection

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await modify_selection(action="clear")
        data = json.loads(result)

        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_modify_selection_replace(self, mock_get_client):
        """Test replacing the selection."""
        from src.server import modify_selection

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await modify_selection(action="replace", fixture_ids=[1, 5])
        data = json.loads(result)

        assert "command_sent" in data

    @pytest.mark.asyncio
    async def test_modify_selection_missing_fixtures(self):
        """Test that non-clear action without fixture_ids returns an error."""
        from src.server import modify_selection

        result = await modify_selection(action="add")
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_modify_selection_invalid_action(self):
        """Test that invalid action returns an error."""
        from src.server import modify_selection

        result = await modify_selection(action="toggle", fixture_ids=[1])
        data = json.loads(result)

        assert "error" in data


class TestAdjustValueRelativeTool:
    """Tests for the adjust_value_relative MCP tool (tool #33)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_adjust_value_positive_delta(self, mock_get_client):
        """Test nudging a value up by a positive delta."""
        from src.server import adjust_value_relative

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_client.send_command = AsyncMock()
        mock_get_client.return_value = mock_client

        result = await adjust_value_relative(delta=10.0)
        data = json.loads(result)

        assert "at + 10" in data["commands_sent"][-1]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_adjust_value_negative_delta(self, mock_get_client):
        """Test nudging a value down by a negative delta."""
        from src.server import adjust_value_relative

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_client.send_command = AsyncMock()
        mock_get_client.return_value = mock_client

        result = await adjust_value_relative(delta=-5.0)
        data = json.loads(result)

        assert "at - 5" in data["commands_sent"][-1]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_adjust_value_with_fixture_and_attribute(self, mock_get_client):
        """Test nudging with fixture selection and attribute targeting."""
        from src.server import adjust_value_relative

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_client.send_command = AsyncMock()
        mock_get_client.return_value = mock_client

        result = await adjust_value_relative(
            delta=10.0, fixture_ids=[1], attribute_name="Pan"
        )
        data = json.loads(result)

        assert len(data["commands_sent"]) == 3

    @pytest.mark.asyncio
    async def test_adjust_value_zero_delta(self):
        """Test that delta=0 returns an error."""
        from src.server import adjust_value_relative

        result = await adjust_value_relative(delta=0)
        data = json.loads(result)

        assert "error" in data


class TestControlTimecodeTool:
    """Tests for the control_timecode MCP tool (tool #34)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_timecode_start(self, mock_get_client):
        """Test starting a timecode show."""
        from src.server import control_timecode

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_timecode(action="start", timecode_id=1)
        data = json.loads(result)

        assert data["command_sent"] == "go timecode 1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_timecode_stop(self, mock_get_client):
        """Test stopping a timecode show."""
        from src.server import control_timecode

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_timecode(action="stop", timecode_id=2)
        data = json.loads(result)

        assert data["command_sent"] == "off timecode 2"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_timecode_goto(self, mock_get_client):
        """Test jumping to a timecode position."""
        from src.server import control_timecode

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_timecode(
            action="goto", timecode_id=1, timecode_position="00:01:30:00"
        )
        data = json.loads(result)

        assert "00:01:30:00" in data["command_sent"]

    @pytest.mark.asyncio
    async def test_control_timecode_goto_missing_position(self):
        """Test that goto without timecode_position returns an error."""
        from src.server import control_timecode

        result = await control_timecode(action="goto", timecode_id=1)
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_control_timecode_invalid_action(self):
        """Test that invalid action returns an error."""
        from src.server import control_timecode

        result = await control_timecode(action="pause", timecode_id=1)
        data = json.loads(result)

        assert "error" in data


class TestControlTimerTool:
    """Tests for the control_timer MCP tool (tool #35)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_timer_start(self, mock_get_client):
        """Test starting a timer."""
        from src.server import control_timer

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_timer(action="start", timer_id=1)
        data = json.loads(result)

        assert data["command_sent"] == "go timer 1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_timer_stop(self, mock_get_client):
        """Test stopping a timer."""
        from src.server import control_timer

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_timer(action="stop", timer_id=3)
        data = json.loads(result)

        assert data["command_sent"] == "off timer 3"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_timer_reset(self, mock_get_client):
        """Test resetting a timer."""
        from src.server import control_timer

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_timer(action="reset", timer_id=2)
        data = json.loads(result)

        assert data["command_sent"] == "goto timer 2"

    @pytest.mark.asyncio
    async def test_control_timer_invalid_id(self):
        """Test that timer_id < 1 returns an error."""
        from src.server import control_timer

        result = await control_timer(action="start", timer_id=0)
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_control_timer_invalid_action(self):
        """Test that invalid action returns an error."""
        from src.server import control_timer

        result = await control_timer(action="pause", timer_id=1)
        data = json.loads(result)

        assert "error" in data


class TestUndoLastActionTool:
    """Tests for the undo_last_action MCP tool (tool #36)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_undo_once(self, mock_get_client):
        """Test undoing a single action."""
        from src.server import undo_last_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await undo_last_action(count=1)
        data = json.loads(result)

        assert data["count"] == 1
        assert data["commands_sent"] == ["oops"]
        mock_client.send_command_with_response.assert_called_once_with("oops")

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_undo_multiple(self, mock_get_client):
        """Test undoing multiple actions."""
        from src.server import undo_last_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await undo_last_action(count=3)
        data = json.loads(result)

        assert data["count"] == 3
        assert len(data["commands_sent"]) == 3
        assert mock_client.send_command_with_response.call_count == 3

    @pytest.mark.asyncio
    async def test_undo_count_too_high(self):
        """Test that count > 20 returns an error."""
        from src.server import undo_last_action

        result = await undo_last_action(count=21)
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_undo_count_zero(self):
        """Test that count=0 returns an error."""
        from src.server import undo_last_action

        result = await undo_last_action(count=0)
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_undo_risk_tier(self, mock_get_client):
        """Test that risk tier is SAFE_WRITE."""
        from src.server import undo_last_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await undo_last_action()
        data = json.loads(result)

        assert data["risk_tier"] == "SAFE_WRITE"


class TestToggleConsoleModeTool:
    """Tests for the toggle_console_mode MCP tool (tool #37)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_toggle_blind(self, mock_get_client):
        """Test toggling blind mode."""
        from src.server import toggle_console_mode

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await toggle_console_mode(mode="blind")
        data = json.loads(result)

        assert data["command_sent"] == "blind"
        assert data["mode"] == "blind"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_toggle_highlight(self, mock_get_client):
        """Test toggling highlight mode."""
        from src.server import toggle_console_mode

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await toggle_console_mode(mode="highlight")
        data = json.loads(result)

        assert data["command_sent"] == "highlight"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_toggle_freeze(self, mock_get_client):
        """Test toggling freeze mode."""
        from src.server import toggle_console_mode

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await toggle_console_mode(mode="freeze")
        data = json.loads(result)

        assert data["command_sent"] == "freeze"

    @pytest.mark.asyncio
    async def test_toggle_invalid_mode(self):
        """Test that invalid mode returns an error."""
        from src.server import toggle_console_mode

        result = await toggle_console_mode(mode="blackout")
        data = json.loads(result)

        assert "error" in data


class TestUpdateCueDataTool:
    """Tests for the update_cue_data MCP tool (tool #38)."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        """Test that update is blocked without confirmation."""
        from src.server import update_cue_data

        result = await update_cue_data()
        data = json.loads(result)

        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_update_active_cue(self, mock_get_client):
        """Test updating the currently active cue."""
        from src.server import update_cue_data

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await update_cue_data(confirm_destructive=True)
        data = json.loads(result)

        assert data["command_sent"] == "update"
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_update_specific_cue(self, mock_get_client):
        """Test updating a specific cue."""
        from src.server import update_cue_data

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await update_cue_data(confirm_destructive=True, cue_id=5.0)
        data = json.loads(result)

        assert "cue 5" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_update_with_merge(self, mock_get_client):
        """Test updating with merge option."""
        from src.server import update_cue_data

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await update_cue_data(
            confirm_destructive=True, cue_id=3.0, merge=True
        )
        data = json.loads(result)

        assert "/merge" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_update_with_sequence_scope(self, mock_get_client):
        """Test updating with sequence scoping."""
        from src.server import update_cue_data

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await update_cue_data(
            confirm_destructive=True, cue_id=2.0, sequence_id=1
        )
        data = json.loads(result)

        assert "sequence 1" in data["command_sent"]


class TestSetCueTimingTool:
    """Tests for the set_cue_timing MCP tool (tool #39)."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        """Test that set_cue_timing is blocked without confirmation."""
        from src.server import set_cue_timing

        result = await set_cue_timing(cue_id=1, fade_time=3.0)
        data = json.loads(result)

        assert data["blocked"] is True

    @pytest.mark.asyncio
    async def test_error_no_times_provided(self):
        """Test that omitting both fade_time and delay_time returns an error."""
        from src.server import set_cue_timing

        result = await set_cue_timing(cue_id=1, confirm_destructive=True)
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_set_fade_time_only(self, mock_get_client):
        """Test setting fade time only."""
        from src.server import set_cue_timing

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_cue_timing(
            cue_id=3, confirm_destructive=True, fade_time=5.0
        )
        data = json.loads(result)

        assert len(data["commands_sent"]) == 1
        assert "fade" in data["commands_sent"][0]
        assert "3" in data["commands_sent"][0]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_set_delay_time_only(self, mock_get_client):
        """Test setting delay time only."""
        from src.server import set_cue_timing

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_cue_timing(
            cue_id=4, confirm_destructive=True, delay_time=2.0
        )
        data = json.loads(result)

        assert len(data["commands_sent"]) == 1
        assert "delay" in data["commands_sent"][0]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_set_both_fade_and_delay(self, mock_get_client):
        """Test setting both fade and delay times."""
        from src.server import set_cue_timing

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await set_cue_timing(
            cue_id=5, confirm_destructive=True, fade_time=3.0, delay_time=1.0
        )
        data = json.loads(result)

        assert len(data["commands_sent"]) == 2
        assert data["risk_tier"] == "DESTRUCTIVE"


class TestSelectFixturesByGroupTool:
    """Tests for the select_fixtures_by_group MCP tool (tool #40)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_group_replace(self, mock_get_client):
        """Test selecting a group (replacing current selection)."""
        from src.server import select_fixtures_by_group

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await select_fixtures_by_group(group_id=2)
        data = json.loads(result)

        assert data["command_sent"] == "group 2"
        assert data["group_id"] == 2

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_group_append(self, mock_get_client):
        """Test appending a group to the current selection."""
        from src.server import select_fixtures_by_group

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await select_fixtures_by_group(group_id=3, append=True)
        data = json.loads(result)

        assert data["command_sent"] == "+ group 3"

    @pytest.mark.asyncio
    async def test_select_group_invalid_id(self):
        """Test that group_id < 1 returns an error."""
        from src.server import select_fixtures_by_group

        result = await select_fixtures_by_group(group_id=0)
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_group_risk_tier(self, mock_get_client):
        """Test that risk tier is SAFE_WRITE."""
        from src.server import select_fixtures_by_group

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await select_fixtures_by_group(group_id=1)
        data = json.loads(result)

        assert data["risk_tier"] == "SAFE_WRITE"


class TestControlExecutorTool:
    """Tests for the control_executor MCP tool (tool #41)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_executor_on(self, mock_get_client):
        """Test turning an executor on."""
        from src.server import control_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_executor(action="on", executor_id=5)
        data = json.loads(result)

        assert data["risk_tier"] == "SAFE_WRITE"
        assert "on" in data["command_sent"].lower() or "5" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_executor_off(self, mock_get_client):
        """Test turning an executor off."""
        from src.server import control_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_executor(action="off", executor_id=5)
        data = json.loads(result)

        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_executor_flash(self, mock_get_client):
        """Test flashing an executor."""
        from src.server import control_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_executor(action="flash", executor_id=3)
        data = json.loads(result)

        assert "command_sent" in data

    @pytest.mark.asyncio
    async def test_control_executor_set_speed_blocked(self):
        """Test that set_speed is blocked without confirmation."""
        from src.server import control_executor

        result = await control_executor(
            action="set_speed", executor_id=1, speed_value=120.0
        )
        data = json.loads(result)

        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_executor_set_speed_confirmed(self, mock_get_client):
        """Test setting executor speed with confirmation."""
        from src.server import control_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_executor(
            action="set_speed", executor_id=1, speed_value=120.0,
            confirm_destructive=True
        )
        data = json.loads(result)

        assert "120" in data["command_sent"]
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    async def test_control_executor_invalid_action(self):
        """Test that invalid action returns an error."""
        from src.server import control_executor

        result = await control_executor(action="pause", executor_id=1)
        data = json.loads(result)

        assert "error" in data

    @pytest.mark.asyncio
    async def test_control_executor_invalid_id(self):
        """Test that executor_id < 1 returns an error."""
        from src.server import control_executor

        result = await control_executor(action="on", executor_id=0)
        data = json.loads(result)

        assert "error" in data


class TestGetExecutorStatusTool:
    """Tests for the get_executor_status MCP tool (tool #42)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_get_status_all_executors(self, mock_get_client):
        """Test listing all executors."""
        from src.server import get_executor_status

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Executor list")
        mock_get_client.return_value = mock_client

        result = await get_executor_status()
        data = json.loads(result)

        assert data["command_sent"] == "list executor"
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_get_status_specific_executor(self, mock_get_client):
        """Test listing a specific executor."""
        from src.server import get_executor_status

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Executor 5")
        mock_get_client.return_value = mock_client

        result = await get_executor_status(executor_id=5)
        data = json.loads(result)

        assert data["command_sent"] == "list executor 5"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_get_status_with_page(self, mock_get_client):
        """Test listing a page-qualified executor."""
        from src.server import get_executor_status

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Executor 2.5")
        mock_get_client.return_value = mock_client

        result = await get_executor_status(executor_id=5, page=2)
        data = json.loads(result)

        assert data["command_sent"] == "list executor 2.5"


class TestStoreTimecodeEventTool:
    """Tests for the store_timecode_event MCP tool (tool #43)."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        """Test that store_timecode_event is blocked without confirmation."""
        from src.server import store_timecode_event

        result = await store_timecode_event(
            timecode_id=1, cue_id=5.0, sequence_id=1
        )
        data = json.loads(result)

        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_timecode_without_position(self, mock_get_client):
        """Test storing a timecode event without a position."""
        from src.server import store_timecode_event

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await store_timecode_event(
            timecode_id=2, cue_id=3.0, sequence_id=1, confirm_destructive=True
        )
        data = json.loads(result)

        assert data["command_sent"] == "store timecode 2"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_timecode_with_position(self, mock_get_client):
        """Test storing a timecode event at a specific position."""
        from src.server import store_timecode_event

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await store_timecode_event(
            timecode_id=1, cue_id=5.0, sequence_id=2,
            confirm_destructive=True, timecode_position="00:01:00:00"
        )
        data = json.loads(result)

        assert "assign timecode 1" in data["command_sent"]
        assert "00:01:00:00" in data["command_sent"]
        assert "sequence 2" in data["command_sent"]


class TestSetSequencePropertyTool:
    """Tests for the set_sequence_property MCP tool (tool #44)."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        """Test that set_sequence_property is blocked without confirmation."""
        from src.server import set_sequence_property

        result = await set_sequence_property(
            sequence_id=1, property_name="loop", value="on"
        )
        data = json.loads(result)

        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.set_property", new_callable=AsyncMock)
    @patch("src.server.get_client")
    async def test_set_loop_property(self, mock_get_client, mock_set_property):
        """Test setting the loop property on a sequence."""
        from src.navigation import SetPropertyResult
        from src.server import set_sequence_property

        mock_set_property.return_value = SetPropertyResult(
            path="sequence 1", commands_sent=["cd sequence 1", 'assign "loop" "on"', "cd /"],
            raw_responses=["", "", ""], success=True, verified_value=None, error=None,
        )

        result = await set_sequence_property(
            sequence_id=1, property_name="loop", value="on",
            confirm_destructive=True
        )
        data = json.loads(result)

        assert data["sequence_id"] == 1
        assert data["property"] == "loop"
        assert data["value"] == "on"
        assert data["risk_tier"] == "DESTRUCTIVE"
        assert data["success"] is True
        mock_set_property.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.server.set_property", new_callable=AsyncMock)
    @patch("src.server.get_client")
    async def test_set_tracking_property(self, mock_get_client, mock_set_property):
        """Test setting the tracking property on a sequence."""
        from src.navigation import SetPropertyResult
        from src.server import set_sequence_property

        mock_set_property.return_value = SetPropertyResult(
            path="sequence 3", commands_sent=["cd sequence 3", 'assign "tracking" "off"', "cd /"],
            raw_responses=["", "", ""], success=True, verified_value=None, error=None,
        )

        result = await set_sequence_property(
            sequence_id=3, property_name="tracking", value="off",
            confirm_destructive=True
        )
        data = json.loads(result)

        assert data["sequence_id"] == 3
        assert data["success"] is True
        mock_set_property.assert_called_once()


# ============================================================
# Tests for New Tools 45-52 -- Quick Start Guide Gap-Fill
# ============================================================


class TestSaveShowTool:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_save_show_save(self, mock_get_client):
        from src.server import save_show
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await save_show(action="save")
        data = json.loads(result)
        assert data["command_sent"] == "save"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_save_show_saveas(self, mock_get_client):
        from src.server import save_show
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await save_show(action="saveas", show_name="my_show")
        data = json.loads(result)
        assert data["command_sent"] == 'saveas "my_show"'

    @pytest.mark.asyncio
    async def test_save_show_saveas_missing_name(self):
        from src.server import save_show
        result = await save_show(action="saveas")
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_save_show_invalid_action(self):
        from src.server import save_show
        result = await save_show(action="delete")
        data = json.loads(result)
        assert "error" in data


class TestStoreCueWithTimingTool:
    @pytest.mark.asyncio
    async def test_store_cue_with_timing_blocked(self):
        from src.server import store_cue_with_timing
        result = await store_cue_with_timing(cue_id=1)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_cue_with_timing_fade(self, mock_get_client):
        from src.server import store_cue_with_timing
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await store_cue_with_timing(cue_id=2, confirm_destructive=True, fade_time=15.0)
        data = json.loads(result)
        assert "store cue 2" in data["command_sent"]
        assert "time 15.0" in data["command_sent"]
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_cue_with_timing_both_times(self, mock_get_client):
        from src.server import store_cue_with_timing
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await store_cue_with_timing(cue_id=3, confirm_destructive=True, fade_time=20.0, out_time=10.0)
        data = json.loads(result)
        assert "time 20.0" in data["command_sent"]
        assert "outtime 10.0" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_cue_with_timing_merge(self, mock_get_client):
        from src.server import store_cue_with_timing
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await store_cue_with_timing(cue_id=1, confirm_destructive=True, fade_time=5.0, merge=True)
        data = json.loads(result)
        assert "/merge" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_cue_with_timing_sequence_id(self, mock_get_client):
        from src.server import store_cue_with_timing
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await store_cue_with_timing(
            cue_id=4, confirm_destructive=True, fade_time=10.0, sequence_id=2
        )
        data = json.loads(result)
        assert "store cue 4" in data["command_sent"]
        assert "sequence 2" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_cue_with_timing_no_sequence_id(self, mock_get_client):
        """Without sequence_id, command should NOT contain 'sequence'."""
        from src.server import store_cue_with_timing
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await store_cue_with_timing(cue_id=4, confirm_destructive=True, fade_time=10.0)
        data = json.loads(result)
        assert "sequence" not in data["command_sent"]


class TestSelectExecutorTool:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_executor_basic(self, mock_get_client):
        from src.server import select_executor
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await select_executor(executor_id=3)
        data = json.loads(result)
        assert data["command_sent"] == "select executor 3"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_executor_with_page(self, mock_get_client):
        from src.server import select_executor
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await select_executor(executor_id=5, page=2)
        data = json.loads(result)
        assert data["command_sent"] == "select executor 2.5"


class TestRemoveFromProgrammerTool:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_remove_channel(self, mock_get_client):
        from src.server import remove_from_programmer
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await remove_from_programmer(object_type="channel", object_id=5)
        data = json.loads(result)
        assert data["command_sent"] == "off channel 5"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_remove_channel_range(self, mock_get_client):
        from src.server import remove_from_programmer
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await remove_from_programmer(object_type="channel", object_id=1, end_id=10)
        data = json.loads(result)
        assert data["command_sent"] == "off channel 1 thru 10"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_remove_fixture(self, mock_get_client):
        from src.server import remove_from_programmer
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await remove_from_programmer(object_type="fixture", object_id=111)
        data = json.loads(result)
        assert data["command_sent"] == "off fixture 111"

    @pytest.mark.asyncio
    async def test_remove_invalid_type(self):
        from src.server import remove_from_programmer
        result = await remove_from_programmer(object_type="preset", object_id=1)
        data = json.loads(result)
        assert "error" in data


class TestAssignCueTriggerTool:
    @pytest.mark.asyncio
    async def test_assign_cue_trigger_blocked(self):
        from src.server import assign_cue_trigger
        result = await assign_cue_trigger(cue_id=3, sequence_id=1, trigger_type="follow")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_cue_trigger_follow(self, mock_get_client):
        from src.server import assign_cue_trigger
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await assign_cue_trigger(cue_id=3, sequence_id=1, trigger_type="follow", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == "assign trigger follow cue 3 sequence 1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_cue_trigger_bpm(self, mock_get_client):
        from src.server import assign_cue_trigger
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await assign_cue_trigger(cue_id=4, sequence_id=2, trigger_type="bpm", trigger_value=120.0, confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == "assign trigger bpm 120.0 cue 4 sequence 2"

    @pytest.mark.asyncio
    async def test_assign_cue_trigger_bpm_missing_value(self):
        from src.server import assign_cue_trigger
        result = await assign_cue_trigger(cue_id=1, sequence_id=1, trigger_type="bpm", confirm_destructive=True)
        data = json.loads(result)
        assert "error" in data


class TestAssignExecutorPropertyTool:
    @pytest.mark.asyncio
    async def test_assign_executor_property_blocked(self):
        from src.server import assign_executor_property
        result = await assign_executor_property(property_name="width", executor_id=1, value=2)
        data = json.loads(result)
        assert data["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_executor_width(self, mock_get_client):
        from src.server import assign_executor_property
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await assign_executor_property(executor_id=1, option="width", value=2, confirm_destructive=True, page=1)
        data = json.loads(result)
        assert data["command_sent"] == "Assign Executor 1.1 /width=2"

    @pytest.mark.asyncio
    async def test_assign_executor_property_invalid_option(self):
        from src.server import assign_executor_property
        result = await assign_executor_property(executor_id=1, option="badoption", value="on", confirm_destructive=True)
        data = json.loads(result)
        assert data["blocked"] is True
        assert "badoption" in data["error"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_executor_ratemaster(self, mock_get_client):
        from src.server import assign_executor_property
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await assign_executor_property(executor_id=3, option="ratemaster", value="rate_individual", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == "Assign Executor 1.3 /ratemaster=rate_individual"


class TestIfFilterTool:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_if_filter_active(self, mock_get_client):
        from src.server import if_filter
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await if_filter(filter_type="active")
        data = json.loads(result)
        assert data["command_sent"] == "if"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_if_filter_fixture(self, mock_get_client):
        from src.server import if_filter
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await if_filter(filter_type="fixture", fixture_id=5)
        data = json.loads(result)
        assert data["command_sent"] == "if fixture 5"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_if_filter_attribute(self, mock_get_client):
        from src.server import if_filter
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await if_filter(filter_type="attribute", fixture_id=5, attribute_name="Pan")
        data = json.loads(result)
        assert data["command_sent"] == 'if fixture 5 attribute "Pan"'

    @pytest.mark.asyncio
    async def test_if_filter_invalid_type(self):
        from src.server import if_filter
        result = await if_filter(filter_type="group")
        data = json.loads(result)
        assert "error" in data


class TestSaveRecallViewTool:
    @pytest.mark.asyncio
    async def test_save_recall_view_store_blocked(self):
        from src.server import save_recall_view
        result = await save_recall_view(action="store", view_id=1)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_save_recall_view_store(self, mock_get_client):
        from src.server import save_recall_view
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await save_recall_view(action="store", view_id=1, screen_id=2, confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == "store ViewButton 2.1"
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_save_recall_view_recall(self, mock_get_client):
        from src.server import save_recall_view
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await save_recall_view(action="recall", view_id=3)
        data = json.loads(result)
        assert data["command_sent"] == "ViewButton 1.3"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_save_recall_view_label(self, mock_get_client):
        from src.server import save_recall_view
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await save_recall_view(action="label", view_id=2, view_name="My View")
        data = json.loads(result)
        assert data["command_sent"] == 'label ViewButton 1.2 "My View"'

    @pytest.mark.asyncio
    async def test_save_recall_view_invalid_view_id(self):
        from src.server import save_recall_view
        result = await save_recall_view(action="recall", view_id=11)
        data = json.loads(result)
        assert "error" in data



    # ============================================================
    # Tests for Tools 53-54 -- Import / Export
    # ============================================================


class TestExportObjectsTool:
    @pytest.mark.asyncio
    async def test_export_blocked(self):
        from src.server import export_objects
        result = await export_objects(object_type="Group", object_id="1", filename="test")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_export_basic(self, mock_get_client):
        from src.server import export_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await export_objects(object_type="Group", object_id="1", filename="my_groups", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'export Group 1 "my_groups" /noconfirm'
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_export_range(self, mock_get_client):
        from src.server import export_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await export_objects(object_type="Macro", object_id="1 thru 5", filename="macros", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'export Macro 1 thru 5 "macros" /noconfirm'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_export_preset(self, mock_get_client):
        from src.server import export_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await export_objects(object_type="Preset", object_id="1.3", filename="dim3", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'export Preset 1.3 "dim3" /noconfirm'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_export_with_style_csv(self, mock_get_client):
        from src.server import export_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await export_objects(object_type="Sequence", object_id="1", filename="seqs", style="csv", confirm_destructive=True)
        data = json.loads(result)
        assert "/style=csv" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_export_with_overwrite(self, mock_get_client):
        from src.server import export_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await export_objects(object_type="Group", object_id="1", filename="grp", overwrite=True, confirm_destructive=True)
        data = json.loads(result)
        assert "/overwrite" in data["command_sent"]

    @pytest.mark.asyncio
    async def test_export_invalid_type(self):
        from src.server import export_objects
        result = await export_objects(object_type="Banana", object_id="1", filename="test", confirm_destructive=True)
        data = json.loads(result)
        assert "error" in data
        assert "Banana" in data["error"]

    @pytest.mark.asyncio
    async def test_export_invalid_style(self):
        from src.server import export_objects
        result = await export_objects(object_type="Group", object_id="1", filename="test", style="pdf", confirm_destructive=True)
        data = json.loads(result)
        assert "error" in data
        assert "style" in data["error"]


class TestImportObjectsTool:
    @pytest.mark.asyncio
    async def test_import_blocked(self):
        from src.server import import_objects
        result = await import_objects(filename="my_groups", destination_type="Group")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_basic(self, mock_get_client):
        from src.server import import_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="1 object(s) imported.")
        mock_get_client.return_value = mock_client
        result = await import_objects(filename="my_groups", destination_type="Group", destination_id="99", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'import "my_groups" at Group 99 /noconfirm'
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_no_id(self, mock_get_client):
        from src.server import import_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_objects(filename="macros", destination_type="Macro", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'import "macros" at Macro /noconfirm'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_preset(self, mock_get_client):
        from src.server import import_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_objects(filename="preset_dimmer", destination_type="Preset", destination_id="1.99", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'import "preset_dimmer" at Preset 1.99 /noconfirm'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_matricks(self, mock_get_client):
        from src.server import import_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_objects(filename="matricks_test", destination_type="MAtricks", destination_id="99", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'import "matricks_test" at MAtricks 99 /noconfirm'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_with_quiet(self, mock_get_client):
        from src.server import import_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_objects(filename="show_backup", destination_type="Group", destination_id="10", quiet=True, confirm_destructive=True)
        data = json.loads(result)
        assert "/quiet" in data["command_sent"]

    @pytest.mark.asyncio
    async def test_import_invalid_type(self):
        from src.server import import_objects
        result = await import_objects(filename="test", destination_type="Banana", confirm_destructive=True)
        data = json.loads(result)
        assert "error" in data
        assert "Banana" in data["error"]

    @pytest.mark.asyncio
    async def test_import_screen_rejected(self):
        from src.server import import_objects
        result = await import_objects(filename="screen_test", destination_type="Screen", confirm_destructive=True)
        data = json.loads(result)
        assert "error" in data


class TestImportFixtureTypeTool:
    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import import_fixture_type
        result = await import_fixture_type(manufacturer="Martin", fixture="Mac700Profile_Extended", mode="Extended")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_four_commands(self, mock_get_client):
        from src.server import import_fixture_type
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_fixture_type(
            manufacturer="Martin",
            fixture="Mac700Profile_Extended",
            mode="Extended",
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert len(data["steps"]) == 4
        commands = [s["command"] for s in data["steps"]]
        assert commands[0] == 'ChangeDest "EditSetup"'
        assert commands[1] == 'ChangeDest "FixtureTypes"'
        assert commands[2] == 'Import "Martin@Mac700Profile_Extended@Extended"'
        assert commands[3] == 'ChangeDest /'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_returns_fixture_key(self, mock_get_client):
        from src.server import import_fixture_type
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_fixture_type(
            manufacturer="Generic",
            fixture="Dimmer",
            mode="Standard",
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert data["fixture_key"] == "Generic@Dimmer@Standard"
        assert data["risk_tier"] == "DESTRUCTIVE"


class TestImportFixtureLayerTool:
    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import import_fixture_layer
        result = await import_fixture_layer(filename="dimmers")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_four_commands_no_layer_index(self, mock_get_client):
        from src.server import import_fixture_layer
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_fixture_layer(filename="dimmers", confirm_destructive=True)
        data = json.loads(result)
        assert len(data["steps"]) == 4
        commands = [s["command"] for s in data["steps"]]
        assert commands[0] == 'ChangeDest "EditSetup"'
        assert commands[1] == 'ChangeDest "Layers"'
        assert commands[2] == 'Import "dimmers"'
        assert commands[3] == 'ChangeDest /'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_four_commands_with_layer_index(self, mock_get_client):
        from src.server import import_fixture_layer
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_fixture_layer(filename="mac700s", layer_index=2, confirm_destructive=True)
        data = json.loads(result)
        commands = [s["command"] for s in data["steps"]]
        assert commands[2] == 'Import "mac700s" At 2'


class TestGenerateFixtureLayerXmlTool:
    """Tests for generate_fixture_layer_xml — writes to importexport dir."""

    SAMPLE_FIXTURE = {
        "fixture_id": 1,
        "name": "Dim 1",
        "fixture_type_no": 2,
        "fixture_type_name": "2 Dimmer 00",
        "dmx_address": 1,
        "num_channels": 1,
    }

    @pytest.mark.asyncio
    async def test_creates_file(self, tmp_path, monkeypatch):
        from src.server import generate_fixture_layer_xml
        monkeypatch.setattr("src.server.generate_fixture_layer_xml.__wrapped__", None, raising=False)
        # Patch output dir to tmp_path

        # We'll patch os.path.join indirectly by monkeypatching the output_dir
        # inside the function — simplest approach: just call the real function
        # since the importexport dir exists on this machine.
        import os
        output_dir = r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport"
        test_filename = "_test_generate_xml_unit"
        test_file = os.path.join(output_dir, f"{test_filename}.xml")
        # Cleanup before
        if os.path.exists(test_file):
            os.unlink(test_file)

        result = await generate_fixture_layer_xml(
            filename=test_filename,
            layer_name="Test Layer",
            layer_index=1,
            fixtures=[self.SAMPLE_FIXTURE],
            showfile="unit_test",
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert data["fixture_count"] == 1
        assert data["layer_index"] == 1
        assert os.path.exists(data["file_path"])

        # Validate XML structure
        import xml.etree.ElementTree as ET
        tree = ET.parse(data["file_path"])
        root = tree.getroot()
        assert root.tag == "MA"
        layer = root.find("Layer")
        assert layer is not None
        assert layer.get("name") == "Test Layer"
        fixtures_el = layer.findall("Fixture")
        assert len(fixtures_el) == 1
        assert fixtures_el[0].get("fixture_id") == "1"

        # Cleanup
        os.unlink(data["file_path"])

    @pytest.mark.asyncio
    async def test_overwrite_blocked_by_default(self):
        import os

        from src.server import generate_fixture_layer_xml
        output_dir = r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport"
        test_filename = "_test_overwrite_block"
        test_file = os.path.join(output_dir, f"{test_filename}.xml")
        if os.path.exists(test_file):
            os.unlink(test_file)

        # First call — succeeds
        await generate_fixture_layer_xml(
            filename=test_filename,
            layer_name="L",
            layer_index=1,
            fixtures=[self.SAMPLE_FIXTURE],
            confirm_destructive=True,
        )
        # Second call without overwrite — should fail
        result = await generate_fixture_layer_xml(
            filename=test_filename,
            layer_name="L",
            layer_index=1,
            fixtures=[self.SAMPLE_FIXTURE],
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert "error" in data

        os.unlink(test_file)

    @pytest.mark.asyncio
    async def test_overwrite_allowed(self):
        import os

        from src.server import generate_fixture_layer_xml
        output_dir = r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport"
        test_filename = "_test_overwrite_allow"
        test_file = os.path.join(output_dir, f"{test_filename}.xml")
        if os.path.exists(test_file):
            os.unlink(test_file)

        await generate_fixture_layer_xml(
            filename=test_filename, layer_name="L", layer_index=1,
            fixtures=[self.SAMPLE_FIXTURE], confirm_destructive=True,
        )
        result = await generate_fixture_layer_xml(
            filename=test_filename, layer_name="L", layer_index=1,
            fixtures=[self.SAMPLE_FIXTURE], overwrite=True, confirm_destructive=True,
        )
        data = json.loads(result)
        assert "error" not in data
        assert data["fixture_count"] == 1

        os.unlink(test_file)

    @pytest.mark.asyncio
    async def test_channel_count(self):
        import os
        import xml.etree.ElementTree as ET

        from src.server import generate_fixture_layer_xml
        output_dir = r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport"
        test_filename = "_test_channel_count"
        test_file = os.path.join(output_dir, f"{test_filename}.xml")
        if os.path.exists(test_file):
            os.unlink(test_file)

        fx = dict(self.SAMPLE_FIXTURE)
        fx["num_channels"] = 3
        result = await generate_fixture_layer_xml(
            filename=test_filename, layer_name="L", layer_index=1,
            fixtures=[fx], confirm_destructive=True,
        )
        data = json.loads(result)
        tree = ET.parse(data["file_path"])
        channels = tree.getroot().findall(".//Channel")
        assert len(channels) == 3

        os.unlink(test_file)


    # ============================================================
    # Tests for validation helpers + refactored park/unpark/goto
    # + list_fixtures / list_sequence_cues (tools 55-56)
    # ============================================================


class TestValidateObjectExists:
    @pytest.mark.asyncio
    async def test_fixture_exists(self):
        from src.server import _validate_object_exists
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Fixture 20  Id=20  Name=RGBBLIND"
        )
        exists, raw = await _validate_object_exists(mock_client, "fixture", 20)
        assert exists is True
        mock_client.send_command_with_response.assert_called_once_with("list fixture 20")

    @pytest.mark.asyncio
    async def test_fixture_not_found(self):
        from src.server import _validate_object_exists
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="NO OBJECTS FOUND FOR LIST"
        )
        exists, raw = await _validate_object_exists(mock_client, "fixture", 1)
        assert exists is False

    @pytest.mark.asyncio
    async def test_cue_exists_in_sequence(self):
        from src.server import _validate_object_exists
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Cue 1  Name=Open  Mode=Normal"
        )
        exists, raw = await _validate_object_exists(mock_client, "cue", "1 sequence 278")
        assert exists is True
        mock_client.send_command_with_response.assert_called_once_with("list cue 1 sequence 278")

    @pytest.mark.asyncio
    async def test_cue_not_found_in_sequence(self):
        from src.server import _validate_object_exists
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="NO OBJECTS FOUND FOR LIST"
        )
        exists, raw = await _validate_object_exists(mock_client, "cue", "99 sequence 278")
        assert exists is False

    @pytest.mark.asyncio
    async def test_case_insensitive_sentinel(self):
        from src.server import _validate_object_exists
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="WARNING, no objects found for list"
        )
        exists, _ = await _validate_object_exists(mock_client, "group", 99)
        assert exists is False


class TestGetSequenceForExecutor:
    @pytest.mark.asyncio
    async def test_parses_sequence_id(self):
        from src.server import _get_sequence_for_executor
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Exec 1.1  Name=BIG BAR  Sequence=Seq 278(2)  Width=1"
        )
        seq_id, raw = await _get_sequence_for_executor(mock_client, executor_id=1, page=1)
        assert seq_id == 278
        mock_client.send_command_with_response.assert_called_once_with("list executor 1.1")

    @pytest.mark.asyncio
    async def test_returns_none_when_no_sequence(self):
        from src.server import _get_sequence_for_executor
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Exec 1.5  Name=Empty  Width=1"
        )
        seq_id, raw = await _get_sequence_for_executor(mock_client, executor_id=5)
        assert seq_id is None

    @pytest.mark.asyncio
    async def test_custom_page(self):
        from src.server import _get_sequence_for_executor
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Exec 2.3  Sequence=Seq 42(1)"
        )
        seq_id, _ = await _get_sequence_for_executor(mock_client, executor_id=3, page=2)
        assert seq_id == 42
        mock_client.send_command_with_response.assert_called_once_with("list executor 2.3")


class TestParkFixtureValidated:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_park_existing_fixture(self, mock_get_client):
        from src.server import park_fixture
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "Fixture 20  Id=20  Name=RGBBLIND",  # probe — exists
            "[channel]>",                          # park command
        ])
        mock_get_client.return_value = mock_client
        result = await park_fixture(target="fixture 20")
        data = json.loads(result)
        assert data["exists"] is True
        assert data["command_sent"] == "park fixture 20"
        assert mock_client.send_command_with_response.call_count == 2

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_park_nonexistent_fixture_blocked(self, mock_get_client):
        from src.server import park_fixture
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="NO OBJECTS FOUND FOR LIST"
        )
        mock_get_client.return_value = mock_client
        result = await park_fixture(target="fixture 1")
        data = json.loads(result)
        assert data["exists"] is False
        assert data["command_sent"] is None
        assert "does not exist" in data["error"]
        assert "list_fixtures" in data["hint"]
        assert mock_client.send_command_with_response.call_count == 1

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_park_dmx_skips_validation(self, mock_get_client):
        from src.server import park_fixture
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await park_fixture(target="dmx 101", value=128)
        data = json.loads(result)
        assert "park dmx 101" in data["command_sent"]
        assert data["exists"] is None
        assert mock_client.send_command_with_response.call_count == 1

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_park_fixture_with_value(self, mock_get_client):
        from src.server import park_fixture
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "Fixture 20  Id=20",
            "[channel]>",
        ])
        mock_get_client.return_value = mock_client
        result = await park_fixture(target="fixture 20", value=50)
        data = json.loads(result)
        assert "at 50" in data["command_sent"]


class TestUnparkFixtureValidated:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_unpark_existing_fixture(self, mock_get_client):
        from src.server import unpark_fixture
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "Fixture 20  Id=20",
            "[channel]>",
        ])
        mock_get_client.return_value = mock_client
        result = await unpark_fixture(target="fixture 20")
        data = json.loads(result)
        assert data["exists"] is True
        assert data["command_sent"] == "unpark fixture 20"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_unpark_nonexistent_fixture_blocked(self, mock_get_client):
        from src.server import unpark_fixture
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="NO OBJECTS FOUND FOR LIST"
        )
        mock_get_client.return_value = mock_client
        result = await unpark_fixture(target="fixture 1")
        data = json.loads(result)
        assert data["command_sent"] is None
        assert data["exists"] is False
        assert "does not exist" in data["error"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_unpark_dmx_skips_validation(self, mock_get_client):
        from src.server import unpark_fixture
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await unpark_fixture(target="dmx 101")
        data = json.loads(result)
        assert "unpark dmx 101" in data["command_sent"]
        assert data["exists"] is None
        assert mock_client.send_command_with_response.call_count == 1


class TestPlaybackActionGotoValidated:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_goto_cue_exists_with_sequence(self, mock_get_client):
        from src.server import playback_action
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "Cue 1  Name=Open  Mode=Normal",  # cue probe — exists
            "[channel]>",                       # goto command
        ])
        mock_get_client.return_value = mock_client
        result = await playback_action(action="goto", cue_id=1, sequence=278)
        data = json.loads(result)
        assert "goto cue 1" in data["command_sent"]
        assert data["cue_exists"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_goto_cue_not_found_blocked(self, mock_get_client):
        from src.server import playback_action
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="NO OBJECTS FOUND FOR LIST"
        )
        mock_get_client.return_value = mock_client
        result = await playback_action(action="goto", cue_id=99, sequence=278)
        data = json.loads(result)
        assert data["command_sent"] is None
        assert data["cue_exists"] is False
        assert "Error #72" in data["error"]
        assert "list_sequence_cues" in data["hint"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_goto_resolves_sequence_from_executor(self, mock_get_client):
        from src.server import playback_action
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "Exec 1.1  Sequence=Seq 278(2)",   # executor probe
            "Cue 1  Name=Open",                  # cue probe — exists
            "[channel]>",                         # goto command
        ])
        mock_get_client.return_value = mock_client
        result = await playback_action(action="goto", cue_id=1, executor=1)
        data = json.loads(result)
        assert "goto cue 1" in data["command_sent"]
        assert data["cue_exists"] is True
        assert "executor_probe_response" in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_goto_no_sequence_context_warns_and_executes(self, mock_get_client):
        from src.server import playback_action
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client
        result = await playback_action(action="goto", cue_id=5)
        data = json.loads(result)
        assert "goto cue 5" in data["command_sent"]
        assert "warning" in data
        assert "without cue" in data["warning"]

    @pytest.mark.asyncio
    async def test_goto_missing_cue_id_returns_error(self):
        from src.server import playback_action
        result = await playback_action(action="goto")
        data = json.loads(result)
        assert "error" in data
        assert "cue_id" in data["error"]


class TestListFixturesTool:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_all_fixtures(self, mock_get_client):
        from src.server import list_fixtures
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Fixture 20  Id=20  Name=RGBBLIND\nFixture 25  Id=25"
        )
        mock_get_client.return_value = mock_client
        result = await list_fixtures()
        data = json.loads(result)
        assert data["command_sent"] == "list fixture"
        assert data["exists"] is True
        assert data["fixture_id"] is None
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_specific_fixture_exists(self, mock_get_client):
        from src.server import list_fixtures
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Fixture 20  Id=20  Name=RGBBLIND"
        )
        mock_get_client.return_value = mock_client
        result = await list_fixtures(fixture_id=20)
        data = json.loads(result)
        assert data["command_sent"] == "list fixture 20"
        assert data["exists"] is True
        assert data["fixture_id"] == 20

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_specific_fixture_not_found(self, mock_get_client):
        from src.server import list_fixtures
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="NO OBJECTS FOUND FOR LIST"
        )
        mock_get_client.return_value = mock_client
        result = await list_fixtures(fixture_id=1)
        data = json.loads(result)
        assert data["exists"] is False
        assert data["fixture_id"] == 1


class TestListSequenceCuesTool:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_all_cues_by_sequence_id(self, mock_get_client):
        from src.server import list_sequence_cues
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Cue 1  Name=Open\nCue 2  Name=Close"
        )
        mock_get_client.return_value = mock_client
        result = await list_sequence_cues(sequence_id=278)
        data = json.loads(result)
        assert data["command_sent"] == "list cue sequence 278"
        assert data["resolved_sequence_id"] == 278
        assert data["exists"] is True
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_check_specific_cue_exists(self, mock_get_client):
        from src.server import list_sequence_cues
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Cue 1  Name=Open  Mode=Normal"
        )
        mock_get_client.return_value = mock_client
        result = await list_sequence_cues(sequence_id=278, cue_id=1)
        data = json.loads(result)
        assert data["command_sent"] == "list cue 1 sequence 278"
        assert data["exists"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_check_specific_cue_not_found(self, mock_get_client):
        from src.server import list_sequence_cues
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="NO OBJECTS FOUND FOR LIST"
        )
        mock_get_client.return_value = mock_client
        result = await list_sequence_cues(sequence_id=278, cue_id=99)
        data = json.loads(result)
        assert data["exists"] is False
        assert data["command_sent"] == "list cue 99 sequence 278"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_resolve_sequence_from_executor(self, mock_get_client):
        from src.server import list_sequence_cues
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "Exec 1.1  Sequence=Seq 278(2)",  # executor resolution
            "Cue 1  Name=Open\nCue 2",         # list cue
        ])
        mock_get_client.return_value = mock_client
        result = await list_sequence_cues(executor_id=1, cue_id=1)
        data = json.loads(result)
        assert data["resolved_sequence_id"] == 278
        assert data["command_sent"] == "list cue 1 sequence 278"
        assert data["exists"] is True
        assert "executor_probe_response" in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_executor_with_no_sequence_linked(self, mock_get_client):
        from src.server import list_sequence_cues
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="Exec 1.5  Name=Empty  Width=1"
        )
        mock_get_client.return_value = mock_client
        result = await list_sequence_cues(executor_id=5)
        data = json.loads(result)
        assert data["exists"] is False
        assert data["resolved_sequence_id"] is None
        assert "sequence assigned" in data["error"]

    @pytest.mark.asyncio
    async def test_no_sequence_or_executor_returns_error(self):
        from src.server import list_sequence_cues
        result = await list_sequence_cues()
        data = json.loads(result)
        assert "error" in data
        assert data["command_sent"] is None


# ============================================================
# Tools 57–64: Tier 1 — High-Impact Tools
# ============================================================


class TestHighlightFixtures:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_highlight_on(self, mock_get_client):
        from src.server import highlight_fixtures
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await highlight_fixtures(on=True)
        data = json.loads(result)
        assert data["command_sent"] == "highlight on"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_highlight_off(self, mock_get_client):
        from src.server import highlight_fixtures
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await highlight_fixtures(on=False)
        data = json.loads(result)
        assert data["command_sent"] == "highlight off"


class TestReleaseExecutor:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_release_basic(self, mock_get_client):
        from src.server import release_executor
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await release_executor(executor_id=3)
        data = json.loads(result)
        assert data["command_sent"] == "release executor 3"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_release_with_page(self, mock_get_client):
        from src.server import release_executor
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await release_executor(executor_id=5, page=2)
        data = json.loads(result)
        assert data["command_sent"] == "release executor 2.5"


class TestBlackoutToggle:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_blackout(self, mock_get_client):
        from src.server import blackout_toggle
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await blackout_toggle()
        data = json.loads(result)
        assert data["command_sent"] == "blackout"
        assert data["risk_tier"] == "SAFE_WRITE"


class TestListShows:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_shows(self, mock_get_client):
        from src.server import list_shows
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Show1\nShow2")
        mock_get_client.return_value = mock_client
        result = await list_shows()
        data = json.loads(result)
        assert data["command_sent"] == "listshows"
        assert data["risk_tier"] == "SAFE_READ"


class TestLoadShow:
    @pytest.mark.asyncio
    async def test_load_show_blocked(self):
        from src.server import load_show
        result = await load_show(name="myshow")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_load_show_confirmed(self, mock_get_client):
        from src.server import load_show
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await load_show(name="myshow", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'loadshow "myshow"'
        assert data["blocked"] is False


class TestNewShow:
    @pytest.mark.asyncio
    async def test_new_show_blocked(self):
        from src.server import new_show
        result = await new_show(name="fresh")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_new_show_confirmed_default_connectivity(self, mock_get_client):
        """Default preserve_connectivity=True auto-adds /globalsettings /protocols /network."""
        from src.server import new_show
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await new_show(name="fresh", confirm_destructive=True)
        data = json.loads(result)
        cmd = data["command_sent"]
        assert "/globalsettings" in cmd
        assert "/network" in cmd
        assert "/protocols" in cmd
        assert data["blocked"] is False
        assert data["preserve_connectivity"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_new_show_no_connectivity_preservation(self, mock_get_client):
        """preserve_connectivity=False: only /noconfirm, no keep flags unless explicit."""
        from src.server import new_show
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await new_show(name="fresh", confirm_destructive=True, preserve_connectivity=False)
        data = json.loads(result)
        assert data["command_sent"] == 'newshow "fresh" /noconfirm'
        assert data["blocked"] is False
        assert data["preserve_connectivity"] is False

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_new_show_all_keep_flags(self, mock_get_client):
        """All keep flags + preserve_connectivity=False → all six flags in command."""
        from src.server import new_show
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await new_show(
            name="fresh",
            confirm_destructive=True,
            preserve_connectivity=False,
            keep_timeconfig=True,
            keep_globalsettings=True,
            keep_localsettings=True,
            keep_protocols=True,
            keep_network=True,
            keep_user=True,
        )
        data = json.loads(result)
        cmd = data["command_sent"]
        assert cmd == 'newshow "fresh" /noconfirm /timeconfig /globalsettings /localsettings /protocols /network /user'
        assert data["blocked"] is False


class TestGetVariable:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_get_user_var(self, mock_get_client):
        from src.server import get_variable
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="5")
        mock_get_client.return_value = mock_client
        result = await get_variable(action="get_user", var_name="$mycounter")
        data = json.loads(result)
        assert data["command_sent"] == "getuservar $mycounter"
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_var(self, mock_get_client):
        from src.server import get_variable
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="vars")
        mock_get_client.return_value = mock_client
        result = await get_variable(action="list_var")
        data = json.loads(result)
        assert data["command_sent"] == "listvar"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_user_var(self, mock_get_client):
        from src.server import get_variable
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="vars")
        mock_get_client.return_value = mock_client
        result = await get_variable(action="list_user_var")
        data = json.loads(result)
        assert data["command_sent"] == "listuservar"

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        from src.server import get_variable
        result = await get_variable(action="invalid")
        data = json.loads(result)
        assert data["blocked"] is True

    @pytest.mark.asyncio
    async def test_get_user_missing_name(self):
        from src.server import get_variable
        result = await get_variable(action="get_user")
        data = json.loads(result)
        assert data["blocked"] is True


class TestListUndoHistory:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_oops(self, mock_get_client):
        from src.server import list_undo_history
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="undo history")
        mock_get_client.return_value = mock_client
        result = await list_undo_history()
        data = json.loads(result)
        assert data["command_sent"] == "listoops"
        assert data["risk_tier"] == "SAFE_READ"


# ============================================================
# Tools 65–69: Tier 2 — Setup & Library Tools
# ============================================================


class TestListFixtureTypes:
    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    @patch("src.server.get_client")
    async def test_list_fixture_types(self, mock_get_client, mock_navigate, mock_list_dest):
        from src.prompt_parser import ListEntry, ListOutput
        from src.server import list_fixture_types

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_nav = MagicMock()
        mock_nav.command_sent = "cd /"
        mock_navigate.return_value = mock_nav

        mock_list = MagicMock()
        mock_list.command_sent = "list"
        mock_list.raw_response = "FixtureType 1 Dimmer"
        mock_list.parsed_list = ListOutput(
            raw_response="FixtureType 1 Dimmer",
            entries=(
                ListEntry(object_type="FixtureType", object_id="1", name="Dimmer"),
            ),
        )
        mock_list_dest.return_value = mock_list

        result = await list_fixture_types()
        data = json.loads(result)
        assert data["risk_tier"] == "SAFE_READ"
        assert data["entry_count"] == 1
        assert data["entries"][0]["name"] == "Dimmer"


class TestListLayers:
    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    @patch("src.server.get_client")
    async def test_list_layers(self, mock_get_client, mock_navigate, mock_list_dest):
        from src.prompt_parser import ListOutput
        from src.server import list_layers

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_nav = MagicMock()
        mock_nav.command_sent = "cd /"
        mock_navigate.return_value = mock_nav

        mock_list = MagicMock()
        mock_list.command_sent = "list"
        mock_list.raw_response = "Layer 1 Auto-Created"
        mock_list.parsed_list = ListOutput(raw_response="Layer 1", entries=())
        mock_list_dest.return_value = mock_list

        result = await list_layers()
        data = json.loads(result)
        assert data["risk_tier"] == "SAFE_READ"
        assert "commands_sent" in data


class TestListUniverses:
    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    @patch("src.server.get_client")
    async def test_list_universes(self, mock_get_client, mock_navigate, mock_list_dest):
        from src.prompt_parser import ListEntry, ListOutput
        from src.server import list_universes

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_nav = MagicMock()
        mock_nav.command_sent = "cd /"
        mock_navigate.return_value = mock_nav

        mock_list = MagicMock()
        mock_list.command_sent = "list"
        mock_list.raw_response = "Universe 1"
        mock_list.parsed_list = ListOutput(
            raw_response="Universe 1",
            entries=(
                ListEntry(object_type="Universe", object_id="1", name="Universe"),
            ),
        )
        mock_list_dest.return_value = mock_list

        result = await list_universes(max_universes=4)
        data = json.loads(result)
        assert data["risk_tier"] == "SAFE_READ"
        assert data["entry_count"] == 1


class TestListLibrary:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fixture_library(self, mock_get_client):
        from src.server import list_library
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="library data")
        mock_get_client.return_value = mock_client
        result = await list_library(library_type="fixture")
        data = json.loads(result)
        assert data["command_sent"] == "listlibrary"
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_effect_library(self, mock_get_client):
        from src.server import list_library
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="effects")
        mock_get_client.return_value = mock_client
        result = await list_library(library_type="effect")
        data = json.loads(result)
        assert data["command_sent"] == "listeffectlibrary"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_macro_library(self, mock_get_client):
        from src.server import list_library
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="macros")
        mock_get_client.return_value = mock_client
        result = await list_library(library_type="macro")
        data = json.loads(result)
        assert data["command_sent"] == "listmacrolibrary"

    @pytest.mark.asyncio
    async def test_invalid_type(self):
        from src.server import list_library
        result = await list_library(library_type="invalid")
        data = json.loads(result)
        assert data["blocked"] is True


# ============================================================
# Tools 70–73: Tier 3 — Fixture Patching
# ============================================================


class TestBrowsePatchSchedule:
    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    @patch("src.server.get_client")
    async def test_browse_all(self, mock_get_client, mock_navigate, mock_list_dest):
        from src.prompt_parser import ListEntry, ListOutput
        from src.server import browse_patch_schedule

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_nav = MagicMock()
        mock_nav.command_sent = "cd /"
        mock_navigate.return_value = mock_nav
        mock_list = MagicMock()
        mock_list.command_sent = "list"
        mock_list.raw_response = "FixtureType 1 Dimmer"
        mock_list.parsed_list = ListOutput(
            raw_response="FixtureType 1 Dimmer",
            entries=(ListEntry(object_type="FixtureType", object_id="1", name="Dimmer"),),
        )
        mock_list_dest.return_value = mock_list

        result = await browse_patch_schedule()
        data = json.loads(result)
        assert data["risk_tier"] == "SAFE_READ"
        assert len(data["commands_sent"]) == 5

    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    @patch("src.server.get_client")
    async def test_browse_specific_type(self, mock_get_client, mock_navigate, mock_list_dest):
        from src.prompt_parser import ListOutput
        from src.server import browse_patch_schedule

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_nav = MagicMock()
        mock_nav.command_sent = "cd /"
        mock_navigate.return_value = mock_nav
        mock_list = MagicMock()
        mock_list.command_sent = "list"
        mock_list.raw_response = "instances"
        mock_list.parsed_list = ListOutput(raw_response="instances", entries=())
        mock_list_dest.return_value = mock_list

        result = await browse_patch_schedule(fixture_type_id=2)
        data = json.loads(result)
        assert data["risk_tier"] == "SAFE_READ"
        assert len(data["commands_sent"]) == 6


class TestPatchFixture:
    @pytest.mark.asyncio
    async def test_patch_blocked(self):
        from src.server import patch_fixture
        result = await patch_fixture(fixture_id=101, dmx_universe=1, dmx_address=1)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_patch_confirmed(self, mock_get_client):
        from src.server import patch_fixture
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await patch_fixture(
            fixture_id=101, dmx_universe=1, dmx_address=1,
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert data["blocked"] is False
        assert data["risk_tier"] == "DESTRUCTIVE"
        assert len(data["commands_sent"]) == 1  # just DMX assign
        assert "dmx" in data["commands_sent"][0].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_patch_with_fixture_type(self, mock_get_client):
        from src.server import patch_fixture
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await patch_fixture(
            fixture_id=101, dmx_universe=2, dmx_address=50,
            fixture_type_id=3, confirm_destructive=True,
        )
        data = json.loads(result)
        assert len(data["commands_sent"]) == 2  # fixture type assign + DMX assign


class TestUnpatchFixture:
    @pytest.mark.asyncio
    async def test_unpatch_blocked(self):
        from src.server import unpatch_fixture
        result = await unpatch_fixture(fixture_id=101)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_unpatch_confirmed(self, mock_get_client):
        from src.server import unpatch_fixture
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await unpatch_fixture(fixture_id=101, confirm_destructive=True)
        data = json.loads(result)
        assert data["blocked"] is False
        assert "delete fixture 101" in data["command_sent"]


class TestSetFixtureTypeProperty:
    @pytest.mark.asyncio
    async def test_blocked(self):
        from src.server import set_fixture_type_property
        result = await set_fixture_type_property(
            fixture_type_id=1, property_name="Name", value="Test",
        )
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.set_property", new_callable=AsyncMock)
    @patch("src.server.get_client")
    async def test_confirmed(self, mock_get_client, mock_set_prop):
        from src.navigation import SetPropertyResult
        from src.server import set_fixture_type_property

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_set_prop.return_value = SetPropertyResult(
            path="10.3.2",
            commands_sent=["cd /", "cd 10", "cd 3", 'assign 2/Name="NewName"', "cd /"],
            raw_responses=["ok"] * 5,
            success=True,
            verified_value="NewName",
        )

        result = await set_fixture_type_property(
            fixture_type_id=2, property_name="Name", value="NewName",
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert data["blocked"] is False
        assert data["success"] is True
        mock_set_prop.assert_called_once()


class TestStoreNewPresetScopeFlags:
    """Tests for universal/selective/global_scope flags on store_new_preset."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_universal_color_preset(self, mock_get_client):
        from src.server import store_new_preset

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="ok")
        mock_get_client.return_value = mock_client

        result = await store_new_preset(
            preset_type="color", preset_id=6,
            universal=True, overwrite=True,
            confirm_destructive=True,
        )
        data = json.loads(result)

        assert "/universal" in data["command_sent"]
        assert "/overwrite" in data["command_sent"]
        assert data["command_sent"].startswith("store preset 4.6")

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_selective_preset(self, mock_get_client):
        from src.server import store_new_preset

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="ok")
        mock_get_client.return_value = mock_client

        result = await store_new_preset(
            preset_type="position", preset_id=3,
            selective=True,
            confirm_destructive=True,
        )
        data = json.loads(result)

        assert "/selective" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_global_scope_preset(self, mock_get_client):
        from src.server import store_new_preset

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="ok")
        mock_get_client.return_value = mock_client

        result = await store_new_preset(
            preset_type="dimmer", preset_id=2,
            global_scope=True,
            confirm_destructive=True,
        )
        data = json.loads(result)

        assert "/global" in data["command_sent"]


class TestListPresetPoolTool:
    """Tests for the list_preset_pool MCP tool."""

    POOL_OVERVIEW_RAW = (
        "Executing : List\r\n"
        "PresetPool 0 ALL        (1)\r\n"
        "PresetPool 1 DIMMER\r\n"
        "PresetPool 4 COLOR      (5)\r\n"
        "Presets/Global  >\r\n"
    )

    COLOR_POOL_RAW = (
        "Executing : List\r\n"
        "Color 4.3 4.3  Red    Normal\r\n"
        "Color 4.4 4.4  Green  Normal\r\n"
        "Color 4.5 4.5  Blue   Normal\r\n"
        "Presets/Global /Color 4 >\r\n"
    )

    @pytest.mark.asyncio
    @patch("src.server.list_destination", new_callable=AsyncMock)
    @patch("src.server.navigate", new_callable=AsyncMock)
    async def test_overview_no_args(self, mock_navigate, mock_list_dest):
        from src.server import list_preset_pool

        mock_navigate.return_value = MagicMock()
        mock_lst = MagicMock()
        mock_lst.raw_response = self.POOL_OVERVIEW_RAW
        mock_lst.parsed_list = MagicMock()
        mock_lst.parsed_list.entries = []
        mock_list_dest.return_value = mock_lst

        result = await list_preset_pool()
        data = json.loads(result)

        assert data["cd_path"] == "17.1"
        assert data["risk_tier"] == "SAFE_READ"
        assert "Global PresetPool" in data["description"]

    @pytest.mark.asyncio
    @patch("src.server.list_destination", new_callable=AsyncMock)
    @patch("src.server.navigate", new_callable=AsyncMock)
    async def test_color_pool_by_name(self, mock_navigate, mock_list_dest):
        from src.server import list_preset_pool

        mock_navigate.return_value = MagicMock()
        mock_lst = MagicMock()
        mock_lst.raw_response = self.COLOR_POOL_RAW
        mock_lst.parsed_list = MagicMock()
        mock_lst.parsed_list.entries = []
        mock_list_dest.return_value = mock_lst

        result = await list_preset_pool(preset_type="color")
        data = json.loads(result)

        assert data["pool_index"] == 4
        assert data["cd_path"] == "17.1.4"

    @pytest.mark.asyncio
    @patch("src.server.list_destination", new_callable=AsyncMock)
    @patch("src.server.navigate", new_callable=AsyncMock)
    async def test_color_pool_by_number(self, mock_navigate, mock_list_dest):
        from src.server import list_preset_pool

        mock_navigate.return_value = MagicMock()
        mock_lst = MagicMock()
        mock_lst.raw_response = self.COLOR_POOL_RAW
        mock_lst.parsed_list = MagicMock()
        mock_lst.parsed_list.entries = []
        mock_list_dest.return_value = mock_lst

        result = await list_preset_pool(preset_type="4")
        data = json.loads(result)

        assert data["pool_index"] == 4

    @pytest.mark.asyncio
    @patch("src.server.navigate", new_callable=AsyncMock)
    async def test_unknown_preset_type_returns_error(self, mock_navigate):
        from src.server import list_preset_pool

        mock_navigate.return_value = MagicMock()

        result = await list_preset_pool(preset_type="bogus")
        data = json.loads(result)

        assert "error" in data


# ============================================================
# Safety Gate Blocking Tests
# ============================================================


class TestSafetyGateCreateFixtureGroup:
    """Test that create_fixture_group blocks without confirm_destructive."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import create_fixture_group

        result = await create_fixture_group(1, 10, 1)
        data = json.loads(result)
        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["risk_tier"]


class TestSafetyGateSetNodeProperty:
    """Test that set_node_property blocks without confirm_destructive."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import set_node_property

        result = await set_node_property("3.1", "Telnet", "Login Disabled")
        data = json.loads(result)
        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["risk_tier"]


class TestSafetyGateCopyOrMoveObject:
    """Test that copy_or_move_object blocks without confirm_destructive."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import copy_or_move_object

        result = await copy_or_move_object("copy", "group", 1, 5)
        data = json.loads(result)
        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["risk_tier"]


class TestSafetyGateGenerateFixtureLayerXml:
    """Test that generate_fixture_layer_xml blocks without confirm_destructive."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import generate_fixture_layer_xml

        result = await generate_fixture_layer_xml(
            "test", "Layer", 1, [{"fixture_id": 1, "name": "F1",
            "fixture_type_no": 1, "fixture_type_name": "FT",
            "dmx_address": 1, "num_channels": 1}]
        )
        data = json.loads(result)
        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["risk_tier"]


class TestManageMAtricksRefactored:
    """Test that refactored manage_matricks uses direct command keywords (SAFE_WRITE)."""

    @pytest.mark.asyncio
    async def test_invalid_action_returns_error(self):
        from src.server import manage_matricks

        result = await manage_matricks("nonexistent_action")
        data = json.loads(result)
        assert "error" in data
        assert "Unknown action" in data["error"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_no_confirm_destructive_needed(self, mock_get_client):
        """manage_matricks no longer requires confirm_destructive (SAFE_WRITE)."""
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client
        result = await manage_matricks("reset")
        data = json.loads(result)
        assert "blocked" not in data
        assert data["command_sent"] == "MAtricksReset"
        assert data["risk_tier"] == "SAFE_WRITE"


# ============================================================
# is_connected Property Tests
# ============================================================


class TestIsConnectedProperty:
    """Tests for GMA2TelnetClient.is_connected property."""

    def test_initially_disconnected(self):
        from src.telnet_client import GMA2TelnetClient
        client = GMA2TelnetClient("127.0.0.1", 30000)
        assert client.is_connected is False

    def test_connected_after_mock_setup(self):
        from src.telnet_client import GMA2TelnetClient
        client = GMA2TelnetClient("127.0.0.1", 30000)
        client._writer = MagicMock()
        client._connection = MagicMock()
        assert client.is_connected is True

    def test_disconnected_when_writer_none(self):
        from src.telnet_client import GMA2TelnetClient
        client = GMA2TelnetClient("127.0.0.1", 30000)
        client._writer = None
        client._connection = MagicMock()
        assert client.is_connected is False


# ============================================================
# store_cue sequence_id Builder Tests
# ============================================================


class TestStoreCueSequenceId:
    """Tests for the store_cue builder with sequence_id parameter."""

    def test_store_cue_with_sequence_id(self):
        from src.commands.functions.store import store_cue
        result = store_cue(5, sequence_id=99)
        assert result == "store cue 5 sequence 99"

    def test_store_cue_without_sequence_id(self):
        from src.commands.functions.store import store_cue
        result = store_cue(5)
        assert result == "store cue 5"

    def test_store_cue_sequence_with_options(self):
        from src.commands.functions.store import store_cue
        result = store_cue(5, sequence_id=1, merge=True)
        assert "store cue 5 sequence 1" in result
        assert "/merge" in result


# ============================================================
# store_matricks Builder Tests
# ============================================================


class TestStoreMAtricksBuilder:
    """Tests for the store_matricks command builder."""

    def test_basic_store(self):
        from src.commands.functions.store import store_matricks
        assert store_matricks(5) == "store matricks 5"

    def test_with_overwrite(self):
        from src.commands.functions.store import store_matricks
        assert store_matricks(10, overwrite=True) == "store matricks 10 /overwrite"

    def test_with_all_options(self):
        from src.commands.functions.store import store_matricks
        result = store_matricks(99, overwrite=True, noconfirm=True)
        assert result == "store matricks 99 /overwrite /noconfirm"


# ============================================================
# create_matricks_library Tool Tests
# ============================================================


class TestCreateMAtricksLibraryTool:
    """Tests for the create_matricks_library MCP tool."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import create_matricks_library

        result = await create_matricks_library(max_value=1)
        data = json.loads(result)
        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["risk_tier"]

    @pytest.mark.asyncio
    @patch("src.server._check_pool_slots", new_callable=AsyncMock)
    @patch("src.server.navigate", new_callable=AsyncMock)
    @patch("src.server.get_client")
    async def test_creates_with_embedded_colors(self, mock_get_client, mock_navigate, mock_check):
        from src.server import create_matricks_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        mock_navigate.return_value = MagicMock()
        mock_check.return_value = {"occupied_slots": [], "free_ranges": [], "next_free_slots": [],
                                   "total_occupied": 0, "total_free_in_range": 0,
                                   "largest_contiguous": 0, "can_fit": None, "suggested_start": None}

        result = await create_matricks_library(
            max_value=1, confirm_destructive=True,
        )
        data = json.loads(result)

        # 2^4 = 16 items for max_value=1
        assert data["pool_items_created"] == 16
        assert data["total_slots"] == 16
        assert data["max_value"] == 1
        assert data["color_scheme"]["status"] == "embedded_in_xml"

        # Only 1 import command — colors are in XML, no telnet loop
        assert mock_client.send_command_with_response.call_count == 1

    def test_naming_and_appearance_in_xml(self):
        """Verify the XML generator produces correct names and appearance colors."""
        from scripts.create_matricks_library import generate_xml

        xml_content, count = generate_xml(1)
        assert count == 16
        assert 'name="W0-G0-B0-I0"' in xml_content
        assert 'name="W1-G1-B1-I1"' in xml_content
        # Appearance Color embedded for each entry
        assert '<Appearance Color="' in xml_content
        assert 'wings="1" group_x="1" block_x="1" interleave="1"' in xml_content


class TestScopeEnforcement:
    """Verify that @require_scope blocks tools when GMA_SCOPE is insufficient."""

    @pytest.mark.asyncio
    async def test_user_manage_blocked_at_tier0(self, monkeypatch):
        """User management tools (tier:5) are blocked at tier:0."""
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import create_console_user

        result = await create_console_user(
            slot=3, name="test", password="pw", rights_level=1, confirm_destructive=True
        )
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["scope_required"] == "gma2:user:manage"

    @pytest.mark.asyncio
    async def test_state_read_allowed_at_tier0(self, monkeypatch):
        """Read-only tools (tier:0) pass scope check at tier:0 — use get_executor_status."""
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import get_executor_status

        with patch("src.server.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.send_command_with_response = AsyncMock(return_value="")
            mock_get_client.return_value = mock_client
            result = await get_executor_status(executor_id=1)

        data = json.loads(result)
        # Scope check passed — no scope_required key in result
        assert "scope_required" not in data

    @pytest.mark.asyncio
    async def test_user_manage_blocked_at_tier4(self, monkeypatch):
        """User management (tier:5) is blocked at tier:4."""
        monkeypatch.setenv("GMA_SCOPE", "tier:4")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import create_console_user

        result = await create_console_user(
            slot=3, name="test", password="pw", rights_level=1, confirm_destructive=True
        )
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["scope_required"] == "gma2:user:manage"

    @pytest.mark.asyncio
    async def test_user_manage_allowed_at_tier5(self, monkeypatch):
        """User management is accessible at tier:5."""
        monkeypatch.setenv("GMA_SCOPE", "tier:5")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import create_console_user

        with patch("src.server.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.send_command_with_response = AsyncMock(return_value="OK")
            mock_get_client.return_value = mock_client
            result = await create_console_user(
                slot=3, name="testuser", password="pw", rights_level=1, confirm_destructive=True
            )

        data = json.loads(result)
        # Scope check passed — the result should NOT have scope_required
        assert "scope_required" not in data

    @pytest.mark.asyncio
    async def test_bypass_overrides_scope_check(self, monkeypatch):
        """GMA_AUTH_BYPASS=1 grants all scopes regardless of GMA_SCOPE."""
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import create_console_user

        with patch("src.server.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.send_command_with_response = AsyncMock(return_value="OK")
            mock_get_client.return_value = mock_client
            result = await create_console_user(
                slot=3, name="testuser", password="pw", rights_level=1, confirm_destructive=True
            )

        data = json.loads(result)
        assert "scope_required" not in data

    @pytest.mark.asyncio
    async def test_scope_and_destructive_are_independent(self, monkeypatch):
        """Scope block and destructive block are checked independently — scope runs first."""
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import create_console_user

        # No confirm_destructive AND no scope — should get scope error (checked first)
        result = await create_console_user(
            slot=3, name="test", password="pw", rights_level=1
        )
        data = json.loads(result)
        assert data["blocked"] is True
        # Scope check fires before destructive check because @require_scope wraps @_handle_errors
        assert "scope_required" in data

    @pytest.mark.asyncio
    async def test_list_console_users_scope_is_user_manage(self, monkeypatch):
        """list_console_users now requires gma2:user:manage (tier:5) — user data is sensitive."""
        monkeypatch.setenv("GMA_SCOPE", "tier:4")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import list_console_users

        result = await list_console_users()

        # Should be scope-blocked at tier:4 — requires tier:5 (user:manage)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["scope_required"] == "gma2:user:manage"


# ── store_world / label_world ────────────────────────────────────────────────

class TestStoreWorldTool:
    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import store_world
        result = json.loads(await store_world(world_id=5))
        assert result["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_store_command(self, mock_get_client):
        from src.server import store_world
        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = client

        result = json.loads(await store_world(world_id=5, confirm_destructive=True))
        assert "store world 5" in result["commands_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_overwrite_flag(self, mock_get_client):
        from src.server import store_world
        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = client

        result = json.loads(await store_world(world_id=3, overwrite=True, confirm_destructive=True))
        assert "store world 3 /overwrite" in result["commands_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_with_name_sends_two_commands(self, mock_get_client):
        from src.server import store_world
        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = client

        result = json.loads(await store_world(world_id=5, name="Stage Left", confirm_destructive=True))
        assert len(result["commands_sent"]) == 2
        assert result["commands_sent"][0] == "store world 5"
        assert "Stage Left" in result["commands_sent"][1]


class TestLabelWorldTool:
    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import label_world
        result = json.loads(await label_world(world_id=3, name="FOH"))
        assert result["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_label_command(self, mock_get_client):
        from src.server import label_world
        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = client

        result = json.loads(await label_world(world_id=3, name="Stage Left", confirm_destructive=True))
        assert "Stage Left" in result["command_sent"]
        assert "world" in result["command_sent"]


# ── store_agenda ─────────────────────────────────────────────────────────────

class TestStoreAgendaTool:
    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import store_agenda
        result = json.loads(await store_agenda(agenda_id=1))
        assert result["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_store_command(self, mock_get_client):
        from src.server import store_agenda
        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = client

        result = json.loads(await store_agenda(agenda_id=1, confirm_destructive=True))
        assert "store agenda 1" in result["commands_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_with_name_sends_two_commands(self, mock_get_client):
        from src.server import store_agenda
        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = client

        result = json.loads(await store_agenda(agenda_id=2, name="Song A", confirm_destructive=True))
        assert len(result["commands_sent"]) == 2
        assert result["commands_sent"][0] == "store agenda 2"
        assert "Song A" in result["commands_sent"][1]
