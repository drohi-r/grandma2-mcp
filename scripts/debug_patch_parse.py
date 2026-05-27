"""Debug the patch_reader regex against live data."""

from __future__ import annotations

import asyncio
import os
import re

from dotenv import load_dotenv

load_dotenv()


async def main() -> int:
    from src.show_strategies.patch_reader import (
        _FIXTURE_ROW_RE,
        _FT_ROW_RE,
        _GROUP_ROW_RE,
        _strip_ansi,
    )
    from src.telnet_client import GMA2TelnetClient

    pw = os.getenv("GMA_PASSWORD", "admin")
    async with GMA2TelnetClient(
        host="127.0.0.1", user="administrator", password=pw,
    ) as c:
        resp = await c.send_command_with_response("list fixture", timeout=3.0)
        stripped = _strip_ansi(resp)
        # MA2 uses \n\r line breaks; normalise to \n for regex MULTILINE.
        normalised = stripped.replace("\n\r", "\n").replace("\r\n", "\n")
        print("=== first 1500 chars of normalised stripped response ===")
        print(repr(normalised[:1500]))
        print()
        print("=== fixture regex matches (normalised) ===")
        matches = list(_FIXTURE_ROW_RE.finditer(normalised))
        print(f"count: {len(matches)}")
        for m in matches[:3]:
            print(f"  id={m.group('id')!r} name={m.group('name')!r} type={m.group('type')!r} patch={m.group('patch')!r}")

        print()
        print("=== first non-header row ===")
        lines = [ln for ln in normalised.splitlines() if ln.strip() and "Fixture" in ln and "Name" not in ln and "Executing" not in ln]
        for ln in lines[:2]:
            print(repr(ln))

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
