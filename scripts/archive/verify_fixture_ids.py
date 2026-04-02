"""Test: can we discover fixture ID range for a FixtureType dynamically in a macro?"""
import asyncio
import re
import sys
sys.path.insert(0, ".")
from src.telnet_client import GMA2TelnetClient


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


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    print("=" * 70)
    print("TEST: Discover fixture IDs per FixtureType")
    print("=" * 70)

    # For each FT, select it and see what we can learn about fixture IDs
    for ft in range(1, 8):
        await client.send_command("ClearAll", delay=0.3)
        await cmd(client, f"FixtureType {ft}.1.1 Thru", delay=0.5)
        count = await get_selfix_count(client)

        # Store as a temp group and export to see fixture IDs
        await cmd(client, f"Store Group 990 /o", delay=0.5)
        fname = f"test_ft{ft}"
        fpath = f"C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\importexport\\{fname}.xml"
        from pathlib import Path
        p = Path(fpath)
        if p.exists():
            p.unlink()
        await cmd(client, f'Export Group 990 "{fname}"', delay=2.0)
        await asyncio.sleep(0.5)

        if p.exists():
            import xml.etree.ElementTree as ET
            tree = ET.parse(p)
            root = tree.getroot()
            fix_ids = set()
            for elem in root.iter():
                local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if local == "Subfixture":
                    fix_ids.add(int(elem.get("fix_id", "0")))
            fix_ids_sorted = sorted(fix_ids)
            p.unlink()
            print(f"  FT {ft}: {count} subfixtures, fix_ids={fix_ids_sorted}")
        else:
            print(f"  FT {ft}: {count} subfixtures, export failed")

    print()
    print("=" * 70)
    print("TEST: SelFix Fixture range vs FixtureType Thru ordering")
    print("=" * 70)

    # For FT 4 (fix_ids 401-404), test SelFix range
    await client.send_command("ClearAll", delay=0.3)
    await cmd(client, "SelFix Fixture 401 Thru 404", delay=0.5)
    c1 = await get_selfix_count(client)
    print(f"  SelFix Fixture 401 Thru 404: {c1} fixtures (fixture-grouped order)")

    # Also test: can macro discover first/last fixture ID from a FixtureType?
    # Test: after FixtureType selection, is there a system var with fixture IDs?
    print()
    print("=" * 70)
    print("TEST: System vars after FixtureType selection")
    print("=" * 70)

    await client.send_command("ClearAll", delay=0.3)
    await cmd(client, "FixtureType 4.1.1 Thru", delay=0.5)

    # Check various system vars
    for var in ["$SELECTEDFIXTURESCOUNT", "$SELECTEDEXEC", "$SELECTEDEXECCUE"]:
        resp = await cmd(client, f"ListVar {var}", delay=0.3)
        for line in resp.split("\n"):
            if "ListVar" in line and "Executing" not in line:
                print(f"  {var} = {line.strip()}")

    # Test: can Next/Previous with MAtricks give us individual fixture selection?
    print()
    print("=" * 70)
    print("TEST: MAtricks Blocks=7 + Next -> per-fixture sub-selection for Store")
    print("=" * 70)

    # With 28 fixtures in patch order, Blocks=7 should give 4 blocks of 7
    # (one block per physical fixture IF patch is sequential within fixture)
    await client.send_command("ClearAll", delay=0.3)
    await cmd(client, "SelFix Fixture 401 Thru 404", delay=0.5)
    print(f"  Starting with SelFix Fixture 401 Thru 404 (fixture-grouped order)")
    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, "MAtricksBlocks 7", delay=0.3)

    from pathlib import Path as P2
    import xml.etree.ElementTree as ET2

    for step in range(5):
        await cmd(client, "Next", delay=0.3)
        await cmd(client, f"Store Group {990 + step} /o", delay=0.5)

    await cmd(client, "MAtricksReset", delay=0.3)
    await client.send_command("ClearAll", delay=0.3)

    for step in range(5):
        gnum = 990 + step
        await client.send_command("ClearAll", delay=0.3)
        await client.send_command(f"SelFix Group {gnum}", delay=0.5)
        c = await get_selfix_count(client)
        if c > 0:
            fname = f"test_blocks_{gnum}"
            fpath = P2(f"C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\importexport\\{fname}.xml")
            if fpath.exists():
                fpath.unlink()
            await cmd(client, f'Export Group {gnum} "{fname}"', delay=2.0)
            await asyncio.sleep(0.5)
            if fpath.exists():
                tree = ET2.parse(fpath)
                root = tree.getroot()
                fixes = []
                for elem in root.iter():
                    local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    if local == "Subfixture":
                        fixes.append(f"{elem.get('fix_id')}.{elem.get('sub_index')}")
                fpath.unlink()
                print(f"  Block {step+1} (Group {gnum}): {c} fixtures -> {', '.join(fixes)}")
            else:
                print(f"  Block {step+1}: count={c}, export failed")
        else:
            print(f"  Block {step+1}: empty")

    # Cleanup
    for g in range(990, 996):
        await cmd(client, f"Delete Group {g} /nc", delay=0.2)
    await cmd(client, "MAtricksReset", delay=0.3)
    await client.send_command("ClearAll", delay=0.3)
    print("\nDone.")

    await client.disconnect()


asyncio.run(main())
