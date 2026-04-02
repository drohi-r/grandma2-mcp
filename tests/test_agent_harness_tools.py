import json
from unittest.mock import patch

import pytest


class _FakeTrace:
    def __init__(self, payload: dict):
        self._payload = payload

    def to_json(self) -> str:
        return json.dumps(self._payload, indent=2)


class _FakeRuntime:
    last_init_registry = None
    last_run_goal = None
    last_run_on_confirm = None
    last_plan_goal = None

    def __init__(self, tool_registry, **kwargs):
        type(self).last_init_registry = tool_registry

    async def run(self, goal: str, on_confirm=None):
        type(self).last_run_goal = goal
        type(self).last_run_on_confirm = on_confirm
        confirmed = None
        if on_confirm is not None:
            confirmed = await on_confirm(object())
        return _FakeTrace(
            {
                "goal": goal,
                "confirmed": confirmed,
                "used_confirmation_callback": on_confirm is not None,
            }
        )

    async def plan_only(self, goal: str):
        type(self).last_plan_goal = goal
        return (
            type("ParsedGoal", (), {"intent": type("Intent", (), {"value": "discover"})(), "confidence": 0.9, "object_type": None})(),
            [],
            [],
        )


@pytest.mark.asyncio
class TestAgentHarnessTools:
    async def test_published_entrypoints_registered_on_mcp(self):
        from src.server import mcp

        registry = getattr(mcp._tool_manager, "_tools", {})

        for tool_name in ("plan_agent_goal", "run_agent_goal", "decompose_task", "run_task"):
            assert tool_name in registry

    @patch("src.agent.runtime.AgentRuntime", _FakeRuntime)
    async def test_run_agent_goal_without_auto_confirm_passes_no_callback(self):
        from src.server import run_agent_goal

        result = json.loads(await run_agent_goal("Patch 1 fixture", auto_confirm=False))

        assert result["goal"] == "Patch 1 fixture"
        assert result["used_confirmation_callback"] is False
        assert _FakeRuntime.last_run_on_confirm is None

    @patch("src.agent.runtime.AgentRuntime", _FakeRuntime)
    async def test_run_agent_goal_with_auto_confirm_passes_callback(self):
        from src.server import run_agent_goal

        result = json.loads(await run_agent_goal("Patch 1 fixture", auto_confirm=True))

        assert result["goal"] == "Patch 1 fixture"
        assert result["used_confirmation_callback"] is True
        assert result["confirmed"] is True
        assert _FakeRuntime.last_run_on_confirm is not None

    @pytest.mark.asyncio
    async def test_run_agent_goal_requires_system_admin_scope(self, monkeypatch):
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        monkeypatch.setenv("GMA_SCOPE", "tier:4")

        from src.server import run_agent_goal

        result = json.loads(await run_agent_goal("List all groups"))

        assert result["blocked"] is True
        assert result["scope_required"] == "gma2:system:admin"

    @pytest.mark.asyncio
    async def test_plan_agent_goal_requires_discover_scope(self, monkeypatch):
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        monkeypatch.setenv("GMA_SCOPE", "")

        from src.server import plan_agent_goal

        result = json.loads(await plan_agent_goal("List all groups"))

        assert result["blocked"] is True
        assert result["scope_required"] == "gma2:discover"

    @patch("src.agent.runtime.AgentRuntime", _FakeRuntime)
    async def test_plan_agent_goal_allows_discover_scope(self, monkeypatch):
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        monkeypatch.setenv("GMA_SCOPE", "gma2:discover")

        from src.server import plan_agent_goal

        result = json.loads(await plan_agent_goal("List all groups"))

        assert result["goal"] == "List all groups"
        assert result["intent"] == "discover"
