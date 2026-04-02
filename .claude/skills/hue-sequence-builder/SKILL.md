---
title: Hue Sequence Builder
description: Worker instruction module for building a 16-cue grandMA2 sequence from an adjacent hue pair — 8 saturation variants per hue, color-coded with HSB appearance
version: 1.0.0
created: 2026-03-31T21:52:55Z
last_updated: 2026-03-31T21:52:55Z
---

# Hue Sequence Builder

**Worker charter:** DESTRUCTIVE — builds one 16-cue sequence from two adjacent hues
(8 saturation-descending cues each), assigns it to an executor, and labels both.

Invoke when asked to: build a hue pair sequence, create a saturation-gradient fader,
populate one of executors 202–207, or rebuild a specific hue group.

---

## The 6 Hue Pairs

| Pair | Hues | Seq ID | Executor |
|------|------|--------|----------|
| 0 | Red + Orange | 100 | 202 |
| 1 | Amber + Yellow | 101 | 203 |
| 2 | Lime + Green | 102 | 204 |
| 3 | Teal + Cyan | 103 | 205 |
| 4 | Azure + Blue | 104 | 206 |
| 5 | Violet + Magenta | 105 | 207 |

---

## Cue Structure (16 cues per sequence)

```
Cue  1–8:  Hue A — Full → Deep → Rich → Mid → Soft → Pale → Blush → Hint
Cue 9–16:  Hue B — Full → Deep → Rich → Mid → Soft → Pale → Blush → Hint
```

Go-stepping descends from punchy to pastel within the first hue, then repeats
the gradient for the second hue. An LD can move from saturated to washed-out
without breaking flow across a complementary color family.

---

## Preset Reference Map

Each cue references a universal preset from the 4.101–4.196 block.

| Cue | Preset | Name |
|-----|--------|------|
| 1 | 4.(101 + pair×16 + 0) | Hue A Full |
| 2 | 4.(101 + pair×16 + 1) | Hue A Deep |
| … | … | … |
| 8 | 4.(101 + pair×16 + 7) | Hue A Hint |
| 9 | 4.(101 + pair×16 + 8) | Hue B Full |
| … | … | … |
| 16 | 4.(101 + pair×16 + 15) | Hue B Hint |

---

## Allowed Tools

```
get_client (for SelFix, ClearAll),
apply_preset, store_current_cue, label_or_appearance,
assign_object, get_executor_status, query_object_list
```

DESTRUCTIVE tools: `store_current_cue`, `assign_object`, `label_or_appearance`.
All require `confirm_destructive=True`.

---

## Steps

### 1. Build 16 cues (SelFix → apply_preset → store → appearance → ClearAll)

```
cue_number = 1
for each preset_entry in [hue_a_slice(8) + hue_b_slice(8)]:
    a. SelFix:      send "SelFix 1 Thru 9999"
    b. Apply:       apply_preset(preset_type="color", preset_id=entry.id)
    c. Store cue:   store_current_cue(
                        cue_number=cue_number,
                        sequence_id=sequence_id,
                        label=entry.name,         # e.g. "Red Full"
                        overwrite=True,
                        confirm_destructive=True
                    )
    d. Appearance:  label_or_appearance(
                        action="appearance",
                        object_type="cue",
                        object_id=f"{cue_number} sequence {sequence_id}",
                        hue=entry.h,              # 0-360 — direct HSB, no conversion
                        saturation=entry.s,        # 0-100
                        brightness=entry.br,       # always 100
                        confirm_destructive=True
                    )
    e. Clear:       send "ClearAll"
    cue_number += 1
```

**Why HSB for appearance:** MA2's `/h= /s= /br=` appearance flags directly encode
the perceptual color. Using HSB avoids floating-point rounding artifacts that can
occur when RGB-converting near 0° or 360° hue boundaries. For all 96 presets in
this system, `entry.h`, `entry.s`, `entry.br` are exact integers — pass them as-is.

---

### 2. Label the sequence

```python
label_or_appearance(
    action="label", object_type="sequence",
    object_id=sequence_id,
    name=seq_label,          # e.g. "Red / Orange"
    confirm_destructive=True
)
```

---

### 3. Assign to executor

```python
assign_object(
    mode="assign",
    source_type="sequence", source_id=sequence_id,
    target_type="executor", target_id=executor_id,
    confirm_destructive=True,
)
```

Then verify with `get_executor_status(executor_id=executor_id)` and label the executor:

```python
label_or_appearance(
    action="label", object_type="executor",
    object_id=executor_id, name=seq_label,
    confirm_destructive=True,
)
```

---

### 4. Verify cue count

Call `query_object_list("cue", sequence_id=N)` and assert exactly 16 cues.

---

### 5. Compress findings

```json
{
  "summary": "Built 'Red / Orange' — 16 cues in Seq 100, Exec 202 confirmed",
  "findings": [],
  "cues_created": [...],
  "state_changes": [...],
  "confidence": "high"
}
```

---

## Safety Escalation

Before Step 1 print:
`"About to build 16 cues in Sequence N (Hue A / Hue B) → Executor E"`.
If `confirm_destructive` is not set → abort.
Never auto-set `confirm_destructive=True`.
