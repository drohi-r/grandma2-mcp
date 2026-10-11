"""MCP tools — import export. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
import os

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    export_object as build_export_object,
    import_object as build_import_object,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Tools 53–54 — Import / Export
# ============================================================

# Valid export types (live-validated on MA2 3.9.60.65)
_EXPORT_TYPES = {
    "group", "preset", "macro", "effect", "sequence", "view", "page",
    "camera", "layout", "form", "plugin", "matricks", "mask", "image",
    "executor", "timecode", "userprofile", "channel", "screen", "filter",
}

# Valid import types (screen excluded — Error #16 RESIZE FORBIDDEN on import)
_IMPORT_TYPES = {
    "group", "preset", "macro", "effect", "sequence", "view", "page",
    "camera", "layout", "form", "plugin", "matricks", "mask", "image",
    "executor", "timecode", "userprofile", "filter",
}

# Type-specific subfolders (informational — MA2 routes automatically)
# macros/ | effects/ | plugins/ | matricks/ | masks/ | importexport/ (default)
_GMA2_DATA_ROOT = os.environ.get(
    "GMA2_DATA_ROOT",
    r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60",
)
_IMPORT_EXPORT_DATA_ROOT = os.path.join(_GMA2_DATA_ROOT, "importexport")


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def export_objects(
    object_type: str,
    object_id: str,
    filename: str,
    style: str | None = None,
    overwrite: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Export objects from the show file to disk (DESTRUCTIVE — writes files).

    Files are written to the grandMA2 data directory. MA2 routes each type
    to its own subfolder automatically:
      - Macro → macros/    Effect → effects/    Plugin → plugins/
      - MAtricks → matricks/    Mask → masks/
      - All others → importexport/

    On this system: C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\

    Supported object types (19 validated):
      group, preset, macro, effect, sequence, view, page, camera, layout,
      form, plugin, matricks, mask, image, executor, timecode, userprofile,
      channel, screen

    Preset syntax for object_id:
      - Single preset:  "1.3"  (type 1=Dimmer, 2=Position, 3=Gobo, 4=Color,
                                 5=Beam, 6=Focus, 7=Control, 8=Shapers, 9=Video)
      - All of a type:  "1"    (exports all dimmer presets)
      - Range:          "1 thru 5"

    Args:
        object_type: Object type (case-insensitive)
        object_id: ID, preset ref ("1.3"), range ("1 thru 5"), or name (UserProfile)
        filename: Output filename — no extension, no path needed
        style: "csv" or "html" — default is xml
        overwrite: Replace existing file without prompting
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with command_sent, raw_response, risk_tier, data_path
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Export writes files to disk. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if object_type.lower() not in _srv._EXPORT_TYPES:
        return json.dumps({
            "error": (
                f"Invalid object_type '{object_type}'. "
                f"Valid types: {sorted(_srv._EXPORT_TYPES)}"
            ),
            "blocked": True,
        }, indent=2)

    if style is not None and style.lower() not in ("csv", "html"):
        return json.dumps(
            {"error": "style must be 'csv' or 'html' (omit for default xml)", "blocked": True},
            indent=2,
        )

    cmd = build_export_object(
        object_type,
        object_id,
        filename,
        overwrite=overwrite,
        noconfirm=True,
        style=style,
    )

    client = await _srv.get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "DESTRUCTIVE",
        "data_path": _srv._IMPORT_EXPORT_DATA_ROOT,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.FIXTURE_IMPORT)
@_handle_errors
async def import_objects(
    filename: str,
    destination_type: str,
    destination_id: str | None = None,
    quiet: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Import objects from a file into the show (DESTRUCTIVE — modifies show file).

    MA2 locates the file using the destination type to determine the correct
    subfolder automatically (same routing as export). The file must exist in
    the grandMA2 data directory before calling this tool.

    Files are read from: C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\
      - Macro → macros/    Effect → effects/    Plugin → plugins/
      - MAtricks → matricks/    Mask → masks/
      - All others → importexport/

    Supported destination types (17 validated):
      group, preset, macro, effect, sequence, view, page, camera, layout,
      form, plugin, matricks, mask, image, executor, timecode, userprofile

    (Screen is export-only — import gives RESIZE FORBIDDEN error.)

    Preset destination_id format: "T.N"  e.g. "1.99" = Dimmer slot 99

    Args:
        filename: Source filename — no extension, no path needed
        destination_type: Object type for placement (REQUIRED — MA2 Error #28 without it)
        destination_id: Slot number or preset ref ("T.N"). None = next free slot.
        quiet: Suppress MA2 feedback output during import
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Import modifies the show file. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if destination_type.lower() not in _srv._IMPORT_TYPES:
        return json.dumps({
            "error": (
                f"Invalid destination_type '{destination_type}'. "
                f"Valid types: {sorted(_srv._IMPORT_TYPES)}"
            ),
            "blocked": True,
        }, indent=2)

    cmd = build_import_object(
        filename,
        destination_type,
        destination_id,
        noconfirm=True,
        quiet=quiet,
    )

    client = await _srv.get_client()

    # Pre-import slot check — informational only
    slot_status: dict | None = None
    if destination_id is not None:
        try:
            slot_int = int(str(destination_id).split(".")[0])
            avail = await _srv._check_pool_slots(
                client, destination_type,
                start_from=slot_int, scan_up_to=slot_int,
            )
            is_occupied = any(
                s["slot"] == slot_int for s in avail["occupied_slots"]
            )
            slot_status = {"occupied": is_occupied}
            if is_occupied:
                match = next(
                    s for s in avail["occupied_slots"] if s["slot"] == slot_int
                )
                slot_status["previous_name"] = match["name"]
        except (ValueError, TypeError):
            pass  # non-numeric destination_id (e.g. preset "2.5")

    raw_response = await client.send_command_with_response(cmd)

    result: dict = {
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "DESTRUCTIVE",
    }
    if slot_status is not None:
        result["slot_status"] = slot_status

    return json.dumps(result, indent=2)
