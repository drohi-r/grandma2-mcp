"""
scripts/probe_list_fields.py -- Discover List output fields for all major MA2 object types.

Connects directly to the console and runs targeted List commands for each object type,
capturing every KEY=VALUE field in the response. Results saved to:
  doc/list_fields_discovery.json   -- raw + parsed fields
  doc/list-fields-reference.md     -- human-readable table

Usage:
    PYTHONPATH=. python scripts/probe_list_fields.py
"""

import asyncio
import json
import re
import sys
from pathlib import Path

CONSOLE_HOST = "127.0.0.1"
CONSOLE_PORT = 30000

OUTPUT_JSON = Path("doc/list_fields_discovery.json")
OUTPUT_MD   = Path("doc/list-fields-reference.md")


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text or "")


def extract_fields(raw: str) -> dict[str, str]:
    """Extract KEY=VALUE pairs from a List response line."""
    clean = strip_ansi(raw).replace("\r", " ").replace("\n", " ")
    fields: dict[str, str] = {}
    # Match KEY=Value where value runs until next KEY= or end
    for m in re.finditer(r"([A-Za-z][A-Za-z0-9_]*)=([^\s=]+(?:\s+[^\s=]+)*?)(?=\s+[A-Za-z][A-Za-z0-9_]*=|$)", clean):
        fields[m.group(1)] = m.group(2).strip()
    return fields


# ---------------------------------------------------------------------------
# All commands to probe, organised by object type
# Each entry: (type_label, command, note)
# ---------------------------------------------------------------------------
PROBE_PLAN: list[tuple[str, str, str]] = [

    # --- Sequence ---
    ("Sequence", "List Sequence 201",    "Color Palette Profiles (8 cues)"),
    ("Sequence", "List Sequence 202",    "Color Palette Washes (8 cues)"),

    # --- Cue ---
    ("Cue",      "List Cue Sequence 201",   "All cues in sequence 201"),
    ("Cue",      "List Cue 1 Sequence 201", "Cue 1 of sequence 201"),
    ("Cue",      "List Cue 8 Sequence 201", "Cue 8 of sequence 201"),

    # --- Group ---
    ("Group",    "List Group 1",   "First group"),
    ("Group",    "List Group 13",  "Viper Profiles group"),
    ("Group",    "List Group 15",  "Washes group"),

    # --- Preset ---
    ("Preset",   "List Preset 1.1", "Dimmer - Full"),
    ("Preset",   "List Preset 2.1", "Position - Home"),
    ("Preset",   "List Preset 3.1", "Gobo - Open"),
    ("Preset",   "List Preset 4.1", "Color - White"),
    ("Preset",   "List Preset 4.5", "Color - Amber"),

    # --- Fixture (single IDs only - never bare) ---
    ("Fixture",  "List Fixture 111",  "Mac 700 Profile #1"),
    ("Fixture",  "List Fixture 120",  "Mac Viper Profile #1"),
    ("Fixture",  "List Fixture 201",  "Mac Quantum Wash #1"),

    # --- Channel (single IDs only) ---
    ("Channel",  "List Channel 111",  "Channel for fixture 111"),
    ("Channel",  "List Channel 201",  "Channel for fixture 201"),

    # --- Macro (probe bare first) ---
    ("Macro",    "List Macro",      "All macros (probe)"),
    ("Macro",    "List Macro 1",    "Macro 1"),

    # --- Filter (168 imported, pick a populated slot) ---
    ("Filter",   "List Filter 3",   "Filter slot 3"),
    ("Filter",   "List Filter 10",  "Filter slot 10"),
    ("Filter",   "List Filter 50",  "Filter slot 50"),

    # --- Effect ---
    ("Effect",   "List Effect",     "All effects (probe)"),
    ("Effect",   "List Effect 1",   "Effect 1"),

    # --- Layout ---
    ("Layout",   "List Layout",     "All layouts (probe)"),
    ("Layout",   "List Layout 1",   "Layout 1"),

    # --- View ---
    ("View",     "List View",       "All views (probe)"),
    ("View",     "List View 1",     "View 1"),

    # --- Timecode ---
    ("Timecode", "List Timecode",   "All timecodes (probe)"),
    ("Timecode", "List Timecode 1", "Timecode 1"),

    # --- Timer ---
    ("Timer",    "List Timer",      "All timers (probe)"),
    ("Timer",    "List Timer 1",    "Timer 1"),

    # --- World ---
    ("World",    "List World 1",    "World 1"),

    # --- MAtricks ---
    ("MAtricks", "List MAtricks 1", "MAtricks slot 1"),
    ("MAtricks", "List MAtricks 2", "MAtricks slot 2"),

    # --- Page ---
    ("Page",     "List Page 1",     "Page 1"),
    ("Page",     "List Page 2",     "Page 2 (Sat Bands)"),
    ("Page",     "List Page 3",     "Page 3 (Hue Faders)"),

    # --- Plugin (may not exist) ---
    ("Plugin",   "List Plugin",     "All plugins (probe)"),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run_probes() -> dict:
    from src.telnet_client import GMA2TelnetClient

    client = GMA2TelnetClient(CONSOLE_HOST, CONSOLE_PORT)
    await client.connect()
    await client.login()
    print(f"Connected to {CONSOLE_HOST}:{CONSOLE_PORT}\n")

    results: dict[str, list[dict]] = {}

    for obj_type, cmd, note in PROBE_PLAN:
        print(f"  >>> [{obj_type}] {cmd}")
        try:
            raw = await client.send_command_with_response(cmd)
        except Exception as e:
            raw = f"ERROR: {e}"

        raw_clean = strip_ansi(raw).strip()
        fields = extract_fields(raw_clean)

        # Classify response
        if "NO OBJECTS FOUND" in raw_clean or "WARNING" in raw_clean:
            status = "empty"
        elif "UNKNOWN COMMAND" in raw_clean or "Error" in raw_clean:
            status = "error"
        elif fields:
            status = "ok"
        else:
            status = "no_fields"  # had text but no KEY=VALUE pairs (e.g. table header)

        entry = {
            "command": cmd,
            "note": note,
            "status": status,
            "fields": fields,
            "raw_truncated": raw_clean[:500],
        }

        results.setdefault(obj_type, []).append(entry)
        print(f"       [{status}] fields={list(fields.keys())[:8]}")
        await asyncio.sleep(0.6)

    await client.disconnect()
    return results


# ---------------------------------------------------------------------------
# Output: JSON
# ---------------------------------------------------------------------------

def save_json(results: dict) -> None:
    OUTPUT_JSON.parent.mkdir(exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved JSON -> {OUTPUT_JSON}")


# ---------------------------------------------------------------------------
# Output: Markdown reference table
# ---------------------------------------------------------------------------

MD_HEADER = """\
---
title: grandMA2 List Command Field Reference
description: All KEY=VALUE fields returned by List <ObjectType> for each major MA2 object type — live-verified from console
version: 1.0.0
created: 2026-03-31T00:00:00Z
last_updated: 2026-03-31T00:00:00Z
---

# grandMA2 List Command Field Reference

All fields below are live-verified from `List <Type> <ID>` telnet responses on show `claude_ma2_ctrl`.

"""

def build_markdown(results: dict) -> str:
    lines = [MD_HEADER]

    for obj_type, entries in results.items():
        lines.append(f"## {obj_type}\n")

        # Collect all unique fields across all entries of this type
        all_fields: dict[str, str] = {}
        example_cmd = ""
        for entry in entries:
            if entry["status"] == "ok":
                all_fields.update(entry["fields"])
                if not example_cmd:
                    example_cmd = entry["command"]

        if not all_fields:
            # Check if any entry had content
            for entry in entries:
                if entry["status"] in ("empty", "error", "no_fields"):
                    lines.append(f"*Pool empty or not present on this show.*\n\n")
                    break
            else:
                lines.append(f"*No data captured.*\n\n")
            continue

        lines.append(f"Example: `{example_cmd}`\n")
        lines.append("")
        lines.append("| Field | Example Value |")
        lines.append("|-------|--------------|")
        for k, v in sorted(all_fields.items()):
            lines.append(f"| `{k}` | `{v}` |")
        lines.append("")

        # Per-entry raw samples
        lines.append("<details><summary>Raw samples</summary>\n")
        for entry in entries:
            if entry["status"] == "ok":
                raw_snippet = entry["raw_truncated"].replace("\n", " ").replace("\r", "")[:200]
                lines.append(f"```\n{entry['command']}\n{raw_snippet}\n```\n")
        lines.append("</details>\n\n")

    return "\n".join(lines)


def save_markdown(results: dict) -> None:
    md = build_markdown(results)
    OUTPUT_MD.parent.mkdir(exist_ok=True)
    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"Saved MD   -> {OUTPUT_MD}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("grandMA2 List Field Discovery")
    print(f"Console: {CONSOLE_HOST}:{CONSOLE_PORT}")
    print(f"Commands to run: {len(PROBE_PLAN)}\n")

    results = await run_probes()

    save_json(results)
    save_markdown(results)

    # Summary
    print("\n=== SUMMARY ===")
    for obj_type, entries in results.items():
        ok_entries = [e for e in entries if e["status"] == "ok"]
        all_fields: set[str] = set()
        for e in ok_entries:
            all_fields.update(e["fields"].keys())
        status_summary = ", ".join(f"{e['status']}" for e in entries)
        print(f"  {obj_type:<12} {len(all_fields):2d} fields  [{status_summary}]")
        if all_fields:
            print(f"               {sorted(all_fields)}")


if __name__ == "__main__":
    asyncio.run(main())
