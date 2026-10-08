"""MCP tools — users. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    build_assign_world_to_user_profile,
    build_list_users,
    build_store_user,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================================
# USER MANAGEMENT TOOLS (Tools 98-100)
# Require OAuth scope gma2:user:manage (Tier 5 — Admin only)
# ============================================================================


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def list_console_users() -> str:
    """
    List all user accounts in the current show file (SAFE_READ).

    Returns the raw `list user` output from the console, showing all
    user slots with their names, rights levels, and profile assignments.

    Returns:
        str: JSON result with raw console response
    """
    client = await _srv.get_client()
    cmd = build_list_users()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def create_console_user(
    slot: int,
    name: str,
    password: str,
    rights_level: int,
    confirm_destructive: bool = False,
) -> str:
    """
    Create or overwrite a user account in the show file (DESTRUCTIVE — Admin only).

    Requires both gma2:user:manage OAuth scope AND confirm_destructive=True.

    grandMA2 rights levels:
        0 = None     (view/change views only, no programmer)
        1 = Playback (run show, no store)
        2 = Presets  (update existing presets only)
        3 = Program  (full show programming)
        4 = Setup    (patch, fixture import, console setup)
        5 = Admin    (full access + user/session/show management)

    Args:
        slot: User slot number (2-N; slot 1 = Administrator, always exists)
        name: Username (alphanumeric + underscores, no spaces)
        password: Console login password (empty string = no password required)
        rights_level: MA2 rights level 0-5
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "create_console_user is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)
    if slot < 1:
        return json.dumps({"error": "slot must be >= 1", "blocked": True}, indent=2)
    if rights_level not in range(6):
        return json.dumps({
            "error": f"rights_level must be 0-5, got {rights_level}",
            "blocked": True,
        }, indent=2)
    if not name or not name.replace("_", "").isalnum():
        return json.dumps({
            "error": "name must be alphanumeric (underscores allowed), no spaces",
            "blocked": True,
        }, indent=2)

    cmd = build_store_user(slot, name, password, rights_level)
    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    _rights_names = {0: "None", 1: "Playback", 2: "Presets",
                     3: "Program", 4: "Setup", 5: "Admin"}
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "slot": slot,
        "name": name,
        "rights_level": rights_level,
        "rights_name": _rights_names[rights_level],
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def assign_world_to_user_profile(
    user_profile_slot: int,
    world_slot: int,
    confirm_destructive: bool = False,
) -> str:
    """
    Assign a World (fixture visibility mask) to a User Profile (DESTRUCTIVE — Admin only).

    Restricts all Users assigned to this profile to only access fixtures and attributes
    visible in the specified World. Use world_slot=0 to remove the restriction (None).

    Args:
        user_profile_slot: UserProfile slot number to modify
        world_slot: World slot number (0 = no restriction / remove World assignment)
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "assign_world_to_user_profile is DESTRUCTIVE. Set confirm_destructive=True.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)
    if user_profile_slot < 1:
        return json.dumps({"error": "user_profile_slot must be >= 1", "blocked": True}, indent=2)

    cmd = build_assign_world_to_user_profile(user_profile_slot, world_slot)
    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "user_profile_slot": user_profile_slot,
        "world_slot": world_slot,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def inspect_sessions() -> str:
    """
    Inspect active per-operator Telnet session pool (SAFE_READ).

    Returns a snapshot of the session manager's current state: how many
    sessions are open, which console users they are authenticated as, and
    how long each has been idle.  Useful for diagnosing connection issues
    in multi-operator deployments.

    Returns:
        JSON with session_count and a sessions list, each entry containing:
        identity, username, connected, idle_seconds, age_seconds.
    """
    manager = await _srv._get_session_manager()
    return json.dumps({
        "session_count": manager.session_count(),
        "max_sessions": manager._max_sessions,
        "idle_timeout_seconds": manager._idle_timeout,
        "sessions": manager.session_info(),
    }, indent=2)
