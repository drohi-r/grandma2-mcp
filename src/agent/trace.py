"""Execution trace — structured JSON artifacts for auditability.

Produces a complete record of what the agent did: goal, plan, each step
with its tool call and result, final outcome, and timing.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.agent.state import PlanStep, RunContext, RunStatus, StepStatus

logger = logging.getLogger(__name__)

TRACES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "agent_traces")


@dataclass
class StepRecord:
    """One executed step in the trace."""

    step_id: str
    tool_name: str
    tool_args: dict[str, Any]
    status: str
    risk_tier: str
    result_summary: str
    verification: dict[str, Any] | None
    duration_ms: int
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "status": self.status,
            "risk_tier": self.risk_tier,
            "result_summary": self.result_summary,
            "verification": self.verification,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionTrace:
    """Complete record of an agent run."""

    run_id: str
    goal: str
    plan: list[dict[str, Any]]
    steps: list[StepRecord]
    result: str
    started_at: str
    completed_at: str
    policy_warnings: list[str] = field(default_factory=list)
    total_duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "plan": self.plan,
            "steps": [s.to_dict() for s in self.steps],
            "result": self.result,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "policy_warnings": self.policy_warnings,
            "total_duration_ms": self.total_duration_ms,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_file(self, path: str | None = None) -> str:
        """Write trace to a JSON file. Returns the file path used."""
        if path is None:
            os.makedirs(TRACES_DIR, exist_ok=True)
            path = os.path.join(TRACES_DIR, f"{self.run_id}.json")
        with open(path, "w") as f:
            f.write(self.to_json())
        logger.info("Trace written to %s", path)
        return path


def _truncate(text: str | None, max_len: int = 500) -> str:
    """Truncate tool result for trace readability."""
    if text is None:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "...(truncated)"


def _step_duration_ms(step: PlanStep) -> int:
    """Calculate step duration in milliseconds."""
    if step.started_at and step.completed_at:
        delta = step.completed_at - step.started_at
        return int(delta.total_seconds() * 1000)
    return 0


def build_step_record(step: PlanStep) -> StepRecord:
    """Convert a completed PlanStep into a StepRecord for the trace."""
    return StepRecord(
        step_id=step.id,
        tool_name=step.tool_name,
        tool_args=step.tool_args,
        status=step.status.value,
        risk_tier=step.risk_tier.value,
        result_summary=_truncate(step.result),
        verification=step.verification.to_dict() if step.verification else None,
        duration_ms=_step_duration_ms(step),
        timestamp=step.started_at.isoformat() if step.started_at else "",
    )


def _determine_result(context: RunContext) -> str:
    """Determine the overall result string from the run context."""
    if context.status == RunStatus.ABORTED:
        return "aborted"
    failed = context.failed_steps()
    completed = context.completed_steps()
    if not failed:
        return "success"
    if completed:
        return "partial_failure"
    return "failure"


def build_trace(
    context: RunContext,
    started_at: datetime,
    policy_warnings: list[str] | None = None,
) -> ExecutionTrace:
    """Build a complete ExecutionTrace from a finished RunContext."""
    completed_at = datetime.now(UTC)
    total_ms = int((completed_at - started_at).total_seconds() * 1000)

    plan_summary = [
        {
            "step": s.description,
            "tool": s.tool_name,
            "risk": s.risk_tier.value,
        }
        for s in context.plan
    ]

    step_records = []
    for step in context.plan:
        if step.status != StepStatus.PENDING:
            step_records.append(build_step_record(step))

    return ExecutionTrace(
        run_id=context.run_id,
        goal=context.goal,
        plan=plan_summary,
        steps=step_records,
        result=_determine_result(context),
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        policy_warnings=policy_warnings or [],
        total_duration_ms=total_ms,
    )
