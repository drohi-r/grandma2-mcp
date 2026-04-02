"""Audit ALL presets created by v7 macro — verify all values are release-only."""
import asyncio
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, ".")
from src.telnet_client import GMA2TelnetClient

IMPORTEXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport")
NS = "http://schemas.malighting.de/grandma2/xml/MA"


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


def audit_preset_xml(filepath):
    """Parse exported preset XML, return audit info."""
    tree = ET.parse(filepath)
    root = tree.getroot()

    result = {
        "name": None,
        "preset_mode": None,
        "subfixtures": [],
        "attributes": [],
        "values_with_data": [],
        "release_only": True,
    }

    # Find Preset element
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == "Preset":
            result["name"] = elem.get("name", "?")
            result["preset_mode"] = elem.get("preset_mode", "?")

        if local == "Subfixture":
            fix_id = elem.get("fix_id", "?")
            sub_idx = elem.get("sub_index", "?")
            result["subfixtures"].append(f"{fix_id}.{sub_idx}")

        if local == "PresetValue":
            attr_name = None
            value = elem.get("Value", None)
            # Find child Attribute element for the name
            for child in elem:
                child_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child_local == "Attribute":
                    attr_name = child.get("name", "?")

            entry = {"attribute": attr_name, "value": value}
            result["attributes"].append(entry)
            if value is not None:
                result["values_with_data"].append(entry)
                result["release_only"] = False

    return result


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # Discover which ALL preset slots exist (11-19 expected from v7 macro)
    print("=" * 70)
    print("ALL PRESET AUDIT — v7 Macro Output")
    print("=" * 70)

    # First, list ALL presets to see what's there
    await go_root(client)
    for nav in ["cd 17", "cd 1"]:
        await client.send_command(nav, delay=0.3)
    resp = await client.send_command_with_response("list", timeout=5.0, delay=1.0)
    c = clean(resp)
    print(f"\nPresetPool 0 (ALL) listing:")
    for line in c.split("\n"):
        if "Preset" in line.strip() or "ALL" in line:
            print(f"  {line.strip()}")
    await go_root(client)

    # Export and audit each ALL preset slot 11-19
    results = {}
    for slot in range(11, 20):
        fname = f"audit_preset_0_{slot}"
        fpath = IMPORTEXPORT / f"{fname}.xml"
        if fpath.exists():
            fpath.unlink()

        resp = await cmd(client, f'Export Preset 0.{slot} "{fname}"', delay=2.0)
        await asyncio.sleep(0.5)

        if fpath.exists():
            info = audit_preset_xml(fpath)
            results[slot] = info
            fpath.unlink()
        else:
            # Check if response indicates no object
            if "NO OBJECTS" in resp or "Error" in resp:
                print(f"\n  Preset 0.{slot}: NOT FOUND (skipping)")
            else:
                print(f"\n  Preset 0.{slot}: Export failed (no file)")

    # Print detailed audit
    print(f"\n{'='*70}")
    print("DETAILED AUDIT")
    print(f"{'='*70}")

    all_release = True
    for slot in sorted(results.keys()):
        info = results[slot]
        status = "RELEASE-ONLY" if info["release_only"] else "HAS VALUES"
        if not info["release_only"]:
            all_release = False

        print(f"\n  Preset 0.{slot} \"{info['name']}\" ({info['preset_mode']})")
        print(f"    Subfixtures: {len(info['subfixtures'])}")
        if info["subfixtures"]:
            # Show first few
            parts = info["subfixtures"]
            for i in range(0, len(parts), 7):
                print(f"      {', '.join(parts[i:i+7])}")

        print(f"    Attributes: {len(info['attributes'])} total")
        if info["attributes"]:
            # Show all attributes and their values
            for attr in info["attributes"]:
                val_str = f"Value={attr['value']}" if attr["value"] is not None else "RELEASE"
                print(f"      {attr['attribute']}: {val_str}")

        if info["values_with_data"]:
            print(f"    *** NON-RELEASE VALUES FOUND: {len(info['values_with_data'])} ***")
            for v in info["values_with_data"]:
                print(f"      {v['attribute']} = {v['value']}")

        print(f"    Status: {status}")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Presets audited: {len(results)}")
    print(f"  All release-only: {'YES' if all_release else 'NO'}")

    if not all_release:
        bad = [s for s, i in results.items() if not i["release_only"]]
        print(f"  Presets with non-release values: {bad}")
    else:
        print("  All ALL presets contain only release values — CORRECT")

    await client.send_command("ClearAll", delay=0.3)
    await client.disconnect()


asyncio.run(main())
