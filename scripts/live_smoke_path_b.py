"""Live verification for Path B tasks against onPC.

Usage:
    .\\.venv\\Scripts\\python.exe -m scripts.live_smoke_path_b --task T6

Each --task argument runs the corresponding verification block:
    T6 — check_plugin_available against the live plugin pool
    T6-import-then-verify — destructive: import EcubeColorPicker then re-verify
    T4 — build_show_from_patch dry-run against Nemesis
    T8 — architect_preset_library dry-run against Nemesis
    T5 — build_layout_for_screen dry-run

No mutation unless explicitly --confirm passed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def task_t6(verify_only: bool, confirm: bool) -> int:
    failures: list[str] = []

    print("[T6.a] check_plugin_available('EcubeColorPicker') — pre-import state")
    from src.server import check_plugin_available
    raw = await check_plugin_available(
        "EcubeColorPicker", use_cache=False, cache_ttl_seconds=0,
    )
    data = json.loads(raw)
    pre_available = data["available"]
    print(f"       available={pre_available}, pool_id={data['pool_id']}, "
          f"match={data['match']}, source={data['source']}")

    if verify_only:
        if not pre_available:
            print("[T6] Plugin not loaded. Use --import to import it (requires --confirm).")
        return 0

    if pre_available:
        print(f"[T6] Plugin already present at pool_id={data['pool_id']}. "
              "Skipping import; re-running check to confirm.")
        return 0

    if not confirm:
        print("[T6] Import requested but --confirm not passed. Aborting.")
        print("     To import: --task T6 --import --confirm")
        return 1

    print("[T6.b] Importing EcubeColorPicker.xml into Nemesis plugin pool slot 2")
    from src.server import send_raw_command
    # MA2 syntax: Import "filename" object-list /path=...
    # (MA2's `Help Import` reports: `Import filename [Object-list]`.)
    import_cmd = (
        'Import "EcubeColorPicker" Plugin 2 '
        '/path=C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/plugins'
    )
    raw = await send_raw_command(import_cmd, confirm_destructive=True)
    print(f"       send_raw_command -> {raw[:300]}")

    await asyncio.sleep(0.5)

    print("[T6.c] check_plugin_available('EcubeColorPicker') — post-import state")
    raw = await check_plugin_available(
        "EcubeColorPicker", use_cache=False, cache_ttl_seconds=0,
    )
    data = json.loads(raw)
    print(f"       available={data['available']}, pool_id={data['pool_id']}, "
          f"match={data['match']}, source={data['source']}")
    if not data["available"]:
        failures.append("T6.c: plugin still not present after import")
    elif data["match"] != "exact":
        failures.append(f"T6.c: expected exact match; got {data['match']!r}")

    if failures:
        print(f"[T6] FAILED: {failures}")
        return 1
    print("[T6] OK — plugin imported and check_plugin_available reports it correctly.")
    return 0


async def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task", required=True,
        choices=["T6", "T4", "T5", "T8"],
    )
    parser.add_argument("--import", dest="do_import", action="store_true",
                        help="(T6 only) Import EcubeColorPicker.xml into the live show.")
    parser.add_argument("--confirm", action="store_true",
                        help="Required for destructive operations.")
    args = parser.parse_args(argv)

    if args.task == "T6":
        return await task_t6(verify_only=not args.do_import, confirm=args.confirm)
    if args.task == "T4":
        print("[T4] not implemented in this script revision")
        return 1
    if args.task == "T5":
        print("[T5] not implemented in this script revision")
        return 1
    if args.task == "T8":
        print("[T8] not implemented in this script revision")
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
