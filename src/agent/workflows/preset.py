"""Preset creation workflow template.

Canonical ordering:
1. Select fixtures (by group or range)
2. Set attribute values
3. Store preset
4. Label preset
5. Verify preset
"""

from __future__ import annotations

from src.agent.state import ParsedGoal, PlanStep
from src.agent.workflows.common import build_label_step, build_verify_step
from src.vocab import RiskTier


def build_preset_workflow(goal: ParsedGoal) -> list[PlanStep]:
    """Build a preset creation workflow from a parsed goal.

    Args:
        goal: Parsed goal with options including:
            - preset_type: e.g. "color", "position", "gobo"
            - preset_id: target preset slot number
            - group_id: fixture group to select (optional)
            - fixture_start/fixture_end: fixture range (optional)
            - values: dict of attribute → value pairs
            - names: list with preset label

    Returns:
        Ordered list of PlanSteps with dependency edges.
    """
    steps: list[PlanStep] = []

    preset_type = goal.options.get("preset_type", "color")
    preset_id = goal.options.get("preset_id", 1)
    group_id = goal.options.get("group_id")
    fixture_start = goal.options.get("fixture_start")
    fixture_end = goal.options.get("fixture_end")
    values = goal.options.get("values", {})

    # Step 1: Select fixtures
    if group_id is not None:
        select = PlanStep(
            tool_name="select_fixtures_by_group",
            tool_args={"group_id": group_id},
            description=f"Select fixtures from group {group_id}",
            risk_tier=RiskTier.SAFE_WRITE,
        )
    elif fixture_start is not None:
        select = PlanStep(
            tool_name="modify_selection",
            tool_args={
                "action": "select",
                "start": fixture_start,
                "end": fixture_end or fixture_start,
            },
            description=f"Select fixtures {fixture_start}-{fixture_end or fixture_start}",
            risk_tier=RiskTier.SAFE_WRITE,
        )
    else:
        # Default: select all
        select = PlanStep(
            tool_name="clear_programmer",
            tool_args={"scope": "selection"},
            description="Clear selection before preset workflow",
            risk_tier=RiskTier.SAFE_WRITE,
        )
    steps.append(select)

    # Step 2: Set attribute values
    for attr_name, attr_value in values.items():
        set_val = PlanStep(
            tool_name="set_attribute",
            tool_args={
                "attribute": attr_name,
                "value": attr_value,
            },
            description=f"Set {attr_name} to {attr_value}",
            risk_tier=RiskTier.SAFE_WRITE,
            depends_on=[select.id],
        )
        steps.append(set_val)

    # Step 3: Store preset
    last_value_id = steps[-1].id
    store = PlanStep(
        tool_name="store_new_preset",
        tool_args={
            "preset_type": preset_type,
            "preset_id": preset_id,
            "confirm_destructive": False,
        },
        description=f"Store {preset_type} preset {preset_id}",
        risk_tier=RiskTier.DESTRUCTIVE,
        depends_on=[last_value_id],
    )
    steps.append(store)

    # Step 4: Label preset (if name provided)
    if goal.names:
        label = build_label_step(
            "preset", preset_id, goal.names[0], depends_on=[store.id]
        )
        steps.append(label)

    # Step 5: Verify preset
    verify = build_verify_step(
        "query_object_list",
        f"Verify {preset_type} preset {preset_id} exists",
        tool_args={"object_type": "preset"},
        depends_on=[steps[-1].id],
    )
    steps.append(verify)

    return steps
