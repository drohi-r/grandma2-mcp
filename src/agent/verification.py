"""Post-mutation verification — checks that tool calls achieved intended state.

Each strategy reads back the *specific* object a mutation touched (``list group
5``, ``list executor 2.105``) through an existing SAFE_READ tool and checks the
console's answer for that object — not a substring anywhere in a pool listing.
Also provides preflight snapshots and rollback strategy suggestions.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
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

_NO_OBJECTS = "NO OBJECTS FOUND"


def _console_text(data: Any) -> str:
    """Raw console text from a read-back reply (tools return it as raw_response)."""
    if isinstance(data, dict):
        parts = [data.get(k) for k in ("raw_response", "response")]
        text = "\n".join(p for p in parts if isinstance(p, str))
        return text or json.dumps(data, default=str)
    return str(data)


def _object_absent(data: Any) -> bool:
    if isinstance(data, dict) and _NO_OBJECTS in (data.get("console_warnings") or []):
        return True
    return _NO_OBJECTS in _console_text(data).upper()


def _exists(step: PlanStep, data: Any, label: str) -> tuple[bool, str]:
    if _object_absent(data):
        return False, f"{label} not found on the console after the step"
    return True, f"{label} present on the console"


def _absent(step: PlanStep, data: Any, label: str) -> tuple[bool, str]:
    if _object_absent(data):
        return True, f"{label} confirmed deleted"
    return False, f"{label} still present on the console"


def _has_name(step: PlanStep, data: Any, label: str) -> tuple[bool, str]:
    name = str(step.tool_args.get("name") or "")
    if _object_absent(data):
        return False, f"{label} not found on the console"
    if name.lower() in _console_text(data).lower():
        return True, f"{label} is labelled {name!r}"
    return False, f"{label} does not show label {name!r}"


def _patched_at(step: PlanStep, data: Any, label: str) -> tuple[bool, str]:
    address = f"{int(step.tool_args['dmx_universe'])}.{int(step.tool_args['dmx_address']):03d}"
    if _object_absent(data):
        return False, f"{label} not found on the console"
    if address in _console_text(data):
        return True, f"{label} patched at {address}"
    return False, f"{label} is not patched at {address}"


def _executor_has_sequence(step: PlanStep, data: Any, label: str) -> tuple[bool, str]:
    seq = step.tool_args.get("source_id")
    if re.search(rf"Sequence\s*=\s*Seq\s+{re.escape(str(seq))}\b", _console_text(data), re.IGNORECASE):
        return True, f"{label} plays sequence {seq}"
    return False, f"{label} does not show sequence {seq}"


def _split_executor(target: Any) -> tuple[int, int | None]:
    text = str(target)
    if "." in text:
        page, exec_id = text.split(".", 1)
        return int(exec_id), int(page)
    return int(text), None


@dataclass(frozen=True)
class VerificationStrategy:
    verify_tool: str
    build_args: Callable[[dict[str, Any]], dict[str, Any] | None]  # None → not verifiable
    check: Callable[[PlanStep, Any, str], tuple[bool, str]]
    label: Callable[[dict[str, Any]], str]


def _object_args(object_type: str | None = None) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    def build(args: dict[str, Any]) -> dict[str, Any] | None:
        otype = object_type or args.get("object_type")
        oid = args.get("object_id")
        if oid is None:
            return None
        out: dict[str, Any] = {"object_id": oid}
        if otype:
            out["object_type"] = otype
        return out
    return build


def _group_args(args: dict[str, Any]) -> dict[str, Any] | None:
    return {"object_type": "group", "object_id": args["group_id"]} if "group_id" in args else None


def _preset_args(args: dict[str, Any]) -> dict[str, Any] | None:
    if "preset_id" not in args:
        return None
    return {"object_type": "preset", "preset_type": args.get("preset_type"), "object_id": args["preset_id"]}


def _cue_args(cue_key: str) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    def build(args: dict[str, Any]) -> dict[str, Any] | None:
        if args.get("sequence_id") is None or args.get(cue_key) is None:
            return None  # cue went to the selected executor's sequence — unknown id
        return {"sequence_id": args["sequence_id"], "cue_id": args[cue_key]}
    return build


def _assign_args(args: dict[str, Any]) -> dict[str, Any] | None:
    if (
        str(args.get("mode", "")).lower() != "assign"
        or str(args.get("source_type", "")).lower() != "sequence"
        or str(args.get("target_type", "")).lower() != "executor"
        or args.get("target_id") is None
    ):
        return None  # only sequence → executor assignments have a read-back
    exec_id, page = _split_executor(args["target_id"])
    out: dict[str, Any] = {"executor_id": exec_id}
    if page is not None:
        out["page"] = page
    return out


def _patch_args(args: dict[str, Any]) -> dict[str, Any] | None:
    return {"fixture_id": args["fixture_id"]} if "fixture_id" in args else None


def _label_args(args: dict[str, Any]) -> dict[str, Any] | None:
    if str(args.get("action", "label")).lower() != "label" or not args.get("name"):
        return None
    return _object_args()(args)


def _describe(kind: str, *keys: str) -> Callable[[dict[str, Any]], str]:
    def label(args: dict[str, Any]) -> str:
        ids = ".".join(str(args[k]) for k in keys if args.get(k) is not None)
        return f"{kind} {ids}".strip()
    return label


VERIFICATION_STRATEGIES: dict[str, VerificationStrategy] = {
    "create_fixture_group": VerificationStrategy(
        "query_object_list", _group_args, _exists, _describe("Group", "group_id")),
    "store_new_preset": VerificationStrategy(
        "query_object_list", _preset_args, _exists, _describe("Preset", "preset_type", "preset_id")),
    "store_current_cue": VerificationStrategy(
        "list_sequence_cues", _cue_args("cue_number"), _exists, _describe("Cue", "sequence_id", "cue_number")),
    "store_cue_with_timing": VerificationStrategy(
        "list_sequence_cues", _cue_args("cue_id"), _exists, _describe("Cue", "sequence_id", "cue_id")),
    "assign_object": VerificationStrategy(
        "get_executor_status", _assign_args, _executor_has_sequence, _describe("Executor", "target_id")),
    "patch_fixture": VerificationStrategy(
        "list_fixtures", _patch_args, _patched_at, _describe("Fixture", "fixture_id")),
    "label_or_appearance": VerificationStrategy(
        "query_object_list", _label_args, _has_name, _describe("Object", "object_type", "object_id")),
    "store_object": VerificationStrategy(
        "query_object_list", _object_args(), _exists, _describe("Object", "object_type", "object_id")),
    "delete_object": VerificationStrategy(
        "query_object_list", _object_args(), _absent, _describe("Object", "object_type", "object_id")),
}


def build_verification_call(step: PlanStep) -> tuple[str, dict[str, Any]] | None:
    """The read-back (tool name, args) for *step*, or None when it can't be verified."""
    strategy = VERIFICATION_STRATEGIES.get(step.tool_name)
    if strategy is None:
        return None
    args = strategy.build_args(step.tool_args)
    if args is None:
        return None
    return strategy.verify_tool, {k: v for k, v in args.items() if v is not None}


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
        """Read the touched object back from the console and check the mutation."""
        strategy = VERIFICATION_STRATEGIES.get(step.tool_name)
        if not strategy:
            # DESTRUCTIVE steps without a verification strategy must NOT
            # silently pass — fail explicitly so the operator is alerted.
            is_destructive = getattr(step, "risk_tier", None) and str(step.risk_tier) == "DESTRUCTIVE"
            if is_destructive:
                return VerificationResult(
                    step_id=step.id,
                    passed=False,
                    expected={},
                    actual={},
                    details=f"No verification strategy for DESTRUCTIVE tool '{step.tool_name}' — cannot confirm success",
                )
            return VerificationResult(
                step_id=step.id,
                passed=True,
                expected={},
                actual={},
                details=f"No verification strategy for tool '{step.tool_name}' — assumed OK",
            )

        label = strategy.label(step.tool_args)
        call = build_verification_call(step)
        if call is None:
            return VerificationResult(
                step_id=step.id,
                passed=True,
                expected={},
                actual={},
                details=f"{label}: not verifiable from the step arguments — relying on the tool reply",
            )

        verify_tool_name, verify_args = call
        verify_fn = self._dispatch.get(verify_tool_name)
        if not verify_fn:
            return VerificationResult(
                step_id=step.id,
                passed=True,
                expected={},
                actual={},
                details=f"Verification tool '{verify_tool_name}' not available — assumed OK",
            )

        expected = {"read_back": verify_tool_name, "args": verify_args}
        try:
            raw_result = await verify_fn(**verify_args)
            result_data = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
            if isinstance(result_data, dict) and (
                result_data.get("ok") is False or result_data.get("blocked") is True
            ):
                passed, details = False, f"{label}: read-back failed — {result_data.get('error', 'unknown error')}"
            else:
                passed, details = strategy.check(step, result_data, label)
            return VerificationResult(
                step_id=step.id,
                passed=passed,
                expected=expected,
                actual={"raw_response_snippet": _console_text(result_data)[:200]},
                details=details,
            )
        except Exception as e:
            logger.warning("Verification failed for step %s: %s", step.id, e)
            return VerificationResult(
                step_id=step.id,
                passed=False,
                expected=expected,
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
