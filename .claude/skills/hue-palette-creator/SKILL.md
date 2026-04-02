---
title: Hue Palette Creator
description: Worker instruction module for storing 96 universal hue presets (4.101-4.196) — 12 hues × 8 saturation steps using HSB color model
version: 1.0.0
created: 2026-03-31T21:52:55Z
last_updated: 2026-03-31T21:52:55Z
---

# Hue Palette Creator

**Worker charter:** DESTRUCTIVE — creates or overwrites 96 universal color presets in
preset pool slots 4.101–4.196. Presets are stored as universal scope and immediately
labeled. This is the foundation for the 6 hue-pair sequences on executors 202–207.

Invoke when asked to: build a full hue palette, create the 96-preset expanded color
library, or repopulate presets 4.101–4.196.

---

## Preset Block Layout

| Hue | Hue° | Slots | Names |
|-----|------|-------|-------|
| Red | 0° | 4.101–4.108 | Red Full, Red Deep, Red Rich, Red Mid, Red Soft, Red Pale, Red Blush, Red Hint |
| Orange | 30° | 4.109–4.116 | Orange Full … Orange Hint |
| Amber | 60° | 4.117–4.124 | Amber Full … Amber Hint |
| Yellow | 90° | 4.125–4.132 | Yellow Full … Yellow Hint |
| Lime | 120° | 4.133–4.140 | Lime Full … Lime Hint |
| Green | 150° | 4.141–4.148 | Green Full … Green Hint |
| Teal | 180° | 4.149–4.156 | Teal Full … Teal Hint |
| Cyan | 210° | 4.157–4.164 | Cyan Full … Cyan Hint |
| Azure | 240° | 4.165–4.172 | Azure Full … Azure Hint |
| Blue | 270° | 4.173–4.180 | Blue Full … Blue Hint |
| Violet | 300° | 4.181–4.188 | Violet Full … Violet Hint |
| Magenta | 330° | 4.189–4.196 | Magenta Full … Magenta Hint |

Slot formula: `slot = 101 + (hue_index × 8) + sat_step_index`

---

## 8 Saturation Steps

| Step | Saturation | Suffix |
|------|-----------|--------|
| 0 | 100 | Full |
| 1 | 88 | Deep |
| 2 | 75 | Rich |
| 3 | 63 | Mid |
| 4 | 50 | Soft |
| 5 | 38 | Pale |
| 6 | 25 | Blush |
| 7 | 13 | Hint |

All entries use brightness=100. Saturation=13 (Hint) retains a visible tint — never use 0 (pure white).

---

## HSB → RGB Conversion (MA2 0-100 scale)

MA2 fixture attributes (`ColorRgb1/2/3`) use a 0–100 percentage scale. Convert HSB:

```
s_frac = S / 100
v_frac = B / 100   (always 1.0 in this palette)
h_norm = H / 60
i = floor(h_norm) % 6
f = h_norm - floor(h_norm)
p = v * (1 - s)
q = v * (1 - s*f)
t = v * (1 - s*(1-f))

sector 0: R=v, G=t, B=p
sector 1: R=q, G=v, B=p
sector 2: R=p, G=v, B=t
sector 3: R=p, G=q, B=v
sector 4: R=t, G=p, B=v
sector 5: R=v, G=p, B=q

Scale to 0-100: multiply each by 100, round to nearest int.
```

---

## Allowed Tools

```
get_client (for SelFix, attribute, ClearAll — via send_command_with_response),
store_new_preset, label_or_appearance, list_preset_pool
```

DESTRUCTIVE tools used: `store_new_preset` and `label_or_appearance` — both require
`confirm_destructive=True`.

---

## Steps

### 1. For each of 96 presets — select, set RGB, store, label, clear

```
for each entry in HUE_PALETTE_96:
    a. SelFix:  send "SelFix 1 Thru 9999"
    b. Red:     send 'attribute "ColorRgb1" at {r}'
    c. Green:   send 'attribute "ColorRgb2" at {g}'
    d. Blue:    send 'attribute "ColorRgb3" at {b}'
    e. Store:   store_new_preset(preset_type="color", preset_id=slot_id,
                    universal=True, overwrite=True, confirm_destructive=True)
    f. Label:   label_or_appearance(action="label", object_type="preset",
                    object_id=slot_id, preset_type="color", name=name,
                    confirm_destructive=True)
    g. Clear:   send "ClearAll"
```

**Step (f) is mandatory.** MA2's `store preset /overwrite` updates DMX values but
never updates the slot label. Without an explicit label call the pool will show stale
names from any previous occupant of the slot.

---

### 2. Verify

Call `list_preset_pool("color")` and confirm entries span 4.101–4.196.

---

### 3. Compress findings

```json
{
  "summary": "Created 96 universal hue presets (4.101–4.196)",
  "findings": [],
  "presets_created": [...],
  "state_changes": [...],
  "recommended_actions": [
    "Run hue-sequence-builder for each of 6 hue pairs",
    "Or run full-hue-expansion to do everything in one pass"
  ],
  "confidence": "high"
}
```

---

## Existing presets 4.1–4.8

Do NOT touch presets 4.1–4.8 (Red, Blue, Green, Amber, White, Magenta, Cyan, UV).
Those slots belong to Sequence 99 "Color Palette" / Executor 201 which must remain intact.

---

## Safety Escalation

Before executing Step 1, print:
`"About to store/overwrite 96 hue presets (Preset 4.101–4.196)"`.
If `confirm_destructive` is not set → abort.
Never auto-set `confirm_destructive=True`.
