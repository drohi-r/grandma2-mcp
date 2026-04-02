"""
Live telnet probe: Test pure-telnet filter creation via Attribute keywords.

Round 2: Tests whether Attribute "X" activates specific attributes in the
programmer, Store Filter N captures exactly those, and Export confirms via XML.

Usage:
    PYTHONPATH=. python scripts/probe_programmer_state.py
"""

import asyncio
from pathlib import Path

EXPORT_DIR = Path(
    "C:/ProgramData/MA Lighting Technologies/grandma/"
    "gma2_V_3.9.60/importexport/exports"
)


async def run_probes():
    from src.telnet_client import GMA2TelnetClient

    client = GMA2TelnetClient("127.0.0.1", 30000)
    await client.connect()
    await client.login()

    async def probe(label: str, commands: list[str]) -> None:
        print(f"\n{'='*80}")
        print(f"  PROBE: {label}")
        print(f"{'='*80}")
        for cmd in commands:
            print(f"\n  >>> {cmd}")
            resp = await client.send_command_with_response(cmd)
            print(f"  {resp.strip()}")

    def read_export(filename: str) -> None:
        fpath = EXPORT_DIR / f"{filename}.xml"
        print(f"\n  --- Exported XML: {fpath.name} ---")
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            print(content)
        else:
            print(f"  FILE NOT FOUND: {fpath}")

    # ── Test 1: Color attributes only ────────────────────────────────
    await probe("Test 1: Color attributes -> Store Filter 30", [
        "ClearAll",
        "cd /",
        "SelFix 111",
        'Attribute "COLOR1"',
        'Attribute "COLORRGB1"',
        'Attribute "COLORRGB2"',
        'Attribute "COLORRGB3"',
        "Store Filter 30",
        'Label Filter 30 "Test Color"',
        'Export Filter 30 "test_filter_color"',
    ])
    read_export("test_filter_color")

    # ── Test 2: Position attributes only ─────────────────────────────
    await probe("Test 2: Position attributes -> Store Filter 31", [
        "ClearAll",
        "SelFix 111",
        'Attribute "PAN"',
        'Attribute "TILT"',
        "Store Filter 31",
        'Label Filter 31 "Test Position"',
        'Export Filter 31 "test_filter_position"',
    ])
    read_export("test_filter_position")

    # ── Test 3: Mixed Dim + Color ────────────────────────────────────
    await probe("Test 3: Dim + Color -> Store Filter 32", [
        "ClearAll",
        "SelFix 111",
        'Attribute "DIM"',
        'Attribute "COLORRGB1"',
        'Attribute "COLORRGB2"',
        'Attribute "COLORRGB3"',
        "Store Filter 32",
        'Label Filter 32 "Test Dim+Color"',
        'Export Filter 32 "test_filter_dim_color"',
    ])
    read_export("test_filter_dim_color")

    # ── Test 4: Attribute without At value ───────────────────────────
    await probe("Test 4: Attribute without At value -> Store Filter 33", [
        "ClearAll",
        "SelFix 111",
        'Attribute "GOBO1"',
        "Store Filter 33",
        'Label Filter 33 "Test Gobo NoAt"',
        'Export Filter 33 "test_filter_gobo_noat"',
    ])
    read_export("test_filter_gobo_noat")

    # ── Cleanup ──────────────────────────────────────────────────────
    await probe("Cleanup: delete test filters", [
        "Delete Filter 30 Thru 33 /noconfirm",
        "ClearAll",
        "cd /",
    ])

    await client.disconnect()
    print("\n\nDone! Review exported XMLs above.")


if __name__ == "__main__":
    asyncio.run(run_probes())
