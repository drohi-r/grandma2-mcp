"""
Repatch: remove wrong Mac 700 extras, import Mac Viper Profile + Mac Quantum Wash,
patch 6 Vipers (IDs 120-125) on Universe 3 and 20 Quantums (IDs 201-220) on Universe 4,
then rebuild groups 13/14/15.

What is removed:
  - Fixtures 120-125: Mac 700 Profile (FixtureType 3, 31ch), Universe 3
  - Fixtures 201-220: Mac 700 Wash Extended (FixtureType 4, 23ch), Universe 4

Target state:
  - Fixtures 120-125: Mac Viper Profile 16-bit (FixtureType 5, 33ch), Universe 3
  - Fixtures 201-220: Mac Quantum Wash basic (FixtureType 6, 24ch), Universe 4

Groups rebuilt:
  - Group 13 "Profiles" : Fixtures 111-125  (original 111-119 + new Vipers 120-125)
  - Group 14 "Washes"   : Fixtures 201-220
  - Group 15 "All Movers": Fixtures 111-125 + 201-220

Usage:
    PYTHONPATH=. python scripts/repatch_vipers_quantums.py
"""

import asyncio
import re
from pathlib import Path
from datetime import datetime, timezone


IMPORTEXPORT_DIR = Path(
    "C:/ProgramData/MA Lighting Technologies/grandma/"
    "gma2_V_3.9.60/importexport"
)

# ---------------------------------------------------------------------------
# XML generation
# ---------------------------------------------------------------------------


def generate_layer_xml(
    layer_index: int,
    layer_name: str,
    fixture_type_no: int,
    fixture_type_name: str,
    start_id: int,
    num_fixtures: int,
    channels_per: int,
    universe_offset: int,
    address_step: int,
    name_prefix: str,
) -> str:
    """Generate a grandMA2 layer XML for a block of same-type fixtures."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    fixtures_xml = []
    for i in range(num_fixtures):
        fid = start_id + i
        name = f"{name_prefix} {i + 1}"
        dmx_start = universe_offset + 1 + (i * address_step)

        channel_lines = "\n".join(
            f'\t\t\t\t<Channel index="{ch}" />' for ch in range(channels_per)
        )

        fixtures_xml.append(
            f'\t\t<Fixture index="{i}" name="{name}" fixture_id="{fid}" channel_id="{fid}">\n'
            f'\t\t\t<FixtureType name="{fixture_type_name}">\n'
            f'\t\t\t\t<No>{fixture_type_no}</No>\n'
            f'\t\t\t</FixtureType>\n'
            f'\t\t\t<SubFixture index="0" react_to_grandmaster="true" color="ffffff">\n'
            f'\t\t\t\t<Patch>\n'
            f'\t\t\t\t\t<Address>{dmx_start}</Address>\n'
            f'\t\t\t\t</Patch>\n'
            f'\t\t\t\t<AbsolutePosition>\n'
            f'\t\t\t\t\t<Location x="0" y="0" z="0" />\n'
            f'\t\t\t\t\t<Rotation x="0" y="-0" z="0" />\n'
            f'\t\t\t\t\t<Scaling x="1" y="1" z="1" />\n'
            f'\t\t\t\t</AbsolutePosition>\n'
            f'{channel_lines}\n'
            f'\t\t\t</SubFixture>\n'
            f'\t\t</Fixture>'
        )

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns="http://schemas.malighting.de/grandma2/xml/MA" '
        'xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA '
        'http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd" '
        'major_vers="3" minor_vers="9" stream_vers="60">\n'
        f'\t<Info datetime="{now}" showfile="claude_ma2_ctrl" />\n'
        f'\t<Layer index="{layer_index}" name="{layer_name}">\n'
        + "\n".join(fixtures_xml) + "\n"
        f'\t</Layer>\n'
        '</MA>'
    )


# ---------------------------------------------------------------------------
# Type number detection helpers
# ---------------------------------------------------------------------------


def _find_type_no_by_name(response: str, name_fragment: str) -> int | None:
    """Return the pool number for the first fixture type whose name contains name_fragment.

    The List FixtureType response has lines like:
      FixtureType 5 5    Mac Quantum Wash Basic  ...
    We look for lines containing name_fragment and extract the first number on that line.
    """
    clean = re.sub(r"\x1b\[[0-9;]*m", "", response)
    for line in clean.splitlines():
        if name_fragment.lower() in line.lower():
            m = re.search(r"(\d+)", line)
            if m:
                return int(m.group(1))
    return None


def _find_layer_nos_by_name(response: str, name_fragments: list[str]) -> list[int]:
    """Return layer numbers whose names contain any of the given fragments.

    The list response inside EditSetup/Layers has lines like:
      Layer 4 Mac Viper Profiles  [120..125]  ...
    """
    clean = re.sub(r"\x1b\[[0-9;]*m", "", response)
    result = []
    for line in clean.splitlines():
        for frag in name_fragments:
            if frag.lower() in line.lower():
                m = re.search(r"Layer\s+(\d+)", line, re.IGNORECASE)
                if m:
                    result.append(int(m.group(1)))
                break
    return result


# ---------------------------------------------------------------------------
# Main repatch procedure
# ---------------------------------------------------------------------------


async def repatch() -> None:
    from src.telnet_client import GMA2TelnetClient

    client = GMA2TelnetClient("127.0.0.1", 30000)
    await client.connect()
    await client.login()

    sep = "=" * 70

    async def run(label: str, commands: list[str]) -> list[str]:
        """Send commands and return stripped responses."""
        print(f"\n{sep}")
        print(f"  {label}")
        print(f"{sep}")
        responses = []
        for cmd in commands:
            print(f"  >>> {cmd}")
            resp = await client.send_command_with_response(cmd)
            resp_clean = (resp or "").strip()
            if resp_clean:
                print(f"  {resp_clean[:600]}")
            responses.append(resp_clean)
        return responses

    # ── Step 1: Check for existing Viper/Quantum fixture types ──────────────
    resps = await run("Step 1: List existing fixture types", [
        "List FixtureType",
    ])
    existing_viper_type = _find_type_no_by_name(resps[0], "Viper")
    existing_quantum_type = _find_type_no_by_name(resps[0], "Quantum")
    print(f"\n  Found: Viper type = {existing_viper_type},  Quantum type = {existing_quantum_type}")

    # ── Step 2: Import any missing fixture types ─────────────────────────────
    # Must navigate to EditSetup/FixtureTypes context before each library import.
    # Skip import if the type already exists — prevents duplicates on re-runs.
    if not existing_viper_type:
        await run("Step 2: Import Mac Viper Profile from library (EditSetup/FixtureTypes context)", [
            'cd "EditSetup"',
            'cd "FixtureTypes"',
            'Import "martin@mac_viper_profile@16_bit"',
            'cd /',
        ])
    else:
        print(f"\n  Viper Profile already in library as type {existing_viper_type} -- skipping import")

    if not existing_quantum_type:
        await run("Step 2b: Import Mac Quantum Wash from library (EditSetup/FixtureTypes context)", [
            'cd "EditSetup"',
            'cd "FixtureTypes"',
            'Import "martin@mac_quantum_wash@basic"',
            'cd /',
        ])
    else:
        print(f"\n  Quantum Wash already in library as type {existing_quantum_type} -- skipping import")

    # Confirm actual type numbers by name (authoritative — not predicted by count)
    resps2 = await run("Step 2c: Confirm actual type numbers by name", [
        "List FixtureType",
    ])
    viper_type_no = _find_type_no_by_name(resps2[0], "Viper")
    quantum_type_no = _find_type_no_by_name(resps2[0], "Quantum")
    if not viper_type_no or not quantum_type_no:
        print(f"\n  ERROR: Could not detect type numbers after import.")
        print(f"         Viper={viper_type_no}  Quantum={quantum_type_no}")
        print(f"         Check library keys: try adding a ListLibrary step to find exact names.")
        await client.disconnect()
        return

    # Known channel counts for these specific modes
    ch_viper = 33   # Mac Viper Profile 16-bit
    ch_quantum = 24  # Mac Quantum Wash basic
    print(f"\n  Viper  type {viper_type_no}: {ch_viper} ch/fixture")
    print(f"  Quantum type {quantum_type_no}: {ch_quantum} ch/fixture")
    print(f"  Universe 3 Viper  footprint: {6 * ch_viper} / 512 DMX slots")
    print(f"  Universe 4 Quantum footprint: {20 * ch_quantum} / 512 DMX slots")

    # ── Step 3: Delete any existing wrong-type fixtures ──────────────────────
    await run("Step 3: Delete fixtures 120-125 and 201-220 (no-op if absent)", [
        "Delete Fixture 120 Thru 125 /noconfirm",
        "Delete Fixture 201 Thru 220 /noconfirm",
    ])

    # ── Step 4: Clean up old Viper/Quantum layers, then find next free slot ──
    resps4 = await run("Step 4a: List existing layers", [
        'cd "EditSetup"',
        'cd "Layers"',
        "list",
        "cd /",
    ])
    list_resp = resps4[2]
    stale_layers = _find_layer_nos_by_name(list_resp, ["Viper", "Quantum"])
    if stale_layers:
        # Delete highest-numbered layer first — MA2 renumbers layers after each
        # deletion, so deleting ascending causes lower layers to shift and the
        # subsequent delete hits the wrong slot.
        print(f"\n  Deleting stale layers (descending): {sorted(stale_layers, reverse=True)}")
        del_cmds = ['cd "EditSetup"', 'cd "Layers"']
        for ln in sorted(stale_layers, reverse=True):
            del_cmds.append(f"Delete {ln} /noconfirm")
        del_cmds += ["list", "cd /"]
        resps4b = await run("Step 4b: Delete stale Viper/Quantum layers", del_cmds)
        # Re-query after deletion
        resps4 = await run("Step 4c: Re-list layers after cleanup", [
            'cd "EditSetup"', 'cd "Layers"', "list", "cd /",
        ])
        list_resp = resps4[2]

    # Find next available layer slot — MA2 always places import in next free slot,
    # so the index in the XML is advisory. Use next free to keep numbering tidy.
    clean_list = re.sub(r"\x1b\[[0-9;]*m", "", list_resp)
    used_layer_nos = [
        int(m.group(1))
        for line in clean_list.splitlines()
        for m in [re.search(r"Layer\s+(\d+)", line, re.IGNORECASE)]
        if m
    ]
    next_layer = (max(used_layer_nos) + 1) if used_layer_nos else 4
    viper_layer_idx = next_layer
    quantum_layer_idx = next_layer + 1
    print(f"\n  Used layer slots: {sorted(used_layer_nos)}")
    print(f"  Viper  -> Layer {viper_layer_idx},  Quantum -> Layer {quantum_layer_idx}")

    # Ensure fixtures 201-220 are truly gone before the Quantum layer import.
    # After stale layer deletion, any surviving fixture refs would block re-import.
    await run("Step 4d: Re-delete fixtures 120-125 and 201-220 (defensive)", [
        "Delete Fixture 120 Thru 125 /noconfirm",
        "Delete Fixture 201 Thru 220 /noconfirm",
    ])

    # Fixture type names for XML (cosmetic, <No> is authoritative)
    viper_type_name = f"{viper_type_no} Mac Viper Profile - 16 bit"
    quantum_type_name = f"{quantum_type_no} Mac Quantum Wash - basic"

    # ── Step 5: Write + import Viper layer XML ───────────────────────────────
    # Universe 3: offset 1024 (512 * 2), step = ch_viper per fixture
    viper_xml = generate_layer_xml(
        layer_index=viper_layer_idx,
        layer_name="Mac Viper Profiles",
        fixture_type_no=viper_type_no,
        fixture_type_name=viper_type_name,
        start_id=120,
        num_fixtures=6,
        channels_per=ch_viper,
        universe_offset=1024,
        address_step=ch_viper,
        name_prefix="Viper",
    )
    viper_xml_path = IMPORTEXPORT_DIR / "viper_layer.xml"
    viper_xml_path.write_text(viper_xml, encoding="utf-8")
    print(f"\n  Wrote Viper layer XML -> {viper_xml_path}")
    print(f"  Addresses: {[1 + i * ch_viper for i in range(6)]} (Universe 3 local)")

    await run("Step 5: Import Viper layer", [
        'cd "EditSetup"',
        'cd "Layers"',
        f'Import "viper_layer" At Layer {viper_layer_idx}',
        "list",
        "cd /",
    ])

    # ── Step 6: Write + import Quantum layer XML ─────────────────────────────
    # Universe 4: offset 1536 (512 * 3), step = ch_quantum per fixture
    quantum_xml = generate_layer_xml(
        layer_index=quantum_layer_idx,
        layer_name="Mac Quantum Washes",
        fixture_type_no=quantum_type_no,
        fixture_type_name=quantum_type_name,
        start_id=201,
        num_fixtures=20,
        channels_per=ch_quantum,
        universe_offset=1536,
        address_step=ch_quantum,
        name_prefix="Quantum W",
    )
    quantum_xml_path = IMPORTEXPORT_DIR / "quantum_layer.xml"
    quantum_xml_path.write_text(quantum_xml, encoding="utf-8")
    print(f"\n  Wrote Quantum layer XML -> {quantum_xml_path}")
    print(f"  Addresses: {[1 + i * ch_quantum for i in range(20)]} (Universe 4 local)")

    await run("Step 6: Import Quantum layer", [
        'cd "EditSetup"',
        'cd "Layers"',
        f'Import "quantum_layer" At Layer {quantum_layer_idx}',
        "list",
        "cd /",
    ])

    # ── Step 7: Label fixtures ────────────────────────────────────────────────
    await run('Step 7: Label fixtures "Viper" and "Quantum W"', [
        'Label Fixture 120 Thru 125 "Viper"',
        'Label Fixture 201 Thru 220 "Quantum W"',
    ])

    # ── Step 8: Rebuild groups 13 / 14 / 15 ─────────────────────────────────
    await run("Step 8: Rebuild Group 13 — Profiles (111-125)", [
        "SelFix Fixture 111 Thru 125",
        "Store Group 13 /overwrite",
        'Label Group 13 "Profiles"',
    ])

    await run("Step 8b: Rebuild Group 14 — Washes (201-220)", [
        "SelFix Fixture 201 Thru 220",
        "Store Group 14 /overwrite",
        'Label Group 14 "Washes"',
    ])

    await run("Step 8c: Rebuild Group 15 — All Movers (111-125 + 201-220)", [
        "SelFix Fixture 111 Thru 125 + Fixture 201 Thru 220",
        "Store Group 15 /overwrite",
        'Label Group 15 "All Movers"',
    ])

    # ── Step 9: Verify ────────────────────────────────────────────────────────
    await run("Step 9: Verify — Vipers (120-125)", [
        "List Fixture 120 Thru 125",
    ])
    await run("Step 9b: Verify — Quantums (201-220)", [
        "List Fixture 201 Thru 220",
    ])
    await run("Step 9c: Verify — Groups 13/14/15", [
        "List Group 13",
        "List Group 14",
        "List Group 15",
    ])

    await client.disconnect()

    print(f"\n{sep}")
    print("  REPATCH COMPLETE")
    print(f"{sep}")
    print(f"  Vipers   120-125 : FixtureType {viper_type_no}  ({ch_viper} ch)  Universe 3")
    print(f"  Quantums 201-220 : FixtureType {quantum_type_no}  ({ch_quantum} ch)  Universe 4")
    print("  Groups 13/14/15 rebuilt.")
    print()


if __name__ == "__main__":
    asyncio.run(repatch())
