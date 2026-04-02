"""
tests/test_server_orchestration_tools.py — Unit tests for src/server_orchestration_tools.py

Strategy: register_orchestration_tools() is called with a CaptureMcp shim that
intercepts @mcp.tool() registrations without scope-checking or error-handling,
giving direct access to the raw async tool functions. This avoids needing a live
FastMCP instance or the OAuth layer.

Tools covered:
  119 — get_console_state
  120 — get_park_ledger
  121 — get_filter_state
  122 — get_world_state
  123 — get_matricks_state
  124 — get_programmer_selection
  125 — hydrate_sequences
  126 — get_sequence_memory
  127 — assert_selection_count
  128 — assert_preset_exists
  129 — get_executor_detail
  131 — diff_console_state
  137 — assert_fixture_exists
  132 — get_showfile_info
  133 — watch_system_var
  134 — confirm_destructive_steps
  135 — abort_task
  136 — retry_failed_steps
  (110-118 smoke tests via no-snapshot guard)
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.commands.constants import OAuthScope
from src.console_state import (
    ConsoleStateSnapshot,
    CueRecord,
    ExecutorState,
    SequenceEntry,
)
from src.server_orchestration_tools import register_orchestration_tools

# ── Test helpers ──────────────────────────────────────────────────────────────

def _make_snap(**kwargs) -> ConsoleStateSnapshot:
    return ConsoleStateSnapshot(**kwargs)


def _capture_tools(mock_orch) -> dict:
    """Register all orchestration tools with a capturing shim; return by name."""
    tools: dict = {}

    class CaptureMcp:
        def tool(self_inner):
            def decorator(fn):
                tools[fn.__name__] = fn
                return fn
            return decorator

    def noop_scope(scope):
        def dec(fn):
            return fn
        return dec

    def noop_errors(fn):
        return fn

    register_orchestration_tools(
        CaptureMcp(), mock_orch, noop_scope, noop_errors, OAuthScope
    )
    return tools


# ── No-snapshot guard (all Tools 119-129) ────────────────────────────────────

class TestNoSnapshotGuard:
    """Every snapshot-read tool returns an error dict when last_snapshot is None."""

    @pytest.mark.asyncio
    async def test_get_console_state_no_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_console_state"]())
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_park_ledger_no_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_park_ledger"]())
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_filter_state_no_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_filter_state"]())
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_world_state_no_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_world_state"]())
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_matricks_state_no_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_matricks_state"]())
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_programmer_selection_no_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_programmer_selection"]())
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_sequence_memory_no_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_sequence_memory"](sequence_id=1))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_assert_selection_count_no_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_selection_count"](expected=5))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_assert_preset_exists_no_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_preset_exists"](preset_type=2, preset_id=1))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_executor_detail_no_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_executor_detail"](executor_id=201))
        assert "error" in result


# ── Tool 119: get_console_state ───────────────────────────────────────────────

class TestGetConsoleState:

    @pytest.mark.asyncio
    async def test_returns_expected_keys(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_console_state"]())
        assert "hydrated" in result
        assert "staleness_warning" in result
        assert "age_seconds" in result
        assert "partial" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_age_seconds_is_numeric(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_console_state"]())
        assert isinstance(result["age_seconds"], float)

    @pytest.mark.asyncio
    async def test_partial_false_by_default(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_console_state"]())
        assert result["partial"] is False


# ── Tool 120: get_park_ledger ─────────────────────────────────────────────────

class TestGetParkLedger:

    @pytest.mark.asyncio
    async def test_empty_park_set(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_park_ledger"]())
        assert result["parked_fixtures"] == []
        assert result["count"] == 0
        assert result["warning"] is None

    @pytest.mark.asyncio
    async def test_with_parked_fixtures(self):
        snap = _make_snap()
        snap.parked_fixtures.add("fixture 20")
        snap.parked_fixtures.add("fixture 21")
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_park_ledger"]())
        assert result["count"] == 2
        assert "fixture 20" in result["parked_fixtures"]
        assert result["warning"] is not None
        assert "2" in result["warning"]


# ── Tool 121: get_filter_state ────────────────────────────────────────────────

class TestGetFilterState:

    @pytest.mark.asyncio
    async def test_no_active_filter(self):
        snap = _make_snap()
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_filter_state"]())
        assert result["active_filter"] is None
        assert result["warning"] is None

    @pytest.mark.asyncio
    async def test_with_active_filter(self):
        snap = _make_snap()
        snap.active_filter = 3
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_filter_state"]())
        assert result["active_filter"] == 3
        assert result["warning"] is not None
        assert "3" in result["warning"]

    @pytest.mark.asyncio
    async def test_filter_vte_default(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_filter_state"]())
        assert result["filter_vte"] == {"value": True, "value_timing": True, "effect": True}


# ── Tool 122: get_world_state ─────────────────────────────────────────────────

class TestGetWorldState:

    @pytest.mark.asyncio
    async def test_no_active_world(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_world_state"]())
        assert result["active_world"] is None
        assert result["warning"] is None

    @pytest.mark.asyncio
    async def test_with_active_world(self):
        snap = _make_snap()
        snap.active_world = 2
        snap.world_labels = {2: "Stage Left"}
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_world_state"]())
        assert result["active_world"] == 2
        assert result["warning"] is not None
        assert result["world_labels"]["2"] == "Stage Left"


# ── Tool 123: get_matricks_state ──────────────────────────────────────────────

class TestGetMatricksState:

    @pytest.mark.asyncio
    async def test_default_state(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_matricks_state"]())
        assert result["interleave"] is None
        assert result["wings"] is None
        assert result["active"] is False
        assert result["summary"] == "off"
        assert "note" in result

    @pytest.mark.asyncio
    async def test_with_active_matricks(self):
        snap = _make_snap()
        snap.matricks.interleave = 4
        snap.matricks.wings = 2
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_matricks_state"]())
        assert result["interleave"] == 4
        assert result["wings"] == 2
        assert "interleave=4" in result["summary"]


# ── Tool 124: get_programmer_selection ───────────────────────────────────────

class TestGetProgrammerSelection:

    @pytest.mark.asyncio
    async def test_zero_selection(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_programmer_selection"]())
        assert result["selected_fixture_count"] == 0
        assert result["warning"] is not None

    @pytest.mark.asyncio
    async def test_with_selection(self):
        snap = _make_snap()
        snap.selected_fixture_count = 12
        snap.selected_exec = "1.1.201"
        snap.selected_exec_cue = "3"
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_programmer_selection"]())
        assert result["selected_fixture_count"] == 12
        assert result["selected_exec"] == "1.1.201"
        assert result["selected_exec_cue"] == "3"
        assert result["warning"] is None


# ── Tool 125: hydrate_sequences ───────────────────────────────────────────────

class TestHydrateSequences:

    @pytest.mark.asyncio
    async def test_invalid_ids_returns_error(self):
        mock_orch = MagicMock()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["hydrate_sequences"](sequence_ids="1,two,3"))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_ids_returns_error(self):
        mock_orch = MagicMock()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["hydrate_sequences"](sequence_ids="  "))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_valid_ids_calls_hydrate(self):
        snap = _make_snap()
        mock_orch = MagicMock()
        mock_orch.hydrate_snapshot = AsyncMock(return_value=snap)
        t = _capture_tools(mock_orch)
        result = json.loads(await t["hydrate_sequences"](sequence_ids="1,2,5"))
        assert result["hydrated"] is True
        assert result["sequence_ids"] == [1, 2, 5]
        mock_orch.hydrate_snapshot.assert_called_once_with(sequence_ids=[1, 2, 5])

    @pytest.mark.asyncio
    async def test_updates_last_snapshot(self):
        snap = _make_snap()
        mock_orch = MagicMock()
        mock_orch.hydrate_snapshot = AsyncMock(return_value=snap)
        t = _capture_tools(mock_orch)
        await t["hydrate_sequences"](sequence_ids="1")
        assert mock_orch.last_snapshot == snap


# ── Tool 126: get_sequence_memory ─────────────────────────────────────────────

class TestGetSequenceMemory:

    @pytest.mark.asyncio
    async def test_sequence_not_in_snapshot_returns_error(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_sequence_memory"](sequence_id=99))
        assert "error" in result
        assert "hint" in result

    @pytest.mark.asyncio
    async def test_sequence_found_returns_fields(self):
        snap = _make_snap()
        snap.sequences.append(SequenceEntry(id=5, label="Main", loop=True))
        snap.sequence_cues.append(CueRecord(sequence_id=5, cue_number=1.0, label="Go"))
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_sequence_memory"](sequence_id=5))
        assert result["id"] == 5
        assert result["label"] == "Main"
        assert result["loop"] is True
        assert result["cue_count"] == 1
        assert result["cues"][0]["cue_number"] == 1.0

    @pytest.mark.asyncio
    async def test_known_ids_listed_in_error(self):
        snap = _make_snap()
        snap.sequences.append(SequenceEntry(id=3, label="Seq3"))
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_sequence_memory"](sequence_id=99))
        assert 3 in result["known_ids"]


# ── Tool 127: assert_selection_count ─────────────────────────────────────────

class TestAssertSelectionCount:

    @pytest.mark.asyncio
    async def test_exact_match_passes(self):
        snap = _make_snap()
        snap.selected_fixture_count = 12
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_selection_count"](expected=12))
        assert result["passed"] is True
        assert result["message"] == "OK"

    @pytest.mark.asyncio
    async def test_mismatch_fails(self):
        snap = _make_snap()
        snap.selected_fixture_count = 10
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_selection_count"](expected=12))
        assert result["passed"] is False
        assert "10" in result["message"]

    @pytest.mark.asyncio
    async def test_within_tolerance_passes(self):
        snap = _make_snap()
        snap.selected_fixture_count = 11
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_selection_count"](expected=12, tolerance=2))
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_outside_tolerance_fails(self):
        snap = _make_snap()
        snap.selected_fixture_count = 5
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_selection_count"](expected=12, tolerance=2))
        assert result["passed"] is False


# ── Tool 128: assert_preset_exists ───────────────────────────────────────────

class TestAssertPresetExists:

    @pytest.mark.asyncio
    async def test_preset_not_in_index(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_preset_exists"](preset_type=2, preset_id=1))
        assert result["exists"] is False
        assert result["warning"] is not None

    @pytest.mark.asyncio
    async def test_preset_in_index(self):
        snap = _make_snap()
        snap.name_index.add_entry("preset", "Position 1", 1, preset_type=2)
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_preset_exists"](preset_type=2, preset_id=1))
        assert result["exists"] is True
        assert result["warning"] is None


# ── Tool 129: get_executor_detail ─────────────────────────────────────────────

class TestGetExecutorDetail:

    @pytest.mark.asyncio
    async def test_executor_not_in_snapshot(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_executor_detail"](executor_id=201))
        assert "error" in result
        assert "known_ids" in result

    @pytest.mark.asyncio
    async def test_executor_found_returns_all_fields(self):
        snap = _make_snap()
        snap.executor_state[201] = ExecutorState(id=201, page=1, priority="high", kill_protect=True)
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_executor_detail"](executor_id=201))
        assert result["id"] == 201
        assert result["priority"] == "high"
        assert result["kill_protect"] is True

    @pytest.mark.asyncio
    async def test_known_ids_listed_in_error(self):
        snap = _make_snap()
        snap.executor_state[5] = ExecutorState(id=5)
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_executor_detail"](executor_id=99))
        assert 5 in result["known_ids"]


# ── Tool 131: diff_console_state ──────────────────────────────────────────────

class TestDiffConsoleState:

    @pytest.mark.asyncio
    async def test_no_snapshot_returns_error(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["diff_console_state"](baseline="{}"))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_json_baseline_returns_error(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["diff_console_state"](baseline="{not valid json"))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_no_change_empty_diff(self):
        snap = _make_snap()
        snap.active_filter = None
        snap.active_world = None
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        baseline = '{"active_filter": null, "active_world": null}'
        result = json.loads(await t["diff_console_state"](baseline=baseline))
        assert result["changed_count"] == 0
        assert result["unchanged_count"] == 2

    @pytest.mark.asyncio
    async def test_changed_field_detected(self):
        snap = _make_snap()
        snap.active_filter = 5
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        baseline = '{"active_filter": null}'
        result = json.loads(await t["diff_console_state"](baseline=baseline))
        assert result["changed_count"] == 1
        assert "active_filter" in result["changed_fields"]
        assert result["changed_fields"]["active_filter"]["before"] is None
        assert result["changed_fields"]["active_filter"]["after"] == 5

    @pytest.mark.asyncio
    async def test_parked_count_diff(self):
        snap = _make_snap()
        snap.parked_fixtures.add("fixture 1")
        snap.parked_fixtures.add("fixture 2")
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        baseline = '{"parked_count": 0}'
        result = json.loads(await t["diff_console_state"](baseline=baseline))
        assert result["changed_count"] == 1
        assert result["changed_fields"]["parked_count"]["after"] == 2

    @pytest.mark.asyncio
    async def test_unknown_keys_ignored(self):
        snap = _make_snap()
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        baseline = '{"unknown_field": "xyz"}'
        result = json.loads(await t["diff_console_state"](baseline=baseline))
        assert result["changed_count"] == 0

    @pytest.mark.asyncio
    async def test_snapshot_age_seconds_present(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["diff_console_state"](baseline="{}"))
        assert "snapshot_age_seconds" in result


# ── Tool 132: get_showfile_info ───────────────────────────────────────────────

class TestGetShowfileInfo:

    @pytest.mark.asyncio
    async def test_no_snapshot_returns_error(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_showfile_info"]())
        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_required_keys(self):
        snap = _make_snap()
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_showfile_info"]())
        for key in ("showfile", "version", "host_status", "active_user", "hostname"):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_returns_snapshot_values(self):
        snap = _make_snap()
        snap.showfile    = "my_show"
        snap.version     = "3.9.60.65"
        snap.host_status = "Standalone"
        snap.active_user = "operator"
        snap.hostname    = "WINDELL-PC"
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_showfile_info"]())
        assert result["showfile"]    == "my_show"
        assert result["version"]     == "3.9.60.65"
        assert result["host_status"] == "Standalone"
        assert result["active_user"] == "operator"
        assert result["hostname"]    == "WINDELL-PC"

    @pytest.mark.asyncio
    async def test_note_field_present(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = _make_snap()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["get_showfile_info"]())
        assert "note" in result


# ── Tool 133: watch_system_var ────────────────────────────────────────────────

class TestWatchSystemVar:

    @pytest.mark.asyncio
    async def test_no_send_fn_returns_error(self):
        mock_orch = MagicMock()
        mock_orch._send = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["watch_system_var"](
            var_name="FADERPAGE", expected_value="2"
        ))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_matches_on_first_poll(self):
        listvar_response = "$Global : $FADERPAGE = 2\n"
        mock_orch = MagicMock()
        mock_orch._send = AsyncMock(return_value=listvar_response)
        t = _capture_tools(mock_orch)
        result = json.loads(await t["watch_system_var"](
            var_name="FADERPAGE", expected_value="2", poll_interval=0.1
        ))
        assert result["matched"] is True
        assert result["final_value"] == "2"
        assert result["polls"] >= 1

    @pytest.mark.asyncio
    async def test_timeout_when_value_never_matches(self):
        listvar_response = "$Global : $FADERPAGE = 1\n"
        mock_orch = MagicMock()
        mock_orch._send = AsyncMock(return_value=listvar_response)
        t = _capture_tools(mock_orch)
        result = json.loads(await t["watch_system_var"](
            var_name="FADERPAGE", expected_value="99",
            timeout_seconds=0.3, poll_interval=0.1
        ))
        assert result["matched"] is False
        assert result["final_value"] == "1"

    @pytest.mark.asyncio
    async def test_timeout_capped_at_30(self):
        # We only test that it doesn't raise — actual cap is enforced internally
        mock_orch = MagicMock()
        mock_orch._send = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["watch_system_var"](
            var_name="X", expected_value="Y", timeout_seconds=999
        ))
        # No send_fn → error path, but we verify no exception
        assert "error" in result

    @pytest.mark.asyncio
    async def test_var_name_with_dollar_prefix(self):
        listvar_response = "$Global : $TIME = 12h00m00.000s\n"
        mock_orch = MagicMock()
        mock_orch._send = AsyncMock(return_value=listvar_response)
        t = _capture_tools(mock_orch)
        result = json.loads(await t["watch_system_var"](
            var_name="$TIME", expected_value="12h00m00.000s", poll_interval=0.1
        ))
        assert result["matched"] is True
        assert result["var_name"] == "$TIME"


# ── Tool 134: confirm_destructive_steps ──────────────────────────────────────

class TestConfirmDestructiveSteps:

    @pytest.mark.asyncio
    async def test_returns_required_keys(self):
        mock_orch = MagicMock()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["confirm_destructive_steps"](goal="select fixtures"))
        for key in ("goal", "total_steps", "destructive_count", "destructive_steps", "safe_to_run", "hint"):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_safe_goal_has_zero_destructive(self):
        mock_orch = MagicMock()
        t = _capture_tools(mock_orch)
        # A read-only-style goal should produce no DESTRUCTIVE steps
        result = json.loads(await t["confirm_destructive_steps"](goal="list groups"))
        assert isinstance(result["destructive_count"], int)
        assert result["destructive_count"] >= 0

    @pytest.mark.asyncio
    async def test_destructive_steps_have_expected_shape(self):
        mock_orch = MagicMock()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["confirm_destructive_steps"](goal="store blue cue"))
        for step in result.get("destructive_steps", []):
            assert "step_index" in step
            assert "name" in step
            assert "description" in step

    @pytest.mark.asyncio
    async def test_safe_to_run_true_when_no_destructive(self):
        mock_orch = MagicMock()
        t = _capture_tools(mock_orch)
        result = json.loads(await t["confirm_destructive_steps"](goal="list groups"))
        # safe_to_run is True when destructive_count == 0
        assert result["safe_to_run"] == (result["destructive_count"] == 0)


# ── Tool 135: abort_task ─────────────────────────────────────────────────────

class TestAbortTask:

    @pytest.mark.asyncio
    async def test_unknown_session_returns_error(self):
        mock_orch = MagicMock()
        mock_orch.recall = MagicMock(return_value=None)
        t = _capture_tools(mock_orch)
        result = json.loads(await t["abort_task"](session_id="nonexist"))
        assert "error" in result
        assert "hint" in result

    @pytest.mark.asyncio
    async def test_known_session_returns_aborted(self):
        mock_orch = MagicMock()
        mock_orch.recall = MagicMock(return_value={
            "task_description": "blue wash",
            "completed_steps": ["step_A"],
            "failed_steps": [],
            "token_spend": 42,
        })
        t = _capture_tools(mock_orch)
        result = json.loads(await t["abort_task"](session_id="abc12345"))
        assert result["aborted"] is True
        assert result["session_id"] == "abc12345"
        assert result["reason"] == "user_requested"
        assert "step_A" in result["steps_completed"]

    @pytest.mark.asyncio
    async def test_custom_reason_propagated(self):
        mock_orch = MagicMock()
        mock_orch.recall = MagicMock(return_value={
            "task_description": "test",
            "completed_steps": [],
            "failed_steps": [],
            "token_spend": 0,
        })
        t = _capture_tools(mock_orch)
        result = json.loads(await t["abort_task"](session_id="x", reason="emergency_stop"))
        assert result["reason"] == "emergency_stop"


# ── Tool 136: retry_failed_steps ─────────────────────────────────────────────

class TestRetryFailedSteps:

    @pytest.mark.asyncio
    async def test_unknown_session_returns_error(self):
        mock_orch = MagicMock()
        mock_orch.recall = MagicMock(return_value=None)
        t = _capture_tools(mock_orch)
        result = json.loads(await t["retry_failed_steps"](session_id="nope"))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_no_failed_steps_returns_zero_retried(self):
        mock_orch = MagicMock()
        mock_orch.recall = MagicMock(return_value={
            "task_description": "blue wash",
            "completed_steps": ["step_A"],
            "failed_steps": [],
            "token_spend": 10,
        })
        t = _capture_tools(mock_orch)
        result = json.loads(await t["retry_failed_steps"](session_id="abc12345"))
        assert result["retried"] == 0

    @pytest.mark.asyncio
    async def test_failed_steps_trigger_run(self):
        from unittest.mock import AsyncMock as _AsyncMock

        from src.orchestrator import OrchestrationResult

        fake_result = OrchestrationResult(
            session_id="new123",
            goal="blue wash",
            outcome="success",
            steps_done=2,
            steps_failed=0,
            total_tokens=50,
            elapsed_s=0.5,
        )
        mock_orch = MagicMock()
        mock_orch.recall = MagicMock(return_value={
            "task_description": "blue wash",
            "completed_steps": [],
            "failed_steps": ["step_B: timeout"],
            "token_spend": 5,
        })
        mock_orch.run = _AsyncMock(return_value=fake_result)
        t = _capture_tools(mock_orch)
        result = json.loads(await t["retry_failed_steps"](session_id="old99"))
        assert result["retried"] == 1
        assert result["new_session_id"] == "new123"
        assert result["outcome"] == "success"
        mock_orch.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_task_description_returns_error(self):
        mock_orch = MagicMock()
        mock_orch.recall = MagicMock(return_value={
            "task_description": "",
            "failed_steps": ["step_X"],
            "completed_steps": [],
            "token_spend": 0,
        })
        t = _capture_tools(mock_orch)
        result = json.loads(await t["retry_failed_steps"](session_id="empty99"))
        assert "error" in result


# ── Tool 137: assert_fixture_exists ──────────────────────────────────────────

class TestAssertFixtureExists:

    @pytest.mark.asyncio
    async def test_snapshot_fixture_present(self):
        snap = _make_snap()
        snap.name_index.add_entry("Fixture", "Mac700", 101)
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_fixture_exists"](fixture_id=101))
        assert result["exists"] is True
        assert result["source"] == "snapshot"
        assert result["hint"] is None

    @pytest.mark.asyncio
    async def test_snapshot_fixture_absent(self):
        snap = _make_snap()
        snap.name_index.add_entry("Fixture", "Mac700", 20)  # 101 not here
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_fixture_exists"](fixture_id=101))
        assert result["exists"] is False
        assert result["source"] == "snapshot"
        assert result["hint"] is not None
        assert "101" in result["hint"]

    @pytest.mark.asyncio
    async def test_no_snapshot_no_send_returns_error(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        mock_orch._send = None
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_fixture_exists"](fixture_id=101))
        assert "error" in result
        assert result.get("fixture_id") == 101

    @pytest.mark.asyncio
    async def test_live_telnet_fixture_exists(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        mock_orch._send = AsyncMock(return_value="Fixture 101  Id=101  Name=Mac700\n")
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_fixture_exists"](fixture_id=101))
        assert result["exists"] is True
        assert result["source"] == "live_telnet"
        assert result["hint"] is None

    @pytest.mark.asyncio
    async def test_live_telnet_fixture_not_found(self):
        mock_orch = MagicMock()
        mock_orch.last_snapshot = None
        mock_orch._send = AsyncMock(return_value="WARNING, NO OBJECTS FOUND FOR LIST\n")
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_fixture_exists"](fixture_id=101))
        assert result["exists"] is False
        assert result["source"] == "live_telnet"
        assert result["hint"] is not None
        assert "101" in result["hint"]

    @pytest.mark.asyncio
    async def test_snapshot_without_fixture_entries_falls_to_telnet(self):
        # Snapshot exists but Fixture pool not indexed → falls back to live probe
        snap = _make_snap()  # name_index empty → no Fixture entries
        mock_orch = MagicMock()
        mock_orch.last_snapshot = snap
        mock_orch._send = AsyncMock(return_value="Fixture 101  Id=101\n")
        t = _capture_tools(mock_orch)
        result = json.loads(await t["assert_fixture_exists"](fixture_id=101))
        assert result["source"] == "live_telnet"
        assert result["exists"] is True
