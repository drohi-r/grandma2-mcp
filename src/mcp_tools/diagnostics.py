"""MCP tools — diagnostics. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    label as build_label,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# New Tools — Batch Operations & Diagnostics
# Added during MA2 Agent hardening pass
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def batch_label(
    object_type: str,
    items: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Label multiple objects in a single call (DESTRUCTIVE).

    Instead of calling label_or_appearance once per object, batch_label applies
    names to an entire list. Accepts a JSON array of {id, name} pairs.

    Args:
        object_type: Object type (e.g. "group", "sequence", "macro", "preset")
        items: JSON array string, e.g. '[{"id": 1, "name": "Front Wash"}, {"id": 2, "name": "Back Light"}]'
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: JSON with labels_applied, commands, errors, risk_tier.

    Examples:
        - Label groups 1-3: object_type="group", items='[{"id":1,"name":"Front"},{"id":2,"name":"Back"},{"id":3,"name":"Side"}]'
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "batch_label is DESTRUCTIVE. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    try:
        item_list = json.loads(items) if isinstance(items, str) else items
    except (json.JSONDecodeError, TypeError) as e:
        return json.dumps({"error": f"Invalid items JSON: {e}", "blocked": True}, indent=2)

    if not isinstance(item_list, list) or not item_list:
        return json.dumps({"error": "items must be a non-empty JSON array of {id, name} objects.", "blocked": True}, indent=2)

    client = await _srv.get_client()
    commands: list[str] = []
    errors: list[str] = []

    for item in item_list:
        obj_id = item.get("id")
        name = item.get("name")
        if obj_id is None or name is None:
            errors.append(f"Skipped item missing id or name: {item}")
            continue
        cmd = build_label(object_type, obj_id, name)
        try:
            await client.send_command_with_response(cmd)
            commands.append(cmd)
        except Exception as e:
            errors.append(f"Failed {cmd}: {e}")

    return json.dumps({
        "labels_applied": len(commands),
        "total_items": len(item_list),
        "commands": commands,
        "errors": errors,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def bulk_executor_assign(
    executor_id: int,
    sequence_id: int,
    executor_page: int = 1,
    trigger: str | None = None,
    priority: str | None = None,
    fader_function: str | None = None,
    label: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Assign a sequence to an executor and configure it in one call (DESTRUCTIVE).

    Combines assign + optional trigger/priority/fader/label into a single
    operation instead of 4-5 separate tool calls.

    Args:
        executor_id: Executor number to assign to.
        sequence_id: Sequence number to assign.
        executor_page: Executor page (default 1).
        trigger: Optional trigger type (e.g. "go", "flash", "toggle").
        priority: Optional priority level (e.g. "normal", "high", "super", "htp").
        fader_function: Optional fader function (e.g. "master", "crossfade", "speed").
        label: Optional label for the executor.
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation).

    Returns:
        str: JSON with commands_sent, raw_responses, risk_tier.

    Examples:
        - Assign seq 1 to exec 101: executor_id=101, sequence_id=1
        - Full setup: executor_id=101, sequence_id=1, trigger="go", priority="high", label="Main Wash"
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "bulk_executor_assign is DESTRUCTIVE. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()
    exec_ref = f"{executor_page}.{executor_id}"
    commands_sent: list[str] = []
    raw_responses: list[str] = []

    # 1. Assign sequence to executor
    assign_cmd = f"assign sequence {sequence_id} at executor {exec_ref}"
    raw = await client.send_command_with_response(assign_cmd)
    commands_sent.append(assign_cmd)
    raw_responses.append(raw)

    # 2. Optional: set trigger
    if trigger:
        cmd = f"assign executor {exec_ref} /trigger={trigger}"
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    # 3. Optional: set priority
    if priority:
        cmd = f"assign executor {exec_ref} /priority={priority}"
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    # 4. Optional: set fader function
    if fader_function:
        cmd = f"assign executor {exec_ref} /fader={fader_function}"
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    # 5. Optional: label
    if label:
        cmd = f'label executor {exec_ref} "{label}"'
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    return json.dumps({
        "executor": exec_ref,
        "sequence_id": sequence_id,
        "commands_sent": commands_sent,
        "raw_responses": raw_responses,
        "options_applied": {
            "trigger": trigger,
            "priority": priority,
            "fader_function": fader_function,
            "label": label,
        },
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def auto_number_cues(
    sequence_id: int,
    start: float = 1.0,
    spacing: float = 1.0,
    confirm_destructive: bool = False,
) -> str:
    """
    Renumber all cues in a sequence with configurable start and spacing (DESTRUCTIVE).

    Lists existing cues, then moves each to its new number. Useful for cleaning
    up cue lists with irregular numbering (e.g. 1, 1.5, 3, 7 → 1, 2, 3, 4).

    Args:
        sequence_id: Sequence to renumber.
        start: Starting cue number (default 1.0).
        spacing: Increment between cues (default 1.0).
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation).

    Returns:
        str: JSON with cues_renumbered, old_to_new mapping, commands.

    Examples:
        - Standard: sequence_id=1 → cues become 1, 2, 3, ...
        - By tens: sequence_id=1, start=10, spacing=10 → 10, 20, 30, ...
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "auto_number_cues is DESTRUCTIVE. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()

    # List existing cues
    list_cmd = f"list cue sequence {sequence_id}"
    raw = await client.send_command_with_response(list_cmd)
    if "NO OBJECTS FOUND" in raw.upper():
        return json.dumps({
            "error": f"Sequence {sequence_id} has no cues.",
            "command_sent": list_cmd,
            "raw_response": raw,
            "risk_tier": "DESTRUCTIVE",
            "blocked": True,
        }, indent=2)

    # Parse cue IDs from the raw list output (look for numeric IDs in first column)
    import re
    cue_ids: list[float] = []
    for line in raw.splitlines():
        m = re.match(r"^\s*(\d+(?:\.\d+)?)\s", line.strip())
        if m:
            cue_ids.append(float(m.group(1)))

    if not cue_ids:
        return json.dumps({
            "error": "Could not parse cue IDs from sequence listing.",
            "raw_response": raw,
            "risk_tier": "DESTRUCTIVE",
            "blocked": True,
        }, indent=2)

    # Build old→new mapping (work in reverse to avoid collisions)
    old_to_new: dict[str, str] = {}
    commands: list[str] = []
    new_num = start
    mapping = []
    for old_id in sorted(cue_ids):
        mapping.append((old_id, new_num))
        new_num += spacing

    # Move cues in reverse order to avoid overwriting
    for old_id, new_id in reversed(mapping):
        if old_id != new_id:
            cmd = f"move cue {old_id} sequence {sequence_id} at cue {new_id} sequence {sequence_id}"
            await client.send_command_with_response(cmd)
            commands.append(cmd)
        old_to_new[str(old_id)] = str(new_id)

    return json.dumps({
        "cues_renumbered": len(old_to_new),
        "sequence_id": sequence_id,
        "old_to_new": old_to_new,
        "commands": commands,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def compare_cue_values(
    sequence_id: int,
    cue_a: float,
    cue_b: float,
) -> str:
    """
    Compare two cues in a sequence and show differences (SAFE_READ).

    Lists both cues and diffs the raw console output to help identify
    what changes between them. Useful for tracking analysis and cue cleanup.

    Args:
        sequence_id: Sequence containing both cues.
        cue_a: First cue number.
        cue_b: Second cue number.

    Returns:
        str: JSON with cue_a, cue_b, raw outputs, and line-by-line differences.
    """
    client = await _srv.get_client()

    cmd_a = f"list cue {cue_a} sequence {sequence_id}"
    cmd_b = f"list cue {cue_b} sequence {sequence_id}"
    raw_a = await client.send_command_with_response(cmd_a)
    raw_b = await client.send_command_with_response(cmd_b)

    # Line-by-line diff
    lines_a = set(raw_a.strip().splitlines())
    lines_b = set(raw_b.strip().splitlines())
    only_in_a = sorted(lines_a - lines_b)
    only_in_b = sorted(lines_b - lines_a)

    return json.dumps({
        "sequence_id": sequence_id,
        "cue_a": cue_a,
        "cue_b": cue_b,
        "command_a": cmd_a,
        "command_b": cmd_b,
        "raw_a": raw_a,
        "raw_b": raw_b,
        "only_in_cue_a": only_in_a,
        "only_in_cue_b": only_in_b,
        "identical": len(only_in_a) == 0 and len(only_in_b) == 0,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def diagnose_no_output(
    fixture_id: int | None = None,
    universe: int | None = None,
) -> str:
    """
    Diagnostic tree for fixtures not producing output (SAFE_READ).

    Runs a series of non-destructive checks to identify why fixtures
    may not be responding: Grand Master level, blackout state, park status,
    patch, executor state. Returns structured findings.

    Args:
        fixture_id: Optional specific fixture to check.
        universe: Optional DMX universe to check.

    Returns:
        str: JSON with checks list, each having check name, status (ok/warning/fail), detail.
    """
    client = await _srv.get_client()
    checks: list[dict[str, str]] = []

    # 1. Grand Master
    try:
        raw = await client.send_command_with_response("listvar")
        if "$GRANDMASTER" in raw.upper() or "grand" in raw.lower():
            checks.append({"check": "grand_master", "status": "ok", "detail": "Grand Master variable found in system vars"})
        else:
            checks.append({"check": "grand_master", "status": "warning", "detail": "Could not determine Grand Master level — check manually"})
    except Exception as e:
        checks.append({"check": "grand_master", "status": "fail", "detail": f"Error checking Grand Master: {e}"})

    # 2. Blackout state
    try:
        raw = await client.send_command_with_response("listvar")
        if "blackout" in raw.lower():
            checks.append({"check": "blackout", "status": "warning", "detail": "Blackout reference found — check B.O. button on console"})
        else:
            checks.append({"check": "blackout", "status": "ok", "detail": "No blackout indication in system variables"})
    except Exception as e:
        checks.append({"check": "blackout", "status": "fail", "detail": f"Error checking blackout: {e}"})

    # 3. Park status
    if fixture_id is not None:
        try:
            raw = await client.send_command_with_response(f"list fixture {fixture_id}")
            if "PARK" in raw.upper():
                checks.append({"check": "park_status", "status": "fail", "detail": f"Fixture {fixture_id} appears to be PARKED — use unpark_fixture to release"})
            else:
                checks.append({"check": "park_status", "status": "ok", "detail": f"Fixture {fixture_id} is not parked"})
        except Exception as e:
            checks.append({"check": "park_status", "status": "fail", "detail": f"Error checking park status: {e}"})

    # 4. Patch / DMX address
    if fixture_id is not None:
        try:
            raw = await client.send_command_with_response(f"info fixture {fixture_id}")
            if "NO OBJECTS" in raw.upper():
                checks.append({"check": "patch", "status": "fail", "detail": f"Fixture {fixture_id} not found — may not be patched"})
            else:
                checks.append({"check": "patch", "status": "ok", "detail": f"Fixture {fixture_id} found in patch"})
        except Exception as e:
            checks.append({"check": "patch", "status": "fail", "detail": f"Error checking patch: {e}"})

    # 5. Universe check
    if universe is not None:
        try:
            raw = await client.send_command_with_response(f"list dmxuniverse {universe}")
            checks.append({"check": "universe", "status": "ok", "detail": f"Universe {universe} response: {raw[:200]}"})
        except Exception as e:
            checks.append({"check": "universe", "status": "fail", "detail": f"Error checking universe {universe}: {e}"})

    # 6. Selected fixtures count
    try:
        raw = await client.send_command_with_response("listvar")
        if "SELECTEDFIXTURESCOUNT" in raw:
            checks.append({"check": "selection", "status": "ok", "detail": "Selection variable present in system vars"})
        else:
            checks.append({"check": "selection", "status": "warning", "detail": "Could not find fixture selection count"})
    except Exception as e:
        checks.append({"check": "selection", "status": "fail", "detail": f"Error checking selection: {e}"})

    overall = "ok"
    if any(c["status"] == "fail" for c in checks):
        overall = "fail"
    elif any(c["status"] == "warning" for c in checks):
        overall = "warning"

    return json.dumps({
        "overall_status": overall,
        "fixture_id": fixture_id,
        "universe": universe,
        "checks": checks,
        "risk_tier": "SAFE_READ",
        "recommendation": "If all checks pass but no output, verify: (1) correct DMX universe output enabled in Setup, (2) physical DMX connection, (3) fixture address matching patch",
    }, indent=2)
