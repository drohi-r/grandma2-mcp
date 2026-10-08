"""MCP tools — setup library. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
from datetime import UTC

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    list_effect_library as build_list_effect_library,
    list_library as build_list_library,
    list_macro_library as build_list_macro_library,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Tools 65–69: Tier 2 — Setup & Library Tools
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_fixture_types() -> str:
    """
    List all fixture types in the show (from LiveSetup/FixtureTypes).

    Navigates to cd 10 (LiveSetup) -> cd 3 (FixtureTypes) -> list -> cd /

    Returns:
        str: JSON with raw_response, entries (fixture type names, manufacturers,
             DMX footprint), risk_tier.
    """
    client = await _srv.get_client()
    commands_sent = []

    # Navigate to root
    nav = await _srv.navigate(client, "/")
    commands_sent.append(nav.command_sent)

    # Navigate to LiveSetup
    nav = await _srv.navigate(client, "10")
    commands_sent.append(nav.command_sent)

    # Navigate to FixtureTypes
    nav = await _srv.navigate(client, "3")
    commands_sent.append(nav.command_sent)

    # List
    lst = await _srv.list_destination(client)
    commands_sent.append(lst.command_sent)

    # Return to root
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
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_layers() -> str:
    """
    List all fixture layers in the show (from LiveSetup/Layers).

    Navigates to cd 10 (LiveSetup) -> cd 4 (Layers) -> list -> cd /

    Returns:
        str: JSON with raw_response, entries (layer names, fixture ranges),
             risk_tier.
    """
    client = await _srv.get_client()
    commands_sent = []

    nav = await _srv.navigate(client, "/")
    commands_sent.append(nav.command_sent)

    nav = await _srv.navigate(client, "10")
    commands_sent.append(nav.command_sent)

    nav = await _srv.navigate(client, "4")
    commands_sent.append(nav.command_sent)

    lst = await _srv.list_destination(client)
    commands_sent.append(lst.command_sent)

    nav = await _srv.navigate(client, "/")
    commands_sent.append(nav.command_sent)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": lst.raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_universes(
    max_universes: int = 16,
) -> str:
    """
    List DMX universes and their configuration (from LiveSetup/Universes).

    Navigates to cd 10 (LiveSetup) -> cd 5 (Universes) -> list -> cd /

    Args:
        max_universes: Limit output to first N universes (default 16, max 256).

    Returns:
        str: JSON with raw_response, risk_tier.
    """
    client = await _srv.get_client()
    commands_sent = []

    nav = await _srv.navigate(client, "/")
    commands_sent.append(nav.command_sent)

    nav = await _srv.navigate(client, "10")
    commands_sent.append(nav.command_sent)

    nav = await _srv.navigate(client, "5")
    commands_sent.append(nav.command_sent)

    lst = await _srv.list_destination(client)
    commands_sent.append(lst.command_sent)

    nav = await _srv.navigate(client, "/")
    commands_sent.append(nav.command_sent)

    # Truncate raw response if too many universes
    entries = [
        {"object_type": e.object_type, "object_id": e.object_id, "name": e.name}
        for e in lst.parsed_list.entries[:max_universes]
    ]

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": lst.raw_response[:2000] if len(lst.raw_response) > 2000 else lst.raw_response,
        "entries": entries,
        "entry_count": len(lst.parsed_list.entries),
        "showing": min(max_universes, len(lst.parsed_list.entries)),
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_library(
    library_type: str = "fixture",
) -> str:
    """
    Browse the console's built-in libraries.

    Args:
        library_type: "fixture" (ListLibrary), "effect" (ListEffectLibrary),
                      or "macro" (ListMacroLibrary).

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    valid_types = ("fixture", "effect", "macro")
    if library_type not in valid_types:
        return json.dumps({
            "error": f"library_type must be one of {valid_types}",
            "blocked": True,
        }, indent=2)

    if library_type == "fixture":
        cmd = build_list_library()
    elif library_type == "effect":
        cmd = build_list_effect_library()
    else:
        cmd = build_list_macro_library()

    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def manage_matricks(
    action: str,
    value: int | None = None,
    x: int | None = None,
    y: int | None = None,
    column: int | None = None,
    increment: str | None = None,
    name: str | None = None,
    mode: str | None = None,
    turn_off: bool = False,
) -> str:
    """
    Control MAtricks selection patterns via direct command keywords (SAFE_WRITE).

    Uses grandMA2 MAtricks command keywords that act directly on the current
    fixture selection — no navigation required.

    Actions and their parameters:
      - "interleave": Set virtual grid width. Params: value (width), column, increment (+/-), turn_off.
      - "blocks": Set block size. Params: value (size), x, y (x.y notation), increment (+ N/- N), turn_off.
      - "groups": Set align group size. Params: value (size), x, y (x.y notation), increment (+ N/- N), turn_off.
      - "wings": Set wing/mirror parts. Params: value (parts), increment (+/-), turn_off.
      - "filter": Set sub-selection filter. Params: value (filter_num), name (filter name), increment (+/-), turn_off.
      - "reset": Clear all MAtricks settings. No params.
      - "recall": Recall a MAtricks pool object or toggle mode. Params: value (matricks_id), mode (on/off/toggle).
      - "all": Reset Single X sub-selection. No params.
      - "allrows": Reset Single Y sub-selection. No params.
      - "next": Step forward through Single X sub-selection. No params.
      - "previous": Step backward through Single X sub-selection. No params.
      - "nextrow": Step forward through Single Y (row) sub-selection. No params.

    Args:
        action: The MAtricks action to perform.
        value: Primary numeric value (width/size/parts/filter_num/matricks_id).
        x: X-axis value for blocks/groups x.y notation.
        y: Y-axis value for blocks/groups x.y notation.
        column: Column for interleave column.width notation.
        increment: Step value: "+", "-", "+ N", or "- N".
        name: Filter name (for action="filter").
        mode: "on", "off", or "toggle" (for action="recall").
        turn_off: Send the "Off" variant of the command.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    from src.commands import (
        all_rows_sub_selection as _build_all_rows,
        all_sub_selection as _build_all,
        matricks_blocks as _build_blocks,
        matricks_filter as _build_filter,
        matricks_groups as _build_groups,
        matricks_interleave as _build_interleave,
        matricks_reset as _build_reset,
        matricks_wings as _build_wings,
        next_row_sub_selection as _build_next_row,
        next_sub_selection as _build_next,
        previous_sub_selection as _build_previous,
        recall_matricks as _build_recall,
    )

    action_lower = action.lower()
    try:
        if action_lower == "interleave":
            cmd = _build_interleave(
                width=value, column=column,
                increment=increment, off=turn_off,
            )
        elif action_lower == "blocks":
            cmd = _build_blocks(
                size=value, x=x, y=y,
                increment=increment, off=turn_off,
            )
        elif action_lower == "groups":
            cmd = _build_groups(
                size=value, x=x, y=y,
                increment=increment, off=turn_off,
            )
        elif action_lower == "wings":
            cmd = _build_wings(
                parts=value, increment=increment, off=turn_off,
            )
        elif action_lower == "filter":
            cmd = _build_filter(
                filter_num=value, name=name,
                increment=increment, off=turn_off,
            )
        elif action_lower == "reset":
            cmd = _build_reset()
        elif action_lower == "recall":
            cmd = _build_recall(matricks_id=value, mode=mode)
        elif action_lower == "all":
            cmd = _build_all()
        elif action_lower == "allrows":
            cmd = _build_all_rows()
        elif action_lower == "next":
            cmd = _build_next()
        elif action_lower == "previous":
            cmd = _build_previous()
        elif action_lower == "nextrow":
            cmd = _build_next_row()
        else:
            return json.dumps({
                "error": f"Unknown action: {action!r}. Valid: interleave, blocks, groups, wings, filter, reset, recall, all, allrows, next, previous, nextrow.",
                "risk_tier": "SAFE_WRITE",
            }, indent=2)
    except ValueError as exc:
        return json.dumps({
            "error": str(exc),
            "risk_tier": "SAFE_WRITE",
        }, indent=2)

    client = await _srv.get_client()
    raw = await client.send_command_with_response(cmd)

    # Update in-memory write-tracker (Gap 6 — no telnet readback for MAtricks state)
    if snap := _srv._orchestrator.last_snapshot:
        mt = snap.matricks
        if action_lower == "reset":
            mt.reset()
        elif action_lower == "interleave":
            mt.interleave = None if turn_off else (value or 1)
        elif action_lower == "blocks":
            mt.blocks_x = None if turn_off else (x or value or 1)
            mt.blocks_y = None if turn_off else (y or 1)
        elif action_lower == "groups":
            mt.groups_x = None if turn_off else (x or value or 1)
            mt.groups_y = None if turn_off else (y or 1)
        elif action_lower == "wings":
            mt.wings = None if turn_off else (value or 1)
        elif action_lower == "filter":
            mt.filter_id = None if turn_off else (value or None)
        elif action_lower == "recall":
            mt.active = True
        # all/allrows/next/previous/nextrow are selection steps — no persistent state to track

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.GROUP_STORE)
@_handle_errors
async def store_matricks_preset(
    pool_slot: int,
    name: str,
    interleave: int | None = None,
    blocks: int | None = None,
    blocks_y: int | None = None,
    groups: int | None = None,
    groups_y: int | None = None,
    wings: int | None = None,
    filter_num: int | None = None,
    filter_name: str | None = None,
    reset_first: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """
    Set MAtricks state, store to pool, and label — all in one call (DESTRUCTIVE).

    Workflow:
      1. Optionally resets all MAtricks settings (reset_first=True, default)
      2. Applies specified MAtricks settings (interleave, blocks, groups, wings, filter)
      3. Stores current MAtricks state to the specified pool slot (/overwrite)
      4. Labels the pool object with the given name

    At least one MAtricks setting must be provided.

    Args:
        pool_slot: Pool slot number to store into (e.g. 2).
        name: Label for the stored MAtricks object (e.g. "Wings-2-I4").
        interleave: Virtual grid width (MAtricksInterleave).
        blocks: Block size X (MAtricksBlocks). Use with blocks_y for x.y.
        blocks_y: Block size Y (requires blocks for x.y notation).
        groups: Align group size X (MAtricksGroups). Use with groups_y for x.y.
        groups_y: Align group size Y (requires groups for x.y notation).
        wings: Wing/mirror parts (MAtricksWings).
        filter_num: Filter number (MAtricksFilter).
        filter_name: Filter name (MAtricksFilter, e.g. "OddID").
        reset_first: Reset all MAtricks before applying (default True).
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation).

    Returns:
        str: JSON with commands_sent list, pool_slot, name, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "store_matricks_preset modifies the MAtricks pool. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from src.commands import (
        label as _build_label,
        matricks_blocks as _build_blocks,
        matricks_filter as _build_filter,
        matricks_groups as _build_groups,
        matricks_interleave as _build_interleave,
        matricks_reset as _build_reset,
        matricks_wings as _build_wings,
        store_matricks as _build_store_matricks,
    )

    # Validate: at least one setting must be provided
    has_setting = any(v is not None for v in [
        interleave, blocks, groups, wings, filter_num, filter_name,
    ])
    if not has_setting:
        return json.dumps({
            "error": "At least one MAtricks setting must be provided (interleave, blocks, groups, wings, filter_num, or filter_name).",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()
    commands_sent = []

    # Step 1: Reset if requested
    if reset_first:
        cmd = _build_reset()
        await client.send_command(cmd)
        commands_sent.append(cmd)

    # Step 2: Apply settings
    if interleave is not None:
        cmd = _build_interleave(width=interleave)
        await client.send_command(cmd)
        commands_sent.append(cmd)

    if blocks is not None:
        if blocks_y is not None:
            cmd = _build_blocks(x=blocks, y=blocks_y)
        else:
            cmd = _build_blocks(size=blocks)
        await client.send_command(cmd)
        commands_sent.append(cmd)

    if groups is not None:
        if groups_y is not None:
            cmd = _build_groups(x=groups, y=groups_y)
        else:
            cmd = _build_groups(size=groups)
        await client.send_command(cmd)
        commands_sent.append(cmd)

    if wings is not None:
        cmd = _build_wings(parts=wings)
        await client.send_command(cmd)
        commands_sent.append(cmd)

    if filter_num is not None or filter_name is not None:
        cmd = _build_filter(filter_num=filter_num, name=filter_name)
        await client.send_command(cmd)
        commands_sent.append(cmd)

    # Step 3: Store to pool slot
    store_cmd = _build_store_matricks(pool_slot, overwrite=True)
    raw_store = await client.send_command_with_response(store_cmd)
    commands_sent.append(store_cmd)

    # Step 4: Label the pool object
    label_cmd = _build_label("matricks", pool_slot, name)
    raw_label = await client.send_command_with_response(label_cmd)
    commands_sent.append(label_cmd)

    return json.dumps({
        "commands_sent": commands_sent,
        "pool_slot": pool_slot,
        "name": name,
        "store_response": raw_store[:200],
        "label_response": raw_label[:200],
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.FILTER_MANAGE)
@_handle_errors
async def create_matricks_library(
    max_value: int = 4,
    start_slot: int = 2,
    confirm_destructive: bool = False,
) -> str:
    """
    Create a full MAtricks combinatorial library (DESTRUCTIVE).

    Generates every combination of Wings × Groups × Blocks × Interleave
    (values 0 to max_value) as XML with embedded appearance colors and
    imports into the MAtricks pool. Colors are instant — no telnet loop needed.

    25-color scheme: Wings=hue (Red/YellowGreen/Cyan/Blue/Magenta),
    Groups=brightness (100/80/60/45/30).

    With max_value=4: 5^4 = 625 pool items, named W0-G0-B0-I0 through W4-G4-B4-I4.

    Args:
        max_value: Upper bound for each property (default 4, gives 5^4=625 items).
        start_slot: First pool slot to import into (default 2, slot 1 is Reset).
        confirm_destructive: Must be True to execute (overwrites MAtricks pool entries).

    Returns:
        str: JSON with pool_items_created, color_scheme, first_slot, last_slot.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Create MAtricks Library overwrites MAtricks pool entries. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from datetime import datetime
    from pathlib import Path

    matricks_dir = Path(_srv._GMA2_DATA_ROOT) / "matricks"
    xml_filename = "matricks_combinatorial_library"

    # 25-color scheme: Wings=hue (5 hues), Groups=brightness (5 levels)
    wings_hues = {0: 0, 1: 72, 2: 144, 3: 216, 4: 288}
    groups_brightness = {0: 100, 1: 80, 2: 60, 3: 45, 4: 30}

    def _hsb_to_hex(hue: int, sat: int, bright: int) -> str:
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(hue / 360, sat / 100, bright / 100)
        return f"{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    # Generate XML with appearance colors embedded
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns="http://schemas.malighting.de/grandma2/xml/MA"'
        ' xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA'
        ' http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd"'
        ' major_vers="3" minor_vers="9" stream_vers="60">',
        f'\t<Info datetime="{now}" showfile="" />',
    ]

    total = (max_value + 1) ** 4
    index = 0
    for w in range(max_value + 1):
        for g in range(max_value + 1):
            h = wings_hues.get(w, 0)
            br = groups_brightness.get(g, 100)
            hex_color = _hsb_to_hex(h, 100, br)
            for b in range(max_value + 1):
                for i in range(max_value + 1):
                    name = f"W{w}-G{g}-B{b}-I{i}"
                    lines.append(f'\t<Matrix index="{index}" name="{name}">')
                    lines.append(f'\t\t<Appearance Color="{hex_color}" />')
                    lines.append(
                        f'\t\t<Settings wings="{w}" group_x="{g}"'
                        f' block_x="{b}" interleave="{i}" />'
                    )
                    lines.append("\t</Matrix>")
                    index += 1

    lines.append("</MA>")

    # Write XML to MA2 matricks directory
    xml_path = matricks_dir / f"{xml_filename}.xml"
    xml_path.write_text("\n".join(lines), encoding="utf-8")

    # Import via telnet — colors are embedded in XML, no telnet loop needed
    client = await _srv.get_client()

    # Pre-import availability check
    last_slot = start_slot + total - 1
    avail = await _srv._check_pool_slots(
        client, "MAtricks",
        start_from=start_slot, scan_up_to=last_slot,
    )
    availability_warning = None
    if avail["occupied_slots"]:
        availability_warning = {
            "slots_that_will_be_overwritten": len(avail["occupied_slots"]),
            "occupied": avail["occupied_slots"][:20],  # cap at 20 for readability
        }

    import_cmd = f'import "{xml_filename}" at matricks {start_slot}'
    response = await client.send_command_with_response(import_cmd)

    result: dict = {
        "pool_items_created": total,
        "total_slots": total,
        "first_slot": start_slot,
        "last_slot": last_slot,
        "naming_scheme": "W{wings}-G{groups}-B{blocks}-I{interleave}",
        "color_scheme": {
            "status": "embedded_in_xml",
            "mapping": "25 colors: Wings=hue (Red/YellowGreen/Cyan/Blue/Magenta), Groups=brightness (100/80/60/45/30)",
        },
        "max_value": max_value,
        "xml_file": str(xml_path),
        "import_response": response[:200],
        "risk_tier": "DESTRUCTIVE",
    }
    if availability_warning:
        result["availability_warning"] = availability_warning

    return json.dumps(result, indent=2)


async def _discover_filter_attributes() -> dict[str, list[str]]:
    """Discover actual attribute names from the current show's fixture library.

    Browses PresetTypes 1-7 at depth 2, collecting all attribute names.
    Returns a dict with the same shape as FILTER_ATTRIBUTES in constants.py.
    Falls back to FILTER_ATTRIBUTES if discovery fails.
    """
    from src.commands.constants import FILTER_ATTRIBUTES

    preset_type_names = ["dimmer", "position", "gobo", "color", "beam", "focus", "control"]
    discovered: dict[str, list[str]] = {}

    try:
        client = await _srv.get_client()
        for pt_id, cat_name in enumerate(preset_type_names, start=1):
            attrs: list[str] = []
            await _srv.navigate(client, "/")
            await _srv.navigate(client, f"10.2.{pt_id}")
            feat_list = await _srv.list_destination(client)
            feat_raw = feat_list.raw_response
            features = _srv._parse_preset_tree_list(feat_raw)

            for fi in range(1, len(features) + 1):
                await _srv.navigate(client, "/")
                await _srv.navigate(client, f"10.2.{pt_id}.{fi}")
                attr_list = await _srv.list_destination(client)
                attr_raw = attr_list.raw_response
                attr_entries = _srv._parse_preset_tree_list(attr_raw)
                for entry in attr_entries:
                    name = entry.get("name", "").upper()
                    if name and name not in attrs:
                        attrs.append(name)

            discovered[cat_name] = attrs if attrs else FILTER_ATTRIBUTES.get(cat_name, [])
        await _srv.navigate(client, "/")
    except Exception:
        # On any failure, return defaults
        return dict(FILTER_ATTRIBUTES)

    return discovered


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def discover_filter_attributes() -> str:
    """
    Discover actual filter attributes from the current show's fixture library (SAFE_READ).

    Browses PresetTypes 1-7 (Dimmer through Control) at depth 2 to collect
    attribute names from all patched fixture types. Returns a dict matching the
    shape of FILTER_ATTRIBUTES in constants.py but with show-specific values.

    Use this before create_filter_library if your show uses fixtures other than
    Mac 700 Profile Extended + Generic Dimmer (the defaults in FILTER_ATTRIBUTES).

    Returns:
        str: JSON dict mapping category names to attribute name lists.
    """
    discovered = await _srv._discover_filter_attributes()
    return json.dumps({
        "attributes": discovered,
        "total_attributes": sum(len(v) for v in discovered.values()),
        "note": "Pass these as fixture_attributes to create_filter_library for accurate filters.",
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.FILTER_MANAGE)
@_handle_errors
async def create_filter_library(
    start_slot: int = 3,
    include_combos: bool = True,
    include_exclusions: bool = True,
    include_vte: bool = False,
    fixture_attributes: dict[str, list[str]] | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Create a comprehensive Filter library with color-coded pool items (DESTRUCTIVE).

    Generates filters for each PresetType (Dimmer, Position, Gobo, Color, Beam,
    Focus, Control), useful multi-type combos, and "No X" exclusion filters.
    Each filter is color-coded by category and imported as individual XML files.

    Optionally generates Value/ValueTimes/Effects on/off variants for each base
    filter (7 combos per filter, excluding all-off). V/VT/E toggles are embedded
    in the XML as value="false", value_timing="false", effect="false" attributes.

    Slot layout (default start_slot=3):
      - Slots 3-9: Single PresetType filters (7 items)
      - Slots 10-16: Combo filters (7 items, if include_combos)
      - Slots 17-23: "No X" exclusion filters (7 items, if include_exclusions)
      - Slots 24+: V/VT/E variants (N_base × 7, if include_vte)

    Args:
        start_slot: First pool slot (default 3, preserving system filters 1-2).
        include_combos: Include multi-type combo filters (default True).
        include_exclusions: Include "No X" exclusion filters (default True).
        include_vte: Include Value/ValueTimes/Effects variants (default False).
            When True, generates 7 V/VT/E combos for each base filter.
        fixture_attributes: Show-specific attribute dict (same shape as FILTER_ATTRIBUTES).
            If None, uses hardcoded defaults (Mac 700 + Generic Dimmer).
            Call discover_filter_attributes() first to get accurate values for your show.
        confirm_destructive: Must be True to execute (overwrites filter pool entries).

    Returns:
        str: JSON with filters_created, slots, color_scheme summary.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Create Filter Library overwrites filter pool entries. "
                     "Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from datetime import datetime
    from pathlib import Path

    from src.commands.constants import (
        FILTER_ATTRIBUTES,
        FILTER_COLORS,
        FILTER_VTE_COMBOS,
    )

    importexport_dir = Path(_srv._GMA2_DATA_ROOT) / "importexport" / "filters"

    # Use provided fixture attributes or fall back to hardcoded defaults
    attrs_source = fixture_attributes if fixture_attributes else FILTER_ATTRIBUTES

    # Build attribute lists
    dimmer = attrs_source.get("dimmer", FILTER_ATTRIBUTES["dimmer"])
    position = attrs_source.get("position", FILTER_ATTRIBUTES["position"])
    gobo = attrs_source.get("gobo", FILTER_ATTRIBUTES["gobo"])
    color = attrs_source.get("color", FILTER_ATTRIBUTES["color"])
    beam = attrs_source.get("beam", FILTER_ATTRIBUTES["beam"])
    focus = attrs_source.get("focus", FILTER_ATTRIBUTES["focus"])
    control = attrs_source.get("control", FILTER_ATTRIBUTES["control"])
    all_attrs = dimmer + position + gobo + color + beam + focus + control

    # Build base filter definitions: (slot, name, attrs, cat)
    base_filters: list[tuple[int, str, list[str], str]] = []
    slot = start_slot

    for cat, attrs in [
        ("dimmer", dimmer), ("position", position), ("gobo", gobo),
        ("color", color), ("beam", beam), ("focus", focus), ("control", control),
    ]:
        base_filters.append((slot, cat.capitalize(), attrs, cat))
        slot += 1

    if include_combos:
        for name, attrs in [
            ("Dim+Pos", dimmer + position),
            ("Dim+Color", dimmer + color),
            ("Pos+Color", position + color),
            ("Pos+Gobo", position + gobo),
            ("Gobo+Beam", gobo + beam),
            ("Beam+Focus", beam + focus),
            ("Pos+Col+Gobo", position + color + gobo),
        ]:
            base_filters.append((slot, name, attrs, "combo"))
            slot += 1

    if include_exclusions:
        for name, attrs in [
            ("No Dimmer", [a for a in all_attrs if a not in dimmer]),
            ("No Position", [a for a in all_attrs if a not in position]),
            ("No Gobo", [a for a in all_attrs if a not in gobo]),
            ("No Color", [a for a in all_attrs if a not in color]),
            ("No Beam", [a for a in all_attrs if a not in beam]),
            ("No Focus", [a for a in all_attrs if a not in focus]),
            ("No Control", [a for a in all_attrs if a not in control]),
        ]:
            base_filters.append((slot, name, attrs, "exclude"))
            slot += 1

    # Build full filter list: base + optional V/VT/E variants
    # Each entry: (slot, name, attrs, cat, value, value_timing, effect)
    all_filters: list[tuple[int, str, list[str], str, bool, bool, bool]] = []
    for f_slot, f_name, f_attrs, f_cat in base_filters:
        all_filters.append((f_slot, f_name, f_attrs, f_cat, True, True, True))

    if include_vte:
        vte_slot = slot  # continue after base filters
        for _base_slot, base_name, f_attrs, f_cat in base_filters:
            for suffix, v, vt, e in FILTER_VTE_COMBOS:
                vte_name = f"{base_name} {suffix}"
                all_filters.append(
                    (vte_slot, vte_name, f_attrs, f_cat, v, vt, e)
                )
                vte_slot += 1

    # XML generation helper
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    xml_header = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns="http://schemas.malighting.de/grandma2/xml/MA"'
        ' xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA'
        ' http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd"'
        ' major_vers="3" minor_vers="9" stream_vers="60">\n'
        f'\t<Info datetime="{now}" showfile="" />\n'
    )

    client = await _srv.get_client()

    # Pre-import availability check
    last_filter_slot = all_filters[-1][0] if all_filters else start_slot
    avail = await _srv._check_pool_slots(
        client, "Filter",
        start_from=start_slot, scan_up_to=last_filter_slot,
    )
    availability_warning = None
    if avail["occupied_slots"]:
        availability_warning = {
            "slots_that_will_be_overwritten": len(avail["occupied_slots"]),
            "occupied": avail["occupied_slots"][:20],
        }

    results = []

    for f_slot, f_name, f_attrs, f_cat, f_v, f_vt, f_e in all_filters:
        color_hex = FILTER_COLORS[f_cat]

        # Build V/VT/E XML attributes (only emit false values)
        vte_parts = []
        if not f_v:
            vte_parts.append('value="false"')
        if not f_vt:
            vte_parts.append('value_timing="false"')
        if not f_e:
            vte_parts.append('effect="false"')
        vte_str = (" " + " ".join(vte_parts)) if vte_parts else ""

        attr_lines = "\n".join(
            f'\t\t\t<AttributeLink name="{a}" />' for a in f_attrs
        )
        filter_xml = (
            f'\t<Filter index="{f_slot - 1}"{vte_str} keep_filter="false">\n'
            f'\t\t<Appearance Color="{color_hex}" />\n'
            f"\t\t<Attributes>\n{attr_lines}\n\t\t</Attributes>\n"
            f"\t</Filter>"
        )
        xml_content = xml_header + filter_xml + "\n</MA>"

        fname = f"filter_{f_slot:03d}"
        fpath = importexport_dir / f"{fname}.xml"
        fpath.write_text(xml_content, encoding="utf-8")

        # Import (use 8.3 short path to avoid spaces in path)
        resp = await client.send_command_with_response(
            f'Import "{fname}" At Filter {f_slot}'
            " /path=C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/IMPORT~1/filters"
        )
        import_ok = "Error" not in resp

        # Label
        await client.send_command_with_response(
            f'Label Filter {f_slot} "{f_name}"'
        )

        # Apply appearance color via telnet (backup if XML color didn't take)
        r = int(color_hex[0:2], 16) * 100 // 255
        g = int(color_hex[2:4], 16) * 100 // 255
        b = int(color_hex[4:6], 16) * 100 // 255
        await client.send_command_with_response(
            f"Appearance Filter {f_slot} /r={r} /g={g} /b={b}"
        )

        results.append({
            "slot": f_slot,
            "name": f_name,
            "category": f_cat,
            "attributes": len(f_attrs),
            "vte": f"V={'on' if f_v else 'off'}"
                   f" VT={'on' if f_vt else 'off'}"
                   f" E={'on' if f_e else 'off'}",
            "import_ok": import_ok,
        })

    result_json: dict = {
        "filters_created": len(results),
        "base_filters": len(base_filters),
        "vte_variants": len(results) - len(base_filters),
        "first_slot": start_slot,
        "last_slot": all_filters[-1][0] if all_filters else start_slot,
        "filters": results,
        "color_scheme": {
            "dimmer": "FFCC00 (yellow)",
            "position": "0088FF (blue)",
            "gobo": "00CC44 (green)",
            "color": "FF00CC (magenta)",
            "beam": "FF6600 (orange)",
            "focus": "00CCCC (cyan)",
            "control": "999999 (grey)",
            "combo": "CC44FF (purple)",
            "exclude": "FF3333 (red)",
        },
        "xml_directory": str(importexport_dir),
        "risk_tier": "DESTRUCTIVE",
    }
    if availability_warning:
        result_json["availability_warning"] = availability_warning

    # Update filter_vte write-tracker (Gap 1 — VTE layer toggles have no telnet readback)
    if snap := _srv._orchestrator.last_snapshot:
        snap.filter_vte.update({"value": True, "value_timing": True, "effect": True})

    return json.dumps(result_json, indent=2)
