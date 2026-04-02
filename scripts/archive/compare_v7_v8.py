"""Compare v7 vs v8 macro output: counts, fixture order, and appearance colors."""
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


async def run_macro(client, macro_num, macro_name, timeout_s=180):
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
    start = time.time()
    client._writer.write(f"Go Macro {macro_num}\r\n")

    while time.time() - start < timeout_s:
        try:
            await asyncio.wait_for(client._reader.read(8192), timeout=2.0)
        except asyncio.TimeoutError:
            if time.time() - start > 5:
                try:
                    await asyncio.wait_for(client._reader.read(8192), timeout=3.0)
                    continue
                except asyncio.TimeoutError:
                    elapsed = time.time() - start
                    print(f"  Macro completed at {elapsed:.1f}s")
                    break

    await asyncio.sleep(2.0)
    await flush(client)
    return time.time() - start


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
    tree = ET.parse(filepath)
    root = tree.getroot()
    fixtures = []
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == "Subfixture":
            fixtures.append((elem.get("fix_id", "?"), elem.get("sub_index", "?")))
    return fixtures


def check_fixture_grouped(fixtures):
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


def get_group_color(filepath):
    """Parse exported group XML, return appearance color hex or 'none'."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == "Appearance":
            return elem.get("Color", "none")
    return "none"


async def get_fixture_order_and_color(client, group_num):
    fname = f"cmp78_g{group_num}"
    fpath = IMPORTEXPORT / f"{fname}.xml"
    if fpath.exists():
        fpath.unlink()
    await cmd(client, f'Export Group {group_num} "{fname}"', delay=2.0)
    await asyncio.sleep(0.5)
    if fpath.exists():
        fixtures = export_fixture_order(fpath)
        color = get_group_color(fpath)
        fpath.unlink()
        return fixtures, color
    return [], "none"


async def audit_pools(client):
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

    # ========== RUN v7 ==========
    print("=" * 70)
    print("PHASE 1: MACRO v7")
    print("=" * 70)
    print("  Cleaning pools...")
    await clean_pools(client)
    v7_time = await run_macro(client, 7, "::Auto Create Multi-Pools v7::", timeout_s=180)
    v7_data, v7_counts = await audit_pools(client)

    v7_orders = {}
    v7_colors = {}
    for g in sorted(v7_data["groups"].keys()):
        if g < 11:
            v7_orders[g], v7_colors[g] = await get_fixture_order_and_color(client, g)
    for g in sorted(v7_data["groups"].keys()):
        if g >= 11:
            _, v7_colors[g] = await get_fixture_order_and_color(client, g)

    print(f"\n  v7 Groups: {len(v7_data['groups'])}, Presets: {v7_data['presets']}, Worlds: {len(v7_data['worlds'])}")

    # ========== RUN v8 ==========
    print("\n" + "=" * 70)
    print("PHASE 2: MACRO v8")
    print("=" * 70)
    print("  Cleaning pools...")
    await clean_pools(client)
    v8_time = await run_macro(client, 8, "::Auto Create Multi-Pools v8::", timeout_s=180)
    v8_data, v8_counts = await audit_pools(client)

    v8_orders = {}
    v8_colors = {}
    for g in sorted(v8_data["groups"].keys()):
        if g < 11:
            v8_orders[g], v8_colors[g] = await get_fixture_order_and_color(client, g)
    for g in sorted(v8_data["groups"].keys()):
        if g >= 11:
            _, v8_colors[g] = await get_fixture_order_and_color(client, g)

    print(f"\n  v8 Groups: {len(v8_data['groups'])}, Presets: {v8_data['presets']}, Worlds: {len(v8_data['worlds'])}")

    # ========== COMPARISON ==========
    print("\n" + "=" * 70)
    print("COMPARISON: v7 vs v8")
    print("=" * 70)

    # FT groups
    all_ft_groups = sorted(set(
        [g for g in v7_data["groups"] if g < 11] +
        [g for g in v8_data["groups"] if g < 11]
    ))
    print(f"\n  {'Grp':<5} {'v7 Fix':<8} {'v7 Order':<14} {'v7 Color':<10} {'v8 Fix':<8} {'v8 Order':<14} {'v8 Color':<10} {'Match?'}")
    print(f"  {'-'*5} {'-'*8} {'-'*14} {'-'*10} {'-'*8} {'-'*14} {'-'*10} {'-'*6}")
    for g in all_ft_groups:
        v7_c = v7_counts.get(g, "-")
        v7_o = "GROUPED" if check_fixture_grouped(v7_orders.get(g, [])) else "INTERLEAVED"
        v7_col = v7_colors.get(g, "none")
        v8_c = v8_counts.get(g, "-")
        v8_o = "GROUPED" if check_fixture_grouped(v8_orders.get(g, [])) else "INTERLEAVED"
        v8_col = v8_colors.get(g, "none")
        match = "YES" if v7_c == v8_c else "DIFF"
        print(f"  {g:<5} {v7_c:<8} {v7_o:<14} {v7_col:<10} {v8_c:<8} {v8_o:<14} {v8_col:<10} {match}")

    # Pool groups
    all_pool = sorted(set(
        [g for g in v7_data["groups"] if g >= 11] +
        [g for g in v8_data["groups"] if g >= 11]
    ))
    print(f"\n  {'Pool':<5} {'v7 Label':<16} {'v7 Fix':<8} {'v7 Color':<10} {'v8 Label':<16} {'v8 Fix':<8} {'v8 Color':<10} {'Match?'}")
    print(f"  {'-'*5} {'-'*16} {'-'*8} {'-'*10} {'-'*16} {'-'*8} {'-'*10} {'-'*6}")
    for g in all_pool:
        v7_l = v7_data["groups"].get(g, "-")
        v7_c = v7_counts.get(g, "-")
        v7_col = v7_colors.get(g, "none")
        v8_l = v8_data["groups"].get(g, "-")
        v8_c = v8_counts.get(g, "-")
        v8_col = v8_colors.get(g, "none")
        match = "YES" if v7_c == v8_c else "DIFF"
        print(f"  {g:<5} {v7_l:<16} {v7_c:<8} {v7_col:<10} {v8_l:<16} {v8_c:<8} {v8_col:<10} {match}")

    # Summary
    print(f"\n  Worlds: v7={len(v7_data['worlds'])}, v8={len(v8_data['worlds'])}")
    print(f"  Presets: v7={v7_data['presets']}, v8={v8_data['presets']}")
    print(f"  Execution time: v7={v7_time:.1f}s, v8={v8_time:.1f}s, delta={v7_time - v8_time:.1f}s")

    # Color validation
    print(f"\n  {'='*40}")
    print(f"  COLOR VALIDATION")
    print(f"  {'='*40}")
    has_colors = any(c != "none" for c in v8_colors.values())
    print(f"  v7 has colors: {any(c != 'none' for c in v7_colors.values())}")
    print(f"  v8 has colors: {has_colors}")
    if has_colors:
        unique_colors = set(v8_colors.values()) - {"none"}
        print(f"  v8 unique colors: {len(unique_colors)}")
        for color in sorted(unique_colors):
            slots = [str(g) for g, c in v8_colors.items() if c == color]
            print(f"    {color}: groups {', '.join(slots)}")

    await client.disconnect()


asyncio.run(main())
