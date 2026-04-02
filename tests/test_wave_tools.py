"""
Tests for Wave 1-5 MCP tools added to src/server.py.

Covers:
- Wave 1: console_login, console_logout, lock_console_ui, unlock_console_ui
- Wave 2: list_layouts, list_worlds, list_timers, list_filters,
          list_effects_pool, list_images, list_forms, list_timecode_events
- Wave 3: control_chaser, set_effect_param
- Wave 4: call_plugin_tool, run_lua_script, reload_all_plugins, control_special_master
- Wave 5: rdm_discover, rdm_get_info, rdm_patch
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_client(response="OK"):
    mock_client = MagicMock()
    mock_client.send_command_with_response = AsyncMock(return_value=response)
    return mock_client


# ============================================================
# Wave 1 — Console Session & UI Lock
# ============================================================


class TestConsoleLogin:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_login_command(self, mock_get_client):
        from src.server import console_login

        client = _mock_client("Logged in")
        mock_get_client.return_value = client

        result_str = await console_login("operator", "pw123")
        result = json.loads(result_str)

        assert result["command_sent"] == 'Login "operator" "pw123"'
        assert result["raw_response"] == "Logged in"


class TestConsoleLogout:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_logout_command(self, mock_get_client):
        from src.server import console_logout

        client = _mock_client("Logged out")
        mock_get_client.return_value = client

        result_str = await console_logout()
        result = json.loads(result_str)

        assert result["command_sent"] == "Logout"


class TestLockConsoleUI:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_lock_command(self, mock_get_client):
        from src.server import lock_console_ui

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await lock_console_ui()
        result = json.loads(result_str)

        assert result["command_sent"] == "Lock"


class TestUnlockConsoleUI:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_unlock_no_password(self, mock_get_client):
        from src.server import unlock_console_ui

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await unlock_console_ui()
        result = json.loads(result_str)
        assert result["command_sent"] == "Unlock"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_unlock_with_password(self, mock_get_client):
        from src.server import unlock_console_ui

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await unlock_console_ui("1234")
        result = json.loads(result_str)
        assert result["command_sent"] == 'Unlock "1234"'


# ============================================================
# Wave 2 — Read-only list tools
# ============================================================


@pytest.mark.parametrize("tool_name,expected_cmd", [
    ("list_layouts", "list Layout"),
    ("list_worlds", "list World"),
    ("list_timers", "list Timer"),
    ("list_filters", "list Filter"),
    ("list_effects_pool", "list Effect"),
    ("list_images", "list Image"),
    ("list_forms", "list Form"),
    ("list_timecode_events", "list Timecode"),
    ("list_agenda_events", "list Agenda"),
])
class TestWave2ListTools:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_command_sent(self, mock_get_client, tool_name, expected_cmd):
        import src.server as server_module

        client = _mock_client("data")
        mock_get_client.return_value = client

        tool_fn = getattr(server_module, tool_name)
        result_str = await tool_fn()
        result = json.loads(result_str)

        assert result["command_sent"] == expected_cmd
        assert result["raw_response"] == "data"


# ============================================================
# Wave 3 — Chaser control & Effect parameters
# ============================================================


class TestControlChaser:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_rate(self, mock_get_client):
        from src.server import control_chaser

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await control_chaser("rate", value=100)
        result = json.loads(result_str)
        assert result["command_sent"] == "Rate 100"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_speed(self, mock_get_client):
        from src.server import control_chaser

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await control_chaser("speed", value=120, executor_id=201)
        result = json.loads(result_str)
        assert result["command_sent"] == "Speed 120 Executor 1.201"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_skip_fwd(self, mock_get_client):
        from src.server import control_chaser

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await control_chaser("skip_fwd")
        result = json.loads(result_str)
        assert result["command_sent"] == "SkipPlus"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_skip_bk(self, mock_get_client):
        from src.server import control_chaser

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await control_chaser("skip_bk", executor_id=201)
        result = json.loads(result_str)
        assert result["command_sent"] == "SkipMinus Executor 1.201"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_xfade_ab(self, mock_get_client):
        from src.server import control_chaser

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await control_chaser("xfade_ab")
        result = json.loads(result_str)
        assert result["command_sent"] == "CrossFadeAB"

    @pytest.mark.asyncio
    async def test_rate_missing_value_returns_error(self):
        from src.server import control_chaser

        result_str = await control_chaser("rate")
        result = json.loads(result_str)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self):
        from src.server import control_chaser

        result_str = await control_chaser("dance")
        result = json.loads(result_str)
        assert "error" in result


class TestSetEffectParam:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_bpm(self, mock_get_client):
        from src.server import set_effect_param

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await set_effect_param("bpm", 120)
        result = json.loads(result_str)
        assert result["command_sent"] == "EffectBPM 120"

    @pytest.mark.asyncio
    async def test_invalid_param_returns_error(self):
        from src.server import set_effect_param

        result_str = await set_effect_param("invalid", 50)
        result = json.loads(result_str)
        assert "error" in result


# ============================================================
# Wave 4 — Plugin / Lua / Special Master
# ============================================================


class TestCallPluginTool:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_call_by_id(self, mock_get_client):
        from src.server import call_plugin_tool

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await call_plugin_tool(1, confirm_destructive=True)
        result = json.loads(result_str)
        assert result["command_sent"] == "Plugin 1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_call_by_name(self, mock_get_client):
        from src.server import call_plugin_tool

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await call_plugin_tool("MyPlugin", confirm_destructive=True)
        result = json.loads(result_str)
        assert result["command_sent"] == 'Plugin "MyPlugin"'


class TestRunLuaScript:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_simple_script(self, mock_get_client):
        from src.server import run_lua_script

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await run_lua_script('print("hi")', confirm_destructive=True)
        result = json.loads(result_str)
        assert "Lua" in result["command_sent"]


class TestReloadAllPlugins:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_reload(self, mock_get_client):
        from src.server import reload_all_plugins

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await reload_all_plugins(confirm_destructive=True)
        result = json.loads(result_str)
        assert result["command_sent"] == "ReloadPlugins"


class TestControlSpecialMaster:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_grandmaster(self, mock_get_client):
        from src.server import control_special_master

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await control_special_master("grandmaster", 80)
        result = json.loads(result_str)
        assert result["command_sent"] == "SpecialMaster GrandMaster At 80"

    @pytest.mark.asyncio
    async def test_invalid_master_returns_error(self):
        from src.server import control_special_master

        result_str = await control_special_master("invalid", 50)
        result = json.loads(result_str)
        assert "error" in result
        assert "valid_masters" in result


# ============================================================
# Wave 5 — RDM
# ============================================================


class TestRdmDiscover:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_automatch(self, mock_get_client):
        from src.server import rdm_discover

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await rdm_discover("automatch")
        result = json.loads(result_str)
        assert result["command_sent"] == "RdmAutomatch"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_autopatch(self, mock_get_client):
        from src.server import rdm_discover

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await rdm_discover("autopatch")
        result = json.loads(result_str)
        assert result["command_sent"] == "RdmAutopatch"

    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self):
        from src.server import rdm_discover

        result_str = await rdm_discover("magic")
        result = json.loads(result_str)
        assert "error" in result


class TestRdmGetInfo:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_all(self, mock_get_client):
        from src.server import rdm_get_info

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await rdm_get_info()
        result = json.loads(result_str)
        assert result["command_sent"] == "RdmList"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_universe(self, mock_get_client):
        from src.server import rdm_get_info

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await rdm_get_info(universe=2)
        result = json.loads(result_str)
        assert result["command_sent"] == "RdmList Universe 2"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fixture_info(self, mock_get_client):
        from src.server import rdm_get_info

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await rdm_get_info(fixture_id=101)
        result = json.loads(result_str)
        assert result["command_sent"] == "RdmInfo Fixture 101"


class TestRdmPatch:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_setpatch(self, mock_get_client):
        from src.server import rdm_patch

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await rdm_patch(101, "setpatch", universe=1, address=1, confirm_destructive=True)
        result = json.loads(result_str)
        assert result["command_sent"] == "RdmSetpatch Fixture 101 Universe 1 Address 1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_unmatch(self, mock_get_client):
        from src.server import rdm_patch

        client = _mock_client()
        mock_get_client.return_value = client

        result_str = await rdm_patch(101, "unmatch", confirm_destructive=True)
        result = json.loads(result_str)
        assert result["command_sent"] == "RdmUnmatch Fixture 101"

    @pytest.mark.asyncio
    async def test_setpatch_missing_universe_returns_error(self):
        from src.server import rdm_patch

        result_str = await rdm_patch(101, "setpatch", address=1)
        result = json.loads(result_str)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self):
        from src.server import rdm_patch

        result_str = await rdm_patch(101, "magic")
        result = json.loads(result_str)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_setpatch_missing_address_returns_error(self):
        from src.server import rdm_patch

        result_str = await rdm_patch(101, "setpatch", universe=1)
        result = json.loads(result_str)
        assert "error" in result


# ============================================================
# Additional branch-coverage for control_chaser
# ============================================================


class TestControlChaserBranchCoverage:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_xfade_a(self, mock_get_client):
        from src.server import control_chaser

        client = _mock_client()
        mock_get_client.return_value = client
        result = json.loads(await control_chaser("xfade_a"))
        assert result["command_sent"] == "CrossFadeA"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_xfade_b(self, mock_get_client):
        from src.server import control_chaser

        client = _mock_client()
        mock_get_client.return_value = client
        result = json.loads(await control_chaser("xfade_b"))
        assert result["command_sent"] == "CrossFadeB"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_skip_fwd_with_executor_and_page(self, mock_get_client):
        from src.server import control_chaser

        client = _mock_client()
        mock_get_client.return_value = client
        result = json.loads(await control_chaser("skip_fwd", executor_id=201, page=2))
        assert result["command_sent"] == "SkipPlus Executor 2.201"

    @pytest.mark.asyncio
    async def test_speed_missing_value_returns_error(self):
        from src.server import control_chaser

        result = json.loads(await control_chaser("speed"))
        assert "error" in result

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_case_insensitive_action(self, mock_get_client):
        from src.server import control_chaser

        client = _mock_client()
        mock_get_client.return_value = client
        result = json.loads(await control_chaser("RATE", value=100))
        assert result["command_sent"] == "Rate 100"


# ============================================================
# Additional branch-coverage for control_special_master
# ============================================================


class TestControlSpecialMasterBranchCoverage:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_speed_master(self, mock_get_client):
        from src.server import control_special_master

        client = _mock_client()
        mock_get_client.return_value = client
        result = json.loads(await control_special_master("speed1", 120))
        assert result["command_sent"] == "SpecialMaster Speed1Master At 120"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_rate_master(self, mock_get_client):
        from src.server import control_special_master

        client = _mock_client()
        mock_get_client.return_value = client
        result = json.loads(await control_special_master("rate1", 100))
        assert result["command_sent"] == "SpecialMaster Rate1Master At 100"

    @pytest.mark.asyncio
    async def test_error_includes_valid_masters_list(self):
        from src.server import control_special_master

        result = json.loads(await control_special_master("bogus", 50))
        assert "error" in result
        assert "valid_masters" in result
        assert "grandmaster" in result["valid_masters"]
