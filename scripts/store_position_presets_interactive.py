"""
scripts/store_position_presets_interactive.py

Interactive workflow for storing the 5 position presets (2.1-2.5) using Virtual Position Mode.

Since fixtures 601-606 use VPM (STAGEX/Y/Z stage coordinates, not raw Pan/Tilt),
presets must be stored while the fixtures have real XYZ data in the programmer.

The two ways to get XYZ data into the programmer:
  A) Aim the fixtures physically on the console (encoders / 3D layout) — most accurate
  B) Set STAGEX/STAGEY/STAGEZ directly if you know the coordinates

Usage:
    python scripts/store_position_presets_interactive.py           # all 5 presets
    python scripts/store_position_presets_interactive.py --slot 4  # single slot only
    python scripts/store_position_presets_interactive.py --skip-verify  # no XML check
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import time

os.environ.setdefault("GMA_AUTH_BYPASS", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.server import get_client, navigate_console  # noqa: E402

EXPORT_BASE = (
    r"C:\ProgramData\MA Lighting Technologies"
    r"\grandma\gma2_V_3.9.60\importexport"
)

PRESETS: list[tuple[int, str]] = [
    (1, "Home"),
    (2, "FOH-Center"),
    (3, "Stage-Left"),
    (4, "Stage-Right"),
    (5, "TopLight"),
]

_W = 70


def banner(title: str) -> None:
    print()
    print("=" * _W)
    print(f"  {title}")
    print("=" * _W)


def section(label: str) -> None:
    print(f"\n-- {label} {'-' * max(_W - len(label) - 4, 0)}")


def ok(msg: str) -> None:   print(f"  [OK]    {msg}")
def warn(msg: str) -> None: print(f"  [!]     {msg}")
def fail(msg: str) -> None: print(f"  [FAIL]  {msg}")
def info(msg: str) -> None: print(f"  -->     {msg}")


async def store_slot(
    client,
    slot: int,
    name: str,
    skip_verify: bool,
) -> bool:
    """Store one position preset. Returns True if XML confirms Values block."""

    async def send(cmd: str) -> str:
        r = await client.send_command_with_response(cmd)
        return re.sub(r"\x1b\[[0-9;]*m", "", r).strip()

    # Check how many fixtures are in the programmer
    raw = await send("ListVar SELECTEDFIXTURESCOUNT")
    m = re.search(r"=\s*(\d+)", raw)
    count = int(m.group(1)) if m else 0

    if count == 0:
        warn(f"0 fixtures in programmer — store will be empty. Skipping slot {slot}.")
        return False

    info(f"{count} fixture(s) in programmer — storing preset 2.{slot} ({name})...")

    raw_store = await send(f"store preset 2.{slot} /overwrite")
    cs = re.sub(r"\x1b\[[0-9;]*m", "", raw_store).strip()
    if any(x in cs.upper() for x in ("NOTHING", "NO PROG", "EMPTY", "ERROR", "NOT STORED")):
        fail(f"Store reported empty: {cs[:60]!r}")
        return False

    await send(f'label preset 2.{slot} "{name}"')
    ok(f"Stored + labeled preset 2.{slot} '{name}'")

    if skip_verify:
        return True

    # Export and verify
    fname = f"verify_preset_2_{slot}"
    fpath = os.path.join(EXPORT_BASE, fname + ".xml")
    await send(f'Export Preset 2.{slot} "{fname}" /overwrite')
    time.sleep(0.8)

    if not os.path.exists(fpath):
        warn("Export file not found — cannot verify.")
        return True  # store may still be fine

    with open(fpath, encoding="utf-8-sig", errors="replace") as f:
        content = f.read()

    if "<Values>" in content:
        ok("XML has <Values> block — position data confirmed in showfile.")
        return True
    else:
        warn("XML has NO <Values> block — programmer may have been empty when stored.")
        warn("Re-aim fixtures and run this script again for this slot.")
        return False


async def main(target_slot: int | None, skip_verify: bool) -> None:
    banner("Interactive Position Preset Store — VPM Workflow")
    print(f"  Console : {os.getenv('GMA_HOST', '127.0.0.1')}:{os.getenv('GMA_PORT', '30000')}")
    print()
    print("  Fixtures use Virtual Position Mode (STAGEX/Y/Z), NOT raw Pan/Tilt.")
    print("  Steps for each preset:")
    print("    1. On the console: select fixtures 601-606")
    print("    2. Aim them to the desired position (encoders or 3D stage layout)")
    print("    3. Press Enter here — script reads programmer and stores the preset")
    print()

    info("Connecting...")
    client = await get_client()
    if client is None:
        print("  x  Could not connect.")
        sys.exit(1)
    ok("Connected.")

    await navigate_console("/")

    slots_to_do = [(s, n) for s, n in PRESETS if target_slot is None or s == target_slot]

    if not slots_to_do:
        warn(f"Slot {target_slot} not in preset list {[s for s, _ in PRESETS]}")
        sys.exit(1)

    results: dict[int, bool] = {}

    for slot, name in slots_to_do:
        section(f"Preset 2.{slot} — {name}")
        print(f"  On the console:")
        print(f"    1. Select fixtures 601-606")
        print(f"    2. Aim them to the '{name}' position")
        print(f"    3. Press Enter when the programmer has the position data")
        print()
        try:
            input("  Press Enter to store  (Ctrl+C to skip this slot)... ")
        except KeyboardInterrupt:
            print()
            warn(f"Skipped slot 2.{slot}")
            results[slot] = False
            continue

        print()
        results[slot] = await store_slot(client, slot, name, skip_verify)

    # Summary
    section("Summary")
    print()
    print(f"  {'Slot':<8} {'Name':<16} {'Result'}")
    print(f"  {'-'*8} {'-'*16} {'-'*10}")
    for slot, name in slots_to_do:
        r = results.get(slot)
        status = "OK" if r else ("SKIPPED" if r is False else "FAILED")
        print(f"  {'2.' + str(slot):<8} {name:<16} {status}")

    if all(results.get(s) for s, _ in slots_to_do):
        print()
        ok("All slots stored with position data.")
        ok("Recall each preset tile on the console to verify fixtures move correctly.")
    else:
        print()
        warn("Some slots were skipped or failed — re-run for those slots when ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Interactively store position presets 2.1-2.5 using VPM XYZ data"
    )
    parser.add_argument(
        "--slot", type=int, default=None,
        help="Store a single slot only (1-5). Omit to do all 5."
    )
    parser.add_argument(
        "--skip-verify", action="store_true", default=False,
        help="Skip the XML export verification step after storing."
    )
    args = parser.parse_args()
    asyncio.run(main(target_slot=args.slot, skip_verify=args.skip_verify))
