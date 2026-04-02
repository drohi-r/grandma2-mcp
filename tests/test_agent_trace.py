"""Tests for src/agent/trace.py — execution trace building and serialization."""

import json
import os
import tempfile
from datetime import UTC, datetime

from src.agent.state import PlanStep, RunContext, RunStatus, StepStatus, VerificationResult
from src.agent.trace import (
    ExecutionTrace,
    StepRecord,
    build_step_record,
    build_trace,
)
from src.vocab import RiskTier


class TestStepRecord:
    def test_to_dict(self):
        sr = StepRecord(
            step_id="abc",
            tool_name="list_fixture_types",
            tool_args={},
            status="completed",
            risk_tier="SAFE_READ",
            result_summary="OK",
            verification=None,
            duration_ms=150,
            timestamp="2026-03-12T00:00:00+00:00",
        )
        d = sr.to_dict()
        assert d["tool_name"] == "list_fixture_types"
        assert d["duration_ms"] == 150
        assert d["verification"] is None


class TestExecutionTrace:
    def _make_trace(self):
        return ExecutionTrace(
            run_id="run_test123",
            goal="List all groups",
            plan=[{"step": "List groups", "tool": "query_object_list", "risk": "SAFE_READ"}],
            steps=[
                StepRecord(
                    step_id="s1",
                    tool_name="query_object_list",
                    tool_args={"object_type": "group"},
                    status="completed",
                    risk_tier="SAFE_READ",
                    result_summary="5 groups found",
                    verification=None,
                    duration_ms=200,
                    timestamp="2026-03-12T00:00:00+00:00",
                )
            ],
            result="success",
            started_at="2026-03-12T00:00:00+00:00",
            completed_at="2026-03-12T00:00:01+00:00",
            total_duration_ms=1000,
        )

    def test_to_dict(self):
        trace = self._make_trace()
        d = trace.to_dict()
        assert d["run_id"] == "run_test123"
        assert d["result"] == "success"
        assert len(d["steps"]) == 1
        assert d["total_duration_ms"] == 1000

    def test_to_json(self):
        trace = self._make_trace()
        j = trace.to_json()
        data = json.loads(j)
        assert data["goal"] == "List all groups"

    def test_to_file(self):
        trace = self._make_trace()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_trace.json")
            result_path = trace.to_file(path)
            assert os.path.exists(result_path)
            with open(result_path) as f:
                data = json.loads(f.read())
            assert data["run_id"] == "run_test123"


class TestBuildStepRecord:
    def test_from_completed_step(self):
        now = datetime.now(UTC)
        step = PlanStep(
            tool_name="create_fixture_group",
            tool_args={"group_id": 1},
            description="Create group 1",
            risk_tier=RiskTier.DESTRUCTIVE,
            status=StepStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            result='{"ok": true}',
        )
        sr = build_step_record(step)
        assert sr.tool_name == "create_fixture_group"
        assert sr.status == "completed"
        assert sr.risk_tier == "DESTRUCTIVE"

    def test_from_failed_step(self):
        step = PlanStep(
            tool_name="patch_fixture",
            tool_args={},
            description="Patch fixture",
            risk_tier=RiskTier.DESTRUCTIVE,
            status=StepStatus.FAILED,
            error="Connection lost",
        )
        sr = build_step_record(step)
        assert sr.status == "failed"
        assert sr.duration_ms == 0  # no timestamps

    def test_with_verification(self):
        now = datetime.now(UTC)
        vr = VerificationResult(
            step_id="s1", passed=True, expected={}, actual={}, details="OK"
        )
        step = PlanStep(
            tool_name="store_object",
            tool_args={},
            description="Store",
            risk_tier=RiskTier.DESTRUCTIVE,
            status=StepStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            verification=vr,
        )
        sr = build_step_record(step)
        assert sr.verification is not None
        assert sr.verification["passed"] is True


class TestBuildTrace:
    def test_success_trace(self):
        step = PlanStep(
            tool_name="query_object_list",
            tool_args={},
            description="List groups",
            risk_tier=RiskTier.SAFE_READ,
            status=StepStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        ctx = RunContext(goal="List groups", plan=[step], status=RunStatus.COMPLETED)
        started = datetime.now(UTC)
        trace = build_trace(ctx, started)
        assert trace.result == "success"
        assert len(trace.steps) == 1

    def test_failure_trace(self):
        step = PlanStep(
            tool_name="patch_fixture",
            tool_args={},
            description="Patch",
            risk_tier=RiskTier.DESTRUCTIVE,
            status=StepStatus.FAILED,
            error="timeout",
        )
        ctx = RunContext(goal="Patch", plan=[step], status=RunStatus.FAILED)
        started = datetime.now(UTC)
        trace = build_trace(ctx, started)
        assert trace.result == "failure"

    def test_partial_failure_trace(self):
        s1 = PlanStep(
            tool_name="a", tool_args={}, description="a",
            risk_tier=RiskTier.SAFE_READ, status=StepStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        s2 = PlanStep(
            tool_name="b", tool_args={}, description="b",
            risk_tier=RiskTier.DESTRUCTIVE, status=StepStatus.FAILED,
        )
        ctx = RunContext(goal="test", plan=[s1, s2], status=RunStatus.FAILED)
        started = datetime.now(UTC)
        trace = build_trace(ctx, started)
        assert trace.result == "partial_failure"

    def test_aborted_trace(self):
        ctx = RunContext(goal="test", plan=[], status=RunStatus.ABORTED)
        started = datetime.now(UTC)
        trace = build_trace(ctx, started)
        assert trace.result == "aborted"

    def test_with_policy_warnings(self):
        ctx = RunContext(goal="test", plan=[], status=RunStatus.COMPLETED)
        started = datetime.now(UTC)
        trace = build_trace(ctx, started, policy_warnings=["warning 1"])
        assert trace.policy_warnings == ["warning 1"]
