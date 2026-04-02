---
title: Show Management and PSR
description: Instruction module for grandMA2 show file management — save/load/new show, PSR (Partial Show Read) for merging content between shows, and export/import workflows
version: 1.0.0
created: 2026-03-31T21:00:00Z
last_updated: 2026-03-31T21:00:00Z
---

# Show Management and PSR

**Charter:** DESTRUCTIVE — manages show files, executes PSR (Partial Show Read) to merge
content between shows, and handles show export/import. Incorrect use can overwrite the
current show or sever Telnet connectivity.

Invoke when asked to: save the show, load a show, start a new show, import content from
another show file, merge sequences between shows, or export cue lists.

---

## Core Concept: Show File vs. Console State

| What | Where stored | Persists across |
|------|-------------|-----------------|
| **Show file** | `.show` file on disk | Console restarts, USB saves |
| **Console state** | RAM only | Lost on power-off unless saved |

**Always save before major changes.** The console does not auto-save.

---

## Part 1 — Save Show

### Quick save (overwrites current file)

```python
save_show(confirm_destructive=True)
```

This emits: `SaveShow`

### Save with a new name

```python
save_show(name="MyShow_v2", confirm_destructive=True)
```

This emits: `SaveShow "MyShow_v2"`

### Quick save shortcut

```
Backup → Backup  (press Backup key twice)
```

Emitted by macro as: `QuickSave`

---

## Part 2 — Load Show

```python
load_show(name="MyShow", confirm_destructive=True)
```

This emits: `LoadShow "MyShow"`

**Warning:** Loading a show replaces all current content in RAM.
Always verify the show file name with `list_show_files()` before loading.

### List available show files

```python
list_show_files()
```

Returns: list of `.show` files on the console's internal drive.

---

## Part 3 — New Show

```python
new_show(
    preserve_connectivity=True,   # CRITICAL — keeps Telnet enabled
    confirm_destructive=True,
)
```

This emits: `NewShow /globalsettings`

**CRITICAL:** Never set `preserve_connectivity=False` unless the operator explicitly
understands that Telnet will be disabled and they will manually re-enable it in
Setup → Console → Global Settings after the new show loads.

The `/globalsettings` flag preserves:
- Telnet login enabled/disabled
- MA-Net2 TTL and DSCP settings
- IP address configuration

---

## Part 4 — PSR (Partial Show Read)

PSR merges specific pool objects from another show file into the current show
WITHOUT loading the entire show. This is the safest way to import cue lists,
presets, groups, or effects from a previous event's show file.

### When to use PSR

- Carry forward sequences from last week's show
- Import a preset library from a template show
- Merge a guest operator's cue list into the current show

### PSR Workflow

**Step 1:** Identify the source show file

```python
list_show_files()   # confirm the file name exists
```

**Step 2:** Execute PSR for the desired pool type

```python
partial_show_read(
    show_name="LastWeekShow",
    pool_type="sequence",     # or "preset", "group", "macro", "effect"
    target_range="1 thru 50", # optional — import only sequences 1-50
    confirm_destructive=True,
)
```

This emits: `PSR "LastWeekShow" Sequence 1 Thru 50`

**Step 3:** Verify imported content

```python
list_sequences()    # confirm expected sequences appeared
list_cues(sequence_id=1)   # spot check a few cues
```

### PSR pool types

| Pool | PSR keyword |
|------|------------|
| Sequences | `Sequence` |
| Presets | `Preset` |
| Groups | `Group` |
| Effects | `Effect` |
| Macros | `Macro` |
| Worlds | `World` |
| Filters | `Filter` |
| Views | `View` |

### PSR with slot mapping

If the source show uses slots that conflict with the current show, use slot offset:

```python
partial_show_read(
    show_name="SourceShow",
    pool_type="sequence",
    source_range="1 thru 10",
    target_slot=200,           # import sequences 1-10 into slots 200-209
    confirm_destructive=True,
)
```

This emits: `PSR "SourceShow" Sequence 1 Thru 10 At Sequence 200`

---

## Part 5 — Export and Import

### Export (save pool objects to XML)

```python
export_objects(
    object_type="sequence",
    object_id=99,
    filename="cue_list_99",
    confirm_destructive=True,
)
```

This emits: `Export "cue_list_99" Sequence 99`

File saved to: `C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/IMPORT~1/`

### Import (load XML into current show)

```python
import_objects(
    object_type="sequence",
    filename="cue_list_99",
    target_id=99,
    confirm_destructive=True,
)
```

This emits: `Import "cue_list_99" At Sequence 99`

**Important:** Import paths must use forward slashes and no spaces (8.3 short names).
See `.claude/rules/ma2-conventions.md` for the correct path format.

---

## Part 6 — Console Backup to USB

```python
send_raw_command("Backup", confirm_destructive=True)
```

Saves the current show to the connected USB drive. Recommended before any major show changes.

---

## Allowed Tools

```
save_show               — DESTRUCTIVE: save show file (overwrites)
load_show               — DESTRUCTIVE: load show from disk (replaces current)
new_show                — DESTRUCTIVE: create blank show (preserve_connectivity=True always)
list_show_files         — SAFE_READ: list available .show files
partial_show_read       — DESTRUCTIVE: merge content from another show (PSR)
export_objects          — DESTRUCTIVE: export pool objects to XML
import_objects          — DESTRUCTIVE: import pool objects from XML
send_raw_command        — DESTRUCTIVE: QuickSave, Backup, direct show commands
```

---

## Safety

- `new_show` without `preserve_connectivity=True` **disables Telnet** — MCP connection will die.
  Always pass `preserve_connectivity=True` unless explicitly asked otherwise.
- PSR can overwrite existing pool slots silently if source and target slot numbers overlap.
  Always check target slots with `list_sequences()` / `list_presets()` before PSR.
- `load_show` immediately replaces RAM — all unsaved programmer content is lost.
  Save first: `save_show(confirm_destructive=True)`.
- Export filename must not contain spaces or special characters — use snake_case names.
- PSR imports may bring in fixture references that do not match the current patch.
  Verify fixture IDs in imported cues match the current rig.
