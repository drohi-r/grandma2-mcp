"""Post-mutation verification — checks that tool calls achieved intended state.

Uses existing MCP inspection tools (query_object_list, get_object_info,
list_console_destination, list_sequence_cues) to verify mutations.
Also provides preflight snapshots and rollback strategy suggestions.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from src.agent.state import (
    Checkpoint,
    PlanStep,
    RollbackStrategy,
    RunContext,
    VerificationResult,
)

logger = logging.getLogger(__name__)

# Tool name → verification strategy mapping.
# Each entry maps a mutating tool to the inspection tool + args pattern
# that should be used to verify the mutation succeeded.
VERIFICATION_STRATEGIES: dict[str, dict[str, Any]] = {
    "create_fixture_group": {
        "verify_tool": "query_object_list",
        "args_template": {"object_type": "group"},
        "check_field": "object_id",
        "extract_from_args": "group_id",
    },
    "store_new_preset": {
        "verify_tool": "query_object_list",
        "args_template": {"object_type": "preset"},
        "check_field": "object_id",
        "extract_from_args": "preset_id",
    },
    "store_current_cue": {
        "verify_tool": "list_sequence_cues",
        "args_template": {},
        "check_field": "cue_id",
        "extract_from_args": "cue_id",
    },
    "assign_object": {
        "verify_tool": "get_object_info",
        "args_template": {},
        "check_field": "assignment",
        "extract_from_args": "target",
    },
    "patch_fixture": {
        "verify_tool": "query_object_list",
        "args_template": {"object_type": "fixture"},
        "check_field": "object_id",
        "extract_from_args": "fixture_id",
    },
    "label_or_appearance": {
        "verify_tool": "get_object_info",
        "args_template": {},
        "check_field": "label",
        "extract_from_args": "name",
    },
    "store_object": {
        "verify_tool": "query_object_list",
        "args_template": {},
        "check_field": "object_id",
        "extract_from_args": "object_id",
    },
    "delete_object": {
        "verify_tool": "query_object_list",
        "args_template": {},
        "check_field": "absent",
        "extract_from_args": "object_id",
    },
}

# Tools that can potentially be rolled back with oops
OOPS_ELIGIBLE = {
    "store_current_cue",
    "store_new_preset",
    "store_object",
    "assign_object",
    "label_or_appearance",
    "create_fixture_group",
    "delete_object",
    "copy_or_move_object",
}


class Verifier:
    """Post-mutation verification using existing inspection tools."""

    def __init__(self, tool_dispatch: dict[str, Any] | None = None):
        """Initialize with an optional tool dispatch registry.

        Args:
            tool_dispatch: Map of tool_name → async callable. If None,
                verification will return unverified results.
        """
        self._dispatch = tool_dispatch or {}

    async def preflight_snapshot(
        self, step: PlanStep, context: RunContext
    ) -> Checkpoint:
        """Capture console state before a mutation.

        Calls get_console_location to record where we are, and optionally
        queries the object being modified.
        """
        snapshot_data: dict[str, Any] = {"step_description": step.description}
        console_location = "unknown"

        get_location = self._dispatch.get("get_console_location")
        if get_location:
            try:
                raw = await get_location()
                result = json.loads(raw) if isinstance(raw, str) else raw
                console_location = result.get("parsed_prompt", {}).get("location", "unknown")
                snapshot_data["console_location_raw"] = raw
            except Exception as e:
                logger.warning("Preflight snapshot failed for get_console_location: %s", e)
                snapshot_data["snapshot_error"] = str(e)

        return Checkpoint(
            step_id=step.id,
            timestamp=datetime.now(UTC),
            console_location=console_location,
            snapshot_data=snapshot_data,
        )

    async def verify_step(
        self, step: PlanStep, context: RunContext
    ) -> VerificationResult:
        """Check that a mutation achieved the intended state.

        Uses VERIFICATION_STRATEGIES to determine which inspection tool
        to call and what to check in the response.
        """
        strategy = VERIFICATION_STRATEGIES.get(step.tool_name)
        if not strategy:
            return VerificationResult(
                step_id=step.id,
                passed=True,
                expected={},
                actual={},
                details=f"No verification strategy for tool '{step.tool_name}' — assumed OK",
            )

        verify_tool_name = strategy["verify_tool"]
        verify_fn = self._dispatch.get(verify_tool_name)
        if not verify_fn:
            return VerificationResult(
                step_id=step.id,
                passed=True,
                expected={},
                actual={},
                details=f"Verification tool '{verify_tool_name}' not available — assumed OK",
            )

        # Build verification args from the strategy template + step args
        verify_args = dict(strategy["args_template"])
        extract_key = strategy.get("extract_from_args")
        expected_value = step.tool_args.get(extract_key) if extract_key else None

        try:
            raw_result = await verify_fn(**verify_args)
            result_data = json.loads(raw_result) if isinstance(raw_result, str) else raw_result

            # Check for the expected value in the response
            check_field = strategy["check_field"]
            if check_field == "absent":
                # For delete: verify object is NOT present
                passed = "NO OBJECTS FOUND" in str(result_data).upper()
                details = "Object confirmed deleted" if passed else "Object may still exist"
            else:
                # For create/modify: verify object IS present
                passed = str(expected_value) in str(result_data)
                details = f"Verified {check_field}={expected_value}" if passed else (
                    f"Expected {check_field}={expected_value} not found in response"
                )

            return VerificationResult(
                step_id=step.id,
                passed=passed,
                expected={check_field: expected_value},
                actual={"raw_response_snippet": str(result_data)[:200]},
                details=details,
            )

        except Exception as e:
            logger.warning("Verification failed for step %s: %s", step.id, e)
            return VerificationResult(
                step_id=step.id,
                passed=False,
                expected={strategy["check_field"]: expected_value},
                actual={"error": str(e)},
                details=f"Verification error: {e}",
            )

    def suggest_rollback(self, step: PlanStep) -> RollbackStrategy:
        """Determine the best rollback strategy for a failed step."""
        if step.tool_name in OOPS_ELIGIBLE:
            return RollbackStrategy.OOPS
        if step.tool_name in ("patch_fixture",):
            return RollbackStrategy.DELETE
        return RollbackStrategy.NONE

    def has_strategy(self, tool_name: str) -> bool:
        """Check if a verification strategy exists for the given tool."""
        return tool_name in VERIFICATION_STRATEGIES
