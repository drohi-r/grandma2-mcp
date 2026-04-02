---
title: Busking Lighting Performance
description: Instruction module for live-performance busking on grandMA2 — fader-per-effect model, executor layout, effect layering, and live recovery
version: 1.0.0
created: 2026-03-30T03:17:46Z
last_updated: 2026-03-30T03:17:46Z
---

# Busking Lighting Performance

## Core Model: Fader-Per-Effect

In busking mode the LD *performs*, not triggers. Each executor runs one
continuously looping effect. The fader controls master intensity:

- **Fader at 0** → effect runs but outputs nothing (silenced, not released)
- **Fader at 100** → effect runs at full intensity
- **Raise/lower live** → real-time modulation without programmer interaction

This is the opposite of sequence-cue playback. There are no cue steps;
everything is always running, always modulatable.

## Executor Layout Convention

```
Page layout (one page per song + one fixed global page):

[1]  Song loader macro (first-button protocol — see song-macro-page-design skill)
[2]  Strobe / flash effect
[3]  Chase effect (color or position)
[4]  Beam effect (gobos, zoom)
[5]  Ambient wash effect
[6]  Key light effect or special
[7]  Audience blinder effect
[8]  Haze / atmospheric
[9]  Group master — front wash (intensity only)
[10] Group master — back wash (intensity only)
```

Fixed global page (always loaded as second layer):
- Overture / downtime look
- House light control
- Emergency blackout macro
- Stage manager cueing macro

## Rate vs Intensity

| What you want | Tool | Parameter |
|---|---|---|
| Make effect feel slower/faster | `modulate_effect(mode="rate", value=N)` | 50 = half speed, 200 = double |
| Lock effect to BPM | `modulate_effect(mode="speed", value=BPM)` | e.g. 128 for EDM |
| Make effect brighter/dimmer | Push/pull fader via `set_executor_level` | 0–100 |
| Kill effect completely | `clear_effects_on_page(page, start_exec=N, end_exec=N)` | single exec |

Rate is relative (multiplier around whatever the effect's base speed is).
Speed is absolute — it locks the BPM regardless of the effect's programmed rate.
Use rate for feel adjustments; use speed when syncing to a specific BPM track.

## Effect Layering with MAtricks

Layer spatial variation on top of effects without duplicating them:

1. Select the fixture group the effect runs on
2. Apply `MAtricksInterleave 4` (or other split) — divides fixtures into alternating groups
3. Run the effect — MA2 applies the phase offset automatically per MAtricks split
4. Adjust interleave live with `modulate_effect` rate to tighten/loosen the chase

Useful combinations:
- Strobe + Interleave 2 → alternating strobe (odd vs even fixtures)
- Chase + Interleave 4 → 4-way pixel chase
- Beam effect + Groups 2 → two independent beam balls

## Live Recovery Protocol

When show state drifts (levels stuck, wrong color, effect not responding):

```
Step 1: normalize_page_faders(page)
        → silences everything without visual glitch (faders → 0, executors stay active)

Step 2: clear_effects_on_page(page)
        → releases all executors on page (clean slate)

Step 3: Re-trigger song loader (Exec 1 on current page)
        → restores song's base state: color, position, programmer clear

Step 4: Gradually raise effect faders in order
        → 1 fader at a time, verify each effect before adding the next
```

Never: jump straight to step 2 without step 1 — releasing running effects
causes a visible flash if their faders are above zero.

## Safety Rules

- Never call `assign_effect_to_executor` during a live show — always pre-show
- Use `normalize_page_faders` before `clear_effects_on_page` in all recovery paths
- Effects assigned to executors survive `ClearAll` — programmer clear does not kill faders
- Group masters (execs 9-10) override individual effect intensities — always check these
  when an effect seems low/high
