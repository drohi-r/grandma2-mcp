"""
agent_bridge.py — Adapters between the orchestrator's SubTask model and the
agent harness's PlanStep model.

The two subsystems use different vocabulary for the same concept (one atomic
unit of console work), so these pure converters let them interoperate without
coupling their internals.

Conversion rules
----------------
SubTask → PlanStep
  tool_name   = subtask.mcp_tools[0] if mcp_tools else "noop"
  tool_args   = subtask.inputs
  description = subtask.description
  risk_tier   = subtask.allowed_risk
  depends_on  = subtask.depends_on

PlanStep → SubTask
  name        = planstep.id (UUID string)
  agent_role  = "BridgedAgent"
  description = planstep.description
  allowed_risk = planstep.risk_tier
  mcp_tools   = [planstep.tool_name]
  inputs      = planstep.tool_args
  confirmed   = False  (DESTRUCTIVE steps must be re-confirmed on the SubTask side)
  depends_on  = planstep.depends_on
"""

from __future__ import annotations

from src.agent.state import PlanStep, StepStatus
from src.task_decomposer import SubTask
from src.vocab import RiskTier


def subtask_to_planstep(subtask: SubTask) -> PlanStep:
    """Convert an orchestrator SubTask to an agent-harness PlanStep.

    If ``mcp_tools`` is empty the step is mapped to tool name ``"noop"`` so the
    agent executor can handle it gracefully without crashing.
    """
    tool_name = subtask.mcp_tools[0] if subtask.mcp_tools else "noop"
    return PlanStep(
        tool_name=tool_name,
        tool_args=dict(subtask.inputs),
        description=subtask.description,
        risk_tier=subtask.allowed_risk,
        depends_on=list(subtask.depends_on),
    )


def planstep_to_subtask(planstep: PlanStep) -> SubTask:
    """Convert an agent-harness PlanStep to an orchestrator SubTask.

    Notes
    -----
    - ``confirmed`` is always ``False``: DESTRUCTIVE steps must be explicitly
      re-confirmed by the orchestrator before execution.
    - ``agent_role`` is set to ``"BridgedAgent"`` as a sentinel so callers can
      detect bridged steps if needed.
    - ``status``, ``result``, ``error``, and timing fields on the PlanStep are
      intentionally dropped; they are execution-state that the SubTask model
      does not carry.
    """
    return SubTask(
        name=planstep.id,
        agent_role="BridgedAgent",
        description=planstep.description,
        allowed_risk=planstep.risk_tier,
        mcp_tools=[planstep.tool_name],
        inputs=dict(planstep.tool_args),
        depends_on=list(planstep.depends_on),
        confirmed=False,
    )


def plansteps_from_subtasks(subtasks: list[SubTask]) -> list[PlanStep]:
    """Bulk convert an ordered SubTask list to PlanSteps."""
    return [subtask_to_planstep(st) for st in subtasks]


def subtasks_from_plansteps(plansteps: list[PlanStep]) -> list[SubTask]:
    """Bulk convert a PlanStep list to SubTasks."""
    return [planstep_to_subtask(ps) for ps in plansteps]
