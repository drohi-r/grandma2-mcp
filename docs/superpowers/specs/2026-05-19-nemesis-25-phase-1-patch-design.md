---
title: Nemesis 25 — Phase 1, Depence MVR → MA2 Patch Transfer
description: Design for extracting the Nemesis 25 Years rig from a Depence R4 MVR file and patching it into a fresh grandMA2 showfile via the MCP server
version: 1.0.0
created: 2026-05-19T11:25:04Z
last_updated: 2026-05-19T11:25:04Z
---

# Nemesis 25 — Phase 1: Patch Transfer

## Goal

Transfer the approved Depence R4 rig (`/Users/Drohi/Desktop/Nemesis 25 Years/Lights.mvr`) into a fresh grandMA2 showfile on console `Ma2` (`2.0.0.101:30000`) using the grandma2-mcp server, and verify every fixture is patched correctly before any further programming.

## Non-Goals (deferred to later phases)

- Fixture groups (Phase 2)
- Color / position / beam / gobo preset library (Phase 2)
- Executor page layout / busking template (Phase 3)
- Song cuelists, SMPTE timecode (Phase 4)
- 3D positions from the MVR `<Matrix>` data — extracted to CSV for reference but not pushed into MA2 in Phase 1

Done = patched, verified, signed off. Then we move on.

## Source of Truth

The Depence MVR is the canonical rig description. It contains **76 fixtures across 5 types in 5 universes** (already parsed and verified):

| MA2 Fixture # | GDTF | Mode | Ch/fix | Count | DMX Range | MVR FixtureIDs |
|---|---|---|---|---|---|---|
| 1–24 | Clay Paky@HY B-EYE K25 | Standard | 21 | 24 | U1.001–U1.504 | (from MVR) |
| 101–116 | Clay Paky@Sharpy | Standard | 16 | 16 | U2.001–U2.256 | (from MVR) |
| 201–210 | GLP@Impression X4 Bar 20 | Normal | 34 | 10 | U3.001–U3.340 | (from MVR) |
| 301–318 | Robe@ColorStrobe | M1 – RGBW | 9 | 18 | U4.001–U4.162 | (from MVR) |
| 401–408 | Generic@4-Lite Blinder | Single | 1 | 8 | U5.001–U5.008 | (from MVR) |

Numbering follows the project standard (see `memory/feedback_fixture_numbering.md`): 100-block per fixture-type role, smallest IDs to primary wash.

MVR addresses use `break="0"` with absolute DMX address; conversion to MA2 `Uxx.yyy`: `universe = ceil(addr/512)`, `offset = addr - 512×(universe-1)`.

## Architecture

Three discrete units, each independently testable. Data flows one-way: MVR → CSV → MA2.

```
┌────────────────┐   ┌──────────────────┐   ┌──────────────────────────┐
│  MVR Extractor │ → │ Patch CSV (truth)│ → │ MA2 Patcher (via MCP)    │
│  Python script │   │ tmp/nemesis_*.csv│   │ uses patch_fixture tool  │
└────────────────┘   └──────────────────┘   └──────────────────────────┘
                                                      │
                                                      ▼
                                              ┌──────────────────────────┐
                                              │ Verifier: list patch     │
                                              │ → diff vs CSV → report   │
                                              └──────────────────────────┘
```

### Unit 1 — MVR Extractor

**Purpose:** Parse the MVR ZIP, emit a canonical `nemesis_patch.csv` plus a `nemesis_fixture_types.csv` listing the 5 unique GDTF/mode combinations.

**Inputs:** `/Users/Drohi/Desktop/Nemesis 25 Years/Lights.mvr`

**Outputs:**
- `tmp/nemesis_patch.csv` — one row per fixture, columns: `ma2_fixture_id, type_key, gdtf_name, mode, universe, address, channel_count, position_x_mm, position_y_mm, position_z_mm, depence_fixture_id, label`
- `tmp/nemesis_fixture_types.csv` — one row per unique type, columns: `type_key, gdtf_name, mode, channel_count, ma2_library_path, ma2_library_mode`
  - `ma2_library_path` and `ma2_library_mode` start blank and get filled in during type-mapping review

**Dependencies:** Python stdlib only (`zipfile`, `xml.etree.ElementTree`, `csv`, `math`). No new packages.

**Where it lives:** `scripts/mvr_to_patch_csv.py` (new file). Generic — takes MVR path and CSV output dir as args. Reusable for future shows.

**Renumbering logic:** MVR `FixtureID`s are 1025–1100 (Depence-internal). The extractor groups fixtures by GDTF+mode, sorts each group by MVR address ascending, then re-assigns MA2 IDs by walking the block scheme:

```
HY B-EYE K25 (Standard) → start at 1
Sharpy (Standard)       → start at 101
X4 Bar 20 (Normal)      → start at 201
ColorStrobe (M1-RGBW)   → start at 301
4-Lite Blinder (Single) → start at 401
```

The block-start map is a config dict at the top of the script — easy to override per show.

### Unit 2 — MA2 Patcher

**Purpose:** Drive the grandma2-mcp tools to (a) create a fresh show, (b) ensure each fixture type exists in the FixtureType pool, (c) patch every fixture from the CSV.

**Tools used (existing MCP tools, no new code):**
| MCP tool | Purpose | Risk tier |
|---|---|---|
| `console_login` | Confirm session under Drohi/1234 | SAFE_READ |
| `get_system_info` | Verify console version + reachability | SAFE_READ |
| `new_show` | Fresh show, `preserve_connectivity=True`, `confirm_destructive=True` | DESTRUCTIVE |
| `list_console_destination("FixtureType")` | Check which types already exist | SAFE_READ |
| (operator action) | Add missing fixture types from MA2 built-in library on the console | DESTRUCTIVE |
| `patch_fixture` | One call per fixture, `confirm_destructive=True` | DESTRUCTIVE |
| `list_console_destination("Patch")` | Verification read-back | SAFE_READ |

**Show name:** `nemesis_25` (created fresh with `new_show("nemesis_25", preserve_connectivity=True)`).

**Fixture-type source:** the built-in MA2 v3.9 library — all 5 GDTFs in the MVR have direct MA2 library equivalents (Clay Paky HY B-EYE K25, Sharpy, Robe ColorStrobe, GLP X4 Bar 20, generic 1-ch dimmer). The mapping CSV (`nemesis_fixture_types.csv`) is reviewed and filled in by the operator before any patching happens — this is the one manual sync point.

**Mode-match risk:** GDTF mode names won't be byte-identical to MA2 library mode names. The mapping review step explicitly captures the chosen MA2 mode for each type and we verify channel-count matches the MVR before patching.

**Batching:** patch by fixture type (24 → 16 → 10 → 18 → 8 = 76 total calls). After each type, run a `list patch` read-back to catch failures early instead of at the end.

### Unit 3 — Verifier

**Purpose:** Prove the console patch matches the CSV. No silent partial successes.

**Steps:**
1. `list_console_destination("Patch")` → parse table output → produce `tmp/console_patch_readback.csv`
2. Diff `nemesis_patch.csv` vs `console_patch_readback.csv` on columns: `ma2_fixture_id, fixture_type_name, universe, address, channel_count`
3. Spot-check 3 random fixtures with `info fixture <N>` (one per side of the universe range)
4. Emit `tmp/patch_verification_report.md` with:
   - Total expected vs total patched
   - Per-type counts
   - Any address overlaps detected
   - Any mismatches (fixture-by-fixture diff table)
   - GREEN / AMBER / RED status

**Pass criteria for Phase 1:**
- 76 patched, 0 missing, 0 extras
- All universes match
- All addresses match
- All fixture types resolved (no `Unknown` type rows)
- No address overlaps
- Operator sign-off

## Sequence

```
1. Run MVR extractor                                  → CSVs written, eyeball-check pass
2. Operator reviews nemesis_fixture_types.csv         → fills in MA2 library paths/modes
3. Confirm MA2 reachable (console_login + system_info)
4. new_show("nemesis_25", preserve_connectivity=True) → fresh show
5. Verify FixtureType pool has the 5 needed types     → add via MA2 console GUI if missing
6. Patch loop, batched by type, with read-back per batch
7. Final verification pass → patch_verification_report.md
8. Operator sign-off → Phase 1 done
```

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| GDTF mode name ≠ MA2 library mode name | High | Manual mapping CSV reviewed before patching; channel-count cross-check |
| MA2 library missing one of the 5 fixture types | Low | All 5 are common types in MA2 v3.9. Fallback: convert GDTF or substitute a same-channel-count generic profile |
| Telnet drops mid-patch | Low | Session auto-reconnects per `src/session_manager.py`; resume from last successful fixture (CSV is idempotent — re-patching same ID is a no-op or overwrite) |
| Address overlap between types | Very low (verified in MVR) | Verifier explicitly checks for overlaps after each batch |
| `new_show` wipes Sami's Busking/Programming views | Certain — intended | Documented loss; rebuild for Drohi in Phase 3 |
| Operator runs script with wrong console env | Low | Pre-flight `get_system_info` displays host + version + show name, operator confirms before `new_show` |

## Rollback

`new_show` is destructive but the prior show (`Ecube busking template`) is saved on the console. To roll back: `LoadShow "Ecube busking template"`. No data loss outside what was unsaved on the prior session.

If patch goes wrong mid-flight: `Oops` repeatedly to undo, or run `new_show` again to wipe and restart from the CSV (idempotent).

## Deferred (later phases)

- **Phase 2:** fixture groups (by type, by side, by position-row), preset library (colors, positions, beams, gobos)
- **Phase 3:** executor page layout via `busking-template-generator` skill, View pool slots for Drohi
- **Phase 4:** per-song cuelists, SMPTE timecode setup
- **3D positions:** MVR `<Matrix>` data lands in the CSV but is not consumed in Phase 1. Phase 2 may use it to seed position presets.

## Open Items (none blocking Phase 1)

- Decision deferred: whether to also patch a Grand Master / Master Speed / Special Master assignment in Phase 1 — current plan is *no*, leave defaults until Phase 3.
- Decision deferred: whether the showfile lives on the console or also gets backed up to the worktree after each phase — recommend yes via `SaveShow` + manual file pull, but not gating Phase 1 sign-off.
