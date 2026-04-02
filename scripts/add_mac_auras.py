"""
Re-generate Mac Aura layer XML with correct format and re-import.

Mac Aura Extended has 2 instances:
  - Main Module: patch offset 1, 19 channels
  - Aura ring: patch offset 20, 10 channels
  Total: 29 DMX channels

Absolute DMX addresses: Universe 3 starts at 1025 (512*2 + 1)

Usage:
    PYTHONPATH=. python scripts/add_mac_auras.py
"""

import asyncio
from pathlib import Path
from datetime import datetime, timezone


IMPORTEXPORT_DIR = Path(
    "C:/ProgramData/MA Lighting Technologies/grandma/"
    "gma2_V_3.9.60/importexport"
)


def generate_aura_layer_xml() -> str:
    """Generate layer XML for 6 Mac Aura fixtures on universe 3."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    num_fixtures = 6
    start_id = 121
    channels_per = 29  # 19 main + 10 aura ring
    universe_3_offset = 1024  # absolute address = 1024 + dmx_addr

    fixture_type_no = 4
    fixture_type_name = "4 Mac Aura Extended - Colour Calibration Off"

    fixtures_xml = []
    for i in range(num_fixtures):
        fid = start_id + i
        name = f"Aura {i + 1}"
        dmx_start = universe_3_offset + 1 + (i * channels_per)

        # Generate Channel index elements (0 to 28 = 29 channels)
        channel_lines = "\n".join(
            f'\t\t\t\t<Channel index="{ch}" />' for ch in range(channels_per)
        )

        fixtures_xml.append(f"""\t\t<Fixture index="{i}" name="{name}" fixture_id="{fid}" channel_id="{fid}">
\t\t\t<FixtureType name="{fixture_type_name}">
\t\t\t\t<No>{fixture_type_no}</No>
\t\t\t</FixtureType>
\t\t\t<SubFixture index="0" react_to_grandmaster="true" color="ffffff">
\t\t\t\t<Patch>
\t\t\t\t\t<Address>{dmx_start}</Address>
\t\t\t\t</Patch>
\t\t\t\t<AbsolutePosition>
\t\t\t\t\t<Location x="0" y="0" z="0" />
\t\t\t\t\t<Rotation x="0" y="-0" z="0" />
\t\t\t\t\t<Scaling x="1" y="1" z="1" />
\t\t\t\t</AbsolutePosition>
{channel_lines}
\t\t\t</SubFixture>
\t\t</Fixture>""")

    return f"""<?xml version="1.0" encoding="utf-8"?>
<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://schemas.malighting.de/grandma2/xml/MA" xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd" major_vers="3" minor_vers="9" stream_vers="60">
\t<Info datetime="{now}" showfile="claude_ma2_ctrl" />
\t<Layer index="4" name="Mac Auras">
{chr(10).join(fixtures_xml)}
\t</Layer>
</MA>"""


async def add_auras():
    from src.telnet_client import GMA2TelnetClient

    client = GMA2TelnetClient("127.0.0.1", 30000)
    await client.connect()
    await client.login()

    async def run(label: str, commands: list[str]) -> None:
        print(f"\n{'='*70}")
        print(f"  {label}")
        print(f"{'='*70}")
        for cmd in commands:
            print(f"  >>> {cmd}")
            resp = await client.send_command_with_response(cmd)
            resp_clean = resp.strip()
            if resp_clean:
                print(f"  {resp_clean[:600]}")

    # Step 1: Delete existing unpatched Layer 4
    # Need to navigate into EditSetup/Layers context first
    await run("Delete existing unpatched Layer 4", [
        'cd "EditSetup"',
        'cd "Layers"',
        'cd 4',
        'list',
        'cd /',
        # Try deleting via the layer context
        'cd "EditSetup"',
        'cd "Layers"',
        'Delete 4 /noconfirm',
        'list',
        'cd /',
    ])

    # Step 2: Write new layer XML
    xml_content = generate_aura_layer_xml()
    xml_path = IMPORTEXPORT_DIR / "mac_aura_layer.xml"
    xml_path.write_text(xml_content, encoding="utf-8")
    print(f"\n  Wrote layer XML to: {xml_path}")

    # Step 3: Import the layer (overwrite existing)
    await run("Import Mac Aura layer", [
        'cd "EditSetup"',
        'cd "Layers"',
        'Import "mac_aura_layer" At Layer 4',
        'list',
        'cd /',
    ])

    # Step 4: Verify patch
    await run("Verify Aura fixtures", [
        "List Fixture 121 Thru 126",
    ])

    # Step 5: Check channel assignments
    await run("List Channel for Auras", [
        "List Channel 121 Thru 126",
    ])

    await client.disconnect()
    print("\n\nDone!")


if __name__ == "__main__":
    asyncio.run(add_auras())
