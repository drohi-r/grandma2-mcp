"""
Live telnet test: Send Object Keywords and capture prompt changes.
Discovers which keywords change the [default]> prompt context.

Phase 1: 22 vocabulary Object Keywords (completed — 20 change context, CuePart errors)
Phase 2: Extended keywords — Appearance (missed from vocab), FixtureType, SubFixture,
         MAtricks, and other tree-level object types not in the v3.9 vocabulary.
"""

import asyncio
import json
import sys

# Original 22 vocabulary Object Keywords (lines 82-104 of vocabulary JSON)
OBJECT_KEYWORDS = [
    "Channel", "Fixture", "Group", "Preset", "PresetType",
    "Cue", "CuePart", "Sequence", "Executor", "Macro",
    "Effect", "Layout", "Page", "Attribute", "Feature",
    "DMX", "DMXUniverse", "Timecode", "TimecodeSlot", "Timer",
    "World", "Messages",
]

# Extended keywords: vocabulary keyword missed + tree object types from scan_output.json
EXTENDED_KEYWORDS = [
    # Vocabulary Object Keyword missed from original test
    "Appearance",
    # Tree object types (navigable via cd, NOT in vocabulary)
    "FixtureType",
    "SubFixture",
    "MAtricks",
    # Pool/container types from scan
    "Filter",
    "Mask",
    "Form",
    "Gel",
    # Other console constructs
    "Selection",
    "Programmer",
    "BlindEdit",
]

# Round 3: More tree object types and known console terms
EXTENDED_KEYWORDS_R3 = [
    # Discovered pool/data types from scan_output.json
    "Camera",
    "Matrix",
    "View",
    "Image",
    "Sound",
    # Possible undocumented keywords
    "SpecialMaster",
    "Agenda",
    "RDM",
    "Stage",
    "DMXProfile",
    "AllPreset",
]

# OFFICIAL: All 48 Object Keywords from MA2 help page:
# https://help.malighting.com/grandMA2/en/help/key_cs_object_keywords.html
OFFICIAL_OBJECT_KEYWORDS = [
    "Agenda",
    "Attribute",
    "ButtonPage",
    "Camera",
    "Channel",
    "ChannelFader",
    "Cue",
    "Default",
    "Dmx",
    "Effect",
    "ExecButton1",
    "ExecButton2",
    "ExecButton3",
    "Executor",
    "Fader",
    "FaderPage",
    "Feature",
    "Filter",
    "Fixture",
    "FixtureType",
    "Form",
    "Full",
    "Group",
    "Layout",
    "Macro",
    "Mask",
    "MAtricks",
    "Normal",
    "Page",
    "Part",
    "Preset",
    "PresetType",
    "PreviewExecutor",
    "Remote",
    "Root",
    "Screen",
    "Selection",
    "Sequence",
    "SpecialMaster",
    "Timecode",
    "Timer",
    "User",
    "UserProfile",
    "View",
    "ViewButton",
    "ViewPage",
    "World",
    "Zero",
]

# Keywords in our vocabulary but NOT in official list (to verify separately)
VOCAB_ONLY_KEYWORDS = [
    "Appearance",       # In vocab, not in official Object Keywords list
    "CuePart",          # In vocab, not in official list (Part is official instead)
    "DMXUniverse",      # In vocab, official uses "Dmx" only
    "Messages",         # In vocab, not in official list
    "TimecodeSlot",     # In vocab, not in official list
]

# Extra keywords discovered via telnet that work but aren't in either list
DISCOVERED_KEYWORDS = [
    "Gel",
    "Image",
    "Programmer",
    "RDM",              # Maps to RdmFixtureType
    "Sound",            # Maps to SoundChannel
    "BlindEdit",        # Toggle, doesn't change context
    "SubFixture",       # Error #1: UNKNOWN COMMAND
]


async def test_keyword_list(client, parse_prompt, keywords, label):
    """Test a list of keywords and return results."""
    results = []

    print(f"\n{'='*90}")
    print(f"  {label} ({len(keywords)} keywords)")
    print(f"{'='*90}")

    for kw in keywords:
        # Reset to Channel first
        reset_resp = await client.send_command_with_response("Channel")
        rp = parse_prompt(reset_resp)

        # Send the keyword
        resp = await client.send_command_with_response(kw)
        ap = parse_prompt(resp)

        # Detect errors in raw response
        has_error = "Error" in resp or "UNKNOWN" in resp

        changed = None
        if rp.location and ap.location:
            changed = ap.location != rp.location

        result = {
            "keyword": kw,
            "before_prompt": rp.prompt_line,
            "before_location": rp.location,
            "after_prompt": ap.prompt_line,
            "after_location": ap.location,
            "after_type": ap.object_type,
            "after_id": ap.object_id,
            "changed": changed,
            "has_error": has_error,
            "raw_snippet": resp[:300].replace("\n", " | ").strip(),
        }
        results.append(result)

        if has_error:
            status = "ERROR"
        elif changed:
            status = "CHANGED"
        elif changed is False:
            status = "SAME"
        else:
            status = "UNKNOWN"
        print(f"  {kw:20s} | {str(rp.prompt_line):25s} -> {str(ap.prompt_line):35s} | {status}")

    return results


async def test_keywords():
    from src.telnet_client import GMA2TelnetClient
    from src.prompt_parser import parse_prompt

    client = GMA2TelnetClient("127.0.0.1", 30000)
    await client.connect()
    await client.login()

    # Get baseline prompt
    baseline = await client.send_command_with_response("")
    bp = parse_prompt(baseline)
    print(f"BASELINE: prompt_line={bp.prompt_line!r}, location={bp.location!r}")

    # Determine which set to test from CLI args
    test_set = sys.argv[1] if len(sys.argv) > 1 else "all"

    all_results = []

    if test_set in ("original", "all"):
        results = await test_keyword_list(
            client, parse_prompt, OBJECT_KEYWORDS, "ORIGINAL VOCABULARY OBJECT KEYWORDS"
        )
        all_results.extend(results)

    if test_set in ("extended", "all"):
        results = await test_keyword_list(
            client, parse_prompt, EXTENDED_KEYWORDS, "EXTENDED / TREE OBJECT KEYWORDS"
        )
        all_results.extend(results)

    if test_set in ("round3", "all"):
        results = await test_keyword_list(
            client, parse_prompt, EXTENDED_KEYWORDS_R3, "ROUND 3 / ADDITIONAL TREE OBJECTS"
        )
        all_results.extend(results)

    if test_set in ("official", "all"):
        results = await test_keyword_list(
            client, parse_prompt, OFFICIAL_OBJECT_KEYWORDS, "OFFICIAL MA2 OBJECT KEYWORDS (48)"
        )
        all_results.extend(results)

    if test_set in ("vocab_only",):
        results = await test_keyword_list(
            client, parse_prompt, VOCAB_ONLY_KEYWORDS, "VOCABULARY-ONLY KEYWORDS (not in official)"
        )
        all_results.extend(results)

    if test_set in ("discovered",):
        results = await test_keyword_list(
            client, parse_prompt, DISCOVERED_KEYWORDS, "DISCOVERED KEYWORDS (from telnet testing)"
        )
        all_results.extend(results)

    # Reset back to Channel
    await client.send_command_with_response("Channel")
    await client.disconnect()

    # Summary
    print(f"\n{'='*90}")
    print("SUMMARY:")
    changers = [r for r in all_results if r["changed"] is True]
    same = [r for r in all_results if r["changed"] is False]
    errors = [r for r in all_results if r.get("has_error")]
    unknown = [r for r in all_results if r["changed"] is None and not r.get("has_error")]

    print(f"  Changed default: {len(changers)} keywords")
    for r in changers:
        print(f"    {r['keyword']:20s} -> {r['after_prompt']}")
    print(f"  Same (no change): {len(same)} keywords")
    for r in same:
        print(f"    {r['keyword']:20s} (stayed at {r['before_prompt']})")
    if errors:
        print(f"  Errors: {len(errors)} keywords")
        for r in errors:
            print(f"    {r['keyword']:20s} (error in response)")
    if unknown:
        print(f"  Unknown: {len(unknown)} keywords")
        for r in unknown:
            print(f"    {r['keyword']:20s} (prompt={r['after_prompt']})")

    # Output full JSON
    print()
    print("FULL RESULTS:")
    print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    asyncio.run(test_keywords())
