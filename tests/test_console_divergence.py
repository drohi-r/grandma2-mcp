"""Tests for console divergence detection: the baseline/diff tools and the
agent runtime's pre-destructive showfile guard + recipe learning loop."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.runtime import AgentRuntime
from src.vocab import RiskTier


def _listvar_raw(showfile: str, faderpage: str = "1") -> str:
    return (
        f"$Global : $SHOWFILE = {showfile}\n"
        "$Global : $USER = administrator\n"
        "$Global : $USERPROFILE = Default\n"
        f"$Global : $FADERPAGE = {faderpage}\n"
        "$Global : $BUTTONPAGE = 1\n"
        "$Global : $CHANNELPAGE = 1\n"
        "$Global : $SELECTEDEXEC = 1.1.1\n"
    )


def _pool_raw(keyword: str, ids: list[int]) -> str:
    return "\n".join(f"{keyword.capitalize()} 1 {i}   Obj {i}" for i in ids)


def _mock_client(showfile: str, group_ids: list[int]):
    client = MagicMock()

    async def send(cmd: str, **kw):
        if cmd == "ListVar":
            return _listvar_raw(showfile)
        kw_name = cmd.split()[1] if cmd.startswith("list ") else ""
        if kw_name == "group":
            return _pool_raw("group", group_ids)
        return ""

    client.send_command_with_response = AsyncMock(side_effect=send)
    return client


# ---------------------------------------------------------------- MCP tools

class TestDivergenceTools:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_no_baseline_errors(self, mock_get_client):
        import src.server as server
        server._console_baseline = None
        data = json.loads(await server.detect_console_divergence())
        assert data["diverged"] is None
        assert "baseline" in data["error"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_snapshot_then_no_divergence(self, mock_get_client):
        import src.server as server
        mock_get_client.return_value = _mock_client("show_a", [1, 2])
        snap = json.loads(await server.snapshot_console_baseline())
        assert snap["baseline"]["vars"]["$SHOWFILE"] == "show_a"
        data = json.loads(await server.detect_console_divergence())
        assert data["diverged"] is False
        assert data["changed_vars"] == {} and data["pool_changes"] == {}

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_detects_show_and_pool_changes(self, mock_get_client):
        import src.server as server
        mock_get_client.return_value = _mock_client("show_a", [1, 2])
        await server.snapshot_console_baseline()
        # Operator loads another show and deletes group 2 / adds group 9
        mock_get_client.return_value = _mock_client("show_b", [1, 9])
        data = json.loads(await server.detect_console_divergence())
        assert data["diverged"] is True
        assert data["changed_vars"]["$SHOWFILE"]["current"] == "show_b"
        assert data["pool_changes"]["group"] == {"added": [9], "removed": [2]}
        assert "warning" in data


# ---------------------------------------------------------------- runtime guard

def _registry_with_showfile(showfiles: list[str], calls: list[str]):
    """Tool registry whose list_system_variables returns successive showfiles."""
    state = {"i": 0}

    async def list_system_variables(filter_prefix=None):
        idx = min(state["i"], len(showfiles) - 1)
        state["i"] += 1
        return json.dumps({"variables": {"$SHOWFILE": showfiles[idx]}})

    async def safe_tool(**kw):
        calls.append("safe_tool")
        return json.dumps({"ok": True})

    async def destructive_tool(**kw):
        calls.append("destructive_tool")
        return json.dumps({"ok": True})

    return {
        "list_system_variables": list_system_variables,
        "query_object_list": safe_tool,
        "store_object": destructive_tool,
    }


class TestShowfilePreflight:
    @pytest.mark.asyncio
    async def test_destructive_step_aborts_on_showfile_change(self, tmp_path):
        from src.agent.state import PlanStep, RunContext, RunStatus

        calls: list[str] = []
        # Baseline read shows show_a; the preflight read shows show_b
        registry = _registry_with_showfile(["show_a", "show_b"], calls)
        runtime = AgentRuntime(
            tool_registry=registry, memory_db_path=str(tmp_path / "wm.db")
        )
        runtime._baseline_showfile = await runtime._read_showfile()

        step = PlanStep(
            tool_name="store_object",
            tool_args={},
            description="destructive step",
            risk_tier=RiskTier.DESTRUCTIVE,
        )
        context = RunContext(goal="g", plan=[step])
        context = await runtime.executor.execute_plan(context)

        assert context.status == RunStatus.ABORTED
        assert "showfile changed" in (step.error or "")
        assert "destructive_tool" not in calls

    @pytest.mark.asyncio
    async def test_safe_steps_skip_preflight(self, tmp_path):
        from src.agent.state import PlanStep, RunContext, RunStatus

        calls: list[str] = []
        registry = _registry_with_showfile(["show_a", "show_b"], calls)
        runtime = AgentRuntime(
            tool_registry=registry, memory_db_path=str(tmp_path / "wm.db")
        )
        runtime._baseline_showfile = await runtime._read_showfile()

        step = PlanStep(
            tool_name="query_object_list",
            tool_args={},
            description="safe step",
            risk_tier=RiskTier.SAFE_READ,
        )
        context = RunContext(goal="g", plan=[step])
        context = await runtime.executor.execute_plan(context)
        assert context.status == RunStatus.COMPLETED
        assert calls == ["safe_tool"]


# ---------------------------------------------------------------- recipe loop

class TestRecipeLoop:
    @pytest.mark.asyncio
    async def test_success_stores_recipe_and_replays_it(self, tmp_path):
        calls: list[str] = []
        registry = _registry_with_showfile(["show_a"], calls)
        runtime = AgentRuntime(
            tool_registry=registry, memory_db_path=str(tmp_path / "wm.db")
        )

        goal = "list all groups"
        trace1 = await runtime.run(goal)
        assert trace1.result == "success"
        recipes = runtime.memory.recall_recipe(name="list all groups")
        assert len(recipes) == 1, "successful run must be captured as a recipe"

        # Second identical run replays the recipe (use_count increments)
        trace2 = await runtime.run(goal)
        assert trace2.result == "success"
        recipes = runtime.memory.recall_recipe(name="list all groups")
        assert recipes[0]["use_count"] == 1

    @pytest.mark.asyncio
    async def test_recipe_sanitizes_destructive_confirm(self, tmp_path):
        from src.agent.state import PlanStep

        registry = _registry_with_showfile(["show_a"], [])
        runtime = AgentRuntime(
            tool_registry=registry, memory_db_path=str(tmp_path / "wm.db")
        )
        step = PlanStep(
            tool_name="store_object",
            tool_args={"confirm_destructive": True},   # as mutated by executor
            description="store",
            risk_tier=RiskTier.DESTRUCTIVE,
        )
        sanitized = runtime._sanitize_plan_for_recipe([step])
        assert sanitized[0]["tool_args"]["confirm_destructive"] is False
        assert "status" not in sanitized[0]

    @pytest.mark.asyncio
    async def test_corrupt_recipe_falls_back_to_planner(self, tmp_path):
        registry = _registry_with_showfile(["show_a"], [])
        runtime = AgentRuntime(
            tool_registry=registry, memory_db_path=str(tmp_path / "wm.db")
        )
        runtime.memory.store_recipe(
            name="list all groups", steps=[{"bogus": True}], tags=["discover"]
        )
        trace = await runtime.run("list all groups")
        assert trace.result == "success"   # planner fallback executed
