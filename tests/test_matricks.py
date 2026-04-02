"""
MAtricks Command Builder & MCP Tool Tests

Tests for all MAtricks command builder functions and the refactored
manage_matricks MCP tool. All keywords live-validated against grandMA2
onPC v3.9.60.65 (2026-03-11).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.commands import (
    all_rows_sub_selection,
    all_sub_selection,
    matricks_blocks,
    matricks_filter,
    matricks_groups,
    matricks_interleave,
    matricks_reset,
    matricks_wings,
    next_row_sub_selection,
    next_sub_selection,
    previous_sub_selection,
    recall_matricks,
)

# ============================================================
# MAtricksInterleave Builder Tests
# ============================================================


class TestMAtricksInterleave:
    """Tests for matricks_interleave() command builder."""

    def test_bare(self):
        assert matricks_interleave() == "MAtricksInterleave"

    def test_width(self):
        assert matricks_interleave(width=2) == "MAtricksInterleave 2"

    def test_width_large(self):
        assert matricks_interleave(width=10) == "MAtricksInterleave 10"

    def test_column_dot_width(self):
        assert matricks_interleave(width=2, column=1) == "MAtricksInterleave 1.2"

    def test_column_without_width_raises(self):
        with pytest.raises(ValueError, match="column requires width"):
            matricks_interleave(column=1)

    def test_increment_plus(self):
        assert matricks_interleave(increment="+") == "MAtricksInterleave +"

    def test_increment_minus(self):
        assert matricks_interleave(increment="-") == "MAtricksInterleave -"

    def test_off(self):
        assert matricks_interleave(off=True) == "MAtricksInterleave Off"

    def test_mutual_exclusion_off_and_value(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            matricks_interleave(width=2, off=True)

    def test_mutual_exclusion_off_and_increment(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            matricks_interleave(increment="+", off=True)

    def test_mutual_exclusion_value_and_increment(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            matricks_interleave(width=2, increment="+")

    def test_invalid_increment(self):
        with pytest.raises(ValueError, match="increment must be"):
            matricks_interleave(increment="foo")

    def test_increment_n_not_allowed(self):
        """Interleave only supports +/-, not + N/- N."""
        with pytest.raises(ValueError, match="increment must be"):
            matricks_interleave(increment="+ 2")


# ============================================================
# MAtricksBlocks Builder Tests
# ============================================================


class TestMAtricksBlocks:
    """Tests for matricks_blocks() command builder."""

    def test_bare(self):
        assert matricks_blocks() == "MAtricksBlocks"

    def test_size(self):
        assert matricks_blocks(size=2) == "MAtricksBlocks 2"

    def test_x_only(self):
        assert matricks_blocks(x=3) == "MAtricksBlocks 3"

    def test_x_y(self):
        assert matricks_blocks(x=2, y=3) == "MAtricksBlocks 2.3"

    def test_y_without_x_raises(self):
        with pytest.raises(ValueError, match="y requires x"):
            matricks_blocks(y=3)

    def test_size_and_x_conflict(self):
        with pytest.raises(ValueError, match="size and x are mutually exclusive"):
            matricks_blocks(size=2, x=3)

    def test_increment_plus_n(self):
        assert matricks_blocks(increment="+ 1") == "MAtricksBlocks + 1"

    def test_increment_minus_n(self):
        assert matricks_blocks(increment="- 2") == "MAtricksBlocks - 2"

    def test_off(self):
        assert matricks_blocks(off=True) == "MAtricksBlocks Off"

    def test_mutual_exclusion(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            matricks_blocks(size=2, off=True)


# ============================================================
# MAtricksGroups Builder Tests
# ============================================================


class TestMAtricksGroups:
    """Tests for matricks_groups() command builder."""

    def test_bare(self):
        assert matricks_groups() == "MAtricksGroups"

    def test_size(self):
        assert matricks_groups(size=4) == "MAtricksGroups 4"

    def test_x_y(self):
        assert matricks_groups(x=2, y=3) == "MAtricksGroups 2.3"

    def test_y_without_x_raises(self):
        with pytest.raises(ValueError, match="y requires x"):
            matricks_groups(y=3)

    def test_increment_plus_n(self):
        assert matricks_groups(increment="+ 1") == "MAtricksGroups + 1"

    def test_off(self):
        assert matricks_groups(off=True) == "MAtricksGroups Off"

    def test_mutual_exclusion(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            matricks_groups(size=2, increment="+ 1")


# ============================================================
# MAtricksWings Builder Tests
# ============================================================


class TestMAtricksWings:
    """Tests for matricks_wings() command builder."""

    def test_bare(self):
        assert matricks_wings() == "MAtricksWings"

    def test_parts(self):
        assert matricks_wings(parts=2) == "MAtricksWings 2"

    def test_increment_plus(self):
        assert matricks_wings(increment="+") == "MAtricksWings +"

    def test_increment_minus(self):
        assert matricks_wings(increment="-") == "MAtricksWings -"

    def test_off(self):
        assert matricks_wings(off=True) == "MAtricksWings Off"

    def test_mutual_exclusion(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            matricks_wings(parts=2, off=True)

    def test_increment_n_not_allowed(self):
        with pytest.raises(ValueError, match="increment must be"):
            matricks_wings(increment="+ 2")


# ============================================================
# MAtricksFilter Builder Tests
# ============================================================


class TestMAtricksFilter:
    """Tests for matricks_filter() command builder."""

    def test_bare(self):
        assert matricks_filter() == "MAtricksFilter"

    def test_filter_num(self):
        assert matricks_filter(filter_num=1) == "MAtricksFilter 1"

    def test_filter_name_plain(self):
        assert matricks_filter(name="OddID") == "MAtricksFilter OddID"

    def test_filter_name_with_spaces(self):
        assert matricks_filter(name="Odd Fixtures") == 'MAtricksFilter "Odd Fixtures"'

    def test_filter_num_and_name_conflict(self):
        with pytest.raises(ValueError, match="filter_num and name are mutually exclusive"):
            matricks_filter(filter_num=1, name="OddID")

    def test_increment_plus(self):
        assert matricks_filter(increment="+") == "MAtricksFilter +"

    def test_increment_minus(self):
        assert matricks_filter(increment="-") == "MAtricksFilter -"

    def test_off(self):
        assert matricks_filter(off=True) == "MAtricksFilter Off"

    def test_mutual_exclusion(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            matricks_filter(filter_num=1, off=True)


# ============================================================
# MAtricksReset Builder Tests
# ============================================================


class TestMAtricksReset:
    """Tests for matricks_reset() command builder."""

    def test_reset(self):
        assert matricks_reset() == "MAtricksReset"


# ============================================================
# RecallMAtricks Builder Tests
# ============================================================


class TestRecallMAtricks:
    """Tests for recall_matricks() command builder."""

    def test_bare(self):
        assert recall_matricks() == "MAtricks"

    def test_id(self):
        assert recall_matricks(matricks_id=5) == "MAtricks 5"

    def test_mode_on(self):
        assert recall_matricks(mode="on") == "MAtricks On"

    def test_mode_off(self):
        assert recall_matricks(mode="off") == "MAtricks Off"

    def test_mode_toggle(self):
        assert recall_matricks(mode="toggle") == "MAtricks Toggle"

    def test_mode_case_insensitive(self):
        assert recall_matricks(mode="ON") == "MAtricks On"
        assert recall_matricks(mode="Toggle") == "MAtricks Toggle"

    def test_id_and_mode_conflict(self):
        with pytest.raises(ValueError, match="matricks_id and mode are mutually exclusive"):
            recall_matricks(matricks_id=5, mode="on")

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="mode must be"):
            recall_matricks(mode="invalid")


# ============================================================
# All / AllRows Builder Tests
# ============================================================


class TestAllSubSelection:
    """Tests for all_sub_selection() command builder."""

    def test_all(self):
        assert all_sub_selection() == "All"


class TestAllRowsSubSelection:
    """Tests for all_rows_sub_selection() command builder."""

    def test_all_rows(self):
        assert all_rows_sub_selection() == "AllRows"


# ============================================================
# Next / Previous / NextRow Builder Tests
# ============================================================


class TestNextSubSelection:
    """Tests for next_sub_selection() command builder."""

    def test_next(self):
        assert next_sub_selection() == "Next"


class TestPreviousSubSelection:
    """Tests for previous_sub_selection() command builder."""

    def test_previous(self):
        assert previous_sub_selection() == "Previous"


class TestNextRowSubSelection:
    """Tests for next_row_sub_selection() command builder."""

    def test_next_row(self):
        assert next_row_sub_selection() == "NextRow"


# ============================================================
# MCP Tool Tests (Mocked)
# ============================================================


class TestManageMAtricksTool:
    """Tests for the manage_matricks MCP tool dispatch."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_interleave_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("interleave", value=3)
        data = json.loads(result)
        assert data["command_sent"] == "MAtricksInterleave 3"
        assert data["risk_tier"] == "SAFE_WRITE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_blocks_xy_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("blocks", x=2, y=3)
        data = json.loads(result)
        assert data["command_sent"] == "MAtricksBlocks 2.3"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_wings_off_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("wings", turn_off=True)
        data = json.loads(result)
        assert data["command_sent"] == "MAtricksWings Off"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_filter_name_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("filter", name="OddID")
        data = json.loads(result)
        assert data["command_sent"] == "MAtricksFilter OddID"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_recall_id_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("recall", value=10)
        data = json.loads(result)
        assert data["command_sent"] == "MAtricks 10"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_recall_mode_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("recall", mode="toggle")
        data = json.loads(result)
        assert data["command_sent"] == "MAtricks Toggle"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_reset_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("reset")
        data = json.loads(result)
        assert data["command_sent"] == "MAtricksReset"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_all_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("all")
        data = json.loads(result)
        assert data["command_sent"] == "All"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_allrows_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("allrows")
        data = json.loads(result)
        assert data["command_sent"] == "AllRows"

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        from src.server import manage_matricks

        result = await manage_matricks("bogus")
        data = json.loads(result)
        assert "error" in data
        assert "Unknown action" in data["error"]

    @pytest.mark.asyncio
    async def test_validation_error_forwarded(self):
        from src.server import manage_matricks

        # column without width should raise ValueError, forwarded as error
        result = await manage_matricks("interleave", column=1)
        data = json.loads(result)
        assert "error" in data
        assert "column requires width" in data["error"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_groups_increment_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("groups", increment="+ 2")
        data = json.loads(result)
        assert data["command_sent"] == "MAtricksGroups + 2"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_next_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("next")
        data = json.loads(result)
        assert data["command_sent"] == "Next"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_previous_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("previous")
        data = json.loads(result)
        assert data["command_sent"] == "Previous"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_nextrow_dispatch(self, mock_get_client):
        from src.server import manage_matricks

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await manage_matricks("nextrow")
        data = json.loads(result)
        assert data["command_sent"] == "NextRow"


# ============================================================
# store_matricks_preset Workflow Tool Tests
# ============================================================


class TestStoreMAtricksPresetTool:
    """Tests for the store_matricks_preset MCP tool."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import store_matricks_preset

        result = await store_matricks_preset(
            pool_slot=10, name="Test", interleave=4,
        )
        data = json.loads(result)
        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["risk_tier"]

    @pytest.mark.asyncio
    async def test_error_no_settings(self):
        from src.server import store_matricks_preset

        result = await store_matricks_preset(
            pool_slot=10, name="Empty", confirm_destructive=True,
        )
        data = json.loads(result)
        assert "error" in data
        assert "At least one" in data["error"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_basic_workflow(self, mock_get_client):
        from src.server import store_matricks_preset

        mock_client = AsyncMock()
        mock_client.send_command = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await store_matricks_preset(
            pool_slot=10, name="I4-W2",
            interleave=4, wings=2,
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert data["pool_slot"] == 10
        assert data["name"] == "I4-W2"
        assert "MAtricksReset" in data["commands_sent"]
        assert "MAtricksInterleave 4" in data["commands_sent"]
        assert "MAtricksWings 2" in data["commands_sent"]
        assert "store matricks 10 /overwrite" in data["commands_sent"]
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_no_reset(self, mock_get_client):
        from src.server import store_matricks_preset

        mock_client = AsyncMock()
        mock_client.send_command = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await store_matricks_preset(
            pool_slot=5, name="Blocks-3",
            blocks=3, reset_first=False,
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert "MAtricksReset" not in data["commands_sent"]
        assert "MAtricksBlocks 3" in data["commands_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_blocks_xy(self, mock_get_client):
        from src.server import store_matricks_preset

        mock_client = AsyncMock()
        mock_client.send_command = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await store_matricks_preset(
            pool_slot=6, name="B2x3",
            blocks=2, blocks_y=3,
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert "MAtricksBlocks 2.3" in data["commands_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_all_settings(self, mock_get_client):
        from src.server import store_matricks_preset

        mock_client = AsyncMock()
        mock_client.send_command = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await store_matricks_preset(
            pool_slot=7, name="Full",
            interleave=4, blocks=2, groups=4, wings=2, filter_num=1,
            confirm_destructive=True,
        )
        data = json.loads(result)
        cmds = data["commands_sent"]
        assert "MAtricksReset" in cmds
        assert "MAtricksInterleave 4" in cmds
        assert "MAtricksBlocks 2" in cmds
        assert "MAtricksGroups 4" in cmds
        assert "MAtricksWings 2" in cmds
        assert "MAtricksFilter 1" in cmds
        assert "store matricks 7 /overwrite" in cmds
