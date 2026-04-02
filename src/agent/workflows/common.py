"""Common workflow building blocks — label, verify, discover.

Shared step builders used across patch, preset, and playback workflows.
"""

from __future__ import annotations

from src.agent.state import PlanStep
from src.vocab import RiskTier


def build_label_step(
    object_type: str,
    object_id: int | str,
    name: str,
    *,
    depends_on: list[str] | None = None,
) -> PlanStep:
    """Build a step that labels an object."""
    return PlanStep(
        tool_name="label_or_appearance",
        tool_args={
            "object_type": object_type,
            "object_id": int(object_id) if str(object_id).isdigit() else object_id,
            "name": name,
            "action": "label",
        },
        description=f'Label {object_type} {object_id} as "{name}"',
        risk_tier=RiskTier.DESTRUCTIVE,
        depends_on=depends_on or [],
    )


def build_verify_step(
    verify_tool: str,
    description: str,
    *,
    tool_args: dict | None = None,
    depends_on: list[str] | None = None,
) -> PlanStep:
    """Build a verification step that inspects console state."""
    return PlanStep(
        tool_name=verify_tool,
        tool_args=tool_args or {},
        description=f"Verify: {description}",
        risk_tier=RiskTier.SAFE_READ,
        depends_on=depends_on or [],
    )


def build_discover_names_steps(
    destination: str,
) -> list[PlanStep]:
    """Build steps for discovering object names at a pool destination."""
    discover = PlanStep(
        tool_name="discover_object_names",
        tool_args={"destination": destination},
        description=f"Discover object names at {destination}",
        risk_tier=RiskTier.SAFE_READ,
    )
    return [discover]


def build_get_location_step(*, depends_on: list[str] | None = None) -> PlanStep:
    """Build a step that queries the current console location."""
    return PlanStep(
        tool_name="get_console_location",
        tool_args={},
        description="Get current console location",
        risk_tier=RiskTier.SAFE_READ,
        depends_on=depends_on or [],
    )
