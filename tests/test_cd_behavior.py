"""
test_cd_behavior.py -- Live telnet probe of CD navigation behavior.

Connects to the MA2 console and runs a structured series of cd/list
commands to answer these questions:

1. What prompt does "cd /" produce? (root location string)
2. What does "list" at root return? (valid root indexes)
3. Does "cd .." from a root child return to root?
4. Does "cd .." from a depth-2 child return to its parent?
5. What happens when "cd .." is used at root? (stays at root?)
6. Do circular references exist? (cd N lands at same location as ancestor)
7. What does a "miss" look like? (cd N to nonexistent index)

Output: JSON report with raw telnet feedback for every step.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass, field

from dotenv import get_key

from src.prompt_parser import _strip_ansi, parse_list_output, parse_prompt
from src.telnet_client import GMA2TelnetClient


@dataclass
class Step:
    """One command→response record."""
    label: str
    command: str
    raw_response: str = ""
    stripped_response: str = ""
    parsed_location: str | None = None
    parsed_object_type: str | None = None
    parsed_object_id: str | None = None
    list_entry_count: int = 0
    list_entries: list[dict] = field(default_factory=list)
    notes: str = ""


async def send_and_parse(
    client: GMA2TelnetClient,
    command: str,
    label: str,
    *,
    timeout: float = 2.0,
    delay: float = 0.3,
) -> Step:
    """Send a command and parse the prompt from the response."""
    raw = await client.send_command_with_response(command, timeout=timeout, delay=delay)
    stripped = _strip_ansi(raw)
    parsed = parse_prompt(raw)

    step = Step(
        label=label,
        command=command,
        raw_response=raw,
        stripped_response=stripped,
        parsed_location=parsed.location,
        parsed_object_type=parsed.object_type,
        parsed_object_id=parsed.object_id,
    )
    return step


async def send_list(
    client: GMA2TelnetClient,
    label: str,
    *,
    timeout: float = 3.0,
    delay: float = 0.5,
) -> Step:
    """Send 'list' and parse both the entries and the trailing prompt."""
    raw = await client.send_command_with_response("list", timeout=timeout, delay=delay)
    stripped = _strip_ansi(raw)
    parsed_list = parse_list_output(raw)
    parsed_prompt = parse_prompt(raw)

    entries = [
        {
            "object_type": e.object_type,
            "object_id": e.object_id,
            "name": e.name,
            "raw_line": e.raw_line,
        }
        for e in parsed_list.entries
    ]

    step = Step(
        label=label,
        command="list",
        raw_response=raw,
        stripped_response=stripped,
        parsed_location=parsed_prompt.location,
        parsed_object_type=parsed_prompt.object_type,
        parsed_object_id=parsed_prompt.object_id,
        list_entry_count=len(entries),
        list_entries=entries,
    )
    return step


async def run_tests(client: GMA2TelnetClient) -> list[Step]:
    steps: list[Step] = []

    def log(step: Step):
        steps.append(step)
        loc = step.parsed_location or "(null)"
        entries = f" [{step.list_entry_count} entries]" if step.command == "list" else ""
        print(f"  {step.label}: {step.command} -> location={loc!r}{entries}")

    # ================================================================
    # TEST 1: What is root?
    # ================================================================
    print("\n=== TEST 1: Root location ===")

    s = await send_and_parse(client, "cd /", "T1.1 cd /")
    log(s)
    root_location = s.parsed_location

    # list at root
    s = await send_list(client, "T1.2 list at root")
    log(s)
    root_entry_count = s.list_entry_count

    # ================================================================
    # TEST 2: cd .. at root (should stay at root)
    # ================================================================
    print("\n=== TEST 2: cd .. at root ===")

    s = await send_and_parse(client, "cd ..", "T2.1 cd .. at root")
    s.notes = f"Expected to stay at root ({root_location!r})"
    log(s)

    # ================================================================
    # TEST 3: cd into first few root children and back
    # ================================================================
    print("\n=== TEST 3: cd N from root, list, cd .. back ===")

    # Pick first 5 valid root indexes from the list
    test_indexes = list(range(1, 9))  # indexes 1-8

    for idx in test_indexes:
        # cd / first (clean slate)
        s = await send_and_parse(client, "cd /", f"T3.{idx}a cd / (reset)")
        log(s)

        # cd N
        s = await send_and_parse(client, f"cd {idx}", f"T3.{idx}b cd {idx}")
        child_location = s.parsed_location
        log(s)

        if child_location is None or child_location == root_location:
            s.notes = "MISS - did not move from root"
            continue

        # list at this child
        s = await send_list(client, f"T3.{idx}c list at cd {idx}")
        log(s)

        # cd .. back
        s = await send_and_parse(client, "cd ..", f"T3.{idx}d cd .. (back from cd {idx})")
        back_location = s.parsed_location
        if back_location == root_location:
            s.notes = "OK - cd .. returned to root"
        else:
            s.notes = f"PROBLEM - cd .. went to {back_location!r}, expected root {root_location!r}"
        log(s)

    # ================================================================
    # TEST 4: Two-level deep: cd / -> cd N -> cd M -> cd .. -> verify -> cd .. -> verify
    # ================================================================
    print("\n=== TEST 4: Two-level deep cd .. behavior ===")

    # Use index 8 (UserImagePool) which has children, and index 16 (Gels)
    deep_tests = [8, 16]

    for parent_idx in deep_tests:
        # cd / reset
        s = await send_and_parse(client, "cd /", f"T4.{parent_idx}a cd / (reset)")
        log(s)

        # cd into parent
        s = await send_and_parse(client, f"cd {parent_idx}", f"T4.{parent_idx}b cd {parent_idx}")
        parent_location = s.parsed_location
        log(s)

        if parent_location is None or parent_location == root_location:
            print(f"  Skipping {parent_idx} - could not navigate")
            continue

        # list to find children
        s = await send_list(client, f"T4.{parent_idx}c list at {parent_location}")
        log(s)
        child_count = s.list_entry_count

        if child_count == 0:
            print(f"  No children at {parent_location}, skipping deep test")
            continue

        # cd 1 into first child
        s = await send_and_parse(client, "cd 1", f"T4.{parent_idx}d cd 1 (into child)")
        child_location = s.parsed_location
        log(s)

        if child_location is None or child_location == parent_location:
            s.notes = "MISS - child cd 1 did not move"
            continue

        # list at child level
        s = await send_list(client, f"T4.{parent_idx}e list at child")
        log(s)

        # cd .. should go back to parent
        s = await send_and_parse(client, "cd ..", f"T4.{parent_idx}f cd .. (child -> parent)")
        back_location = s.parsed_location
        if back_location == parent_location:
            s.notes = f"OK - cd .. returned to parent {parent_location!r}"
        elif back_location == root_location:
            s.notes = f"ESCAPED - cd .. went to root {root_location!r} instead of parent {parent_location!r}"
        else:
            s.notes = f"WRONG - cd .. went to {back_location!r}, expected {parent_location!r}"
        log(s)

        # cd .. again should go to root
        s = await send_and_parse(client, "cd ..", f"T4.{parent_idx}g cd .. (parent -> root)")
        back2_location = s.parsed_location
        if back2_location == root_location:
            s.notes = f"OK - cd .. returned to root {root_location!r}"
        else:
            s.notes = f"PROBLEM - cd .. went to {back2_location!r}, expected root {root_location!r}"
        log(s)

    # ================================================================
    # TEST 5: Miss detection - cd to nonexistent index
    # ================================================================
    print("\n=== TEST 5: Miss detection (nonexistent index) ===")

    s = await send_and_parse(client, "cd /", "T5.1 cd / (reset)")
    log(s)

    # Try a very high index that shouldn't exist
    s = await send_and_parse(client, "cd 99", "T5.2 cd 99 (should miss)")
    if s.parsed_location == root_location:
        s.notes = "CONFIRMED MISS - stayed at root"
    elif s.parsed_location is None:
        s.notes = "NULL LOCATION - could not parse (ambiguous miss)"
    else:
        s.notes = f"UNEXPECTED - moved to {s.parsed_location!r}"
    log(s)

    # ================================================================
    # TEST 6: Circular reference probe
    # cd / -> cd 8 -> cd 15 -> check if location matches an ancestor
    # ================================================================
    print("\n=== TEST 6: Circular reference probe (path 8.15.15) ===")

    s = await send_and_parse(client, "cd /", "T6.1 cd / (reset)")
    log(s)

    s = await send_and_parse(client, "cd 8", "T6.2 cd 8 (UserImagePool)")
    loc_8 = s.parsed_location
    log(s)

    s = await send_and_parse(client, "cd 15", "T6.3 cd 15 from UserImagePool")
    loc_8_15 = s.parsed_location
    log(s)

    if loc_8_15 == loc_8:
        s.notes = f"CIRCULAR at depth 2 - same as parent {loc_8!r}"
    elif loc_8_15 == root_location:
        s.notes = "ESCAPED to root at depth 2"

    s = await send_and_parse(client, "cd 15", "T6.4 cd 15 again (depth 3)")
    loc_8_15_15 = s.parsed_location
    log(s)

    if loc_8_15_15 == loc_8:
        s.notes = f"CIRCULAR at depth 3 - matches ancestor {loc_8!r}"
    elif loc_8_15_15 == loc_8_15:
        s.notes = f"STUCK - same as previous level {loc_8_15!r}"
    elif loc_8_15_15 == root_location:
        s.notes = "ESCAPED to root at depth 3"

    # list to see what's here
    s = await send_list(client, "T6.5 list at depth 3")
    log(s)

    # ================================================================
    # TEST 7: cd / recovery after deep navigation
    # ================================================================
    print("\n=== TEST 7: cd / recovery after deep navigation ===")

    s = await send_and_parse(client, "cd /", "T7.1 cd / (recovery from deep)")
    if s.parsed_location == root_location:
        s.notes = "OK - cd / successfully returned to root after deep nav"
    else:
        s.notes = f"PROBLEM - cd / returned {s.parsed_location!r}, expected {root_location!r}"
    log(s)

    # Verify with list
    s = await send_list(client, "T7.2 list at root (verify recovery)")
    if s.list_entry_count == root_entry_count:
        s.notes = f"OK - same entry count as initial root list ({root_entry_count})"
    else:
        s.notes = f"MISMATCH - got {s.list_entry_count} entries, expected {root_entry_count}"
    log(s)

    # ================================================================
    # TEST 8: Empty line (just press enter) to get current prompt
    # ================================================================
    print("\n=== TEST 8: Empty command to query current location ===")

    s = await send_and_parse(client, "cd /", "T8.1 cd / (reset)")
    log(s)

    s = await send_and_parse(client, "", "T8.2 empty command at root")
    s.notes = f"Empty command returned location={s.parsed_location!r}"
    log(s)

    s = await send_and_parse(client, "cd 8", "T8.3 cd 8")
    log(s)

    s = await send_and_parse(client, "", "T8.4 empty command at UserImagePool")
    s.notes = f"Empty command returned location={s.parsed_location!r}"
    log(s)

    return steps


async def main():
    host = get_key(".env", "GMA_HOST") or "127.0.0.1"
    user = get_key(".env", "GMA_USER") or "administrator"
    password = get_key(".env", "GMA_PASSWORD") or "admin"
    port = 30000

    print(f"Connecting to {host}:{port} as {user}...")

    client = GMA2TelnetClient(host=host, port=port, user=user, password=password)

    try:
        await client.connect()
        await client.login()
        print("Connected and logged in.\n")

        t_start = time.monotonic()
        steps = await run_tests(client)
        elapsed = time.monotonic() - t_start

    finally:
        await client.disconnect()
        print("\nDisconnected.")

    # Write JSON report
    output = {
        "test_meta": {
            "host": host,
            "port": port,
            "elapsed_seconds": round(elapsed, 2),
            "step_count": len(steps),
        },
        "steps": [asdict(s) for s in steps],
    }

    out_path = "test_cd_behavior_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n=== DONE === ({elapsed:.1f}s, {len(steps)} steps)")
    print(f"Output: {out_path}")

    # Print summary of PROBLEM/ESCAPED/CIRCULAR notes
    print("\n=== FINDINGS ===")
    for s in steps:
        if s.notes and any(kw in s.notes for kw in ("PROBLEM", "ESCAPED", "CIRCULAR", "WRONG", "MISMATCH", "NULL")):
            print(f"  ** {s.label}: {s.notes}")


if __name__ == "__main__":
    asyncio.run(main())
