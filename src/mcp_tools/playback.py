"""MCP tools — playback. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    blackout as build_blackout,
    get_user_var as build_get_user_var,
    highlight as build_highlight,
    list_oops as build_list_oops,
    list_shows as build_list_shows,
    list_user_var as build_list_user_var,
    list_var as build_list_var,
    load_show as build_load_show,
    new_show as build_new_show,
    release_executor as build_release_executor,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Tools 57–64: Tier 1 — High-Impact Tools
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def highlight_fixtures(on: bool = True) -> str:
    """
    Toggle highlight mode for the currently selected fixtures.

    Highlight mode temporarily sets selected fixtures to full intensity to help
    identify them on stage. Easily reversible (toggle off).

    Args:
        on: True to enable, False to disable highlight mode.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    cmd = build_highlight(on)
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def release_executor(
    executor_id: int,
    page: int | None = None,
) -> str:
    """
    Release an executor, returning it to its default state.

    Args:
        executor_id: Executor ID (1-999).
        page: Page number for page-qualified addressing (optional).

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    cmd = build_release_executor(executor_id, page=page)
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def blackout_toggle() -> str:
    """
    Toggle master blackout (kills all lighting output).

    Blackout is a toggle — call once to enable, again to disable.
    SAFE_WRITE because it is easily reversible.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    cmd = build_blackout()
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_shows() -> str:
    """
    List available show files on the console.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    cmd = build_list_shows()
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SHOW_LOAD)
@_handle_errors
async def load_show(
    name: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Load an existing show file (DESTRUCTIVE — replaces current show).

    Args:
        name: Show file name to load.
        confirm_destructive: Must be True to proceed.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "LoadShow replaces the current show. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    cmd = build_load_show(name)
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SHOW_LOAD)
@_handle_errors
async def new_show(
    name: str,
    confirm_destructive: bool = False,
    preserve_connectivity: bool = True,
    keep_timeconfig: bool = False,
    keep_globalsettings: bool = False,
    keep_localsettings: bool = False,
    keep_protocols: bool = False,
    keep_network: bool = False,
    keep_user: bool = False,
) -> str:
    """
    Create a new empty show (DESTRUCTIVE — replaces current show).

    CONNECTIVITY WARNING
    --------------------
    Creating a new show clears Global Settings, which **disables Telnet login**
    and severs the MCP connection.  ``preserve_connectivity=True`` (the default)
    automatically adds /globalsettings + /network + /protocols so Telnet stays
    enabled and network/DMX config is preserved.

    Set ``preserve_connectivity=False`` only if you intend to manually
    re-enable Telnet on the console afterwards (Setup → Console → Global
    Settings → Telnet → Login Enabled).

    Keep flags (correspond to un-checking "Clear …" in the MA2 New Show dialog):

    | Flag               | Dialog checkbox          | MA2 flag        | Included by preserve_connectivity |
    |--------------------|--------------------------|-----------------|-----------------------------------|
    | keep_globalsettings| Clear Global Settings    | /globalsettings | YES — contains Telnet login       |
    | keep_network       | Clear Network Config     | /network        | YES — IP / MA-Net2 config         |
    | keep_protocols     | Clear Network Protocols  | /protocols      | YES — Art-Net, sACN, etc.         |
    | keep_timeconfig    | Clear Time Config        | /timeconfig     | no                                |
    | keep_localsettings | Clear Local Settings     | /localsettings  | no                                |
    | keep_user          | Clear User Profiles      | /user           | no                                |

    Args:
        name: New show file name.
        confirm_destructive: Must be True to proceed.
        preserve_connectivity: Auto-add /globalsettings + /network + /protocols
            to prevent Telnet being disabled (default True).
        keep_timeconfig: Preserve Time Config from current show.
        keep_globalsettings: Preserve Global Settings (overrides preserve_connectivity).
        keep_localsettings: Preserve Local Settings from current show.
        keep_protocols: Preserve Network Protocol settings (overrides preserve_connectivity).
        keep_network: Preserve Network Config (overrides preserve_connectivity).
        keep_user: Preserve User Profiles from current show.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier,
             and connectivity_flags listing which flags were applied.

    AI assistant guidance
    ---------------------
    Always confirm ``preserve_connectivity=True`` unless the user explicitly
    wants a completely clean show AND understands Telnet will be disabled.
    Ask about keep_timeconfig, keep_localsettings, keep_user separately —
    these have no connectivity impact and are purely about preserving show data.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "NewShow replaces the current show. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    # Merge preserve_connectivity defaults with explicit flags
    effective_globalsettings = keep_globalsettings or preserve_connectivity
    effective_network = keep_network or preserve_connectivity
    effective_protocols = keep_protocols or preserve_connectivity

    # /noconfirm is always needed — the telnet connection is stateless
    # (each call reconnects) so it cannot answer the console's
    # "save old show first?" dialog mid-stream.
    cmd = build_new_show(
        name,
        noconfirm=True,
        keep_timeconfig=keep_timeconfig,
        keep_globalsettings=effective_globalsettings,
        keep_localsettings=keep_localsettings,
        keep_protocols=effective_protocols,
        keep_network=effective_network,
        keep_user=keep_user,
    )
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
        "preserve_connectivity": preserve_connectivity,
        "connectivity_flags": {
            "globalsettings": effective_globalsettings,
            "network": effective_network,
            "protocols": effective_protocols,
        },
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_variable(
    action: str,
    var_name: str | None = None,
) -> str:
    """
    Read variables from the console (SAFE_READ).

    Args:
        action: One of:
            "echo"         — read any variable via `Echo $NAME` (system + user vars).
                             Use this for built-in system variables: $SELECTEDEXEC,
                             $TIME, $DATE, $VERSION, $FADERPAGE, $BUTTONPAGE,
                             $SELECTEDFIXTURESCOUNT, $USER, $HOSTNAME, $HOSTSTATUS, etc.
            "get_user"     — read a user variable via GetUserVar.
            "list_var"     — list all global show variables.
            "list_user_var"— list all user-profile variables.
        var_name: Variable name (required for "echo" and "get_user").
                  May include or omit leading $. E.g. "SELECTEDEXEC" or "$mycounter".

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
             For "echo", also includes `variable` and `value` keys.
    """
    valid_actions = ("echo", "get_user", "list_var", "list_user_var")
    if action not in valid_actions:
        return json.dumps({
            "error": f"action must be one of {valid_actions}",
            "blocked": True,
        }, indent=2)

    if action == "echo":
        if not var_name:
            return json.dumps({
                "error": "var_name is required for echo action",
                "blocked": True,
            }, indent=2)
        clean = var_name.lstrip("$")
        cmd = "ListVar"
        client = await _srv.get_client()
        raw = await client.send_command_with_response(cmd)
        variables = _srv._parse_listvar(raw)
        value = variables.get(f"${clean}") or variables.get(f"${clean.upper()}")
        return json.dumps({
            "variable": f"${clean}",
            "value": value,
            "found": value is not None,
            "command_sent": cmd,
            "raw_response": raw,
            "risk_tier": "SAFE_READ",
        }, indent=2)

    if action == "get_user":
        if not var_name:
            return json.dumps({
                "error": "var_name is required for get_user action",
                "blocked": True,
            }, indent=2)
        cmd = build_get_user_var(var_name)
    elif action == "list_var":
        cmd = build_list_var()
    else:
        cmd = build_list_user_var()

    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_preset_pool(
    preset_type: str | None = None,
) -> str:
    """
    List presets stored in the show's Global preset pool.

    Without arguments: returns all PresetPool entries with their counts
    (Dimmer, Position, Gobo, Color, Beam, Focus, Control, Shapers, Video).

    With preset_type: navigates into that pool and lists individual presets
    with their slot number, name, and Special field.

    CD tree path navigated:
      cd 17 → cd 1 → list             (pool overview)
      cd 17 → cd 1 → cd N → list      (individual preset type)

    Pool index → type mapping (live-verified v3.9.60.65):
      0=ALL  1=DIMMER  2=POSITION  3=GOBO  4=COLOR
      5=BEAM  6=FOCUS  7=CONTROL  8=SHAPERS  9=VIDEO

    Note: The "Special" column shows "Normal" (standard) or "Embedded" — it
    does NOT indicate Universal vs Selective scope. Scope is an internal flag
    only visible in the console GUI or show XML.

    Args:
        preset_type: Optional type to drill into. Accepts name ("color", "position")
            or number ("4"). If omitted, returns pool overview.

    Returns:
        str: JSON with pool overview or individual preset list.
    """
    from src.commands.constants import PRESET_TYPES

    client = await _srv.get_client()

    # Navigate to Global preset pool
    await _srv.navigate(client, "/")
    await _srv.navigate(client, "17")
    await _srv.navigate(client, "1")

    if preset_type is None:
        # Overview: list all pools
        lst = await _srv.list_destination(client)
        await _srv.navigate(client, "/")
        return json.dumps({
            "cd_path": "17.1",
            "description": "Global PresetPool overview",
            "raw_response": lst.raw_response if lst else "",
            "entries": [
                {"type": e.object_type, "id": e.object_id, "name": e.name}
                for e in (lst.parsed_list.entries if lst and lst.parsed_list else [])
            ],
            "risk_tier": "SAFE_READ",
        }, indent=2)

    # Resolve preset_type to pool index
    try:
        pool_idx = int(preset_type)
    except (ValueError, TypeError):
        pool_idx = PRESET_TYPES.get(str(preset_type).lower())
        if pool_idx is None:
            await _srv.navigate(client, "/")
            return json.dumps({
                "error": f"Unknown preset_type {preset_type!r}. Use name (color, position) or number 1-9."
            }, indent=2)

    await _srv.navigate(client, str(pool_idx))
    lst = await _srv.list_destination(client)
    await _srv.navigate(client, "/")

    return json.dumps({
        "cd_path": f"17.1.{pool_idx}",
        "preset_type": preset_type,
        "pool_index": pool_idx,
        "raw_response": lst.raw_response if lst else "",
        "entries": [
            {"type": e.object_type, "id": e.object_id, "name": e.name}
            for e in (lst.parsed_list.entries if lst and lst.parsed_list else [])
        ],
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_undo_history() -> str:
    """
    Display the undo (Oops) history.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    cmd = build_list_oops()
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)
