---
title: Constrained Color Design
description: Instruction module for monochromatic palette design in grandMA2 — HSB strategy, preset numbering, color lock technique, and song-to-palette mapping
version: 1.1.0
created: 2026-03-30T03:17:46Z
last_updated: 2026-03-30T11:57:23Z
---

# Constrained Color Design

## Why Constrained Palettes Work for Busking

In live performance, unconstrained color creates visual chaos. A single hue
per song gives the audience a consistent emotional anchor that reinforces the
music. The LD modulates *intensity and texture* (via effects), not color.

Rule: one hue per song, 4 brightness stops, applied via presets.

## HSB in grandMA2

Always use HSB for palette design. MA2 HSB range: **0–100**, NOT 0–255.

| Parameter | Flag | Range | Example |
|-----------|------|-------|---------|
| Hue | `/h=` | 0–360° | `/h=30` = orange |
| Saturation | `/s=` | 0–100 | `/s=95` = deeply saturated |
| Brightness | `/br=` | 0–100 | `/br=80` = 80% intensity |

**Never use RGB for live color design** — RGB values are not perceptually
linear; HSB maps directly to what the LD sees. RGB is only for pixel-exact
replication of a specific LED color.

## Monochromatic Palette Strategy: 4 Stops per Song

```
Stop 1 — Full punch:    br=100, s=90   (used: chorus, peak moments)
Stop 2 — Mid warm:     br=70,  s=85   (used: verse, moderate energy)
Stop 3 — Moody fill:   br=40,  s=80   (used: breakdown, intimate sections)
Stop 4 — Near-black:   br=15,  s=75   (used: intro/outro, transitions)
```

Saturation stays high across all stops — dropping saturation washes color out.
Vary brightness only. The hue and saturation define the song's identity.

## Preset Numbering Convention

```
preset_id = (song_number × 10) + stop_index

Stop indices: 1=full, 2=mid, 3=moody, 4=accent
Preset type: Color (preset_type=4 in MA2)
```

| Song | Stop | Preset ID | Description |
|------|------|-----------|-------------|
| Song 1 | Full (1) | 11 | Song 1 full punch |
| Song 1 | Accent (4) | 14 | Song 1 near-black |
| Song 3 | Mid (2) | 32 | Song 3 mid warm |
| Song 7 | Moody (3) | 73 | Song 7 moody fill |

Apply with: `apply_preset(preset_type="color", preset_id=32)`

Store with:
```
store_new_preset(preset_type=4, preset_id=32, confirm_destructive=True)
label_or_appearance("label", "preset", 32, name="Song3_MidWarm", preset_type="color", confirm_destructive=True)
```

## Color Lock Technique

Prevents color bleed when effects run on top of a base color:

**Setup (pre-show, per song):**
1. Select all rig fixtures: `select_fixtures_by_group(group_id=99)` (all-fixtures group)
2. Apply song's full-punch color preset to programmer
3. Store as a Color preset at the song's slot: `store_new_preset(preset_type=4, preset_id=N*10+1)`
4. Label it: `SNG_{N}_Full`

**Live application (first-button macro line 2):**
```
Go Preset 4.{song_id*10+1}
```
This fires the full-punch color onto all fixtures before effects start.

**Why it works:**
Effects run in HTP/LTP over the programmer base. When the color preset is
applied first (via the first-button macro), it becomes the baseline. Effects
that modulate only *intensity* or *position* inherit the locked color. Effects
that modulate *color attributes* override the preset — avoid these in
monochromatic shows, or restrict them to specific fixture groups.

**Transition between songs:**
```
1. New song's first-button macro fires: ClearAll + new color preset applied
2. The new color is now the base for ALL fixtures
3. Fade up new song's effect faders
4. Old song's effects are already released (from ClearAll)
```

## CMY Moving Light Considerations

CMY fixtures (movers with Cyan/Magenta/Yellow subtractive mixing) need
special handling — their color presets must use attribute-level values, not
just HSB:

- Store Color presets using `set_attribute(attribute="Cyan", value=N)` etc.
  for fixtures where HSB does not map cleanly
- Alternatively: use the MA2 color picker in the Edit screen and store via
  `store_new_preset` — MA2 auto-converts to the fixture's native color model
- Group CMY and LED fixtures separately if they need different color values
  for perceptually matching colors (CMY Orange ≠ LED /h=30)
