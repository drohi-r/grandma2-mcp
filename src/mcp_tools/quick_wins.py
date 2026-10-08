"""MCP tools — quick wins. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    build_delete_user,
    delete_show as build_delete_show,
    list_effect_library as build_list_effect_library,
    list_fader_modules as build_list_fader_modules,
    list_macro_library as build_list_macro_library,
    list_plugin_library as build_list_plugin_library,
    list_update as build_list_update,
    temp_fader as build_temp_fader,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Tools 102–109: Quick-wins sprint
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def delete_user(
    slot: int,
    confirm_destructive: bool = False,
) -> str:
    """
    Delete a console user account by slot number (DESTRUCTIVE).

    The built-in Administrator in slot 1 cannot be deleted.
    Requires confirm_destructive=True to proceed.

    Args:
        slot: User slot number to delete (2–N). Slot 1 is protected.
        confirm_destructive: Must be True to execute (safety gate).

    Returns:
        JSON with command_sent, raw_response, or block info.
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "risk_tier": "DESTRUCTIVE",
            "error": "Delete User is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    if slot == 1:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "risk_tier": "DESTRUCTIVE",
            "error": "Slot 1 (Administrator) is protected and cannot be deleted.",
        }, indent=2)

    cmd = build_delete_user(slot)
    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def browse_effect_library() -> str:
    """
    Browse the grandMA2 effect library (SAFE_READ).

    Lists all available effect templates that can be applied to fixtures.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    cmd = build_list_effect_library()
    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def browse_macro_library() -> str:
    """
    Browse the grandMA2 macro library (SAFE_READ).

    Lists all available macro templates that can be imported into the show.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    cmd = build_list_macro_library()
    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def browse_plugin_library() -> str:
    """
    Browse the grandMA2 plugin library (SAFE_READ).

    Lists all available plugin templates installed on the console.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    cmd = build_list_plugin_library()
    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_fader_modules() -> str:
    """
    List connected fader modules (SAFE_READ).

    Returns information about all fader wing modules currently connected
    to the grandMA2 console.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    cmd = build_list_fader_modules()
    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_update_history() -> str:
    """
    List programming update history (SAFE_READ).

    Shows the recent update log of programmer changes made in the show.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    cmd = build_list_update()
    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SHOW_LOAD)
@_handle_errors
async def delete_show(
    name: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Delete a show file from disk (DESTRUCTIVE).

    Permanently removes the named show file. This cannot be undone.
    Requires confirm_destructive=True to proceed.

    Args:
        name: Show file name to delete (without extension).
        confirm_destructive: Must be True to execute (safety gate).

    Returns:
        JSON with command_sent, raw_response, or block info.
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "risk_tier": "DESTRUCTIVE",
            "error": "Delete Show is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    cmd = build_delete_show(name, noconfirm=True)
    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def assign_temp_fader(
    value: int = 50,
) -> str:
    """
    Set the temp fader level on the currently selected executor (SAFE_WRITE).

    TempFader crossfades the cue on when pulled up and crossfades the cue off
    when pulled down, relative to the given value. The value range is 0–100.

    Args:
        value: Fader level 0–100 (default 50). 0 = full off, 100 = full on.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    if not (0 <= value <= 100):
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": f"value must be between 0 and 100, got {value}.",
        }, indent=2)

    cmd = build_temp_fader(value)
    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)
