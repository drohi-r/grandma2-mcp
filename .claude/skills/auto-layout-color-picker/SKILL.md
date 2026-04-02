---
title: Auto Layout Color Picker
description: Instruction module for using the grandMA2 auto-layout color picker plugin — reserve pool ranges, verify groups and images, and run the plugin safely for fast color-access layouts
version: 1.0.0
created: 2026-04-02T05:05:00Z
last_updated: 2026-04-02T05:05:00Z
---

# Auto Layout Color Picker

**Worker charter:** DESTRUCTIVE once the plugin is run. Use this skill to prepare, validate, and execute the **auto-layout** color picker workflow only. Do **not** run `HighLowFX` as part of this skill.

Use when asked to: set up a color picker quickly, build a color layout from groups, run the Egidius/leonreucher auto-layout color picker plugin, or validate the pool ranges before using that plugin.

This skill assumes the plugin is already available on the MA2 system or in the show environment. It does not assume a fixed plugin slot number.

Upstream reference: `egidiusmengelberg/grandma2_colorpicker_plugin` auto-layout branch/fork workflow. Preserve attribution if you export or redistribute plugin files.

---

## What This Skill Is For

The auto-layout color picker variant:

- builds the layout view automatically
- assigns images automatically
- creates the macro/sequence structure needed for color access
- **does not include the original HighLowFX workflow**

This skill is for **quick operational setup**, not for re-authoring the plugin code.

---

## Phase 0 — Preflight Survey (SAFE_READ, always first)

Run these before touching any pool ranges:

```python
hydrate_console_state()
list_fixtures()
list_groups()
list_layouts()
list_images()
list_macro_library()
query_object_list(object_type="sequence")
check_pool_slot_availability(object_type="macro", start_id=mac_start, end_id=mac_end)
check_pool_slot_availability(object_type="sequence", start_id=seq_start, end_id=seq_end)
check_pool_slot_availability(object_type="image", start_id=img_start, end_id=img_end)
```

Confirm with operator:

- target groups exist and contain the intended fixtures
- the plugin's macro range is free
- the plugin's sequence range is free
- the target layout slot is free or intentionally disposable
- the image pool range is free enough for copies
- the target page/fader range is acceptable

If any of these are unclear, stop and ask before running the plugin.

---

## Required Plugin Inputs

The auto-layout workflow depends on the same core configuration concepts as the upstream plugin:

- `grpNum`: group pool items used by the color picker
- `macStart`: first macro slot to populate
- `seqStart`: first sequence slot to populate
- `startingPage`: page used for the backing sequences
- `startingFader`: first executor/fader used on that page
- `layoutView`: target layout pool item
- `spacing`: spacing between layout elements
- `imgStart`: first image slot used for copied color images
- `allImgStart`: image slot range for the `All` buttons
- `filledImages`: filled icon pool list
- `unfilledImages`: unfilled icon pool list

Default color order from the upstream plugin:

`White, Red, Orange, Yellow, Green, Seagreen, Cyan, Blue, Lavender, Violet, Magenta, Pink`

Do not silently change the color order unless the operator explicitly wants a custom picker.

---

## Phase 1 — Validate Group Strategy

The skill works best when groups are:

- fixture-type coherent
- color-capable
- already labeled clearly
- safe to trigger together

Good examples:

- `All Wash`
- `All Spot`
- `All Beam`
- `Stage Wash`
- `Audience Blinders`

Bad candidates:

- groups that mix incompatible color systems without intent
- utility groups used for programming only
- temporary troubleshooting groups

Use:

```python
list_groups()
query_object_list(object_type="group")
```

If the rig is not grouped well yet, use `patch-and-group-builder` or `busking-template-generator` first.

---

## Phase 2 — Reserve and Sanity-Check Pool Ranges

Before running the plugin, explicitly reserve the intended ranges on paper/in chat:

- macro slots
- sequence slots
- executor page/fader span
- layout slot
- image slots

Recommended operator confirmation:

> "I will use groups [..], macros [..], sequences [..], layout [..], images [..], page [..], faders [..]. This may overwrite existing picker assets in those ranges. Proceed?"

If any range overlaps active show content, do not continue until a new range is chosen.

---

## Phase 3 — Plugin Execution

If the plugin is already installed and the slot is known, use the plugin execution tools only after the preflight above passes.

Typical options:

```python
reload_all_plugins()
call_plugin_tool(plugin_id=<slot>)
```

If direct plugin invocation is not reliable in the current environment, fall back to operator-guided manual execution on the console while this skill acts as the checklist and validator.

Do not invent plugin arguments or slot IDs. Use the installed plugin's real configuration and execution path.

---

## Phase 4 — Post-Run Verification

Immediately verify the results:

```python
list_layouts()
list_images()
list_macro_library()
query_object_list(object_type="sequence")
scan_page_executor_layout(page=starting_page)
get_page_map(page=starting_page)
```

Check specifically:

- layout pool item exists
- layout elements have the expected color/icon population
- macros were created in the expected range
- sequences were created in the expected range
- executor assignments landed on the intended page/faders
- no obvious collisions occurred with unrelated show content

If anything looks off, stop and inspect before trying to rerun the plugin into the same ranges.

---

## When To Use This Skill vs Other Skills

- Use **this skill** when the goal is a fast color picker surface using the installed auto-layout plugin.
- Use `song-macro-page-design` when the goal is song-page first-button architecture.
- Use `busking-template-generator` when the rig needs a full busk scaffold, not just color access.
- Use `companion-integration` if the final target is Stream Deck / Companion mirroring.

---

## Allowed Tools

```text
SAFE_READ: hydrate_console_state, list_fixtures, list_groups, list_layouts,
           list_images, list_macro_library, query_object_list,
           check_pool_slot_availability, scan_page_executor_layout, get_page_map

DESTRUCTIVE / LIVE ACTION: reload_all_plugins, call_plugin_tool
```

Treat plugin execution as destructive showfile mutation even if the command itself is a single plugin call.
