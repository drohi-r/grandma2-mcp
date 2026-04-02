---
title: View and Layout Designer
description: Instruction module for creating and managing grandMA2 custom views, console layouts, and button assignments — executor button placement, view saving/recall, and image library usage
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-01T00:00:00Z
---

# View and Layout Designer

**Worker charter:** DESTRUCTIVE (creating layouts modifies show data). Read phase uses SAFE_READ tools only. All write operations require `confirm_destructive=True`.

Invoke when asked to: create a custom view, design a fixture layout, place executor buttons on a layout canvas, assign images to buttons, or save and recall screen arrangements.

---

## Allowed Tools

```
SAFE_READ:
  list_layouts, list_images, save_recall_view (action="recall")

DESTRUCTIVE:
  store_object (view/layout), assign_to_layout, label_or_appearance,
  save_recall_view (action="save")
```

---

## Core Concepts

- **View**: A saved arrangement of MA2 screen windows (cue sheet, fixture sheet, executor sheet, etc). Saved in the View pool (up to 999 views). Views are per-show — they are lost if a different show is loaded without PSR (Partial Show Read).
- **Layout**: A custom visual representation of the rig — fixtures or buttons arranged on a 2D canvas. Used for busking, fixture selection, and monitoring.
- **Executor Sheet**: A layout showing executor buttons. Customizable per page.

---

## Steps: Save a View

1. **Arrange the screen** — the operator must have the desired window layout visible on the console before storing.

2. **Store the view**:

```
store_object(
    object_type="view",
    object_id=<N>,
    confirm_destructive=True
)
```

Use slot numbers that do not already contain views you want to keep. Verify with `list_layouts()` first.

3. **Label the view**:

```
label_or_appearance(
    object_type="view",
    object_id=<N>,
    label="<descriptive name>",
    confirm_destructive=True
)
```

4. **Verify**: call `list_layouts()` and confirm the view appears with the correct label.

---

## Steps: Recall a View

```
save_recall_view(view_id=<N>, action="recall")
```

This is SAFE_READ — no show data is modified.

---

## Steps: Create a Fixture Layout for Busking

1. **Determine fixture placement** — gather fixture IDs and their physical positions on stage (left/center/right, front/back). Map these to x/y coordinates on the layout canvas.

2. **Place each fixture**:

```
assign_to_layout(
    layout_id=<N>,
    object_type="fixture",
    fixture_id=<fixture_id>,
    x_pos=<x>,
    y_pos=<y>,
    confirm_destructive=True
)
```

3. **Label the layout**:

```
label_or_appearance(
    object_type="layout",
    object_id=<N>,
    label="<venue name> Stage Overview",
    confirm_destructive=True
)
```

4. **Verify**: call `list_layouts()` to confirm the layout is present.

---

## Steps: Add an Executor Button to a Layout

```
assign_to_layout(
    layout_id=<N>,
    object_type="executor",
    object_id="<page>.<executor>",
    x_pos=<x>,
    y_pos=<y>,
    confirm_destructive=True
)
```

Example: executor 5 on page 1 → `object_id="1.5"`.

---

## Steps: Assign an Image to a Button

1. **List available images** — call `list_images()` to see available images in the MA2 library. Verify the target image exists before assigning.

2. **Assign the image**:

```
label_or_appearance(
    object_type="executor",
    object_id="<page>.<executor>",
    label="<name>",
    image_id=<N>,
    confirm_destructive=True
)
```

Images are JPG or PNG files from the MA2 image library. They cannot be uploaded via Telnet — they must be present in the console's image directory before assignment.

---

## Screen Window Types (for view design)

Recommended windows to include in a live-operation view:

- **Sequence Sheet (Cue Sheet)**: most critical — always include for live operation
- **Executor Sheet**: shows running executors and fader states
- **Command Line**: always visible
- **Pool windows** (Group, Preset, Sequence pools): for touch-based busking

Additional windows for programming sessions:

- **Fixture Sheet**: attribute values per fixture
- **Patch Sheet**: fixture patch and ID assignments
- **Effect Sheet**: running effect states

---

## Best Practices for Busking Layouts

- One layout per venue type (club, theater, festival stage)
- Group fixtures spatially: left / center / right, front / back
- Use distinct colors for fixture types: wash=blue, spot=white, beam=yellow, strobe=red
- Keep the most-used groups in the top-left of the layout (fastest to tap)
- Keep the layout to a single screen of buttons — avoid scrolling during live performance
- Name layouts with venue and date: `"Club Main 2026"` not `"Layout 1"`

---

## Recompute Rule

Store a `DecisionCheckpoint` after listing existing layouts:

```json
{
  "fault": "layout_inventory",
  "query": "list_layouts",
  "observed_at": "<timestamp>",
  "fresh_for_seconds": 60,
  "replay": "list_layouts"
}
```

Layout inventory changes only when a DESTRUCTIVE operation runs. A 60-second cache is safe during a design session.

---

## Safety

- Layout modifications change show data — always save show before major layout redesign.
- Views are saved per show file — they are lost if you load a different show without PSR.
- Image assignments require the image to exist in the MA2 library. Verify with `list_images()` before assigning; assigning a non-existent image ID produces a silent failure.
- Overwriting an existing view slot is non-reversible. Use `list_layouts()` to confirm the target slot is free or intentionally being replaced.
