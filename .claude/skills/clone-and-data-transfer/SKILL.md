---
title: Clone and Data Transfer
description: Instruction module for grandMA2 Clone workflow — copying fixture data between fixture types, selective cloning by attribute, and transferring cue content between sequences
version: 1.0.0
created: 2026-03-31T21:00:00Z
last_updated: 2026-03-31T21:00:00Z
---

# Clone and Data Transfer

**Charter:** DESTRUCTIVE — clones fixture programming from one fixture to another (readdressing),
copies cue content between sequences, and transfers pool objects. Used when swapping fixture
types, duplicating show content, or redistributing programming after a rig change.

Invoke when asked to: clone fixtures, copy programming from one fixture to another, transfer a
cue list to a new sequence, copy presets between slots, duplicate a group, or remap fixture IDs.

---

## Core Concept: Clone vs. Copy

| Command | What it does | Use when |
|---------|-------------|---------|
| **Clone** | Copies programming data from fixture A to fixture B across ALL cues and presets | Swapping fixture types or IDs in a live show |
| **Copy** | Duplicates a pool object (sequence, preset, group) to a new slot | Duplicating a cue list or preset set |
| **Move** | Moves a pool object to a new slot (removes from source) | Renumbering or reorganizing |

---

## Part 1 — Clone Fixtures

Clone copies all programmer values, preset references, and cue data for the source
fixture and reassigns them to the target fixture ID.

### Basic clone

```python
clone_fixture(
    source_fixture_id=1,
    target_fixture_id=201,
    confirm_destructive=True,
)
```

This emits: `Clone Fixture 1 At Fixture 201`

After cloning, Fixture 201 has the same programming as Fixture 1 in all cues,
presets, and groups.

### Clone a range of fixtures

```python
clone_fixture(
    source_fixture_id="1 Thru 9",
    target_fixture_id="201 Thru 209",
    confirm_destructive=True,
)
```

This emits: `Clone Fixture 1 Thru 9 At Fixture 201 Thru 209`

Ranges must match in size. MA2 maps source[N] → target[N] sequentially.

### Clone with selective flag

`/selective` limits the clone to only attributes that are currently set in the
programmer (rather than all stored attributes):

```python
clone_fixture(
    source_fixture_id=1,
    target_fixture_id=201,
    selective=True,
    confirm_destructive=True,
)
```

This emits: `Clone Fixture 1 At Fixture 201 /selective`

Use `/selective` when:
- You want to copy only color data (not position or gobo)
- Preserving partial programming in the target fixture
- Merging specific attribute layers between fixtures

---

## Part 2 — Clone to New Fixture Type

When a fixture is physically replaced with a different model:

1. Patch the new fixture type at the same or new ID
2. Clone programming from old ID to new ID
3. Optionally delete the old fixture from the patch

```python
# Step 1: Discover old fixture data
get_object_info("fixture", 1)

# Step 2: Clone to new fixture
clone_fixture(
    source_fixture_id=1,
    target_fixture_id=301,   # new fixture ID
    confirm_destructive=True,
)

# Step 3: Delete old fixture (after verifying clone succeeded)
delete_object("fixture", 1, confirm_destructive=True)
```

**Note:** Attribute name mapping between fixture types is automatic when library names
match (both use `Pan`/`Tilt`/`ColorRgb1` etc.). If attribute names differ, Clone may
not map all attributes — verify in a cue after cloning.

---

## Part 3 — Copy Pool Objects

### Copy a sequence

```python
copy_object(
    object_type="sequence",
    source_id=99,
    target_id=100,
    confirm_destructive=True,
)
```

This emits: `Copy Sequence 99 At Sequence 100`

### Copy presets (range)

```python
copy_object(
    object_type="preset",
    source_id="4.1 Thru 4.8",
    target_id="4.101",     # start of target range
    confirm_destructive=True,
)
```

This emits: `Copy Preset 4.1 Thru 4.8 At Preset 4.101`

### Copy a group

```python
copy_object(
    object_type="group",
    source_id=14,
    target_id=24,
    confirm_destructive=True,
)
```

---

## Part 4 — Move Pool Objects

Move (rename/renumber) a pool object to a new slot. Source slot is emptied.

```python
move_object(
    object_type="sequence",
    source_id=200,
    target_id=10,
    confirm_destructive=True,
)
```

This emits: `Move Sequence 200 At Sequence 10`

---

## Part 5 — Transfer Cue Content Between Sequences

To copy specific cues from one sequence to another:

```python
# Copy cues 1-8 from sequence 99 to sequence 200
send_raw_command(
    "Copy Cue 1 Thru 8 Sequence 99 At Cue 1 Sequence 200",
    confirm_destructive=True,
)
```

Or copy a single cue to a different position:

```python
send_raw_command(
    "Copy Cue 5 Sequence 99 At Cue 10 Sequence 99",  # duplicate within same sequence
    confirm_destructive=True,
)
```

---

## Part 6 — Export and Re-import for Cross-Show Transfer

For transferring content between different show files (not just within one show),
use Export + PSR (see show-management-and-psr skill):

```python
# In source show: export the content
export_objects("sequence", 99, "color_show_seq_99", confirm_destructive=True)

# Load target show...

# In target show: import
import_objects("sequence", "color_show_seq_99", 99, confirm_destructive=True)
```

---

## Allowed Tools

```
clone_fixture       — DESTRUCTIVE: copy fixture programming across all cues/presets
copy_object         — DESTRUCTIVE: duplicate pool object to new slot
move_object         — DESTRUCTIVE: renumber/rename pool object
delete_object       — DESTRUCTIVE: remove pool object after clone verification
export_objects      — DESTRUCTIVE: save pool objects to XML for cross-show transfer
import_objects      — DESTRUCTIVE: load pool objects from XML
send_raw_command    — DESTRUCTIVE: cue-range copy within or between sequences
get_object_info     — SAFE_READ: verify fixture data before cloning
list_sequences      — SAFE_READ: confirm target slots are free
```

---

## Safety

- Always verify the target slot is empty before Copy/Move — MA2 overwrites without warning.
  Use `list_sequences()` / `list_presets()` before every copy operation.
- Clone to a new fixture type may not map all attributes — run the sequence and visually
  confirm all attributes have transferred correctly.
- `/selective` clone respects programmer state at clone time — set attributes in programmer
  before running a selective clone.
- `Move` is irreversible (unlike Copy). Always Copy first, verify, then delete the source.
- After cloning fixture IDs, update any groups that referenced the old ID:
  `SelFix Fixture 301 → Store Group N /o` to refresh group membership.
- Cross-show PSR may bring in fixture references that do not match the current patch.
  Verify fixture IDs in imported cues match current rig after every PSR.
