"""Tests for src/agent/verification.py — post-mutation verification."""

import json

import pytest

from src.agent.state import PlanStep, RollbackStrategy, RunContext
from src.agent.verification import Verifier
from src.vocab import RiskTier


async def _mock_get_location(**kwargs):
    return json.dumps({
        "parsed_prompt": {"location": "Group 1"},
        "success": True,
    })


async def _mock_query_list(**kwargs):
    return json.dumps({
        "entries": [{"object_id": "1", "name": "Front Wash"}],
        "raw_response": "Group 1 Front Wash",
    })


async def _mock_query_list_empty(**kwargs):
    return json.dumps({
        "entries": [],
        "raw_response": "NO OBJECTS FOUND FOR LIST",
    })


async def _mock_get_info(**kwargs):
    return json.dumps({
        "label": "Front Wash",
        "raw_response": "Label=Front Wash",
    })


async def _mock_raise(**kwargs):
    raise ConnectionError("timeout")


def _make_step(tool_name, tool_args=None):
    return PlanStep(
        tool_name=tool_name,
        tool_args=tool_args or {},
        description=f"test {tool_name}",
        risk_tier=RiskTier.DESTRUCTIVE,
    )


@pytest.mark.asyncio
class TestVerifier:
    async def test_preflight_snapshot(self):
        verifier = Verifier(tool_dispatch={"get_console_location": _mock_get_location})
        step = _make_step("create_fixture_group", {"group_id": 1})
        ctx = RunContext(goal="test", plan=[step])
        checkpoint = await verifier.preflight_snapshot(step, ctx)
        assert checkpoint.console_location == "Group 1"
        assert checkpoint.step_id == step.id

    async def test_preflight_snapshot_no_tool(self):
        verifier = Verifier(tool_dispatch={})
        step = _make_step("test")
        ctx = RunContext(goal="test", plan=[step])
        checkpoint = await verifier.preflight_snapshot(step, ctx)
        assert checkpoint.console_location == "unknown"

    async def test_verify_create_group(self):
        verifier = Verifier(tool_dispatch={"query_object_list": _mock_query_list})
        step = _make_step("create_fixture_group", {"group_id": 1})
        ctx = RunContext(goal="test", plan=[step])
        result = await verifier.verify_step(step, ctx)
        assert result.passed is True

    async def test_verify_delete_success(self):
        verifier = Verifier(tool_dispatch={"query_object_list": _mock_query_list_empty})
        step = _make_step("delete_object", {"object_id": 1})
        ctx = RunContext(goal="test", plan=[step])
        result = await verifier.verify_step(step, ctx)
        assert result.passed is True

    async def test_verify_no_strategy(self):
        verifier = Verifier()
        step = _make_step("some_unknown_tool")
        ctx = RunContext(goal="test", plan=[step])
        result = await verifier.verify_step(step, ctx)
        assert result.passed is True  # assumed OK
        assert "No verification strategy" in result.details

    async def test_verify_tool_not_available(self):
        verifier = Verifier(tool_dispatch={})
        step = _make_step("create_fixture_group", {"group_id": 1})
        ctx = RunContext(goal="test", plan=[step])
        result = await verifier.verify_step(step, ctx)
        assert result.passed is True
        assert "not available" in result.details

    async def test_verify_exception(self):
        verifier = Verifier(tool_dispatch={"query_object_list": _mock_raise})
        step = _make_step("create_fixture_group", {"group_id": 1})
        ctx = RunContext(goal="test", plan=[step])
        result = await verifier.verify_step(step, ctx)
        assert result.passed is False

    async def test_suggest_rollback_oops(self):
        verifier = Verifier()
        step = _make_step("create_fixture_group")
        assert verifier.suggest_rollback(step) == RollbackStrategy.OOPS

    async def test_suggest_rollback_delete(self):
        verifier = Verifier()
        step = _make_step("patch_fixture")
        assert verifier.suggest_rollback(step) == RollbackStrategy.DELETE

    async def test_suggest_rollback_none(self):
        verifier = Verifier()
        step = _make_step("navigate_console")
        assert verifier.suggest_rollback(step) == RollbackStrategy.NONE

    async def test_has_strategy(self):
        verifier = Verifier()
        assert verifier.has_strategy("create_fixture_group") is True
        assert verifier.has_strategy("navigate_console") is False
