---
title: Command Builder Reference
description: Pure-function reference for all 198 grandMA2 command builders
version: 1.6.0
created: 2026-03-02T23:52:10Z
last_updated: 2026-03-31T23:56:48Z
---

# Command Builder Reference

> Back to [README](../README.md)

The command builder (`src/commands/`) generates grandMA2 command strings without any network I/O. All functions are pure and return `str`. There are **198 exported functions** (206 exports including 8 constants) covering navigation, selection, playback, values, store, delete, assign, label, info, park, call, variables, user management, and more.

grandMA2 syntax: `[Function] [Object]` — keywords are classified as **Function** (verbs), **Object** (nouns), or **Helping** (prepositions).

## Navigation (ChangeDest)

| Function | Output |
|----------|--------|
| `changedest("/")` | `cd /` |
| `changedest("..")` | `cd ..` |
| `changedest("5")` | `cd 5` |
| `changedest('"MySequence"')` | `cd "MySequence"` |
| `changedest("Group", 1)` | `cd Group.1` |
| `changedest("Preset", "4.1")` | `cd Preset.4.1` |
| `changedest("Group")` | `cd Group` |

## Object Keywords

| Function | Example | Output |
|----------|---------|--------|
| `fixture(34)` | Select by Fixture ID | `fixture 34` |
| `channel(11, sub_id=5)` | Select by Channel ID | `channel 11.5` |
| `group(3)` | Select a group | `group 3` |
| `preset("color", 5)` | Apply a preset | `preset 2.5` |
| `cue(5)` | Reference a cue | `cue 5` |
| `cue_part(5, 2)` | Reference a cue part | `cue 5 part 2` |
| `sequence(3)` | Reference a sequence | `sequence 3` |
| `executor(1)` | Reference an executor | `executor 1` |
| `dmx(101, universe=2)` | Reference DMX address | `dmx 2.101` |
| `dmx_universe(1)` | Reference DMX universe | `dmxuniverse 1` |
| `layout(1)` | Reference a layout | `layout 1` |
| `attribute("Pan")` | Reference an attribute | `attribute "Pan"` |
| `feature(1)` | Reference a feature | `feature 1` |
| `timecode(1)` | Reference a timecode show | `timecode 1` |
| `timer(1)` | Reference a timer | `timer 1` |

## Selection & Clear

| Function | Output |
|----------|--------|
| `select_fixture(1, 10)` | `selfix fixture 1 thru 10` |
| `select_fixture([1, 3, 5])` | `selfix fixture 1 + 3 + 5` |
| `clear()` | `clear` |
| `clear_selection()` | `clearselection` |
| `clear_active()` | `clearactive` |
| `clear_all()` | `clearall` |
| `fix_fixture(1)` | `fix fixture 1` |
| `fix_fixture(1, end=5)` | `fix fixture 1 thru 5` |
| `fix_fixture()` | `fix` |
| `locate()` | `locate` |
| `invert()` | `invert` |
| `align()` | `align` |

## Store

| Function | Output |
|----------|--------|
| `store("macro", 5)` | `store macro 5` |
| `store_cue(1, merge=True)` | `store cue 1 /merge` |
| `store_preset("dimmer", 3)` | `store preset 1.3` |
| `store_group(1)` | `store group 1` |

Store options: `merge`, `overwrite`, `remove`, `noconfirm`, `cueonly`, `tracking`, `source`, and more.

## Playback

| Function | Output |
|----------|--------|
| `go(executor_id=1)` | `go executor 1` |
| `go_back(executor_id=1)` | `goback executor 1` |
| `goto(cue_id=5)` | `goto cue 5` |
| `go_sequence(1)` | `go+ sequence 1` |
| `pause_sequence(1)` | `pause sequence 1` |
| `goto_cue(1, 5)` | `goto cue 5 sequence 1` |
| `go_fast_back()` | `<<<` |
| `go_fast_forward()` | `>>>` |
| `def_go_forward()` | `go+` |
| `def_go_back()` | `goback-` |
| `def_go_pause()` | `pause` |
| `swop_executor(3)` | `swop executor 3` |
| `swop_executor(3, page=2)` | `swop executor 2.3` |
| `top_executor(3)` | `top executor 3` |
| `stomp_executor(3)` | `stomp executor 3` |
| `load_next()` | `loadnext` |
| `load_next(executor=1)` | `loadnext executor 1` |
| `load_prev(sequence=2)` | `loadprev sequence 2` |

## At (Values)

`At` can function as both a Function Keyword and a Helping Keyword.

| Function | Output |
|----------|--------|
| `at(75)` | `at 75` |
| `at(cue=3)` | `at cue 3` |
| `at(fade=2)` | `at fade 2` |
| `at_full()` | `at full` |
| `at_zero()` | `at 0` |
| `attribute_at("Pan", 20)` | `attribute "Pan" at 20` |
| `fixture_at(2, 50)` | `fixture 2 at 50` |
| `fixture_at(2, source_fixture=3)` | `fixture 2 at fixture 3` |
| `channel_at(1, 75)` | `channel 1 at 75` |
| `group_at(3, 50)` | `group 3 at 50` |
| `executor_at(3, 50)` | `executor 3 at 50` |
| `preset_type_at(2, 50, end_type=9)` | `presettype 2 thru 9 at 50` |

## Copy, Move, Cut, Paste, Clone

| Function | Output |
|----------|--------|
| `copy("group", 1, 5)` | `copy group 1 at 5` |
| `copy("group", 1, end=3, target=11)` | `copy group 1 thru 3 at 11` |
| `copy_cue(2, 6)` | `copy cue 2 at 6` |
| `move("group", 5, 9)` | `move group 5 at 9` |
| `cut("preset", "4.1")` | `cut preset 4.1` |
| `paste("group", 5)` | `paste group 5` |
| `clone("sequence", 1, 5)` | `clone sequence 1 at 5` |
| `clone("sequence", 1, 5, noconfirm=True)` | `clone sequence 1 at 5 /noconfirm` |
| `clone("cue", [1,2], [3,4])` | `clone cue 1 + 2 at 3 + 4` |

Copy/Move/Clone options: `overwrite`, `merge`, `status`, `cueonly`, `noconfirm`

## Block & Unblock

| Function | Output |
|----------|--------|
| `block(3)` | `block cue 3` |
| `block(1, end=5)` | `block cue 1 thru 5` |
| `block(3, sequence_id=2)` | `block cue 3 sequence 2` |
| `unblock(3)` | `unblock cue 3` |
| `unblock(1, end=5, sequence_id=2)` | `unblock cue 1 thru 5 sequence 2` |

## Delete & Remove

| Function | Output |
|----------|--------|
| `delete("cue", 7)` | `delete cue 7` |
| `delete_cue(1, end=5, noconfirm=True)` | `delete cue 1 thru 5 /noconfirm` |
| `delete_group(3)` | `delete group 3` |
| `delete_preset("color", 5)` | `delete preset 4.5` |
| `delete_fixture(4)` | `delete fixture 4` |
| `delete_messages()` | `delete messages` |
| `remove("selection")` | `remove selection` |
| `remove_preset_type("position")` | `remove presettype "position"` |
| `remove_fixture(1, if_filter="PresetType 1")` | `remove fixture 1 if PresetType 1` |
| `remove_effect(1)` | `remove effect 1` |

## Assign

| Function | Output |
|----------|--------|
| `assign("sequence", 1, "executor", 6)` | `assign sequence 1 at executor 6` |
| `assign("dmx", "2.101", "channel", 5)` | `assign dmx 2.101 at channel 5` |
| `assign_function("Toggle", "executor", 101)` | `assign toggle at executor 101` |
| `assign_fade(3, 5)` | `assign fade 3 cue 5` |
| `assign_to_layout("group", 1, 1, x=5, y=2)` | `assign group 1 at layout 1 /x=5 /y=2` |
| `assign_property(1, "Telnet", "Login Disabled")` | `assign 1/Telnet="Login Disabled"` |
| `build_set_executor_priority(201, "high")` | `Assign Executor 201 /priority=high` |
| `empty("executor", 1)` | `empty executor 1` |
| `temp_fader("executor", 1)` | `temp_fader executor 1` |

## Label & Appearance

| Function | Output |
|----------|--------|
| `label("group", 3, "All Studiocolors")` | `label group 3 "All Studiocolors"` |
| `label_group(1, "Front")` | `label group 1 "Front"` |
| `label_preset("color", 1, "Red")` | `label preset 2.1 "Red"` |
| `appearance("preset", "0.1", red=100)` | `appearance preset 0.1 /r=100` |
| `appearance("group", 1, color="FF0000")` | `appearance group 1 /color=FF0000` |

## Info & List

| Function | Output |
|----------|--------|
| `list_objects("cue")` | `list cue` |
| `list_group()` | `list group` |
| `list_preset("color")` | `list preset 4` |
| `info("cue", 1)` | `info cue 1` |
| `info_group(3)` | `info group 3` |
| `list_plugin_library()` | `listpluginlibrary` |
| `list_fader_modules()` | `listfadermodules` |
| `list_update()` | `listupdate` |

## Park & Unpark

| Function | Output |
|----------|--------|
| `park("fixture", 1)` | `park fixture 1` |
| `park("dmx", 101, value=128)` | `park dmx 101 at 128` |
| `unpark("fixture", 1)` | `unpark fixture 1` |

## Call

| Function | Output |
|----------|--------|
| `call("preset", "2.1")` | `call preset 2.1` |
| `call("cue", 3, sequence=1)` | `call cue 3 sequence 1` |

## Variables

| Function | Output |
|----------|--------|
| `set_var("myvar", 42)` | `setvar "myvar" 42` |
| `set_user_var("speed", 100)` | `setuservar "speed" 100` |
| `add_var("counter", 1)` | `addvar "counter" 1` |
| `add_user_var("counter", 1)` | `adduservar "counter" 1` |

## Helping Keywords

| Function | Output |
|----------|--------|
| `at_relative(10)` | `+ 10` |
| `at_relative(-5)` | `- 5` |
| `add_to_selection("fixture", 5)` | `+ fixture 5` |
| `remove_from_selection("fixture", 3)` | `- fixture 3` |
| `page_next()` | `page +` |
| `page_previous()` | `page -` |
| `condition_and("group", 1)` | `and group 1` |
| `if_condition("PresetType", 1)` | `if PresetType 1` |

## Macro Placeholder (@)

The `@` character is a placeholder for user input in macros (distinct from the `At` keyword).

| Function | Output |
|----------|--------|
| `macro_with_input_after("Load")` | `Load @` |
| `macro_with_input_before("Fade 20")` | `@ Fade 20` |

## User Management

Requires Admin (rights=5) Telnet session. Part of the dual-enforcement authorization architecture.

| Function | Output |
|----------|--------|
| `build_login("operator", "pw123")` | `Login "operator" "pw123"` |
| `build_logout()` | `Logout` |
| `build_list_users()` | `list user` |
| `build_store_user(2, "operator", "pw", 1)` | `Store User 2 /name="operator" /password="pw" /rights=1` |
| `build_store_user(5, "guest", "", 0)` | `Store User 5 /name="guest" /password="" /rights=0` |
| `build_delete_user(3)` | `Delete User 3 /noconfirm` |
| `build_assign_world_to_user_profile(3, 4)` | `Assign World 4 At UserProfile 3` |
| `build_assign_world_to_user_profile(3, 0)` | `Assign World 0 At UserProfile 3` |

Rights levels: 0=None, 1=Playback, 2=Presets, 3=Program, 4=Setup, 5=Admin

## MA2 Native Rights

`MA2Right` and `MA2RIGHT_TO_OAUTH_SCOPE` are exported from `src/commands/constants.py`.

| MA2Right | Value | OAuth Scope | OAuth Tier |
|----------|-------|-------------|------------|
| `MA2Right.NONE` | `"none"` | `gma2:state:read` | 0 |
| `MA2Right.PLAYBACK` | `"playback"` | `gma2:playback:go` | 1 |
| `MA2Right.PRESETS` | `"presets"` | `gma2:programmer:write` | 2 |
| `MA2Right.PROGRAM` | `"program"` | `gma2:cue:store` | 3 |
| `MA2Right.SETUP` | `"setup"` | `gma2:setup:console` | 4 |
| `MA2Right.ADMIN` | `"admin"` | `gma2:user:manage` | 5 |

Use `@require_ma2_right(MA2Right.X)` in `src/server.py` as a human-readable alternative to `@require_scope(OAuthScope.Y)`. The full 176-tool rights assignment is in `doc/ma2-rights-matrix.json`.
