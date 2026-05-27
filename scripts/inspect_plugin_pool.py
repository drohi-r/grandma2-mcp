"""Inspect the live plugin pool — debug Import command result."""

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
        print("=== list plugin (raw) ===")
        resp = await c.send_command_with_response("list plugin", timeout=3.0)
        print(repr(resp[:2000]))
        print()
        print("=== plain lines ===")
        for ln in resp.splitlines():
            print(f"  {ln.rstrip()}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
