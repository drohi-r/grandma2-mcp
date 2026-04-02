"""CD Index Audit: Before/After Macro v4 Execution."""
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


def extract_data(raw):
    c = clean(raw)
    lines = []
    for l in c.split("\n"):
        s = l.strip()
        if not s:
            continue
        if any(skip in s for skip in NOISE):
            continue
        lines.append(s)
    return lines


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


async def cd_list(client, path_parts, label):
    await go_root(client)
    for p in path_parts:
        await client.send_command(f"cd {p}", delay=0.5)
    resp = await client.send_command_with_response("list", timeout=5.0, delay=1.0)
    await go_root(client)
    data = extract_data(resp)
    print(f"  [{label}]")
    if data:
        for d in data:
            print(f"    {d}")
    else:
        print("    (empty / NO OBJECTS FOUND)")
    print()
    return data


async def direct_list(client, cmd, label):
    await go_root(client)
    resp = await client.send_command_with_response(cmd, timeout=5.0, delay=1.0)
    data = extract_data(resp)
    print(f"  [{label}]")
    if data:
        for d in data:
            print(f"    {d}")
    else:
        print("    (empty / NO OBJECTS FOUND)")
    print()
    return data


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # STEP 1: CLEAN SLATE
    print("=" * 60)
    print("STEP 1: CLEAN SLATE")
    print("=" * 60)
    for cmd in [
        "delete group 1 thru 999 /nc",
        "delete world 2 thru 999 /nc",
        "delete preset 0.1 thru 0.999 /nc",
        "ClearAll",
    ]:
        await client.send_command_with_response(cmd, timeout=5.0, delay=2.0)
        await flush(client)
    print("  Deleted all groups, worlds (except 1), and ALL presets.")
    print()

    # STEP 2: BEFORE AUDIT
    print("=" * 60)
    print("STEP 2: BEFORE AUDIT — CD INDEX PROFILE (empty pools)")
    print("=" * 60)
    print()
    await cd_list(client, ["22"], "cd 22 — Groups pool overview")
    await direct_list(client, "list group", "list group — direct")
    await cd_list(client, ["18"], "cd 18 — Worlds pool overview")
    await direct_list(client, "list world", "list world — direct")
    await cd_list(client, ["17", "1"], "cd 17.1 — Preset pools overview")

    # STEP 3: RUN MACRO
    print("=" * 60)
    print("STEP 3: RUN MACRO v4")
    print("=" * 60)

    await go_root(client)
    resp = await client.send_command_with_response("list macro 4", timeout=5.0, delay=1.0)
    c = clean(resp)
    if "Auto Create Multi-Pools v4" not in c:
        print("  Macro 4 not found — importing...")
        await client.send_command_with_response(
            'import "auto_create_multi_pools_v4" at macro 4 /nc',
            timeout=5.0, delay=2.0,
        )
        await flush(client)

    await flush(client)
    print(f"  Go Macro 4 — started at {time.strftime('%H:%M:%S')}")
    client._writer.write("Go Macro 4\r\n")

    all_output = []
    start = time.time()
    while time.time() - start < 60:
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
                    print(f"  Macro completed at {elapsed:.1f}s")
                    break

    raw = "".join(all_output)
    cleaned = clean(raw)

    trace = [
        l.strip()
        for l in cleaned.split("\n")
        if l.strip() and ("Macro 4" in l or "Error" in l) and "Executing" not in l
    ]
    errors = [l for l in trace if "Error" in l]

    print(f"  Trace: {len(trace)} lines, {len(errors)} errors")
    print()

    if errors:
        print("  Errors:")
        for e in errors:
            print(f"    {e}")
        print()

    print("  Last 5 trace lines:")
    for t in trace[-5:]:
        print(f"    {t}")
    print()

    # Wait for macro to stop
    await asyncio.sleep(2.0)
    await flush(client)

    # STEP 4: AFTER AUDIT
    print("=" * 60)
    print("STEP 4: AFTER AUDIT — CD INDEX PROFILE (populated pools)")
    print("=" * 60)
    print()
    await go_root(client)
    await cd_list(client, ["22"], "cd 22 — Groups pool overview")
    await direct_list(client, "list group", "list group — direct")
    await cd_list(client, ["18"], "cd 18 — Worlds pool overview")
    await direct_list(client, "list world", "list world — direct")
    await cd_list(client, ["17", "1"], "cd 17.1 — Preset pools overview")

    await client.disconnect()


asyncio.run(main())
