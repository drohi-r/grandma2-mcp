"""Effect, chaser, and MAtricks workflow templates.

Rule-based plan builders for the live-programming domains the planner
previously routed to the discover fallback. Same conventions as the other
workflow modules: pure functions, ParsedGoal in, ordered PlanSteps out.
"""

from __future__ import annotations

import re

from src.agent.state import ParsedGoal, PlanStep
from src.agent.workflows.common import build_verify_step
from src.vocab import RiskTier

_EFFECT_ID_RE = re.compile(r"\beffect\s+(\d+)", re.IGNORECASE)
_EXECUTOR_ID_RE = re.compile(r"\bexec(?:utor)?\s+(\d+)", re.IGNORECASE)
_SEQUENCE_ID_RE = re.compile(r"\bsequence\s+(\d+)", re.IGNORECASE)
_GROUP_ID_RE = re.compile(r"\bgroup\s+(\d+)", re.IGNORECASE)
_INTERLEAVE_RE = re.compile(r"\binterleave\s+(\d+)", re.IGNORECASE)
_BLOCKS_RE = re.compile(r"\bblocks?\s+(\d+)(?:\.(\d+))?", re.IGNORECASE)
_WINGS_RE = re.compile(r"\bwings?\s+(\d+)", re.IGNORECASE)


def _build_selection_step(goal: ParsedGoal) -> PlanStep:
    """Select the target fixtures: group, explicit range, or whole rig
    in type order (the safe default for rig-wide effects)."""
    m = _GROUP_ID_RE.search(goal.raw)
    if m:
        return PlanStep(
            tool_name="select_fixtures_by_group",
            tool_args={"group_id": int(m.group(1))},
            description=f"Select fixtures from group {m.group(1)}",
            risk_tier=RiskTier.SAFE_WRITE,
        )
    start = goal.options.get("fixture_start")
    end = goal.options.get("fixture_end")
    if start is not None:
        return PlanStep(
            tool_name="modify_selection",
            tool_args={"action": "select", "start": start, "end": end or start},
            description=f"Select fixtures {start}-{end or start}",
            risk_tier=RiskTier.SAFE_WRITE,
        )
    return PlanStep(
        tool_name="select_fixtures_by_type_order",
        tool_args={"execute": True},
        description="Select the whole rig in fixture-type order",
        risk_tier=RiskTier.SAFE_WRITE,
    )


def build_effect_workflow(goal: ParsedGoal) -> list[PlanStep]:
    """Effect workflow: discover pool → select fixtures → assign to executor.

    Rule-based planning can wire an existing effect to fixtures/executors;
    designing new effect content stays with the operator (the discover step
    surfaces the library so the operator can pick).
    """
    steps: list[PlanStep] = []

    discover = PlanStep(
        tool_name="list_effects_pool",
        tool_args={},
        description="List the effect pool",
        risk_tier=RiskTier.SAFE_READ,
    )
    steps.append(discover)

    select = _build_selection_step(goal)
    select.depends_on.append(discover.id)
    steps.append(select)

    effect_m = _EFFECT_ID_RE.search(goal.raw)
    exec_m = _EXECUTOR_ID_RE.search(goal.raw)
    if effect_m and exec_m:
        assign = PlanStep(
            tool_name="assign_effect_to_executor",
            tool_args={
                "effect_id": int(effect_m.group(1)),
                "executor_id": int(exec_m.group(1)),
                "page": goal.options.get("page"),
                "confirm_destructive": False,
            },
            description=(
                f"Assign effect {effect_m.group(1)} to executor {exec_m.group(1)}"
            ),
            risk_tier=RiskTier.DESTRUCTIVE,
            depends_on=[select.id],
        )
        steps.append(assign)
        steps.append(build_verify_step(
            "list_effects_pool",
            "Verify effect pool state after assignment",
            tool_args={},
            depends_on=[assign.id],
        ))
    else:
        # No concrete effect/executor — surface the library details so the
        # operator (or a follow-up goal) can pick an effect to wire up.
        steps.append(build_verify_step(
            "browse_effect_library",
            "Browse the predefined effect library for candidates",
            tool_args={},
            depends_on=[select.id],
        ))
    return steps


def build_chaser_workflow(goal: ParsedGoal) -> list[PlanStep]:
    """Color-chaser workflow: select → (apply preset → store cue) × N →
    assign sequence to executor.

    Steps recall existing color presets (1..N) — preset content is assumed
    present (create_presets_for_patch covers that); each recalled look is
    stored as one cue of the chaser sequence.
    """
    steps: list[PlanStep] = []
    step_count = goal.count or 4
    seq_m = _SEQUENCE_ID_RE.search(goal.raw)
    sequence_id = int(seq_m.group(1)) if seq_m else goal.options.get("sequence_id", 90)
    exec_m = _EXECUTOR_ID_RE.search(goal.raw)

    select = _build_selection_step(goal)
    steps.append(select)

    prev_id = select.id
    for i in range(1, step_count + 1):
        recall = PlanStep(
            tool_name="apply_preset",
            tool_args={"preset_type": "color", "preset_id": i},
            description=f"Recall color preset {i} for chaser step {i}",
            risk_tier=RiskTier.SAFE_WRITE,
            depends_on=[prev_id],
        )
        steps.append(recall)
        store = PlanStep(
            tool_name="store_cue_with_timing",
            tool_args={
                "cue_id": i,
                "sequence_id": sequence_id,
                "cue_name": f"Chase {i}",
                "confirm_destructive": False,
            },
            description=f"Store chaser cue {i} into sequence {sequence_id}",
            risk_tier=RiskTier.DESTRUCTIVE,
            depends_on=[recall.id],
        )
        steps.append(store)
        prev_id = store.id

    if exec_m:
        assign = PlanStep(
            tool_name="assign_object",
            tool_args={
                "mode": "assign",
                "source_type": "Sequence",
                "source_id": sequence_id,
                "target_type": "Executor",
                "target_id": int(exec_m.group(1)),
                "confirm_destructive": False,
            },
            description=f"Assign sequence {sequence_id} to executor {exec_m.group(1)}",
            risk_tier=RiskTier.DESTRUCTIVE,
            depends_on=[prev_id],
        )
        steps.append(assign)
        prev_id = assign.id

    steps.append(build_verify_step(
        "query_object_list",
        f"Verify chaser sequence {sequence_id} exists",
        tool_args={"object_type": "sequence"},
        depends_on=[prev_id],
    ))
    return steps


def build_matricks_workflow(goal: ParsedGoal) -> list[PlanStep]:
    """MAtricks workflow: select fixtures → apply MAtricks → read back state."""
    steps: list[PlanStep] = []
    text = goal.raw

    select = _build_selection_step(goal)
    steps.append(select)

    tool_args: dict = {"action": "interleave", "value": 2}
    description = "Apply MAtricks interleave 2 (every other fixture)"
    if m := _INTERLEAVE_RE.search(text):
        tool_args = {"action": "interleave", "value": int(m.group(1))}
        description = f"Apply MAtricks interleave {m.group(1)}"
    elif m := _BLOCKS_RE.search(text):
        if m.group(2):
            tool_args = {"action": "blocks", "x": int(m.group(1)), "y": int(m.group(2))}
            description = f"Apply MAtricks blocks {m.group(1)}.{m.group(2)}"
        else:
            tool_args = {"action": "blocks", "value": int(m.group(1))}
            description = f"Apply MAtricks blocks {m.group(1)}"
    elif m := _WINGS_RE.search(text):
        tool_args = {"action": "wings", "value": int(m.group(1))}
        description = f"Apply MAtricks wings {m.group(1)}"
    elif re.search(r"\breset\b|\boff\b", text, re.IGNORECASE):
        tool_args = {"action": "reset"}
        description = "Reset MAtricks"

    apply = PlanStep(
        tool_name="manage_matricks",
        tool_args=tool_args,
        description=description,
        risk_tier=RiskTier.SAFE_WRITE,
        depends_on=[select.id],
    )
    steps.append(apply)

    steps.append(build_verify_step(
        "get_matricks_state",
        "Read back tracked MAtricks state",
        tool_args={},
        depends_on=[apply.id],
    ))
    return steps


__all__ = [
    "build_effect_workflow",
    "build_chaser_workflow",
    "build_matricks_workflow",
]
