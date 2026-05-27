"""Probe onPC for current patch + plugin state — informs Path B scope.

Reports:
- Showfile name
- Number of patched fixtures (and a sample)
- Number of fixture types
- Number of groups
- Plugin pool contents (looking for auto-layout-color-picker)

No mutations. Exit 0 always.
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


async def main() -> int:
    from src.telnet_client import GMA2TelnetClient
    host = os.getenv("GMA_HOST", "127.0.0.1")
    port = int(os.getenv("GMA_PORT", "30000"))
    user = os.getenv("GMA_USER", "administrator")
    pw = os.getenv("GMA_PASSWORD", "admin")

    async with GMA2TelnetClient(host=host, port=port, user=user, password=pw) as c:
        print("=== Show ===")
        resp = await c.send_command_with_response("ListVar", timeout=2.0)
        for line in resp.splitlines():
            if "$SHOWFILE" in line or "$VERSION" in line or "$USER " in line:
                print(f"  {line.strip()}")

        print("\n=== Fixtures (list fixture) ===")
        resp = await c.send_command_with_response("list fixture", timeout=3.0)
        lines = [ln for ln in resp.splitlines() if ln.strip()]
        # MA2 list output is tabular; count data rows after the header
        data_rows = [ln for ln in lines if not ln.startswith("Executing") and ":" in ln]
        print(f"  total lines: {len(lines)} (~{len(data_rows)} fixture rows)")
        for ln in lines[:8]:
            print(f"    {ln.rstrip()}")
        if len(lines) > 8:
            print(f"    ... ({len(lines) - 8} more)")

        print("\n=== Fixture types (list fixturetype) ===")
        resp = await c.send_command_with_response("list fixturetype", timeout=2.0)
        lines = [ln for ln in resp.splitlines() if ln.strip()]
        print(f"  total lines: {len(lines)}")
        for ln in lines[:6]:
            print(f"    {ln.rstrip()}")
        if len(lines) > 6:
            print(f"    ... ({len(lines) - 6} more)")

        print("\n=== Groups (list group) ===")
        resp = await c.send_command_with_response("list group", timeout=2.0)
        lines = [ln for ln in resp.splitlines() if ln.strip()]
        print(f"  total lines: {len(lines)}")
        for ln in lines[:6]:
            print(f"    {ln.rstrip()}")

        print("\n=== Plugin pool (list plugin) ===")
        resp = await c.send_command_with_response("list plugin", timeout=3.0)
        lines = [ln for ln in resp.splitlines() if ln.strip()]
        print(f"  total lines: {len(lines)}")
        for ln in lines[:15]:
            print(f"    {ln.rstrip()}")
        if "color" in resp.lower():
            print("  -> contains 'color' — color picker plugin may be present")

        print("\n=== Macros (list macro) ===")
        resp = await c.send_command_with_response("list macro", timeout=2.0)
        lines = [ln for ln in resp.splitlines() if ln.strip()]
        print(f"  total lines: {len(lines)}")

        print("\n=== Sequences (list sequence) ===")
        resp = await c.send_command_with_response("list sequence", timeout=2.0)
        lines = [ln for ln in resp.splitlines() if ln.strip()]
        print(f"  total lines: {len(lines)}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
