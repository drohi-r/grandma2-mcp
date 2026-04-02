"""Fixture patch workflow template.

Canonical ordering:
1. List existing fixture types (discovery)
2. Import fixture type if needed
3. Patch fixtures at addresses
4. Label fixtures
5. Verify patch
"""

from __future__ import annotations

from src.agent.state import ParsedGoal, PlanStep
from src.agent.workflows.common import build_label_step, build_verify_step
from src.vocab import RiskTier


def build_patch_workflow(goal: ParsedGoal) -> list[PlanStep]:
    """Build a complete fixture patch workflow from a parsed goal.

    Args:
        goal: Parsed goal with fixture_type, count, names, and options
              (universe, start_address, start_id).

    Returns:
        Ordered list of PlanSteps with dependency edges.
    """
    steps: list[PlanStep] = []

    fixture_type = goal.fixture_type or "Generic Dimmer"
    count = goal.count or 1
    universe = goal.options.get("universe", 1)
    start_address = goal.options.get("start_address", 1)
    start_id = goal.options.get("start_id", 1)

    # Step 1: Discover existing fixture types
    discover = PlanStep(
        tool_name="list_fixture_types",
        tool_args={},
        description="List existing fixture types",
        risk_tier=RiskTier.SAFE_READ,
    )
    steps.append(discover)

    # Step 2: Import fixture type if specified
    import_step = PlanStep(
        tool_name="import_fixture_type",
        tool_args={
            "fixture_type": fixture_type,
            "confirm_destructive": False,
        },
        description=f"Import fixture type '{fixture_type}'",
        risk_tier=RiskTier.DESTRUCTIVE,
        depends_on=[discover.id],
    )
    steps.append(import_step)

    # Step 3: Patch fixtures
    for i in range(count):
        fixture_id = start_id + i
        address = start_address + i  # simplified; real addressing depends on channel count
        patch = PlanStep(
            tool_name="patch_fixture",
            tool_args={
                "fixture_id": fixture_id,
                "fixture_type": fixture_type,
                "universe": universe,
                "address": address,
                "confirm_destructive": False,
            },
            description=f"Patch fixture {fixture_id} at {universe}.{address:03d}",
            risk_tier=RiskTier.DESTRUCTIVE,
            depends_on=[import_step.id],
        )
        steps.append(patch)

    # Step 4: Label fixtures (if names provided)
    patch_step_ids = [s.id for s in steps if s.tool_name == "patch_fixture"]
    for i, name in enumerate(goal.names[:count]):
        fixture_id = start_id + i
        label = build_label_step(
            "fixture", fixture_id, name, depends_on=[patch_step_ids[i]]
        )
        steps.append(label)

    # Step 5: Verify patch
    last_mutation_id = steps[-1].id if steps else ""
    verify = build_verify_step(
        "query_object_list",
        f"Verify {count} fixtures patched",
        tool_args={"object_type": "fixture"},
        depends_on=[last_mutation_id],
    )
    steps.append(verify)

    return steps
