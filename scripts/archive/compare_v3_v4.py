"""Compare v3 vs v5 macro output: clean → run → audit → clean → run → audit → compare."""
import asyncio
import re
import time
import sys
sys.path.insert(0, ".")
from src.telnet_client import GMA2TelnetClient


def clean(s):
    return re.sub(r"\x1b\[[0-9;]*m", "", s).replace("[K", "")


NOISE = [
    "Executing", "ChangeDest", "UserSettings", "Selection", "BlindProgrammer",
    "BlindSelection", "Displays", "Views", "MainViews", "StoreDefaults",
    "MatrixPool", "ViewButtons", "Arrangements", "LayerMask", "StoreSettings",
    "Cameras", "Rendering", "Remote", "Preview", "MaskPool", "Screen",
    "SurfaceCollect", "ShortcutDef", "DMXPorts",
]


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


async def clean_pools(client):
    for cmd in [
        "delete group 1 thru 999 /nc",
        "delete world 2 thru 999 /nc",
        "delete preset 0.1 thru 0.999 /nc",
        "ClearAll",
    ]:
        await client.send_command_with_response(cmd, timeout=5.0, delay=2.0)
        await flush(client)


async def run_macro(client, macro_num, macro_name):
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
    print(f"  Go Macro {macro_num} — {time.strftime('%H:%M:%S')}")
    client._writer.write(f"Go Macro {macro_num}\r\n")

    start = time.time()
    while time.time() - start < 60:
        try:
            chunk = await asyncio.wait_for(client._reader.read(8192), timeout=2.0)
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


async def get_selfix_count(client, cmd):
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command(cmd, delay=0.5)
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


async def audit_pools(client):
    """Audit groups, worlds, presets and return structured data."""
    result = {"groups": {}, "worlds": [], "presets": "?"}

    # List groups
    await go_root(client)
    resp = await client.send_command_with_response("list group", timeout=5.0, delay=1.0)
    c = clean(resp)
    for line in c.split("\n"):
        s = line.strip()
        if "Group" in s and not any(skip in s for skip in NOISE):
            # Parse: "Group  N N    LABEL"
            m = re.search(r"Group\s+(\d+)\s+\d+\s+(.*)", s)
            if m:
                gnum = int(m.group(1))
                label = m.group(2).strip()
                result["groups"][gnum] = label

    # Get SelFix count for each group
    group_counts = {}
    for gnum in sorted(result["groups"].keys()):
        count = await get_selfix_count(client, f"SelFix Group {gnum}")
        group_counts[gnum] = count

    # List worlds
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
                if wnum > 1:  # Skip World 1 "Full"
                    result["worlds"].append((wnum, label))

    # Count presets
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

    # ========== RUN v3 ==========
    print("=" * 70)
    print("PHASE 1: MACRO v3")
    print("=" * 70)
    print("  Cleaning pools...")
    await clean_pools(client)
    await run_macro(client, 3, "Auto Create Multi-Pools v3")
    v3_data, v3_counts = await audit_pools(client)

    print(f"\n  v3 Groups: {len(v3_data['groups'])}, Presets: {v3_data['presets']}, Worlds: {len(v3_data['worlds'])}")
    print(f"  {'Grp':<5} {'Label':<16} {'SelFix':<8}")
    for gnum in sorted(v3_data["groups"].keys()):
        print(f"  {gnum:<5} {v3_data['groups'][gnum]:<16} {v3_counts.get(gnum, '?'):<8}")
    print(f"\n  Worlds:")
    for wnum, label in v3_data["worlds"]:
        print(f"    World {wnum}: {label}")

    # ========== RUN v5 ==========
    print("\n" + "=" * 70)
    print("PHASE 2: MACRO v5")
    print("=" * 70)
    print("  Cleaning pools...")
    await clean_pools(client)
    await run_macro(client, 5, "Auto Create Multi-Pools v5")
    v4_data, v4_counts = await audit_pools(client)

    print(f"\n  v5 Groups: {len(v4_data['groups'])}, Presets: {v4_data['presets']}, Worlds: {len(v4_data['worlds'])}")
    print(f"  {'Grp':<5} {'Label':<16} {'SelFix':<8}")
    for gnum in sorted(v4_data["groups"].keys()):
        print(f"  {gnum:<5} {v4_data['groups'][gnum]:<16} {v4_counts.get(gnum, '?'):<8}")
    print(f"\n  Worlds:")
    for wnum, label in v4_data["worlds"]:
        print(f"    World {wnum}: {label}")

    # ========== COMPARISON ==========
    print("\n" + "=" * 70)
    print("COMPARISON: v3 vs v5")
    print("=" * 70)

    # Compare FT groups
    all_ft_groups = sorted(set(
        [g for g in v3_data["groups"] if g < 11] +
        [g for g in v4_data["groups"] if g < 11]
    ))
    print(f"\n  {'Grp':<5} {'v3 Label':<16} {'v3 Fix':<8} {'v5 Label':<16} {'v5 Fix':<8} {'Match?'}")
    print(f"  {'-'*5} {'-'*16} {'-'*8} {'-'*16} {'-'*8} {'-'*6}")
    for g in all_ft_groups:
        v3_l = v3_data["groups"].get(g, "-")
        v3_c = v3_counts.get(g, "-")
        v4_l = v4_data["groups"].get(g, "-")
        v4_c = v4_counts.get(g, "-")
        match = "YES" if v3_c == v4_c else "DIFF"
        print(f"  {g:<5} {v3_l:<16} {v3_c:<8} {v4_l:<16} {v4_c:<8} {match}")

    # Compare pool groups
    all_pool_groups = sorted(set(
        [g for g in v3_data["groups"] if g >= 11] +
        [g for g in v4_data["groups"] if g >= 11]
    ))
    print(f"\n  {'Pool':<5} {'v3 Label':<16} {'v3 Fix':<8} {'v5 Label':<16} {'v5 Fix':<8} {'Match?'}")
    print(f"  {'-'*5} {'-'*16} {'-'*8} {'-'*16} {'-'*8} {'-'*6}")
    for g in all_pool_groups:
        v3_l = v3_data["groups"].get(g, "-")
        v3_c = v3_counts.get(g, "-")
        v4_l = v4_data["groups"].get(g, "-")
        v4_c = v4_counts.get(g, "-")
        match = "YES" if v3_c == v4_c else "DIFF"
        print(f"  {g:<5} {v3_l:<16} {v3_c:<8} {v4_l:<16} {v4_c:<8} {match}")

    # Compare worlds
    print(f"\n  Worlds: v3={len(v3_data['worlds'])}, v5={len(v4_data['worlds'])}")
    print(f"  Presets: v3={v3_data['presets']}, v5={v4_data['presets']}")

    await client.disconnect()


asyncio.run(main())
