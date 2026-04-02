---
title: MA2 Command Conventions
description: Live-verified MA2 command rules, quoting, navigation, and data directory layout
version: 1.0.0
created: 2026-03-29T21:44:45Z
last_updated: 2026-03-29T21:44:45Z
---

# MA2 Command Conventions

> Loaded on-demand when working on MA2 command builders, navigation, or console scripting.

---

## New Show — connectivity preservation

Always use the default `preserve_connectivity=True` when calling `new_show()`.
Creating a new show without `/globalsettings` **resets Telnet to "Login Disabled"**, severing the MCP connection.

| MA2 flag | What it preserves |
|---|---|
| `/globalsettings` | Telnet login enabled/disabled + MA-Net2 TTL/DSCP |
| `/network` | IP addresses and MA-Net2 network config |
| `/protocols` | Art-Net, sACN, DMX protocol assignments |

Only pass `preserve_connectivity=False` when the user **explicitly** wants a completely clean show AND understands they must manually re-enable Telnet in Setup → Console → Global Settings.

---

## Name quoting — quote_name()

All label/info/list commands that include a name use `quote_name(name, match_mode)` from `src/commands/helpers.py`.

- **Rule A (default)**: quote if the name contains any MA2 special character (`* @ $ . / ; [ ] ( ) " space`). Plain names are emitted bare.
- **match_mode="wildcard"**: emits the name raw so `*` acts as a wildcard operator.
- Callers must pass the **raw name**, not a pre-quoted string (e.g. `"Mac700 Front"` not `'"Mac700 Front"'`).

---

## Wildcard workflow — discover_object_names

1. Call `discover_object_names("Group")` → returns `names_only` list + `wildcard_tip`
2. Derive a pattern from the names (e.g. `Mac700*`)
3. Pass to `list_objects("group", name="Mac700*", match_mode="wildcard")` → `list group Mac700*`

Works with any keyword (`"Group"`, `"Sequence"`, `"Macro"`, etc.) or numeric cd index.

---

## MAtricks command keywords (live-verified 2026-03-11)

MAtricks use **direct command keywords** — no `cd` navigation needed.

| Keyword | Syntax | Example |
|---------|--------|---------|
| `MAtricksInterleave` | `[width]`, `[col].[width]`, `+/-`, `Off` | `MAtricksInterleave 4` |
| `MAtricksBlocks` | `[size]`, `[x].[y]`, `+ N/- N`, `Off` | `MAtricksBlocks 2.3` |
| `MAtricksGroups` | `[size]`, `[x].[y]`, `+ N/- N`, `Off` | `MAtricksGroups 4` |
| `MAtricksWings` | `[parts]`, `+/-`, `Off` | `MAtricksWings 2` |
| `MAtricksFilter` | `[num]`, `"name"`, `+/-`, `Off` | `MAtricksFilter "OddID"` |
| `MAtricksReset` | (no args) | `MAtricksReset` |
| `MAtricks` | `[id]`, `On/Off/Toggle` | `MAtricks 5` |
| `All` | (no args) | resets Single X sub-selection |
| `AllRows` | (no args) | resets Single Y sub-selection |
| `Next` / `Previous` | (no args) | step forward/backward Single X |
| `NextRow` | (no args) | step forward Single Y (row) |

- `Interleave` is a synonym for `MAtricksInterleave`.
- Y-axis settings require Interleave to be active first.
- **No `PreviousRow`** — asymmetric; only `NextRow` exists.
- **No telnet command reads current MAtricks state** — GUI only.
- Pool path: `cd MAtricks` → `UserProfiles/Default 1/MatrixPool`.

---

## Appearance colors

MA2 appearance commands use **0-100 percentage scale** for RGB and HSB — NOT 0-255.

| Mode | Parameters | Range |
|------|-----------|-------|
| RGB | `/r=R /g=G /b=B` | 0-100 each |
| HSB | `/h=H /s=S /br=BR` | hue 0-360, sat/bright 0-100 |
| Hex | `/color=RRGGBB` | 6-digit hex, no `#` |

**XML format:** `<Appearance Color="RRGGBB" />` embeds inside any pool object element. Colors imported via XML appear instantly.

**Filter library color scheme:** 9 categories — see `src/commands/constants.py:FILTER_COLOR_MAP`.

---

## Import `/path=` option (live-verified 2026-03-13)

**Critical constraint**: path must use **forward slashes** and **no spaces** (use Windows 8.3 short names).

| Syntax | Result |
|--------|--------|
| `\` backslashes | `ILLEGAL CHARACTER \` error |
| Full path with spaces | MA2 splits on space — token parse error |
| 8.3 short path + `/` | **SUCCESS** |
| Relative path | `FILE NOT FOUND` |

**8.3 short paths for this system:**

| Short path | Resolves to |
|------------|-------------|
| `C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/IMPORT~1/` | `importexport/` |
| `C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/IMPORT~1/filters` | `importexport/filters/` |
| `C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/macros/` | `macros/` |

---

## MA2 data directory organization

```
macros/
  archive/        — iteration history (v1-v8.2), exports, duplicates
  utilities/      — Delete Group, Import-Type-Selector, Preset-Type-Selector
  stock/          — MA2 stock macros (WYG2GMA, DIMMER FX, etc.)
  *.xml           — active macros (v7, v8.3, v9) + predefined.xml (MA2 system)

importexport/
  filters/        — 168 filter library XMLs (filter_003..filter_170)
  imports/        — user import files (presets, fixture layers)
  exports/        — exported objects
  archive/        — old test files, audit artifacts
  styles/         — MA2 system XSL stylesheets (do not touch)
```

---

## Macro Store Group timing (live-verified 2026-03-13)

| Pattern | Result |
|---------|--------|
| `FixtureType X.M.1 Thru` (own line) → `Store Group N /o` (later line) | **WORKS** |
| `ClearAll ; FixtureType X.M.1 Thru` + `Store Group` (next line) | **FAILS** — 1 subfixture |
| `SelFix Group N` + `Store Group` | **FAILS** — 1 subfixture |
| `Preset 0.$name` recall + `Store Group` | **WRONG** — ALL patched fixtures |

**Rule:** When adding features to a working macro, insert new lines around existing logic — do not modify lines that perform critical Store operations.

**Jump target convention:** `Go Macro 1."name".N` targets Line N (1-based) = XML index N-1. When inserting lines, use an index shift table to remap all jump targets.

---

## grandMA2 System Variables

26 built-in read-only system variables. Access via `list_system_variables()` or `get_variable(action="echo", var_name="NAME")`.

**`Echo $VARNAME` does NOT work** — MA2 expands before executing → UNKNOWN COMMAND. Always use `ListVar`.

**Key variables:**

| Variable | Example | Notes |
|----------|---------|-------|
| `$VERSION` | `3.9.60.65` | Full build version |
| `$SHOWFILE` | `claude_ma2_ctrl` | Current show name |
| `$USER` | `administrator` | Current login |
| `$USERRIGHTS` | `Admin` | Rights level |
| `$SELECTEDEXEC` | `1.1.1` | `page.page.exec` format |
| `$SELECTEDEXECCUE` | `NONE` or `1` | Active cue on selected executor |
| `$SELECTEDFIXTURESCOUNT` | `0`–`N` | Only updated by `SelFix`, not `Select` |
| `$FADERPAGE` | `1` | Change via `Page N` |
| `$PRESET` / `$FEATURE` / `$ATTRIBUTE` | `GOBO` / `GOBO1` / `GOBO1` | Updated by `Feature [name]` or `PresetType [id]` |

---

## PresetType / Feature / CD-Tree Correlation (live-verified 2026-03-10)

| PresetType | ID | CD path | $PRESET |
|------------|----|---------|---------|
| Dimmer | 1 | cd 10.2.1 | DIMMER |
| Position | 2 | cd 10.2.2 | POSITION |
| Gobo | 3 | cd 10.2.3 | GOBO |
| Color | 4 | cd 10.2.4 | COLOR |
| Beam | 5 | cd 10.2.5 | BEAM |
| Focus | 6 | cd 10.2.6 | FOCUS |
| Control | 7 | cd 10.2.7 | CONTROL |

`cd 10.2.N` uses sequential child index (1=first listed), not the internal library ID.

---

## CD Tree Root Location

The root prompt name is **show-dependent** — do not hardcode `"Fixture"`:
- Old show (`claude_ma2_ctrl`): root is `[Fixture]>`
- Different show loaded: root is `[Screen]>`

Navigation code must detect root dynamically (e.g. `cd /` then read the prompt).

---

## Strategic Scan (`scripts/strategic_scan.py`)

Fast 4-phase re-scan (~24 min vs 138 min full):

| Phase | What | Time |
|-------|------|------|
| 1 Root | cd+list indexes 1-50 | ~38s |
| 2 Structure | depth 3 all branches | ~15 min |
| 3 Deep | full recursive cd 10.3, 30, 38 | ~5 min |
| 4 Triage | retry failed edges 2x | ~1 min |

```bash
PYTHONUNBUFFERED=1 python -u scripts/strategic_scan.py [--output scan_output_new.json] [--old-scan scan_output.json]
```
