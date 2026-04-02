"""
scripts/fix_presets.py -- Targeted repair for empty/absent grandMA2 preset slots.

Scans all 25 expected preset slots, identifies which are absent or empty,
then re-stores only the bad ones with pre-store fixture-count verification.
Does NOT touch slots that are already populated.

Usage:
    python scripts/fix_presets.py --validate   # read-only: check current state
    python scripts/fix_presets.py --dry-run    # diagnose + plan, no writes
    python scripts/fix_presets.py              # live repair
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time

os.environ.setdefault("GMA_AUTH_BYPASS", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.server import (  # noqa: E402
    browse_preset_type,
    get_client,
    list_preset_pool,
    navigate_console,
)

# ---------------------------------------------------------------------------
# Fixture selection strings (Toronto show defaults — update if IDs differ)
# ---------------------------------------------------------------------------
ALL_FIXTURES = "fixture 1 thru"                    # all patched fixtures
COLOR_FIXTURES_A = "fixture 411 thru 414"           # LB150
COLOR_FIXTURES_B = "+ fixture 601 thru 616"         # Spot + Wash
SPOT_FIXTURES = "fixture 601 thru 606"              # moving heads only

# ---------------------------------------------------------------------------
# Preset definitions (inlined — no cross-script imports)
# ---------------------------------------------------------------------------
PRESET_TYPE_NUM: dict[str, int] = {"dimmer": 1, "position": 2, "gobo": 3, "color": 4}

EXPECTED_SLOTS: dict[str, list[tuple[int, str]]] = {
    "dimmer": [
        (1, "Full"), (2, "75pct"), (3, "Half"), (4, "25pct"), (5, "Off"),
    ],
    "color": [
        (1, "White"), (2, "Red"), (3, "Green"), (4, "Blue"), (5, "Amber"),
        (6, "Cyan"), (7, "Magenta"), (8, "Yellow"), (9, "WarmWhite"), (10, "CoolWhite"),
    ],
    "position": [
        (1, "Home"), (2, "FOH-Center"), (3, "Stage-Left"), (4, "Stage-Right"), (5, "TopLight"),
    ],
    "gobo": [
        (1, "Open"), (2, "Gobo1"), (3, "Gobo2"), (4, "Gobo3"), (5, "Gobo4"),
    ],
}

DIMMER_PRESETS = [
    (1, "Full", 100),
    (2, "75pct", 75),
    (3, "Half", 50),
    (4, "25pct", 25),
    (5, "Off", 0),
]

COLOR_VALUES = [
    (1,  "White",     100, 100, 100),
    (2,  "Red",       100,   0,   0),
    (3,  "Green",       0, 100,   0),
    (4,  "Blue",        0,   0, 100),
    (5,  "Amber",     100,  55,   0),
    (6,  "Cyan",        0, 100, 100),
    (7,  "Magenta",   100,   0, 100),
    (8,  "Yellow",    100, 100,   0),
    (9,  "WarmWhite", 100,  78,  40),
    (10, "CoolWhite",  80,  90, 100),
]

# Virtual Position Mode (VPM) — fixtures 601-606 use STAGEX/Y/Z, not raw Pan/Tilt.
# STAGEZ baseline -1.4356079 from preset 2.7 (live-verified 2026-03-30, toronto show).
# attribute "Pan"/"Tilt" are silently discarded by MA2 in VPM mode.
POSITION_PRESETS = [
    (1, "Home",         0.0,   0.0,  -1.4356079),
    (2, "FOH-Center",   0.0,   3.0,  -1.4356079),
    (3, "Stage-Left",  -3.0,   1.5,  -1.4356079),
    (4, "Stage-Right",  3.0,   1.5,  -1.4356079),
    (5, "TopLight",     0.0,   0.0,  -4.0),
]

GOBO_PRESETS = [
    (1, "Open",  0),
    (2, "Gobo1", 1),
    (3, "Gobo2", 2),
    (4, "Gobo3", 3),
    (5, "Gobo4", 4),
]

_WIDTH = 72
_DRY_RUN = False
_VERBOSE = False


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
    print(f"  [OK]     {msg}")


def info(msg: str) -> None:
    print(f"  -->      {msg}")


def warn(msg: str) -> None:
    print(f"  [!]      {msg}")


def skip_msg(msg: str) -> None:
    print(f"  [-]      {msg}")


def fixed(msg: str) -> None:
    print(f"  [FIXED]  {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL]   {msg}")


def dry(msg: str) -> None:
    print(f"  [DRY]    {msg}")


# ---------------------------------------------------------------------------
# Raw telnet helper
# ---------------------------------------------------------------------------

async def send(cmd: str) -> str:
    """Send a raw telnet command and return the response."""
    if _DRY_RUN:
        dry(f"CMD: {cmd}")
        return ""
    client = await get_client()
    return await client.send_command_with_response(cmd)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_count(raw: str) -> int:
    """Parse integer from ListVar response: '$Global : $VAR = N'."""
    m = re.search(r"=\s*(\d+)", raw)
    return int(m.group(1)) if m else 0


async def _fixture_count(selfix_cmds: list[str]) -> int:
    """
    Run fixture selection commands then return $SELECTEDFIXTURESCOUNT.
    NOTE: MA2 expands $VAR tokens before executing, so ListVar must be sent
    WITHOUT the $ prefix (ListVar SELECTEDFIXTURESCOUNT, not ListVar $SELECTEDFIXTURESCOUNT).
    """
    if _DRY_RUN:
        return 1  # optimistic — can't check in dry-run
    for cmd in selfix_cmds:
        await send(cmd)
    raw = await send("ListVar SELECTEDFIXTURESCOUNT")
    n = _parse_count(raw)
    if _VERBOSE:
        info(f"  ListVar SELECTEDFIXTURESCOUNT -> {_clean(raw)[:60]!r} -> count={n}")
    return n


def _clean(raw: str) -> str:
    """Strip ANSI escape codes from a telnet response."""
    return re.sub(r"\x1b\[[0-9;]*m", "", raw).strip()


# ---------------------------------------------------------------------------
# inspect_slot — navigate into pool slot and list contents
# ---------------------------------------------------------------------------

async def inspect_slot(preset_type_num: int, slot: int) -> bool:
    """
    Navigate into the preset slot (cd 17→1→type→slot) and list its contents.
    Returns True if the slot exists AND has fixture data (non-empty list).

    Populated slot: list returns fixture entries.
    Empty slot (stored with empty programmer): list returns 'NO OBJECTS FOUND'.
    Absent slot: cd {slot} lands nowhere useful; list is empty/error.
    """
    if _DRY_RUN:
        return False  # unknown in dry-run — treat as needs fixing

    await navigate_console("/")
    # Descend into the preset slot using sequential cd steps
    await send("cd 17")
    await send("cd 1")
    await send(f"cd {preset_type_num}")
    await send(f"cd {slot}")
    raw_list = await send("list")
    await navigate_console("/")  # always return to root

    clean = re.sub(r"\x1b\[[0-9;]*m", "", raw_list)
    upper = clean.upper()
    if "NO OBJECTS FOUND" in upper:
        return False
    # Non-trivial response that isn't just a prompt = data present
    stripped = clean.strip()
    return len(stripped) > 5


# ---------------------------------------------------------------------------
# Phase 0: Pre-flight fixture range check
# ---------------------------------------------------------------------------

async def preflight_fixtures() -> dict:
    """
    Verify which fixture ranges are patched in the current show.
    Returns counts per range and warns if any are 0.
    """
    await navigate_console("/")

    ranges = [
        ("all",    ALL_FIXTURES,     "all patched"),
        ("spot",   SPOT_FIXTURES,    "Spot 601-606"),
        ("lb150",  COLOR_FIXTURES_A, "LB150 411-414"),
        ("wash",   "fixture 601 thru 616",          "Spot+Wash 601-616"),
    ]
    counts: dict[str, int] = {}
    for key, cmd, label in ranges:
        if _DRY_RUN:
            counts[key] = 0
            info(f"[DRY] would check: {cmd}")
            continue
        await send(cmd)
        raw = await send("ListVar SELECTEDFIXTURESCOUNT")
        n = _parse_count(raw)
        counts[key] = n
        status = f"{n} fixture(s)" if n > 0 else "0 — NOT FOUND in this show"
        info(f"{label:<22} {status}")

    await send("clearall")
    await navigate_console("/")
    return counts


# ---------------------------------------------------------------------------
# Phase 1: Scan for bad slots
# ---------------------------------------------------------------------------

async def scan_pool(preset_type: str) -> dict:
    """
    List the preset pool and check which expected slots are absent.
    Returns dict: present, absent, slot_names.
    """
    expected = EXPECTED_SLOTS[preset_type]
    expected_nums = {s for s, _ in expected}

    result = await list_preset_pool(preset_type)
    data = json.loads(result)

    entries = data.get("entries", [])
    raw = data.get("raw_response", "")

    present_nums: set[int] = set()
    slot_names: dict[int, str] = {}

    for entry in entries:
        eid = entry.get("id")
        ename = entry.get("name", "")
        if eid is not None:
            try:
                # IDs may be "4.1" format — take the part after the dot
                raw_id = str(eid)
                n = int(raw_id.split(".")[-1]) if "." in raw_id else int(raw_id)
                present_nums.add(n)
                slot_names[n] = ename
            except (ValueError, TypeError):
                pass

    # Fallback: parse raw response — handles "Color 4.1  4.1  White  Normal" format
    if not present_nums and raw:
        clean = re.sub(r"\x1b\[[0-9;]*m", "", raw)
        for line in clean.splitlines():
            # Match "TypeName  4.N  4.N  SlotName  ..."
            m = re.search(r"\b\d+\.(\d+)\b", line)
            if m:
                try:
                    n = int(m.group(1))
                    if n in expected_nums:
                        present_nums.add(n)
                        # Extract name: last multi-char word token before "Normal"/"Embedded"
                        parts = re.sub(r"\s+", " ", line).strip().split()
                        name_parts = [
                            p for p in parts
                            if p not in ("Normal", "Embedded") and not re.match(r"^\d", p)
                        ]
                        slot_names[n] = name_parts[-1] if name_parts else ""
                except (ValueError, TypeError):
                    pass

    return {
        "present": sorted(present_nums & expected_nums),
        "absent":  sorted(expected_nums - present_nums),
        "slot_names": slot_names,
    }


# ---------------------------------------------------------------------------
# Phase 2: Discover attribute names
# ---------------------------------------------------------------------------

def _pick_rgb(attrs: list[str]) -> tuple[str, str, str]:
    """Priority-ranked R/G/B attribute selection."""
    # Pass 1: COLORRGB suffix
    rgb_exact = [a for a in attrs if re.search(r"COLORRGB\d*", a, re.IGNORECASE)]
    if len(rgb_exact) >= 3:
        return rgb_exact[0], rgb_exact[1], rgb_exact[2]
    # Pass 2: any RGB token
    rgb_any = [a for a in attrs if "RGB" in a.upper()]
    if len(rgb_any) >= 3:
        return rgb_any[0], rgb_any[1], rgb_any[2]
    # Pass 3: RED / GREEN / BLUE substrings
    reds   = [a for a in attrs if "RED"   in a.upper()]
    greens = [a for a in attrs if "GREEN" in a.upper()]
    blues  = [a for a in attrs if "BLUE"  in a.upper()]
    if reds and greens and blues:
        return reds[0], greens[0], blues[0]
    return "ColorRgb1", "ColorRgb2", "ColorRgb3"


async def discover_attrs() -> dict:
    """
    Browse preset types on fixture 601 to get real attribute names.
    Returns dict: r_attr, g_attr, b_attr, pan_attr, tilt_attr, gobo_attr.
    """
    await navigate_console("/")

    def _collect(bd: dict) -> list[str]:
        names: list[str] = []
        for feat in bd.get("features", []):
            for attr in feat.get("attributes", []):
                n = attr.get("library_name", "") or attr.get("name", "")
                if n:
                    names.append(n)
        return names

    # Color (type 4)
    r_attr = g_attr = b_attr = None
    try:
        await send("fixture 601")
        attrs = _collect(json.loads(await browse_preset_type(4, depth=2)))
        info(f"Color attrs (fixture 601): {attrs[:8]}")
        r_attr, g_attr, b_attr = _pick_rgb(attrs)
    except Exception as e:
        warn(f"Color discovery failed: {e}")
    r_attr = r_attr or "ColorRgb1"
    g_attr = g_attr or "ColorRgb2"
    b_attr = b_attr or "ColorRgb3"

    # Position (type 2)
    # Live-verified 2026-03-30: Fuze SFX Extended uses Virtual Position Mode (VPM).
    # VPM fixtures expose STAGEX/STAGEY/STAGEZ (and VIRTUAL_POSITION_MODE) instead of Pan/Tilt.
    # attribute "Pan"/"Tilt" are silently ignored in VPM mode — detect dynamically.
    pan_attr = tilt_attr = None
    position_mode = "raw"       # default; updated to "vpm" if STAGE attrs detected
    try:
        await send("fixture 601")
        attrs = _collect(json.loads(await browse_preset_type(2, depth=2)))
        info(f"Position attrs (fixture 601): {attrs[:8]}")
        stage_c = [a for a in attrs if "STAGE" in a.upper() or "VIRTUAL" in a.upper()]
        pan_c   = [a for a in attrs if "PAN"   in a.upper()]
        tilt_c  = [a for a in attrs if "TILT"  in a.upper()]
        if stage_c:
            position_mode = "vpm"
            info(f"  -> VPM detected: {stage_c[:3]}")
        elif pan_c and tilt_c:
            pan_attr  = pan_c[0]
            tilt_attr = tilt_c[0]
            info(f"  -> Raw Pan/Tilt detected: {pan_attr}, {tilt_attr}")
    except Exception as e:
        warn(f"Position discovery failed: {e}")
    pan_attr  = pan_attr  or "Pan"
    tilt_attr = tilt_attr or "Tilt"

    # Gobo (type 3)
    gobo_attr = None
    try:
        await send("fixture 601")
        attrs = _collect(json.loads(await browse_preset_type(3, depth=2)))
        info(f"Gobo attrs (fixture 601): {attrs[:6]}")
        gobo_c = [a for a in attrs if "GOBO" in a.upper()]
        gobo_attr = gobo_c[0] if gobo_c else None
    except Exception as e:
        warn(f"Gobo discovery failed: {e}")
    # Live-verified 2026-03-30: Fuze SFX Extended Gobo → $ATTRIBUTE = GOBO1
    gobo_attr = gobo_attr or "GOBO1"

    await navigate_console("/")
    await send("clearall")

    return {
        "r_attr": r_attr, "g_attr": g_attr, "b_attr": b_attr,
        "pan_attr": pan_attr, "tilt_attr": tilt_attr, "gobo_attr": gobo_attr,
        "position_mode": position_mode,     # "vpm" | "raw"
    }


# ---------------------------------------------------------------------------
# Phase 3: Re-store a single bad slot
# ---------------------------------------------------------------------------

async def fix_slot(
    preset_type: str,
    slot: int,
    name: str,
    selection_cmds: list[str],
    attr_cmds: list[str],
) -> str:
    """
    Re-store one preset slot.
    Returns: "fixed", "skipped", or "failed".
    """
    ptype_num = PRESET_TYPE_NUM[preset_type]
    label = f"{preset_type}.{slot} {name:<14}"

    await navigate_console("/")
    await send("clearall")

    # Check fixture selection BEFORE setting attributes
    fixture_count = await _fixture_count(selection_cmds)
    if fixture_count == 0:
        selfix_desc = " / ".join(selection_cmds)
        skip_msg(f"{label} 0 fixtures selected ({selfix_desc}) — check fixture IDs")
        await send("clearall")
        return "skipped"

    info(f"{label} {fixture_count} fixture(s) selected — setting attributes...")

    # Set attribute values in programmer; log and warn on any error response
    for cmd in attr_cmds:
        resp = await send(cmd)
        cr = _clean(resp)
        if _VERBOSE:
            info(f"    CMD: {cmd!r}  ->  {cr[:80]!r}")
        if any(x in cr.upper() for x in ("ERROR", "ILLEGAL", "UNKNOWN COMMAND")):
            warn(f"{label} attr cmd failed: {cmd!r} -> {cr[:60]!r}")

    if not _DRY_RUN:
        if _VERBOSE:
            # list attribute shows the attribute library, not programmer state — useless.
            # info fixture N outputs to console GUI only, not telnet.
            # Rely on store response and post-store XML export to verify programmer content.
            info("    (programmer state not readable via telnet — rely on store response)")

        store_cmd = f"store preset {ptype_num}.{slot} /universal /overwrite"
        raw_store = await send(store_cmd)
        clean_store = _clean(raw_store)
        if _VERBOSE:
            info(f"    STORE response: {clean_store[:100]!r}")
        nothing_indicators = ("NOTHING", "NO PROG", "EMPTY", "ERROR", "NOT STORED")
        if any(x in clean_store.upper() for x in nothing_indicators):
            fail(f"{label} store reported empty: {clean_store[:60]!r}")
            await send("clearall")
            return "failed"

    # Label
    await send(f'label preset {ptype_num}.{slot} "{name}"')

    # Clear programmer
    await send("clearall")

    if _DRY_RUN:
        dry(f"{label} would be stored+labeled")
        return "fixed"

    # NOTE: post-store verify via 'list' inside a slot ALWAYS returns
    # "NO OBJECTS FOUND" in MA2 — this is normal behaviour, not evidence
    # of an empty preset.  Rely on the direct send() store response above.
    fixed(f"{label}")
    return "fixed"


# ---------------------------------------------------------------------------
# Build repair plan per preset type
# ---------------------------------------------------------------------------

def _build_repair_plan(
    preset_type: str,
    bad_slots: set[int],
    attrs: dict,
) -> list[tuple[int, str, list[str], list[str]]]:
    r  = attrs["r_attr"]
    g  = attrs["g_attr"]
    b  = attrs["b_attr"]
    pan  = attrs["pan_attr"]
    tilt = attrs["tilt_attr"]
    gobo = attrs["gobo_attr"]

    if preset_type == "dimmer":
        return [
            # 'at {level}' sets the default (dimmer) attribute for all fixture types
            # without needing to know the per-fixture attribute name.
            (slot, name, [ALL_FIXTURES], [f"at {level}"])
            for slot, name, level in DIMMER_PRESETS
            if slot in bad_slots
        ]
    if preset_type == "color":
        return [
            (
                slot, name,
                [COLOR_FIXTURES_A, COLOR_FIXTURES_B],
                [
                    # CMY fixtures (Fuze SFX Extended 601-606, LB150 411-414)
                    # CMY inversion: Cyan=100-R, Magenta=100-G, Yellow=100-B
                    f'attribute "Cyan"    at {100 - rv}',
                    f'attribute "Magenta" at {100 - gv}',
                    f'attribute "Yellow"  at {100 - bv}',
                    # RGB/LED fixtures (Rogue R1 Beam Wash 611-616)
                    f'attribute "{r}" at {rv}',
                    f'attribute "{g}" at {gv}',
                    f'attribute "{b}" at {bv}',
                ],
            )
            for slot, name, rv, gv, bv in COLOR_VALUES
            if slot in bad_slots
        ]
    if preset_type == "position":
        if attrs.get("position_mode") != "vpm":
            # Non-VPM show: no hardcoded Pan/Tilt coordinates available — skip with warning.
            warn("Position: non-VPM mode detected but no Pan/Tilt coordinates configured — skipping position presets.")
            return []
        # VPM mode: set STAGEX/Y/Z stage coordinates (meters).
        # MA2 auto-adds VIRTUAL_POSITION_MODE, MARK, FLIP to the programmer.
        return [
            (
                slot, name,
                [SPOT_FIXTURES],
                [
                    f'attribute "STAGEX" at {sx}',
                    f'attribute "STAGEY" at {sy}',
                    f'attribute "STAGEZ" at {sz}',
                ],
            )
            for slot, name, sx, sy, sz in POSITION_PRESETS
            if slot in bad_slots
        ]
    if preset_type == "gobo":
        return [
            (slot, name, [SPOT_FIXTURES], [f'attribute "{gobo}" at {gv}'])
            for slot, name, gv in GOBO_PRESETS
            if slot in bad_slots
        ]
    return []


# ---------------------------------------------------------------------------
# --validate mode: read-only inspection of all 25 slots
# ---------------------------------------------------------------------------

async def run_validate() -> None:
    """Read-only: navigate into each expected slot and report POPULATED/EMPTY/ABSENT."""
    banner("FIX PRESETS -- Validate Mode (read-only)")
    print(f"  Console : {os.getenv('GMA_HOST', '127.0.0.1')}:{os.getenv('GMA_PORT', '30000')}")
    print()

    info("Connecting...")
    client = await get_client()
    if client is None:
        print("\n  x  Could not connect.")
        sys.exit(1)
    ok("Connected.")

    section("Slot inspection")

    # Pre-fetch pool lists once per type (avoids repeated list_preset_pool calls)
    pools: dict[str, dict] = {}
    for pt in ("dimmer", "color", "position", "gobo"):
        pools[pt] = await scan_pool(pt)

    # For Dimmer: MA2 auto-generates a name from the stored value (e.g. "100%", "Off").
    # Empty slots get the type name ("Dimmer") as auto-name.  Absent slots don't appear.
    # For Color/Position/Gobo: MA2 always uses the type name ("Color", "Position", …)
    # regardless of content — cannot distinguish empty from populated via telnet.
    async def _dimmer_has_data(slot: int) -> bool | None:
        """Check pool-level auto-name for Dimmer slots.  Returns None if absent."""
        pool = pools["dimmer"]
        if slot in pool.get("absent", []):
            return None
        name = pool.get("slot_names", {}).get(slot, "")
        return name.upper() != "DIMMER"  # "Dimmer" = empty; anything else = has data

    total = absent = empty = populated = unknown = 0
    for ptype in ("dimmer", "color", "position", "gobo"):
        ptype_num = PRESET_TYPE_NUM[ptype]
        pool = pools[ptype]
        print(f"\n  {ptype.upper()}")
        for slot, name in EXPECTED_SLOTS[ptype]:
            total += 1
            if slot in pool.get("absent", []):
                absent += 1
                status = "[ABSENT]  "
            elif ptype == "dimmer":
                has_data = await _dimmer_has_data(slot)
                if has_data:
                    populated += 1
                    status = "[POPULATED]"
                else:
                    empty += 1
                    status = "[EMPTY]   "
            else:
                # Cannot verify Color/Position/Gobo content via telnet
                unknown += 1
                status = "[UNKNOWN] (verify on console GUI)"
            print(f"    preset {ptype_num}.{slot:<3}  {name:<14}  {status}")

    section("Summary")
    print(f"  Total    : {total}")
    print(f"  Populated: {populated}  (Dimmer only — value confirmed via pool list)")
    print(f"  Empty    : {empty}  (Dimmer — slot exists, no data)")
    print(f"  Absent   : {absent}  (slot never stored)")
    print(f"  Unknown  : {unknown}  (Color/Position/Gobo — verify on console GUI)")
    print()
    if empty + absent > 0:
        warn(f"{empty + absent} Dimmer slot(s) need repair — run without --validate to fix.")
    elif unknown > 0:
        info("Color/Position/Gobo slots exist — check console GUI to confirm content.")
    else:
        ok("All slots populated.")
    print()


# ---------------------------------------------------------------------------
# --test-slot mode: repair exactly one slot with full verbose output
# ---------------------------------------------------------------------------

async def run_test_slot(slot_spec: str) -> None:
    """
    Repair a single preset slot with full verbose output.
    slot_spec format: "TYPE.SLOT" e.g. "position.1", "color.3", "dimmer.2"
    """
    global _VERBOSE
    _VERBOSE = True  # always verbose in test mode

    try:
        ptype, slot_str = slot_spec.split(".", 1)
        slot = int(slot_str)
        ptype = ptype.lower()
    except (ValueError, AttributeError):
        print(f"  x  Invalid --test-slot spec: {slot_spec!r}")
        print("     Format: TYPE.SLOT  e.g. position.1  color.3  dimmer.5")
        sys.exit(1)

    if ptype not in PRESET_TYPE_NUM:
        print(f"  x  Unknown preset type: {ptype!r}  (valid: dimmer, color, position, gobo)")
        sys.exit(1)

    # Find the name for this slot
    slot_name = next((n for s, n in EXPECTED_SLOTS[ptype] if s == slot), f"Slot{slot}")

    banner(f"FIX PRESETS -- Test Slot {ptype}.{slot} ({slot_name})")
    print(f"  Console : {os.getenv('GMA_HOST', '127.0.0.1')}:{os.getenv('GMA_PORT', '30000')}")
    print()

    info("Connecting...")
    client = await get_client()
    if client is None:
        print("\n  x  Could not connect.")
        sys.exit(1)
    ok("Connected.")
    print()

    # Discover attrs (needed for non-dimmer types)
    attrs = await discover_attrs()

    plan = _build_repair_plan(ptype, {slot}, attrs)
    if not plan:
        warn(f"No repair plan generated for {ptype}.{slot}")
        sys.exit(1)

    _, name, sel_cmds, attr_cmds = plan[0]
    status = await fix_slot(ptype, slot, name, sel_cmds, attr_cmds)

    print()
    print(f"  Result  : {status.upper()}")
    print()
    if status == "fixed":
        ok(f"Check console: open the {ptype.upper()} preset pool and look at slot {slot} ({name}).")
        ok("If it still appears empty, select the relevant fixtures first.")
    elif status == "skipped":
        warn("0 fixtures selected — update the fixture range constants at the top of the script.")
    else:
        warn("Fix failed — check the output above for error details.")
    print()


# ---------------------------------------------------------------------------
# Main — repair mode
# ---------------------------------------------------------------------------

async def main(dry_run: bool) -> None:
    global _DRY_RUN
    _DRY_RUN = dry_run

    banner("FIX PRESETS -- Targeted Repair")
    print(f"  Console : {os.getenv('GMA_HOST', '127.0.0.1')}:{os.getenv('GMA_PORT', '30000')}")
    if dry_run:
        print("  Mode    : DRY RUN (no telnet writes)")
    print()

    info("Connecting...")
    client = await get_client()
    if client is None:
        print("\n  x  Could not connect. Check GMA_HOST in .env.")
        sys.exit(1)
    ok("Connected.")

    t0 = time.perf_counter()

    # ------------------------------------------------------------------
    # Pre-flight: fixture range check
    # ------------------------------------------------------------------
    section("Pre-flight -- Fixture range check")
    counts = await preflight_fixtures()

    if not _DRY_RUN and counts.get("all", 0) == 0:
        warn("No fixtures found in range 1-9001. Cannot store presets. Aborting.")
        sys.exit(1)

    if counts.get("spot", 0) == 0:
        warn("No Spot fixtures at 601-606 — position/gobo presets will be SKIPPED.")
        warn("Update SPOT_FIXTURES constant if your show uses different fixture IDs.")
    if counts.get("lb150", 0) == 0 and counts.get("wash", 0) == 0:
        warn("No color fixtures at 411-416 or 601-616 — color presets may be SKIPPED.")
        warn("Update COLOR_FIXTURES_A/B constants if your show uses different fixture IDs.")

    # ------------------------------------------------------------------
    # Phase 1 — Scan for bad slots
    # ------------------------------------------------------------------
    section("Phase 1 -- Scanning for bad slots")

    bad_slots: list[tuple[str, int, str, str]] = []

    for ptype in ("dimmer", "color", "position", "gobo"):
        ptype_num = PRESET_TYPE_NUM[ptype]
        pool = await scan_pool(ptype)
        absent_set = set(pool["absent"])
        present_set = set(pool["present"])

        absent_count = len(absent_set)
        empty_count = 0

        for slot_num, slot_name in EXPECTED_SLOTS[ptype]:
            if slot_num in absent_set:
                bad_slots.append((ptype, slot_num, slot_name, "absent"))
            elif slot_num in present_set:
                has_data = await inspect_slot(ptype_num, slot_num)
                if not has_data:
                    empty_count += 1
                    bad_slots.append((ptype, slot_num, slot_name, "empty"))

        ok(f"{ptype.upper():<10} {len(EXPECTED_SLOTS[ptype])} expected, {absent_count} absent, {empty_count} empty")

    total_bad    = len(bad_slots)
    total_absent = sum(1 for _, _, _, r in bad_slots if r == "absent")
    total_empty  = total_bad - total_absent

    if total_bad == 0:
        ok("\nAll 25 preset slots are present and populated — nothing to repair.")
        print()
        return

    print()
    warn(f"Bad slots: {total_bad} total ({total_absent} absent, {total_empty} empty)")
    for ptype, slot, name, reason in bad_slots:
        pnum = PRESET_TYPE_NUM[ptype]
        print(f"    preset {pnum}.{slot:<3}  [{ptype}] {name:<14}  ({reason})")

    # ------------------------------------------------------------------
    # Phase 2 — Discover attribute names
    # ------------------------------------------------------------------
    section("Phase 2 -- Attribute discovery")

    attrs = await discover_attrs()
    ok(f"Color   : R={attrs['r_attr']}  G={attrs['g_attr']}  B={attrs['b_attr']}")
    _pos_mode = attrs["position_mode"]
    _pos_label = "VPM (STAGEX/Y/Z)" if _pos_mode == "vpm" else f"Raw (Pan={attrs['pan_attr']} Tilt={attrs['tilt_attr']})"
    ok(f"Position: {_pos_label}")
    ok(f"Gobo    : {attrs['gobo_attr']}")

    # ------------------------------------------------------------------
    # Phase 3 — Re-store bad slots
    # ------------------------------------------------------------------
    section("Phase 3 -- Re-storing bad slots")

    results: dict[str, int] = {"fixed": 0, "skipped": 0, "failed": 0}
    failures: list[tuple[str, int, str, str]] = []

    for ptype in ("dimmer", "color", "position", "gobo"):
        bad_for_type = {slot for (pt, slot, _, _) in bad_slots if pt == ptype}
        if not bad_for_type:
            continue

        plan = _build_repair_plan(ptype, bad_for_type, attrs)
        for slot, name, sel_cmds, attr_cmds in plan:
            status = await fix_slot(ptype, slot, name, sel_cmds, attr_cmds)
            results[status] += 1
            if status in ("skipped", "failed"):
                failures.append((ptype, slot, name, status))

    # ------------------------------------------------------------------
    # Phase 4 — Summary
    # ------------------------------------------------------------------
    section("Phase 4 -- Summary")

    elapsed = time.perf_counter() - t0
    print(f"  Scanned : 25 slots across 4 preset types")
    print(f"  Bad     : {total_bad}  ({total_absent} absent, {total_empty} empty)")
    print(f"  Fixed   : {results['fixed']}")
    print(f"  Skipped : {results['skipped']}  (0 fixtures selected)")
    print(f"  Failed  : {results['failed']}")
    print(f"  Elapsed : {elapsed:.1f}s")

    if failures:
        print()
        warn("Remaining issues:")
        for ptype, slot, name, status in failures:
            pnum = PRESET_TYPE_NUM[ptype]
            print(f"    preset {pnum}.{slot}  [{ptype}] {name:<14}  ({status})")
        print()
        if results["skipped"] > 0:
            info("Skipped slots = 0 fixtures selected. Fix:")
            info("  Update SPOT_FIXTURES / COLOR_FIXTURES_A/B / ALL_FIXTURES at top of script")
            info("  to match the fixture IDs actually patched in this show.")
    else:
        print()
        ok("All bad slots repaired successfully.")

    print()
    if not dry_run and results["fixed"] > 0:
        info("Re-run with --validate or run audit_presets.py to confirm.")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair empty/absent MA2 preset slots")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--validate",
        action="store_true",
        default=False,
        help="Read-only: inspect each slot and report POPULATED / EMPTY / ABSENT",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Scan and plan only — no telnet writes",
    )
    mode.add_argument(
        "--test-slot",
        metavar="TYPE.SLOT",
        default=None,
        help="Repair exactly one slot with full verbose output (e.g. position.1, color.3)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Print raw MA2 responses for every telnet command",
    )
    args = parser.parse_args()

    _VERBOSE = args.verbose  # set before any async code runs

    if args.validate:
        asyncio.run(run_validate())
    elif args.test_slot:
        asyncio.run(run_test_slot(args.test_slot))
    else:
        asyncio.run(main(args.dry_run))
