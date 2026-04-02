---
title: "CD Tree \u2194 MCP Tool Correlation Matrix"
description: Maps every MCP tool to its grandMA2 console object tree branch for navigation-based verification
version: 3.1.0
created: 2026-03-08T23:31:47Z
last_updated: 2026-03-31T23:56:48Z
---

# CD Tree \u2194 MCP Tool Correlation Matrix

## Purpose

This document maps every MCP tool to the grandMA2 console object tree branch
it operates on. Use this to know which `cd` + `list` path to inspect when
verifying that an MCP tool actually created/modified/deleted the expected object.

## Quick Reference: 176 MCP Tools → Tree Branches (143 interactive + 33 agentic)

### Navigation & Inspection Tools (6)

| MCP Tool | Tree Branch | cd Command | Purpose |
|----------|------------|------------|---------|
| `navigate_console` | Any | `cd [destination]` | Navigate to any tree branch |
| `get_console_location` | Any | _(empty line)_ | Query current location |
| `list_console_destination` | Any | `list` | Enumerate children at current cd |
| `scan_console_indexes` | Any | `cd N` \u2192 `list` \u2192 `cd /` (loop) | Sequential index discovery |
| `set_node_property` | Any | `cd [path]` \u2192 `assign N/prop=val` | Set property on tree node |
| `get_object_info` | Any | `info [type] [id]` | Query object metadata |

### Object-Creating/Modifying Tools (13)

| MCP Tool | Tree Branch | cd + list Verification | MA Command |
|----------|------------|----------------------|------------|
| `create_fixture_group` | `cd Group` | `cd Group` \u2192 `list` \u2192 check group ID appears | `SelFix N Thru M; Store Group X` |
| `store_current_cue` | `cd Sequence.N` | `cd Sequence.N` \u2192 `list` \u2192 check cue ID appears | `Store Cue N [Sequence X]` |
| `store_new_preset` | `cd PresetType.N` | `cd PresetType.N` \u2192 `list` \u2192 check preset ID | `Store Preset T.N` |
| `store_object` | _varies_ | `cd [type]` \u2192 `list` \u2192 check object ID | `Store [Type] N` |
| `assign_object(assign)` | `cd Executor` | `cd Executor` \u2192 `list` \u2192 check executor has source | `Assign [Src] At [Tgt]` |
| `assign_object(layout)` | `cd Layout` | `cd Layout.N` \u2192 `list` \u2192 check object placed | `Assign [Src] At Layout N` |
| `assign_object(function)` | `cd Executor` | `cd Executor` \u2192 `list` \u2192 check function set | `Assign [Func] Executor N` |
| `assign_object(fade)` | `cd Sequence.N` | `cd Sequence.N` \u2192 `list` \u2192 check fade time | `Assign Fade T Cue N` |
| `assign_object(empty)` | `cd Executor` | `cd Executor` \u2192 `list` \u2192 executor cleared | `Assign Empty Executor N` |
| `label_or_appearance` | _varies_ | `cd [type]` \u2192 `list` \u2192 check name/appearance | `Label [Type] N "Name"` |
| `copy_or_move_object` | _varies_ | `cd [type]` \u2192 `list` \u2192 check target ID | `Copy/Move [Type] N At M` |
| `edit_object` | _varies_ | N/A (opens editor) | `Edit/Cut/Paste [Type] N` |
| `set_intensity` | `cd Fixture`/`cd Channel` | Programmer state (not persistent in tree) | `Fixture N At L` |

### Object-Deleting Tools (2)

| MCP Tool | Tree Branch | cd + list Verification | MA Command |
|----------|------------|----------------------|------------|
| `delete_object` | _varies_ | `cd [type]` \u2192 `list` \u2192 confirm ID is gone | `Delete [Type] N /noconfirm` |
| `remove_content` | _varies_ | `cd [parent]` \u2192 `list` \u2192 confirm content removed | `Remove [Type] N` |

### Playback & Control Tools (5)

| MCP Tool | Tree Branch | cd + list Verification | MA Command |
|----------|------------|----------------------|------------|
| `execute_sequence` | `cd Sequence` | N/A (playback state, not tree) | `Go+ Sequence N` |
| `playback_action` | `cd Executor` | N/A (playback state) | `Go/GoBack/Goto` |
| `run_macro` | `cd Macro` | N/A (triggers execution) | `Go+ Macro N` |
| `apply_preset` | `cd PresetType.N` | Programmer state | `Call Preset T.N` |
| `set_attribute` | `cd Fixture` | Programmer state | `Attribute "X" At V` |

### Utility Tools (3)

| MCP Tool | Tree Branch | Notes |
|----------|------------|-------|
| `clear_programmer` | Programmer | Clears selection/values, no tree change |
| `park_fixture` / `unpark_fixture` | `cd Fixture` | Parks/unparks output values |
| `manage_variable` | N/A | Variables are not in the cd tree |
| `send_raw_command` | Any | Depends on the raw command sent |
| `search_codebase` | N/A | RAG search, no console interaction |

### Import/Export Tools (2)

| MCP Tool | Tree Branch | MA Command | Purpose |
|----------|------------|------------|---------|
| `export_objects` | _varies_ | `Export [Type] [Range] "file"` | Export show objects to XML file |
| `import_objects` | _varies_ | `Import [Type] "file" At [id]` | Import objects from XML file |

### Highlight & Blackout Tools (2)

| MCP Tool | Tree Branch | MA Command | Purpose |
|----------|------------|------------|---------|
| `highlight_fixtures` | Programmer | `Highlight On/Off` | Toggle highlight mode for selected fixtures |
| `blackout_toggle` | Global | `Blackout` | Toggle master blackout |

### Executor & Playback Tools (4)

| MCP Tool | Tree Branch | cd + list Verification | MA Command |
|----------|------------|----------------------|------------|
| `release_executor` | `cd Executor` | N/A (playback state) | `Release Executor N` |
| `get_executor_state` | `List Executor page.id` | Returns 32 KEY=VALUE fields | `List Executor 1.N` |
| `scan_page_executor_layout` | `List Executor page.id` (range) | Occupancy map + free slots | `List Executor 1.N` (per slot) |
| `discover_fixture_type_attributes` | `cd EditSetup → FixtureTypes → N → 1 → 1` | ChannelType rows with attribute names | `cd EditSetup; cd FixtureTypes; cd N; cd 1; cd 1; list` |

### Show Management Tools (2)

| MCP Tool | Tree Branch | MA Command | Risk |
|----------|------------|------------|------|
| `load_show` | N/A | `LoadShow "name"` | DESTRUCTIVE — replaces current show |
| `new_show` | N/A | `NewShow "name"` | DESTRUCTIVE — replaces current show |

### Variable & History Tools (2)

| MCP Tool | Tree Branch | MA Command | Purpose |
|----------|------------|------------|---------|
| `get_variable` | N/A | `GetUserVar`, `ListVar`, `ListUserVar` | Read variables (complement to `manage_variable`) |
| `list_undo_history` | N/A | `ListOops` | Show undo history |

### List & Library Tools (2)

| MCP Tool | Tree Branch | MA Command | Purpose |
|----------|------------|------------|---------|
| `list_shows` | N/A | `ListShows` | List available show files |
| `list_library` | N/A | `ListLibrary`, `ListEffectLibrary`, `ListMacroLibrary` | Browse fixture/effect/macro libraries |

### LiveSetup Navigation Tools (3)

| MCP Tool | Tree Branch | cd Path | Purpose |
|----------|------------|---------|---------|
| `list_fixture_types` | `cd 10.3` | `cd /` → `cd 10` → `cd 3` → `list` | List all fixture types in the show |
| `list_layers` | `cd 10.4` | `cd /` → `cd 10` → `cd 4` → `list` | List all fixture layers |
| `list_universes` | `cd 10.5` | `cd /` → `cd 10` → `cd 5` → `list` | List DMX universes |

### MAtricks Tools (2)

| MCP Tool | Tree Branch | cd Path | Purpose |
|----------|------------|---------|---------|
| `manage_matricks` | `cd MAtricks` | `set_property("MAtricks", ...)` | Configure MAtricks selection patterns |
| `create_matricks_library` | `cd MAtricks` | Store + assign + label loop | Generate combinatorial MAtricks pool (**DESTRUCTIVE**) |

### Fixture Patching Tools (4)

| MCP Tool | Tree Branch | cd Path | MA Command | Risk |
|----------|------------|---------|------------|------|
| `browse_patch_schedule` | `cd 10.3.N` | `cd /` → `cd 10` → `cd 3` → `cd N` → `list` | Navigation + list | SAFE_READ |
| `patch_fixture` | `cd Fixture` | N/A | `Assign FixtureType At Fixture; Assign DMX At Fixture` | DESTRUCTIVE |
| `unpatch_fixture` | `cd Fixture` | N/A | `Delete Fixture N` | DESTRUCTIVE |
| `set_fixture_type_property` | `cd 10.3.N` | `set_property("10.3.N", ...)` | `cd` + `assign N/prop=val` | DESTRUCTIVE |

## Object Tree Branches (53 navigable via cd)

### Core Show Objects (most commonly used)

| Branch | cd Keyword | Create Tools | Delete Tools | Query Tools |
|--------|-----------|--------------|--------------|-------------|
| **Groups** | `cd Group` | `create_fixture_group` | `delete_object("group")` | `query_object_list("group")`, `list_console_destination` |
| **Sequences** | `cd Sequence` | `store_object("sequence")` | `delete_object("sequence")` | `query_object_list("sequence")`, `list_console_destination` |
| **Cues** | `cd Sequence.N` | `store_current_cue` | `delete_object("cue")` | `query_object_list("cue")`, `list_console_destination` |
| **Presets** | `cd Preset`, `cd PresetType.N`, `cd 17.1.N` | `store_new_preset` | `delete_object("preset")` | `query_object_list("preset")`, `list_preset_pool`, `list_console_destination` |
| **Macros** | `cd Macro` | `store_object("macro")` | `delete_object("macro")` | `query_object_list`, `list_console_destination` |
| **Effects** | `cd Effect` | `store_object("effect")` | `delete_object("effect")` | `query_object_list`, `list_console_destination` |
| **Executors** | `cd Executor` | `assign_object(assign)` | `assign_object(empty)` | `list_console_destination` |
| **Layouts** | `cd Layout` | `assign_object(layout)` | `delete_object("layout")` | `list_console_destination` |
| **Fixtures** | `cd Fixture` | `patch_fixture` | `delete_object("fixture")`, `unpatch_fixture` | `query_object_list`, `list_console_destination` |
| **Channels** | `cd Channel` | _(patched externally)_ | \u2014 | `list_console_destination` |

### Page Context

| Branch | cd Keyword | Related Tools |
|--------|-----------|---------------|
| **Pages** | `cd Page` | `playback_action` (page context) |
| **Fader Pages** | `cd FaderPage` | `playback_action` |
| **Button Pages** | `cd ButtonPage` | `playback_action` |

### Configuration & System Objects

| Branch | cd Keyword | Related Tools |
|--------|-----------|---------------|
| **Filters** | `cd Filter` | `store_object("filter")` |
| **Worlds** | `cd World` | `store_object("world")` |
| **Timecodes** | `cd Timecode` | `store_object("timecode")` |
| **Timers** | `cd Timer` | `store_object("timer")` |
| **Users** | `cd User` | Read-only via `list` |
| **User Profiles** | `cd UserProfile` | Read-only via `list` |
| **DMX** | `cd Dmx`, `cd DmxUniverse`, `cd 10.5` | `park_fixture`/`unpark_fixture`, `list_universes` |
| **Fixture Types** | `cd FixtureType`, `cd 10.3` | `list_fixture_types`, `browse_patch_schedule`, `set_fixture_type_property` |
| **Attributes** | `cd Attribute` | `set_attribute`, `query_object_list("attribute")` |
| **Features** | `cd Feature` | Read-only via `list` |

### UI & Display Objects

| Branch | cd Keyword | Related Tools |
|--------|-----------|---------------|
| **Views** | `cd View`, `cd ViewButton`, `cd ViewPage` | Read-only |
| **Screens** | `cd Screen` | Read-only |
| **Cameras** | `cd Camera` | Read-only |
| **Forms** | `cd Form` | Read-only |
| **Images** | `cd Image` | Read-only |
| **Gel** | `cd Gel` | Read-only |

### Remaining Navigable Branches (no direct MCP tool)

`Agenda`, `ChannelFader`, `Cue`, `Default`, `ExecButton1-3`, `Fader`,
`Mask`, `MAtricks`, `Part`, `PreviewExecutor`, `Programmer`, `Remote`,
`Root`, `RdmFixtureType`, `Selection`, `SoundChannel`, `SpecialMaster`,
`Messages`

### LiveSetup Tree (cd 10) — Deep Navigation

The LiveSetup branch is accessed via numeric index `cd 10` and supports
deep dot-separated paths up to depth 8+.

| Index Path | Node | MCP Tools |
|------------|------|-----------|
| `10` | LiveSetup | _(parent)_ |
| `10.1` | DMX_Profiles | — |
| `10.2` | PresetTypes (9 types: Dimmer-Video) | `browse_preset_type` |
| `10.2.N` | PresetType N — lists Features | `browse_preset_type(depth=1)` |
| `10.2.N.M` | Feature M under PresetType N — lists Attributes | `browse_preset_type(depth=2)` |
| `10.2.N.M.K` | Attribute K — lists SubAttributes | `browse_preset_type(depth=3)` |
| `10.2.N.M.K.L` | SubAttribute L — **leaf** (NO OBJECTS FOUND) | — |
| `10.3` | FixtureTypes | `list_fixture_types` |
| `10.3.N` | Fixture Type N | `browse_patch_schedule`, `set_fixture_type_property` |
| `10.4` | Layers | `list_layers` |
| `10.5` | Universes | `list_universes` |
| `10.6` | Objects3D | — |

## Verification Pattern

For every object-creating or object-deleting MCP tool, use this 3-step cycle:

```
1. navigate_console(destination="[branch]")
   list_console_destination()                  # BEFORE state

2. <execute MCP tool>                           # create / modify / delete

3. navigate_console(destination="[branch]")
   list_console_destination()                  # AFTER state
   # Compare entries \u2192 validate object appeared/disappeared
```

## Phase 2 Test Matrix (8 Core Branches)

| # | Branch | MCP Tool Call | Expected MA Command | Verify |
|---|--------|-------------|---------------------|--------|
| 1 | `Group` | `create_fixture_group(1, 10, 99, "Test")` | `SelFix 1 Thru 10; Store Group 99` | `cd Group` \u2192 Group 99 appears |
| 2 | `Group` | `delete_object("group", 99, confirm_destructive=True)` | `Delete Group 99 /noconfirm` | `cd Group` \u2192 Group 99 gone |
| 3 | `Sequence` | `store_object("sequence", 99, confirm_destructive=True)` | `Store Sequence 99` | `cd Sequence` \u2192 Seq 99 appears |
| 4 | `Sequence.99` | `store_current_cue(1, sequence_id=99)` | `Store Cue 1 Sequence 99` | `cd Sequence.99` \u2192 Cue 1 appears |
| 5 | `PresetType.4` | `store_new_preset("color", 99)` | `Store Preset 4.99` | `cd PresetType.4` \u2192 Preset 99 appears |
| 6 | `Macro` | `store_object("macro", 99, confirm_destructive=True)` | `Store Macro 99` | `cd Macro` \u2192 Macro 99 appears |
| 7 | `Executor` | `assign_object(mode="assign", ...)` | `Assign Seq 99 At Exec 201` | `cd Executor` \u2192 Exec 201 has seq |
| 8 | `Effect` | `store_object("effect", 99, confirm_destructive=True)` | `Store Effect 99` | `cd Effect` \u2192 Effect 99 appears |

### Cleanup Sequence

```
delete_object("group", 99, confirm_destructive=True)
delete_object("cue", 1, confirm_destructive=True)        # in sequence 99
delete_object("sequence", 99, confirm_destructive=True)
delete_object("preset", "4.99", confirm_destructive=True)
delete_object("macro", 99, confirm_destructive=True)
assign_object(mode="empty", target_type="executor", target_id=201, confirm_destructive=True)
delete_object("effect", 99, confirm_destructive=True)
```

## Tool Count Summary

| Category | Count | Tools |
|----------|-------|-------|
| Navigation & Inspection | 6 | `navigate_console`, `get_console_location`, `list_console_destination`, `scan_console_indexes`, `set_node_property`, `get_object_info` |
| Object Create/Modify | 15 | `create_fixture_group`, `store_current_cue`, `store_new_preset`, `store_object`, `assign_object` (5 modes), `label_or_appearance`, `copy_or_move_object`, `edit_object`, `set_intensity`, `clone_object`, `block_unblock_cue` |
| Object Delete | 2 | `delete_object`, `remove_content` |
| Playback & Control | 11 | `execute_sequence`, `playback_action`, `run_macro`, `apply_preset`, `set_attribute`, `release_executor`, `blackout_toggle`, `control_executor`, `load_cue`, `cut_paste_object`, `fix_locate_fixture` |
| Executor Inspection | 3 | `get_executor_state`, `scan_page_executor_layout`, `discover_fixture_type_attributes` |
| Import/Export | 2 | `export_objects`, `import_objects` |
| Highlight & Selection | 3 | `highlight_fixtures`, `modify_selection`, `manipulate_selection` |
| Show Management | 2 | `load_show`, `new_show` |
| Variable & History | 2 | `get_variable`, `list_undo_history` |
| List & Library | 2 | `list_shows`, `list_library` |
| LiveSetup Navigation | 3 | `list_fixture_types`, `list_layers`, `list_universes` |
| MAtricks | 3 | `manage_matricks`, `create_matricks_library`, `store_matricks_preset` |
| Filter Library | 2 | `create_filter_library`, `discover_filter_attributes` |
| Fixture Patching | 4 | `browse_patch_schedule`, `patch_fixture`, `unpatch_fixture`, `set_fixture_type_property` |
| User Management | 4 | `list_console_users`, `create_console_user`, `assign_world_to_user_profile`, `inspect_sessions` |
| Utility | 5 | `clear_programmer`, `park_fixture`/`unpark_fixture`, `manage_variable`, `send_raw_command`, `search_codebase` |
| **Total** | **89** | *(54 additional interactive tools + 33 agentic tools [110-143] not mapped to cd tree branches)* |
