"""Capture the live patch summary from onPC → write to tests/fixtures/.

One-off: run with the Nemesis show loaded; commits the JSON for
deterministic plan tests against the real production patch.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


async def main() -> int:
    from src.show_strategies.patch_reader import summarize_patch
    from src.telnet_client import GMA2TelnetClient

    host = os.getenv("GMA_HOST", "127.0.0.1")
    port = int(os.getenv("GMA_PORT", "30000"))
    user = os.getenv("GMA_USER", "administrator")
    pw = os.getenv("GMA_PASSWORD", "admin")

    async with GMA2TelnetClient(host=host, port=port, user=user, password=pw) as c:
        summary = await summarize_patch(c)

    out = Path("tests/fixtures/nemesis_patch_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"  showfile={summary['showfile']}")
    print(f"  fixtures={summary['fixture_count']}")
    print(f"  fixture_types={len(summary['fixture_types'])}")
    print(f"  groups={len(summary['groups'])}")
    print(f"  sequences~={summary['sequences_count']}")
    print(f"  macros~={summary['macros_count']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
