"""
New MCP Tool Tests — swop/top/stomp, load_cue, cut_paste_object,
clone_object, fix_locate_fixture, manipulate_selection, block_unblock_cue.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestControlExecutorExtendedActions:
    """Tests for new swop, top, stomp actions on control_executor."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_executor_swop(self, mock_get_client):
        from src.server import control_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_executor(action="swop", executor_id=3)
        data = json.loads(result)

        assert data["risk_tier"] == "SAFE_WRITE"
        assert data["command_sent"] == "swop executor 3"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_executor_top(self, mock_get_client):
        from src.server import control_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_executor(action="top", executor_id=3)
        data = json.loads(result)

        assert data["risk_tier"] == "SAFE_WRITE"
        assert data["command_sent"] == "top executor 3"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_control_executor_stomp(self, mock_get_client):
        from src.server import control_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await control_executor(action="stomp", executor_id=3)
        data = json.loads(result)

        assert data["risk_tier"] == "SAFE_WRITE"
        assert data["command_sent"] == "stomp executor 3"

    @pytest.mark.asyncio
    async def test_control_executor_invalid_action_still_rejected(self):
        from src.server import control_executor

        result = await control_executor(action="pause", executor_id=1)
        data = json.loads(result)
        assert "error" in data


class TestLoadCueTool:
    """Tests for the load_cue MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_load_cue_next_bare(self, mock_get_client):
        from src.server import load_cue

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await load_cue(direction="next")
        data = json.loads(result)

        assert data["command_sent"] == "loadnext"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_load_cue_next_executor(self, mock_get_client):
        from src.server import load_cue

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await load_cue(direction="next", executor_id=5)
        data = json.loads(result)

        assert data["command_sent"] == "loadnext executor 5"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_load_cue_prev_sequence(self, mock_get_client):
        from src.server import load_cue

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await load_cue(direction="prev", sequence_id=3)
        data = json.loads(result)

        assert data["command_sent"] == "loadprev sequence 3"

    @pytest.mark.asyncio
    async def test_load_cue_invalid_direction(self):
        from src.server import load_cue

        result = await load_cue(direction="forward")
        data = json.loads(result)
        assert "error" in data


class TestCutPasteObjectTool:
    """Tests for the cut_paste_object MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_cut_group(self, mock_get_client):
        from src.server import cut_paste_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await cut_paste_object(action="cut", object_type="group", object_id=1)
        data = json.loads(result)

        assert data["command_sent"] == "cut group 1"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_paste_to_target(self, mock_get_client):
        from src.server import cut_paste_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await cut_paste_object(action="paste", object_type="group", target_id=5)
        data = json.loads(result)

        assert data["command_sent"] == "paste group 5"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_paste_bare(self, mock_get_client):
        from src.server import cut_paste_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await cut_paste_object(action="paste")
        data = json.loads(result)

        assert data["command_sent"] == "paste"

    @pytest.mark.asyncio
    async def test_cut_missing_object_type(self):
        from src.server import cut_paste_object

        result = await cut_paste_object(action="cut")
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        from src.server import cut_paste_object

        result = await cut_paste_object(action="copy")
        data = json.loads(result)
        assert "error" in data


class TestCloneObjectTool:
    """Tests for the clone_object MCP tool (DESTRUCTIVE)."""

    @pytest.mark.asyncio
    async def test_clone_blocked_without_confirmation(self):
        from src.server import clone_object

        result = await clone_object(object_type="fixture", object_id=1, target_id=2)
        data = json.loads(result)

        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_clone_fixture_confirmed(self, mock_get_client):
        from src.server import clone_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await clone_object(
            object_type="fixture", object_id=1, target_id=2,
            confirm_destructive=True,
        )
        data = json.loads(result)

        assert data["command_sent"] == "clone fixture 1 at 2"
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_clone_with_range_and_noconfirm(self, mock_get_client):
        from src.server import clone_object

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await clone_object(
            object_type="fixture", object_id=1, target_id=10,
            end=5, noconfirm=True, confirm_destructive=True,
        )
        data = json.loads(result)

        assert data["command_sent"] == "clone fixture 1 thru 5 at 10 /noconfirm"


class TestFixLocateFixtureTool:
    """Tests for the fix_locate_fixture MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fix_selection(self, mock_get_client):
        from src.server import fix_locate_fixture

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await fix_locate_fixture(action="fix")
        data = json.loads(result)

        assert data["command_sent"] == "fix"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fix_specific_fixtures(self, mock_get_client):
        from src.server import fix_locate_fixture

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await fix_locate_fixture(action="fix", fixture_ids=[1, 3, 5])
        data = json.loads(result)

        assert data["command_sent"] == "fix fixture 1 + 3 + 5"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fix_single_with_end(self, mock_get_client):
        from src.server import fix_locate_fixture

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await fix_locate_fixture(action="fix", fixture_ids=[1], end=10)
        data = json.loads(result)

        assert data["command_sent"] == "fix fixture 1 thru 10"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_locate(self, mock_get_client):
        from src.server import fix_locate_fixture

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await fix_locate_fixture(action="locate")
        data = json.loads(result)

        assert data["command_sent"] == "locate"

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        from src.server import fix_locate_fixture

        result = await fix_locate_fixture(action="park")
        data = json.loads(result)
        assert "error" in data


class TestManipulateSelectionTool:
    """Tests for the manipulate_selection MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_invert(self, mock_get_client):
        from src.server import manipulate_selection

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await manipulate_selection(action="invert")
        data = json.loads(result)

        assert data["command_sent"] == "invert"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_align(self, mock_get_client):
        from src.server import manipulate_selection

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await manipulate_selection(action="align")
        data = json.loads(result)

        assert data["command_sent"] == "align"

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        from src.server import manipulate_selection

        result = await manipulate_selection(action="sort")
        data = json.loads(result)
        assert "error" in data


class TestBlockUnblockCueTool:
    """Tests for the block_unblock_cue MCP tool (DESTRUCTIVE)."""

    @pytest.mark.asyncio
    async def test_block_blocked_without_confirmation(self):
        from src.server import block_unblock_cue

        result = await block_unblock_cue(action="block", cue_id=5)
        data = json.loads(result)

        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    async def test_unblock_blocked_without_confirmation(self):
        from src.server import block_unblock_cue

        result = await block_unblock_cue(action="unblock", cue_id=5)
        data = json.loads(result)

        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_block_cue_confirmed(self, mock_get_client):
        from src.server import block_unblock_cue

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await block_unblock_cue(
            action="block", cue_id=5, confirm_destructive=True,
        )
        data = json.loads(result)

        assert data["command_sent"] == "block cue 5"
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_unblock_cue_with_sequence(self, mock_get_client):
        from src.server import block_unblock_cue

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await block_unblock_cue(
            action="unblock", cue_id=3, sequence_id=1, confirm_destructive=True,
        )
        data = json.loads(result)

        assert data["command_sent"] == "unblock cue 3 sequence 1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_block_cue_range(self, mock_get_client):
        from src.server import block_unblock_cue

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await block_unblock_cue(
            action="block", cue_id=1, end=5, confirm_destructive=True,
        )
        data = json.loads(result)

        assert data["command_sent"] == "block cue 1 thru 5"

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        from src.server import block_unblock_cue

        result = await block_unblock_cue(action="freeze", cue_id=1)
        data = json.loads(result)
        assert "error" in data


# ── Tools 103–109: Quick-wins sprint ──────────────────────────────────────────


class TestBrowseEffectLibraryTool:
    """Tests for browse_effect_library MCP tool (tool 103)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_listeffectlibrary(self, mock_get_client):
        from src.server import browse_effect_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Effect Library:\nFire")
        mock_get_client.return_value = mock_client

        result = await browse_effect_library()
        data = json.loads(result)

        assert data["command_sent"] == "listeffectlibrary"
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    async def test_blocked_without_scope(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "gma2:unknown:scope")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import browse_effect_library

        result = await browse_effect_library()
        data = json.loads(result)
        assert data["blocked"] is True


class TestBrowseMacroLibraryTool:
    """Tests for browse_macro_library MCP tool (tool 104)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_listmacrolibrary(self, mock_get_client):
        from src.server import browse_macro_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Macro Library:\nFoo")
        mock_get_client.return_value = mock_client

        result = await browse_macro_library()
        data = json.loads(result)

        assert data["command_sent"] == "listmacrolibrary"
        assert data["risk_tier"] == "SAFE_READ"


class TestBrowsePluginLibraryTool:
    """Tests for browse_plugin_library MCP tool (tool 105)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_listpluginlibrary(self, mock_get_client):
        from src.server import browse_plugin_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Plugin Library:\nBar")
        mock_get_client.return_value = mock_client

        result = await browse_plugin_library()
        data = json.loads(result)

        assert data["command_sent"] == "listpluginlibrary"
        assert data["risk_tier"] == "SAFE_READ"


class TestListFaderModulesTool:
    """Tests for list_fader_modules MCP tool (tool 106)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_listfadermodules(self, mock_get_client):
        from src.server import list_fader_modules

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="No fader modules")
        mock_get_client.return_value = mock_client

        result = await list_fader_modules()
        data = json.loads(result)

        assert data["command_sent"] == "listfadermodules"
        assert data["risk_tier"] == "SAFE_READ"


class TestListUpdateHistoryTool:
    """Tests for list_update_history MCP tool (tool 107)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_listupdate(self, mock_get_client):
        from src.server import list_update_history

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Update history")
        mock_get_client.return_value = mock_client

        result = await list_update_history()
        data = json.loads(result)

        assert data["command_sent"] == "listupdate"
        assert data["risk_tier"] == "SAFE_READ"


class TestDeleteShowTool:
    """Tests for delete_show MCP tool (tool 108)."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import delete_show

        result = await delete_show(name="old_show")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_deletes_show_with_noconfirm(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import delete_show

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await delete_show(name="old_show", confirm_destructive=True)
        data = json.loads(result)

        assert data["command_sent"] == 'deleteshow "old_show" /noconfirm'
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    async def test_blocked_without_scope(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:4")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import delete_show

        result = await delete_show(name="old_show", confirm_destructive=True)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["scope_required"] == "gma2:show:load"


class TestAssignTempFaderTool:
    """Tests for assign_temp_fader MCP tool (tool 109)."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_tempfader_default(self, mock_get_client):
        from src.server import assign_temp_fader

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await assign_temp_fader()
        data = json.loads(result)

        assert data["command_sent"] == "tempfader 50"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_tempfader_value(self, mock_get_client):
        from src.server import assign_temp_fader

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await assign_temp_fader(value=75)
        data = json.loads(result)

        assert data["command_sent"] == "tempfader 75"

    @pytest.mark.asyncio
    async def test_blocked_without_scope(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import assign_temp_fader

        result = await assign_temp_fader(value=50)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["scope_required"] == "gma2:executor:control"

    @pytest.mark.asyncio
    async def test_out_of_range_high(self):
        from src.server import assign_temp_fader

        result = await assign_temp_fader(value=101)
        data = json.loads(result)
        assert data["blocked"] is True
        assert "101" in data["error"]

    @pytest.mark.asyncio
    async def test_out_of_range_negative(self):
        from src.server import assign_temp_fader

        result = await assign_temp_fader(value=-1)
        data = json.loads(result)
        assert data["blocked"] is True
        assert "-1" in data["error"]


# ---------------------------------------------------------------------------
# playback_action — multi-executor list support (Gap 1)
# ---------------------------------------------------------------------------

class TestPlaybackActionMultiExecutor:
    """Tests for playback_action MCP tool with list[int] executor/object_id."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fast_forward_executor_list(self, mock_get_client):
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(action="fast_forward", executor=[1, 2, 3])
        data = json.loads(result)
        assert data["command_sent"] == ">>> executor 1 + 2 + 3"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_fast_back_executor_list(self, mock_get_client):
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(action="fast_back", executor=[2, 4])
        data = json.loads(result)
        assert data["command_sent"] == "<<< executor 2 + 4"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_go_object_id_list(self, mock_get_client):
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(
            action="go", object_type="executor", object_id=[1, 2, 3]
        )
        data = json.loads(result)
        assert data["command_sent"] == "go executor 1 + 2 + 3"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_go_back_object_id_list(self, mock_get_client):
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await playback_action(
            action="go_back", object_type="executor", object_id=[5, 6]
        )
        data = json.loads(result)
        assert data["command_sent"] == "goback executor 5 + 6"


# ---------------------------------------------------------------------------
# playback_action — def_go/def_go_back/def_pause read $SELECTEDEXEC (Gap 2)
# ---------------------------------------------------------------------------

_LISTVAR_EXEC5 = (
    "$Global : $SELECTEDEXEC = 5\n"
    "$Global : $SELECTEDEXECCUE = 3\n"
    "[channel]>"
)
_LISTVAR_EXEC7 = (
    "$Global : $SELECTEDEXEC = 7\n"
    "$Global : $SELECTEDEXECCUE = 1\n"
    "[channel]>"
)


class TestPlaybackActionDefGoReadsSelectedExec:
    """Tests that def_go / def_go_back / def_pause read $SELECTEDEXEC before firing."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_def_go_includes_selected_exec(self, mock_get_client):
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=[_LISTVAR_EXEC5, "[channel]>"]
        )
        mock_get_client.return_value = mock_client

        result = await playback_action(action="def_go")
        data = json.loads(result)

        assert data["command_sent"] == "defgoforward"
        assert data["selected_executor"] == "5"
        assert data["selected_cue_before"] == "3"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_def_pause_includes_selected_exec(self, mock_get_client):
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=[_LISTVAR_EXEC7, "[channel]>"]
        )
        mock_get_client.return_value = mock_client

        result = await playback_action(action="def_pause")
        data = json.loads(result)

        assert data["command_sent"] == "defgopause"
        assert data["selected_executor"] == "7"
        assert data["selected_cue_before"] == "1"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_def_go_back_fires_defgoback(self, mock_get_client):
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=[_LISTVAR_EXEC5, "[channel]>"]
        )
        mock_get_client.return_value = mock_client

        result = await playback_action(action="def_go_back")
        data = json.loads(result)

        assert data["command_sent"] == "defgoback"
        assert data["selected_executor"] == "5"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_def_goback_alias(self, mock_get_client):
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=[_LISTVAR_EXEC5, "[channel]>"]
        )
        mock_get_client.return_value = mock_client

        result = await playback_action(action="def_goback")
        data = json.loads(result)

        assert data["command_sent"] == "defgoback"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_def_go_selected_exec_none_when_listvar_empty(self, mock_get_client):
        from src.server import playback_action

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=["[channel]>", "[channel]>"]
        )
        mock_get_client.return_value = mock_client

        result = await playback_action(action="def_go")
        data = json.loads(result)

        assert data["command_sent"] == "defgoforward"
        assert data["selected_executor"] is None
        assert data["selected_cue_before"] is None


# ---------------------------------------------------------------------------
# select_executor — $SELECTEDEXEC readback confirmation (Gap 3)
# ---------------------------------------------------------------------------

_LISTVAR_SEL5 = "$Global : $SELECTEDEXEC = 5\n[channel]>"
_LISTVAR_SEL3 = "$Global : $SELECTEDEXEC = 3\n[channel]>"


class TestSelectExecutorConfirmation:
    """Tests that select_executor reads back $SELECTEDEXEC to confirm selection."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_executor_confirmed_match(self, mock_get_client):
        from src.server import select_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=["[channel]>", _LISTVAR_SEL5]
        )
        mock_get_client.return_value = mock_client

        result = await select_executor(executor_id=5)
        data = json.loads(result)

        assert data["command_sent"] == "select executor 5"
        assert data["confirmed_selected_exec"] == "5"
        assert "warning" not in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_executor_warning_on_mismatch(self, mock_get_client):
        from src.server import select_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=["[channel]>", _LISTVAR_SEL3]
        )
        mock_get_client.return_value = mock_client

        result = await select_executor(executor_id=7)
        data = json.loads(result)

        assert data["confirmed_selected_exec"] == "3"
        assert "warning" in data
        assert "7" in data["warning"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_executor_warning_when_listvar_empty(self, mock_get_client):
        from src.server import select_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=["[channel]>", "[channel]>"]
        )
        mock_get_client.return_value = mock_client

        result = await select_executor(executor_id=2)
        data = json.loads(result)

        assert data["confirmed_selected_exec"] is None
        assert "warning" in data

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_select_executor_page_no_warning(self, mock_get_client):
        """page=2/exec=5 → command 'select executor 2.5'; $SELECTEDEXEC='5' → no warning."""
        from src.server import select_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=["[channel]>", _LISTVAR_SEL5]
        )
        mock_get_client.return_value = mock_client

        result = await select_executor(executor_id=5, page=2)
        data = json.loads(result)

        assert data["command_sent"] == "select executor 2.5"
        assert data["confirmed_selected_exec"] == "5"
        assert "warning" not in data


# ---------------------------------------------------------------------------
# select_executor — deselect parameter (Gap 4)
# ---------------------------------------------------------------------------

class TestSelectExecutorDeselect:
    """Tests for select_executor deselect=True parameter."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_deselect_sends_bare_select(self, mock_get_client):
        from src.server import select_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=["[channel]>", "[channel]>"]
        )
        mock_get_client.return_value = mock_client

        result = await select_executor(executor_id=1, deselect=True)
        data = json.loads(result)

        assert data["command_sent"] == "select"
        assert "note" in data
        assert "unverified" in data["note"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_deselect_ignores_executor_id(self, mock_get_client):
        """When deselect=True, executor_id must not appear in the command."""
        from src.server import select_executor

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            side_effect=["[channel]>", "[channel]>"]
        )
        mock_get_client.return_value = mock_client

        result = await select_executor(executor_id=99, deselect=True)
        data = json.loads(result)

        assert data["command_sent"] == "select"
        assert "99" not in data["command_sent"]
