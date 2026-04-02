"""Agent harness for grandMA2 MCP server.

Provides the runtime layer that turns high-level goals into executed
multi-step plans with verification, policy enforcement, and audit traces.

Public API:
    AgentRuntime — top-level orchestrator
    DomainPlanner — rule-based goal → plan decomposition
    StepExecutor — step-by-step tool dispatch with retries
    PolicyEngine — plan-level governance
    Verifier — post-mutation state verification
    WorkflowMemory — SQLite-backed operational memory

Data models:
    RunContext, PlanStep, Checkpoint, ParsedGoal
    ExecutionTrace, StepRecord
    StepStatus, RunStatus, GoalIntent
"""

from src.agent.executor import StepExecutor
from src.agent.memory import WorkflowMemory
from src.agent.planner import DomainPlanner
from src.agent.policy import PolicyEngine
from src.agent.runtime import AgentRuntime
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
from src.agent.trace import ExecutionTrace, StepRecord
from src.agent.verification import Verifier

__all__ = [
    "AgentRuntime",
    "Checkpoint",
    "DomainPlanner",
    "ExecutionTrace",
    "GoalIntent",
    "ParsedGoal",
    "PlanStep",
    "PolicyEngine",
    "RollbackStrategy",
    "RunContext",
    "RunStatus",
    "StepExecutor",
    "StepRecord",
    "StepStatus",
    "VerificationResult",
    "Verifier",
    "WorkflowMemory",
]
