"""Identify the 2 fixtures in Group 14 and check FT 4 sub-types."""
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


async def cmd(client, command, label, delay=1.0):
    resp = await client.send_command_with_response(command, timeout=5.0, delay=delay)
    c = clean(resp)
    print(f"\n--- {label} ---")
    for line in c.split("\n"):
        s = line.strip()
        if s and not any(skip in s for skip in NOISE):
            print(f"  {s}")
    return c


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()

    # Confirm Group 14 count
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 14", delay=0.5)
    resp = await client.send_command_with_response(
        "ListVar $SELECTEDFIXTURESCOUNT", timeout=3.0, delay=0.5
    )
    c = clean(resp)
    for line in c.split("\n"):
        if "ListVar" in line:
            m = re.search(r"ListVar\s+(\d+)", line)
            if m:
                print(f"Group 14 $SELECTEDFIXTURESCOUNT = {m.group(1)}")

    # Info on Group 14
    await cmd(client, "info group 14", "info group 14")

    # List fixtures in Group 14 via cd tree
    for nav_cmd in ["cd /", "cd 22", "cd 1"]:
        await client.send_command(nav_cmd, delay=0.3)
    await cmd(client, "cd 14", "cd into group 14 slot")
    await cmd(client, "list", "list inside group 14")
    await client.send_command("cd /", delay=0.3)

    # Check FT 4 sub-types
    await cmd(client, "FixtureType 4.1.1 Thru", "FixtureType 4.1.1 Thru — select")

    # Navigate to FT 4 in fixture type tree to see sub-types
    for nav_cmd in ["cd /", "cd 10", "cd 3"]:
        await client.send_command(nav_cmd, delay=0.3)
    await cmd(client, "cd 4", "cd into FixtureType 4 (in LiveSetup)")
    await cmd(client, "list", "list FT 4 sub-types")
    await client.send_command("cd /", delay=0.3)

    # Also try individual sub-types
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("FixtureType 4.1.1", delay=0.5)
    resp = await client.send_command_with_response(
        "ListVar $SELECTEDFIXTURESCOUNT", timeout=3.0, delay=0.5
    )
    c = clean(resp)
    for line in c.split("\n"):
        if "ListVar" in line:
            m = re.search(r"ListVar\s+(\d+)", line)
            if m:
                print(f"\nFixtureType 4.1.1 (no Thru) count = {m.group(1)}")

    await client.send_command("ClearAll", delay=0.3)
    await client.disconnect()


asyncio.run(main())
