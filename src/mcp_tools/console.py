"""MCP tools — console. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
import re
import time
from pathlib import Path

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    attribute_at,
    call,
    channel_at,
    clear as build_clear,
    clear_active as build_clear_active,
    clear_all as build_clear_all,
    clear_selection as build_clear_selection,
    copy as build_copy,
    delete as build_delete,
    delete_cue as build_delete_cue,
    fixture_at,
    go_macro,
    go_sequence,
    goto_cue,
    group_at,
    info as build_info,
    label as build_label,
    label_group,
    move as build_move,
    park as build_park,
    pause_sequence,
    select_fixture,
    store_cue as build_store_cue,
    store_group,
    store_preset as build_store_preset,
    unpark as build_unpark,
)
from src.mcp_features import (
    report_progress,
)
from src.navigation import scan_indexes
from src.server import (
    _MAX_COMMAND_CHARS,
    _handle_errors,
    _validate_object_exists,
    _vocab_spec,
    logger,
    mcp,
)
from src.telnet_client import hold_connection
from src.vocab import RiskTier, classify_command

# ============================================================
# MCP Tools Definition
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.GROUP_STORE)
@_handle_errors
async def create_fixture_group(
    start_fixture: int,
    end_fixture: int,
    group_id: int,
    group_name: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Create a group containing a specified range of fixtures (DESTRUCTIVE).

    This tool selects the specified range of fixtures and saves them as a group.
    Optionally, a name can be assigned to the group.

    Args:
        start_fixture: Starting fixture number
        end_fixture: Ending fixture number
        group_id: Group number to save
        group_name: (Optional) Group name, e.g., "Front Wash"
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: Operation result message

    Examples:
        - Save fixtures 1 to 10 as group 1
        - Save fixtures 1 to 10 as group 1 with name "Front Wash"
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Create Fixture Group uses Store (DESTRUCTIVE). Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()

    # Select fixtures
    select_cmd = select_fixture(start_fixture, end_fixture)
    await client.send_command(select_cmd)

    # Save as group
    store_cmd = store_group(group_id)
    await client.send_command(store_cmd)

    # Add label if name is provided
    if group_name:
        label_cmd = label_group(group_id, group_name)
        await client.send_command(label_cmd)
        return f'Created Group {group_id} "{group_name}" containing Fixtures {start_fixture} to {end_fixture}'

    return (
        f"Created Group {group_id} containing Fixtures {start_fixture} to {end_fixture}"
    )


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def execute_sequence(
    sequence_id: int,
    action: str,
    cue_id: int | None = None,
) -> str:
    """
    Execute sequence-related operations.

    Args:
        sequence_id: Sequence number
        action: Operation type: "go" (execute), "pause" (pause), or "goto" (jump to cue)
        cue_id: (Required for goto) Target cue number

    Returns:
        str: Operation result message

    Examples:
        - Execute sequence 1
        - Pause sequence 2
        - Jump to cue 5 of sequence 1
    """
    client = await _srv.get_client()

    if action == "go":
        cmd = go_sequence(sequence_id)
        await client.send_command(cmd)
        return f"Executed Sequence {sequence_id}"

    elif action == "pause":
        cmd = pause_sequence(sequence_id)
        await client.send_command(cmd)
        return f"Paused Sequence {sequence_id}"

    elif action == "goto":
        if cue_id is None:
            return "Error: goto action requires cue_id to be specified"
        cmd = goto_cue(sequence_id, cue_id)
        await client.send_command(cmd)
        return f"Jumped to Cue {cue_id} of Sequence {sequence_id}"

    return f"Unknown action: {action}, use go, pause, or goto"


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def send_raw_command(
    command: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Send a raw MA command to grandMA2 and return the console response.

    WARNING: This is a low-level tool that sends commands directly to a LIVE
    lighting console. Prefer the higher-level tools (create_fixture_group,
    execute_sequence) whenever possible.

    SAFETY: Commands are classified by risk tier before sending:
    - SAFE_READ (list, info, cd): Always allowed
    - SAFE_WRITE (at, go, clear, blackout): Allowed in standard and admin mode
    - DESTRUCTIVE (delete, store, assign, shutdown): Blocked unless
      confirm_destructive=True. Set GMA_SAFETY_LEVEL=admin to skip checks.

    Args:
        command: Raw MA command to send
        confirm_destructive: Must be True to send destructive commands
            (delete, store, assign, shutdown, newshow, etc.)

    Returns:
        str: JSON with command_sent, risk_tier, raw_response, and any
            safety block information.

    Examples:
        - go+ executor 1.1
        - list cue
        - store sequence 1 cue 1 (requires confirm_destructive=True)
    """
    # Input sanitization: reject line breaks that could inject commands
    if "\r" in command or "\n" in command:
        return json.dumps({
            "command_sent": None,
            "error": "Command contains line breaks (\\r or \\n) which could "
                     "inject additional commands. Remove them and retry.",
            "blocked": True,
        }, indent=2)

    if len(command) > _MAX_COMMAND_CHARS:
        return json.dumps({
            "command_sent": None,
            "error": (
                f"Command is {len(command)} characters; the console truncates at "
                f"{_MAX_COMMAND_CHARS} and fails with Error #72. Split it, or use "
                "run_command_batch."
            ),
            "blocked": True,
        }, indent=2)

    # Safety gate: classify every ';'-separated part — "ClearAll ; Store ..." is DESTRUCTIVE
    resolved = classify_command(command, _vocab_spec)
    risk = resolved.risk

    # Log and optionally block destructive commands
    if risk == RiskTier.DESTRUCTIVE:
        if _srv._GMA_SAFETY_LEVEL == "admin":
            # Admin mode: allow but still log for audit trail
            logger.warning(
                "ADMIN-MODE destructive command: %r (risk=%s, canonical=%s)",
                command, risk.value, resolved.canonical,
            )
        elif not confirm_destructive:
            logger.warning(
                "BLOCKED destructive command: %r (risk=%s, canonical=%s)",
                command, risk.value, resolved.canonical,
            )
            return json.dumps({
                "command_sent": None,
                "risk_tier": risk.value,
                "canonical_keyword": resolved.canonical,
                "error": (
                    f"Command part '{resolved.part}' is classified as {risk.value} "
                    f"({resolved.reason}). Set confirm_destructive=True to proceed, or use "
                    f"GMA_SAFETY_LEVEL=admin to disable safety checks."
                ),
                "blocked": True,
            }, indent=2)
        else:
            logger.warning(
                "CONFIRMED destructive command: %r (risk=%s, canonical=%s)",
                command, risk.value, resolved.canonical,
            )

    # Block all write commands in read-only mode
    if _srv._GMA_SAFETY_LEVEL == "read-only" and risk != RiskTier.SAFE_READ:
        logger.warning(
            "BLOCKED non-read command in read-only mode: %r (risk=%s)",
            command, risk.value,
        )
        return json.dumps({
            "command_sent": None,
            "risk_tier": risk.value,
            "error": (
                "Server is in read-only mode (GMA_SAFETY_LEVEL=read-only). "
                "Only SAFE_READ commands (list, info, cd) are allowed."
            ),
            "blocked": True,
        }, indent=2)

    logger.info(
        "Sending command: %r (risk=%s, canonical=%s)",
        command, risk.value, resolved.canonical,
    )

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(command)

    return json.dumps({
        "command_sent": command,
        "risk_tier": risk.value,
        "canonical_keyword": resolved.canonical,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


# Command files a batch may read (plain command lists only — not .env, keys, etc.)
_BATCH_FILE_SUFFIXES = {".txt", ".cmd", ".ma2", ".macro"}
_BATCH_MAX_FAILURES_REPORTED = 50


def _load_batch_lines(commands: list[str] | None, commands_file: str | None) -> tuple[list[str], str | None]:
    if commands_file:
        path = Path(commands_file)
        if path.suffix.lower() not in _srv._BATCH_FILE_SUFFIXES:
            return [], f"commands_file must be one of {sorted(_srv._BATCH_FILE_SUFFIXES)}"
        if not path.is_file():
            return [], f"commands_file not found: {commands_file}"
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    else:
        raw_lines = list(commands or [])
    lines = [ln.strip() for ln in raw_lines]
    return [ln for ln in lines if ln and not ln.startswith("#")], None


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def run_command_batch(
    commands: list[str] | None = None,
    commands_file: str | None = None,
    confirm_destructive: bool = False,
    stop_on_error: bool = True,
    delay: float = 0.0,
    timeout: float = 5.0,
) -> str:
    """
    Run many raw MA commands in order on one held connection (DESTRUCTIVE if any line is).

    Every line (and every ';'-part of a line) is risk-classified before anything
    is sent; if any is DESTRUCTIVE the whole batch needs confirm_destructive=True.
    Each command waits for its own console prompt, so batches run far faster than
    one send_raw_command call per line. Stops at the first console error or
    pop-up unless stop_on_error=False (a pop-up always stops the batch).

    Args:
        commands: Command lines to send, in order.
        commands_file: Path to a .txt/.cmd/.ma2/.macro file, one command per
            line; blank lines and lines starting with '#' are skipped.
        confirm_destructive: Required when any line is DESTRUCTIVE.
        stop_on_error: Stop at the first rejected command (default True).
        delay: Seconds to wait after each send before reading (default 0).
        timeout: Seconds to wait for each command's first output.

    Returns:
        str: JSON summary — total, executed, failed (line, command, errors),
            stopped_early, duration_s, last_reply.
    """
    from src.console_feedback import find_console_errors, find_pending_popup

    lines, load_error = _srv._load_batch_lines(commands, commands_file)
    if load_error:
        return json.dumps({"error": load_error, "blocked": True}, indent=2)
    if not lines:
        return json.dumps({"error": "No commands given (commands or commands_file).", "blocked": True}, indent=2)

    too_long = [i for i, ln in enumerate(lines, 1) if len(ln) > _MAX_COMMAND_CHARS]
    if too_long:
        return json.dumps({
            "error": f"Lines exceed {_MAX_COMMAND_CHARS} characters (console truncates them): {too_long[:20]}",
            "blocked": True,
        }, indent=2)

    risks = [classify_command(ln, _vocab_spec) for ln in lines]
    destructive = [i for i, r in enumerate(risks, 1) if r.risk == RiskTier.DESTRUCTIVE]
    if _srv._GMA_SAFETY_LEVEL == "read-only":
        not_read = [i for i, r in enumerate(risks, 1) if r.risk != RiskTier.SAFE_READ]
        if not_read:
            return json.dumps({
                "error": "Server is in read-only mode; batch contains non-read lines.",
                "non_read_lines": not_read[:50],
                "blocked": True,
            }, indent=2)
    if destructive and not confirm_destructive and _srv._GMA_SAFETY_LEVEL != "admin":
        return json.dumps({
            "blocked": True,
            "risk_tier": "DESTRUCTIVE",
            "destructive_lines": destructive[:50],
            "destructive_count": len(destructive),
            "error": (
                f"{len(destructive)} of {len(lines)} lines are DESTRUCTIVE "
                f"(first: line {destructive[0]} '{risks[destructive[0] - 1].part}'). "
                "Set confirm_destructive=True to run the batch."
            ),
        }, indent=2)

    client = await _srv.get_client()
    ctx = _srv.active_context(_srv.mcp)
    progress_every = max(1, len(lines) // 50)
    started = time.monotonic()
    failed: list[dict] = []
    executed = 0
    stopped_early = False
    last_reply = ""
    async with hold_connection(client):
        for lineno, cmd in enumerate(lines, 1):
            raw = await client.send_command_with_response(
                cmd, delay=delay, timeout=timeout, until_prompt=True,
            )
            executed += 1
            last_reply = raw
            if lineno % progress_every == 0 or lineno == len(lines):
                await report_progress(ctx, lineno, len(lines), f"line {lineno}/{len(lines)}")
            errors = find_console_errors(raw, cmd)
            popup = find_pending_popup(raw)
            if errors or popup:
                if len(failed) < _srv._BATCH_MAX_FAILURES_REPORTED:
                    failed.append({
                        "line": lineno,
                        "command": cmd,
                        "errors": [e.describe() for e in errors],
                        "pending_popup": popup,
                    })
                if popup or stop_on_error:
                    stopped_early = lineno < len(lines)
                    break

    result: dict = {
        "total": len(lines),
        "executed": executed,
        "failed": failed,
        "stopped_early": stopped_early,
        "duration_s": round(time.monotonic() - started, 2),
        "destructive_count": len(destructive),
        "last_reply": last_reply[-500:],
        "ok": not failed,
    }
    if failed:
        first = failed[0]
        result["error"] = (
            f"Line {first['line']} ('{first['command']}') failed: "
            + ("; ".join(first["errors"]) or "console is waiting on a pop-up — use answer_console_popup")
        )
    return json.dumps(result, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def answer_console_popup(
    choice: int,
    cancel_option: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Answer a console pop-up a previous tool reported as pending_popup.

    Pass the option number from pending_popup.options. Choosing the Cancel
    option is always allowed (give its number as cancel_option); any other
    answer can confirm an overwrite or delete and needs confirm_destructive=True.

    Args:
        choice: Option number to press (e.g. 1 for "Ok").
        cancel_option: The pop-up's Cancel option number, when known.
        confirm_destructive: Required for any answer other than Cancel.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if choice < 0 or choice > 9:
        return json.dumps({"error": "choice must be a single option number 0-9", "blocked": True}, indent=2)
    if choice != cancel_option and not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "risk_tier": "DESTRUCTIVE",
            "error": (
                "Answering a pop-up with anything but its Cancel option can confirm an "
                "overwrite or delete. Set confirm_destructive=True, or pass cancel_option."
            ),
        }, indent=2)

    client = await _srv.get_client()
    cmd = str(choice)
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_WRITE" if choice == cancel_option else "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SESSION_MANAGE)
@_handle_errors
async def disconnect_console() -> str:
    """
    Close this server's Telnet session(s) to the console.

    Use it to free the console for another Telnet client or to stop an idle
    session; the next tool call reconnects automatically with the current
    settings. Does not change any console state.

    Returns:
        str: JSON with sessions_closed.
    """
    manager = await _srv._get_session_manager()
    closed = await manager.release_all()
    return json.dumps({
        "sessions_closed": closed,
        "note": "Disconnected. The next tool call reconnects automatically.",
        "ok": True,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def navigate_console(
    destination: str,
    object_id: int | None = None,
) -> str:
    """
    Navigate the grandMA2 console's object tree using ChangeDest (cd).

    Sends a cd command and captures the raw telnet response, attempting
    to parse the resulting console prompt to determine the current
    location in the object tree.

    EXPLORATORY: The exact MA2 telnet prompt format is being validated.
    The raw_response field always contains the unmodified telnet output
    for manual inspection, regardless of whether parsing succeeded.

    Args:
        destination: Navigation target. Supported formats:
            - "/" to go to root
            - ".." to go up one level
            - A number (e.g., "5") to navigate by index
            - An object type (e.g., "Group") when object_id is provided
              (uses dot notation: cd Group.1)
            - A quoted name (e.g., '"MySequence"') to navigate by name
        object_id: Object ID, produces dot notation cd [type].[id]
            (e.g., destination="Group", object_id=1 → cd Group.1)

    Returns:
        str: JSON with command_sent, raw_response, parsed prompt details,
             and success indicator.

    Examples:
        - Navigate to root: destination="/"
        - Go up one level: destination=".."
        - Navigate to Group 1: destination="Group", object_id=1 → cd Group.1
        - Navigate by index: destination="5"
        - After navigating, use list_console_destination to enumerate objects
    """
    client = await _srv.get_client()
    result = await _srv.navigate(client, destination, object_id)

    return json.dumps(
        {
            "command_sent": result.command_sent,
            "raw_response": result.raw_response,
            "success": result.success,
            "parsed_prompt": {
                "prompt_line": result.parsed_prompt.prompt_line,
                "location": result.parsed_prompt.location,
                "object_type": result.parsed_prompt.object_type,
                "object_id": result.parsed_prompt.object_id,
            },
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_console_location() -> str:
    """
    Query the current grandMA2 console destination without navigating.

    Sends an empty command to prompt the console to re-display its
    prompt, then parses the response to determine the current location.

    Returns:
        str: JSON with raw_response, parsed prompt details,
             and success indicator.
    """
    client = await _srv.get_client()
    result = await _srv.get_current_location(client)

    return json.dumps(
        {
            "command_sent": result.command_sent,
            "raw_response": result.raw_response,
            "success": result.success,
            "parsed_prompt": {
                "prompt_line": result.parsed_prompt.prompt_line,
                "location": result.parsed_prompt.location,
                "object_type": result.parsed_prompt.object_type,
                "object_id": result.parsed_prompt.object_id,
            },
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_console_destination(
    object_type: str | None = None,
) -> str:
    """
    List objects at the current grandMA2 console destination.

    After navigating with cd (navigate_console), use this tool to
    enumerate children at the current location.  Parses the list
    feedback to extract object-type, object-id, and element names.

    Args:
        object_type: Optional filter (e.g., "cue", "group", "preset").
            If omitted, lists everything at the current destination.

    Returns:
        str: JSON with command_sent, raw_response, and parsed entries
             (each with object_type, object_id, name).
    """
    client = await _srv.get_client()
    result = await _srv.list_destination(client, object_type)

    entries_out = []
    for e in result.parsed_list.entries:
        entry = {
            "object_type": e.object_type,
            "object_id": e.object_id,
            "name": e.name,
            "raw_line": e.raw_line,
        }
        if e.col3 is not None:
            entry["col3"] = e.col3
        if e.columns:
            entry["columns"] = e.columns
        entries_out.append(entry)

    return json.dumps(
        {
            "command_sent": result.command_sent,
            "raw_response": result.raw_response,
            "entries": entries_out,
            "entry_count": len(result.parsed_list.entries),
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def scan_console_indexes(
    reset_to: str = "/",
    max_index: int = 50,
    stop_after_failures: int = 3,
) -> str:
    """
    Scan numeric indexes via cd N → list → cd <reset_to>.

    For each index N from 1 to max_index:
      1. cd N           — navigate into that index
      2. list           — enumerate children there
      3. cd <reset_to>  — return to the base location for the next iteration

    The reset_to destination controls what each cd N is relative to:
      - "/"          (default) scan root-level indexes (Showfile, TimeConfig, …)
      - "Sequence"   reset to Sequence pool → cd N enters Sequence N → list shows its cues
      - "Group"      reset to Group pool → cd N enters Group N

    Stops early after stop_after_failures consecutive indexes with no entries.

    Args:
        reset_to: Where to navigate after each list before the next cd N (default "/").
        max_index: Highest index to try (default 50).
        stop_after_failures: Stop after this many consecutive empty indexes (default 3).

    Returns:
        str: JSON with a list of scan results — one entry per index that
             returned list output, each with index, location, object_type,
             and parsed entries (object_type, object_id, name).
    """
    client = await _srv.get_client()
    results = await scan_indexes(
        client,
        reset_to=reset_to,
        max_index=max_index,
        stop_after_failures=stop_after_failures,
    )

    return json.dumps(
        {
            "scanned_count": len(results),
            "results": [
                {
                    "index": r.index,
                    "location": r.location,
                    "object_type": r.object_type,
                    "entry_count": len(r.entries),
                    "entries": [
                        {
                            "object_type": e.object_type,
                            "object_id": e.object_id,
                            "name": e.name,
                        }
                        for e in r.entries
                    ],
                }
                for r in results
            ],
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def set_node_property(
    path: str,
    property_name: str,
    value: str,
    verify: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """
    Set a property on a node in the grandMA2 object tree (DESTRUCTIVE).

    Uses the scan tree path notation (dot-separated indexes) to navigate
    to a node and set an inline property using Assign [index]/property=value.

    The path uses the same index-based notation as the scan tree output.
    Split the path into parent segments and target index:
    - "3.1" → cd 3 (Settings), then Assign 1/property=value (on Global)
    - "4.1" → cd 4 (DMX_Protocols), then Assign 1/property=value (on Art-Net)
    - "3" → at root, Assign 3/property=value (on Settings itself)

    After setting, navigates back to root (cd /).
    If verify=True (default), re-lists and confirms the property changed.

    SAFETY: This modifies live console state. Requires confirm_destructive=True.

    Args:
        path: Dot-separated index path (e.g. "3.1" for Settings/Global)
        property_name: Property to set (e.g. "Telnet", "OutActive")
        value: New value (e.g. "Login Enabled", "On")
        verify: Re-list after setting to confirm the change (default True)
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: JSON with commands_sent, success, verified_value, and any errors.

    Examples:
        - Set telnet to disabled: path="3.1", property_name="Telnet", value="Login Disabled"
        - Enable Art-Net output: path="4.1", property_name="OutActive", value="On"
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Set Node Property uses Assign (DESTRUCTIVE). Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()
    result = await _srv.set_property(
        client,
        path,
        property_name,
        value,
        verify=verify,
    )

    return json.dumps(
        {
            "path": result.path,
            "property_name": property_name,
            "value": value,
            "commands_sent": result.commands_sent,
            "success": result.success,
            "verified_value": result.verified_value,
            "error": result.error,
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def set_intensity(
    target_type: str,
    target_id: int,
    level: int | float,
    end_id: int | None = None,
) -> str:
    """
    Set the intensity (dimmer) level on fixtures, groups, or channels.

    This is the most fundamental lighting operation — controlling how bright
    lights are. Selects the target and sets it to the specified percentage.

    Args:
        target_type: Object type — "fixture", "group", or "channel"
        target_id: Object ID number
        level: Intensity percentage (0-100). Use 0 for off, 100 for full.
        end_id: End ID for range selection (e.g., fixture 1 thru 10)

    Returns:
        str: JSON with command_sent and raw_response from the console.

    Examples:
        - Set fixture 1 to 50%: target_type="fixture", target_id=1, level=50
        - Set group 3 to full: target_type="group", target_id=3, level=100
        - Set fixtures 1-10 to 75%: target_type="fixture", target_id=1, level=75, end_id=10
    """
    target_type = target_type.lower()

    if target_type == "fixture":
        cmd = fixture_at(target_id, level, end=end_id)
    elif target_type == "group":
        cmd = group_at(target_id, level)
    elif target_type == "channel":
        cmd = channel_at(target_id, level, end=end_id)
    else:
        return json.dumps({
            "error": f"Unknown target_type: {target_type}. Use 'fixture', 'group', or 'channel'.",
            "blocked": True,
        }, indent=2)

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def apply_preset(
    preset_type: str,
    preset_id: int,
    fixture_id: int | None = None,
    fixture_end: int | None = None,
    group_id: int | None = None,
) -> str:
    """
    Apply a preset to fixtures or groups.

    Presets are stored lighting looks (color, position, gobo, etc.) that
    can be recalled by type and ID. Optionally select fixtures/group first.

    Preset types: "dimmer" (1), "position" (2), "gobo" (3), "color" (4),
    "beam" (5), "focus" (6), "control" (7), "shapers" (8), "video" (9)

    Args:
        preset_type: Preset type name or number (e.g. "color", "position", "4")
        preset_id: Preset number within that type
        fixture_id: Optional fixture to select first (single or range start)
        fixture_end: Optional end fixture for range selection
        group_id: Optional group to select first (alternative to fixture_id)

    Returns:
        str: JSON with commands_sent and raw_response.

    Examples:
        - Apply color preset 3 to current selection: preset_type="color", preset_id=3
        - Apply position preset 1 to group 2: preset_type="position", preset_id=1, group_id=2
        - Apply gobo preset 5 to fixtures 1-10: preset_type="gobo", preset_id=5, fixture_id=1, fixture_end=10
    """
    commands_sent = []
    client = await _srv.get_client()

    # Optionally select fixtures or group first
    if group_id is not None:
        sel_cmd = f"group {group_id}"
        await client.send_command_with_response(sel_cmd)
        commands_sent.append(sel_cmd)
    elif fixture_id is not None:
        sel_cmd = select_fixture(fixture_id, fixture_end)
        await client.send_command_with_response(sel_cmd)
        commands_sent.append(sel_cmd)

    # Build the preset type reference
    preset_type_str = preset_type.lower()
    # Map common names to numbers for the call syntax
    type_map = {
        "dimmer": "1", "position": "2", "gobo": "3", "color": "4",
        "beam": "5", "focus": "6", "control": "7", "shapers": "8", "video": "9",
    }
    type_num = type_map.get(preset_type_str, preset_type_str)

    call_cmd = call(f"preset {type_num}.{preset_id}")
    raw_response = await client.send_command_with_response(call_cmd)
    commands_sent.append(call_cmd)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def store_current_cue(
    cue_number: int,
    sequence_id: int | None = None,
    label: str | None = None,
    merge: bool = False,
    overwrite: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Store the current programmer state as a cue (DESTRUCTIVE).

    Saves whatever is currently in the programmer (selected fixtures +
    active values) into a cue in the specified sequence. This is how
    lighting looks are programmed into a show.

    Executor-sequence relationship:
      When sequence_id is omitted, MA2 stores into the sequence assigned to
      the currently selected executor on the console. Use select_executor()
      first to set the target, or pass sequence_id explicitly to make the
      destination unambiguous regardless of executor selection state.

      select executor N      → sets executor N as the active store target
      Store Cue M            → stores into the sequence on selected executor
      Store Cue M Sequence S → stores into sequence S directly (preferred)

    Args:
        cue_number: Cue number to store (required)
        sequence_id: Sequence to store into. Omit to use the selected executor's
                     sequence (call select_executor() first if needed)
        label: Optional name for the cue
        merge: Merge new values into existing cue (default False)
        overwrite: Replace existing cue completely (default False)
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: JSON with commands_sent and raw_response.

    Examples:
        - Store cue 5 (explicit sequence): cue_number=5, sequence_id=1, confirm_destructive=True
        - Store cue 3 named "Opening Look": cue_number=3, label="Opening Look", confirm_destructive=True
        - Merge into cue 1: cue_number=1, merge=True, confirm_destructive=True
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": (
                "Store Cue is a DESTRUCTIVE operation. Pass confirm_destructive=True to proceed. "
                "Tip: pass sequence_id explicitly to target a specific sequence rather than relying "
                "on the currently selected executor."
            ),
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    commands_sent = []
    client = await _srv.get_client()

    # Build store cue command
    store_cmd = build_store_cue(
        cue_id=cue_number,
        sequence_id=sequence_id,
        merge=merge,
        overwrite=overwrite,
    )

    raw_response = await client.send_command_with_response(store_cmd)
    commands_sent.append(store_cmd)

    # Optionally label the cue
    if label and cue_number is not None:
        cue_ref = str(cue_number)
        if sequence_id is not None:
            cue_ref += f" sequence {sequence_id}"
        label_cmd = build_label("cue", cue_ref, label)
        await client.send_command_with_response(label_cmd)
        commands_sent.append(label_cmd)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_object_info(
    object_type: str,
    object_id: int | str,
) -> str:
    """
    Query information about any object in the show.

    Returns the console's info response for the specified object,
    which includes its properties, status, and metadata.

    Args:
        object_type: Object type (e.g. "fixture", "group", "cue",
            "sequence", "preset", "executor", "macro")
        object_id: Object ID. For presets use "type.id" format
            (e.g. "2.1" for color preset 1).

    Returns:
        str: JSON with command_sent and raw_response containing
            the object's information.

    Examples:
        - Get info on group 3: object_type="group", object_id=3
        - Get info on cue 5: object_type="cue", object_id=5
        - Get info on color preset 1: object_type="preset", object_id="2.1"
    """
    cmd = build_info(object_type, object_id)

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def clear_programmer(
    mode: str = "all",
) -> str:
    """
    Clear the programmer to reset fixture selection and active values.

    The programmer holds the current working state — selected fixtures
    and any values you've applied. Clearing it gives you a clean slate.

    Modes:
    - "all": Empty the entire programmer (selection + values)
    - "selection": Deselect all fixtures but keep active values
    - "active": Deactivate values but keep fixture selection
    - "clear": Sequential clear (selection → active → all on repeated calls)

    Args:
        mode: Clear mode — "all" (default), "selection", "active", or "clear"

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - Full reset: mode="all"
        - Just deselect fixtures: mode="selection"
        - Just drop active values: mode="active"
    """
    mode = mode.lower()
    if mode == "all":
        cmd = build_clear_all()
    elif mode == "selection":
        cmd = build_clear_selection()
    elif mode == "active":
        cmd = build_clear_active()
    elif mode == "clear":
        cmd = build_clear()
    else:
        return json.dumps({
            "error": f"Unknown mode: {mode}. Use 'all', 'selection', 'active', or 'clear'.",
            "blocked": True,
        }, indent=2)

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def set_attribute(
    attribute_name: str,
    value: int | float,
    fixture_id: int | None = None,
    fixture_end: int | None = None,
    group_id: int | None = None,
) -> str:
    """
    Set a specific fixture attribute (Pan, Tilt, Zoom, etc.) to a value.

    Controls individual fixture parameters beyond simple dimmer intensity.
    Optionally select fixtures/group first.

    Args:
        attribute_name: Attribute name (e.g. "Pan", "Tilt", "Zoom", "Focus", "Iris")
        value: Attribute value (typically 0-100 for percentage, or degrees for Pan/Tilt)
        fixture_id: Optional fixture to select first (single or range start)
        fixture_end: Optional end fixture for range selection
        group_id: Optional group to select first

    Returns:
        str: JSON with commands_sent and raw_response.

    Examples:
        - Set Pan to 120: attribute_name="Pan", value=120
        - Set Tilt to 50 on group 2: attribute_name="Tilt", value=50, group_id=2
        - Set Zoom on fixtures 1-10: attribute_name="Zoom", value=80, fixture_id=1, fixture_end=10
    """
    commands_sent = []
    client = await _srv.get_client()

    # Optionally select fixtures or group first
    if group_id is not None:
        sel_cmd = f"group {group_id}"
        await client.send_command_with_response(sel_cmd)
        commands_sent.append(sel_cmd)
    elif fixture_id is not None:
        sel_cmd = select_fixture(fixture_id, fixture_end)
        await client.send_command_with_response(sel_cmd)
        commands_sent.append(sel_cmd)

    cmd = attribute_at(attribute_name, value)
    raw_response = await client.send_command_with_response(cmd)
    commands_sent.append(cmd)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PRESET_UPDATE)
@_handle_errors
async def park_fixture(
    target: str,
    value: int | float | None = None,
) -> str:
    """
    Park a fixture or DMX address at its current or specified output value.

    Parking locks the output so it won't change when cues or programmer
    values change. Useful for testing, worklights, or safety overrides.

    Fixture targets are pre-validated: if the fixture does not exist on the
    console, the command is not sent and an informative error is returned.
    DMX targets (e.g. "dmx 101") bypass pre-validation.

    Args:
        target: What to park (e.g. "fixture 20", "dmx 101", "fixture 20 thru 30")
        value: Optional output value to park at (0-255 for DMX, 0-100 for %)

    Returns:
        str: JSON with command_sent (None if blocked), raw_response, exists.

    Examples:
        - Park fixture 20 at current output: target="fixture 20"
        - Park DMX 101 at 128: target="dmx 101", value=128
        - Park fixture range: target="fixture 20 thru 30"
    """
    client = await _srv.get_client()

    fixture_match = re.match(r"^fixture\s+(\d+)", target.strip(), re.IGNORECASE)
    if fixture_match:
        fixture_id = fixture_match.group(1)
        exists, probe_raw = await _validate_object_exists(client, "fixture", fixture_id)
        if not exists:
            return json.dumps({
                "command_sent": None,
                "exists": False,
                "error": f"Fixture {fixture_id} does not exist on the console.",
                "hint": "Use list_fixtures() to discover valid fixture IDs.",
                "probe_response": probe_raw,
                "blocked": True,
            }, indent=2)
        exists_flag: bool | None = True
    else:
        exists_flag = None  # DMX or other — validation skipped

    cmd = build_park(target, at=value)
    raw_response = await client.send_command_with_response(cmd)

    # Sync park ledger to snapshot write-tracker (Gap 3)
    if snap := _srv._orchestrator.last_snapshot:
        snap.parked_fixtures.add(str(target))

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "exists": exists_flag,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PRESET_UPDATE)
@_handle_errors
async def unpark_fixture(
    target: str,
) -> str:
    """
    Unpark a previously parked fixture or DMX address.

    Fixture targets are pre-validated before unparking. DMX targets bypass
    pre-validation.

    Args:
        target: What to unpark (e.g. "fixture 20", "dmx 101", "fixture 20 thru 30")

    Returns:
        str: JSON with command_sent (None if blocked), raw_response, exists.

    Examples:
        - Unpark fixture 20: target="fixture 20"
        - Unpark DMX 101: target="dmx 101"
    """
    client = await _srv.get_client()

    fixture_match = re.match(r"^fixture\s+(\d+)", target.strip(), re.IGNORECASE)
    if fixture_match:
        fixture_id = fixture_match.group(1)
        exists, probe_raw = await _validate_object_exists(client, "fixture", fixture_id)
        if not exists:
            return json.dumps({
                "command_sent": None,
                "exists": False,
                "error": f"Fixture {fixture_id} does not exist on the console.",
                "hint": "Use list_fixtures() to discover valid fixture IDs.",
                "probe_response": probe_raw,
                "blocked": True,
            }, indent=2)
        exists_flag: bool | None = True
    else:
        exists_flag = None

    cmd = build_unpark(target)
    raw_response = await client.send_command_with_response(cmd)

    # Sync park ledger to snapshot write-tracker (Gap 3)
    if snap := _srv._orchestrator.last_snapshot:
        snap.parked_fixtures.discard(str(target))

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "exists": exists_flag,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def run_macro(
    macro_id: int,
) -> str:
    """
    Execute a macro by its ID number.

    Macros are stored command sequences on the console. This triggers
    the macro to run.

    Args:
        macro_id: Macro number to execute

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - Run macro 1: macro_id=1
        - Run macro 99: macro_id=99
    """
    client = await _srv.get_client()
    cmd = go_macro(macro_id)
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def delete_object(
    object_type: str,
    object_id: int | str,
    end_id: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Delete an object from the show.

    SAFETY: This is a DESTRUCTIVE operation. Requires confirm_destructive=True.

    Args:
        object_type: Object type (e.g. "cue", "group", "preset", "fixture", "macro")
        object_id: Object ID to delete
        end_id: Optional end ID for range deletion (e.g. cue 1 thru 10)
        confirm_destructive: Must be True to execute (safety gate)

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Delete cue 5: object_type="cue", object_id=5, confirm_destructive=True
        - Delete cues 1-10: object_type="cue", object_id=1, end_id=10, confirm_destructive=True
        - Delete group 3: object_type="group", object_id=3, confirm_destructive=True
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": "Delete is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    if object_type.lower() == "cue":
        cmd = build_delete_cue(object_id, end=end_id, noconfirm=True)
    else:
        cmd = build_delete(object_type, object_id, end=end_id, noconfirm=True)

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def copy_or_move_object(
    action: str,
    object_type: str,
    source_id: int,
    target_id: int,
    source_end: int | None = None,
    overwrite: bool = False,
    merge: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Copy or move an object to a new location (DESTRUCTIVE).

    SAFETY: Both operations modify show data. Copy duplicates the object,
    move relocates it (deleting the original). Requires confirm_destructive=True.

    Args:
        action: "copy" or "move"
        object_type: Object type (e.g. "group", "cue", "preset", "macro")
        source_id: Source object ID
        target_id: Destination object ID
        source_end: Optional end ID for range copy/move
        overwrite: Overwrite target if it exists (default False)
        merge: Merge into target if it exists (default False)
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - Copy group 1 to 5: action="copy", object_type="group", source_id=1, target_id=5
        - Move macro 3 to 10: action="move", object_type="macro", source_id=3, target_id=10
        - Copy cue range: action="copy", object_type="cue", source_id=1, target_id=20, source_end=10
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Copy/Move is a DESTRUCTIVE operation. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    action = action.lower()

    if action == "copy":
        cmd = build_copy(
            object_type, source_id, target_id,
            end=source_end, overwrite=overwrite, merge=merge,
        )
    elif action == "move":
        cmd = build_move(
            object_type, source_id, target_id,
            end=source_end,
        )
    else:
        return json.dumps({
            "error": f"Unknown action: {action}. Use 'copy' or 'move'.",
            "blocked": True,
        }, indent=2)

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PRESET_UPDATE)
@_handle_errors
async def store_new_preset(
    preset_type: str,
    preset_id: int,
    merge: bool = False,
    overwrite: bool = False,
    universal: bool = False,
    selective: bool = False,
    global_scope: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Store the current programmer values as a preset.

    Saves the active fixture values (from the programmer) into a preset
    slot for later recall with apply_preset.

    Preset types: "dimmer" (1), "position" (2), "gobo" (3), "color" (4),
    "beam" (5), "focus" (6), "control" (7), "shapers" (8), "video" (9)

    Scope flags (mutually exclusive — pick at most one):
      universal   — stores values indexed by fixture type (applies to any fixture
                    of the same profile; not tied to specific fixture IDs).
      selective   — stores values tied to the specific fixtures selected during
                    store. Recalled preset only affects those fixture IDs.
      global_scope — stores absolute values (no relative/tracking offset).

    Workflow for universal color presets:
      1. SelFix 1 Thru 999
      2. attribute "ColorRgb1" at 100
      3. store_new_preset("color", 6, universal=True, overwrite=True, confirm_destructive=True)

    SAFETY: This is a STORE operation which modifies show data.

    Args:
        preset_type: Preset type name (e.g. "color", "position", "gobo")
        preset_id: Preset number within that type
        merge: Merge into existing preset (default False)
        overwrite: Replace existing preset with /overwrite flag (default False)
        universal: Store as universal preset — applies to any fixture of the same type
        selective: Store as selective preset — applies only to selected fixture IDs
        global_scope: Store with global (absolute) values
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - Store universal color preset: preset_type="color", preset_id=6, universal=True, confirm_destructive=True
        - Overwrite position preset 3: preset_type="position", preset_id=3, overwrite=True, confirm_destructive=True
    """
    if not confirm_destructive:
        return json.dumps({
            "error": "Store Preset is a DESTRUCTIVE operation. Pass confirm_destructive=True to proceed."
        }, indent=2)
    client = await _srv.get_client()
    cmd = build_store_preset(
        preset_type, preset_id,
        merge=merge, overwrite=overwrite,
        universal=universal, selective=selective,
        global_scope=global_scope,
    )
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)
