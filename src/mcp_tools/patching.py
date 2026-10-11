"""MCP tools — patching. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    delete_fixture as build_delete_fixture,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Tools 70–73: Tier 3 — Fixture Patching Workflow
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def browse_patch_schedule(
    fixture_type_id: int | None = None,
) -> str:
    """
    Browse the fixture patch schedule from LiveSetup.

    If fixture_type_id is provided, drills into that specific fixture type
    to show its instances (fixtures, DMX addresses, channels).

    Args:
        fixture_type_id: Fixture type index to drill into (optional).
                         Omit to see all fixture types.

    Returns:
        str: JSON with raw_response, entries, risk_tier.
    """
    client = await _srv.get_client()
    commands_sent = []

    nav = await _srv.navigate(client, "/")
    commands_sent.append(nav.command_sent)

    nav = await _srv.navigate(client, "10")
    commands_sent.append(nav.command_sent)

    nav = await _srv.navigate(client, "3")
    commands_sent.append(nav.command_sent)

    if fixture_type_id is not None:
        nav = await _srv.navigate(client, str(fixture_type_id))
        commands_sent.append(nav.command_sent)

    lst = await _srv.list_destination(client)
    commands_sent.append(lst.command_sent)

    nav = await _srv.navigate(client, "/")
    commands_sent.append(nav.command_sent)

    entries = [
        {"object_type": e.object_type, "object_id": e.object_id, "name": e.name}
        for e in lst.parsed_list.entries
    ]

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": lst.raw_response,
        "entries": entries,
        "entry_count": len(entries),
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PATCH_WRITE)
@_handle_errors
async def patch_fixture(
    fixture_id: int,
    dmx_universe: int,
    dmx_address: int,
    fixture_type_id: int | None = None,
    channel_id: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Patch a fixture to a DMX address (DESTRUCTIVE — modifies the patch).

    Assigns a DMX address to a fixture. Optionally assigns a fixture type first.

    MA2 syntax:
      assign dmx [universe].[address] at fixture [fixture_id]
      assign fixture_type [type_id] at fixture [fixture_id]  (if fixture_type_id given)

    Args:
        fixture_id: Fixture ID to patch.
        dmx_universe: DMX universe number (1-256).
        dmx_address: DMX address within universe (1-512).
        fixture_type_id: Fixture type to assign (optional).
        channel_id: Channel ID to assign (optional).
        confirm_destructive: Must be True to proceed.

    Returns:
        str: JSON with commands_sent, raw_responses, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Patching modifies fixture DMX assignments. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()
    commands_sent = []
    raw_responses = []

    # Optionally assign fixture type first
    if fixture_type_id is not None:
        from src.commands import assign as build_assign
        cmd = build_assign(
            source_type="fixturetype",
            source_id=str(fixture_type_id),
            target_type="fixture",
            target_id=str(fixture_id),
        )
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    # Assign DMX address
    from src.commands import assign as build_assign
    dmx_ref = f"{dmx_universe}.{dmx_address}"
    cmd = build_assign(
        source_type="dmx",
        source_id=dmx_ref,
        target_type="fixture",
        target_id=str(fixture_id),
    )
    raw = await client.send_command_with_response(cmd)
    commands_sent.append(cmd)
    raw_responses.append(raw)

    # Optionally assign channel
    if channel_id is not None:
        cmd = build_assign(
            source_type="fixture",
            source_id=str(fixture_id),
            target_type="channel",
            target_id=str(channel_id),
        )
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_responses": raw_responses,
        "fixture_id": fixture_id,
        "dmx_address": f"{dmx_universe}.{dmx_address}",
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PATCH_WRITE)
@_handle_errors
async def unpatch_fixture(
    fixture_id: int,
    confirm_destructive: bool = False,
) -> str:
    """
    Unpatch a fixture (remove its DMX assignment) (DESTRUCTIVE).

    MA2 syntax: delete fixture [fixture_id]
    This removes the DMX assignment but does not delete the fixture from the show.

    Args:
        fixture_id: Fixture ID to unpatch.
        confirm_destructive: Must be True to proceed.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Unpatching removes DMX assignments. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    cmd = build_delete_fixture(fixture_id)
    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PATCH_WRITE)
@_handle_errors
async def set_fixture_type_property(
    fixture_type_id: int,
    property_name: str,
    value: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Set a property on a fixture type in LiveSetup (DESTRUCTIVE).

    Navigates to LiveSetup/FixtureTypes/[N] and assigns a property value.
    Path: cd 10 -> cd 3 -> assign [fixture_type_id]/property=value -> cd /

    Args:
        fixture_type_id: Fixture type index (1-based).
        property_name: Property to set (e.g. "Mode", "Name").
        value: New value for the property.
        confirm_destructive: Must be True to proceed.

    Returns:
        str: JSON with commands_sent, success, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Modifying fixture type properties is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()
    result = await _srv.set_property(
        client,
        path=f"10.3.{fixture_type_id}",
        property_name=property_name,
        value=value,
    )

    return json.dumps({
        "commands_sent": result.commands_sent,
        "raw_responses": result.raw_responses,
        "success": result.success,
        "verified_value": result.verified_value,
        "error": result.error,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)
