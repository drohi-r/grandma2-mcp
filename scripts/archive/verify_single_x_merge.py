"""Test user's approach: select each instance, MAtricks single-x through, store/merge in order."""
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


def export_order(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    return [(elem.get("fix_id"), elem.get("sub_index"))
            for elem in root.iter()
            if elem.tag.split("}")[-1] == "Subfixture"]


async def export_group(client, gnum, label):
    fname = f"test_sx_{gnum}"
    fpath = IMPORTEXPORT / f"{fname}.xml"
    if fpath.exists():
        fpath.unlink()
    await cmd(client, f'Export Group {gnum} "{fname}"', delay=2.0)
    await asyncio.sleep(0.5)
    if fpath.exists():
        fixes = export_order(fpath)
        tags = [f"{f}.{s}" for f, s in fixes]
        print(f"  [{label}] {len(fixes)} fixtures:")
        for i in range(0, len(tags), 7):
            print(f"    {', '.join(tags[i:i+7])}")
        fpath.unlink()
        return fixes
    print(f"  [{label}] Export failed")
    return []


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # =========================================================================
    print("=" * 70)
    print("APPROACH A: Select each instance, MAtricks Blocks=1+Next, Store/Merge")
    print("(This iterates each instance's fixtures one at a time)")
    print("=" * 70)

    # Instance 1 (Group 5 = FT 4.1.1): 401.1, 402.1, 403.1, 404.1
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 5", delay=0.5)
    c = await get_selfix_count(client)
    print(f"\n  Instance 1 (Group 5): {c} fixtures")

    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, "MAtricksBlocks 1", delay=0.3)

    # Step through instance 1, storing first fixture as /o, rest as /merge
    first = True
    for i in range(c):
        await cmd(client, "Next", delay=0.2)
        if first:
            await cmd(client, "Store Group 900 /o", delay=0.3)
            first = False
        else:
            await cmd(client, "Store Group 900 /merge", delay=0.3)

    await cmd(client, "MAtricksReset", delay=0.3)

    # Instance 2 (Group 6 = FT 4.1.2): 24 fixtures
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 6", delay=0.5)
    c2 = await get_selfix_count(client)
    print(f"  Instance 2 (Group 6): {c2} fixtures")

    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, "MAtricksBlocks 1", delay=0.3)

    for i in range(c2):
        await cmd(client, "Next", delay=0.2)
        await cmd(client, "Store Group 900 /merge", delay=0.3)

    await cmd(client, "MAtricksReset", delay=0.3)
    await client.send_command("ClearAll", delay=0.3)

    # Check result
    await client.send_command("SelFix Group 900", delay=0.5)
    total = await get_selfix_count(client)
    print(f"\n  Result Group 900: {total} fixtures (expect 28)")
    await client.send_command("ClearAll", delay=0.3)
    await export_group(client, 900, "Approach A: instance1 then instance2 (single-x)")

    # =========================================================================
    print("\n" + "=" * 70)
    print("APPROACH B: Interleave instances - pick from inst1 then inst2 alternately")
    print("(401.1 from inst1, then 401.2-7 from inst2, then 402.1, then 402.2-7...)")
    print("=" * 70)

    # This requires knowing there are 4 physical fixtures and 7 subs each
    # Instance 1 has 4 fixtures (1 sub each), Instance 2 has 24 (6 subs each)
    # Physical fixture count = instance1_count = 4
    # Subs per fixture in inst2 = inst2_count / inst1_count = 24/4 = 6

    await client.send_command("ClearAll", delay=0.3)

    # Select instance 1, set blocks=1, step through each fixture
    await client.send_command("SelFix Group 5", delay=0.5)
    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, "MAtricksBlocks 1", delay=0.3)

    # For each physical fixture: pick 1 from inst1, then 6 from inst2
    phys_count = c  # 4 physical fixtures
    subs_per_phys = c2 // phys_count  # 6

    first = True
    for phys in range(phys_count):
        # Pick this fixture's sub from instance 1
        await client.send_command("ClearAll", delay=0.2)
        await client.send_command("SelFix Group 5", delay=0.3)
        await cmd(client, "MAtricksReset", delay=0.2)
        await cmd(client, "MAtricksBlocks 1", delay=0.2)
        for _ in range(phys + 1):
            await cmd(client, "Next", delay=0.2)
        if first:
            await cmd(client, "Store Group 901 /o", delay=0.3)
            first = False
        else:
            await cmd(client, "Store Group 901 /merge", delay=0.3)

        # Pick this fixture's subs from instance 2
        await client.send_command("ClearAll", delay=0.2)
        await client.send_command("SelFix Group 6", delay=0.3)
        await cmd(client, "MAtricksReset", delay=0.2)
        await cmd(client, "MAtricksBlocks 1", delay=0.2)
        start = phys * subs_per_phys
        for s in range(start + 1):  # +1 because Next starts from 0
            await cmd(client, "Next", delay=0.15)
        await cmd(client, "Store Group 901 /merge", delay=0.3)

        # Now merge the remaining subs of this fixture from instance 2
        for s in range(subs_per_phys - 1):
            await cmd(client, "Next", delay=0.15)
            await cmd(client, "Store Group 901 /merge", delay=0.3)

    await cmd(client, "MAtricksReset", delay=0.3)
    await client.send_command("ClearAll", delay=0.3)

    await client.send_command("SelFix Group 901", delay=0.5)
    total_b = await get_selfix_count(client)
    print(f"\n  Result Group 901: {total_b} fixtures (expect 28)")
    await client.send_command("ClearAll", delay=0.3)
    await export_group(client, 901, "Approach B: interleaved fixture-grouped")

    # =========================================================================
    print("\n" + "=" * 70)
    print("APPROACH C: SelFix Fixture N Thru M (known correct order)")
    print("=" * 70)
    await client.send_command("ClearAll", delay=0.3)
    await cmd(client, "SelFix Fixture 401 Thru 404", delay=0.5)
    await cmd(client, "Store Group 902 /o", delay=0.5)
    await client.send_command("ClearAll", delay=0.3)
    await export_group(client, 902, "Approach C: SelFix Fixture 401 Thru 404")

    # =========================================================================
    print("\n" + "=" * 70)
    print("CLEANUP")
    print("=" * 70)
    for g in [900, 901, 902]:
        await cmd(client, f"Delete Group {g} /nc", delay=0.3)
    await cmd(client, "MAtricksReset", delay=0.3)
    await client.send_command("ClearAll", delay=0.3)
    print("  Done.")

    await client.disconnect()


asyncio.run(main())
