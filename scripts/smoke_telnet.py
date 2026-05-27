"""Live Telnet smoke test — connect, login, send a SAFE_READ command.

Reads .env, opens a session, runs ListVar, prints the first few lines.
Exit 0 on success, 1 on any failure.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from src.telnet_client import GMA2TelnetClient  # noqa: E402


async def main() -> int:
    host = os.getenv("GMA_HOST", "127.0.0.1")
    port = int(os.getenv("GMA_PORT", "30000"))
    user = os.getenv("GMA_USER", "administrator")
    pw = os.getenv("GMA_PASSWORD", "admin")
    print(f"[smoke] connecting to {host}:{port} as {user}")
    try:
        async with GMA2TelnetClient(host=host, port=port, user=user, password=pw) as c:
            resp = await c.send_command_with_response("ListVar", timeout=2.0)
            print(f"[smoke] ListVar response: {len(resp)} chars")
            for line in resp.splitlines()[:8]:
                print("  ", line.rstrip())
            print("[smoke] OK")
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[smoke] FAILED: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
