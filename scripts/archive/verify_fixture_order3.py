"""Test fixture ordering approaches: SelFix Fixture Thru, MAtricks Next+Store, etc."""
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


async def get_selfix_count(client):
    resp = await cmd(client, "ListVar $SELECTEDFIXTURESCOUNT", delay=0.5)
    for line in resp.split("\n"):
        if "ListVar" in line:
            m = re.search(r"ListVar\s+(\d+)", line)
            if m:
                return int(m.group(1))
    return -1


def export_fixture_order(filepath):
    """Parse exported group XML, return list of (fix_id, sub_index) tuples."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    fixtures = []
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == "Subfixture":
            fix_id = elem.get("fix_id", "?")
            sub_idx = elem.get("sub_index", "?")
            fixtures.append((fix_id, sub_idx))
    return fixtures


async def export_and_show(client, group_num, label):
    """Export a group, parse XML, print fixture order."""
    fname = f"test_order_{group_num}"
    fpath = IMPORTEXPORT / f"{fname}.xml"
    if fpath.exists():
        fpath.unlink()
    await cmd(client, f'Export Group {group_num} "{fname}"', delay=2.0)
    await asyncio.sleep(0.5)
    if fpath.exists():
        fixtures = export_fixture_order(fpath)
        print(f"  [{label}] {len(fixtures)} fixtures:")
        # Show compact: group consecutive sub_indexes for same fix_id
        if fixtures:
            current_fix = None
            line_parts = []
            for fix_id, sub_idx in fixtures:
                tag = f"{fix_id}.{sub_idx}"
                line_parts.append(tag)
            # Print in rows of 7
            for i in range(0, len(line_parts), 7):
                print(f"    {', '.join(line_parts[i:i+7])}")
        fpath.unlink()
    else:
        print(f"  [{label}] Export failed - file not found")


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # =========================================================================
    print("=" * 70)
    print("TEST 1: Current Group 4 order (from v5 macro)")
    print("=" * 70)
    await export_and_show(client, 4, "Group 4 = FT 4. lump (v5)")

    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST 2: SelFix Fixture 401 Thru 404 -> Store Group")
    print("=" * 70)
    await client.send_command("ClearAll", delay=0.3)
    await cmd(client, "SelFix Fixture 401 Thru 404", delay=0.5)
    c = await get_selfix_count(client)
    print(f"  SelFix Fixture 401 Thru 404 -> count = {c}")
    await cmd(client, "Store Group 960 /o", delay=0.5)
    await export_and_show(client, 960, "Group 960 = SelFix Fixture 401 Thru 404")

    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST 3: MAtricks Interleave + Next -> Store (does it capture sub-selection?)")
    print("=" * 70)
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 4", delay=0.5)
    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, "MAtricksInterleave 4", delay=0.3)  # 4 physical fixtures

    for step in range(5):
        await cmd(client, "Next", delay=0.3)
        c = await get_selfix_count(client)
        await cmd(client, f"Store Group {970 + step} /o", delay=0.5)
        print(f"  Next step {step + 1}: count={c}")

    await cmd(client, "MAtricksReset", delay=0.3)
    await client.send_command("ClearAll", delay=0.3)

    for step in range(5):
        gnum = 970 + step
        await client.send_command("ClearAll", delay=0.3)
        await client.send_command(f"SelFix Group {gnum}", delay=0.5)
        c = await get_selfix_count(client)
        if c > 0:
            await export_and_show(client, gnum, f"Group {gnum} = Interleave 4 Next step {step + 1} (count={c})")
        else:
            print(f"  [Group {gnum}] Empty (count={c})")

    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST 4: MAtricks Interleave 7 + Next (7 sub-fixtures per fixture)")
    print("=" * 70)
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 4", delay=0.5)
    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, "MAtricksInterleave 7", delay=0.3)  # 7 subs per fixture

    for step in range(5):
        await cmd(client, "Next", delay=0.3)
        c = await get_selfix_count(client)
        await cmd(client, f"Store Group {980 + step} /o", delay=0.5)
        print(f"  Next step {step + 1}: count={c}")

    await cmd(client, "MAtricksReset", delay=0.3)
    await client.send_command("ClearAll", delay=0.3)

    for step in range(5):
        gnum = 980 + step
        await client.send_command("ClearAll", delay=0.3)
        await client.send_command(f"SelFix Group {gnum}", delay=0.5)
        c = await get_selfix_count(client)
        if c > 0:
            await export_and_show(client, gnum, f"Group {gnum} = Interleave 7 Next step {step + 1} (count={c})")
        else:
            print(f"  [Group {gnum}] Empty (count={c})")

    # =========================================================================
    print("\n" + "=" * 70)
    print("CLEANUP")
    print("=" * 70)
    for g in list(range(960, 966)) + list(range(970, 976)) + list(range(980, 986)):
        await cmd(client, f"Delete Group {g} /nc", delay=0.2)
    await cmd(client, "MAtricksReset", delay=0.3)
    await client.send_command("ClearAll", delay=0.3)
    print("  Done.")

    await client.disconnect()


asyncio.run(main())
