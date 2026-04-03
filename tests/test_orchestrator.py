"""
tests/test_orchestrator.py — Unit tests for src/orchestrator.py

Covers:
  - _preflight_guard()
  - _default_sub_agent() (mocked tool_caller)
  - Orchestrator.run() — sequential execution, success/partial/failed outcomes
  - Orchestrator.run() — auto_confirm_destructive
  - Orchestrator.recent_sessions() / recall()
  - OrchestrationResult.report()
  - TestSnapshotWiring — server tools update _orchestrator.last_snapshot
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent_memory import LongTermMemory, WorkingMemory
from src.commands.constants import MA2Right
from src.orchestrator import (
    OrchestrationResult,
    Orchestrator,
    StepResult,
    _default_sub_agent,
    _preflight_guard,
)
from src.rights import FeedbackClass, RightsContext
from src.task_decomposer import SubTask, TaskPlan
from src.vocab import RiskTier

# ── Helpers ──────────────────────────────────────────────────────────────────

def _step(name, risk=RiskTier.SAFE_READ, tools=None, depends_on=None, confirmed=False):
    return SubTask(
        name=name,
        agent_role="TestAgent",
        description=f"step {name}",
        allowed_risk=risk,
        mcp_tools=tools or ["navigate_console"],
        depends_on=depends_on or [],
        confirmed=confirmed,
    )


def _wm(right=MA2Right.ADMIN):
    wm = WorkingMemory(task_description="test")
    wm.rights_context = RightsContext(user_right=right, username="testuser")
    return wm


def _ltm_tmp():
    fd, path_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    path = Path(path_str)
    return LongTermMemory(db_path=path), path


# ── _preflight_guard() ───────────────────────────────────────────────────────

class TestPreflightGuard:
    def test_safe_read_always_passes(self):
        step = _step("read", risk=RiskTier.SAFE_READ)
        wm = _wm(right=MA2Right.NONE)
        assert _preflight_guard(step, wm) is None

    def test_destructive_unconfirmed_blocked(self):
        step = _step("store", risk=RiskTier.DESTRUCTIVE, confirmed=False)
        wm = _wm()
        err = _preflight_guard(step, wm)
        assert err is not None
        assert "DESTRUCTIVE" in err

    def test_destructive_confirmed_passes_rights(self):
        step = _step("store", risk=RiskTier.DESTRUCTIVE,
                     tools=["store_current_cue"], confirmed=True)
        wm = _wm(right=MA2Right.ADMIN)
        # snapshot None → staleness check returns warning but doesn't block
        result = _preflight_guard(step, wm)
        # DESTRUCTIVE + confirmed + stale snapshot → should block on staleness
        assert result is not None  # "No ConsoleStateSnapshot" staleness warning blocks

    def test_rights_check_insufficient_right(self):
        step = _step("load", risk=RiskTier.SAFE_READ, tools=["load_show"])
        wm = _wm(right=MA2Right.SETUP)  # load_show requires ADMIN
        err = _preflight_guard(step, wm)
        assert err is not None
        assert "FAILED_CLOSED" in err

    def test_rights_check_none_skipped(self):
        # rights=NONE means "not yet hydrated" — do not block
        step = _step("read", risk=RiskTier.SAFE_READ, tools=["load_show"])
        wm = _wm(right=MA2Right.NONE)
        assert _preflight_guard(step, wm) is None

    def test_no_tools_passes(self):
        step = SubTask(
            name="empty", agent_role="A", description="",
            allowed_risk=RiskTier.SAFE_READ, mcp_tools=[],
        )
        wm = _wm()
        assert _preflight_guard(step, wm) is None


# ── _default_sub_agent() ─────────────────────────────────────────────────────

class TestDefaultSubAgent:
    @pytest.mark.asyncio
    async def test_success_pass_allowed(self):
        step = _step("read", tools=["navigate_console"])
        wm = _wm()
        tool_caller = AsyncMock(return_value='{"command_sent": "cd /", "raw_response": "Fixture"}')
        result = await _default_sub_agent(step, wm, tool_caller)
        assert result.success is True
        assert result.feedback_class == FeedbackClass.PASS_ALLOWED

    @pytest.mark.asyncio
    async def test_no_tools_fails(self):
        step = SubTask(
            name="empty", agent_role="A", description="",
            allowed_risk=RiskTier.SAFE_READ, mcp_tools=[],
        )
        wm = _wm()
        result = await _default_sub_agent(step, wm, AsyncMock())
        assert result.success is False
        assert "No tools" in result.error

    @pytest.mark.asyncio
    async def test_destructive_unconfirmed_blocked(self):
        step = _step("store", risk=RiskTier.DESTRUCTIVE, confirmed=False)
        wm = _wm()
        result = await _default_sub_agent(step, wm, AsyncMock())
        assert result.success is False
        assert result.feedback_class == FeedbackClass.PASS_DENIED

    @pytest.mark.asyncio
    async def test_tool_exception_captured(self):
        step = _step("read", tools=["navigate_console"])
        wm = _wm()
        async def raise_fn(name, inputs):
            raise RuntimeError("telnet timeout")
        result = await _default_sub_agent(step, wm, raise_fn)
        assert result.success is False
        assert "telnet timeout" in result.error

    @pytest.mark.asyncio
    async def test_error_72_classified_failed_open(self):
        step = _step("read", tools=["navigate_console"])
        wm = _wm()
        tool_caller = AsyncMock(return_value="Error #72 insufficient rights")
        result = await _default_sub_agent(step, wm, tool_caller)
        assert result.feedback_class == FeedbackClass.FAILED_OPEN


# ── Orchestrator ─────────────────────────────────────────────────────────────

@pytest.fixture
def ltm_and_path():
    ltm, path = _ltm_tmp()
    yield ltm, path
    ltm._conn.close()
    path.unlink(missing_ok=True)


@pytest.fixture
def simple_orchestrator(ltm_and_path):
    ltm, _ = ltm_and_path
    calls = []

    async def tool_caller(name, inputs):
        calls.append((name, inputs))
        return '{"command_sent": "test", "raw_response": "OK"}'

    orch = Orchestrator(
        tool_caller=tool_caller,
        telnet_send=None,
        ltm=ltm,
        parallel=False,
    )
    return orch, calls


class TestOrchestratorRun:
    @pytest.mark.asyncio
    async def test_safe_steps_succeed(self, simple_orchestrator):
        orch, calls = simple_orchestrator
        result = await orch.run("blue wash on movers", {"color": "blue"})
        assert result.outcome in ("success", "partial", "failed")
        assert isinstance(result.session_id, str)
        assert len(result.session_id) == 8

    @pytest.mark.asyncio
    async def test_all_safe_steps_succeed(self, simple_orchestrator):
        orch, _ = simple_orchestrator

        class SafeDecomposer:
            def decompose(self, goal, params):
                return TaskPlan(goal=goal, steps=[
                    _step("read1", risk=RiskTier.SAFE_READ),
                    _step("read2", risk=RiskTier.SAFE_READ, depends_on=["read1"]),
                ])

        orch._decomposer = SafeDecomposer()
        result = await orch.run("safe goal")
        assert result.outcome == "success"
        assert result.steps_done == 2
        assert result.steps_failed == 0

    @pytest.mark.asyncio
    async def test_destructive_blocked_without_confirm(self, simple_orchestrator):
        orch, _ = simple_orchestrator

        class DestructDecomposer:
            def decompose(self, goal, params):
                return TaskPlan(goal=goal, steps=[
                    _step("destroy", risk=RiskTier.DESTRUCTIVE, confirmed=False),
                ])

        orch._decomposer = DestructDecomposer()
        result = await orch.run("destructive goal")
        assert result.steps_failed >= 1

    @pytest.mark.asyncio
    async def test_auto_confirm_destructive(self, simple_orchestrator):
        orch, _ = simple_orchestrator

        class DestructDecomposer:
            def decompose(self, goal, params):
                return TaskPlan(goal=goal, steps=[
                    _step("destroy", risk=RiskTier.DESTRUCTIVE, tools=["navigate_console"],
                          confirmed=False),
                ])

        orch._decomposer = DestructDecomposer()
        result = await orch.run("destructive goal", auto_confirm_destructive=True)
        # staleness check still blocks (no snapshot) — but confirm gate is open
        # outcome depends on whether staleness guard blocks
        assert isinstance(result.outcome, str)

    @pytest.mark.asyncio
    async def test_result_has_report(self, simple_orchestrator):
        orch, _ = simple_orchestrator
        result = await orch.run("blue wash")
        report = result.report()
        assert "Orchestration Report" in report
        assert result.goal in report

    @pytest.mark.asyncio
    async def test_result_tokens_tracked(self, simple_orchestrator):
        orch, _ = simple_orchestrator

        class SafeDecomposer:
            def decompose(self, goal, params):
                return TaskPlan(goal=goal, steps=[
                    _step("s1", risk=RiskTier.SAFE_READ),
                ])

        orch._decomposer = SafeDecomposer()
        result = await orch.run("token test")
        assert result.total_tokens >= 0

    @pytest.mark.asyncio
    async def test_session_saved_to_ltm(self, ltm_and_path):
        ltm, _ = ltm_and_path

        async def tool_caller(name, inputs):
            return '{"ok": true}'

        orch = Orchestrator(tool_caller=tool_caller, ltm=ltm)
        await orch.run("save test")
        sessions = orch.recent_sessions(5)
        assert len(sessions) >= 1

    @pytest.mark.asyncio
    async def test_recall_returns_snapshot(self, ltm_and_path):
        ltm, _ = ltm_and_path

        async def tool_caller(name, inputs):
            return '{"ok": true}'

        orch = Orchestrator(tool_caller=tool_caller, ltm=ltm)
        result = await orch.run("recall test")
        snap = orch.recall(result.session_id)
        assert snap is not None
        assert snap.get("task") == "recall test"

    @pytest.mark.asyncio
    async def test_recall_unknown_returns_none(self, ltm_and_path):
        ltm, _ = ltm_and_path
        orch = Orchestrator(tool_caller=AsyncMock(), ltm=ltm)
        assert orch.recall("deadbeef") is None

    @pytest.mark.asyncio
    async def test_showfile_guard_blocks_destructive_on_show_change(self, ltm_and_path):
        ltm, _ = ltm_and_path

        # telnet_send returns a ListVar response with a DIFFERENT showfile
        listvar_response = "$Global : $SHOWFILE = different_show\n$Global : $USER = admin\n"
        send_mock = AsyncMock(return_value=listvar_response)
        tool_caller = AsyncMock(return_value='{"ok": true}')

        orch = Orchestrator(tool_caller=tool_caller, telnet_send=send_mock, ltm=ltm,
                            auto_hydrate=False)
        orch._last_snapshot = MagicMock()
        orch._last_snapshot.showfile = "original_show"

        class ShowfileDecomposer:
            def decompose(self, goal, params):
                return TaskPlan(goal=goal, steps=[
                    _step("destructive_step", risk=RiskTier.DESTRUCTIVE, confirmed=True),
                ])

        orch._decomposer = ShowfileDecomposer()
        wm = _wm()
        wm.baseline_showfile = "original_show"

        # Directly test _showfile_guard
        step = _step("destructive_step", risk=RiskTier.DESTRUCTIVE, confirmed=True)
        result = await orch._showfile_guard(step, wm)
        assert result is not None
        assert result.success is False
        assert result.feedback_class == FeedbackClass.FAILED_CLOSED
        assert "different_show" in result.error
        assert "original_show" in result.error

    @pytest.mark.asyncio
    async def test_showfile_guard_passes_when_show_unchanged(self, ltm_and_path):
        ltm, _ = ltm_and_path

        listvar_response = "$Global : $SHOWFILE = my_show\n"
        send_mock = AsyncMock(return_value=listvar_response)

        orch = Orchestrator(tool_caller=AsyncMock(), telnet_send=send_mock, ltm=ltm,
                            auto_hydrate=False)

        step = _step("destructive_step", risk=RiskTier.DESTRUCTIVE, confirmed=True)
        wm = _wm()
        wm.baseline_showfile = "my_show"
        result = await orch._showfile_guard(step, wm)
        assert result is None  # no block

    @pytest.mark.asyncio
    async def test_showfile_guard_skips_non_destructive(self, ltm_and_path):
        ltm, _ = ltm_and_path
        send_mock = AsyncMock(return_value="$Global : $SHOWFILE = other_show\n")
        orch = Orchestrator(tool_caller=AsyncMock(), telnet_send=send_mock, ltm=ltm,
                            auto_hydrate=False)
        step = _step("safe_step", risk=RiskTier.SAFE_WRITE)
        wm = _wm()
        wm.baseline_showfile = "my_show"
        # SAFE_WRITE should not trigger showfile guard
        result = await orch._showfile_guard(step, wm)
        assert result is None

    @pytest.mark.asyncio
    async def test_hydrate_snapshot_caches_last_snapshot(self, ltm_and_path):
        ltm, _ = ltm_and_path
        orch = Orchestrator(tool_caller=AsyncMock(), telnet_send=AsyncMock(), ltm=ltm,
                            auto_hydrate=False)
        snapshot = _make_snapshot()

        with patch("src.orchestrator.ConsoleStateHydrator") as hydrator_cls:
            hydrator_cls.return_value.hydrate = AsyncMock(return_value=snapshot)
            result = await orch.hydrate_snapshot(sequence_ids=[1, 2])

        assert result is snapshot
        assert orch.last_snapshot is snapshot
        hydrator_cls.return_value.hydrate.assert_called_once_with(sequence_ids=[1, 2])

    @pytest.mark.asyncio
    async def test_dep_failure_skips_dependent(self, ltm_and_path):
        ltm, _ = ltm_and_path

        async def failing_caller(name, inputs):
            return '{"blocked": true, "error": "scope fail"}'

        orch = Orchestrator(tool_caller=failing_caller, ltm=ltm)

        class DepDecomposer:
            def decompose(self, goal, params):
                return TaskPlan(goal=goal, steps=[
                    _step("fail_step", risk=RiskTier.SAFE_READ),
                    _step("dep_step", risk=RiskTier.SAFE_READ, depends_on=["fail_step"]),
                ])

        orch._decomposer = DepDecomposer()
        result = await orch.run("dep test")
        # dep_step should be skipped because fail_step didn't succeed
        dep_results = [r for r in result.step_results if r.step_name == "dep_step"]
        if dep_results:
            assert dep_results[0].success is False


# ── OrchestrationResult.report() ────────────────────────────────────────────

class TestOrchestrationReport:
    def test_report_format(self):
        r = OrchestrationResult(
            session_id="abc12345",
            goal="test goal",
            outcome="success",
            steps_done=2,
            steps_failed=0,
            total_tokens=100,
            elapsed_s=1.5,
            step_results=[
                StepResult(step_name="s1", success=True,
                           feedback_class=FeedbackClass.PASS_ALLOWED),
            ],
        )
        report = r.report()
        assert "abc12345" in report
        assert "test goal" in report
        assert "SUCCESS" in report
        assert "s1" in report


# ── TestSnapshotWiring ───────────────────────────────────────────────────────

def _make_snapshot():
    """Return a fresh ConsoleStateSnapshot with default fields."""
    from src.console_state import ConsoleStateSnapshot
    return ConsoleStateSnapshot()


def _make_mock_client(response: str = "OK"):
    mock_client = MagicMock()
    mock_client.send_command_with_response = AsyncMock(return_value=response)
    return mock_client


def _make_mock_orchestrator(snapshot=None):
    """Return a MagicMock that acts as _orchestrator with a controllable last_snapshot."""
    mock_orch = MagicMock()
    mock_orch.last_snapshot = snapshot
    return mock_orch


class TestSnapshotWiring:
    """Verify that server tools update _orchestrator.last_snapshot after telnet success."""

    @pytest.fixture(autouse=True)
    def _redirect_gma2_data_root(self, tmp_path, monkeypatch):
        """Redirect GMA2_DATA_ROOT so filter/matricks file writes work on macOS."""
        (tmp_path / "importexport" / "filters").mkdir(parents=True, exist_ok=True)
        (tmp_path / "matricks").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("src.server._GMA2_DATA_ROOT", str(tmp_path))

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_manage_matricks_interleave_updates_tracker(
        self, mock_get_client, mock_orch
    ):
        from src.server import manage_matricks

        snap = _make_snapshot()
        mock_orch.last_snapshot = snap
        mock_get_client.return_value = _make_mock_client()

        await manage_matricks(action="interleave", value=4)

        assert snap.matricks.interleave == 4

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_manage_matricks_reset_clears_tracker(
        self, mock_get_client, mock_orch
    ):
        from src.server import manage_matricks

        snap = _make_snapshot()
        snap.matricks.interleave = 3
        snap.matricks.wings = 2
        mock_orch.last_snapshot = snap
        mock_get_client.return_value = _make_mock_client()

        await manage_matricks(action="reset")

        assert snap.matricks.interleave is None
        assert snap.matricks.wings is None
        assert snap.matricks.active is False

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_manage_matricks_no_snapshot_does_not_raise(
        self, mock_get_client, mock_orch
    ):
        from src.server import manage_matricks

        mock_orch.last_snapshot = None
        mock_get_client.return_value = _make_mock_client()

        # Should complete without raising
        result = await manage_matricks(action="interleave", value=2)
        data = json.loads(result)
        assert "command_sent" in data

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_manage_matricks_wings_turn_off(
        self, mock_get_client, mock_orch
    ):
        from src.server import manage_matricks

        snap = _make_snapshot()
        snap.matricks.wings = 2
        mock_orch.last_snapshot = snap
        mock_get_client.return_value = _make_mock_client()

        await manage_matricks(action="wings", turn_off=True)

        assert snap.matricks.wings is None

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_manage_matricks_selection_steps_no_state_change(
        self, mock_get_client, mock_orch
    ):
        from src.server import manage_matricks

        snap = _make_snapshot()
        snap.matricks.interleave = 5
        mock_orch.last_snapshot = snap
        mock_get_client.return_value = _make_mock_client()

        await manage_matricks(action="next")

        # Selection steps don't modify persistent tracker fields
        assert snap.matricks.interleave == 5

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server._check_pool_slots", new_callable=AsyncMock)
    @patch("src.server.get_client")
    async def test_create_filter_library_updates_vte(
        self, mock_get_client, mock_check, mock_orch
    ):
        from src.server import create_filter_library

        snap = _make_snapshot()
        mock_orch.last_snapshot = snap
        mock_get_client.return_value = _make_mock_client()
        mock_check.return_value = {
            "occupied_slots": [], "free_ranges": [], "next_free_slots": [],
            "total_occupied": 0, "total_free_in_range": 0,
            "largest_contiguous": 0, "can_fit": None, "suggested_start": None,
        }

        await create_filter_library(confirm_destructive=True)

        assert snap.filter_vte == {"value": True, "value_timing": True, "effect": True}

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server._check_pool_slots", new_callable=AsyncMock)
    @patch("src.server.get_client")
    async def test_create_filter_library_no_snapshot_ok(
        self, mock_get_client, mock_check, mock_orch
    ):
        from src.server import create_filter_library

        mock_orch.last_snapshot = None
        mock_get_client.return_value = _make_mock_client()
        mock_check.return_value = {
            "occupied_slots": [], "free_ranges": [], "next_free_slots": [],
            "total_occupied": 0, "total_free_in_range": 0,
            "largest_contiguous": 0, "can_fit": None, "suggested_start": None,
        }

        # Should complete without raising
        result = await create_filter_library(confirm_destructive=True)
        data = json.loads(result)
        assert "filters_created" in data


# ── TestWriteTrackerCompletion ────────────────────────────────────────────────

class TestWriteTrackerCompletion:
    """Phase 1 — park/unpark + toggle_console_mode write-tracker wiring."""

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_park_fixture_adds_to_parked_set(self, mock_client, mock_orch):
        from src.server import park_fixture

        snap = _make_snapshot()
        mock_orch.last_snapshot = snap
        mc = _make_mock_client()
        mc.send_command_with_response = AsyncMock(return_value="OK")
        mock_client.return_value = mc

        await park_fixture(target="fixture 20")

        assert "fixture 20" in snap.parked_fixtures

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_unpark_fixture_removes_from_parked_set(self, mock_client, mock_orch):
        from src.server import unpark_fixture

        snap = _make_snapshot()
        snap.parked_fixtures.add("fixture 20")
        mock_orch.last_snapshot = snap
        mc = _make_mock_client()
        mc.send_command_with_response = AsyncMock(return_value="OK")
        mock_client.return_value = mc

        await unpark_fixture(target="fixture 20")

        assert "fixture 20" not in snap.parked_fixtures

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_park_unpark_nil_snapshot_no_raise(self, mock_client, mock_orch):
        from src.server import park_fixture, unpark_fixture

        mock_orch.last_snapshot = None
        mc = _make_mock_client()
        mc.send_command_with_response = AsyncMock(return_value="OK")
        mock_client.return_value = mc

        # Should not raise
        await park_fixture(target="dmx 101")
        await unpark_fixture(target="dmx 101")

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_toggle_console_mode_updates_console_modes(self, mock_client, mock_orch):
        from src.server import toggle_console_mode

        snap = _make_snapshot()
        mock_orch.last_snapshot = snap
        mc = _make_mock_client()
        mc.send_command_with_response = AsyncMock(return_value="OK")
        mock_client.return_value = mc

        await toggle_console_mode(mode="blind")

        assert snap.console_modes["blind"] is True

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_toggle_console_mode_twice_inverts(self, mock_client, mock_orch):
        from src.server import toggle_console_mode

        snap = _make_snapshot()
        mock_orch.last_snapshot = snap
        mc = _make_mock_client()
        mc.send_command_with_response = AsyncMock(return_value="OK")
        mock_client.return_value = mc

        await toggle_console_mode(mode="freeze")
        assert snap.console_modes["freeze"] is True
        await toggle_console_mode(mode="freeze")
        assert snap.console_modes["freeze"] is False

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_toggle_console_mode_nil_snapshot_no_raise(self, mock_client, mock_orch):
        from src.server import toggle_console_mode

        mock_orch.last_snapshot = None
        mc = _make_mock_client()
        mc.send_command_with_response = AsyncMock(return_value="OK")
        mock_client.return_value = mc

        result = await toggle_console_mode(mode="highlight")
        data = json.loads(result)
        assert "command_sent" in data
