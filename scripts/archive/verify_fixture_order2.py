"""Export groups 5, 900 and compare fixture order via XML."""
import asyncio
import re
import sys
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


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # Export Group 5
    for f in ["audit_group5.xml", "audit_group900.xml"]:
        p = IMPORTEXPORT / f
        if p.exists():
            p.unlink()

    await cmd(client, 'Export Group 5 "audit_group5"', delay=2.0)
    await asyncio.sleep(1.0)

    # Build merged group 900 (instance 1 first, then instance 2)
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 5", delay=0.5)
    await cmd(client, "Store Group 900 /o", delay=0.5)
    await client.send_command("ClearAll", delay=0.3)
    await client.send_command("SelFix Group 6", delay=0.5)
    await cmd(client, "Store Group 900 /merge", delay=0.5)
    await client.send_command("ClearAll", delay=0.3)

    await cmd(client, 'Export Group 900 "audit_group900"', delay=2.0)
    await asyncio.sleep(1.0)

    # Cleanup
    await cmd(client, "Delete Group 900 /nc", delay=0.5)
    await client.disconnect()
    print("Done. Check XML files.")


asyncio.run(main())
