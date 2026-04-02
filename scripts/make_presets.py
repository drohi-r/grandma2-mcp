"""
scripts/make_presets.py -- Build a complete preset library on the live grandMA2 console.

Creates 27 labeled presets across 4 types for all fixtures in the Toronto show:
  Dimmer  (1-5)  : Full, 75pct, Half, 25pct, Off          -- all fixtures
  Color   (1-10) : White, Red, Green, Blue, Amber, Cyan,   -- LB150 + Spot + Wash
                   Magenta, Yellow, WarmWhite, CoolWhite
  Position (1-5) : Home, FOH-Center, Stage-Left,           -- Spots only
                   Stage-Right, TopLight
  Gobo     (1-5) : Open, Gobo1, Gobo2, Gobo3, Gobo4        -- Spots only

Usage:
    python scripts/make_presets.py
    python scripts/make_presets.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

os.environ.setdefault("GMA_AUTH_BYPASS", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.server import (  # noqa: E402
    browse_preset_type,
    get_client,
    list_fixtures,
    navigate_console,
    store_new_preset,
)

# ---------------------------------------------------------------------------
# Fixture ranges in the Toronto show
# ---------------------------------------------------------------------------
ALL_FIXTURES = "selfix fixture 1 thru 9001"          # all patched
COLOR_FIXTURES_A = "selfix fixture 411 thru 414"      # LB150
COLOR_FIXTURES_B = "+ fixture 601 thru 616"            # Spot + Wash
SPOT_FIXTURES = "selfix fixture 601 thru 606"          # moving heads only

# PRESET_TYPE_NUM used for label commands
PRESET_TYPE_NUM = {"dimmer": 1, "position": 2, "gobo": 3, "color": 4}

_WIDTH = 72
_DRY_RUN = False


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def banner(title: str) -> None:
    print()
    print("=" * _WIDTH)
    print(f"  {title}")
    print("=" * _WIDTH)


def section(label: str) -> None:
    pad = _WIDTH - len(label) - 4
    print(f"\n-- {label} {'-' * max(pad, 0)}")


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def info(msg: str) -> None:
    print(f"  --> {msg}")


def warn(msg: str) -> None:
    print(f"  [!]  {msg}")


def skip(msg: str) -> None:
    print(f"  [-]  {msg}")


# ---------------------------------------------------------------------------
# Raw telnet helper
# ---------------------------------------------------------------------------

async def send(cmd: str) -> str:
    """Send a raw telnet command and return the response."""
    if _DRY_RUN:
        print(f"      DRY: {cmd}")
        return ""
    client = await get_client()
    return await client.send_command_with_response(cmd)


# ---------------------------------------------------------------------------
# Core preset-creation helper
# ---------------------------------------------------------------------------

_created: list[dict] = []


async def make_preset(
    preset_type: str,
    slot: int,
    name: str,
    selection_cmds: list[str],
    attr_cmds: list[str],
) -> bool:
    """
    Select fixtures, set attributes, store preset, label it, clear programmer.
    Returns True on success.
    """
    await navigate_console("/")

    # Select fixtures
    for cmd in selection_cmds:
        await send(cmd)

    # Set attribute values in programmer
    for cmd in attr_cmds:
        await send(cmd)

    # Store preset
    if not _DRY_RUN:
        result = await store_new_preset(
            preset_type, slot,
            overwrite=True,
            confirm_destructive=True,
        )
        data = json.loads(result)
        if "error" in data:
            warn(f"Store failed [{preset_type}.{slot}]: {data['error'][:60]}")
            await send("clear")
            return False

    # Label the preset
    ptype_num = PRESET_TYPE_NUM[preset_type]
    label_cmd = f'label preset {ptype_num}.{slot} "{name}"'
    await send(label_cmd)

    # Clear programmer
    await send("clear")

    ok(f"  {preset_type:<10} slot {slot:<3} {name}")
    _created.append({"type": preset_type, "slot": slot, "name": name})
    return True


# ---------------------------------------------------------------------------
# Phase 1: Discovery
# ---------------------------------------------------------------------------

async def discover() -> dict:
    """
    Discover fixture count and attribute names for color/position/gobo.
    Returns dict with keys: fixture_count, color_attrs, pan_attr, tilt_attr, gobo_attr
    """
    section("Phase 1 -- Discovery")

    # Fixture count
    result = await list_fixtures()
    data = json.loads(result)
    raw = data.get("raw_response", "")
    import re
    fix_ids = re.findall(r"Fixture\s+(\d+)", re.sub(r"\x1b\[[0-9;]*m", "", raw))
    info(f"Found {len(fix_ids)} patched fixture(s)")

    # Color attribute names -- browse preset type 4 at depth 2 (features + attrs)
    color_r = color_g = color_b = None
    try:
        # Select a color fixture first so the tree reflects correct fixture profile
        await send("selfix fixture 601")
        browse_result = await browse_preset_type(4, depth=2)
        bd = json.loads(browse_result)
        attrs_found: list[str] = []
        for feat in bd.get("features", []):
            for attr in feat.get("attributes", []):
                attrs_found.append(attr["name"])
        info(f"Color attrs found: {attrs_found[:6]}")
        # Prefer COLORRGB1/2/3 pattern
        rgb = [a for a in attrs_found if "RGB" in a.upper() or "RED" in a.upper()]
        if len(rgb) >= 3:
            color_r, color_g, color_b = rgb[0], rgb[1], rgb[2]
        elif len(rgb) >= 1:
            color_r = rgb[0]
    except Exception as e:
        warn(f"Color discovery failed: {e}")

    # Fall back to standard MA2 names
    color_r = color_r or "ColorRgb1"
    color_g = color_g or "ColorRgb2"
    color_b = color_b or "ColorRgb3"
    info(f"Using color attrs: R={color_r}  G={color_g}  B={color_b}")

    # Position attribute names -- browse preset type 2
    pan_attr = tilt_attr = None
    try:
        await send("selfix fixture 601")
        browse_result = await browse_preset_type(2, depth=2)
        bd = json.loads(browse_result)
        attrs_found = []
        for feat in bd.get("features", []):
            for attr in feat.get("attributes", []):
                attrs_found.append(attr["name"])
        info(f"Position attrs found: {attrs_found[:4]}")
        pan_candidates = [a for a in attrs_found if "PAN" in a.upper()]
        tilt_candidates = [a for a in attrs_found if "TILT" in a.upper()]
        pan_attr = pan_candidates[0] if pan_candidates else None
        tilt_attr = tilt_candidates[0] if tilt_candidates else None
    except Exception as e:
        warn(f"Position discovery failed: {e}")

    pan_attr = pan_attr or "Pan"
    tilt_attr = tilt_attr or "Tilt"
    info(f"Using position attrs: Pan={pan_attr}  Tilt={tilt_attr}")

    # Gobo attribute name -- browse preset type 3
    gobo_attr = None
    try:
        await send("selfix fixture 601")
        browse_result = await browse_preset_type(3, depth=2)
        bd = json.loads(browse_result)
        attrs_found = []
        for feat in bd.get("features", []):
            for attr in feat.get("attributes", []):
                attrs_found.append(attr["name"])
        info(f"Gobo attrs found: {attrs_found[:4]}")
        gobo_candidates = [a for a in attrs_found if "GOBO" in a.upper()]
        gobo_attr = gobo_candidates[0] if gobo_candidates else None
    except Exception as e:
        warn(f"Gobo discovery failed: {e}")

    gobo_attr = gobo_attr or "Gobo1"
    info(f"Using gobo attr: {gobo_attr}")

    await navigate_console("/")
    await send("clear")

    return {
        "fixture_count": len(fix_ids),
        "color_r": color_r,
        "color_g": color_g,
        "color_b": color_b,
        "pan_attr": pan_attr,
        "tilt_attr": tilt_attr,
        "gobo_attr": gobo_attr,
    }


# ---------------------------------------------------------------------------
# Phase 2: Dimmer presets
# ---------------------------------------------------------------------------

DIMMER_PRESETS = [
    (1, "Full",  100),
    (2, "75pct",  75),
    (3, "Half",   50),
    (4, "25pct",  25),
    (5, "Off",     0),
]


async def make_dimmer_presets() -> None:
    section("Phase 2 -- Dimmer presets (all fixtures)")
    for slot, name, level in DIMMER_PRESETS:
        await make_preset(
            preset_type="dimmer",
            slot=slot,
            name=name,
            selection_cmds=[ALL_FIXTURES],
            attr_cmds=[f"at {level}"],
        )


# ---------------------------------------------------------------------------
# Phase 3: Color presets
# ---------------------------------------------------------------------------

def build_color_presets(r_attr: str, g_attr: str, b_attr: str) -> list[tuple]:
    """Returns list of (slot, name, r, g, b) tuples."""
    return [
        (1,  "White",      100, 100, 100),
        (2,  "Red",        100,   0,   0),
        (3,  "Green",        0, 100,   0),
        (4,  "Blue",         0,   0, 100),
        (5,  "Amber",      100,  55,   0),
        (6,  "Cyan",         0, 100, 100),
        (7,  "Magenta",    100,   0, 100),
        (8,  "Yellow",     100, 100,   0),
        (9,  "WarmWhite",  100,  78,  40),
        (10, "CoolWhite",   80,  90, 100),
    ]


async def make_color_presets(r_attr: str, g_attr: str, b_attr: str) -> None:
    section("Phase 3 -- Color presets (LB150 + Spot + Wash)")
    for slot, name, r, g, b in build_color_presets(r_attr, g_attr, b_attr):
        await make_preset(
            preset_type="color",
            slot=slot,
            name=name,
            selection_cmds=[COLOR_FIXTURES_A, COLOR_FIXTURES_B],
            attr_cmds=[
                f'attribute "{r_attr}" at {r}',
                f'attribute "{g_attr}" at {g}',
                f'attribute "{b_attr}" at {b}',
            ],
        )


# ---------------------------------------------------------------------------
# Phase 4: Position presets
# ---------------------------------------------------------------------------

POSITION_PRESETS = [
    (1, "Home",        50, 50),
    (2, "FOH-Center",  50, 35),
    (3, "Stage-Left",  25, 35),
    (4, "Stage-Right", 75, 35),
    (5, "TopLight",    50,  0),
]


async def make_position_presets(pan_attr: str, tilt_attr: str) -> None:
    section("Phase 4 -- Position presets (Spots 601-606)")
    for slot, name, pan, tilt in POSITION_PRESETS:
        await make_preset(
            preset_type="position",
            slot=slot,
            name=name,
            selection_cmds=[SPOT_FIXTURES],
            attr_cmds=[
                f'attribute "{pan_attr}" at {pan}',
                f'attribute "{tilt_attr}" at {tilt}',
            ],
        )


# ---------------------------------------------------------------------------
# Phase 5: Gobo presets
# ---------------------------------------------------------------------------

GOBO_PRESETS = [
    (1, "Open",  0),
    (2, "Gobo1", 1),
    (3, "Gobo2", 2),
    (4, "Gobo3", 3),
    (5, "Gobo4", 4),
]


async def make_gobo_presets(gobo_attr: str) -> None:
    section("Phase 5 -- Gobo presets (Spots 601-606)")
    for slot, name, gobo_val in GOBO_PRESETS:
        await make_preset(
            preset_type="gobo",
            slot=slot,
            name=name,
            selection_cmds=[SPOT_FIXTURES],
            attr_cmds=[f'attribute "{gobo_attr}" at {gobo_val}'],
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(dry_run: bool) -> None:
    global _DRY_RUN
    _DRY_RUN = dry_run

    print()
    print("grandMA2 Preset Library Builder")
    print(f"Console : {os.getenv('GMA_HOST', '127.0.0.1')}:{os.getenv('GMA_PORT', '30000')}")
    if dry_run:
        print("Mode    : DRY RUN (no telnet commands sent)")
    print()

    # Connect
    info("Connecting to console...")
    client = await get_client()
    if client is None:
        print("\nx Could not connect. Check GMA_HOST in .env.")
        sys.exit(1)
    ok("Connected.\n")

    t0 = time.perf_counter()

    # Discovery
    disc = await discover()

    # Create presets
    await make_dimmer_presets()
    await make_color_presets(disc["color_r"], disc["color_g"], disc["color_b"])
    await make_position_presets(disc["pan_attr"], disc["tilt_attr"])
    await make_gobo_presets(disc["gobo_attr"])

    elapsed = time.perf_counter() - t0

    # Summary
    banner("PRESET LIBRARY COMPLETE")
    by_type: dict[str, list[dict]] = {}
    for p in _created:
        by_type.setdefault(p["type"], []).append(p)
    for ptype, presets in by_type.items():
        pnum = PRESET_TYPE_NUM[ptype]
        print(f"  Preset {pnum} ({ptype.upper()}): {len(presets)} preset(s)")
        for p in presets:
            print(f"    slot {p['slot']:<3}  {p['name']}")
        print()
    print(f"  Total   : {len(_created)} presets in {elapsed:.1f}s")
    if not dry_run:
        print()
        print("  Check the console: open each Preset pool to verify labels.")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build grandMA2 preset library")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print commands without sending to console",
    )
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
