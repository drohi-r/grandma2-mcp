"""Verify MAtricksBlocks N + Store /merge captures full block of subs.

Tests the core assumption for v7 macro optimization:
  MAtricksBlocks $subsPerPhys makes each Next select an entire block,
  so one Store /merge captures all subs for that physical fixture.
"""
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


async def export_group(client, group_num, label):
    """Export a group, parse XML, print fixture order, return fixtures."""
    fname = f"verify_blocks_g{group_num}"
    fpath = IMPORTEXPORT / f"{fname}.xml"
    if fpath.exists():
        fpath.unlink()
    await cmd(client, f'Export Group {group_num} "{fname}"', delay=2.0)
    await asyncio.sleep(0.5)
    if fpath.exists():
        fixtures = export_fixture_order(fpath)
        parts = [f"{fid}.{sid}" for fid, sid in fixtures]
        print(f"  [{label}] {len(fixtures)} subfixtures: {', '.join(parts)}")
        fpath.unlink()
        return fixtures
    print(f"  [{label}] Export failed - file not found")
    return []


def check_grouped(fixtures):
    """Return True if all subs of each fix_id are contiguous."""
    if len(fixtures) <= 1:
        return True
    seen = []
    current = None
    for fid, _ in fixtures:
        if fid != current:
            if fid in seen:
                return False
            seen.append(fid)
            current = fid
    return True


async def get_selfix_count(client, selfix_cmd):
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command(selfix_cmd, delay=0.5)
    resp = await cmd(client, "ListVar $SELECTEDFIXTURESCOUNT", delay=0.5)
    for line in resp.split("\n"):
        if "ListVar" in line:
            m = re.search(r"ListVar\s+(\d+)", line)
            if m:
                return int(m.group(1))
    return 0


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # Use FT group 6 (inst2 of FT4, 24 subfixtures: 401.2-7, 402.2-7, 403.2-7, 404.2-7)
    # and FT group 5 (inst1 of FT4, 4 fixtures: 401.1, 402.1, 403.1, 404.1)
    # First verify they exist
    inst1_count = await get_selfix_count(client, "SelFix Group 5")
    inst2_count = await get_selfix_count(client, "SelFix Group 6")
    print(f"FT Group 5 (inst1): {inst1_count} fixtures")
    print(f"FT Group 6 (inst2): {inst2_count} fixtures")

    if inst1_count == 0 or inst2_count == 0:
        print("ERROR: FT groups 5/6 not populated. Run v6 macro first.")
        await client.disconnect()
        return

    subs_per_phys = inst2_count // inst1_count
    print(f"subsPerPhys = {inst2_count} / {inst1_count} = {subs_per_phys}")

    # Clean temp groups
    for g in range(950, 960):
        await cmd(client, f"delete group {g} /nc", delay=0.5)
    await flush(client)

    # ========== TEST 1: Blocks N, first Next ==========
    print(f"\n{'='*60}")
    print("TEST 1: MAtricksBlocks {subs_per_phys}, first Next -> Store 950")
    print(f"{'='*60}")
    await cmd(client, "ClearAll", delay=0.3)
    await cmd(client, "SelFix Group 6", delay=0.5)
    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, f"MAtricksBlocks {subs_per_phys}", delay=0.3)
    await cmd(client, "Next", delay=0.3)
    await cmd(client, "Store Group 950 /o", delay=0.5)
    fx1 = await export_group(client, 950, "Test1: Blocks N, 1st Next")
    expect1 = subs_per_phys
    status1 = "PASS" if len(fx1) == expect1 else f"FAIL (expected {expect1})"
    print(f"  -> {status1}")

    # ========== TEST 2: Blocks N, second Next ==========
    print(f"\n{'='*60}")
    print(f"TEST 2: MAtricksBlocks {subs_per_phys}, Next twice -> Store 951")
    print(f"{'='*60}")
    await cmd(client, "ClearAll", delay=0.3)
    await cmd(client, "SelFix Group 6", delay=0.5)
    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, f"MAtricksBlocks {subs_per_phys}", delay=0.3)
    await cmd(client, "Next", delay=0.3)
    await cmd(client, "Next", delay=0.3)
    await cmd(client, "Store Group 951 /o", delay=0.5)
    fx2 = await export_group(client, 951, "Test2: Blocks N, 2nd Next")
    status2 = "PASS" if len(fx2) == expect1 else f"FAIL (expected {expect1})"
    print(f"  -> {status2}")

    # Check they are DIFFERENT fixtures
    if fx1 and fx2:
        fids1 = set(f[0] for f in fx1)
        fids2 = set(f[0] for f in fx2)
        print(f"  Test1 fix_ids: {fids1}, Test2 fix_ids: {fids2}")
        if fids1 != fids2:
            print(f"  -> PASS: different physical fixtures")
        else:
            print(f"  -> FAIL: same fix_ids in both blocks")

    # ========== TEST 3: /merge with block selection ==========
    print(f"\n{'='*60}")
    print("TEST 3: Store /o (block 1) then /merge (block 2) -> 952")
    print(f"{'='*60}")
    # Block 1: inst1 fixture 1
    await cmd(client, "ClearAll", delay=0.3)
    await cmd(client, "SelFix Group 5", delay=0.5)
    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, "MAtricksBlocks 1", delay=0.3)
    await cmd(client, "Next", delay=0.3)
    await cmd(client, "Store Group 952 /o", delay=0.5)
    # Block 2: inst2 block 1 (6 subs)
    await cmd(client, "ClearAll", delay=0.3)
    await cmd(client, "SelFix Group 6", delay=0.5)
    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, f"MAtricksBlocks {subs_per_phys}", delay=0.3)
    await cmd(client, "Next", delay=0.3)
    await cmd(client, "Store Group 952 /merge", delay=0.5)
    fx3 = await export_group(client, 952, "Test3: inst1.1 + inst2 block 1")
    expected3 = 1 + subs_per_phys  # 1 inst1 + N inst2 subs
    status3 = "PASS" if len(fx3) == expected3 else f"FAIL (expected {expected3})"
    print(f"  -> {status3}")

    # ========== TEST 4: Variable expansion ==========
    print(f"\n{'='*60}")
    print("TEST 4: SetUserVar + MAtricksBlocks $testBlock -> Store 953")
    print(f"{'='*60}")
    await cmd(client, f"SetUserVar $testBlock = {subs_per_phys}", delay=0.3)
    await cmd(client, "ClearAll", delay=0.3)
    await cmd(client, "SelFix Group 6", delay=0.5)
    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, "MAtricksBlocks $testBlock", delay=0.3)
    await cmd(client, "Next", delay=0.3)
    await cmd(client, "Store Group 953 /o", delay=0.5)
    fx4 = await export_group(client, 953, "Test4: variable expansion")
    status4 = "PASS" if len(fx4) == expect1 else f"FAIL (expected {expect1})"
    print(f"  -> {status4}")

    # ========== TEST 5: Full v7 simulation ==========
    print(f"\n{'='*60}")
    print(f"TEST 5: Full v7 merge simulation ({inst1_count} iterations)")
    print(f"{'='*60}")
    for phys_loop in range(inst1_count):
        # Inst1: select single fixture via Blocks 1 + Next
        await cmd(client, "ClearAll", delay=0.3)
        await cmd(client, "SelFix Group 5", delay=0.5)
        await cmd(client, "MAtricksReset", delay=0.3)
        await cmd(client, "MAtricksBlocks 1", delay=0.3)
        for _ in range(phys_loop + 1):
            await cmd(client, "Next", delay=0.2)
        if phys_loop == 0:
            await cmd(client, "Store Group 955 /o", delay=0.5)
        else:
            await cmd(client, "Store Group 955 /merge", delay=0.5)

        # Inst2: select block via Blocks N + Next
        await cmd(client, "ClearAll", delay=0.3)
        await cmd(client, "SelFix Group 6", delay=0.5)
        await cmd(client, "MAtricksReset", delay=0.3)
        await cmd(client, f"MAtricksBlocks {subs_per_phys}", delay=0.3)
        for _ in range(phys_loop + 1):
            await cmd(client, "Next", delay=0.2)
        await cmd(client, "Store Group 955 /merge", delay=0.5)

        count = await get_selfix_count(client, "SelFix Group 955")
        expected_so_far = (phys_loop + 1) * (1 + subs_per_phys)
        print(f"  physLoop={phys_loop}: count={count}, expected={expected_so_far}", end="")
        print(f" {'PASS' if count == expected_so_far else 'FAIL'}")

    fx5 = await export_group(client, 955, "Test5: full v7 simulation")
    total_expected = inst1_count * (1 + subs_per_phys)
    grouped = check_grouped(fx5)
    print(f"  Total: {len(fx5)}, expected: {total_expected}, grouped: {grouped}")
    status5 = "PASS" if len(fx5) == total_expected and grouped else "FAIL"
    print(f"  -> {status5}")

    # ========== CLEANUP ==========
    print(f"\n{'='*60}")
    print("CLEANUP")
    print(f"{'='*60}")
    for g in range(950, 960):
        await cmd(client, f"delete group {g} /nc", delay=0.3)
    await cmd(client, "MAtricksReset", delay=0.3)
    await cmd(client, "ClearAll", delay=0.3)
    print("  Done.")

    # ========== SUMMARY ==========
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Test 1 (Blocks N, 1st Next):      {status1}")
    print(f"  Test 2 (Blocks N, 2nd Next):       {status2}")
    print(f"  Test 3 (/merge with block):        {status3}")
    print(f"  Test 4 (Variable expansion):       {status4}")
    print(f"  Test 5 (Full v7 simulation):       {status5}")

    all_pass = all("PASS" in s for s in [status1, status2, status3, status4, status5])
    print(f"\n  {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")

    await client.disconnect()


asyncio.run(main())
