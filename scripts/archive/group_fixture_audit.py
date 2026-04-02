"""Group Fixture Count Audit: SelFix each group, read $SELECTEDFIXTURESCOUNT."""
import asyncio
import re
import sys
sys.path.insert(0, ".")
from src.telnet_client import GMA2TelnetClient


def clean(s):
    return re.sub(r"\x1b\[[0-9;]*m", "", s).replace("[K", "")


async def get_selfix_count(client, cmd, label):
    """Run a SelFix command, then read $SELECTEDFIXTURESCOUNT via ListVar."""
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command(cmd, delay=0.5)
    resp = await client.send_command_with_response(
        "ListVar $SELECTEDFIXTURESCOUNT", timeout=3.0, delay=0.5
    )
    c = clean(resp)
    count = "?"
    # MA2 expands $VAR before executing, so response is "Executing : ListVar N"
    for line in c.split("\n"):
        if "ListVar" in line:
            m = re.search(r"ListVar\s+(\d+)", line)
            if m:
                count = m.group(1)
                break
    print(f"  {label:<30} count = {count}")
    return count


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()

    # Get group labels first
    resp = await client.send_command_with_response("list group", timeout=5.0, delay=1.0)
    c = clean(resp)
    print("Current groups:")
    for line in c.split("\n"):
        s = line.strip()
        if s and "Group" in s and not any(skip in s for skip in ["Selection", "BlindSelection", "Executing"]):
            print(f"  {s}")
    print()

    print("=" * 60)
    print("FT GROUPS (slots 1-7) — created via Preset 0 recall")
    print("=" * 60)
    ft_counts = {}
    for i in range(1, 8):
        count = await get_selfix_count(client, f"SelFix Group {i}", f"Group {i} (FT {i})")
        ft_counts[i] = count

    print()
    print("=" * 60)
    print("POOL GROUPS (slots 11-17) — created via FixtureType N.1.1 Thru")
    print("=" * 60)
    pool_counts = {}
    for i in range(11, 18):
        ft_num = i - 10
        count = await get_selfix_count(client, f"SelFix Group {i}", f"Group {i} (pool for FT {ft_num})")
        pool_counts[i] = count

    print()
    print("=" * 60)
    print("DIRECT FixtureType N.1.1 Thru (cross-reference)")
    print("=" * 60)
    direct_counts = {}
    for i in range(1, 8):
        count = await get_selfix_count(client, f"FixtureType {i}.1.1 Thru", f"FixtureType {i}.1.1 Thru")
        direct_counts[i] = count

    print()
    print("=" * 60)
    print("SUMMARY — Groups with >1 fixture")
    print("=" * 60)
    print(f"  {'FT':<4} {'FT Grp':<8} {'Pool Grp':<10} {'FT Direct':<10} {'Match?'}")
    print(f"  {'-'*4} {'-'*8} {'-'*10} {'-'*10} {'-'*6}")
    for i in range(1, 8):
        ft_c = ft_counts.get(i, "?")
        pool_c = pool_counts.get(i + 10, "?")
        direct_c = direct_counts.get(i, "?")
        match = "YES" if ft_c == pool_c == direct_c else "NO"
        marker = " ***" if ft_c not in ("0", "1", "?") else ""
        print(f"  {i:<4} {ft_c:<8} {pool_c:<10} {direct_c:<10} {match}{marker}")

    await client.send_command("ClearAll", delay=0.3)
    await client.disconnect()


asyncio.run(main())
