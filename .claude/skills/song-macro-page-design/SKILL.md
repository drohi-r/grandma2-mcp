---
title: Song Macro Page Design
description: Instruction module for designing grandMA2 song macro pages — first-button protocol, executor layout, page naming, and jump target safety
version: 1.0.0
created: 2026-03-30T03:17:46Z
last_updated: 2026-03-30T03:17:46Z
---

# Song Macro Page Design

## First-Button Protocol

Every song page has exactly one macro on Executor 1. This macro loads the
song's complete starting state in a single button press. It is the "first
button" the LD presses when a song starts.

**Canonical first-button macro structure (4 lines):**

```
Line 1: ClearAll
         → wipes programmer, kills strays from previous song

Line 2: Go Preset 4.{color_preset_id}
         → applies song's color palette to all rig fixtures
         → preset_id = song_number * 10 + 1  (e.g. song 3 → Preset 4.31)

Line 3: Go Macro {rig_position_macro_id}
         → fires the rig position / focus macro for this song
         → this macro moves movers to their song-specific positions

Line 4: SelectDrive {song_executor_page}
         → jumps the surface to this song's effect fader page
         → LD's hands are now on the right faders for this song
```

Store this as a macro using `store_object` + `label_or_appearance`.
Macro ID convention: `100 + song_number` (e.g. song 3 → Macro 103).

## Page Naming Convention

```
SNG_{n}_{CamelCaseName}

Examples:
  SNG_1_Intro
  SNG_3_Villains
  SNG_7_GoWithTheFlow
  GLBL_Transitions     ← global page (not a song)
  GLBL_House           ← house lights global page
```

Use `label_or_appearance` to set the page label after creation.

## Executor Column Layout

```
Executor 1  : Song loader macro (NEVER an effect)
Executors 2–8  : Effect faders (one effect per executor)
Executors 9–10 : Group masters for rig sections
Executors 11+  : Optional: alternate versions, special one-offs
```

Effect assignment (pre-show):
```python
assign_effect_to_executor(effect_id=3, executor_id=2, page=song_page, confirm_destructive=True)
assign_effect_to_executor(effect_id=7, executor_id=3, page=song_page, confirm_destructive=True)
# ... repeat for each effect slot
```

## Jump Target Safety After Line Insertion

MA2 macro jump targets (`Go Macro 1."name".N`) reference **1-based line numbers**.
If you insert a line before a jump target, ALL downstream jump targets shift by +1.

**Safe insertion procedure:**
1. Before inserting, record all `Go Macro X."name".N` references in the macro
2. Create a shift table: for each jump target N where N > insert_position, new target = N+1
3. Insert the new line at `insert_position`
4. Update all jump targets using the shift table
5. Verify by running the macro in blind mode

**Example shift table (inserting at line 3):**
```
Old line 3 → now line 4 (shift)
Old line 4 → now line 5 (shift)
Old line 5 → now line 6 (shift)
Old line 1 → still line 1 (no shift — before insertion point)
Old line 2 → still line 2 (no shift — before insertion point)
```

Never insert lines into a working macro without computing this table first.

## Song Transition Checklist

Before triggering the first button for a new song:

```
1. Verify previous song's effects are fading (not hard-cutting)
2. Confirm faders for new song page are at 0 (use normalize_page_faders if needed)
3. Press Exec 1 (first button) — ClearAll + color + positions + page switch fires
4. Wait for position macros to complete (~2–4 seconds for movers)
5. Begin raising effect faders in cue with the music
```

The first button is a *state loader*, not a *playback trigger*. It prepares
the canvas; the LD paints it with faders.
