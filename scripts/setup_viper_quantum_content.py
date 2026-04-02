"""
Create presets and color sequences for Mac Viper Profiles (120-125)
and Mac Quantum Washes (201-220) -- matching the Mac 700 content set.

Phases:
  0  Discovery: attribute names + existing preset state
  1  Dimmer presets  (1.1-1.5): Full / 75pct / Half / 25pct / Off  -- all fixtures
  2  Position presets(2.1-2.5): Home / FOH-Center / Stage-Left / Stage-Right / TopLight
                               -- all movers (111-125 + 201-220)
  3  Gobo presets   (3.1-3.5): Open / Gobo1-4 -- profile spots (111-125) only
  4  Color presets  (4.1-4.8): 8 colors       -- all fixtures (SelFix 1 Thru 9999)
  5  Color sequence for Profiles (111-125): 8 cues -> executor
  6  Color sequence for Washes   (201-220): 8 cues -> executor
  7  Assign sequences to executors + label + appearance
  8  Verify

Usage:
    PYTHONPATH=. python scripts/setup_viper_quantum_content.py
"""

import asyncio
import re

# ---------------------------------------------------------------------------
# Show-specific fixture ranges
# ---------------------------------------------------------------------------

# All movers (Mac 700 + Viper Profiles + Quantum Washes)
ALL_MOVERS = "SelFix Fixture 111 Thru 125 + Fixture 201 Thru 220"
# Profile spots only (Mac 700 + Viper)
PROFILE_SPOTS = "SelFix Fixture 111 Thru 125"
# Wash fixtures only
WASH_ONLY = "SelFix Fixture 201 Thru 220"
# Universal (every patched fixture)
ALL_FIXTURES = "SelFix Fixture 1 Thru 9999"

# ---------------------------------------------------------------------------
# Preset data
# ---------------------------------------------------------------------------

DIMMER_PRESETS: list[tuple[int, str, int]] = [
    (1, "Full",  100),
    (2, "75pct",  75),
    (3, "Half",   50),
    (4, "25pct",  25),
    (5, "Off",     0),
]

POSITION_PRESETS: list[tuple[int, str, int, int]] = [
    (1, "Home",         50, 50),
    (2, "FOH-Center",   50, 35),
    (3, "Stage-Left",   25, 35),
    (4, "Stage-Right",  75, 35),
    (5, "TopLight",     50,  0),
]

GOBO_PRESETS: list[tuple[int, str, int]] = [
    (1, "Open",  0),
    (2, "Gobo1", 1),
    (3, "Gobo2", 2),
    (4, "Gobo3", 3),
    (5, "Gobo4", 4),
]

COLOR_PRESETS: list[tuple[int, str, int, int, int]] = [
    (1, "White",    100, 100, 100),
    (2, "Red",      100,   0,   0),
    (3, "Green",      0, 100,   0),
    (4, "Blue",       0,   0, 100),
    (5, "Amber",    100,  55,   0),
    (6, "Cyan",       0, 100, 100),
    (7, "Magenta",  100,   0, 100),
    (8, "Yellow",   100, 100,   0),
]

# Expected standard MA2 attribute names (warns if absent from discovery)
EXPECTED_ATTRS = {"Pan", "Tilt", "ColorRgb1", "ColorRgb2", "ColorRgb3", "Gobo1"}

# ---------------------------------------------------------------------------
# Sequence / executor IDs (resolved at runtime)
# ---------------------------------------------------------------------------

PROFILE_SEQ_ID: int = 201   # updated in main if occupied
WASH_SEQ_ID: int = 202

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _find_free_seq_id(response: str, candidates: list[int]) -> int:
    """Return first candidate not found in a List Sequence response."""
    clean = _strip_ansi(response)
    for cid in candidates:
        if str(cid) not in clean:
            return cid
    return candidates[-1]


def _warn_missing_attrs(discovery_resp: str, fixture_label: str) -> None:
    """Print WARNING for any expected attribute not mentioned in the Info response."""
    clean = _strip_ansi(discovery_resp).lower()
    for attr in EXPECTED_ATTRS:
        if attr.lower() not in clean:
            print(f"  [!] WARNING: '{attr}' not found in {fixture_label} attribute list.")
            print(f"      Check Phase 0 output and update attribute name if needed.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def setup_content() -> None:
    from src.telnet_client import GMA2TelnetClient

    client = GMA2TelnetClient("127.0.0.1", 30000)
    await client.connect()
    await client.login()

    sep = "=" * 70

    async def run(label: str, commands: list[str]) -> list[str]:
        print(f"\n{sep}")
        print(f"  {label}")
        print(f"{sep}")
        responses = []
        for cmd in commands:
            print(f"  >>> {cmd}")
            resp = await client.send_command_with_response(cmd)
            resp_clean = (_strip_ansi(resp or "")).strip()
            if resp_clean:
                print(f"  {resp_clean[:500]}")
            responses.append(resp_clean)
        return responses

    # ── Phase 0: Discovery ──────────────────────────────────────────────────
    r0a = await run("Phase 0a: Viper Profile 16-bit (type 4) attribute info", [
        "cd /",
        "Info FixtureType 4",
    ])
    _warn_missing_attrs(r0a[1], "Viper Profile (type 4)")

    r0b = await run("Phase 0b: Quantum Wash basic (type 5) attribute info", [
        "Info FixtureType 5",
    ])
    _warn_missing_attrs(r0b[0], "Quantum Wash (type 5)")

    r0c = await run("Phase 0c: List existing presets", [
        "List Preset 1",
        "List Preset 2",
        "List Preset 3",
        "List Preset 4",
    ])

    # Find free sequence IDs
    seq_resp = await run("Phase 0d: List sequences to find free IDs", [
        "List Sequence",
    ])
    global PROFILE_SEQ_ID, WASH_SEQ_ID
    PROFILE_SEQ_ID = _find_free_seq_id(seq_resp[0], [201, 301, 401])
    WASH_SEQ_ID = PROFILE_SEQ_ID + 1
    print(f"\n  Using: Profile seq={PROFILE_SEQ_ID},  Wash seq={WASH_SEQ_ID}")

    # ── Phase 1: Dimmer presets ─────────────────────────────────────────────
    print(f"\n{sep}")
    print("  Phase 1: Dimmer presets (1.1-1.5)")
    print(f"{sep}")
    for slot, name, level in DIMMER_PRESETS:
        await run(f"Dimmer preset 1.{slot} '{name}' ({level}%)", [
            f"at {level}",
            f"Store Preset 1.{slot} /overwrite",
            f'Label Preset 1.{slot} "{name}"',
            "Clear",
        ])

    # ── Phase 2: Position presets ───────────────────────────────────────────
    print(f"\n{sep}")
    print("  Phase 2: Position presets (2.1-2.5) -- all movers 111-125 + 201-220")
    print(f"{sep}")
    for slot, name, pan, tilt in POSITION_PRESETS:
        await run(f"Position preset 2.{slot} '{name}' Pan={pan} Tilt={tilt}", [
            ALL_MOVERS,
            f'attribute "Pan" at {pan}',
            f'attribute "Tilt" at {tilt}',
            f"Store Preset 2.{slot} /overwrite",
            f'Label Preset 2.{slot} "{name}"',
            "Clear",
        ])

    # ── Phase 3: Gobo presets ───────────────────────────────────────────────
    print(f"\n{sep}")
    print("  Phase 3: Gobo presets (3.1-3.5) -- profile spots 111-125 only")
    print(f"{sep}")
    for slot, name, value in GOBO_PRESETS:
        await run(f"Gobo preset 3.{slot} '{name}' (Gobo1={value})", [
            PROFILE_SPOTS,
            f'attribute "Gobo1" at {value}',
            f"Store Preset 3.{slot} /overwrite",
            f'Label Preset 3.{slot} "{name}"',
            "Clear",
        ])

    # ── Phase 4: Color presets ──────────────────────────────────────────────
    print(f"\n{sep}")
    print("  Phase 4: Color presets (4.1-4.8) -- all fixtures (universal)")
    print(f"{sep}")
    for slot, name, r, g, b in COLOR_PRESETS:
        await run(f"Color preset 4.{slot} '{name}' R={r} G={g} B={b}", [
            ALL_FIXTURES,
            f'attribute "ColorRgb1" at {r}',
            f'attribute "ColorRgb2" at {g}',
            f'attribute "ColorRgb3" at {b}',
            f"Store Preset 4.{slot} /overwrite",
            f'Label Preset 4.{slot} "{name}"',
            "Clear",
        ])

    # ── Phase 5: Color sequence — Profiles (111-125) ────────────────────────
    print(f"\n{sep}")
    print(f"  Phase 5: Color sequence {PROFILE_SEQ_ID} for Profiles (111-125)")
    print(f"{sep}")
    for slot, name, r, g, b in COLOR_PRESETS:
        await run(f"Cue {slot} '{name}' -> Seq {PROFILE_SEQ_ID}", [
            PROFILE_SPOTS,
            f"Preset 4.{slot}",
            f"Store Cue {slot} Sequence {PROFILE_SEQ_ID} /overwrite",
            f'Label Cue {slot} Sequence {PROFILE_SEQ_ID} "{name}"',
            f"Appearance Cue {slot} Sequence {PROFILE_SEQ_ID} /r={r} /g={g} /b={b}",
            "ClearAll",
        ])
    await run(f"Label sequence {PROFILE_SEQ_ID}", [
        f'Label Sequence {PROFILE_SEQ_ID} "Color Palette Profiles"',
    ])

    # ── Phase 6: Color sequence — Washes (201-220) ──────────────────────────
    print(f"\n{sep}")
    print(f"  Phase 6: Color sequence {WASH_SEQ_ID} for Washes (201-220)")
    print(f"{sep}")
    for slot, name, r, g, b in COLOR_PRESETS:
        await run(f"Cue {slot} '{name}' -> Seq {WASH_SEQ_ID}", [
            WASH_ONLY,
            f"Preset 4.{slot}",
            f"Store Cue {slot} Sequence {WASH_SEQ_ID} /overwrite",
            f'Label Cue {slot} Sequence {WASH_SEQ_ID} "{name}"',
            f"Appearance Cue {slot} Sequence {WASH_SEQ_ID} /r={r} /g={g} /b={b}",
            "ClearAll",
        ])
    await run(f"Label sequence {WASH_SEQ_ID}", [
        f'Label Sequence {WASH_SEQ_ID} "Color Palette Washes"',
    ])

    # ── Phase 7: Assign to executors ────────────────────────────────────────
    # Find next two free executor slots
    exec_resp = await run("Phase 7a: List executors to find free slots", [
        "List Executor 1 Thru 240",
    ])
    exec_clean = _strip_ansi(exec_resp[0])
    used_execs = {int(m) for m in re.findall(r"Executor\s+(\d+)", exec_clean)}
    exec_a = next((e for e in range(202, 300) if e not in used_execs), 202)
    exec_b = next((e for e in range(exec_a + 1, 300) if e not in used_execs), exec_a + 1)
    print(f"\n  Assigning: Profiles -> Executor {exec_a},  Washes -> Executor {exec_b}")

    await run(f"Phase 7b: Assign + label Profile sequence -> Executor {exec_a}", [
        f"Assign Sequence {PROFILE_SEQ_ID} At Executor {exec_a}",
        f'Label Executor {exec_a} "Profiles Color"',
        f"Appearance Executor {exec_a} /h=30 /s=80 /br=100",
    ])
    await run(f"Phase 7c: Assign + label Wash sequence -> Executor {exec_b}", [
        f"Assign Sequence {WASH_SEQ_ID} At Executor {exec_b}",
        f'Label Executor {exec_b} "Washes Color"',
        f"Appearance Executor {exec_b} /h=200 /s=80 /br=100",
    ])

    # ── Phase 8: Verify ─────────────────────────────────────────────────────
    await run("Phase 8: Verify presets", [
        "List Preset 1",
        "List Preset 2",
        "List Preset 3",
        "List Preset 4",
    ])
    await run("Phase 8b: Verify sequences", [
        f"List Cue 1 Thru 8 Sequence {PROFILE_SEQ_ID}",
        f"List Cue 1 Thru 8 Sequence {WASH_SEQ_ID}",
    ])
    await run("Phase 8c: Verify executors", [
        f"List Executor {exec_a}",
        f"List Executor {exec_b}",
    ])

    await client.disconnect()

    print(f"\n{sep}")
    print("  SETUP COMPLETE")
    print(f"{sep}")
    print("  Dimmer presets  : 1.1-1.5")
    print("  Position presets: 2.1-2.5  (all movers 111-125 + 201-220)")
    print("  Gobo presets    : 3.1-3.5  (profile spots 111-125)")
    print("  Color presets   : 4.1-4.8  (all fixtures)")
    print(f"  Profile seq     : {PROFILE_SEQ_ID}  -> Executor {exec_a} 'Profiles Color'")
    print(f"  Wash seq        : {WASH_SEQ_ID}  -> Executor {exec_b} 'Washes Color'")
    print()


if __name__ == "__main__":
    asyncio.run(setup_content())
