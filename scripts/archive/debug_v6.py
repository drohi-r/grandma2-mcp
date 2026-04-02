"""Debug v6 macro execution — capture all output and errors."""
import asyncio
import re
import time
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
    fname = f"audit_v6_g{group_num}"
    fpath = IMPORTEXPORT / f"{fname}.xml"
    if fpath.exists():
        fpath.unlink()
    await cmd(client, f'Export Group {group_num} "{fname}"', delay=2.0)
    await asyncio.sleep(0.5)
    if fpath.exists():
        fixtures = export_fixture_order(fpath)
        print(f"  [{label}] {len(fixtures)} subfixtures:")
        if fixtures:
            line_parts = [f"{fid}.{sid}" for fid, sid in fixtures]
            for i in range(0, len(line_parts), 7):
                print(f"    {', '.join(line_parts[i:i+7])}")
        fpath.unlink()
        return fixtures
    else:
        print(f"  [{label}] Export failed - file not found")
        return []


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # Clean pools first
    for c in [
        "delete group 1 thru 999 /nc",
        "delete world 2 thru 999 /nc",
        "delete preset 0.1 thru 0.999 /nc",
        "ClearAll",
    ]:
        await client.send_command_with_response(c, timeout=5.0, delay=2.0)
        await flush(client)
    print("Pools cleaned.\n")

    # Check if macro 6 exists, import if needed
    await go_root(client)
    resp = await client.send_command_with_response("list macro 6", timeout=5.0, delay=1.0)
    c = clean(resp)
    print(f"list macro 6 response:\n{c}\n")

    if "Auto Create Multi-Pools v6" not in c:
        print("Macro 6 not found - importing...")
        resp = await client.send_command_with_response(
            'import "auto_create_multi_pools_v6" at macro 6 /nc',
            timeout=5.0, delay=2.0,
        )
        print(f"Import response:\n{clean(resp)}\n")
        await flush(client)

        resp = await client.send_command_with_response("list macro 6", timeout=5.0, delay=1.0)
        print(f"After import, list macro 6:\n{clean(resp)}\n")

    # Run macro
    await flush(client)
    print(f"Go Macro 6 -- {time.strftime('%H:%M:%S')}")
    client._writer.write("Go Macro 6\r\n")

    all_output = []
    start = time.time()
    while time.time() - start < 180:  # 3 min timeout (v6 is longer due to reorder phase)
        try:
            chunk = await asyncio.wait_for(client._reader.read(8192), timeout=2.0)
            if chunk:
                all_output.append(chunk)
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            if elapsed > 5:
                try:
                    chunk = await asyncio.wait_for(client._reader.read(8192), timeout=3.0)
                    if chunk:
                        all_output.append(chunk)
                        continue
                except asyncio.TimeoutError:
                    print(f"Macro done at {elapsed:.1f}s")
                    break

    raw = "".join(all_output)
    cleaned = clean(raw)

    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    print(f"\n=== ALL OUTPUT ({len(lines)} lines) ===")
    for i, l in enumerate(lines):
        print(f"  {i:3d}: {l}")

    errors = [l for l in lines if "Error" in l or "error" in l.lower() or "UNKNOWN" in l]
    if errors:
        print(f"\n=== ERRORS ({len(errors)}) ===")
        for e in errors:
            print(f"  {e}")
    else:
        print("\n=== NO ERRORS ===")

    # === FIXTURE ORDER AUDIT ===
    print("\n" + "=" * 70)
    print("FIXTURE ORDER AUDIT - Lump FT Groups")
    print("=" * 70)
    await asyncio.sleep(1.0)
    await go_root(client)

    # FT groups should be at slots 1-7 (one per FT major)
    # FT 4 is the multi-instance one - its lump group should have fixture-grouped order
    for g in range(1, 8):
        await client.send_command("ClearAll", delay=0.3)
        await client.send_command(f"SelFix Group {g}", delay=0.5)
        resp = await cmd(client, "ListVar $SELECTEDFIXTURESCOUNT", delay=0.5)
        count_line = [l for l in resp.split("\n") if "SELECTEDFIXTURESCOUNT" in l]
        count = "?"
        if count_line:
            m = re.search(r"=\s*(\d+)", count_line[0])
            if m:
                count = m.group(1)

        # Export and check fixture order
        await client.send_command("ClearAll", delay=0.3)
        fixtures = await export_and_show(client, g, f"FT Group {g} (count={count})")

        # Check if fixture-grouped (all subs of fix N before fix N+1)
        if fixtures and len(fixtures) > 1:
            fix_ids_seen = []
            current_fix = None
            is_grouped = True
            for fid, _ in fixtures:
                if fid != current_fix:
                    if fid in fix_ids_seen:
                        is_grouped = False
                        break
                    fix_ids_seen.append(fid)
                    current_fix = fid
            order_status = "FIXTURE-GROUPED (correct)" if is_grouped else "INTERLEAVED (wrong)"
            print(f"    -> Order: {order_status}")

    await client.send_command("ClearAll", delay=0.3)
    await client.disconnect()


asyncio.run(main())
