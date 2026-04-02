"""Tests for pool availability checker (tool #91 + _check_pool_slots helper)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.prompt_parser import ListEntry, ListOutput


def _make_list_result(entries):
    """Build a mock list_destination return value."""
    mock = MagicMock()
    mock.command_sent = "list"
    mock.raw_response = "mock list output"
    mock.parsed_list = ListOutput(
        raw_response="mock list output",
        entries=tuple(entries),
    )
    return mock


def _make_nav():
    """Build a mock navigate return value."""
    mock = MagicMock()
    mock.command_sent = "cd /"
    return mock


# ---------------------------------------------------------------------------
# _check_pool_slots helper tests
# ---------------------------------------------------------------------------


class TestCheckPoolSlots:
    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    async def test_empty_pool_all_free(self, mock_navigate, mock_list_dest):
        from src.server import _check_pool_slots

        mock_navigate.return_value = _make_nav()
        mock_list_dest.return_value = _make_list_result([])
        client = MagicMock()

        result = await _check_pool_slots(client, "Group", start_from=1, scan_up_to=10)

        assert result["total_occupied"] == 0
        assert result["total_free_in_range"] == 10
        assert result["next_free_slots"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert result["largest_contiguous"] == 10

    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    async def test_occupied_slots_detected(self, mock_navigate, mock_list_dest):
        from src.server import _check_pool_slots

        mock_navigate.return_value = _make_nav()
        entries = [
            ListEntry(object_type="Group", object_id="3", name="Front Wash",
                      raw_line="", col3=None, columns={}),
            ListEntry(object_type="Group", object_id="5", name="Back Wash",
                      raw_line="", col3=None, columns={}),
            ListEntry(object_type="Group", object_id="7", name="Sides",
                      raw_line="", col3=None, columns={}),
        ]
        mock_list_dest.return_value = _make_list_result(entries)
        client = MagicMock()

        result = await _check_pool_slots(client, "Group", start_from=1, scan_up_to=10)

        assert result["total_occupied"] == 3
        assert result["total_free_in_range"] == 7
        slots = [s["slot"] for s in result["occupied_slots"]]
        assert slots == [3, 5, 7]

    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    async def test_free_ranges_computed(self, mock_navigate, mock_list_dest):
        from src.server import _check_pool_slots

        mock_navigate.return_value = _make_nav()
        entries = [
            ListEntry(object_type="Group", object_id="3", name="A",
                      raw_line="", col3=None, columns={}),
            ListEntry(object_type="Group", object_id="5", name="B",
                      raw_line="", col3=None, columns={}),
            ListEntry(object_type="Group", object_id="7", name="C",
                      raw_line="", col3=None, columns={}),
        ]
        mock_list_dest.return_value = _make_list_result(entries)
        client = MagicMock()

        result = await _check_pool_slots(client, "Group", start_from=1, scan_up_to=10)

        ranges = result["free_ranges"]
        assert {"start": 1, "end": 2} in ranges
        assert {"start": 4, "end": 4} in ranges
        assert {"start": 6, "end": 6} in ranges
        assert {"start": 8, "end": 10} in ranges

    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    async def test_needed_slots_can_fit(self, mock_navigate, mock_list_dest):
        from src.server import _check_pool_slots

        mock_navigate.return_value = _make_nav()
        # Slots 1-5 occupied, 6-20 free
        entries = [
            ListEntry(object_type="Macro", object_id=str(i), name=f"M{i}",
                      raw_line="", col3=None, columns={})
            for i in range(1, 6)
        ]
        mock_list_dest.return_value = _make_list_result(entries)
        client = MagicMock()

        result = await _check_pool_slots(
            client, "Macro", start_from=1, scan_up_to=20, needed_slots=10,
        )

        assert result["can_fit"] is True
        assert result["suggested_start"] == 6

    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    async def test_needed_slots_cannot_fit(self, mock_navigate, mock_list_dest):
        from src.server import _check_pool_slots

        mock_navigate.return_value = _make_nav()
        # Every other slot occupied: 1,3,5,7,9 — max contiguous free = 1
        entries = [
            ListEntry(object_type="Macro", object_id=str(i), name=f"M{i}",
                      raw_line="", col3=None, columns={})
            for i in range(1, 11, 2)
        ]
        mock_list_dest.return_value = _make_list_result(entries)
        client = MagicMock()

        result = await _check_pool_slots(
            client, "Macro", start_from=1, scan_up_to=10, needed_slots=3,
        )

        assert result["can_fit"] is False
        assert result["suggested_start"] is None

    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    async def test_start_from_filter(self, mock_navigate, mock_list_dest):
        from src.server import _check_pool_slots

        mock_navigate.return_value = _make_nav()
        # Slots 1 and 2 occupied — but start_from=3, so they should be ignored
        entries = [
            ListEntry(object_type="Filter", object_id="1", name="System1",
                      raw_line="", col3=None, columns={}),
            ListEntry(object_type="Filter", object_id="2", name="System2",
                      raw_line="", col3=None, columns={}),
        ]
        mock_list_dest.return_value = _make_list_result(entries)
        client = MagicMock()

        result = await _check_pool_slots(
            client, "Filter", start_from=3, scan_up_to=10,
        )

        assert result["total_occupied"] == 0
        assert result["total_free_in_range"] == 8
        assert result["next_free_slots"][0] == 3

    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    async def test_next_free_slots_ascending_order(self, mock_navigate, mock_list_dest):
        from src.server import _check_pool_slots

        mock_navigate.return_value = _make_nav()
        entries = [
            ListEntry(object_type="Group", object_id="2", name="G2",
                      raw_line="", col3=None, columns={}),
        ]
        mock_list_dest.return_value = _make_list_result(entries)
        client = MagicMock()

        result = await _check_pool_slots(client, "Group", start_from=1, scan_up_to=15)

        free = result["next_free_slots"]
        assert free == sorted(free)
        assert 2 not in free
        assert 1 in free

    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    async def test_sub_pool_detection(self, mock_navigate, mock_list_dest):
        """Pools like Macros (cd 13) show a sub-pool first; helper should descend."""
        from src.server import _check_pool_slots

        mock_navigate.return_value = _make_nav()

        # First list returns a MacroPool container; second returns actual macros
        sub_pool_entry = ListEntry(
            object_type="MacroPool", object_id="1", name="Global",
            raw_line="", col3=None, columns={},
        )
        macro_entry = ListEntry(
            object_type="Macro", object_id="5", name="MyMacro",
            raw_line="", col3=None, columns={},
        )
        mock_list_dest.side_effect = [
            _make_list_result([sub_pool_entry]),
            _make_list_result([macro_entry]),
        ]
        client = MagicMock()

        result = await _check_pool_slots(client, "Macro", start_from=1, scan_up_to=10)

        assert result["total_occupied"] == 1
        assert result["occupied_slots"][0]["slot"] == 5
        assert result["occupied_slots"][0]["name"] == "MyMacro"


# ---------------------------------------------------------------------------
# check_pool_availability tool tests
# ---------------------------------------------------------------------------


class TestCheckPoolAvailabilityTool:
    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    @patch("src.server.get_client")
    async def test_tool_json_structure(self, mock_get_client, mock_navigate, mock_list_dest):
        from src.server import check_pool_availability

        mock_get_client.return_value = MagicMock()
        mock_navigate.return_value = _make_nav()
        entries = [
            ListEntry(object_type="Group", object_id="1", name="All",
                      raw_line="", col3=None, columns={}),
        ]
        mock_list_dest.return_value = _make_list_result(entries)

        result = json.loads(await check_pool_availability("Group", scan_up_to=10))

        assert result["risk_tier"] == "SAFE_READ"
        assert "occupied_slots" in result
        assert "free_ranges" in result
        assert "next_free_slots" in result
        assert "total_occupied" in result
        assert "total_free_in_range" in result
        assert "largest_contiguous" in result
        assert result["total_occupied"] == 1
        assert result["pool_type"] == "Group"

    @pytest.mark.asyncio
    @patch("src.server.list_destination")
    @patch("src.server.navigate")
    @patch("src.server.get_client")
    async def test_tool_with_needed_slots(self, mock_get_client, mock_navigate, mock_list_dest):
        from src.server import check_pool_availability

        mock_get_client.return_value = MagicMock()
        mock_navigate.return_value = _make_nav()
        mock_list_dest.return_value = _make_list_result([])

        result = json.loads(
            await check_pool_availability("Filter", scan_up_to=20, needed_slots=5)
        )

        assert result["can_fit"] is True
        assert result["suggested_start"] == 1


# ---------------------------------------------------------------------------
# Import tool integration tests
# ---------------------------------------------------------------------------


class TestImportObjectsSlotStatus:
    @pytest.mark.asyncio
    @patch("src.server._check_pool_slots")
    @patch("src.server.get_client")
    async def test_import_includes_slot_status_occupied(
        self, mock_get_client, mock_check_slots,
    ):
        from src.server import import_objects

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        mock_check_slots.return_value = {
            "occupied_slots": [{"slot": 5, "name": "OldMacro"}],
            "free_ranges": [],
            "next_free_slots": [],
            "total_occupied": 1,
            "total_free_in_range": 0,
            "largest_contiguous": 0,
            "can_fit": None,
            "suggested_start": None,
        }

        result = json.loads(
            await import_objects("test", "macro", "5", confirm_destructive=True)
        )

        assert result["slot_status"]["occupied"] is True
        assert result["slot_status"]["previous_name"] == "OldMacro"

    @pytest.mark.asyncio
    @patch("src.server._check_pool_slots")
    @patch("src.server.get_client")
    async def test_import_includes_slot_status_free(
        self, mock_get_client, mock_check_slots,
    ):
        from src.server import import_objects

        mock_client = AsyncMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        mock_check_slots.return_value = {
            "occupied_slots": [],
            "free_ranges": [{"start": 14, "end": 14}],
            "next_free_slots": [14],
            "total_occupied": 0,
            "total_free_in_range": 1,
            "largest_contiguous": 1,
            "can_fit": None,
            "suggested_start": None,
        }

        result = json.loads(
            await import_objects("test", "macro", "14", confirm_destructive=True)
        )

        assert result["slot_status"]["occupied"] is False
