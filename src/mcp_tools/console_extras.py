"""MCP tools — console extras. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    SPECIAL_MASTER_NAMES,
    build_login as build_console_login,
    build_logout as build_console_logout,
    call_plugin as build_call_plugin,
    chaser_rate as build_chaser_rate,
    chaser_skip as build_chaser_skip,
    chaser_speed as build_chaser_speed,
    chaser_xfade as build_chaser_xfade,
    label as build_label,
    # query_object_list
    list_objects as build_list_objects,
    lock_console as build_lock_console,
    rdm_automatch as build_rdm_automatch,
    rdm_autopatch as build_rdm_autopatch,
    rdm_info as build_rdm_info,
    rdm_list as build_rdm_list,
    rdm_setpatch as build_rdm_setpatch,
    rdm_unmatch as build_rdm_unmatch,
    reload_plugins as build_reload_plugins,
    run_lua as build_run_lua,
    set_effect_parameter as build_set_effect_parameter,
    set_special_master as build_set_special_master,
    unlock_console as build_unlock_console,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Wave 1 — Console Session & UI Lock
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def console_login(username: str, password: str) -> str:
    """
    Authenticate to the grandMA2 console as a specific user.

    Sends a Login command over the active Telnet session, switching
    the session to the specified user account and rights level.

    Args:
        username: Console username (e.g. "operator", "administrator")
        password: Console password

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_console_login(username, password)
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def console_logout() -> str:
    """
    Log out the current Telnet session user on the grandMA2 console.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_console_logout()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def lock_console_ui() -> str:
    """
    Lock the grandMA2 console UI to prevent accidental input.

    Sends the Lock command, which disables all physical panel input
    until unlocked. Useful during live shows to prevent accidental
    key presses.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_lock_console()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def unlock_console_ui(password: str | None = None) -> str:
    """
    Unlock the grandMA2 console UI.

    Args:
        password: Optional unlock password if the console was locked with one.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_unlock_console(password)
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


# ============================================================
# Wave 2 — Read-only list tools (pool discovery)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_layouts() -> str:
    """
    List all Layout pool objects on the grandMA2 console.

    Returns the raw console output of the List Layout command,
    which shows all defined layout views and their IDs.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_list_objects("Layout")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_worlds() -> str:
    """
    List all World pool objects on the grandMA2 console.

    Worlds are used to restrict which fixtures a user can control.
    Returns the raw console output of the List World command.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_list_objects("World")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def store_world(
    world_id: int,
    name: str | None = None,
    overwrite: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Create (store) a new World pool object on the grandMA2 console. (DESTRUCTIVE)

    Worlds restrict which fixtures a user profile can control. After storing,
    use assign_world_to_user_profile to attach the world to a user.

    Args:
        world_id: World slot number (1-256)
        name: Optional label applied immediately after store
        overwrite: If True, adds /overwrite flag (replaces existing slot)
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with commands_sent and raw_responses.
    """
    if not confirm_destructive:
        return json.dumps({"blocked": True, "reason": "confirm_destructive required"}, indent=2)

    client = await _srv.get_client()
    flag = " /overwrite" if overwrite else ""
    store_cmd = f"store world {world_id}{flag}"
    raw1 = await client.send_command_with_response(store_cmd)

    commands_sent = [store_cmd]
    raw_responses = [raw1]

    if name:
        label_cmd = build_label("world", world_id, name)
        raw2 = await client.send_command_with_response(label_cmd)
        commands_sent.append(label_cmd)
        raw_responses.append(raw2)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_responses": raw_responses,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def label_world(
    world_id: int,
    name: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Label an existing World pool object on the grandMA2 console. (DESTRUCTIVE)

    Args:
        world_id: World slot number to label (1-256)
        name: Name to assign to the world
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if not confirm_destructive:
        return json.dumps({"blocked": True, "reason": "confirm_destructive required"}, indent=2)

    client = await _srv.get_client()
    cmd = build_label("world", world_id, name)
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_timers() -> str:
    """
    List all Timer pool objects on the grandMA2 console.

    Returns the raw console output of the List Timer command,
    which shows all defined countdown / count-up timers.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_list_objects("Timer")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_filters() -> str:
    """
    List all Filter pool objects on the grandMA2 console.

    Filters restrict which fixture attributes are stored or recalled.
    Returns the raw console output of the List Filter command.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_list_objects("Filter")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_effects_pool() -> str:
    """
    List all Effect pool objects on the grandMA2 console.

    Returns stored effects (not the effect library) from the
    Effects pool using the List Effect command.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_list_objects("Effect")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_images() -> str:
    """
    List all Image pool objects on the grandMA2 console.

    Returns the raw console output of the List Image command,
    which shows all user-imported images (for gobo media servers, etc.).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_list_objects("Image")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_forms() -> str:
    """
    List all Form pool objects on the grandMA2 console.

    Forms define the waveform shapes used by effects. Returns
    the raw console output of the List Form command.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_list_objects("Form")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_timecode_events() -> str:
    """
    List all Timecode pool objects on the grandMA2 console.

    Returns the raw console output of the List Timecode command,
    which shows all stored timecode tracks and their slot IDs.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_list_objects("Timecode")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_agenda_events() -> str:
    """
    List all Agenda pool objects on the grandMA2 console.

    Agendas are time-triggered events (sunrise/sunset/specific time) that can
    fire macros or cues automatically. Returns the raw console output of the
    List Agenda command, showing all agenda slots and their IDs.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await _srv.get_client()
    cmd = build_list_objects("Agenda")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def store_agenda(
    agenda_id: int,
    name: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Create (store) a new Agenda pool object on the grandMA2 console. (DESTRUCTIVE)

    Agendas are time-triggered events (clock/sunrise/sunset) that fire macros or
    cues automatically. After storing, use the assign tool to attach a macro trigger.

    The store command creates the pool slot. To add time triggers to an existing
    agenda, use store_timecode_event with object_type="agenda".

    Args:
        agenda_id: Agenda slot number (1-256)
        name: Optional label applied immediately after store
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with commands_sent and raw_responses.
    """
    if not confirm_destructive:
        return json.dumps({"blocked": True, "reason": "confirm_destructive required"}, indent=2)

    client = await _srv.get_client()
    store_cmd = f"store agenda {agenda_id}"
    raw1 = await client.send_command_with_response(store_cmd)

    commands_sent = [store_cmd]
    raw_responses = [raw1]

    if name:
        label_cmd = build_label("agenda", agenda_id, name)
        raw2 = await client.send_command_with_response(label_cmd)
        commands_sent.append(label_cmd)
        raw_responses.append(raw2)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_responses": raw_responses,
    }, indent=2)


# ============================================================
# Wave 3 — Chaser live control & Effect programmer parameters
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def control_chaser(
    action: str,
    value: float | None = None,
    executor_id: int | None = None,
    page: int = 1,
) -> str:
    """
    Control a running chaser (rate, speed, skip, crossfade mode).

    Actions:
    - "rate"    : Set the rate (0-200, 100 = normal). Requires value.
    - "speed"   : Set the BPM speed (0-65535). Requires value.
    - "skip_fwd": Skip one step forward (SkipPlus).
    - "skip_bk" : Skip one step backward (SkipMinus).
    - "xfade_a" : Set crossfade mode A (CrossFadeA).
    - "xfade_b" : Set crossfade mode B (CrossFadeB).
    - "xfade_ab": Set crossfade mode AB (CrossFadeAB).

    Args:
        action: One of: rate, speed, skip_fwd, skip_bk, xfade_a, xfade_b, xfade_ab
        value: Required for rate and speed actions.
        executor_id: Target executor ID (optional; uses selected if omitted).
        page: Page number (default 1).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    action = action.lower()
    if action in ("rate", "speed") and value is None:
        return json.dumps({"error": f"'value' is required for action '{action}'"}, indent=2)

    if action == "rate":
        cmd = build_chaser_rate(value, executor_id, page)
    elif action == "speed":
        cmd = build_chaser_speed(value, executor_id, page)
    elif action == "skip_fwd":
        cmd = build_chaser_skip("plus", executor_id, page)
    elif action == "skip_bk":
        cmd = build_chaser_skip("minus", executor_id, page)
    elif action in ("xfade_a", "xfade_b", "xfade_ab"):
        mode = action.replace("xfade_", "")
        cmd = build_chaser_xfade(mode, executor_id, page)
    else:
        return json.dumps({
            "error": f"Unknown action '{action}'. Use: rate, speed, skip_fwd, skip_bk, xfade_a, xfade_b, xfade_ab"
        }, indent=2)

    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def set_effect_param(param: str, value: float) -> str:
    """
    Set an effect parameter in the programmer for the current fixture selection.

    Valid parameters: bpm, hz, high, low, phase, width, attack, decay.

    - bpm / hz   : Effect speed (beats per minute or Hertz)
    - high / low : Upper and lower value limits (0-100)
    - phase      : Phase offset (0-359 degrees)
    - width      : Pulse width (0-100)
    - attack     : Attack time (0-100)
    - decay      : Decay time (0-100)

    Args:
        param: Parameter name (case-insensitive). One of: bpm, hz, high, low,
               phase, width, attack, decay.
        value: Numeric value appropriate for the parameter.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    try:
        cmd = build_set_effect_parameter(param, value)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, indent=2)
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


# ============================================================
# Wave 4 — Plugin / Lua / Special Master
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def call_plugin_tool(plugin_id: int | str, confirm_destructive: bool = False) -> str:
    """
    Execute a plugin on the grandMA2 console by ID or name.

    Plugins are Lua scripts stored in the Plugin pool. This tool
    invokes them using the Plugin keyword.

    Args:
        plugin_id: Plugin number (int) or name (str).
        confirm_destructive: Must be True to proceed. Defaults to False (blocked).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "call_plugin_tool is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
        }, indent=2)
    client = await _srv.get_client()
    cmd = build_call_plugin(plugin_id)
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def run_lua_script(script: str, confirm_destructive: bool = False) -> str:
    """
    Execute an inline Lua script directly on the grandMA2 console.

    Sends the script using the Lua keyword. Useful for one-off
    automations without creating a persistent Plugin pool entry.

    Args:
        script: Lua source code (e.g. 'print("hello")', 'gma.cmd("Blackout")').
        confirm_destructive: Must be True to proceed. Defaults to False (blocked).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "run_lua_script is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
        }, indent=2)
    client = await _srv.get_client()
    cmd = build_run_lua(script)
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def reload_all_plugins(confirm_destructive: bool = False) -> str:
    """
    Reload all plugins from disk on the grandMA2 console.

    Sends ReloadPlugins, which rescans the plugin folder and reloads
    all Lua plugin files. Use after editing plugin files on disk.

    Args:
        confirm_destructive: Must be True to proceed. Defaults to False (blocked).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "reload_all_plugins is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
        }, indent=2)
    client = await _srv.get_client()
    cmd = build_reload_plugins()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def control_special_master(master: str, value: float) -> str:
    """
    Set the level of a grandMA2 SpecialMaster (Grand Master, Speed/Rate masters).

    Special masters globally control intensity and timing for all playbacks.

    Valid master names:
    - "grandmaster"     : Grand Master (0-100 %)
    - "playbackmaster"  : Playback Master (0-100 %)
    - "speed1".."speed16" : Speed Masters (BPM)
    - "rate1".."rate16"   : Rate Masters (%)

    Args:
        master: Master name (case-insensitive). See valid names above.
        value: Level value appropriate for the master type.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    try:
        cmd = build_set_special_master(master, value)
    except ValueError as exc:
        return json.dumps({
            "error": str(exc),
            "valid_masters": sorted(SPECIAL_MASTER_NAMES),
        }, indent=2)
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


# ============================================================
# Wave 5 — RDM (Remote Device Management)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.PATCH_WRITE)
@_handle_errors
async def rdm_discover(action: str = "automatch") -> str:
    """
    Perform RDM device discovery on the grandMA2 console.

    Actions:
    - "automatch"  : Match discovered RDM devices to existing fixture types (RdmAutomatch).
    - "autopatch"  : Auto-patch discovered RDM devices to free DMX addresses (RdmAutopatch).

    RDM (Remote Device Management) allows two-way communication with
    DMX fixtures that support the RDM protocol.

    Args:
        action: "automatch" or "autopatch" (default: "automatch").

    Returns:
        str: JSON with command_sent and raw_response.
    """
    action = action.lower()
    if action == "automatch":
        cmd = build_rdm_automatch()
    elif action == "autopatch":
        cmd = build_rdm_autopatch()
    else:
        return json.dumps({"error": f"Unknown action '{action}'. Use 'automatch' or 'autopatch'."}, indent=2)
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def rdm_get_info(
    fixture_id: int | None = None,
    universe: int | None = None,
) -> str:
    """
    Query RDM device information from the grandMA2 console.

    - If fixture_id is provided: returns RDM device info for that fixture (RdmInfo Fixture N).
    - If universe is provided (and no fixture_id): lists RDM devices on that universe (RdmList Universe N).
    - If neither is provided: lists all discovered RDM devices (RdmList).

    Args:
        fixture_id: Fixture ID to query (optional).
        universe: Universe number to filter by (optional).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if fixture_id is not None:
        cmd = build_rdm_info(fixture_id)
    else:
        cmd = build_rdm_list(universe)
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PATCH_WRITE)
@_handle_errors
async def rdm_patch(
    fixture_id: int,
    action: str,
    universe: int | None = None,
    address: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Patch or unmatch an RDM device on the grandMA2 console.

    Actions:
    - "setpatch" : Assign the RDM device at fixture_id to a specific DMX address.
                   Requires universe and address.
    - "unmatch"  : Detach the RDM match for a fixture (RdmUnmatch Fixture N).

    Args:
        fixture_id: Fixture ID of the RDM device.
        action: "setpatch" or "unmatch".
        universe: Target universe number (required for setpatch).
        address: Target DMX address 1-512 (required for setpatch).
        confirm_destructive: Must be True to proceed. Defaults to False (blocked).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "rdm_patch is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
        }, indent=2)
    action = action.lower()
    if action == "setpatch":
        if universe is None or address is None:
            return json.dumps({"error": "setpatch requires both 'universe' and 'address'."}, indent=2)
        cmd = build_rdm_setpatch(fixture_id, universe, address)
    elif action == "unmatch":
        cmd = build_rdm_unmatch(fixture_id)
    else:
        return json.dumps({"error": f"Unknown action '{action}'. Use 'setpatch' or 'unmatch'."}, indent=2)
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)
