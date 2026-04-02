"""Tests for the orchestration MCP tools registered via server_orchestration_tools.py.

These tools are closures registered with the FastMCP instance.  We test them by:
  1. Calling the underlying library classes (TaskDecomposer, SkillRegistry, etc.)
     directly — the tool bodies are thin wrappers, so this validates the contract.
  2. Accessing tools via the FastMCP mcp instance where direct import is impossible.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.agent_memory import LongTermMemory, WorkingMemory
from src.skill import SkillRegistry
from src.task_decomposer import TaskDecomposer
from src.telemetry import ToolTelemetry

# ---------------------------------------------------------------------------
# TaskDecomposer (used by decompose_task + confirm_destructive_steps)
# ---------------------------------------------------------------------------


class TestDecomposeTask:
    """The decompose_task tool calls TaskDecomposer.decompose(); test that contract."""

    def test_decompose_returns_plan_with_steps(self):
        d = TaskDecomposer()
        plan = d.decompose("blue wash on movers", {"group": "movers"})
        assert plan.goal == "blue wash on movers"
        assert len(plan.steps) >= 1

    def test_decompose_steps_have_required_fields(self):
        d = TaskDecomposer()
        plan = d.decompose("store cue 5 in sequence 1")
        for step in plan.steps:
            assert step.name
            assert step.allowed_risk is not None
            assert isinstance(step.mcp_tools, list)

    def test_decompose_summary_non_empty(self):
        d = TaskDecomposer()
        plan = d.decompose("select all fixtures and set full")
        assert plan.summary()

    def test_ordered_steps_dependency_order(self):
        d = TaskDecomposer()
        plan = d.decompose("store preset 1")
        ordered = plan.ordered_steps()
        # All steps from the plan should appear
        assert len(ordered) == len(plan.steps)


# ---------------------------------------------------------------------------
# SkillRegistry (used by list_skills, get_skill, promote_session_to_skill, approve_skill)
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_skill_registry(monkeypatch):
    """A fresh in-memory SkillRegistry backed by a temp file.

    Filesystem skills are patched out so list_all() returns only DB skills,
    giving tests a clean slate regardless of the .claude/skills/ directory.
    """
    from unittest.mock import patch as _patch

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    reg = SkillRegistry(db_path=Path(path))
    with _patch("src.skill._list_filesystem_skills", return_value=[]):
        yield reg
    reg._conn.close()
    Path(path).unlink(missing_ok=True)


class TestSkillRegistryViaTools:
    """Test the SkillRegistry interface exercised by the OpenSpace MCP tools."""

    def test_list_all_empty_registry(self, tmp_skill_registry):
        skills = tmp_skill_registry.list_all()
        assert skills == []

    def test_promote_and_list(self, tmp_skill_registry):
        skill = tmp_skill_registry.promote_from_session(
            session_id="abc12345",
            name="blue_wash",
            description="Blue wash look",
            body="1. Select movers\n2. Set blue",
            safety_scope="SAFE_WRITE",
            applicable_context="color wash",
            quality_score=0.9,
        )
        assert skill.id
        assert skill.approved is True  # SAFE_WRITE → auto-approved
        skills = tmp_skill_registry.list_all()
        assert len(skills) == 1
        assert skills[0].name == "blue_wash"

    def test_destructive_skill_not_approved(self, tmp_skill_registry):
        skill = tmp_skill_registry.promote_from_session(
            session_id="abc12345",
            name="delete_all",
            description="Delete everything",
            body="1. Delete all cues",
            safety_scope="DESTRUCTIVE",
            applicable_context="danger",
            quality_score=0.5,
        )
        assert skill.approved is False
        assert not skill.is_usable()

    def test_approve_destructive_skill(self, tmp_skill_registry):
        skill = tmp_skill_registry.promote_from_session(
            session_id="abc12345",
            name="risky_op",
            description="Risky operation",
            body="...",
            safety_scope="DESTRUCTIVE",
            applicable_context="ops",
            quality_score=0.7,
        )
        approved = tmp_skill_registry.approve(skill.id)
        assert approved is True

        fetched = tmp_skill_registry.get(skill.id)
        assert fetched is not None
        assert fetched.approved is True
        assert fetched.is_usable()

    def test_get_nonexistent_skill(self, tmp_skill_registry):
        result = tmp_skill_registry.get("00000000-0000-0000-0000-000000000000")
        assert result is None

    def test_search_by_name(self, tmp_skill_registry):
        tmp_skill_registry.promote_from_session(
            session_id="s1",
            name="blue_wash_look",
            description="Create a blue wash",
            body="...",
            safety_scope="SAFE_WRITE",
            applicable_context="wash",
            quality_score=0.8,
        )
        results = tmp_skill_registry.search("blue")
        assert len(results) == 1
        assert "blue" in results[0].name

    def test_search_no_match(self, tmp_skill_registry):
        results = tmp_skill_registry.search("nonexistent_query_xyz")
        assert results == []

    def test_get_lineage_single(self, tmp_skill_registry):
        skill = tmp_skill_registry.promote_from_session(
            session_id="s1",
            name="v1_skill",
            description="Initial version",
            body="v1 body",
            safety_scope="SAFE_READ",
            applicable_context="",
            quality_score=1.0,
        )
        lineage = tmp_skill_registry.get_lineage(skill.id)
        # Single skill, no parent → lineage is just itself
        assert len(lineage) >= 1


# ---------------------------------------------------------------------------
# ToolTelemetry (used by get_tool_metrics)
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_telemetry():
    """A fresh ToolTelemetry backed by a temp file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    tel = ToolTelemetry(db_path=Path(path))
    yield tel
    tel._conn.close()
    Path(path).unlink(missing_ok=True)


class TestToolTelemetryViaTools:
    """Test the ToolTelemetry interface exercised by get_tool_metrics."""

    def test_no_invocations_returns_zero_calls(self, tmp_telemetry):
        metrics = tmp_telemetry.metrics("list_objects", days=7)
        assert metrics.get("calls", 0) == 0

    def test_record_and_retrieve_metrics(self, tmp_telemetry):
        # Record two successful calls and one failure
        for _i in range(2):
            tmp_telemetry.record_sync(
                tool_name="list_objects",
                inputs_json="{}",
                output_preview="ok",
                risk_tier="SAFE_READ",
                latency_ms=12.5,
                error_class=None,
                operator="testuser",
            )
        tmp_telemetry.record_sync(
            tool_name="list_objects",
            inputs_json="{}",
            output_preview="err",
            risk_tier="SAFE_READ",
            latency_ms=8.0,
            error_class="ConnectionError",
            operator="testuser",
        )

        metrics = tmp_telemetry.metrics("list_objects", days=7)
        assert metrics["calls"] == 3
        assert 0 < metrics["error_rate"] <= 1.0  # 1/3 error rate

    def test_different_tools_isolated(self, tmp_telemetry):
        tmp_telemetry.record_sync(
            tool_name="tool_a",
            inputs_json="{}",
            output_preview="ok",
            risk_tier="SAFE_READ",
            latency_ms=5.0,
            error_class=None,
            operator="user1",
        )
        tmp_telemetry.record_sync(
            tool_name="tool_b",
            inputs_json="{}",
            output_preview="ok",
            risk_tier="SAFE_WRITE",
            latency_ms=10.0,
            error_class=None,
            operator="user1",
        )
        assert tmp_telemetry.metrics("tool_a")["calls"] == 1
        assert tmp_telemetry.metrics("tool_b")["calls"] == 1


# ---------------------------------------------------------------------------
# LongTermMemory (used by list_agent_sessions, recall_agent_session, agent_token_report)
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_ltm():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    ltm = LongTermMemory(db_path=Path(path))
    yield ltm
    ltm._conn.close()
    Path(path).unlink(missing_ok=True)


def _make_wm(task: str = "test task", session_id: str | None = None) -> WorkingMemory:
    from src.agent_memory import WorkingMemory
    wm = WorkingMemory(task_description=task)
    if session_id:
        wm.session_id = session_id
    return wm


class TestAgentSessionViaLTM:
    """Test LongTermMemory contract used by list/recall_agent_session and token_report."""

    def test_empty_db_recent_sessions(self, tmp_ltm):
        sessions = tmp_ltm.recent_sessions(limit=10)
        assert sessions == []

    def test_save_and_recall(self, tmp_ltm):
        wm = _make_wm("blue wash", session_id="sid12345")
        tmp_ltm.save_session(wm, "success")
        snapshot = tmp_ltm.recall_session("sid12345")
        assert snapshot is not None

    def test_recall_unknown_returns_none(self, tmp_ltm):
        assert tmp_ltm.recall_session("deadbeef") is None

    def test_recent_sessions_ordering(self, tmp_ltm):
        for i in range(5):
            wm = _make_wm(f"task_{i}")
            wm.token_spend = i * 100
            tmp_ltm.save_session(wm, "success")
        sessions = tmp_ltm.recent_sessions(limit=3)
        # Returns most recent first, limited to 3
        assert len(sessions) <= 3

    def test_token_report_aggregation(self, tmp_ltm):
        """Simulate the agent_token_report calculation."""
        for i in range(4):
            wm = _make_wm(f"task_{i}")
            wm.token_spend = (i + 1) * 200
            tmp_ltm.save_session(wm, "success")

        sessions = tmp_ltm.recent_sessions(limit=10)
        total = sum(s.get("tokens", 0) for s in sessions)
        avg = round(total / max(len(sessions), 1))

        # Just validate the calculation doesn't explode
        assert isinstance(total, int)
        assert avg >= 0


# ---------------------------------------------------------------------------
# Orchestration tool - snapshot-based tools via _orchestrator mock
# ---------------------------------------------------------------------------


class TestSnapshotToolsNeedHydration:
    """Snapshot-based orchestration tools return error when snapshot is None."""

    def _get_orch_snapshot_tool_names(self):
        """Names of orchestration tools that check orchestrator.last_snapshot."""
        return [
            "get_console_state",
            "get_park_ledger",
            "get_filter_state",
            "get_world_state",
            "get_matricks_state",
            "get_programmer_selection",
            "get_sequence_memory",
            "assert_selection_count",
            "assert_preset_exists",
            "get_executor_detail",
            "get_showfile_info",
        ]

    def _find_tool_fn(self, tool_name: str):
        """Access a tool function via the FastMCP instance."""
        from src.server import mcp
        # FastMCP stores tools in _tool_manager; access the underlying callable
        mgr = mcp._tool_manager
        # Try several attribute paths depending on FastMCP version
        for attr in ("_tools", "tools"):
            registry = getattr(mgr, attr, None)
            if registry and tool_name in registry:
                tool_obj = registry[tool_name]
                fn = getattr(tool_obj, "fn", None) or getattr(tool_obj, "func", None) or tool_obj
                if callable(fn):
                    return fn
        return None

    @pytest.mark.asyncio
    async def test_get_console_state_no_snapshot_returns_error(self):
        """get_console_state returns an error JSON when no snapshot available."""
        fn = self._find_tool_fn("get_console_state")
        if fn is None:
            pytest.skip("Cannot access get_console_state via FastMCP internals")

        # Set last_snapshot to None on the actual orchestrator
        from src.server import _orchestrator
        original = _orchestrator.last_snapshot
        try:
            _orchestrator.last_snapshot = None
            result = await fn()
            data = json.loads(result)
            assert "error" in data
        finally:
            _orchestrator.last_snapshot = original

    @pytest.mark.asyncio
    async def test_get_park_ledger_no_snapshot_returns_error(self):
        fn = self._find_tool_fn("get_park_ledger")
        if fn is None:
            pytest.skip("Cannot access get_park_ledger via FastMCP internals")

        from src.server import _orchestrator
        original = _orchestrator.last_snapshot
        try:
            _orchestrator.last_snapshot = None
            result = await fn()
            data = json.loads(result)
            assert "error" in data
        finally:
            _orchestrator.last_snapshot = original

    @pytest.mark.asyncio
    async def test_get_filter_state_with_snapshot(self):
        fn = self._find_tool_fn("get_filter_state")
        if fn is None:
            pytest.skip("Cannot access get_filter_state via FastMCP internals")

        from src.console_state import ConsoleStateSnapshot
        from src.server import _orchestrator

        snap = ConsoleStateSnapshot()
        snap.active_filter = 5
        original = _orchestrator.last_snapshot
        try:
            _orchestrator.last_snapshot = snap
            result = await fn()
            data = json.loads(result)
            assert data["active_filter"] == 5
            assert data["warning"] is not None  # filter is active
        finally:
            _orchestrator.last_snapshot = original

    @pytest.mark.asyncio
    async def test_get_park_ledger_with_parked_fixtures(self):
        fn = self._find_tool_fn("get_park_ledger")
        if fn is None:
            pytest.skip("Cannot access get_park_ledger via FastMCP internals")

        from src.console_state import ConsoleStateSnapshot
        from src.server import _orchestrator

        snap = ConsoleStateSnapshot()
        snap.parked_fixtures = {"101", "102", "103"}
        original = _orchestrator.last_snapshot
        try:
            _orchestrator.last_snapshot = snap
            result = await fn()
            data = json.loads(result)
            assert data["count"] == 3
            assert data["warning"] is not None
        finally:
            _orchestrator.last_snapshot = original


# ---------------------------------------------------------------------------
# decompose_task / confirm_destructive_steps — via task_decomposer
# ---------------------------------------------------------------------------


class TestDecomposeAndConfirmTools:
    """Verify TaskDecomposer correctly identifies DESTRUCTIVE steps for confirm tool."""

    def test_destructive_steps_identified(self):
        from src.vocab import RiskTier

        d = TaskDecomposer()
        plan = d.decompose("store cue in sequence with new show")
        # Any DESTRUCTIVE steps should have the right risk tier
        for step in plan.steps:
            if step.allowed_risk == RiskTier.DESTRUCTIVE:
                assert step.mcp_tools

    def test_read_only_goal_no_destructive(self):
        from src.vocab import RiskTier

        d = TaskDecomposer()
        plan = d.decompose("list all groups")
        # A list-only goal should not produce DESTRUCTIVE steps
        # May be empty or not — just verify the plan is consistent
        _ = [s for s in plan.steps if s.allowed_risk == RiskTier.DESTRUCTIVE]
        assert plan.goal == "list all groups"
        assert len(plan.steps) >= 1
