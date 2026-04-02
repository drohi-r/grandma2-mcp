"""Compare v5 vs v6 macro output: counts + fixture ORDER validation."""
import asyncio
import re
import time
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, ".")
from src.telnet_client import GMA2TelnetClient

IMPORTEXPORT = Path(r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport")

NOISE = [
    "Executing", "ChangeDest", "UserSettings", "Selection", "BlindProgrammer",
    "BlindSelection", "Displays", "Views", "MainViews", "StoreDefaults",
    "MatrixPool", "ViewButtons", "Arrangements", "LayerMask", "StoreSettings",
    "Cameras", "Rendering", "Remote", "Preview", "MaskPool", "Screen",
    "SurfaceCollect", "ShortcutDef", "DMXPorts",
]


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


async def clean_pools(client):
    for c in [
        "delete group 1 thru 999 /nc",
        "delete world 2 thru 999 /nc",
        "delete preset 0.1 thru 0.999 /nc",
        "ClearAll",
    ]:
        await client.send_command_with_response(c, timeout=5.0, delay=2.0)
        await flush(client)


async def run_macro(client, macro_num, macro_name, timeout_s=120):
    await go_root(client)
    resp = await client.send_command_with_response(
        f"list macro {macro_num}", timeout=5.0, delay=1.0
    )
    c = clean(resp)
    xml_name = macro_name.replace("::", "").replace(" ", "_").lower()
    if macro_name not in c:
        print(f"  Importing macro {macro_num}...")
        await client.send_command_with_response(
            f'import "{xml_name}" at macro {macro_num} /nc',
            timeout=5.0, delay=2.0,
        )
        await flush(client)

    await flush(client)
    print(f"  Go Macro {macro_num} -- {time.strftime('%H:%M:%S')}")
    client._writer.write(f"Go Macro {macro_num}\r\n")

    start = time.time()
    while time.time() - start < timeout_s:
        try:
            await asyncio.wait_for(client._reader.read(8192), timeout=2.0)
        except asyncio.TimeoutError:
            if time.time() - start > 5:
                try:
                    await asyncio.wait_for(client._reader.read(8192), timeout=3.0)
                    continue
                except asyncio.TimeoutError:
                    print(f"  Macro completed at {time.time() - start:.1f}s")
                    break

    await asyncio.sleep(2.0)
    await flush(client)


async def get_selfix_count(client, selfix_cmd):
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command(selfix_cmd, delay=0.5)
    resp = await client.send_command_with_response(
        "ListVar $SELECTEDFIXTURESCOUNT", timeout=3.0, delay=0.5
    )
    c = clean(resp)
    for line in c.split("\n"):
        if "ListVar" in line:
            m = re.search(r"ListVar\s+(\d+)", line)
            if m:
                return m.group(1)
    return "?"


def export_fixture_order(filepath):
    """Parse exported group XML, return list of (fix_id, sub_index) tuples."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    fixtures = []
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == "Subfixture":
            fixtures.append((elem.get("fix_id", "?"), elem.get("sub_index", "?")))
    return fixtures


def check_fixture_grouped(fixtures):
    """Return True if all subs of each fix_id are contiguous."""
    if len(fixtures) <= 1:
        return True
    fix_ids_seen = []
    current_fix = None
    for fid, _ in fixtures:
        if fid != current_fix:
            if fid in fix_ids_seen:
                return False
            fix_ids_seen.append(fid)
            current_fix = fid
    return True


async def get_fixture_order(client, group_num):
    """Export a group and return its fixture order."""
    fname = f"cmp_order_g{group_num}"
    fpath = IMPORTEXPORT / f"{fname}.xml"
    if fpath.exists():
        fpath.unlink()
    await cmd(client, f'Export Group {group_num} "{fname}"', delay=2.0)
    await asyncio.sleep(0.5)
    if fpath.exists():
        fixtures = export_fixture_order(fpath)
        fpath.unlink()
        return fixtures
    return []


async def audit_pools(client):
    """Audit groups, worlds, presets and return structured data."""
    result = {"groups": {}, "worlds": [], "presets": "?"}

    await go_root(client)
    resp = await client.send_command_with_response("list group", timeout=5.0, delay=1.0)
    c = clean(resp)
    for line in c.split("\n"):
        s = line.strip()
        if "Group" in s and not any(skip in s for skip in NOISE):
            m = re.search(r"Group\s+(\d+)\s+\d+\s+(.*)", s)
            if m:
                gnum = int(m.group(1))
                label = m.group(2).strip()
                result["groups"][gnum] = label

    group_counts = {}
    for gnum in sorted(result["groups"].keys()):
        count = await get_selfix_count(client, f"SelFix Group {gnum}")
        group_counts[gnum] = count

    await go_root(client)
    resp = await client.send_command_with_response("list world", timeout=5.0, delay=1.0)
    c = clean(resp)
    for line in c.split("\n"):
        s = line.strip()
        if "World" in s and not any(skip in s for skip in NOISE):
            m = re.search(r"World\s+(\d+)\s+\d+\s+(.*)", s)
            if m:
                wnum = int(m.group(1))
                label = m.group(2).strip()
                if wnum > 1:
                    result["worlds"].append((wnum, label))

    await go_root(client)
    for nav in ["cd 17", "cd 1"]:
        await client.send_command(nav, delay=0.3)
    resp = await client.send_command_with_response("list", timeout=5.0, delay=1.0)
    c = clean(resp)
    for line in c.split("\n"):
        if "PresetPool 0 ALL" in line:
            m = re.search(r"\((\d+)\)", line)
            if m:
                result["presets"] = m.group(1)
    await go_root(client)

    await client.send_command("ClearAll", delay=0.3)
    return result, group_counts


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # ========== RUN v5 ==========
    print("=" * 70)
    print("PHASE 1: MACRO v5")
    print("=" * 70)
    print("  Cleaning pools...")
    await clean_pools(client)
    await run_macro(client, 5, "Auto Create Multi-Pools v5", timeout_s=90)
    v5_data, v5_counts = await audit_pools(client)

    # Get fixture order for FT groups (slots 1-9)
    v5_orders = {}
    for g in sorted(v5_data["groups"].keys()):
        if g < 11:
            v5_orders[g] = await get_fixture_order(client, g)

    print(f"\n  v5 Groups: {len(v5_data['groups'])}, Presets: {v5_data['presets']}, Worlds: {len(v5_data['worlds'])}")
    print(f"  {'Grp':<5} {'Label':<16} {'SelFix':<8} {'Order'}")
    for gnum in sorted(v5_data["groups"].keys()):
        if gnum < 11:
            order = "GROUPED" if check_fixture_grouped(v5_orders.get(gnum, [])) else "INTERLEAVED"
            print(f"  {gnum:<5} {v5_data['groups'][gnum]:<16} {v5_counts.get(gnum, '?'):<8} {order}")

    # ========== RUN v6 ==========
    print("\n" + "=" * 70)
    print("PHASE 2: MACRO v6")
    print("=" * 70)
    print("  Cleaning pools...")
    await clean_pools(client)
    await run_macro(client, 6, "::Auto Create Multi-Pools v6::", timeout_s=180)
    v6_data, v6_counts = await audit_pools(client)

    # Get fixture order for FT groups
    v6_orders = {}
    for g in sorted(v6_data["groups"].keys()):
        if g < 11:
            v6_orders[g] = await get_fixture_order(client, g)

    print(f"\n  v6 Groups: {len(v6_data['groups'])}, Presets: {v6_data['presets']}, Worlds: {len(v6_data['worlds'])}")
    print(f"  {'Grp':<5} {'Label':<16} {'SelFix':<8} {'Order'}")
    for gnum in sorted(v6_data["groups"].keys()):
        if gnum < 11:
            order = "GROUPED" if check_fixture_grouped(v6_orders.get(gnum, [])) else "INTERLEAVED"
            print(f"  {gnum:<5} {v6_data['groups'][gnum]:<16} {v6_counts.get(gnum, '?'):<8} {order}")

    # ========== COMPARISON ==========
    print("\n" + "=" * 70)
    print("COMPARISON: v5 vs v6")
    print("=" * 70)

    # Compare FT groups
    all_ft_groups = sorted(set(
        [g for g in v5_data["groups"] if g < 11] +
        [g for g in v6_data["groups"] if g < 11]
    ))
    print(f"\n  {'Grp':<5} {'v5 Label':<16} {'v5 Fix':<8} {'v5 Order':<14} {'v6 Label':<16} {'v6 Fix':<8} {'v6 Order':<14} {'Fix Match?'}")
    print(f"  {'-'*5} {'-'*16} {'-'*8} {'-'*14} {'-'*16} {'-'*8} {'-'*14} {'-'*10}")
    for g in all_ft_groups:
        v5_l = v5_data["groups"].get(g, "-")
        v5_c = v5_counts.get(g, "-")
        v5_o = "GROUPED" if check_fixture_grouped(v5_orders.get(g, [])) else "INTERLEAVED"
        v6_l = v6_data["groups"].get(g, "-")
        v6_c = v6_counts.get(g, "-")
        v6_o = "GROUPED" if check_fixture_grouped(v6_orders.get(g, [])) else "INTERLEAVED"
        match = "YES" if v5_c == v6_c else "DIFF"
        print(f"  {g:<5} {v5_l:<16} {v5_c:<8} {v5_o:<14} {v6_l:<16} {v6_c:<8} {v6_o:<14} {match}")

    # Detailed fixture order for FT 4 (the multi-instance lump group)
    ft4_groups = [g for g in all_ft_groups if v5_counts.get(g) == "28" or v6_counts.get(g) == "28"]
    for g in ft4_groups:
        print(f"\n  FT Group {g} fixture order:")
        v5_fx = v5_orders.get(g, [])
        v6_fx = v6_orders.get(g, [])
        if v5_fx:
            parts = [f"{f}.{s}" for f, s in v5_fx]
            print(f"    v5: {', '.join(parts[:7])}")
            for i in range(7, len(parts), 7):
                print(f"        {', '.join(parts[i:i+7])}")
        if v6_fx:
            parts = [f"{f}.{s}" for f, s in v6_fx]
            print(f"    v6: {', '.join(parts[:7])}")
            for i in range(7, len(parts), 7):
                print(f"        {', '.join(parts[i:i+7])}")

    # Compare pool groups
    all_pool = sorted(set(
        [g for g in v5_data["groups"] if g >= 11] +
        [g for g in v6_data["groups"] if g >= 11]
    ))
    print(f"\n  {'Pool':<5} {'v5 Label':<16} {'v5 Fix':<8} {'v6 Label':<16} {'v6 Fix':<8} {'Match?'}")
    print(f"  {'-'*5} {'-'*16} {'-'*8} {'-'*16} {'-'*8} {'-'*6}")
    for g in all_pool:
        v5_l = v5_data["groups"].get(g, "-")
        v5_c = v5_counts.get(g, "-")
        v6_l = v6_data["groups"].get(g, "-")
        v6_c = v6_counts.get(g, "-")
        match = "YES" if v5_c == v6_c else "DIFF"
        print(f"  {g:<5} {v5_l:<16} {v5_c:<8} {v6_l:<16} {v6_c:<8} {match}")

    # Summary
    print(f"\n  Worlds: v5={len(v5_data['worlds'])}, v6={len(v6_data['worlds'])}")
    print(f"  Presets: v5={v5_data['presets']}, v6={v6_data['presets']}")

    await client.disconnect()


asyncio.run(main())
