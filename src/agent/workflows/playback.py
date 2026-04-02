"""Playback workflow template — sequence creation + executor assignment.

Canonical ordering:
1. Create/store sequence with cues
2. Assign sequence to executor
3. Label executor
4. Verify assignment
5. Optionally go (start playback)
"""

from __future__ import annotations

from src.agent.state import ParsedGoal, PlanStep
from src.agent.workflows.common import build_label_step, build_verify_step
from src.vocab import RiskTier


def build_playback_workflow(goal: ParsedGoal) -> list[PlanStep]:
    """Build a sequence/executor assignment workflow from a parsed goal.

    Args:
        goal: Parsed goal with options including:
            - sequence_id: target sequence number
            - executor_id: target executor number
            - page: executor page (default 1)
            - cue_count: number of cues to create
            - auto_go: whether to trigger playback after assignment

    Returns:
        Ordered list of PlanSteps with dependency edges.
    """
    steps: list[PlanStep] = []

    sequence_id = goal.options.get("sequence_id", 1)
    executor_id = goal.options.get("executor_id", 1)
    page = goal.options.get("page", 1)
    cue_count = goal.options.get("cue_count", 1)
    auto_go = goal.options.get("auto_go", False)

    # Step 1: List existing sequences (discovery)
    discover = PlanStep(
        tool_name="query_object_list",
        tool_args={"object_type": "sequence"},
        description="List existing sequences",
        risk_tier=RiskTier.SAFE_READ,
    )
    steps.append(discover)

    # Step 2: Store cues into the sequence
    prev_id = discover.id
    for cue_num in range(1, cue_count + 1):
        store_cue = PlanStep(
            tool_name="store_current_cue",
            tool_args={
                "sequence_id": sequence_id,
                "cue_id": cue_num,
                "confirm_destructive": False,
            },
            description=f"Store cue {cue_num} in sequence {sequence_id}",
            risk_tier=RiskTier.DESTRUCTIVE,
            depends_on=[prev_id],
        )
        steps.append(store_cue)
        prev_id = store_cue.id

    # Step 3: Assign sequence to executor
    assign = PlanStep(
        tool_name="assign_object",
        tool_args={
            "source": f"sequence {sequence_id}",
            "target": f"executor {page}.{executor_id}",
            "confirm_destructive": False,
        },
        description=f"Assign sequence {sequence_id} to executor {page}.{executor_id}",
        risk_tier=RiskTier.DESTRUCTIVE,
        depends_on=[prev_id],
    )
    steps.append(assign)

    # Step 4: Label executor (if name provided)
    if goal.names:
        label = build_label_step(
            "executor", f"{page}.{executor_id}", goal.names[0],
            depends_on=[assign.id],
        )
        steps.append(label)

    # Step 5: Verify assignment
    verify = build_verify_step(
        "get_executor_status",
        f"Verify executor {page}.{executor_id} has sequence {sequence_id}",
        tool_args={"executor_id": executor_id, "page": page},
        depends_on=[steps[-1].id],
    )
    steps.append(verify)

    # Step 6: Optional go
    if auto_go:
        go_step = PlanStep(
            tool_name="execute_sequence",
            tool_args={
                "action": "go",
                "executor_id": executor_id,
            },
            description=f"Start playback on executor {executor_id}",
            risk_tier=RiskTier.SAFE_WRITE,
            depends_on=[verify.id],
        )
        steps.append(go_step)

    return steps
