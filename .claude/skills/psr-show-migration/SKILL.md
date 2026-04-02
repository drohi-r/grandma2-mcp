---
title: PSR Show Migration
description: Worker instruction module for cross-show content migration using PSR (Partial Show Read) — slot conflict detection, fixture ID verification, and post-import diff
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# PSR Show Migration

**Charter:** DESTRUCTIVE — extends the `show-management-and-psr` skill with the missing
safety layer: pre-PSR slot conflict detection, mid-migration showfile integrity guards,
post-import diff, and fixture ID verification. Incorrect use silently overwrites existing
cues and leaves fixture references pointing at IDs that do not exist in the current patch.

Invoke when asked to: migrate content between shows, carry forward sequences from a
previous event, import a preset or group library across rigs, or merge a guest operator's
cue list without losing the current show's content.

---

## What This Skill Adds Over show-management-and-psr

| Concern | show-management-and-psr | This skill |
|---------|------------------------|------------|
| Save before PSR | Mentioned in safety note | **Enforced as step 4** |
| Slot conflict check | "check target slots first" | **Explicit step 3 with tool calls** |
| Show identity guard | Not covered | **assert_showfile_unchanged step 4** |
| Post-import diff | Not covered | **diff_console_state step 7** |
| Fixture ID verification | Mentioned in safety note | **Structured step 8 with output format** |

Do not use this skill for simple single-pool PSR from a known-clean show onto an empty
rig. Use `show-management-and-psr` for that. Use this skill when any of the following
are true:
- The current show already has content in the target pool slots.
- The source show was built on a different rig (different fixture IDs / patch).
- Multiple pool types are being migrated in one session.
- The session is time-sensitive and a mistake would be hard to recover.

---

## Allowed Tools

```
list_show_files             — SAFE_READ: confirm source show file exists
hydrate_console_state       — SAFE_READ: snapshot current pool counts (baseline)
get_console_state           — SAFE_READ: read cached console state
diff_console_state          — SAFE_READ: compare current state against baseline
assert_showfile_unchanged   — SAFE_READ: verify no show switch occurred mid-session
get_showfile_info           — SAFE_READ: confirm correct show is loaded
partial_show_read           — DESTRUCTIVE: merge content from another show (PSR)
save_show                   — DESTRUCTIVE: save before PSR to protect current content
query_object_list           — SAFE_READ: inspect cue content for fixture ID references
list_fixtures               — SAFE_READ: enumerate patched fixtures and their IDs
list_sequences              — SAFE_READ: check sequence slot occupancy before PSR
list_preset_pool            — SAFE_READ: check preset slot occupancy before PSR
check_pool_slot_availability — SAFE_READ: direct slot occupancy query (if available)
```

---

## 8-Step Migration Workflow

### Step 1 — Verify source show exists

```python
list_show_files()
# Confirm the source show file name appears in the list.
# Note the exact name — PSR is case-sensitive on some MA2 builds.
```

### Step 2 — Baseline current state

```python
hydrate_console_state()
# Records current counts for all pool types:
# sequences, presets, groups, effects, macros, views, worlds, filters.
# This snapshot is the diff target in step 7.
```

### Step 3 — Check slot occupancy for each pool type being imported

For every pool type in the migration plan, enumerate occupied slots:

```python
list_sequences()      # note which slots are occupied
list_preset_pool()    # note which preset slots are occupied
# (repeat for groups, effects, macros as needed)
```

Alternatively, if `check_pool_slot_availability` is available:

```python
check_pool_slot_availability(pool_type="sequence", slot_range="1 thru 50")
```

**Decision rule:**
- Occupied slots that overlap with the source range → use `target_slot` offset in step 5.
- Occupied slots that will NOT be touched → document them; no action needed.
- If all target slots are free → proceed to step 4.

### Step 4 — Assert showfile and save

```python
assert_showfile_unchanged()
# If this fails: STOP. A show switch occurred since the session began.
# Do not proceed until you understand what changed and why.

save_show(confirm_destructive=True)
# Protect the current show before any PSR operation.
```

### Step 5 — Execute PSR

```python
partial_show_read(
    show_name="SourceShowName",
    pool_type="sequence",
    source_range="1 thru 10",
    target_slot=200,           # omit if no offset needed
    confirm_destructive=True,
)
# Emits: PSR "SourceShowName" Sequence 1 Thru 10 At Sequence 200
# Repeat for each pool type in the migration plan.
```

If migrating multiple pool types, run `assert_showfile_unchanged()` between each
`partial_show_read` call. A console crash or accidental load between PSR calls would
corrupt the partially-migrated show.

### Step 6 — Verify imported content appeared

```python
list_sequences()
# Confirm expected objects are present at correct slot numbers.
# For a spot check, inspect one imported sequence:
list_cues(sequence_id=200)
```

### Step 7 — Diff against baseline

```python
diff_console_state()
# Compares current pool counts against the step 2 baseline.
# Returns delta: sequences_added, presets_added, groups_added, etc.
# If the delta does not match the expected import count — investigate before
# continuing.
```

### Step 8 — Verify fixture references in imported sequences

For each imported sequence, sample a cue and check fixture IDs:

```python
query_object_list(object_type="cue", sequence_id=200, cue_id=1)
# Returns the list of fixture IDs referenced by this cue.

list_fixtures()
# Returns all fixture IDs in the current patch.
```

Compare the two sets. Any fixture ID in the cue that is NOT in the current patch
is an **UNMATCHED_FIXTURE**. Flag it in the output (see format below). Do not
silently discard unmatched references.

---

## Output Format After Migration

Report the result of every migration session in this structure:

```json
{
  "migrated_pools": [
    "sequence: slots 1-10 from SourceShow → slots 200-209"
  ],
  "slot_conflicts_avoided": [
    "sequence slot 5 was occupied by 'ACT2_INTRO' — offset to slot 205 applied"
  ],
  "unmatched_fixtures": [
    "fixture_id 42 referenced in Sequence 200 Cue 3 — not in current patch"
  ],
  "state_diff": {
    "sequences_added": 10,
    "presets_added": 0
  },
  "recommended_actions": [
    "Remap fixture 42 to current rig equivalent before programming Sequence 200",
    "Verify Sequence 200 Cue 3 output visually on next rehearsal"
  ]
}
```

Always populate all four keys. Use empty arrays `[]` when there is nothing to report
for a field — do not omit the key.

---

## Safety Rules

- **Never PSR without checking slot occupancy first.** PSR silently overwrites any
  occupied slot with no warning and no undo. Step 3 is mandatory, not optional.
- **Always save before PSR.** If PSR overwrites something valuable and there is no
  saved version, the content is gone. Step 4 is mandatory.
- **Fixture ID mismatches are the norm, not the exception,** when migrating between
  shows built on different rigs. Step 8 exists precisely because this is easy to miss
  and hard to diagnose at rehearsal.
- **`assert_showfile_unchanged` must pass before any `partial_show_read` call.** If it
  fails, STOP and report. Do not attempt to continue the migration with an unknown
  show state.
- After migrating multiple pool types in sequence, verify the total diff (step 7) adds
  up. A miscount means one PSR silently failed or wrote to the wrong slots.
