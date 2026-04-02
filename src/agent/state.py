"""Agent harness state model — RunContext, PlanStep, Checkpoint.

These dataclasses track the full lifecycle of an agent run:
goal → plan (list of PlanSteps) → execution → completion.

No I/O — pure data structures used by the planner, executor, and policy engine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from src.vocab import RiskTier


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


class RunStatus(StrEnum):
    PLANNED = "planned"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class GoalIntent(StrEnum):
    PATCH = "patch"
    PRESET = "preset"
    PLAYBACK = "playback"
    LABEL = "label"
    DISCOVER = "discover"
    GROUP = "group"
    COMPOSITE = "composite"


@dataclass
class VerificationResult:
    """Outcome of a post-step verification check."""

    step_id: str
    passed: bool
    expected: dict[str, Any]
    actual: dict[str, Any]
    details: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
            "details": self.details,
        }


class RollbackStrategy(StrEnum):
    OOPS = "oops"
    DELETE = "delete"
    NONE = "none"


@dataclass
class PlanStep:
    """A single step in an agent execution plan."""

    tool_name: str
    tool_args: dict[str, Any]
    description: str
    risk_tier: RiskTier
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    depends_on: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    verification: VerificationResult | None = None
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "description": self.description,
            "risk_tier": self.risk_tier.value,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "verification": self.verification.to_dict() if self.verification else None,
            "retry_count": self.retry_count,
        }


@dataclass
class Checkpoint:
    """State snapshot taken before a mutation step."""

    step_id: str
    timestamp: datetime
    console_location: str
    snapshot_data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "timestamp": self.timestamp.isoformat(),
            "console_location": self.console_location,
            "snapshot_data": self.snapshot_data,
        }


@dataclass
class ParsedGoal:
    """Structured representation of a user's goal after keyword extraction."""

    raw: str
    intent: GoalIntent
    object_type: str | None = None
    count: int | None = None
    fixture_type: str | None = None
    names: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class RunContext:
    """Full state of an agent run."""

    goal: str
    plan: list[PlanStep]
    run_id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    current_step_index: int = 0
    status: RunStatus = RunStatus.PLANNED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    checkpoints: list[Checkpoint] = field(default_factory=list)
    confirmations_pending: list[str] = field(default_factory=list)

    def current_step(self) -> PlanStep | None:
        if 0 <= self.current_step_index < len(self.plan):
            return self.plan[self.current_step_index]
        return None

    def advance(self) -> None:
        self.current_step_index += 1
        self.updated_at = datetime.now(UTC)

    def completed_steps(self) -> list[PlanStep]:
        return [s for s in self.plan if s.status == StepStatus.COMPLETED]

    def failed_steps(self) -> list[PlanStep]:
        return [s for s in self.plan if s.status == StepStatus.FAILED]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "plan": [s.to_dict() for s in self.plan],
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
