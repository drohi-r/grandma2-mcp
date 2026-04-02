"""Verify MA2 behaviors needed for v6 macro: cd index, MAtricks Next, /merge, + operator, preset recall."""
import asyncio
import re
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


async def cmd(client, command, delay=1.0):
    resp = await client.send_command_with_response(command, timeout=5.0, delay=delay)
    return clean(resp)


async def cmd_print(client, command, label, delay=1.0):
    c = await cmd(client, command, delay=delay)
    lines = [l.strip() for l in c.split("\n") if l.strip() and not any(skip in l for skip in NOISE)]
    print(f"\n  [{label}]")
    for l in lines:
        print(f"    {l}")
    return lines


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

    # Ensure v5 pools are populated (Group 4 = FT 4. lump, Group 5 = FT 4.1.1, Group 6 = FT 4.1.2)
    await client.send_command("ClearAll", delay=0.3)
    count = await get_selfix_count(client)
    await client.send_command("SelFix Group 4", delay=0.5)
    g4_count = await get_selfix_count(client)
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 5", delay=0.5)
    g5_count = await get_selfix_count(client)
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 6", delay=0.5)
    g6_count = await get_selfix_count(client)
    await client.send_command("ClearAll", delay=0.3)

    print(f"Pre-check: Group 4={g4_count}, Group 5={g5_count}, Group 6={g6_count}")
    if g4_count < 2:
        print("ERROR: v5 pools not populated. Run v5 macro first.")
        await client.disconnect()
        return

    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST A: CD Index — Fixture Names Inside Groups")
    print("=" * 70)

    # Path 1: cd 22 -> cd N (direct group number)
    await go_root(client)
    await client.send_command("cd 22", delay=0.5)
    await cmd_print(client, "list", "cd 22 -> list (Groups pool overview)")

    await go_root(client)
    await client.send_command("cd 22", delay=0.5)
    await client.send_command("cd 4", delay=0.5)
    lines_a1 = await cmd_print(client, "list", "cd 22 -> cd 4 -> list (Group 4 direct)")

    # Path 2: cd 22 -> cd 1 -> cd N (pool -> slot)
    await go_root(client)
    await client.send_command("cd 22", delay=0.5)
    await client.send_command("cd 1", delay=0.5)
    lines_a2 = await cmd_print(client, "list", "cd 22 -> cd 1 -> list")

    await go_root(client)
    await client.send_command("cd 22", delay=0.5)
    await client.send_command("cd 1", delay=0.5)
    await client.send_command("cd 4", delay=0.5)
    lines_a3 = await cmd_print(client, "list", "cd 22 -> cd 1 -> cd 4 -> list")

    # Try Group 5 (FT 4.1.1, 4 fixtures) via whichever path worked
    await go_root(client)
    await client.send_command("cd 22", delay=0.5)
    await client.send_command("cd 5", delay=0.5)
    lines_a4 = await cmd_print(client, "list", "cd 22 -> cd 5 -> list (Group 5 = FT 4.1.1)")

    await go_root(client)

    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST B: MAtricks Single X — Next Stepping")
    print("=" * 70)

    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 4", delay=0.5)
    base_count = await get_selfix_count(client)
    print(f"\n  SelFix Group 4 -> count = {base_count}")

    # Reset MAtricks and set Interleave = 2 (instance count for FT 4)
    await cmd_print(client, "MAtricksReset", "MAtricksReset")
    await cmd_print(client, "MAtricksInterleave 2", "MAtricksInterleave 2")

    # Step with Next — check sub-selection count at each step
    for step in range(4):
        await cmd(client, "Next", delay=0.3)
        count = await get_selfix_count(client)
        print(f"  Next step {step + 1}: $SELECTEDFIXTURESCOUNT = {count}")
        # Store the sub-selection to inspect fixture names
        await cmd(client, f"Store Group {950 + step} /o", delay=0.5)

    # Inspect what Next captured via cd
    for slot in range(4):
        gnum = 950 + slot
        await go_root(client)
        await client.send_command("cd 22", delay=0.5)
        await client.send_command(f"cd {gnum}", delay=0.5)
        await cmd_print(client, "list", f"cd 22 -> cd {gnum} -> list (Next step {slot + 1})")

    # Try MAtricksBlocks as alternative
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 4", delay=0.5)
    await cmd_print(client, "MAtricksReset", "MAtricksReset (before Blocks test)")
    await cmd_print(client, "MAtricksBlocks 4", "MAtricksBlocks 4")
    for step in range(3):
        await cmd(client, "Next", delay=0.3)
        count = await get_selfix_count(client)
        print(f"  Blocks+Next step {step + 1}: $SELECTEDFIXTURESCOUNT = {count}")

    await cmd(client, "MAtricksReset", delay=0.3)
    await client.send_command("ClearAll", delay=0.3)

    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST C: Store Group /merge")
    print("=" * 70)

    # Instance 1 -> create group 900
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 5", delay=0.5)
    c1 = await get_selfix_count(client)
    await cmd_print(client, "Store Group 900 /o", "Store Group 900 /o (instance 1)")
    print(f"  Instance 1 count: {c1}")

    # Instance 2 -> merge into group 900
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 6", delay=0.5)
    c2 = await get_selfix_count(client)
    merge_resp = await cmd_print(client, "Store Group 900 /merge", "Store Group 900 /merge (instance 2)")
    print(f"  Instance 2 count: {c2}")

    # Check result
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 900", delay=0.5)
    merged_count = await get_selfix_count(client)
    print(f"  After merge: Group 900 count = {merged_count} (expect {c1 + c2})")
    print(f"  /merge {'WORKS' if merged_count == c1 + c2 else 'FAILED'}")

    # Inspect fixture order in merged group via cd
    await go_root(client)
    await client.send_command("cd 22", delay=0.5)
    await client.send_command("cd 900", delay=0.5)
    await cmd_print(client, "list", "cd 22 -> cd 900 -> list (merged group fixture order)")
    await go_root(client)

    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST D: Additive Selection with + Operator")
    print("=" * 70)

    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 5", delay=0.5)
    c_before = await get_selfix_count(client)
    print(f"  SelFix Group 5 -> count = {c_before}")

    await cmd_print(client, "+ Group 6", "+ Group 6 (additive)")
    c_after = await get_selfix_count(client)
    print(f"  After + Group 6 -> count = {c_after} (expect {g5_count + g6_count})")
    print(f"  + operator {'WORKS' if c_after == g5_count + g6_count else 'FAILED'}")

    if c_after == g5_count + g6_count:
        await cmd_print(client, "Store Group 901 /o", "Store Group 901 /o (from + selection)")
        # Inspect fixture order
        await go_root(client)
        await client.send_command("cd 22", delay=0.5)
        await client.send_command("cd 901", delay=0.5)
        await cmd_print(client, "list", "cd 22 -> cd 901 -> list (+ operator fixture order)")
        await go_root(client)

    await client.send_command("ClearAll", delay=0.3)

    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST E: Sequential Preset Recall Accumulation")
    print("=" * 70)

    await client.send_command("ClearAll", delay=0.3)
    await cmd_print(client, 'Preset 0."FT 4.1.1', 'Preset 0."FT 4.1.1 (first recall)')
    c_first = await get_selfix_count(client)
    print(f"  After first preset recall -> count = {c_first}")

    await cmd_print(client, 'Preset 0."FT 4.1.2', 'Preset 0."FT 4.1.2 (second recall)')
    c_second = await get_selfix_count(client)
    print(f"  After second preset recall -> count = {c_second}")
    print(f"  Preset accumulation {'WORKS' if c_second == g5_count + g6_count else 'REPLACES' if c_second == g6_count else f'UNEXPECTED ({c_second})'}")

    if c_second > c_first:
        await cmd_print(client, "Store Group 902 /o", "Store Group 902 /o (from preset accumulation)")
        await go_root(client)
        await client.send_command("cd 22", delay=0.5)
        await client.send_command("cd 902", delay=0.5)
        await cmd_print(client, "list", "cd 22 -> cd 902 -> list (preset accumulation fixture order)")
        await go_root(client)

    await client.send_command("ClearAll", delay=0.3)

    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST F: Overwrite Lump Group with Correct Order")
    print("=" * 70)

    # Show current Group 4 fixture order (patch order)
    await go_root(client)
    await client.send_command("cd 22", delay=0.5)
    await client.send_command("cd 4", delay=0.5)
    await cmd_print(client, "list", "BEFORE: cd 22 -> cd 4 -> list (current lump order)")
    await go_root(client)

    # Build correctly-ordered selection (try best available method)
    # Try /merge approach first (most explicit)
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 5", delay=0.5)
    await cmd(client, "Store Group 4 /o", delay=0.5)
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 6", delay=0.5)
    merge_result = await cmd(client, "Store Group 4 /merge", delay=0.5)

    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 4", delay=0.5)
    final_count = await get_selfix_count(client)
    print(f"\n  After overwrite: Group 4 count = {final_count} (expect {g4_count})")

    # Show new fixture order
    await go_root(client)
    await client.send_command("cd 22", delay=0.5)
    await client.send_command("cd 4", delay=0.5)
    await cmd_print(client, "list", "AFTER: cd 22 -> cd 4 -> list (corrected lump order)")
    await go_root(client)

    # =========================================================================
    print("\n" + "=" * 70)
    print("CLEANUP")
    print("=" * 70)

    for gnum in [900, 901, 902, 950, 951, 952, 953]:
        await cmd(client, f"Delete Group {gnum} /nc", delay=0.3)
    await cmd(client, "MAtricksReset", delay=0.3)
    await client.send_command("ClearAll", delay=0.3)
    print("  Cleaned up test groups and MAtricks state.")

    await client.disconnect()


asyncio.run(main())
