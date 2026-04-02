"""Debug v5 macro execution — capture all output and errors."""
import asyncio
import re
import time
import sys
sys.path.insert(0, ".")
from src.telnet_client import GMA2TelnetClient


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


async def main():
    client = GMA2TelnetClient(host="127.0.0.1", port=30000)
    await client.connect()
    await client.login()
    await go_root(client)

    # Clean pools first
    for cmd in [
        "delete group 1 thru 999 /nc",
        "delete world 2 thru 999 /nc",
        "delete preset 0.1 thru 0.999 /nc",
        "ClearAll",
    ]:
        await client.send_command_with_response(cmd, timeout=5.0, delay=2.0)
        await flush(client)
    print("Pools cleaned.\n")

    # Check if macro 5 exists
    await go_root(client)
    resp = await client.send_command_with_response("list macro 5", timeout=5.0, delay=1.0)
    c = clean(resp)
    print(f"list macro 5 response:\n{c}\n")

    if "Auto Create Multi-Pools v5" not in c:
        print("Macro 5 not found — importing...")
        resp = await client.send_command_with_response(
            'import "auto_create_multi_pools_v5" at macro 5 /nc',
            timeout=5.0, delay=2.0,
        )
        print(f"Import response:\n{clean(resp)}\n")
        await flush(client)

        # Verify import
        resp = await client.send_command_with_response("list macro 5", timeout=5.0, delay=1.0)
        print(f"After import, list macro 5:\n{clean(resp)}\n")

    # Run macro
    await flush(client)
    print(f"Go Macro 5 — {time.strftime('%H:%M:%S')}")
    client._writer.write("Go Macro 5\r\n")

    all_output = []
    start = time.time()
    while time.time() - start < 90:
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

    # Print ALL output lines (not just trace)
    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    print(f"\n=== ALL OUTPUT ({len(lines)} lines) ===")
    for i, l in enumerate(lines):
        print(f"  {i:3d}: {l}")

    # Highlight errors
    errors = [l for l in lines if "Error" in l or "error" in l.lower() or "UNKNOWN" in l]
    if errors:
        print(f"\n=== ERRORS ({len(errors)}) ===")
        for e in errors:
            print(f"  {e}")

    await asyncio.sleep(1.0)
    await client.disconnect()


asyncio.run(main())
