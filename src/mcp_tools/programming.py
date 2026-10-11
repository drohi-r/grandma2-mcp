"""MCP tools — programming. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, has_scope, require_scope
from src.commands import (
    add_to_selection as build_add_to_selection,
    align as build_align,
    assign_delay as build_assign_delay,
    assign_fade as build_assign_fade,
    at_relative as build_at_relative,
    block as build_block,
    clear_selection as build_clear_selection,
    clone as build_clone,
    cut as build_cut,
    executor_at as build_executor_at,
    fix_fixture as build_fix_fixture,
    flash_executor as build_flash_executor,
    goto_timecode as build_goto_timecode,
    invert as build_invert,
    load_next as build_load_next,
    load_prev as build_load_prev,
    locate as build_locate,
    off_executor as build_off_executor,
    on_executor as build_on_executor,
    page_next as build_page_next,
    page_previous as build_page_previous,
    paste as build_paste,
    remove_from_selection as build_remove_from_selection,
    select_fixture,
    solo_executor as build_solo_executor,
    stomp_executor as build_stomp_executor,
    swop_executor as build_swop_executor,
    top_executor as build_top_executor,
    unblock as build_unblock,
    update_cue as build_update_cue,
)
from src.server import (
    _SEQUENCE_PROPERTY_ALIASES,
    _handle_errors,
    mcp,
)
from src.telnet_client import hold_connection

# ============================================================
# New Tools (Tools 30–44)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def set_executor_level(
    executor_id: int,
    level: float,
    page: int | None = None,
) -> str:
    """
    Set a fader/executor to a specific output level.

    Args:
        executor_id: Executor number (1-999)
        level: Fader level 0.0–100.0
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: JSON result with command sent
    """
    if not (0.0 <= level <= 100.0):
        return json.dumps({"error": "level must be between 0.0 and 100.0", "blocked": True}, indent=2)
    if executor_id < 1:
        return json.dumps({"error": "executor_id must be >= 1", "blocked": True}, indent=2)

    client = await _srv.get_client()
    cmd = build_executor_at(executor_id, level, page=page)
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def navigate_page(
    action: str,
    page_number: int | None = None,
    steps: int | None = None,
    create_if_missing: bool = False,
) -> str:
    """
    Navigate executor pages on the console.

    $FADERPAGE, $BUTTONPAGE, and $CHANNELPAGE are read-only system variables —
    SetVar has no effect on them. Only `Page N` (this tool) changes the active page.

    Args:
        action: "goto" (absolute page), "next" (page +), or "previous" (page -)
        page_number: Target page number (required for "goto"; 1-999)
        steps: Number of pages to advance/go back (optional; for "next"/"previous")
        create_if_missing: If True, sends `Store Page N /noconfirm` before navigating
            to create the page if it does not yet exist. Only applies to action="goto".
            Without this, MA2 returns Error #9 if the page doesn't exist.

    Returns:
        str: JSON result with command sent
    """
    if action not in ("goto", "next", "previous"):
        return json.dumps({"error": "action must be 'goto', 'next', or 'previous'", "blocked": True}, indent=2)
    if action == "goto":
        if page_number is None:
            return json.dumps({"error": "page_number is required for action='goto'", "blocked": True}, indent=2)
        cmd = f"page {page_number}"
    elif action == "next":
        cmd = build_page_next(steps)
    else:
        cmd = build_page_previous(steps)

    client = await _srv.get_client()
    result_steps = []

    if create_if_missing and action == "goto":
        store_cmd = f"Store Page {page_number} /noconfirm"
        store_raw = await client.send_command_with_response(store_cmd)
        result_steps.append({"command": store_cmd, "response": store_raw})

    response = await client.send_command_with_response(cmd)
    result_steps.append({"command": cmd, "response": response})

    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "steps": result_steps,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def select_feature(
    feature_name: str,
) -> str:
    """
    Select the active feature bank on the grandMA2 console (SAFE_WRITE).

    Sends `Feature [name]` which updates $FEATURE.
    $FEATURE is read-only — SetVar has no effect on it.
    Only `Feature [name]` changes the active feature context.

    Feature names are fixture-dependent — only features present on the selected
    fixture's channels are valid. Live-verified names (v3.9.60.65):
      Dimmer, Position, Gobo1, Gobo2, ColorRGB, Shutter, Focus, MSPEED
    Names that may error if fixture lacks the channel: Color, Zoom, Iris, Frost

    Args:
        feature_name: Feature bank to activate (e.g. "Dimmer", "ColorRGB", "MSPEED")

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    cmd = f"Feature {feature_name}"
    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def select_preset_type(
    preset_type: int | str,
) -> str:
    """
    Select the active preset type on the grandMA2 console (SAFE_WRITE).

    Sends `PresetType [id or name]` which jumps the encoder context to the
    first Feature available in that preset type for the selected fixtures.
    Updates $PRESET, $FEATURE, and $ATTRIBUTE simultaneously.

    CD tree location (live-verified, v3.9.60.65):
      cd 10.2        → lists all 9 PresetTypes
      cd 10.2.N      → lists Features under PresetType N
      cd 10.2.N.M    → lists Attributes under Feature M of PresetType N
      cd 10.2.N.M.K  → lists SubAttributes (deepest level)

    Preset types + live-verified $FEATURE on first activation:
      1=Dimmer  ($FEATURE=DIMMER,   $ATTRIBUTE=DIM)
      2=Position ($FEATURE=POSITION, $ATTRIBUTE=PAN)
      3=Gobo    ($FEATURE=GOBO1,    $ATTRIBUTE=GOBO1)
      4=Color   ($FEATURE=COLORRGB, $ATTRIBUTE=COLORRGB1, fixture-dep)
      5=Beam    ($FEATURE=SHUTTER,  $ATTRIBUTE=SHUTTER,   fixture-dep)
      6=Focus   ($FEATURE=FOCUS,    $ATTRIBUTE=FOCUS)
      7=Control ($FEATURE=MSPEED,   $ATTRIBUTE=INTENSITYMSPEED)
      8=Shapers (fixture must have Shapers channels)
      9=Video   (fixture must have Video channels)

    Args:
        preset_type: Preset type number (1-9) or name (e.g. "Color", "Control")

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    cmd = f"PresetType {preset_type}" if isinstance(preset_type, int) else f'PresetType "{preset_type}"'
    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


def _parse_preset_tree_list(raw: str) -> list[dict]:
    """Parse grandMA2 list output from the PresetType cd-tree.

    Handles rows of the form:
      ``PresetType N  LibName  ScreenName  ...``
      ``Feature N  LibName  ScreenName  ...``
      ``Attribute N  LibName  ScreenName  ...``
      ``SubAttribute N  LibName  ScreenName  ...``

    These rows have only one numeric ID (not the two required by the standard
    tabular parser), so they are skipped by parse_list_output().
    """
    import re
    _ANSI = re.compile(r"\x1b\[[0-9;]*m|\x1b\[K")
    _ROW = re.compile(
        r"^\s*(PresetType|Feature|Attribute|SubAttribute)\s+(\d+)\s+(\S+)\s+(.*?)\s*$",
        re.IGNORECASE,
    )
    entries = []
    for line in raw.splitlines():
        line = _ANSI.sub("", line).strip()
        m = _ROW.match(line)
        if m:
            obj_type, obj_id, lib_name, rest = m.group(1), m.group(2), m.group(3), m.group(4)
            # rest may contain "ScreenName  IdentifiedAs  DefaultScope  (count)"
            parts = re.split(r"\s{2,}", rest)
            entry = {
                "type": obj_type,
                "id": int(obj_id),
                "library_name": lib_name,
            }
            if parts:
                entry["screen_name"] = parts[0].strip()
            if len(parts) > 1:
                entry["identified_as"] = parts[1].strip()
            if len(parts) > 2:
                entry["extra"] = parts[2].strip()
            entries.append(entry)
    return entries


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def browse_preset_type(
    preset_type_id: int,
    depth: int = 1,
) -> str:
    """
    Browse the feature/attribute tree under a preset type (SAFE_READ).

    Navigates the grandMA2 LiveSetup preset-type cd-tree and lists children
    at the requested depth. The tree structure (live-verified v3.9.60.65):

      cd 10.2.N       → Features under PresetType N
      cd 10.2.N.M     → Attributes under Feature M
      cd 10.2.N.M.K   → SubAttributes under Attribute K  (leaf level)

    Indexes at each level use sequential position (1 = first listed child),
    NOT the internal library ID shown in the output.

    Args:
        preset_type_id: Preset type to browse (1=Dimmer, 2=Position, 3=Gobo,
            4=Color, 5=Beam, 6=Focus, 7=Control, 8=Shapers, 9=Video)
        depth: How deep to traverse (1=features only, 2=+attributes,
            3=+subattributes). Defaults to 1.

    Returns:
        str: JSON with the tree structure at the requested depth.
    """
    if not 1 <= preset_type_id <= 9:
        return json.dumps({"error": "preset_type_id must be 1-9", "blocked": True}, indent=2)
    if not 1 <= depth <= 3:
        return json.dumps({"error": "depth must be 1-3", "blocked": True}, indent=2)

    client = await _srv.get_client()

    async def list_path(path: str) -> tuple[str, list[dict]]:
        await _srv.navigate(client, "/")
        await _srv.navigate(client, path)
        lst = await _srv.list_destination(client)
        raw = lst.raw_response
        entries = _srv._parse_preset_tree_list(raw)
        return raw, entries

    # Depth 1: features under preset type
    raw1, features = await list_path(f"10.2.{preset_type_id}")

    result: dict = {
        "preset_type_id": preset_type_id,
        "cd_path": f"10.2.{preset_type_id}",
        "features": features,
        "risk_tier": "SAFE_READ",
    }

    if depth >= 2:
        for fi, feat in enumerate(features, start=1):
            feat_path = f"10.2.{preset_type_id}.{fi}"
            _, attrs = await list_path(feat_path)
            feat["cd_path"] = feat_path
            feat["attributes"] = attrs

            if depth >= 3:
                for ai, attr in enumerate(attrs, start=1):
                    attr_path = f"10.2.{preset_type_id}.{fi}.{ai}"
                    _, sub_attrs = await list_path(attr_path)
                    attr["cd_path"] = attr_path
                    attr["sub_attributes"] = sub_attrs

    # Return to root
    await _srv.navigate(client, "/")
    return json.dumps(result, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def modify_selection(
    action: str,
    fixture_ids: list[int] | None = None,
    end_id: int | None = None,
) -> str:
    """
    Add, remove, replace, or clear the current fixture selection.

    Args:
        action: "add" (+ N), "remove" (- N), "replace" (selfix), or "clear"
        fixture_ids: Fixture IDs to add/remove/replace (required for all except "clear")
        end_id: End of a range (optional; builds thru N)

    Returns:
        str: JSON result with command sent
    """
    if action not in ("add", "remove", "replace", "clear"):
        return json.dumps({"error": "action must be 'add', 'remove', 'replace', or 'clear'", "blocked": True}, indent=2)
    if action != "clear" and not fixture_ids:
        return json.dumps({"error": "fixture_ids is required for action != 'clear'", "blocked": True}, indent=2)

    client = await _srv.get_client()
    if action == "clear":
        cmd = build_clear_selection()
    elif action == "add":
        if len(fixture_ids) == 1 and end_id is not None:
            cmd = build_add_to_selection(fixture_ids[0], end=end_id)
        elif len(fixture_ids) == 1:
            cmd = build_add_to_selection(fixture_ids[0])
        else:
            cmd = build_add_to_selection(fixture_ids)
    elif action == "remove":
        if len(fixture_ids) == 1 and end_id is not None:
            cmd = build_remove_from_selection(fixture_ids[0], end=end_id)
        elif len(fixture_ids) == 1:
            cmd = build_remove_from_selection(fixture_ids[0])
        else:
            cmd = build_remove_from_selection(fixture_ids)
    else:  # replace
        first = fixture_ids[0]
        last = end_id if end_id is not None else (fixture_ids[-1] if len(fixture_ids) > 1 else None)
        cmd = select_fixture(first, last)

    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def adjust_value_relative(
    delta: float,
    attribute_name: str | None = None,
    fixture_ids: list[int] | None = None,
    end_id: int | None = None,
) -> str:
    """
    Nudge an attribute value by a relative delta on the current (or specified) selection.

    Args:
        delta: Relative change (positive or negative, non-zero). E.g. +10 or -5.
        attribute_name: Attribute to target (e.g. "Pan", "Tilt", "Dimmer"). Optional.
        fixture_ids: Select these fixtures before nudging. Optional.
        end_id: End of fixture range. Optional.

    Returns:
        str: JSON result with commands sent
    """
    if delta == 0:
        return json.dumps({"error": "delta cannot be zero", "blocked": True}, indent=2)

    client = await _srv.get_client()
    commands_sent = []

    if fixture_ids:
        first = fixture_ids[0]
        last = end_id if end_id is not None else (fixture_ids[-1] if len(fixture_ids) > 1 else None)
        sel_cmd = select_fixture(first, last)
        await client.send_command(sel_cmd)
        commands_sent.append(sel_cmd)

    if attribute_name:
        attr_cmd = f'attribute "{attribute_name}"'
        await client.send_command(attr_cmd)
        commands_sent.append(attr_cmd)

    nudge_cmd = build_at_relative(delta)
    response = await client.send_command_with_response(nudge_cmd)
    commands_sent.append(nudge_cmd)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def control_timecode(
    action: str,
    timecode_id: int,
    timecode_position: str | None = None,
) -> str:
    """
    Start, stop, or jump to a position in a timecode show.

    Args:
        action: "start" (go), "stop" (off), or "goto"
        timecode_id: Timecode show ID (1-256)
        timecode_position: HH:MM:SS:FF position string (required for "goto")

    Returns:
        str: JSON result with command sent
    """
    if action not in ("start", "stop", "goto"):
        return json.dumps({"error": "action must be 'start', 'stop', or 'goto'", "blocked": True}, indent=2)
    if action == "goto" and timecode_position is None:
        return json.dumps({"error": "timecode_position is required for action='goto'", "blocked": True}, indent=2)

    client = await _srv.get_client()
    if action == "start":
        cmd = f"go timecode {timecode_id}"
    elif action == "stop":
        cmd = f"off timecode {timecode_id}"
    else:
        cmd = build_goto_timecode(timecode_id, timecode_position)

    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def control_timer(
    action: str,
    timer_id: int,
) -> str:
    """
    Start, stop, or reset a console timer.

    Args:
        action: "start" (go), "stop" (off), or "reset" (goto)
        timer_id: Timer ID (1-256)

    Returns:
        str: JSON result with command sent
    """
    if action not in ("start", "stop", "reset"):
        return json.dumps({"error": "action must be 'start', 'stop', or 'reset'", "blocked": True}, indent=2)
    if timer_id < 1:
        return json.dumps({"error": "timer_id must be >= 1", "blocked": True}, indent=2)

    client = await _srv.get_client()
    if action == "start":
        cmd = f"go timer {timer_id}"
    elif action == "stop":
        cmd = f"off timer {timer_id}"
    else:
        cmd = f"goto timer {timer_id}"

    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def undo_last_action(count: int = 1) -> str:
    """
    Undo the last N actions on the console (sends 'oops' N times).

    Args:
        count: Number of actions to undo (1-20, default 1)

    Returns:
        str: JSON result with all raw responses
    """
    if not (1 <= count <= 20):
        return json.dumps({"error": "count must be between 1 and 20", "blocked": True}, indent=2)

    client = await _srv.get_client()
    responses = []
    for _ in range(count):
        response = await client.send_command_with_response("oops")
        responses.append(response)

    return json.dumps({
        "commands_sent": ["oops"] * count,
        "raw_responses": responses,
        "count": count,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def toggle_console_mode(mode: str) -> str:
    """
    Toggle a console mode on/off (blind, highlight, solo, freeze).

    These are toggle commands — each call flips the current state.

    Args:
        mode: "blind", "highlight", "solo", or "freeze"

    Returns:
        str: JSON result with command sent
    """
    valid = ("blind", "highlight", "solo", "freeze")
    if mode not in valid:
        return json.dumps({"error": f"mode must be one of {valid}", "blocked": True}, indent=2)

    # Blind mode puts the console into the programming layer — requires presets scope.
    if mode == "blind" and not has_scope(OAuthScope.PROGRAMMER_WRITE):
        return json.dumps({
            "blocked": True,
            "error": (
                "Blind mode requires OAuth scope 'gma2:programmer:write' "
                "(tier:2 or higher). Highlight/Solo/Freeze only require tier:1."
            ),
            "scope_required": str(OAuthScope.PROGRAMMER_WRITE),
            "scope_tier": 2,
        }, indent=2)

    client = await _srv.get_client()
    response = await client.send_command_with_response(mode)

    # Sync mode toggle to snapshot write-tracker (Gap 11)
    if snap := _srv._orchestrator.last_snapshot:
        snap.console_modes[mode] = not snap.console_modes.get(mode, False)

    return json.dumps({
        "command_sent": mode,
        "raw_response": response,
        "mode": mode,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def update_cue_data(
    confirm_destructive: bool = False,
    cue_id: float | None = None,
    sequence_id: int | None = None,
    merge: bool = False,
    overwrite: bool = False,
    cueonly: bool | None = None,
) -> str:
    """
    Update a cue with current programmer values (DESTRUCTIVE).

    Args:
        confirm_destructive: Must be True to execute
        cue_id: Cue number to update (optional; updates active cue if omitted)
        sequence_id: Sequence ID for scoping (optional)
        merge: Merge programmer into existing cue values
        overwrite: Overwrite cue with programmer values
        cueonly: Prevent tracking forward (True) or allow (False)

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
    cmd = build_update_cue(cue_id, sequence_id=sequence_id, merge=merge,
                           overwrite=overwrite, cueonly=cueonly)
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def set_cue_timing(
    cue_id: int,
    confirm_destructive: bool = False,
    sequence_id: int | None = None,
    fade_time: float | None = None,
    delay_time: float | None = None,
) -> str:
    """
    Set fade and/or delay time on a specific cue (DESTRUCTIVE).

    Args:
        cue_id: Cue number to update
        confirm_destructive: Must be True to execute
        sequence_id: Sequence ID for scoping (optional)
        fade_time: Fade time in seconds (0.0–3600.0, optional)
        delay_time: Delay time in seconds (0.0–3600.0, optional)

    Returns:
        str: JSON result with commands sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)
    if fade_time is None and delay_time is None:
        return json.dumps({"error": "At least one of fade_time or delay_time must be provided", "blocked": True}, indent=2)

    client = await _srv.get_client()
    commands_sent = []
    responses = []

    if fade_time is not None:
        cmd = build_assign_fade(fade_time, cue_id, sequence_id=sequence_id)
        response = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        responses.append(response)

    if delay_time is not None:
        cmd = build_assign_delay(delay_time, cue_id, sequence_id=sequence_id)
        response = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        responses.append(response)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_responses": responses,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def select_fixtures_by_group(
    group_id: int,
    append: bool = False,
) -> str:
    """
    Select all fixtures in a group (replaces or appends to current selection).

    Args:
        group_id: Group ID to select (1-999)
        append: If True, adds group to current selection instead of replacing

    Returns:
        str: JSON result with command sent
    """
    if group_id < 1:
        return json.dumps({"error": "group_id must be >= 1", "blocked": True}, indent=2)

    client = await _srv.get_client()
    cmd = f"+ group {group_id}" if append else f"group {group_id}"
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "group_id": group_id,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def control_executor(
    action: str,
    executor_id: int,
    page: int | None = None,
    speed_value: float | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Control an executor: start, stop, flash, swop, solo, top, stomp, or set speed.

    set_speed is DESTRUCTIVE (modifies stored data).

    Args:
        action: "on", "off", "flash", "swop", "solo", "top", "stomp", or "set_speed"
        executor_id: Executor ID (1-999)
        page: Page number for page-qualified addressing (optional)
        speed_value: BPM value for set_speed (0.0–999.0; required for set_speed)
        confirm_destructive: Must be True when action="set_speed"

    Returns:
        str: JSON result with command sent
    """
    valid_actions = ("on", "off", "flash", "swop", "solo", "top", "stomp", "set_speed")
    if action not in valid_actions:
        return json.dumps({"error": f"action must be one of {valid_actions}", "blocked": True}, indent=2)
    if executor_id < 1:
        return json.dumps({"error": "executor_id must be >= 1", "blocked": True}, indent=2)

    if action == "set_speed":
        if not confirm_destructive:
            return json.dumps({
                "blocked": True,
                "error": "set_speed is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
                "risk_tier": "DESTRUCTIVE",
            }, indent=2)
        if speed_value is None:
            return json.dumps({"error": "speed_value is required for action='set_speed'", "blocked": True}, indent=2)
        ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
        cmd = f"assign speed {speed_value} at executor {ref}"
        risk_tier = "DESTRUCTIVE"
    elif action == "on":
        cmd = build_on_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    elif action == "off":
        cmd = build_off_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    elif action == "flash":
        cmd = build_flash_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    elif action == "swop":
        cmd = build_swop_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    elif action == "top":
        cmd = build_top_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    elif action == "stomp":
        cmd = build_stomp_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    else:  # solo
        cmd = build_solo_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk_tier,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def load_cue(
    direction: str,
    executor_id: int | None = None,
    sequence_id: int | None = None,
) -> str:
    """
    Pre-load the next or previous cue without executing it (SAFE_WRITE).

    LoadNext / LoadPrev arm the cue for Go without firing it.

    Args:
        direction: "next" or "prev"
        executor_id: Executor ID to load on (optional)
        sequence_id: Sequence ID to load on (optional)

    Returns:
        str: JSON result with command sent
    """
    if direction not in ("next", "prev"):
        return json.dumps({"error": "direction must be 'next' or 'prev'", "blocked": True}, indent=2)

    if direction == "next":
        cmd = build_load_next(executor=executor_id, sequence=sequence_id)
    else:
        cmd = build_load_prev(executor=executor_id, sequence=sequence_id)

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
async def cut_paste_object(
    action: str,
    object_type: str | None = None,
    object_id: int | str | None = None,
    target_id: int | str | None = None,
    end: int | str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Cut an object to clipboard, or paste clipboard content at a target (DESTRUCTIVE).

    Cut + Paste is a two-step move: Cut prepares the source, Paste places it.
    Does not work with cue objects — use copy_or_move_object for cues.

    Args:
        action: "cut" or "paste"
        object_type: Object type ("group", "preset", "sequence", "macro", etc.)
        object_id: Source object ID (required for cut; ignored for bare paste)
        target_id: Destination ID (for paste)
        end: End ID for range cut (thru syntax)
        confirm_destructive: Must be True (cut removes the source; paste overwrites)

    Returns:
        str: JSON result with command sent
    """
    if action not in ("cut", "paste"):
        return json.dumps({"error": "action must be 'cut' or 'paste'", "blocked": True}, indent=2)

    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": f"{action.title()} is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if action == "cut":
        if object_type is None or object_id is None:
            return json.dumps({"error": "object_type and object_id required for cut", "blocked": True}, indent=2)
        cmd = build_cut(object_type, object_id, end=end)
    else:
        cmd = build_paste(object_type, target_id)

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def clone_object(
    object_type: str,
    object_id: int,
    target_id: int,
    end: int | None = None,
    target_end: int | None = None,
    noconfirm: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Clone (duplicate with data) one or more objects to new IDs (DESTRUCTIVE).

    Clone copies all stored data from the source to the target — unlike Copy
    it also migrates all associated cue/preset references.

    Args:
        object_type: Object type ("fixture", "group", "sequence", etc.)
        object_id: Source object ID
        target_id: Destination object ID
        end: End ID for source range (thru syntax)
        target_end: End ID for target range
        noconfirm: Suppress confirmation dialog
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "clone_object is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    cmd = build_clone(
        object_type, object_id, target_id,
        end=end, target_end=target_end, noconfirm=noconfirm,
    )
    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def fix_locate_fixture(
    action: str,
    fixture_ids: list[int] | None = None,
    end: int | None = None,
) -> str:
    """
    Fix (park) or Locate selected/specified fixtures (SAFE_WRITE).

    Fix pins fixture output to current level, overriding playback.
    Locate fires fixtures to their default state (full, open, centre).

    Args:
        action: "fix" or "locate"
        fixture_ids: List of fixture IDs to fix (optional — uses selection if omitted)
        end: End ID for range when a single start ID is given

    Returns:
        str: JSON result with command sent
    """
    if action not in ("fix", "locate"):
        return json.dumps({"error": "action must be 'fix' or 'locate'", "blocked": True}, indent=2)

    if action == "locate":
        cmd = build_locate()
    else:
        if fixture_ids is not None and len(fixture_ids) == 1:
            cmd = build_fix_fixture(fixture_ids[0], end=end)
        elif fixture_ids:
            cmd = build_fix_fixture(fixture_ids)
        else:
            cmd = build_fix_fixture()

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def manipulate_selection(action: str) -> str:
    """
    Invert or Align the current fixture selection / programmer values (SAFE_WRITE).

    Invert: swap selected and unselected fixtures.
    Align: distribute programmer values evenly from first to last fixture.

    Args:
        action: "invert" or "align"

    Returns:
        str: JSON result with command sent
    """
    if action not in ("invert", "align"):
        return json.dumps({"error": "action must be 'invert' or 'align'", "blocked": True}, indent=2)

    cmd = build_invert() if action == "invert" else build_align()
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
async def block_unblock_cue(
    action: str,
    cue_id: float,
    sequence_id: int | None = None,
    end: float | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Block or Unblock a cue (DESTRUCTIVE — modifies cue data in the show file).

    Block makes a cue store all active values and stop tracking from prior cues.
    Unblock removes the block flag, allowing values to track through again.

    Args:
        action: "block" or "unblock"
        cue_id: Cue number to block/unblock
        sequence_id: Sequence ID to scope the command (optional)
        end: End cue ID for range (thru syntax)
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON result with command sent
    """
    if action not in ("block", "unblock"):
        return json.dumps({"error": "action must be 'block' or 'unblock'", "blocked": True}, indent=2)
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": f"{action}_cue is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if action == "block":
        cmd = build_block(cue_id, sequence_id=sequence_id, end=end)
    else:
        cmd = build_unblock(cue_id, sequence_id=sequence_id, end=end)

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def get_executor_status(
    executor_id: int | None = None,
    page: int | None = None,
) -> str:
    """
    Query the status of one or all executors (SAFE_READ).

    Args:
        executor_id: Executor ID to inspect (optional; lists all if omitted)
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: JSON result with raw console response
    """
    if executor_id is not None:
        ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
        cmd = f"list executor {ref}"
    else:
        cmd = "list executor"

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def store_timecode_event(
    timecode_id: int,
    cue_id: float,
    sequence_id: int,
    confirm_destructive: bool = False,
    timecode_position: str | None = None,
) -> str:
    """
    Store a timecode trigger event that fires a cue at a specific time (DESTRUCTIVE).

    Args:
        timecode_id: Timecode show ID (1-256)
        cue_id: Cue to trigger
        sequence_id: Sequence containing the cue
        confirm_destructive: Must be True to execute
        timecode_position: HH:MM:SS:FF position string (optional)

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
    if timecode_position:
        cmd = f'assign timecode {timecode_id} cue {cue_id} sequence {sequence_id} "{timecode_position}"'
    else:
        cmd = f"store timecode {timecode_id}"

    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def set_sequence_property(
    sequence_id: int,
    property_name: str,
    value: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Set a property on a sequence object via the console tree (DESTRUCTIVE).

    Navigates to the sequence node, assigns the property, then returns to root.

    Args:
        sequence_id: Sequence ID (1-999)
        property_name: Property name (e.g. "loop", "tracking", "label")
        value: Property value (e.g. "on", "off", "My Sequence")
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON result with commands sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from src.commands.helpers import quote_name
    from src.console_feedback import find_console_errors
    from src.prompt_parser import parse_tabular_list

    # MA2 column names differ from the friendly ones ("tracking" is "Track").
    prop = _SEQUENCE_PROPERTY_ALIASES.get(property_name.strip().lower(), property_name.strip())
    assign_cmd = f"Assign Sequence {sequence_id} /{prop}={quote_name(value)}"
    list_cmd = f"List Sequence {sequence_id}"

    client = await _srv.get_client()
    async with hold_connection(client):
        assign_response = await client.send_command_with_response(assign_cmd)
        list_response = await client.send_command_with_response(list_cmd)

    errors = find_console_errors(assign_response, assign_cmd)
    verified_value = None
    for row in parse_tabular_list(list_response):
        for key, cell in row.items():
            if key.strip().lower() == prop.lower():
                verified_value = cell.strip()
    verified = verified_value is not None and verified_value.lower() == str(value).strip().lower()

    return json.dumps({
        "sequence_id": sequence_id,
        "property": prop,
        "value": value,
        "commands_sent": [assign_cmd, list_cmd],
        "raw_responses": [assign_response, list_response],
        "success": not errors,
        "verified": verified,
        "verified_value": verified_value,
        "note": None if verified else (
            f"Could not read {prop} back from '{list_cmd}' — check the sequence on the console."
        ),
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)
