"""Verify fixture ordering in groups via Export XML parsing."""
import asyncio
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, ".")
from src.telnet_client import GMA2TelnetClient

IMPORTEXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport")


def clean(s):
    return re.sub(r"\x1b\[[0-9;]*m", "", s).replace("[K", "")


async def flush(client):
    try:
        await asyncio.wait_for(client._reader.read(16384), timeout=0.5)
    except Exception:
        pass


async def go_root(client):
    for _ in range(5):
        await client.send_command("cd /", delay=0.2)
    await asyncio.sleep(0.3)
    await flush(client)


async def cmd(client, command, delay=1.0):
    resp = await client.send_command_with_response(command, timeout=5.0, delay=delay)
    return clean(resp)


def parse_group_xml(filepath):
    """Parse exported group XML and return fixture references in order."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {"ma": "http://schemas.malighting.de/grandma2/xml/MA"}

    fixtures = []
    # Try various possible element names
    for tag in ["Subfixture", "Fixture", "FixtureRef", "Selection", "SubFixture"]:
        for elem in root.iter():
            local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if local == tag:
                fixtures.append(dict(elem.attrib))

    # Also dump raw structure for analysis
    all_elements = []
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if elem.attrib:
            all_elements.append((local, dict(elem.attrib)))

    return fixtures, all_elements


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # Export Group 4 (FT 4. lump - 28 fixtures, patch-ordered)
    print("Exporting Group 4 (FT 4. lump, 28 fixtures)...")
    export_file = IMPORTEXPORT / "audit_group4.xml"
    if export_file.exists():
        export_file.unlink()
    resp = await cmd(client, 'Export Group 4 "audit_group4"', delay=2.0)
    print(f"  Export response: {resp.strip()}")

    await asyncio.sleep(1.0)

    if export_file.exists():
        print(f"\n  File exists: {export_file}")
        # Print raw XML
        raw = export_file.read_text(encoding="utf-8")
        print(f"\n  === GROUP 4 RAW XML ({len(raw)} chars) ===")
        for i, line in enumerate(raw.split("\n")[:60]):
            print(f"    {i:3d}: {line}")
        if len(raw.split("\n")) > 60:
            print(f"    ... ({len(raw.split(chr(10)))} total lines)")

        fixtures, all_elems = parse_group_xml(export_file)
        print(f"\n  Fixture elements found: {len(fixtures)}")
        for f in fixtures[:10]:
            print(f"    {f}")
        print(f"\n  All elements with attributes:")
        for tag, attrs in all_elems[:30]:
            print(f"    <{tag}> {attrs}")
    else:
        print(f"  ERROR: Export file not found at {export_file}")

    # Also export Group 5 (FT 4.1.1, 4 fixtures) for comparison
    print("\n\nExporting Group 5 (FT 4.1.1, 4 fixtures)...")
    export_file5 = IMPORTEXPORT / "audit_group5.xml"
    if export_file5.exists():
        export_file5.unlink()
    resp = await cmd(client, 'Export Group 5 "audit_group5"', delay=2.0)
    print(f"  Export response: {resp.strip()}")

    await asyncio.sleep(1.0)

    if export_file5.exists():
        raw5 = export_file5.read_text(encoding="utf-8")
        print(f"\n  === GROUP 5 RAW XML ({len(raw5)} chars) ===")
        for i, line in enumerate(raw5.split("\n")[:40]):
            print(f"    {i:3d}: {line}")

        fixtures5, _ = parse_group_xml(export_file5)
        print(f"\n  Fixture elements found: {len(fixtures5)}")
        for f in fixtures5[:10]:
            print(f"    {f}")
    else:
        print(f"  ERROR: Export file not found at {export_file5}")

    # Export Group 900 (merged via /merge - should have instance-ordered fixtures)
    # First check if it still exists
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 5", delay=0.5)
    await cmd(client, "Store Group 900 /o", delay=0.5)
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 6", delay=0.5)
    await cmd(client, "Store Group 900 /merge", delay=0.5)
    await client.send_command("ClearAll", delay=0.3)

    print("\n\nExporting Group 900 (merged instance 1 + instance 2)...")
    export_file900 = IMPORTEXPORT / "audit_group900.xml"
    if export_file900.exists():
        export_file900.unlink()
    resp = await cmd(client, 'Export Group 900 "audit_group900"', delay=2.0)

    await asyncio.sleep(1.0)

    if export_file900.exists():
        raw900 = export_file900.read_text(encoding="utf-8")
        print(f"\n  === GROUP 900 RAW XML ({len(raw900)} chars) ===")
        for i, line in enumerate(raw900.split("\n")[:60]):
            print(f"    {i:3d}: {line}")
        if len(raw900.split("\n")) > 60:
            print(f"    ... ({len(raw900.split(chr(10)))} total lines)")

        fixtures900, _ = parse_group_xml(export_file900)
        print(f"\n  Fixture elements found: {len(fixtures900)}")
        for f in fixtures900[:10]:
            print(f"    {f}")

    # Cleanup
    await cmd(client, "Delete Group 900 /nc", delay=0.5)
    await client.disconnect()


asyncio.run(main())
