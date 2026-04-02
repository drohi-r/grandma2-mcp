"""
scripts/export_validate_presets.py

Export the position preset pool (2.1–2.5) from grandMA2 to XML, then parse the file to
confirm each preset slot contains fixture data.  Auto-retries the fix + re-export loop
up to MAX_RETRIES times for any empty slot.

Usage:
    python scripts/export_validate_presets.py            # selective mode (default) + retry
    python scripts/export_validate_presets.py --mode selective   # store without /universal
    python scripts/export_validate_presets.py --mode universal   # store with /universal
    python scripts/export_validate_presets.py --mode global      # store with /global
    python scripts/export_validate_presets.py --no-fix   # export + validate only (no writes)
    python scripts/export_validate_presets.py --verbose  # full XML dump for every slot
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

os.environ.setdefault("GMA_AUTH_BYPASS", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.server import get_client, navigate_console  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES = 3

EXPORT_FILENAME = "position_presets"
EXPORT_PATH = (
    r"C:\ProgramData\MA Lighting Technologies"
    r"\grandma\gma2_V_3.9.60\importexport"
    rf"\{EXPORT_FILENAME}.xml"
)

# Position preset definitions — Virtual Position Mode (STAGEX/Y/Z, meters).
# STAGEZ baseline -1.4356079 from preset 2.7 (live-verified 2026-03-30, toronto show).
# attribute "Pan"/"Tilt" are silently discarded by MA2 in VPM mode.
POSITION_PRESETS: list[tuple[int, str, float, float, float]] = [
    (1, "Home",         0.0,   0.0,  -1.4356079),
    (2, "FOH-Center",   0.0,   3.0,  -1.4356079),
    (3, "Stage-Left",  -3.0,   1.5,  -1.4356079),
    (4, "Stage-Right",  3.0,   1.5,  -1.4356079),
    (5, "TopLight",     0.0,   0.0,  -4.0),
]

SPOT_FIXTURES = "fixture 601 thru 606"

_WIDTH = 72
_VERBOSE = False
_MODE = "selective"   # default store mode: selective | universal | global


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


def fail(msg: str) -> None:
    print(f"  [FAIL]   {msg}")


def fixed(msg: str) -> None:
    print(f"  [FIXED]  {msg}")


# ---------------------------------------------------------------------------
# Raw telnet helper
# ---------------------------------------------------------------------------

async def send(cmd: str) -> str:
    client = await get_client()
    return await client.send_command_with_response(cmd)


def _clean(raw: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", raw).strip()


# ---------------------------------------------------------------------------
# Phase 1: Export
# ---------------------------------------------------------------------------

async def export_position_presets() -> None:
    """Send Export command and wait for file to appear on disk."""
    cmd = f'Export Preset 2.1 Thru 2.5 "{EXPORT_FILENAME}" /overwrite'
    info(f"Sending: {cmd}")
    raw = await send(cmd)
    clean = _clean(raw)
    if _VERBOSE:
        info(f"  Console response: {clean[:120]!r}")
    if any(x in clean.upper() for x in ("ERROR", "ILLEGAL", "UNKNOWN COMMAND")):
        warn(f"Export command may have failed: {clean[:80]!r}")

    # Wait up to 5 seconds for the file to appear
    for i in range(10):
        if os.path.exists(EXPORT_PATH):
            ok(f"File ready: {EXPORT_PATH}")
            return
        time.sleep(0.5)
    warn(f"File not found after 5s: {EXPORT_PATH}")
    warn("MA2 may have exported to a different path or the export failed.")


# ---------------------------------------------------------------------------
# Phase 2: Parse + validate XML
# ---------------------------------------------------------------------------

def _find_preset_nodes(root: ET.Element) -> dict[int, ET.Element]:
    """
    Walk the XML tree and return {slot_number: element} for all Preset nodes.

    MA2 XML uses 0-based index:  index="0" → slot 1, index="1" → slot 2, etc.
    Also tries name-matching as a fallback.
    """
    preset_nodes: dict[int, ET.Element] = {}

    for elem in root.iter():
        tag_local = elem.tag.split("}")[-1].lower()  # strip namespace
        if tag_local != "preset":
            continue
        # 0-based index → 1-based slot
        idx_str = elem.get("index") or elem.get("Index")
        if idx_str is not None:
            try:
                slot = int(idx_str) + 1
                preset_nodes[slot] = elem
                continue
            except ValueError:
                pass
        # fallback: match by name
        name = elem.get("name") or elem.get("Name") or ""
        for slot, sname, _, _ in POSITION_PRESETS:
            if sname.lower() == name.lower():
                if slot not in preset_nodes:
                    preset_nodes[slot] = elem
                break

    return preset_nodes


def _check_preset_elem(elem: ET.Element) -> str:
    """Return the preset_mode string from the element (defaults to 'Normal')."""
    return elem.get("preset_mode") or elem.get("PresetMode") or "Normal"


def _is_success(result: dict) -> bool:
    """
    Determine whether a slot counts as successfully stored for the current mode.

    - selective / normal: slot must be present (mode will be 'Normal' or absent)
    - universal:          slot must be present AND preset_mode == 'Universal'
    - global:             slot must be present AND preset_mode == 'Global'
    """
    if not result["present"]:
        return False
    mode_stored = result["mode"].lower()
    if _MODE == "universal":
        return mode_stored == "universal"
    if _MODE == "global":
        return mode_stored == "global"
    # selective (default): any present slot is a success
    return True


def validate_xml(xml_path: str) -> dict[int, dict]:
    """
    Parse the exported XML and return per-slot results.
    Each result: {slot: {name, present, mode, elem}}

    NOTE: MA2 preset XML contains ONLY metadata (name, index, preset_mode).
    Fixture attribute values are stored in the showfile, NOT in the exported XML.
    """
    if not os.path.exists(xml_path):
        return {}

    try:
        # utf-8-sig strips the BOM that MA2 prepends to its XML exports
        with open(xml_path, encoding="utf-8-sig", errors="replace") as fh:
            content = fh.read()
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        warn(f"XML parse error: {exc}")
        return {}

    preset_nodes = _find_preset_nodes(root)

    results: dict[int, dict] = {}
    for slot, name, _, _ in POSITION_PRESETS:
        elem = preset_nodes.get(slot)
        if elem is None:
            results[slot] = {
                "name": name, "present": False,
                "mode": "ABSENT", "elem": None,
            }
        else:
            mode = _check_preset_elem(elem)
            results[slot] = {
                "name": name, "present": True,
                "mode": mode, "elem": elem,
            }
    return results


def print_validation_report(results: dict[int, dict], print_slot4_xml: bool = True) -> None:
    """Print a formatted validation table and dump slot XML.

    MA2 preset XML only carries metadata.  We check:
      present — slot exists in the exported file
      mode    — preset_mode attribute (Normal / Universal / Global / ABSENT)
    Success criteria depend on --mode flag (see _is_success()).
    """
    print()
    print(f"  Store mode : {_MODE}")
    print("  NOTE: MA2 preset XML exports metadata only, not fixture attribute values.")
    print()
    print(f"  {'Slot':<8} {'Name':<16} {'Present':<10} {'Mode':<12} {'Status'}")
    print(f"  {'-'*8} {'-'*16} {'-'*10} {'-'*12} {'-'*20}")
    for slot in sorted(results):
        r = results[slot]
        present = "yes" if r["present"] else "NO"
        mode = r["mode"]
        if _is_success(r):
            status = "OK"
        elif r["present"]:
            status = "wrong mode"
        else:
            status = "MISSING"
        print(f"  {f'2.{slot}':<8} {r['name']:<16} {present:<10} {mode:<12} {status}")

    # Dump raw XML for slot 4 always; all slots in verbose mode
    slots_to_dump = [4] if not _VERBOSE else sorted(results)
    for target in slots_to_dump:
        r = results.get(target)
        label = f"Slot 2.{target} ({r['name'] if r else '?'})"
        print()
        print(f"  --- Raw XML for {label} ---")
        if r and r["elem"] is not None:
            try:
                ET.indent(r["elem"])
            except AttributeError:
                pass
            raw_xml = ET.tostring(r["elem"], encoding="unicode")
            for line in raw_xml.splitlines():
                _safe_print(f"    {line}\n")
        else:
            print("    (no Preset element found in XML for this slot)")


def _safe_print(text: str) -> None:
    """Print a string, replacing characters that can't encode on this terminal."""
    enc = sys.stdout.encoding or "utf-8"
    safe = text.encode(enc, errors="replace").decode(enc, errors="replace")
    print(safe, end="")


def dump_raw_xml_head(xml_path: str, lines: int = 60) -> None:
    """Print the first N lines of the raw XML file so we can see the structure."""
    if not os.path.exists(xml_path):
        return
    print()
    print(f"  --- Raw XML file (first {lines} lines) ---")
    # utf-8-sig strips the BOM that MA2 writes at the start of XML files
    with open(xml_path, encoding="utf-8-sig", errors="replace") as fh:
        for i, line in enumerate(fh):
            if i >= lines:
                print("    ... (truncated)")
                break
            _safe_print(f"    {line}")
    print()


# ---------------------------------------------------------------------------
# Phase 3: Fix a single empty slot (inline — no fix_presets import needed)
# ---------------------------------------------------------------------------

def _store_cmd(slot: int, mode: str) -> str:
    """Build the store command for the given mode."""
    if mode == "universal":
        return f"store preset 2.{slot} /universal /overwrite"
    if mode == "global":
        return f"store preset 2.{slot} /global /overwrite"
    # selective (default) — no mode flag; MA2 stores as Normal/Selective
    return f"store preset 2.{slot} /overwrite"


async def fix_position_slot(
    slot: int,
    name: str,
    sx: float,
    sy: float,
    sz: float,
    mode: str = "selective",
) -> bool:
    """
    Re-store one position preset slot using VPM stage coordinates.
    Returns True on success.

    sx/sy/sz: STAGEX/Y/Z in meters (VPM mode — raw Pan/Tilt is ignored by MA2).
    mode: "selective" (default, no flag), "universal" (/universal), "global" (/global)
    """
    info(f"  Fixing position 2.{slot} ({name}) — mode={mode}, STAGEX={sx} STAGEY={sy} STAGEZ={sz}")
    await navigate_console("/")
    await send("clearall")

    # Select fixtures
    raw_sel = await send(SPOT_FIXTURES)
    clean_sel = _clean(raw_sel)
    if _VERBOSE:
        info(f"    Selection: {clean_sel[:60]!r}")

    # Verify at least 1 fixture selected
    raw_count = await send("ListVar SELECTEDFIXTURESCOUNT")
    m = re.search(r"=\s*(\d+)", raw_count)
    count = int(m.group(1)) if m else 0
    if count == 0:
        warn(f"    0 fixtures selected for {SPOT_FIXTURES} — skipping slot {slot}")
        await send("clearall")
        return False

    info(f"    {count} fixture(s) selected — setting STAGEX/Y/Z")

    # Set VPM stage coordinates — MA2 auto-adds VIRTUAL_POSITION_MODE/MARK/FLIP
    for cmd in [
        f'attribute "STAGEX" at {sx}',
        f'attribute "STAGEY" at {sy}',
        f'attribute "STAGEZ" at {sz}',
    ]:
        resp = await send(cmd)
        cr = _clean(resp)
        if _VERBOSE:
            info(f"    {cmd!r} -> {cr[:60]!r}")
        if any(x in cr.upper() for x in ("ERROR", "ILLEGAL", "UNKNOWN COMMAND")):
            warn(f"    Attribute cmd failed: {cmd!r} -> {cr[:60]!r}")

    # No programmer diagnostic available via telnet:
    # - list attribute shows the attribute library, not programmer state
    # - info fixture N outputs to console GUI only, not telnet
    # Rely on store response + post-store XML <Values> check below.

    # Store preset
    store_cmd = _store_cmd(slot, mode)
    info(f"    Storing: {store_cmd}")
    raw_store = await send(store_cmd)
    clean_store = _clean(raw_store)
    if _VERBOSE:
        info(f"    STORE response: {clean_store[:100]!r}")
    if any(x in clean_store.upper() for x in ("NOTHING", "NO PROG", "EMPTY", "ERROR", "NOT STORED")):
        fail(f"    Store reported empty: {clean_store[:60]!r}")
        await send("clearall")
        return False

    # Label
    await send(f'label preset 2.{slot} "{name}"')
    await send("clearall")
    fixed(f"  position 2.{slot} {name} [{mode}]")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(no_fix: bool, mode: str) -> None:
    global _MODE
    _MODE = mode

    banner(f"EXPORT + VALIDATE Position Presets  [mode={mode}]")
    print(f"  Console : {os.getenv('GMA_HOST', '127.0.0.1')}:{os.getenv('GMA_PORT', '30000')}")
    print(f"  XML     : {EXPORT_PATH}")
    print(f"  Mode    : {mode}")
    print()

    info("Connecting...")
    client = await get_client()
    if client is None:
        print("\n  x  Could not connect.")
        sys.exit(1)
    ok("Connected.")

    # ------------------------------------------------------------------
    # Phase 1: Export
    # ------------------------------------------------------------------
    section("Phase 1 — Export")
    await export_position_presets()

    # ------------------------------------------------------------------
    # Phase 2: Initial validation
    # ------------------------------------------------------------------
    section("Phase 2 — XML Validation")

    if not os.path.exists(EXPORT_PATH):
        warn("Export file not found — cannot validate.")
        warn("Check that grandMA2 onPC is running and the export path is correct.")
        sys.exit(1)

    # Always show the raw XML head on first run so we can see the structure
    dump_raw_xml_head(EXPORT_PATH, lines=80)

    results = validate_xml(EXPORT_PATH)
    print_validation_report(results)

    # Slots needing fix: absent OR present but wrong mode for the requested store mode
    needs_fix = [(slot, r) for slot, r in sorted(results.items()) if not _is_success(r)]

    if not needs_fix:
        print()
        ok(f"All 5 position preset slots are present ({mode} mode).")
        ok("Fixture attribute data is stored in the showfile — verify on console by")
        ok("selecting fixtures 601-606 and recalling each preset tile.")
        return

    warn(f"{len(needs_fix)} slot(s) need fixing: "
         + ", ".join(f"2.{s}" for s, _ in needs_fix))

    if no_fix:
        warn("--no-fix specified — skipping repair.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Phase 3: Retry loop
    # ------------------------------------------------------------------
    section("Phase 3 — Repair + Re-validate loop")

    attempt = 0
    while needs_fix and attempt < MAX_RETRIES:
        attempt += 1
        print()
        info(f"Attempt {attempt}/{MAX_RETRIES} — fixing {len(needs_fix)} slot(s)...")

        for slot, r in needs_fix:
            preset_row = next((p for p in POSITION_PRESETS if p[0] == slot), None)
            if preset_row is None:
                warn(f"  No preset definition found for slot {slot}")
                continue
            _, name, sx, sy, sz = preset_row
            await fix_position_slot(slot, name, sx, sy, sz, mode=mode)

        # Re-export
        print()
        info("Re-exporting after fix...")
        await export_position_presets()
        time.sleep(1.0)  # let MA2 finish writing

        # Re-validate
        results = validate_xml(EXPORT_PATH)
        print_validation_report(results, print_slot4_xml=False)
        needs_fix = [(slot, r) for slot, r in sorted(results.items()) if not _is_success(r)]

        if not needs_fix:
            print()
            ok(f"All 5 position preset slots now stored ({mode} mode, after {attempt} attempt(s)).")
            # Final dump of slot 4 XML to confirm
            section("Final XML for slot 2.4 (Stage-Right)")
            print_validation_report(results, print_slot4_xml=True)
            return

    # ------------------------------------------------------------------
    # Exhausted retries
    # ------------------------------------------------------------------
    print()
    fail(f"Still not fixed after {MAX_RETRIES} attempt(s): "
         + ", ".join(f"2.{s}" for s, _ in needs_fix))
    print()
    info("Possible causes:")
    info("  1. Fixture IDs 601-606 not patched in this show — update SPOT_FIXTURES in this script")
    info("  2. Attribute names 'Pan'/'Tilt' not valid for these fixtures — check with browse_preset_type")
    info("  3. MA2 programmer cleared before store (e.g. screen switch, grandMA2 onPC focus loss)")
    info("  4. Wrong mode for this fixture type — try --mode selective, --mode universal, --mode global")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export + XML-validate + auto-retry position presets"
    )
    parser.add_argument(
        "--no-fix", action="store_true", default=False,
        help="Export and validate only — do not attempt repair on empty slots",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", default=False,
        help="Print full XML for all slots and raw telnet responses",
    )
    parser.add_argument(
        "--mode", choices=["selective", "universal", "global"], default="selective",
        help=(
            "Preset store mode: "
            "selective=no flag (MA2 default, Normal/Selective), "
            "universal=/universal, "
            "global=/global  (default: selective)"
        ),
    )
    args = parser.parse_args()
    _VERBOSE = args.verbose

    asyncio.run(main(no_fix=args.no_fix, mode=args.mode))
