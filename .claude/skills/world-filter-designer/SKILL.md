---
title: World and Filter Designer
description: Instruction module for creating grandMA2 Worlds (fixture access scoping) and Filters (attribute channel restriction) and applying them to executors, sequences, and user profiles
version: 1.0.0
created: 2026-03-31T20:00:00Z
last_updated: 2026-03-31T20:00:00Z
---

# World and Filter Designer

**Charter:** DESTRUCTIVE — creates and configures Worlds and Filters for multi-operator
access control and attribute restriction in grandMA2 shows.

Invoke when asked to: create operator zones, restrict fixture access, limit what attributes
a user can store, configure multi-operator environments, or set up guest operator access.

---

## Core Concept: Three Layers of Restriction

| Object | Restricts | Stored in | Applied to |
|--------|-----------|-----------|------------|
| **World** | Which **fixtures** are accessible | World pool (1-256) | User profile |
| **Filter** | Which **attributes/channels** can be stored or retrieved | Filter pool (1-256) | Executor, sequence, user profile, at-key |
| **Mask** | Which attributes are **shown** in sheets | Mask pool | Sheet views |

Worlds and Filters are independent — a user can have a World AND a Filter active simultaneously.

---

## Part 1 — Worlds

### What Worlds do

A World restricts which fixtures a user can see and control. Fixtures outside the World
are invisible and untouchable to that user. Used for:
- Operator A controls stage left, Operator B controls stage right
- Guest operator can only control FOH wash, not spot fixtures
- Programmer has full access; operator only has playback access

### Creating a World

```
Step 1: Select fixtures that should be IN the world
SelFix Fixture 201 Thru 220      # Quantum Washes = Operator A's world

Step 2: Store the world
store_world(
    world_id=1,
    name="Washes",
    confirm_destructive=True,
)
→ emits: store world 1 / label world 1 "Washes"

Step 3: Verify
list_worlds()
```

### Assigning a World to a user profile

```python
build_assign_world_to_user_profile(
    world_id=1,
    user_profile_name="operator",
)
→ emits: assign world 1 at userprofile "operator"
```

Use `assign_world_to_user_profile` MCP tool with `confirm_destructive=True`.

### World numbering convention

| World ID | Scope | For |
|----------|-------|-----|
| 1 | All fixtures | Admin / TD |
| 2 | Profile spots (111-125) | Spot operator |
| 3 | Wash fixtures (201-220) | Wash operator |
| 4 | FOH only | Guest operator |
| 5+ | Zone-specific | Additional operators |

---

## Part 2 — Filters

### What Filters do

A Filter restricts which attribute **channels** can be stored, retrieved, or transmitted.
Used for:
- Only storing Color attributes (not position or gobo) when programming
- Limiting a playback executor to control Intensity only
- Preventing an operator from accidentally storing Pan/Tilt in a preset

### Filter types

| Filter flag | Meaning |
|-------------|---------|
| Values (V) | Filters which attributes are stored by Store |
| Values+Timing (VT) | Filters both values AND timing information |
| Effect (E) | Filters effect data |

### Discovering filter attributes

```python
discover_filter_attributes()      # lists all filterable attribute names
```

Returns names like: `Dimmer`, `Pan`, `Tilt`, `ColorRgb1/2/3`, `Gobo1`, etc.

### Creating a Filter

The recommended approach is to import a pre-built filter XML:
```python
import_filter_xml(
    filter_file="filter_004.xml",   # Dimmer-only filter
    target_slot=4,
    confirm_destructive=True,
)
```

Or create from scratch using `store_object` then configure attributes:
```python
store_object(
    object_type="filter",
    object_id=1,
    name="Color Only",
    confirm_destructive=True,
)
```

The filter library XMLs are in `C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/IMPORT~1/filters/`.
Use `list_filters()` to see what's already in the pool.

### Applying a Filter to an executor

```python
assign_object(
    object_type="filter",
    object_id=1,
    target_type="executor",
    target_id=201,
    confirm_destructive=True,
)
→ emits: assign filter 1 at executor 1.201
```

### Applying a Filter temporarily (At key)

A temporary filter is active only while its button is held and affects what the
At key stores or retrieves:
```
If Filter 1
```
Use `if_filter` tool (if available) or send via `send_raw_command`.

---

## Part 3 — Masks

Masks restrict what is **displayed** in sheets, not what can be stored.
Useful for simplifying the UI for operators without programming rights.

Masks are created like filters but applied to sheet views, not executors.
Coverage in this skill is limited to awareness — use `store_object("mask", N)`.

---

## Discovery Workflow

Before creating any World or Filter, audit what already exists:

```python
list_worlds()        # check world pool occupancy
list_filters()       # check filter pool occupancy
list_system_variables(filter_prefix="USER")  # confirm current user + rights
```

---

## Allowed Tools

```
list_worlds                    — SAFE_READ: discover world pool
list_filters                   — SAFE_READ: discover filter pool
discover_filter_attributes     — SAFE_READ: list filterable attribute names
store_world                    — DESTRUCTIVE: create World pool slot + label
label_world                    — DESTRUCTIVE: rename existing World
assign_world_to_user_profile   — DESTRUCTIVE: attach World to user
assign_object                  — DESTRUCTIVE: attach Filter to executor/sequence
store_object                   — DESTRUCTIVE: create Filter / Mask pool slot
import_objects                 — DESTRUCTIVE: import filter XML
create_filter_library          — DESTRUCTIVE: batch create filter XMLs
```

---

## Safety

- Assigning the wrong World to a user profile can **lock them out** of all fixtures.
  Always verify with `list_worlds()` before assigning.
- Worlds and Filters survive show saves — they persist across sessions.
- Never delete a World or Filter that is assigned to an active user profile without
  first removing the assignment. Use `assign_world_to_user_profile(world_id=None)`
  to clear before deleting.
- Test filter effects with a non-admin user before deploying to operators.
