"""Tests for src/agent/state.py — data models and state transitions."""

from datetime import UTC, datetime

from src.agent.state import (
    Checkpoint,
    GoalIntent,
    ParsedGoal,
    PlanStep,
    RollbackStrategy,
    RunContext,
    RunStatus,
    StepStatus,
    VerificationResult,
)
from src.vocab import RiskTier


class TestStepStatus:
    def test_enum_values(self):
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.COMPLETED == "completed"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.SKIPPED == "skipped"
        assert StepStatus.AWAITING_CONFIRMATION == "awaiting_confirmation"


class TestRunStatus:
    def test_enum_values(self):
        assert RunStatus.PLANNED == "planned"
        assert RunStatus.EXECUTING == "executing"
        assert RunStatus.PAUSED == "paused"
        assert RunStatus.COMPLETED == "completed"
        assert RunStatus.FAILED == "failed"
        assert RunStatus.ABORTED == "aborted"


class TestGoalIntent:
    def test_enum_values(self):
        assert GoalIntent.PATCH == "patch"
        assert GoalIntent.PRESET == "preset"
        assert GoalIntent.PLAYBACK == "playback"
        assert GoalIntent.DISCOVER == "discover"
        assert GoalIntent.COMPOSITE == "composite"


class TestPlanStep:
    def test_create_with_defaults(self):
        step = PlanStep(
            tool_name="list_fixture_types",
            tool_args={},
            description="List fixtures",
            risk_tier=RiskTier.SAFE_READ,
        )
        assert step.status == StepStatus.PENDING
        assert step.result is None
        assert step.error is None
        assert step.retry_count == 0
        assert step.depends_on == []
        assert step.id  # UUID generated

    def test_to_dict(self):
        step = PlanStep(
            tool_name="create_fixture_group",
            tool_args={"group_id": 1, "start": 1, "end": 12},
            description="Create group 1",
            risk_tier=RiskTier.DESTRUCTIVE,
        )
        d = step.to_dict()
        assert d["tool_name"] == "create_fixture_group"
        assert d["risk_tier"] == "DESTRUCTIVE"
        assert d["status"] == "pending"
        assert d["tool_args"]["group_id"] == 1

    def test_to_dict_with_completed_timestamps(self):
        now = datetime.now(UTC)
        step = PlanStep(
            tool_name="test",
            tool_args={},
            description="test step",
            risk_tier=RiskTier.SAFE_READ,
            started_at=now,
            completed_at=now,
            status=StepStatus.COMPLETED,
        )
        d = step.to_dict()
        assert d["started_at"] is not None
        assert d["completed_at"] is not None

    def test_unique_ids(self):
        s1 = PlanStep(
            tool_name="a", tool_args={}, description="a", risk_tier=RiskTier.SAFE_READ
        )
        s2 = PlanStep(
            tool_name="b", tool_args={}, description="b", risk_tier=RiskTier.SAFE_READ
        )
        assert s1.id != s2.id


class TestVerificationResult:
    def test_to_dict(self):
        vr = VerificationResult(
            step_id="abc",
            passed=True,
            expected={"object_id": 1},
            actual={"raw_response_snippet": "OK"},
            details="Verified",
        )
        d = vr.to_dict()
        assert d["passed"] is True
        assert d["step_id"] == "abc"


class TestCheckpoint:
    def test_to_dict(self):
        cp = Checkpoint(
            step_id="xyz",
            timestamp=datetime(2026, 3, 12, tzinfo=UTC),
            console_location="Group 1",
            snapshot_data={"entries": 5},
        )
        d = cp.to_dict()
        assert d["step_id"] == "xyz"
        assert d["console_location"] == "Group 1"


class TestParsedGoal:
    def test_defaults(self):
        pg = ParsedGoal(raw="test", intent=GoalIntent.DISCOVER)
        assert pg.object_type is None
        assert pg.count is None
        assert pg.names == []
        assert pg.confidence == 1.0


class TestRunContext:
    def _make_step(self, status=StepStatus.PENDING):
        s = PlanStep(
            tool_name="test",
            tool_args={},
            description="test",
            risk_tier=RiskTier.SAFE_READ,
        )
        s.status = status
        return s

    def test_create_defaults(self):
        ctx = RunContext(goal="test goal", plan=[])
        assert ctx.status == RunStatus.PLANNED
        assert ctx.current_step_index == 0
        assert ctx.run_id.startswith("run_")
        assert ctx.checkpoints == []

    def test_current_step(self):
        s1 = self._make_step()
        s2 = self._make_step()
        ctx = RunContext(goal="test", plan=[s1, s2])
        assert ctx.current_step() is s1
        ctx.advance()
        assert ctx.current_step() is s2
        ctx.advance()
        assert ctx.current_step() is None

    def test_completed_and_failed_steps(self):
        s1 = self._make_step(StepStatus.COMPLETED)
        s2 = self._make_step(StepStatus.FAILED)
        s3 = self._make_step(StepStatus.PENDING)
        ctx = RunContext(goal="test", plan=[s1, s2, s3])
        assert len(ctx.completed_steps()) == 1
        assert len(ctx.failed_steps()) == 1

    def test_to_dict(self):
        s = self._make_step()
        ctx = RunContext(goal="test", plan=[s])
        d = ctx.to_dict()
        assert d["goal"] == "test"
        assert d["status"] == "planned"
        assert len(d["plan"]) == 1


class TestRollbackStrategy:
    def test_enum_values(self):
        assert RollbackStrategy.OOPS == "oops"
        assert RollbackStrategy.DELETE == "delete"
        assert RollbackStrategy.NONE == "none"
