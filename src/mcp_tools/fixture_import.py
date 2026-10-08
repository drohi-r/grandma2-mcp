"""MCP tools — fixture import. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
from datetime import UTC

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    import_fixture_type_cmd as build_import_fixture_type_cmd,
    import_layer_cmd as build_import_layer_cmd,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Tools 74–76 — Fixture Type / Layer Import + XML Generation
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.FIXTURE_IMPORT)
@_handle_errors
async def import_fixture_type(
    manufacturer: str,
    fixture: str,
    mode: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Import a fixture type from the MA2 library into the show (DESTRUCTIVE).

    Navigates to EditSetup/FixtureTypes context, imports the fixture type
    by 'manufacturer@fixture@mode' key, then returns to root context.

    Use list_library(library_type="fixture") first to find the exact key values.

    Args:
        manufacturer: Manufacturer name exactly as in MA2 library (e.g. "Martin", "Generic")
        fixture: Fixture model name (e.g. "Mac700Profile_Extended")
        mode: Mode name (e.g. "Extended", "Standard")
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with steps list (command + response per step), fixture_key, risk_tier
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Import fixture type modifies the show. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()
    sequence = [
        'ChangeDest "EditSetup"',
        'ChangeDest "FixtureTypes"',
        build_import_fixture_type_cmd(manufacturer, fixture, mode),
        'ChangeDest /',
    ]
    steps = []
    for cmd in sequence:
        raw = await client.send_command_with_response(cmd)
        steps.append({"command": cmd, "response": raw})

    return json.dumps({
        "steps": steps,
        "fixture_key": f"{manufacturer}@{fixture}@{mode}",
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.FIXTURE_IMPORT)
@_handle_errors
async def import_fixture_layer(
    filename: str,
    layer_index: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Import a fixture layer XML file into the show patch (DESTRUCTIVE).

    Navigates to EditSetup/Layers context, imports the XML layer file,
    then returns to root context. Use generate_fixture_layer_xml to
    create the XML file before calling this tool.

    The file must exist in the MA2 importexport directory:
      C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\importexport\\

    Args:
        filename: Layer XML filename without extension or path
        layer_index: Target layer slot. None = MA2 picks next free slot
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with steps list (command + response per step), filename, risk_tier
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Import fixture layer modifies the show patch. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()
    sequence = [
        'ChangeDest "EditSetup"',
        'ChangeDest "Layers"',
        build_import_layer_cmd(filename, layer_index),
        'ChangeDest /',
    ]
    steps = []
    for cmd in sequence:
        raw = await client.send_command_with_response(cmd)
        steps.append({"command": cmd, "response": raw})

    return json.dumps({
        "steps": steps,
        "filename": filename,
        "layer_index": layer_index,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def generate_fixture_layer_xml(
    filename: str,
    layer_name: str,
    layer_index: int,
    fixtures: list[dict],
    showfile: str = "grandma2",
    overwrite: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Generate a grandMA2 fixture layer XML file and save it to the importexport directory (DESTRUCTIVE).

    The output file can be imported immediately using import_fixture_layer.
    No telnet connection required — this tool writes a local file only.

    Output directory:
      C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\importexport\\

    Each fixture dict must contain:
        fixture_id (int): grandMA2 fixture ID (e.g. 111)
        name (str): Display name (e.g. "Dim 1" or "Mac 700 1")
        fixture_type_no (int): Fixture type number from list_fixture_types()
        fixture_type_name (str): Display name of the fixture type
        dmx_address (int): 1-based DMX start address within its universe
        num_channels (int): Total DMX channel count for this fixture type

    Args:
        filename: Output filename without extension
        layer_name: Layer display name shown in MA2 UI
        layer_index: Layer index number (1-based) for the <Layer> XML element
        fixtures: List of fixture parameter dicts (see schema above)
        showfile: Show name embedded in XML <Info> element
        overwrite: If True, overwrite existing file; if False, return error on conflict
        confirm_destructive: Must be True to execute (writes files to console importexport directory)

    Returns:
        str: JSON with file_path, filename, fixture_count, layer_index, layer_name
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Generate Fixture Layer XML writes files to disk. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    import os
    from datetime import datetime
    from xml.dom import minidom
    from xml.etree.ElementTree import Element, SubElement, tostring

    output_dir = (
        r"C:\ProgramData\MA Lighting Technologies"
        r"\grandma\gma2_V_3.9.60\importexport"
    )
    file_path = os.path.join(output_dir, f"{filename}.xml")

    if os.path.exists(file_path) and not overwrite:
        return json.dumps({
            "error": (
                f"File already exists: {file_path}. "
                "Pass overwrite=True to replace it."
            ),
        }, indent=2)

    root = Element("MA", {
        "major_vers": "3",
        "minor_vers": "9",
        "stream_vers": "60",
    })
    SubElement(root, "Info", {
        "datetime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S"),
        "showfile": showfile,
    })
    layer_el = SubElement(root, "Layer", {
        "index": str(layer_index),
        "name": layer_name,
    })

    for idx, fx in enumerate(fixtures):
        fx_el = SubElement(layer_el, "Fixture", {
            "index": str(idx),
            "name": fx["name"],
            "fixture_id": str(fx["fixture_id"]),
        })
        ft_el = SubElement(fx_el, "FixtureType", {"name": fx["fixture_type_name"]})
        SubElement(ft_el, "No").text = str(fx["fixture_type_no"])

        sf_el = SubElement(fx_el, "SubFixture", {
            "index": "0",
            "react_to_grandmaster": "true",
            "color": "ffffff",
        })
        patch_el = SubElement(sf_el, "Patch")
        SubElement(patch_el, "Address").text = str(fx["dmx_address"])

        pos_el = SubElement(sf_el, "AbsolutePosition")
        SubElement(pos_el, "Location", {"x": "0", "y": "0", "z": "0"})
        SubElement(pos_el, "Rotation", {"x": "0", "y": "-0", "z": "0"})
        SubElement(pos_el, "Scaling", {"x": "1", "y": "1", "z": "1"})

        for ch in range(fx["num_channels"]):
            SubElement(sf_el, "Channel", {"index": str(ch)})

    raw_xml = tostring(root, encoding="unicode")
    pretty_bytes = minidom.parseString(raw_xml).toprettyxml(indent="  ", encoding="utf-8")
    # Replace minidom's XML declaration (includes standalone attr) with a clean one
    lines = pretty_bytes.split(b"\n")
    xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>\n' + b"\n".join(lines[1:])

    os.makedirs(output_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(xml_bytes)

    return json.dumps({
        "file_path": file_path,
        "filename": filename,
        "fixture_count": len(fixtures),
        "layer_index": layer_index,
        "layer_name": layer_name,
    }, indent=2)
