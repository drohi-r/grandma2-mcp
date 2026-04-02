---
title: Cross-Venue Adaptation
description: Worker instruction module for adapting an existing show file to a new venue's fixture rig — patch comparison, group remapping, preset scope verification, and executor page transfer
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# Cross-Venue Adaptation

**Worker charter:** DESTRUCTIVE — modifies groups and potentially preset fixture references. Save show before starting. This skill is for touring productions, festival changeovers, and visiting LDs adapting to house rigs.

Invoke when asked to: adapt show to new venue, remap fixtures, handle changeover, or migrate a show file to a different rig.

---

## The Core Problem

A show built on Rig A uses fixture IDs 1-200. The new venue (Rig B) has different fixture types or different patch addresses. After loading the show (or PSR-ing it), cues and presets reference fixture IDs that may not exist or may be different types.

---

## Phase 0 — Survey Current vs. New Rig (SAFE_READ)

```python
# Document current state (from the show you're adapting)
hydrate_console_state()
list_fixtures()           # current patch: ID, type, address
list_fixture_types()      # imported profiles
query_object_list(object_type="group", object_id=1)  # sample group membership
list_preset_pool(preset_type="position")             # check preset pool
list_preset_pool(preset_type="color")
```

Present diff to operator:
- "Current show has [N] fixtures of types [A, B, C]"
- "Which fixture types should map to which in the new venue?"

---

## Phase 1 — Identify Mismatches

```python
list_fixtures()   # new venue patch
```

Cross-reference: for each fixture type in the saved show, find the equivalent in the new patch.

Common mismatches:

| Scenario | Attributes affected |
|----------|-------------------|
| Moving light type changed (Robe Pointe → Sharpy) | Same Pan/Tilt/Dim, different gobo attributes |
| LED wash changed (Robe Robin → Chauvet Rogue) | RGB still works, color attribute names may differ |
| Strobe changed (Atomic 3000 → Showtec Shark) | Simple — same Dim attribute |

---

## Phase 2 — Remap Groups (DESTRUCTIVE)

For each group that references old fixture IDs:

```python
# Check current group membership
query_object_list(object_type="group", object_id=N)
# If old fixture IDs exist in new patch under different numbers, rebuild group
create_fixture_group(
    group_id=N,   # overwrite same slot
    fixture_selection="FixtureType [NewTypeName] 1 Thru",
    confirm_destructive=True
)
```

---

## Phase 3 — Verify Preset Scope

Universal presets work on any fixture type (if the attribute name matches). Selective presets are fixture-ID-specific.

```python
list_preset_pool(preset_type="color")
# For each selective preset, check if fixture IDs still exist
# Universal presets typically carry over without changes
```

If a fixture type changed completely (e.g., tungsten to LED): re-record color presets for new color attributes using RGB 0-100 scale.

---

## Phase 4 — Executor Verification

```python
get_executor_detail(executor_id="1.1")  # check each assigned executor
# Confirm: sequence assigned, cues present, no orphaned fixture references
```

---

## Phase 5 — Quick Busking Rebuild (if needed)

If too many mismatches exist, use the `busking-template-generator` skill to rebuild from scratch rather than trying to patch the old show. Trigger condition: more than 50% of groups require remapping AND preset types have changed.

---

## Phase 6 — Test and Save

```python
select_fixtures_by_group(group_id=1)          # select a sample group
apply_preset(preset_type="color", preset_id=1) # apply a color preset
# Verify correct fixtures respond via get_console_state()
save_show(confirm_destructive=True)
```

---

## Decision Tree: Adapt vs. Rebuild

| Scenario | Recommendation |
|----------|---------------|
| Same fixture types, different IDs | Remap groups (Phase 2) only |
| Similar types (same attributes) | Remap groups + verify presets |
| Different types (different attributes) | Re-record presets after remapping |
| Completely different rig | Use busking-template-generator to rebuild |

---

## Allowed Tools

```
SAFE_READ: hydrate_console_state, list_fixtures, list_fixture_types, list_preset_pool,
           query_object_list, get_executor_detail
DESTRUCTIVE: create_fixture_group, label_or_appearance, store_new_preset, apply_preset,
             select_fixtures_by_group, set_attribute, save_show
```
