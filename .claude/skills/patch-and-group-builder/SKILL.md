---
title: Patch and Group Builder
description: Instruction module for patching new fixture types and building fixture groups in grandMA2 — fixture type import, DMX addressing, group creation, and verification
version: 1.0.0
created: 2026-03-31T18:00:00Z
last_updated: 2026-03-31T18:00:00Z
---

# Patch and Group Builder

**Charter:** DESTRUCTIVE — imports fixture types, patches fixtures to DMX addresses,
and creates fixture groups. Used when adding new fixture types to an existing show.

Invoke when asked to: repatch fixtures, add new fixture types, create groups for
newly patched fixtures, or reorganize DMX addressing.

---

## Core Concept: Fixture Type → Patch → Group

The workflow has three phases, always in this order:

```
1. Import fixture type XML          (DESTRUCTIVE, once per new fixture type)
2. Patch fixtures to DMX addresses  (DESTRUCTIVE, one per fixture)
3. Create and label groups          (DESTRUCTIVE, one per logical group)
```

Never patch before importing the fixture type. Never create groups before patching.

---

## Phase 1 — Import Fixture Type

Use `import_fixture_type` tool or the direct command:
```
Import "filename.xml" At FixtureType
```

Critical path constraints (live-verified 2026-03-13):
- Path must use **forward slashes** (backslashes cause `ILLEGAL CHARACTER` error)
- Path must use **8.3 short names** if it contains spaces
- 8.3 short path prefix: `C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/IMPORT~1/`

Check for existing fixture types first:
```
list_console_destination("FixtureType")
```
If the type already exists, skip import — re-importing an identical type is safe but slow.

---

## Phase 2 — Patch Fixtures

Patch each fixture individually using fixture number, DMX universe, and address.

### Fixture number conventions for this rig

| Range | Type | Notes |
|-------|------|-------|
| 1–9 | Mac 250 Krypton | Legacy wash fixtures |
| 101–110 | Mac 700 Profile Extended | Profile spots (10 units) |
| 111–125 | Mac Viper Profile | Profile spots (added 2026-03-30) |
| 201–220 | Mac Quantum Wash | Wash fixtures (added 2026-03-30) |
| 301+ | Reserve | For future fixture types |

### Patch command
```
Fixture {fixture_id} At Universe {universe} Address {dmx_address}
```

Or via `patch_fixture` MCP tool with `confirm_destructive=True`.

### DMX addressing rules
- Verify no address overlap before patching: `list_console_destination("Patch")`
- Leave a gap between fixture types (e.g., end at 200, start next at 201)
- Mac Viper Profile Extended: **36 channels** per fixture
- Mac Quantum Wash: **52 channels** per fixture
- Always calculate: `next_address = prev_address + channel_count`

---

## Phase 3 — Create Fixture Groups

Create one group per fixture type (for bulk selection) and optionally per logical
zone (front, back, etc.).

### Store Group timing rule (critical — live-verified 2026-03-13)

The ONLY reliable pattern is:
```
FixtureType {type_id}.M.1 Thru   ← Select by fixture type (standalone line)
Store Group {N} /o               ← Store immediately after (separate line)
```

These patterns **do NOT work**:
- `SelFix Group N` + `Store Group` → yields only 1 subfixture
- `ClearAll ; FixtureType X.M.1 Thru` + `Store Group` → yields only 1 subfixture
- Preset recall + `Store Group` → captures ALL patched fixtures

### Group numbering convention

| Group ID | Contents |
|----------|----------|
| 1–9 | Legacy fixture groups |
| 10–12 | Mac 700 groups (10=All, 11=Left, 12=Right) |
| 13 | All Mac Viper Profile |
| 14 | All Mac Quantum Wash |
| 15 | All Moving Heads (Vipers + Quantums combined) |
| 20+ | Zone groups (FOH, Balcony, etc.) |
| 99 | Test/scratch group (reusable) |

### Label and appearance after creating each group

```
Label Group {N} "{name}"
Appearance Group {N} /h={hue} /s=80 /br=100
```

Use distinct hues to visually distinguish groups in the pool:
- Profiles → hue 30 (warm orange)
- Washes → hue 200 (cool blue)
- All → hue 120 (neutral green)

---

## Macro Approach for Group Store

For reliable group creation via Telnet, use a macro with one command per line:
```xml
<Macro Name="StoreGroups">
  <MacroData>
    <MacroRow index="0">
      <MacroCell><CmdData Cmd="FixtureType 4.M.1 Thru" /></MacroCell>
    </MacroRow>
    <MacroRow index="1">
      <MacroCell><CmdData Cmd="Store Group 13 /o" /></MacroCell>
    </MacroRow>
  </MacroData>
</Macro>
```

Each `FixtureType X.M.1 Thru` → `Store Group N /o` pair must be on consecutive lines
with NO other commands between them. Jump target numbering is 1-based (XML index 0-based).

---

## FixtureType Pool Index (this show)

| Pool index | FixtureType name | MA2 library ID |
|------------|-----------------|----------------|
| 1 | Mac 250 Krypton | (varies) |
| 2 | Mac 700 Profile Extended | (varies) |
| 3 | GLP X4 (if present) | (varies) |
| 4 | Mac Viper Profile | (varies) |
| 5 | Mac Quantum Wash | (varies) |

Discover at runtime: `list_console_destination("FixtureType")` or `Info FixtureType N`.

Pool index (cd 10.3.N) uses sequential position, NOT the internal library ID.

---

## Verification Phase

After all patching and group creation:

```
list_console_destination("Fixture")     # Count patched fixtures
list_console_destination("Group")       # Count groups
Info Group {N}                          # Confirm fixture count per group
```

Assert:
- Group 13 (Vipers) contains 15 fixtures (111–125)
- Group 14 (Quantums) contains 20 fixtures (201–220)
- Group 15 (All movers) contains 35 fixtures (111–220)

---

## Safety

- All patch and group store operations require `confirm_destructive=True`.
- Print intent before each destructive operation.
- Never patch over an occupied DMX address without explicit operator confirmation.
- Never delete existing groups without operator approval — they may be referenced by cues.
- Save show after successful patch: `save_show` (requires `SHOW_LOAD` scope).
