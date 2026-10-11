"""MCP tools — show files. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    store_cue_timed as build_store_cue_timed,
)
from src.server import (
    _handle_errors,
    mcp,
)
from src.telnet_client import hold_connection

# ============================================================
# New Tools (Tools 45–52) — Quick Start Guide Gap-Fill
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def save_show(
    action: str = "save",
    show_name: str | None = None,
) -> str:
    """
    Save the current show file to disk.

    Args:
        action: "save" (overwrite current) or "saveas" (save under a new name).
            Giving show_name implies "saveas".
        show_name: Show name (required for action="saveas")

    Returns:
        str: JSON result with command sent. Saving over an existing file may
            open an overwrite pop-up — reported as pending_popup.
    """
    from src.commands.functions.store import save_show as build_save_show

    if action not in ("save", "saveas"):
        return json.dumps({"error": "action must be 'save' or 'saveas'", "blocked": True}, indent=2)
    if action == "saveas" and not show_name:
        return json.dumps({"error": "show_name is required for action='saveas'", "blocked": True}, indent=2)

    client = await _srv.get_client()
    # SaveShow is the real keyword; "saveas" is UNKNOWN COMMAND on the console.
    cmd = build_save_show(show_name or None)
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def store_cue_with_timing(
    cue_id: int,
    confirm_destructive: bool = False,
    fade_time: float | None = None,
    out_time: float | None = None,
    merge: bool = False,
    overwrite: bool = False,
    cue_name: str | None = None,
    sequence_id: int | None = None,
) -> str:
    """
    Store a cue with inline fade and outtime parameters (DESTRUCTIVE).

    When sequence_id is omitted, MA2 stores into the sequence on the currently
    selected executor. Pass sequence_id explicitly to target a specific sequence
    regardless of executor selection state (same behavior as store_current_cue).

    Args:
        cue_id: Cue number to store
        confirm_destructive: Must be True to execute
        fade_time: Fade-in time in seconds (optional)
        out_time: Fade-out time in seconds (optional)
        merge: Merge into existing cue
        overwrite: Overwrite existing cue
        cue_name: Optional cue label
        sequence_id: Sequence to store into (omit to use selected executor)

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()
    cmd = build_store_cue_timed(
        cue_id,
        name=cue_name,
        fade_time=fade_time,
        out_time=out_time,
        merge=merge,
        overwrite=overwrite,
    )
    if sequence_id is not None:
        cmd += f" sequence {sequence_id}"
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def select_executor(
    executor_id: int,
    page: int | None = None,
    deselect: bool = False,
) -> str:
    """
    Select an executor on the console.

    IMPORTANT: MA2 telnet 'select executor N' is single-selection only — there
    is no list syntax. You cannot select multiple executors simultaneously via
    this command. Pass only a single executor_id integer.

    After sending the command, $SELECTEDEXEC is read back to confirm the
    selection took effect. A 'warning' field is included in the response if
    the confirmed value does not match the requested executor_id.

    To clear the current selection, pass deselect=True. This sends a bare
    'select' command with no argument. NOTE: bare 'select' behaviour is
    unverified on grandMA2 telnet — it may clear selection, be silently
    ignored, or produce an error. Inspect 'raw_response' to confirm.

    Args:
        executor_id: Executor number (1-999). Single value only.
        page: Page number for page-qualified addressing (optional).
              e.g. page=2, executor_id=5 → 'select executor 2.5'.
              $SELECTEDEXEC returns the executor number only (not page-qualified).
        deselect: If True, send bare 'select' to clear the current selection
                  instead of selecting executor_id. Defaults to False.

    Returns:
        str: JSON with command_sent, raw_response, confirmed_selected_exec,
             and risk_tier. Includes 'warning' if confirmed value doesn't match.
    """
    client = await _srv.get_client()

    if deselect:
        cmd = "select"
        response = await client.send_command_with_response(cmd)
        listvar_raw = await client.send_command_with_response("ListVar")
        confirmed = _srv._parse_listvar(listvar_raw).get("$SELECTEDEXEC")
        return json.dumps({
            "command_sent": cmd,
            "raw_response": response,
            "confirmed_selected_exec": confirmed,
            "note": "Bare 'select' sent to clear selection. Behaviour unverified on grandMA2 telnet.",
            "risk_tier": "SAFE_WRITE",
        }, indent=2)

    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    cmd = f"select executor {ref}"
    response = await client.send_command_with_response(cmd)

    listvar_raw = await client.send_command_with_response("ListVar")
    variables = _srv._parse_listvar(listvar_raw)
    confirmed = variables.get("$SELECTEDEXEC")

    result: dict = {
        "command_sent": cmd,
        "raw_response": response,
        "confirmed_selected_exec": confirmed,
        "risk_tier": "SAFE_WRITE",
    }
    # $SELECTEDEXEC stores executor number only (not page-qualified)
    if confirmed is None or confirmed.strip() != str(executor_id):
        result["warning"] = (
            f"$SELECTEDEXEC is '{confirmed}' after command but expected '{executor_id}'. "
            "The selection may not have taken effect."
        )
    return json.dumps(result, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def remove_from_programmer(
    object_type: str,
    object_id: int,
    end_id: int | None = None,
) -> str:
    """
    Remove channels, fixtures, or a group from the programmer using Off.

    Args:
        object_type: "channel", "fixture", or "group"
        object_id: Object ID to remove
        end_id: End of range for channel/fixture (optional; builds thru N)

    Returns:
        str: JSON result with command sent
    """
    if object_type not in ("channel", "fixture", "group"):
        return json.dumps(
            {"error": "object_type must be 'channel', 'fixture', or 'group'", "blocked": True},
            indent=2,
        )
    if end_id is not None and object_type != "group":
        cmd = f"off {object_type} {object_id} thru {end_id}"
    else:
        cmd = f"off {object_type} {object_id}"

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def assign_cue_trigger(
    cue_id: int,
    sequence_id: int,
    trigger_type: str,
    confirm_destructive: bool = False,
    trigger_value: float | None = None,
) -> str:
    """
    Assign a playback trigger type to a cue (DESTRUCTIVE).

    Args:
        cue_id: Cue number to assign the trigger to
        sequence_id: Sequence containing the cue
        trigger_type: "go", "follow", "time", or "bpm"
        confirm_destructive: Must be True to execute
        trigger_value: BPM or time value (required for "bpm" and "time")

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    valid = ("go", "follow", "time", "bpm")
    if trigger_type not in valid:
        return json.dumps({"error": f"trigger_type must be one of {valid}", "blocked": True}, indent=2)
    if trigger_type in ("bpm", "time") and trigger_value is None:
        return json.dumps(
            {"error": f"trigger_value is required for trigger_type='{trigger_type}'", "blocked": True},
            indent=2,
        )

    if trigger_type == "bpm":
        cmd = f"assign trigger bpm {trigger_value} cue {cue_id} sequence {sequence_id}"
    elif trigger_type == "time":
        cmd = f"assign trigger time {trigger_value} cue {cue_id} sequence {sequence_id}"
    else:
        cmd = f"assign trigger {trigger_type} cue {cue_id} sequence {sequence_id}"

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def assign_executor_property(
    executor_id: int,
    option: str,
    value: str | int,
    confirm_destructive: bool = False,
    page: int = 1,
) -> str:
    """
    Assign any of the 22 settable options to an executor (DESTRUCTIVE).

    Always uses page-qualified addressing (page.executor_id) to avoid Error #66.

    Valid options (case-sensitive):
      Layout:   width (1-5)
      Priority: priority (low|normal|high|htp|swap|super)
      Start:    autostart, autostop, autofix, autostomp, restart
      Protect:  ooo, swopprotect, killprotect
      Playback: softltp, wrap, crossfade (off|a|b|ab — requires width>=2), chaser
      Timing:   triggerisgo, cmddisable, effectspeed, autogo
      Speed:    speed (0-65535 BPM), speedmaster (speed_individual|speed1-16),
                ratemaster (rate_individual|rate1-16)

    Args:
        executor_id: Executor ID (e.g. 203).
        option: Option name from the list above.
        value: Value to assign (e.g. 2, "on", "high", "speed1").
        confirm_destructive: Must be True to execute.
        page: Page number (default 1). Always included in the address.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from src.commands import build_assign_executor_option as _build_opt
    try:
        cmd = _build_opt(executor_id, option, value, page=page)
    except ValueError as exc:
        return json.dumps({"error": str(exc), "blocked": True}, indent=2)

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def set_executor_priority(
    executor_id: int,
    priority: str,
    page: int = 1,
) -> str:
    """
    Set the playback priority of an executor (Tool 130).

    Priority determines how this executor interacts with other active executors
    and the programmer. Uses page-qualified addressing (page.executor_id) to
    avoid Error #66 CANNOT ASSIGN.

    Priority levels (highest → lowest):
      - "super"  — LTP above ALL playbacks + programmer. Only Freeze overrides.
      - "swap"   — LTP > HTP; negative override possible. Affects ALL attributes.
      - "htp"    — Highest intensity value wins. Changes ALL attribute priority.
      - "high"   — High LTP. Overrides Normal/Low but not HTP intensity.
      - "normal" — LTP default. Last triggered value wins.
      - "low"    — Lowest priority. Overridden by everything else.

    Args:
        executor_id: The executor to modify (e.g. 201).
        priority: One of "super", "swap", "htp", "high", "normal", "low".
        page: Page number (default 1). Always included in the address.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    from src.commands import build_set_executor_priority as _build_prio
    try:
        cmd = _build_prio(executor_id, priority, page=page)
    except ValueError as exc:
        return json.dumps({"error": str(exc), "blocked": True}, indent=2)

    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)

    # Sync priority to snapshot write-tracker (Gap 10)
    if (snap := _srv._orchestrator.last_snapshot) and executor_id in snap.executor_state:
        snap.executor_state[executor_id].priority = priority

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_executor_state(
    executor_id: int,
    page: int = 1,
) -> str:
    """
    Read all 32 fields of a single executor via 'List Executor page.id' (SAFE_READ).

    Returns all KEY=VALUE fields including Width, Priority, AutoStart, AutoStop,
    Crossfade, SpeedMaster, RateMaster, Filter, PlaybackMaster, etc.

    Must use page-qualified addressing — bare executor IDs return wrong data.

    Args:
        executor_id: Executor ID (e.g. 203).
        page: Page number (default 1).

    Returns:
        str: JSON with fields dict, command_sent, raw_response.
    """
    from src.prompt_parser import parse_executor_list
    cmd = f"List Executor {page}.{executor_id}"
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    fields = parse_executor_list(raw)
    return json.dumps({
        "command_sent": cmd,
        "fields": fields,
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def discover_fixture_type_attributes(
    fixture_type_id: int,
) -> str:
    """
    Discover attribute names for a fixture type via EditSetup tree navigation (SAFE_READ).

    Navigates cd EditSetup → FixtureTypes → type N → first mode → first subfixture → list,
    returning ChannelType rows with attribute library names (e.g. PAN, TILT, COLORRGB1).

    Use this to confirm which attributes a fixture type exposes before building presets.
    Note: Info FixtureType N does NOT return attribute names — this navigation method is
    the correct approach (live-verified 2026-03-31).

    Args:
        fixture_type_id: Fixture type number (e.g. 4 for Mac Viper Profile 16-bit).

    Returns:
        str: JSON with raw_response containing ChannelType rows.
    """
    client = await _srv.get_client()

    async def send(cmd: str) -> str:
        return await client.send_command_with_response(cmd)

    # One uninterrupted cd sequence — a parallel call must not land mid-path.
    async with hold_connection(client):
        await send("cd /")
        await send("cd EditSetup")
        await send("cd FixtureTypes")
        await send(f"cd {fixture_type_id}")
        await send("cd 1")  # first mode
        await send("cd 1")  # first subfixture
        raw = await send("list")
        await send("cd /")  # return to root

    return json.dumps({
        "fixture_type_id": fixture_type_id,
        "navigation": f"EditSetup → FixtureTypes → {fixture_type_id} → 1 → 1 → list",
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def scan_page_executor_layout(
    page: int = 1,
    executor_id_start: int = 201,
    executor_id_end: int = 240,
) -> str:
    """
    Scan a range of executors on a page and return their slot occupancy map (SAFE_READ).

    Queries each executor in the range via 'List Executor page.id' (KEY=VALUE format),
    extracts Name, Sequence, and Width. Builds an occupancy map showing which consecutive
    slots are blocked by wide executors, and lists free slots.

    Use this BEFORE setting width on an executor to confirm the adjacent slot is free.
    A width=2 executor at slot N blocks slot N+1; the console will silently fail or wrap
    if N+1 is already occupied.

    Args:
        page: Page number to scan (default 1).
        executor_id_start: First executor ID to check (default 201).
        executor_id_end: Last executor ID to check (default 240).

    Returns:
        str: JSON with:
          - executors: list of {id, name, sequence, width, slots_occupied}
          - blocked_slots: set of slot IDs consumed by multi-wide executors
          - free_slots: slot IDs in range with no assignment
    """
    import asyncio

    from src.prompt_parser import parse_executor_list

    client = await _srv.get_client()
    executor_data: list[dict] = []
    occupied_slots: set[int] = set()

    for exec_id in range(executor_id_start, executor_id_end + 1):
        cmd = f"List Executor {page}.{exec_id}"
        raw = await client.send_command_with_response(cmd)
        fields = parse_executor_list(raw)

        # Skip unassigned slots — no Name and no Sequence
        if not fields.get("Name") and not fields.get("Sequence"):
            continue

        width = int(fields.get("Width", 1))
        name = fields.get("Name", "")
        sequence = fields.get("Sequence", "")
        slots = list(range(exec_id, exec_id + width))

        executor_data.append({
            "id": exec_id,
            "name": name,
            "sequence": sequence,
            "width": width,
            "slots_occupied": slots,
        })
        for s in slots:
            occupied_slots.add(s)

        await asyncio.sleep(0.1)  # avoid flooding telnet

    all_slots = set(range(executor_id_start, executor_id_end + 1))
    free_slots = sorted(all_slots - occupied_slots)

    return json.dumps({
        "page": page,
        "scanned_range": [executor_id_start, executor_id_end],
        "executors": executor_data,
        "occupied_slots": sorted(occupied_slots),
        "free_slots": free_slots,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def if_filter(
    filter_type: str,
    fixture_id: int | None = None,
    attribute_name: str | None = None,
) -> str:
    """
    Apply an If filter to the current selection or command context.

    Args:
        filter_type: "active" (bare 'if'), "fixture" (specific fixture), or "attribute"
        fixture_id: Fixture ID (required for "fixture" and "attribute")
        attribute_name: Attribute name (required for "attribute"; e.g. "Pan")

    Returns:
        str: JSON result with command sent
    """
    if filter_type not in ("active", "fixture", "attribute"):
        return json.dumps(
            {"error": "filter_type must be 'active', 'fixture', or 'attribute'", "blocked": True},
            indent=2,
        )
    if filter_type in ("fixture", "attribute") and fixture_id is None:
        return json.dumps(
            {"error": "fixture_id is required for filter_type != 'active'", "blocked": True},
            indent=2,
        )
    if filter_type == "attribute" and attribute_name is None:
        return json.dumps(
            {"error": "attribute_name is required for filter_type='attribute'", "blocked": True},
            indent=2,
        )

    if filter_type == "active":
        cmd = "if"
    elif filter_type == "fixture":
        cmd = f"if fixture {fixture_id}"
    else:
        cmd = f'if fixture {fixture_id} attribute "{attribute_name}"'

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def save_recall_view(
    action: str,
    view_id: int,
    screen_id: int = 1,
    view_name: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Store, recall, or label a screen view (store is DESTRUCTIVE).

    Args:
        action: "store" (save current screen), "recall" (load view), or "label" (name it)
        view_id: View slot ID (1-10)
        screen_id: Screen number (1-4, default 1)
        view_name: Label for the view (required for action="label")
        confirm_destructive: Must be True for action="store"

    Returns:
        str: JSON result with command sent
    """
    if action not in ("store", "recall", "label"):
        return json.dumps(
            {"error": "action must be 'store', 'recall', or 'label'", "blocked": True},
            indent=2,
        )
    if not (1 <= view_id <= 10):
        return json.dumps({"error": "view_id must be between 1 and 10", "blocked": True}, indent=2)
    if not (1 <= screen_id <= 4):
        return json.dumps({"error": "screen_id must be between 1 and 4", "blocked": True}, indent=2)
    if action == "store" and not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)
    if action == "label" and not view_name:
        return json.dumps(
            {"error": "view_name is required for action='label'", "blocked": True},
            indent=2,
        )

    ref = f"{screen_id}.{view_id}"
    if action == "store":
        cmd = f"store ViewButton {ref}"
        risk_tier = "DESTRUCTIVE"
    elif action == "recall":
        cmd = f"ViewButton {ref}"
        risk_tier = "SAFE_WRITE"
    else:
        cmd = f'label ViewButton {ref} "{view_name}"'
        risk_tier = "SAFE_WRITE"

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk_tier,
    }, indent=2)
