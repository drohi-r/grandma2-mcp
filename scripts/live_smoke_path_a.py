"""Live smoke test for Path A tools against the currently-active onPC.

Runs:
1. Tier-1 ListVar round-trip via the real Telnet client (sanity check)
2. discover_consoles (UDP broadcast probe, 2s timeout)
3. reconfigure_connection to the CURRENT host (idempotent — should report "no change")
4. suggest_skills_for_task (pure, but exercises the tool wrapper)
5. generate_ma2_macro (pure, but exercises the tool wrapper)

No console state mutation. Safe to re-run.
Exit 0 if every step's success criterion is met; 1 otherwise.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def main() -> int:
    failures: list[str] = []

    # 1. Direct Telnet sanity check
    print("[smoke] 1. Telnet round-trip (ListVar)")
    from src.telnet_client import GMA2TelnetClient
    host = os.getenv("GMA_HOST", "127.0.0.1")
    port = int(os.getenv("GMA_PORT", "30000"))
    user = os.getenv("GMA_USER", "administrator")
    pw = os.getenv("GMA_PASSWORD", "admin")
    try:
        async with GMA2TelnetClient(host=host, port=port, user=user, password=pw) as c:
            resp = await c.send_command_with_response("ListVar", timeout=2.0)
        if not resp or "VERSION" not in resp:
            failures.append("1: ListVar response missing $VERSION marker")
        else:
            print(f"   OK — got {len(resp)} chars; '$VERSION' present")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"1: {type(exc).__name__}: {exc}")

    # 2. discover_consoles via MCP tool wrapper
    print("[smoke] 2. discover_consoles (broadcast, 2s)")
    from src.server import discover_consoles
    try:
        raw = await discover_consoles(timeout_seconds=2)
        data = json.loads(raw)
        elapsed = data.get("elapsed_ms", 0)
        candidates = data.get("candidates", [])
        print(f"   OK — elapsed {elapsed:.1f}ms, {len(candidates)} candidate(s)")
        for c in candidates[:3]:
            print(f"     {c.get('host')}:{c.get('port')} session={c.get('session_name')} version={c.get('version')}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"2: {type(exc).__name__}: {exc}")

    # 3. reconfigure_connection — idempotent no-op
    print("[smoke] 3. reconfigure_connection to current host (idempotent)")
    from src.server import reconfigure_connection
    try:
        raw = await reconfigure_connection(
            host=host, port=port, user=user, password=pw,
            persist=False, verify=False,
        )
        data = json.loads(raw)
        if not data.get("success"):
            failures.append(f"3: success=False, error={data.get('error')}")
        elif data.get("note", "").lower() != "no change":
            failures.append(f"3: expected 'no change' note, got {data.get('note')!r}")
        else:
            print(f"   OK — success={data.get('success')}, note={data.get('note')}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"3: {type(exc).__name__}: {exc}")

    # 4. suggest_skills_for_task — pure, tool wrapper
    print("[smoke] 4. suggest_skills_for_task('make me a color picker', top_k=3)")
    from src.server import suggest_skills_for_task
    try:
        raw = await suggest_skills_for_task(
            intent="make me a color picker", top_k=3, prefer_semantic=False,
        )
        data = json.loads(raw)
        sugs = data.get("suggestions", [])
        if not sugs:
            failures.append("4: no suggestions returned for color-picker intent")
        else:
            print(f"   OK — method={data.get('method')}, top: {sugs[0].get('name')!r} (score={sugs[0].get('score')})")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"4: {type(exc).__name__}: {exc}")

    # 5. generate_ma2_macro — pure, tool wrapper, no store
    print("[smoke] 5. generate_ma2_macro('panic blackout')")
    from src.server import generate_ma2_macro
    try:
        raw = await generate_ma2_macro(
            intent="make a panic blackout macro", store=False,
        )
        data = json.loads(raw)
        if data.get("blocked"):
            failures.append(f"5: macro generation unexpectedly blocked: {data.get('expert_review')}")
        elif "BlackScreen" not in data.get("body_xml", ""):
            failures.append("5: panic-blackout body missing BlackScreen")
        else:
            print(f"   OK — grade={data['expert_review']['grade']}, lines={data.get('line_count')}, lint={len(data.get('lint', []))} finding(s)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"5: {type(exc).__name__}: {exc}")

    print()
    if failures:
        print(f"[smoke] FAILED ({len(failures)}):")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("[smoke] all 5 checks OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
