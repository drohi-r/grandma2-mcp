"""
Live telnet research: Discover Preset/Sequence/Cue/Executor hierarchy,
playback modes (LTP/HTP), priority, tracking, and chase behavior.

Step 3 of Phase 2 Console State Validation.
"""

import asyncio
import json
import re
import sys


def clean_ansi(text):
    """Strip ANSI escape sequences."""
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


async def research_hierarchy():
    from src.telnet_client import GMA2TelnetClient
    from src.prompt_parser import parse_prompt

    client = GMA2TelnetClient("127.0.0.1", 30000)
    await client.connect()
    await client.login()

    sections = {}

    # =========================================================================
    # 1. List PresetType (already known, re-confirm)
    # =========================================================================
    print("=" * 80)
    print("  1. LIST PRESETTYPE")
    print("=" * 80)
    resp = await client.send_command_with_response("List PresetType")
    clean = clean_ansi(resp)
    print(clean)
    sections["presettype_list"] = clean

    # =========================================================================
    # 2. List Preset pools (per preset type)
    # =========================================================================
    print("\n" + "=" * 80)
    print("  2. LIST PRESET (per PresetType)")
    print("=" * 80)
    preset_data = {}
    for pt in range(0, 10):
        resp = await client.send_command_with_response(f"List Preset {pt}.*")
        clean = clean_ansi(resp)
        # Count non-empty lines that look like preset entries
        lines = [l.strip() for l in clean.split("\n") if l.strip() and not l.strip().startswith("[")]
        has_presets = any("Preset" in l for l in lines)
        if has_presets:
            print(f"\n  PresetType {pt}:")
            for l in lines:
                if "Preset" in l or "Executing" in l:
                    print(f"    {l}")
            preset_data[f"pt_{pt}"] = clean
        else:
            print(f"  PresetType {pt}: (empty or no presets)")
    sections["presets"] = preset_data

    # =========================================================================
    # 3. List Sequences
    # =========================================================================
    print("\n" + "=" * 80)
    print("  3. LIST SEQUENCE")
    print("=" * 80)
    resp = await client.send_command_with_response("List Sequence")
    clean = clean_ansi(resp)
    print(clean)
    sections["sequence_list"] = clean

    # Parse sequence numbers for deeper inspection
    seq_nums = []
    for line in clean.split("\n"):
        m = re.match(r"\s*Sequence\s+(\d+)", line.strip())
        if m:
            seq_nums.append(int(m.group(1)))
    print(f"\n  Found {len(seq_nums)} sequences: {seq_nums}")

    # =========================================================================
    # 4. List Cues within each sequence
    # =========================================================================
    print("\n" + "=" * 80)
    print("  4. LIST CUE (per Sequence)")
    print("=" * 80)
    cue_data = {}
    for seq in seq_nums[:10]:  # Limit to first 10 sequences
        resp = await client.send_command_with_response(f"List Cue {seq}.*")
        clean = clean_ansi(resp)
        lines = [l.strip() for l in clean.split("\n") if l.strip() and not l.strip().startswith("[")]
        cue_count = sum(1 for l in lines if re.match(r"Cue\s+\d+", l.strip()))
        print(f"\n  Sequence {seq}: {cue_count} cues")
        for l in lines:
            if re.match(r"\s*Cue\s+", l.strip()) or "Executing" in l:
                print(f"    {l}")
        cue_data[f"seq_{seq}"] = clean
    sections["cues"] = cue_data

    # =========================================================================
    # 5. List Executors
    # =========================================================================
    print("\n" + "=" * 80)
    print("  5. LIST EXECUTOR")
    print("=" * 80)
    resp = await client.send_command_with_response("List Executor")
    clean = clean_ansi(resp)
    print(clean)
    sections["executor_list"] = clean

    # Also try page-specific executor listings
    for page in [1, 2]:
        resp = await client.send_command_with_response(f"List Executor {page}.*")
        clean = clean_ansi(resp)
        lines = [l.strip() for l in clean.split("\n") if l.strip()]
        exec_lines = [l for l in lines if "Exec" in l or "Executor" in l]
        if exec_lines:
            print(f"\n  Executor Page {page}:")
            for l in exec_lines[:20]:
                print(f"    {l}")
        sections[f"executor_page_{page}"] = clean

    # =========================================================================
    # 6. Info Executor (detailed properties)
    # =========================================================================
    print("\n" + "=" * 80)
    print("  6. INFO EXECUTOR (detail views)")
    print("=" * 80)
    # Try common executor positions
    exec_info = {}
    for exec_id in ["1.1", "1.2", "1.3", "1.201", "2.1"]:
        resp = await client.send_command_with_response(f"Info Executor {exec_id}")
        clean = clean_ansi(resp)
        lines = [l.strip() for l in clean.split("\n") if l.strip() and not l.strip().startswith("[")]
        has_info = any(l for l in lines if "=" in l or ":" in l or "Executor" in l)
        if has_info or "Error" not in resp:
            print(f"\n  Info Executor {exec_id}:")
            for l in lines:
                if l and not l.startswith("Executing"):
                    print(f"    {l}")
            exec_info[exec_id] = clean
    sections["executor_info"] = exec_info

    # =========================================================================
    # 7. Discover Executor modes/properties via CD navigation
    # =========================================================================
    print("\n" + "=" * 80)
    print("  7. EXECUTOR PROPERTIES (via cd navigation)")
    print("=" * 80)

    # Navigate to an executor and list its properties
    resp = await client.send_command_with_response("cd /")
    resp = await client.send_command_with_response("cd Executor 1")
    p = parse_prompt(resp)
    print(f"  cd Executor 1 -> {p.prompt_line}")

    resp = await client.send_command_with_response("List")
    clean = clean_ansi(resp)
    print(f"  List at Executor 1:")
    for line in clean.split("\n"):
        l = line.strip()
        if l and not l.startswith("[") and not l.startswith("Executing"):
            print(f"    {l}")
    sections["executor_tree"] = clean

    # Try to navigate into a specific executor
    resp = await client.send_command_with_response("cd 1")
    p = parse_prompt(resp)
    print(f"\n  cd 1 -> {p.prompt_line}")

    resp = await client.send_command_with_response("List")
    clean = clean_ansi(resp)
    print(f"  List inside Executor 1.1:")
    for line in clean.split("\n"):
        l = line.strip()
        if l and not l.startswith("[") and not l.startswith("Executing"):
            print(f"    {l}")
    sections["executor_1_1_tree"] = clean

    # Go back to root
    resp = await client.send_command_with_response("cd /")

    # =========================================================================
    # 8. Sequence properties (via cd navigation)
    # =========================================================================
    print("\n" + "=" * 80)
    print("  8. SEQUENCE PROPERTIES (via cd navigation)")
    print("=" * 80)

    if seq_nums:
        first_seq = seq_nums[0]
        resp = await client.send_command_with_response(f"cd Sequence {first_seq}")
        p = parse_prompt(resp)
        print(f"  cd Sequence {first_seq} -> {p.prompt_line}")

        resp = await client.send_command_with_response("List")
        clean = clean_ansi(resp)
        print(f"  List at Sequence {first_seq}:")
        for line in clean.split("\n"):
            l = line.strip()
            if l and not l.startswith("[") and not l.startswith("Executing"):
                print(f"    {l}")
        sections["sequence_tree"] = clean

        # Navigate into first cue
        resp = await client.send_command_with_response("cd 1")
        p = parse_prompt(resp)
        print(f"\n  cd 1 -> {p.prompt_line}")

        resp = await client.send_command_with_response("List")
        clean = clean_ansi(resp)
        print(f"  List inside Cue 1:")
        for line in clean.split("\n"):
            l = line.strip()
            if l and not l.startswith("[") and not l.startswith("Executing"):
                print(f"    {l}")
        sections["cue_tree"] = clean

        resp = await client.send_command_with_response("cd /")

    # =========================================================================
    # 9. Info Sequence (mode, tracking, etc.)
    # =========================================================================
    print("\n" + "=" * 80)
    print("  9. INFO SEQUENCE (properties)")
    print("=" * 80)
    if seq_nums:
        for seq in seq_nums[:5]:
            resp = await client.send_command_with_response(f"Info Sequence {seq}")
            clean = clean_ansi(resp)
            lines = [l.strip() for l in clean.split("\n") if l.strip() and not l.startswith("[")]
            print(f"\n  Info Sequence {seq}:")
            for l in lines:
                if l and not l.startswith("Executing"):
                    print(f"    {l}")
            sections[f"sequence_info_{seq}"] = clean

    # =========================================================================
    # 10. Store/Cue operations (read-only research: what modes exist?)
    # =========================================================================
    print("\n" + "=" * 80)
    print("  10. EXECUTOR MODE DISCOVERY")
    print("=" * 80)
    # Try Assign Executor with /mode= to discover available modes
    # This should error but reveal valid options
    resp = await client.send_command_with_response("Assign Executor 1.1 /mode=?")
    clean = clean_ansi(resp)
    print(f"  Assign Executor 1.1 /mode=?:")
    for line in clean.split("\n"):
        l = line.strip()
        if l:
            print(f"    {l}")
    sections["mode_discovery_1"] = clean

    # Try Info with /? to see available properties
    resp = await client.send_command_with_response("Info Executor 1.1 /?")
    clean = clean_ansi(resp)
    print(f"\n  Info Executor 1.1 /?:")
    for line in clean.split("\n"):
        l = line.strip()
        if l:
            print(f"    {l}")
    sections["mode_discovery_2"] = clean

    # =========================================================================
    # 11. Chase behavior (if any sequence is a chase)
    # =========================================================================
    print("\n" + "=" * 80)
    print("  11. CHASE / TRACKING DISCOVERY")
    print("=" * 80)
    # List sequence properties to find chase/tracking flags
    for seq in seq_nums[:5]:
        resp = await client.send_command_with_response(
            f"Info Sequence {seq} /tracking"
        )
        clean = clean_ansi(resp)
        print(f"  Info Sequence {seq} /tracking:")
        for line in clean.split("\n"):
            l = line.strip()
            if l and not l.startswith("Executing"):
                print(f"    {l}")

    # Reset to Channel
    await client.send_command_with_response("Channel")
    await client.disconnect()

    # Output JSON
    print("\n" + "=" * 80)
    print("FULL RESULTS JSON:")
    print("=" * 80)
    print(json.dumps(sections, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(research_hierarchy())
