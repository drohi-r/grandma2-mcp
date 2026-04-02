"""
scripts/audit_presets.py -- Read-only diagnostic audit of the grandMA2 preset pools.

Checks which presets are populated vs empty, discovers the actual attribute names
on each fixture type, and produces a diagnosis with recommended fixes for make_presets.py.

Usage:
    python scripts/audit_presets.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys

os.environ.setdefault("GMA_AUTH_BYPASS", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.server import (  # noqa: E402
    browse_preset_type,
    get_client,
    list_preset_pool,
    navigate_console,
)

# ---------------------------------------------------------------------------
# Expected preset definitions (mirrors make_presets.py)
# ---------------------------------------------------------------------------

PRESET_TYPE_NUM = {"dimmer": 1, "position": 2, "gobo": 3, "color": 4}

EXPECTED_SLOTS: dict[str, list[tuple[int, str]]] = {
    "dimmer":   [(1, "Full"), (2, "75pct"), (3, "Half"), (4, "25pct"), (5, "Off")],
    "color":    [
        (1, "White"), (2, "Red"), (3, "Green"), (4, "Blue"), (5, "Amber"),
        (6, "Cyan"), (7, "Magenta"), (8, "Yellow"), (9, "WarmWhite"), (10, "CoolWhite"),
    ],
    "position": [(1, "Home"), (2, "FOH-Center"), (3, "Stage-Left"), (4, "Stage-Right"), (5, "TopLight")],
    "gobo":     [(1, "Open"), (2, "Gobo1"), (3, "Gobo2"), (4, "Gobo3"), (5, "Gobo4")],
}

# Attribute names used in make_presets.py (what was attempted)
ATTEMPTED_ATTRS = {
    "color_r":  "ColorRgb1",
    "color_g":  "ColorRgb2",
    "color_b":  "ColorRgb3",
    "pan":      "Pan",
    "tilt":     "Tilt",
    "gobo":     "Gobo1",
}

_WIDTH = 72


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
    print(f"  [OK]   {msg}")


def info(msg: str) -> None:
    print(f"  -->    {msg}")


def warn(msg: str) -> None:
    print(f"  [!]    {msg}")


def empty(msg: str) -> None:
    print(f"  [EMPTY] {msg}")


def fix(msg: str) -> None:
    print(f"  [FIX]  {msg}")


# ---------------------------------------------------------------------------
# Raw telnet helper
# ---------------------------------------------------------------------------

async def send(cmd: str) -> str:
    """Send a raw telnet command and return the response."""
    client = await get_client()
    return await client.send_command_with_response(cmd)


# ---------------------------------------------------------------------------
# Phase 1: List preset pools and check slot presence
# ---------------------------------------------------------------------------

async def audit_pool(preset_type: str) -> dict:
    """
    List the preset pool, compare against expected slots.
    Returns a dict with present_slots, absent_slots, slot_names.
    """
    expected = EXPECTED_SLOTS[preset_type]
    expected_slot_nums = {s for s, _ in expected}

    result = await list_preset_pool(preset_type)
    data = json.loads(result)

    entries = data.get("entries", [])
    raw = data.get("raw_response", "")

    # Parse slot IDs from entries or raw response
    present_slot_nums: set[int] = set()
    slot_names: dict[int, str] = {}

    for entry in entries:
        # entry has type, id, name
        eid = entry.get("id")
        ename = entry.get("name", "")
        if eid is not None:
            try:
                present_slot_nums.add(int(eid))
                slot_names[int(eid)] = ename
            except (ValueError, TypeError):
                pass

    # Fallback: parse raw response for lines like "Preset N  name"
    if not present_slot_nums and raw:
        clean = re.sub(r"\x1b\[[0-9;]*m", "", raw)
        for line in clean.splitlines():
            m = re.match(r"\s*(?:Preset\s+)?(\d+)\s+([\w\s\-:]+?)(?:\s{2,}|\r|\n|$)", line)
            if m:
                try:
                    slot_num = int(m.group(1))
                    name = m.group(2).strip()
                    if slot_num in expected_slot_nums:
                        present_slot_nums.add(slot_num)
                        slot_names[slot_num] = name
                except (ValueError, TypeError):
                    pass

    absent_slot_nums = expected_slot_nums - present_slot_nums

    return {
        "present": sorted(present_slot_nums & expected_slot_nums),
        "absent": sorted(absent_slot_nums),
        "extra": sorted(present_slot_nums - expected_slot_nums),
        "slot_names": slot_names,
        "raw": raw,
        "entries": entries,
    }


# ---------------------------------------------------------------------------
# Phase 2: Inspect individual preset slots with "info"
# ---------------------------------------------------------------------------

async def inspect_preset(preset_type_num: int, slot: int) -> dict:
    """
    Run 'info preset N.M' and parse the response.
    Returns dict with has_data, fixture_count, attrs_found, raw.
    """
    await navigate_console("/")
    raw = await send(f"info preset {preset_type_num}.{slot}")
    clean = re.sub(r"\x1b\[[0-9;]*m", "", raw)

    has_data = True
    fixture_count = None
    attrs_found: list[str] = []

    # Check for empty indicators
    if "NO OBJECTS FOUND" in clean.upper() or "NOT FOUND" in clean.upper():
        has_data = False
    elif not clean.strip() or clean.strip() == ">":
        has_data = False

    # Try to extract fixture count
    m_fix = re.search(r"(\d+)\s+fixture", clean, re.IGNORECASE)
    if m_fix:
        fixture_count = int(m_fix.group(1))

    # Try to extract attribute names from info output
    attr_matches = re.findall(r"(?:Attribute|Attr)[:\s]+(\w+)", clean, re.IGNORECASE)
    attrs_found.extend(attr_matches)

    # Also look for lines that look like "AttributeName  value"
    for line in clean.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].isalpha() and len(parts[0]) > 3:
            # Heuristic: first token is all-alpha and >3 chars could be attr name
            if re.match(r"^[A-Za-z][A-Za-z0-9_]+$", parts[0]):
                attrs_found.append(parts[0])

    # Deduplicate preserving order
    seen: set[str] = set()
    unique_attrs: list[str] = []
    for a in attrs_found:
        if a not in seen:
            seen.add(a)
            unique_attrs.append(a)

    return {
        "has_data": has_data,
        "fixture_count": fixture_count,
        "attrs_found": unique_attrs[:10],
        "raw": raw,
    }


# ---------------------------------------------------------------------------
# Phase 3: Attribute discovery per fixture type
# ---------------------------------------------------------------------------

async def discover_fixture_attrs(
    fixture_id: int,
    preset_type_ids: list[int],
) -> dict[int, list[str]]:
    """
    Select a fixture, then browse each preset type tree to get real attr names.
    Returns {preset_type_id: [attr_names]}.
    """
    await navigate_console("/")
    await send(f"selfix fixture {fixture_id}")

    result: dict[int, list[str]] = {}
    for pt_id in preset_type_ids:
        try:
            browse_result = await browse_preset_type(pt_id, depth=2)
            bd = json.loads(browse_result)
            attrs: list[str] = []
            for feat in bd.get("features", []):
                for attr in feat.get("attributes", []):
                    name = attr.get("name", "")
                    if name:
                        attrs.append(name)
            result[pt_id] = attrs
        except Exception as exc:
            result[pt_id] = [f"ERROR: {exc}"]

    await navigate_console("/")
    await send("clear")
    return result


# ---------------------------------------------------------------------------
# Phase 4: Attribute name via live programmer listing
# ---------------------------------------------------------------------------

async def list_programmer_attrs(fixture_id: int) -> list[str]:
    """
    Select a fixture, set at 100, then list the programmer to find active attr names.
    """
    await navigate_console("/")
    await send(f"selfix fixture {fixture_id}")
    await send("at 100")
    raw = await send("list attribute")
    await send("clear")
    await navigate_console("/")

    clean = re.sub(r"\x1b\[[0-9;]*m", "", raw)
    attrs: list[str] = []
    for line in clean.splitlines():
        # Attribute lines typically: "AttributeName  type  value  ..."
        stripped = line.strip()
        if not stripped or stripped.startswith("[") or stripped.startswith("$"):
            continue
        parts = stripped.split()
        if parts and re.match(r"^[A-Za-z][A-Za-z0-9_]+$", parts[0]) and len(parts[0]) > 2:
            attrs.append(parts[0])
    return attrs


# ---------------------------------------------------------------------------
# Diagnosis helpers
# ---------------------------------------------------------------------------

def diagnose_attr_mismatch(
    attempted: str,
    discovered: list[str],
    preset_type_label: str,
) -> str | None:
    """
    Return a fix recommendation if attempted attr is not in discovered list.
    Returns None if the attr looks correct.
    """
    discovered_upper = [a.upper() for a in discovered]
    if attempted.upper() in discovered_upper:
        return None  # looks correct

    # Fuzzy match
    candidates = [a for a in discovered if len(a) > 2]
    return (
        f'"{attempted}" not found on {preset_type_label} fixtures. '
        f"Discovered: {candidates[:6]}. "
        f"Use the first matching attr instead."
    )


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------

async def main() -> None:
    banner("PRESET POOL AUDIT")
    print(f"  Console: {os.getenv('GMA_HOST', '127.0.0.1')}:{os.getenv('GMA_PORT', '30000')}")

    info("Connecting to console...")
    client = await get_client()
    if client is None:
        print("\n  x  Could not connect. Check GMA_HOST in .env.")
        sys.exit(1)
    ok("Connected.")

    # ------------------------------------------------------------------
    # Phase 1: Pool presence check
    # ------------------------------------------------------------------
    section("Phase 1 -- Pool presence check")

    pool_results: dict[str, dict] = {}
    issues_found = False

    for ptype in ("dimmer", "color", "position", "gobo"):
        pnum = PRESET_TYPE_NUM[ptype]
        expected = EXPECTED_SLOTS[ptype]
        print(f"\n  {ptype.upper()} (preset type {pnum}) -- expected {len(expected)} slot(s)")

        pr = await audit_pool(ptype)
        pool_results[ptype] = pr

        for slot_num, slot_label in expected:
            if slot_num in pr["present"]:
                stored_name = pr["slot_names"].get(slot_num, "")
                name_tag = f'  name="{stored_name}"' if stored_name else ""
                print(f"    slot {slot_num:<3} {slot_label:<14} [PRESENT]{name_tag}")
            else:
                print(f"    slot {slot_num:<3} {slot_label:<14} [ABSENT]")
                issues_found = True

        if pr["extra"]:
            info(f"  Extra slots not expected: {pr['extra']}")

    # ------------------------------------------------------------------
    # Phase 2: Deeper inspection of present slots
    # ------------------------------------------------------------------
    section("Phase 2 -- Preset content inspection (info preset N.M)")
    info("Checking each present slot for fixture data...")

    inspection: dict[str, dict[int, dict]] = {}
    empty_slots: list[tuple[str, int, str]] = []

    for ptype in ("dimmer", "color", "position", "gobo"):
        pnum = PRESET_TYPE_NUM[ptype]
        pr = pool_results[ptype]
        inspection[ptype] = {}

        for slot_num, slot_label in EXPECTED_SLOTS[ptype]:
            if slot_num not in pr["present"]:
                continue  # already flagged as absent in phase 1

            ins = await inspect_preset(pnum, slot_num)
            inspection[ptype][slot_num] = ins

            if not ins["has_data"] or (ins["fixture_count"] is not None and ins["fixture_count"] == 0):
                marker = "EMPTY"
                empty_slots.append((ptype, slot_num, slot_label))
                issues_found = True
            else:
                fix_count = ins["fixture_count"]
                marker = f"populated  fixtures={fix_count}" if fix_count else "populated"

            print(f"    [{ptype}] slot {slot_num:<3} {slot_label:<14} {marker}")

    # ------------------------------------------------------------------
    # Phase 3: Attribute discovery
    # ------------------------------------------------------------------
    section("Phase 3 -- Attribute name discovery")
    info("Selecting fixture 601 (Spot) to discover actual attribute names...")

    # Discover attrs for color (4), position (2), gobo (3) — all from Spots
    spot_attrs = await discover_fixture_attrs(601, [4, 2, 3])

    info("Discovered attribute names per preset type (fixture 601):")
    pt_labels = {4: "COLOR", 2: "POSITION", 3: "GOBO"}
    for pt_id in (4, 2, 3):
        attrs = spot_attrs.get(pt_id, [])
        print(f"    Preset type {pt_id} ({pt_labels[pt_id]}): {attrs[:8]}")

    # Also check LB150 (fixture 411) for color
    info("Selecting fixture 411 (LB150) to check color attrs...")
    lb150_attrs = await discover_fixture_attrs(411, [4])
    lb150_color = lb150_attrs.get(4, [])
    print(f"    LB150 Color attrs: {lb150_color[:8]}")

    # List programmer attrs on fixture 601 as a cross-check
    info("Listing programmer attributes on fixture 601 (at 100, clear)...")
    prog_attrs = await list_programmer_attrs(601)
    print(f"    Programmer attrs: {prog_attrs[:10]}")

    # ------------------------------------------------------------------
    # Phase 4: Diagnosis
    # ------------------------------------------------------------------
    section("Phase 4 -- Diagnosis and recommended fixes")

    if not issues_found and not empty_slots:
        ok("All preset slots are present and appear populated — no issues found.")
        print()
        return

    # Map what make_presets.py attempted vs what was discovered
    color_attrs_spot = spot_attrs.get(4, [])
    pos_attrs_spot   = spot_attrs.get(2, [])
    gobo_attrs_spot  = spot_attrs.get(3, [])

    diagnoses: list[str] = []

    # Check color R/G/B
    for attr_key, attempted in [
        ("color_r", ATTEMPTED_ATTRS["color_r"]),
        ("color_g", ATTEMPTED_ATTRS["color_g"]),
        ("color_b", ATTEMPTED_ATTRS["color_b"]),
    ]:
        diag = diagnose_attr_mismatch(attempted, color_attrs_spot, "Color")
        if diag:
            diagnoses.append(f"COLOR {attr_key}: {diag}")

    # Check Pan/Tilt
    for attr_key, attempted, disc in [
        ("pan",  ATTEMPTED_ATTRS["pan"],  pos_attrs_spot),
        ("tilt", ATTEMPTED_ATTRS["tilt"], pos_attrs_spot),
    ]:
        diag = diagnose_attr_mismatch(attempted, disc, "Position")
        if diag:
            diagnoses.append(f"POSITION {attr_key}: {diag}")

    # Check Gobo
    diag = diagnose_attr_mismatch(ATTEMPTED_ATTRS["gobo"], gobo_attrs_spot, "Gobo")
    if diag:
        diagnoses.append(f"GOBO gobo_attr: {diag}")

    if diagnoses:
        warn("Attribute name mismatches detected — these are the likely root cause of empty presets:")
        for d in diagnoses:
            print(f"\n    {d}")
    else:
        info("Attribute names from make_presets.py appear correct for fixture 601.")
        info("Empty presets may be due to fixture selection issues or timing.")

    # Show absent / empty slot summary
    absent_all: list[tuple[str, int, str]] = []
    for ptype, pr in pool_results.items():
        for slot_num, slot_label in EXPECTED_SLOTS[ptype]:
            if slot_num in pr["absent"]:
                absent_all.append((ptype, slot_num, slot_label))

    if absent_all:
        print()
        warn(f"{len(absent_all)} slot(s) entirely absent from pool (store command may not have run):")
        for ptype, slot_num, slot_label in absent_all:
            pnum = PRESET_TYPE_NUM[ptype]
            print(f"    preset {pnum}.{slot_num}  [{ptype}] {slot_label}")

    if empty_slots:
        print()
        warn(f"{len(empty_slots)} slot(s) present but contain no fixture data:")
        for ptype, slot_num, slot_label in empty_slots:
            pnum = PRESET_TYPE_NUM[ptype]
            print(f"    preset {pnum}.{slot_num}  [{ptype}] {slot_label}")

    # Recommended corrections
    print()
    section("Recommended corrections for make_presets.py")

    if color_attrs_spot:
        rgb_candidates = [a for a in color_attrs_spot if any(
            k in a.upper() for k in ("RGB", "RED", "COLOR", "R", "G", "B")
        )]
        if rgb_candidates:
            fix(f"Replace ColorRgb1/2/3 with discovered color attrs: {rgb_candidates[:6]}")
        else:
            fix(f"Color attrs on Spot 601: {color_attrs_spot[:6]} -- check which 3 map to R/G/B")

    if pos_attrs_spot:
        pan_c  = [a for a in pos_attrs_spot if "PAN"  in a.upper()]
        tilt_c = [a for a in pos_attrs_spot if "TILT" in a.upper()]
        if pan_c:
            fix(f"Use Pan attr:  {pan_c[0]}  (discovered on fixture 601)")
        else:
            fix(f"No PAN attr found on fixture 601 Position tree: {pos_attrs_spot[:4]}")
        if tilt_c:
            fix(f"Use Tilt attr: {tilt_c[0]}  (discovered on fixture 601)")
        else:
            fix(f"No TILT attr found on fixture 601 Position tree: {pos_attrs_spot[:4]}")

    if gobo_attrs_spot:
        gobo_c = [a for a in gobo_attrs_spot if "GOBO" in a.upper()]
        if gobo_c:
            fix(f"Use Gobo attr: {gobo_c[0]}  (discovered on fixture 601)")
        else:
            fix(f"No GOBO attr found on fixture 601 Gobo tree: {gobo_attrs_spot[:4]}")

    print()
    info("Re-run make_presets.py after updating attr names in the discovery fallbacks.")
    info("Or let make_presets.py's Phase 1 (discover()) pick up the correct attrs automatically.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
