"""Debug v8 macro execution — trace, fixture order audit, and appearance color audit."""
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


def export_fixture_order(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    fixtures = []
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == "Subfixture":
            fixtures.append((elem.get("fix_id", "?"), elem.get("sub_index", "?")))
    return fixtures


async def export_and_show(client, group_num, label):
    fname = f"audit_v8_g{group_num}"
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


async def get_appearance_color(client, object_type, object_id):
    """Get appearance color via info command, return hex string or None."""
    resp = await cmd(client, f"info {object_type} {object_id}", delay=0.5)
    # Look for color info in response
    for line in resp.split("\n"):
        s = line.strip()
        if "Appearance" in s or "Color" in s or "color" in s:
            m = re.search(r"([0-9a-fA-F]{6})", s)
            if m:
                return m.group(1)
    return None


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # Clean pools
    for c in [
        "delete group 1 thru 999 /nc",
        "delete world 2 thru 999 /nc",
        "delete preset 0.1 thru 0.999 /nc",
        "ClearAll",
    ]:
        await client.send_command_with_response(c, timeout=5.0, delay=2.0)
        await flush(client)
    print("Pools cleaned.\n")

    # Delete and reimport macro 8 (ensure latest version)
    await go_root(client)
    print("Deleting macro 8 (if exists)...")
    await client.send_command_with_response("delete macro 8 /nc", timeout=5.0, delay=1.0)
    await flush(client)
    print("Importing macro 8...")
    resp = await client.send_command_with_response(
        'import "auto_create_multi_pools_v10" at macro 8 /nc',
        timeout=5.0, delay=2.0,
    )
    print(f"Import response:\n{clean(resp)}\n")
    await flush(client)

    # Run macro
    await flush(client)
    print(f"Go Macro 8 -- {time.strftime('%H:%M:%S')}")
    client._writer.write("Go Macro 8\r\n")

    all_output = []
    start = time.time()
    while time.time() - start < 180:
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
    print("FIXTURE ORDER AUDIT")
    print("=" * 70)
    await asyncio.sleep(1.0)
    await go_root(client)

    for g in range(1, 10):
        await client.send_command("ClearAll", delay=0.3)
        await client.send_command(f"SelFix Group {g}", delay=0.5)
        resp = await cmd(client, "ListVar $SELECTEDFIXTURESCOUNT", delay=0.5)
        count = "?"
        for line in resp.split("\n"):
            if "SELECTEDFIXTURESCOUNT" in line:
                m = re.search(r"=\s*(\d+)", line)
                if m:
                    count = m.group(1)

        await client.send_command("ClearAll", delay=0.3)
        fixtures = await export_and_show(client, g, f"FT Group {g} (count={count})")

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

    # === APPEARANCE COLOR AUDIT ===
    print("\n" + "=" * 70)
    print("APPEARANCE COLOR AUDIT")
    print("=" * 70)
    await go_root(client)

    # List groups to find all group slots
    resp = await client.send_command_with_response("list group", timeout=5.0, delay=1.0)
    c = clean(resp)
    groups = {}
    for line in c.split("\n"):
        s = line.strip()
        if "Group" in s and not any(skip in s for skip in NOISE):
            m = re.search(r"Group\s+(\d+)\s+\d+\s+(.*)", s)
            if m:
                groups[int(m.group(1))] = m.group(2).strip()

    # Export each group to check its appearance color
    print(f"\n  {'Slot':<6} {'Label':<16} {'Color'}")
    print(f"  {'-'*6} {'-'*16} {'-'*12}")
    for gnum in sorted(groups.keys()):
        fname = f"color_audit_g{gnum}"
        fpath = IMPORTEXPORT / f"{fname}.xml"
        if fpath.exists():
            fpath.unlink()
        await cmd(client, f'Export Group {gnum} "{fname}"', delay=1.0)
        await asyncio.sleep(0.3)
        color = "none"
        if fpath.exists():
            tree = ET.parse(fpath)
            root = tree.getroot()
            for elem in root.iter():
                local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if local == "Appearance":
                    color = elem.get("Color", "none")
                    break
            fpath.unlink()
        print(f"  {gnum:<6} {groups[gnum]:<16} {color}")

    # Export presets and worlds too
    print(f"\n  {'Type':<8} {'Slot':<6} {'Color'}")
    print(f"  {'-'*8} {'-'*6} {'-'*12}")
    for slot in range(11, 20):
        for obj_type, obj_id in [("Preset 0", slot), ("World", slot)]:
            fname = f"color_audit_{obj_type.replace(' ', '_')}_{slot}"
            fpath = IMPORTEXPORT / f"{fname}.xml"
            if fpath.exists():
                fpath.unlink()
            await cmd(client, f'Export {obj_type}.{slot} "{fname}"', delay=1.0)
            await asyncio.sleep(0.3)
            color = "none"
            if fpath.exists():
                tree = ET.parse(fpath)
                root = tree.getroot()
                for elem in root.iter():
                    local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    if local == "Appearance":
                        color = elem.get("Color", "none")
                        break
                fpath.unlink()
            print(f"  {obj_type:<8} {slot:<6} {color}")

    await client.send_command("ClearAll", delay=0.3)
    await client.disconnect()


asyncio.run(main())
