"""Tests for src/agent/executor.py — step execution with mocked tools."""

import json

import pytest

from src.agent.executor import StepExecutor
from src.agent.policy import PolicyEngine
from src.agent.state import PlanStep, RunContext, RunStatus, StepStatus
from src.agent.verification import Verifier
from src.vocab import RiskTier


# Mock tool functions
async def _mock_success(**kwargs) -> str:
    return json.dumps({"ok": True, "data": "mock result"})


async def _mock_error(**kwargs) -> str:
    return json.dumps({"error": "something went wrong", "blocked": True})


async def _mock_raise(**kwargs) -> str:
    raise ConnectionError("connection lost")


def _make_executor(tools=None, max_retries=0):
    if tools is None:
        tools = {"mock_tool": _mock_success}
    policy = PolicyEngine()
    verifier = Verifier(tool_dispatch={})
    return StepExecutor(
        tool_registry=tools,
        policy=policy,
        verifier=verifier,
        max_retries=max_retries,
    )


def _make_step(tool_name="mock_tool", risk=RiskTier.SAFE_READ, depends_on=None):
    return PlanStep(
        tool_name=tool_name,
        tool_args={},
        description=f"test {tool_name}",
        risk_tier=risk,
        depends_on=depends_on or [],
    )


@pytest.mark.asyncio
class TestStepExecutor:
    async def test_execute_single_success(self):
        executor = _make_executor()
        step = _make_step()
        ctx = RunContext(goal="test", plan=[step])
        result = await executor.execute_plan(ctx)
        assert result.status == RunStatus.COMPLETED
        assert step.status == StepStatus.COMPLETED
        assert step.result is not None

    async def test_execute_multiple_steps(self):
        executor = _make_executor()
        s1 = _make_step()
        s2 = _make_step()
        ctx = RunContext(goal="test", plan=[s1, s2])
        result = await executor.execute_plan(ctx)
        assert result.status == RunStatus.COMPLETED
        assert s1.status == StepStatus.COMPLETED
        assert s2.status == StepStatus.COMPLETED

    async def test_execute_with_error_response(self):
        executor = _make_executor(
            tools={"mock_tool": _mock_error}, max_retries=0
        )
        step = _make_step()
        ctx = RunContext(goal="test", plan=[step])
        result = await executor.execute_plan(ctx)
        assert result.status == RunStatus.FAILED
        assert step.status == StepStatus.FAILED

    async def test_execute_with_exception(self):
        executor = _make_executor(
            tools={"mock_tool": _mock_raise}, max_retries=0
        )
        step = _make_step()
        ctx = RunContext(goal="test", plan=[step])
        result = await executor.execute_plan(ctx)
        assert result.status == RunStatus.FAILED
        assert step.status == StepStatus.FAILED
        assert "connection lost" in step.error

    async def test_unknown_tool_fails(self):
        executor = _make_executor(tools={})
        step = _make_step(tool_name="nonexistent")
        ctx = RunContext(goal="test", plan=[step])
        await executor.execute_plan(ctx)
        assert step.status == StepStatus.FAILED

    async def test_skip_dependents_on_failure(self):
        executor = _make_executor(
            tools={"fail_tool": _mock_raise, "mock_tool": _mock_success},
            max_retries=0,
        )
        s1 = _make_step(tool_name="fail_tool")
        s2 = _make_step(depends_on=[s1.id])
        ctx = RunContext(goal="test", plan=[s1, s2])
        await executor.execute_plan(ctx)
        assert s1.status == StepStatus.FAILED
        assert s2.status == StepStatus.SKIPPED

    async def test_destructive_step_auto_confirmed(self):
        """Destructive steps are auto-confirmed when no callback provided."""
        executor = _make_executor()
        step = _make_step(risk=RiskTier.DESTRUCTIVE)
        step.tool_args["confirm_destructive"] = False
        ctx = RunContext(goal="test", plan=[step])
        await executor.execute_plan(ctx)
        assert step.status == StepStatus.COMPLETED
        assert step.tool_args["confirm_destructive"] is True

    async def test_destructive_step_with_callback_confirm(self):
        executor = _make_executor()
        step = _make_step(risk=RiskTier.DESTRUCTIVE)
        step.tool_args["confirm_destructive"] = False

        async def confirm(s):
            return True

        ctx = RunContext(goal="test", plan=[step])
        await executor.execute_plan(ctx, on_confirm=confirm)
        assert step.status == StepStatus.COMPLETED

    async def test_destructive_step_with_callback_decline(self):
        executor = _make_executor()
        step = _make_step(risk=RiskTier.DESTRUCTIVE)
        step.tool_args["confirm_destructive"] = False

        async def decline(s):
            return False

        ctx = RunContext(goal="test", plan=[step])
        result = await executor.execute_plan(ctx, on_confirm=decline)
        assert step.status == StepStatus.SKIPPED
        assert result.status == RunStatus.ABORTED

    async def test_retry_logic(self):
        call_count = 0

        async def flaky_tool(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("flaky")
            return json.dumps({"ok": True})

        executor = _make_executor(
            tools={"mock_tool": flaky_tool}, max_retries=2
        )
        step = _make_step()
        ctx = RunContext(goal="test", plan=[step])
        await executor.execute_plan(ctx)
        assert step.status == StepStatus.COMPLETED
        assert step.retry_count == 2
        assert call_count == 3

    async def test_retry_exhausted(self):
        async def always_fail(**kwargs):
            raise ConnectionError("permanent failure")

        executor = _make_executor(
            tools={"mock_tool": always_fail}, max_retries=1
        )
        step = _make_step()
        ctx = RunContext(goal="test", plan=[step])
        await executor.execute_plan(ctx)
        assert step.status == StepStatus.FAILED
        assert step.retry_count == 2  # initial + 1 retry

    async def test_transitive_dependency_skip(self):
        executor = _make_executor(
            tools={"fail_tool": _mock_raise, "mock_tool": _mock_success},
            max_retries=0,
        )
        s1 = _make_step(tool_name="fail_tool")
        s2 = _make_step(depends_on=[s1.id])
        s3 = _make_step(depends_on=[s2.id])
        ctx = RunContext(goal="test", plan=[s1, s2, s3])
        await executor.execute_plan(ctx)
        assert s1.status == StepStatus.FAILED
        assert s2.status == StepStatus.SKIPPED
        assert s3.status == StepStatus.SKIPPED
