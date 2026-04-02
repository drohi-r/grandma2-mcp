"""
Generate a comprehensive grandMA2 Filter library with color-coded pool items.

Creates filters for each PresetType, useful combos, and "No X" exclusions.
Optionally generates Value/ValueTimes/Effects on/off variants for each filter.
Each filter is color-coded by category using MA2 Appearance commands.

Usage:
    PYTHONPATH=. python scripts/create_filter_library.py
    PYTHONPATH=. python scripts/create_filter_library.py --color-only   # re-apply colors only
    PYTHONPATH=. python scripts/create_filter_library.py --include-vte  # add V/VT/E variants
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from src.commands.constants import FILTER_ATTRIBUTES, FILTER_COLORS, FILTER_VTE_COMBOS

# ── Derive attribute lists from shared constants ─────────────────────────

DIMMER = FILTER_ATTRIBUTES["dimmer"]
POSITION = FILTER_ATTRIBUTES["position"]
GOBO = FILTER_ATTRIBUTES["gobo"]
COLOR = FILTER_ATTRIBUTES["color"]
BEAM = FILTER_ATTRIBUTES["beam"]
FOCUS = FILTER_ATTRIBUTES["focus"]
CONTROL = FILTER_ATTRIBUTES["control"]

ALL_ATTRS = DIMMER + POSITION + GOBO + COLOR + BEAM + FOCUS + CONTROL

COLORS = FILTER_COLORS

# ── Filter definitions ──────────────────────────────────────────────────
# (pool_slot, name, attributes, color_category)

FILTERS: list[tuple[int, str, list[str], str]] = [
    # ── Single PresetType filters (slots 3-9) ───────────────────────
    (3,  "Dimmer",    DIMMER,    "dimmer"),
    (4,  "Position",  POSITION,  "position"),
    (5,  "Gobo",      GOBO,      "gobo"),
    (6,  "Color",     COLOR,     "color"),
    (7,  "Beam",      BEAM,      "beam"),
    (8,  "Focus",     FOCUS,     "focus"),
    (9,  "Control",   CONTROL,   "control"),

    # ── Useful combos (slots 10-16) ─────────────────────────────────
    (10, "Dim+Pos",       DIMMER + POSITION,               "combo"),
    (11, "Dim+Color",     DIMMER + COLOR,                   "combo"),
    (12, "Pos+Color",     POSITION + COLOR,                 "combo"),
    (13, "Pos+Gobo",      POSITION + GOBO,                  "combo"),
    (14, "Gobo+Beam",     GOBO + BEAM,                      "combo"),
    (15, "Beam+Focus",    BEAM + FOCUS,                     "combo"),
    (16, "Pos+Col+Gobo",  POSITION + COLOR + GOBO,          "combo"),

    # ── "No X" exclusion filters (slots 17-23) ─────────────────────
    (17, "No Dimmer",   [a for a in ALL_ATTRS if a not in DIMMER],   "exclude"),
    (18, "No Position", [a for a in ALL_ATTRS if a not in POSITION], "exclude"),
    (19, "No Gobo",     [a for a in ALL_ATTRS if a not in GOBO],     "exclude"),
    (20, "No Color",    [a for a in ALL_ATTRS if a not in COLOR],    "exclude"),
    (21, "No Beam",     [a for a in ALL_ATTRS if a not in BEAM],     "exclude"),
    (22, "No Focus",    [a for a in ALL_ATTRS if a not in FOCUS],    "exclude"),
    (23, "No Control",  [a for a in ALL_ATTRS if a not in CONTROL],  "exclude"),
]


def generate_filter_xml(
    slot: int,
    attrs: list[str],
    color_hex: str,
    *,
    value: bool = True,
    value_timing: bool = True,
    effect: bool = True,
) -> str:
    """Generate MA2 XML for a single filter.

    Args:
        slot: Pool slot number (1-based).
        attrs: List of AttributeLink names.
        color_hex: Hex color (RRGGBB, no #).
        value: Values layer toggle (default True = on).
        value_timing: ValueTimes layer toggle (default True = on).
        effect: Effects layer toggle (default True = on).
    """
    # MA2 omits attributes that are true (default). Only emit false ones.
    vte_parts = []
    if not value:
        vte_parts.append('value="false"')
    if not value_timing:
        vte_parts.append('value_timing="false"')
    if not effect:
        vte_parts.append('effect="false"')
    vte_str = (" " + " ".join(vte_parts)) if vte_parts else ""

    attr_lines = "\n".join(
        f'\t\t\t<AttributeLink name="{a}" />' for a in attrs
    )
    return f"""\t<Filter index="{slot - 1}"{vte_str} keep_filter="false">
\t\t<Appearance Color="{color_hex}" />
\t\t<Attributes>
{attr_lines}
\t\t</Attributes>
\t</Filter>"""


def generate_library_xml() -> str:
    """Generate the complete filter library XML file."""
    header = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns="http://schemas.malighting.de/grandma2/xml/MA" '
        'xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA '
        'http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd" '
        'major_vers="3" minor_vers="9" stream_vers="60">\n'
        '\t<Info datetime="2026-03-11T15:00:00" showfile="claude_ma2_ctrl" />'
    )

    filter_blocks = []
    for slot, name, attrs, cat in FILTERS:
        color = COLORS[cat]
        filter_blocks.append(generate_filter_xml(slot, attrs, color))

    return header + "\n" + "\n".join(filter_blocks) + "\n</MA>"


def build_vte_filters(
    base_filters: list[tuple[int, str, list[str], str]],
    start_slot: int = 24,
) -> list[tuple[int, str, list[str], str, bool, bool, bool]]:
    """Build V/VT/E variant filter definitions from base filters.

    Returns list of (slot, name, attrs, color_cat, value, value_timing, effect).
    """
    vte_filters = []
    slot = start_slot
    for _base_slot, base_name, attrs, cat in base_filters:
        for suffix, v, vt, e in FILTER_VTE_COMBOS:
            name = f"{base_name} {suffix}"
            vte_filters.append((slot, name, attrs, cat, v, vt, e))
            slot += 1
    return vte_filters


def _wrap_xml(filter_xml: str) -> str:
    """Wrap a filter XML fragment in the MA2 XML envelope."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns="http://schemas.malighting.de/grandma2/xml/MA" '
        'xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA '
        'http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd" '
        'major_vers="3" minor_vers="9" stream_vers="60">\n'
        '\t<Info datetime="2026-03-11T15:00:00" showfile="claude_ma2_ctrl" />\n'
        + filter_xml
        + "\n</MA>"
    )


async def _import_filter(
    client,
    importexport_dir: Path,
    slot: int,
    name: str,
    attrs: list[str],
    color_hex: str,
    *,
    value: bool = True,
    value_timing: bool = True,
    effect: bool = True,
) -> bool:
    """Generate XML, write to disk, import, label, and color a single filter."""
    filter_xml = generate_filter_xml(
        slot, attrs, color_hex,
        value=value, value_timing=value_timing, effect=effect,
    )
    fname = f"filter_{slot:03d}"
    fpath = importexport_dir / f"{fname}.xml"
    fpath.write_text(_wrap_xml(filter_xml), encoding="utf-8")

    resp = await client.send_command_with_response(
        f'Import "{fname}" At Filter {slot}'
        " /path=C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/IMPORT~1/filters"
    )
    error = "Error" in resp
    status = "ERROR" if error else "OK"
    print(f"  Filter {slot:3d} {name:20s} | {status}")
    if error:
        print(f"    {resp.strip()}")

    # Label
    await client.send_command_with_response(f'Label Filter {slot} "{name}"')

    # Appearance color
    r = int(color_hex[0:2], 16) * 100 // 255
    g = int(color_hex[2:4], 16) * 100 // 255
    b = int(color_hex[4:6], 16) * 100 // 255
    await client.send_command_with_response(
        f"Appearance Filter {slot} /r={r} /g={g} /b={b}"
    )
    return not error


async def import_and_label():
    """Import filter library XML and label each pool item."""
    from src.telnet_client import GMA2TelnetClient

    importexport_dir = Path(
        "c:/ProgramData/MA Lighting Technologies/grandma/"
        "gma2_V_3.9.60/importexport/filters"
    )

    client = GMA2TelnetClient("127.0.0.1", 30000)
    await client.connect()
    await client.login()

    color_only = "--color-only" in sys.argv
    include_vte = "--include-vte" in sys.argv

    if not color_only:
        # Import base filters
        print("Importing base filters...")
        for slot, name, attrs, cat in FILTERS:
            await _import_filter(
                client, importexport_dir, slot, name, attrs, COLORS[cat],
            )

        # Import V/VT/E variants
        if include_vte:
            vte_filters = build_vte_filters(FILTERS)
            print(f"\nImporting {len(vte_filters)} V/VT/E variant filters...")
            for slot, name, attrs, cat, v, vt, e in vte_filters:
                await _import_filter(
                    client, importexport_dir, slot, name, attrs, COLORS[cat],
                    value=v, value_timing=vt, effect=e,
                )
    else:
        # Color-only mode: re-apply appearance colors
        print("Applying appearance colors...")
        for slot, name, attrs, cat in FILTERS:
            color_hex = COLORS[cat]
            r = int(color_hex[0:2], 16) * 100 // 255
            g = int(color_hex[2:4], 16) * 100 // 255
            b = int(color_hex[4:6], 16) * 100 // 255
            await client.send_command_with_response(
                f"Appearance Filter {slot} /r={r} /g={g} /b={b}"
            )
            print(f"  Filter {slot:2d} {name:15s} | r={r:3d} g={g:3d} b={b:3d}")

    # Final listing
    print("\n=== Final Filter Pool ===")
    resp = await client.send_command_with_response("List Filter")
    print(resp)

    await client.disconnect()
    total = len(FILTERS)
    if include_vte and not color_only:
        total += len(FILTERS) * len(FILTER_VTE_COMBOS)
    print(f"\nDone! Created {total} filter pool items.")


if __name__ == "__main__":
    asyncio.run(import_and_label())
