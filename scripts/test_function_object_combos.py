"""
Live telnet test: Validate Function Keyword + Object Keyword combinations.

Systematically sends every function keyword with common object types to the
grandMA2 console and records which combinations are accepted vs rejected.

This produces a definitive keyword-object compatibility matrix.

Usage:
    python scripts/test_function_object_combos.py
    python scripts/test_function_object_combos.py --output results.json
    python scripts/test_function_object_combos.py --functions "Release,Flash,Solo"
"""

import asyncio
import json
import sys
import time

# Function keywords to test (the ones most likely to have object variants)
FUNCTION_KEYWORDS = [
    # Playback control — currently executor-only, need to verify
    "Release",
    "Flash",
    "Solo",
    "On",
    "Off",
    "Temp",
    "Top",
    "Freeze",
    "Pause",
    # Playback execution — known multi-object
    "Go+",          # Go+ is the telnet form of Go
    "GoBack",
    "Goto",
    # Selection & programmer
    "Select",
    "SelFix",
    "Highlight",
    "Blind",
    # Store/create
    "Store",
    "Delete",
    "Copy",
    "Move",
    "Label",
    "Call",
    # Info/list
    "Info",
    "List",
    # Other
    "Park",
    "Unpark",
    "Assign",
    "Edit",
    "Remove",
    "Appearance",
    "Update",
    "Oops",
    "SaveShow",
    "DeleteShow",
]

# Object keywords to combine with each function
# Using ID 99 to avoid touching real show data
OBJECT_KEYWORDS = [
    "Executor 201",
    "Sequence 99",
    "Cue 99",
    "Fixture 99",
    "Channel 99",
    "Group 99",
    "Preset 1.99",
    "Macro 99",
    "Effect 99",
    "Page 1",
    "Layout 99",
    "World 99",
    "Filter 99",
    "Timecode 99",
    "Timer 99",
    "View 99",
]

# Some functions don't take objects — test them bare
BARE_FUNCTIONS = [
    "Oops",
    "Blackout",
    "Highlight",
    "Blind",
    "SaveShow",
    "Freeze",
]


async def test_combo(client, function_kw, object_kw):
    """Test a single function+object combination.

    Returns dict with: command, accepted (bool), error_code, raw_snippet.
    """
    cmd = f"{function_kw} {object_kw}"

    try:
        resp = await client.send_command_with_response(cmd, timeout=2.0, delay=0.5)
    except Exception as e:
        return {
            "command": cmd,
            "accepted": None,
            "error_code": None,
            "raw_snippet": f"EXCEPTION: {e}",
        }

    # Detect errors
    has_error = False
    error_code = None
    if "Error" in resp:
        has_error = True
        # Extract error number if present: "Error #1: UNKNOWN COMMAND"
        for line in resp.split("\n"):
            if "Error #" in line:
                try:
                    error_code = line.split("Error #")[1].split(":")[0].strip()
                except (IndexError, ValueError):
                    error_code = "unknown"

    # Check for confirmation popups (store/delete trigger these)
    has_confirm = "Confirm" in resp or "Please Confirm" in resp
    # Check for "Illegal" which means bad syntax
    has_illegal = "Illegal" in resp

    return {
        "command": cmd,
        "accepted": not has_error and not has_illegal,
        "has_confirm": has_confirm,
        "error_code": error_code,
        "raw_snippet": resp[:200].replace("\n", " | ").replace("\r", "").strip(),
    }


async def test_bare(client, function_kw):
    """Test a bare function keyword (no object)."""
    try:
        resp = await client.send_command_with_response(function_kw, timeout=2.0, delay=0.5)
    except Exception as e:
        return {
            "command": function_kw,
            "accepted": None,
            "error_code": None,
            "raw_snippet": f"EXCEPTION: {e}",
        }

    has_error = "Error" in resp
    has_illegal = "Illegal" in resp
    error_code = None
    if has_error:
        for line in resp.split("\n"):
            if "Error #" in line:
                try:
                    error_code = line.split("Error #")[1].split(":")[0].strip()
                except (IndexError, ValueError):
                    error_code = "unknown"

    return {
        "command": function_kw,
        "accepted": not has_error and not has_illegal,
        "error_code": error_code,
        "raw_snippet": resp[:200].replace("\n", " | ").replace("\r", "").strip(),
    }


async def main():
    from src.telnet_client import GMA2TelnetClient

    # Parse CLI args
    output_file = None
    filter_functions = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        elif args[i] == "--functions" and i + 1 < len(args):
            filter_functions = [f.strip() for f in args[i + 1].split(",")]
            i += 2
        else:
            i += 1

    functions = filter_functions or FUNCTION_KEYWORDS

    print("=" * 90)
    print("  grandMA2 Function Keyword + Object Keyword Combination Test")
    print(f"  Testing {len(functions)} functions x {len(OBJECT_KEYWORDS)} objects")
    print("=" * 90)

    client = GMA2TelnetClient("127.0.0.1", 30000)
    await client.connect()
    await client.login()
    print("Connected and logged in.\n")

    all_results = {}
    total_combos = 0
    total_accepted = 0
    total_rejected = 0

    for func in functions:
        print(f"\n--- {func} ---")
        func_results = []

        # Test bare form first
        if func in BARE_FUNCTIONS:
            # Undo any side effects from bare commands
            bare = await test_bare(client, func)
            status = "OK" if bare["accepted"] else f"ERR({bare['error_code']})"
            print(f"  {func:40s} | {status:10s} | {bare['raw_snippet'][:60]}")
            func_results.append(bare)
            total_combos += 1
            if bare["accepted"]:
                total_accepted += 1
            else:
                total_rejected += 1

            # Undo oops/blind side effects
            if func == "Oops":
                await client.send_command_with_response("Oops", delay=0.3)
            elif func == "Blind":
                await client.send_command_with_response("Blind", delay=0.3)
            elif func == "Blackout":
                await client.send_command_with_response("Blackout", delay=0.3)

            # Small delay between combos
            await asyncio.sleep(0.3)

        # Test with each object
        for obj in OBJECT_KEYWORDS:
            result = await test_combo(client, func, obj)
            status = "OK" if result["accepted"] else f"ERR({result['error_code']})"
            confirm = " [CONFIRM]" if result.get("has_confirm") else ""
            print(f"  {result['command']:40s} | {status:10s}{confirm} | {result['raw_snippet'][:50]}")
            func_results.append(result)
            total_combos += 1
            if result["accepted"]:
                total_accepted += 1
            else:
                total_rejected += 1

            # Undo any destructive side effects
            # If store/delete was accepted and triggered a confirm, cancel it
            if result.get("has_confirm"):
                await client.send_command_with_response("", delay=0.3)  # dismiss popup

            # Pacing to avoid freezing onPC
            await asyncio.sleep(0.3)

        all_results[func] = func_results

    # Summary
    print("\n" + "=" * 90)
    print("  SUMMARY")
    print("=" * 90)
    print(f"  Total combinations tested: {total_combos}")
    print(f"  Accepted: {total_accepted}")
    print(f"  Rejected: {total_rejected}")

    # Print compatibility matrix
    print("\n  COMPATIBILITY MATRIX (accepted combos):")
    print(f"  {'Function':<15s}", end="")
    short_objs = [o.split()[0] for o in OBJECT_KEYWORDS]
    for o in short_objs:
        print(f" {o[:6]:>6s}", end="")
    print()
    print("  " + "-" * (15 + 7 * len(short_objs)))

    for func in functions:
        results = all_results.get(func, [])
        print(f"  {func:<15s}", end="")
        for obj_full in OBJECT_KEYWORDS:
            # Find matching result
            cmd = f"{func} {obj_full}"
            match = next((r for r in results if r["command"] == cmd), None)
            if match and match["accepted"]:
                print("     Y", end="")
            elif match and not match["accepted"]:
                print("     .", end="")
            else:
                print("     ?", end="")
        print()

    # Save results
    if output_file:
        with open(output_file, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\n  Results saved to {output_file}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
