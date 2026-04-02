---
title: Fixture Swap Surgeon
description: Plan and execute fixture type swaps with compatibility analysis and preset migration
version: 1.0.0
safety_scope: DESTRUCTIVE
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T00:00:00Z
---

# Fixture Swap Surgeon

## Charter

DESTRUCTIVE skill — the analysis phase is SAFE_READ, but the actual swap involves patching, cloning, and preset updates. Requires operator confirmation at each destructive step.

## Invocation

Use when touring to a new venue where the house rig has different fixtures than the show was programmed for (e.g., replacing Mac 700 Profile with Mac Viper).

## Workflow

### Phase 1: Compatibility Analysis (SAFE_READ)

1. Call `plan_fixture_swap(old_fixture_type="Mac 700 Profile", new_fixture_type="Mac Viper")`
2. Review the compatibility report:
   - **compatible_attributes**: These transfer cleanly (dimmer, pan, tilt, etc.)
   - **missing_in_new**: Attributes the new fixture doesn't have — presets using these will break
   - **new_only_attributes**: New fixture capabilities not used in the current show
   - **compatibility_percent**: Quick go/no-go indicator
3. Call `find_preset_usages` for any preset types that use missing attributes

### Phase 2: Pre-Swap Backup (SAFE_WRITE)

**OPERATOR CONFIRMATION REQUIRED**

1. Save the show: `save_show`
2. Export affected presets using `export_objects` for backup
3. Document the current patch with `list_fixtures`

### Phase 3: Execute Swap (DESTRUCTIVE)

**OPERATOR CONFIRMATION REQUIRED**

1. Import the new fixture type if needed: `import_fixture_type`
2. Use Clone to transfer data: `Clone Fixture {old_start} Thru {old_end} At Fixture {new_start} Thru {new_end}`
3. Update the patch: `patch_fixture` to assign new fixtures to the correct DMX addresses
4. Unpatch old fixtures: `unpatch_fixture`

### Phase 4: Verify (SAFE_READ)

1. Call `validate_preset_references` on all sequences that used the old fixtures
2. Call `diff_cues` on key cues to verify they look correct
3. Walk through the cue list visually with `cue-to-cue-rehearsal` skill
4. Check busking page still works with `audit_page_consistency`

### Phase 5: Handle Missing Attributes

For each missing attribute:
1. Identify which presets used it
2. Either: recreate the look using available attributes on the new fixture
3. Or: accept the loss and update affected cues to remove the reference

## Allowed Tools

**SAFE_READ:** `plan_fixture_swap`, `find_preset_usages`, `validate_preset_references`, `diff_cues`, `audit_page_consistency`, `list_fixtures`

**DESTRUCTIVE:** `import_fixture_type`, `patch_fixture`, `unpatch_fixture`, `clone_object`, `export_objects`, `save_show`
