---
title: Skill Index — grandMA2 MCP
description: Friction-grouped index of every skill under .claude/skills/ for fast lookup
version: 1.0.0
created: 2026-05-27T00:00:00Z
last_updated: 2026-05-27T00:00:00Z
---

# Skill Index

A friction-grouped index of all skills under `.claude/skills/`. For semantic search by intent, call the `suggest_skills_for_task(intent, top_k)` MCP tool instead.

## Color & presets

- [`auto-layout-color-picker`](auto-layout-color-picker/SKILL.md) — plugin-backed color picker layout. **First decision:** if the plugin is installed, prefer it over manual paths.
- [`color-preset-creator`](color-preset-creator/SKILL.md) — store universal color presets from RGB/HSB values.
- [`color-palette-sequence-builder`](color-palette-sequence-builder/SKILL.md) — build sequence cues referencing global color presets.
- [`constrained-color-design`](constrained-color-design/SKILL.md) — HSB-strategy monochromatic palette + numbering convention.
- [`hue-palette-creator`](hue-palette-creator/SKILL.md) — store the 96-preset universal hue library (4.101-4.196).
- [`hue-sequence-builder`](hue-sequence-builder/SKILL.md) — 16-cue sequence from an adjacent hue pair.

## Layouts & views

- [`view-and-layout-designer`](view-and-layout-designer/SKILL.md) — custom views, console layouts, button placement.

## Macros & plugins

- [`lua-and-plugins`](lua-and-plugins/SKILL.md) — Lua scripting v5.2, plugin invocation lifecycle.
- [`macro-advanced`](macro-advanced/SKILL.md) — SetVar/GetVar, CmdDelay, jump safety.
- [`macro-linter-and-refactorer`](macro-linter-and-refactorer/SKILL.md) — macro safety scan + refactor.
- [`song-macro-page-design`](song-macro-page-design/SKILL.md) — song-page conventions, first-button protocol.

## Patch, groups, fixtures

- [`patch-and-group-builder`](patch-and-group-builder/SKILL.md) — patch fixture types and build groups.
- [`clone-and-data-transfer`](clone-and-data-transfer/SKILL.md) — Clone workflow, attribute transfer.
- [`fixture-swap-surgeon`](fixture-swap-surgeon/SKILL.md) — fixture type swap with preset migration.
- [`rdm-workflow`](rdm-workflow/SKILL.md) — RDM discovery and autopatch.

## Cues, sequences, executors

- [`cue-tracking-and-timing`](cue-tracking-and-timing/SKILL.md) — tracking, Block/Unblock, MIB, timing.
- [`cue-list-auditor`](cue-list-auditor/SKILL.md) — gaps, labels, timing, health checks.
- [`cue-to-cue-rehearsal`](cue-to-cue-rehearsal/SKILL.md) — annotated cue-by-cue walkthrough.
- [`chaser-builder`](chaser-builder/SKILL.md) — step-based chaser sequences.
- [`executor-configuration`](executor-configuration/SKILL.md) — priority, special masters, trigger types.
- [`sequence-executor-assigner`](sequence-executor-assigner/SKILL.md) — assign a sequence to a free executor.
- [`effect-programmer`](effect-programmer/SKILL.md) — store, assign, modulate effects.

## Busking & live performance

- [`busking-lighting-performance`](busking-lighting-performance/SKILL.md) — fader-per-effect, layered model.
- [`busking-template-generator`](busking-template-generator/SKILL.md) — generate complete busking template from patch.
- [`showkontrol-bpm-sync`](showkontrol-bpm-sync/SKILL.md) — CDJ BPM → MA2 speed masters.

## Preset library architecture

- [`preset-library-architect`](preset-library-architect/SKILL.md) — universal vs selective preset strategy.
- [`preset-impact-manager`](preset-impact-manager/SKILL.md) — assess and plan preset updates / deletes.
- [`cross-venue-adaptation`](cross-venue-adaptation/SKILL.md) — adapt show to a new venue rig.

## Show creation & migration

- [`show-management-and-psr`](show-management-and-psr/SKILL.md) — save/load/PSR workflows.
- [`psr-show-migration`](psr-show-migration/SKILL.md) — slot-conflict detection during PSR merge.
- [`festival-stage-setup`](festival-stage-setup/SKILL.md) — patch to busking-ready in one session.
- [`timecode-show-programmer`](timecode-show-programmer/SKILL.md) — SMPTE pool, cue triggers, playback.
- [`show-health-check`](show-health-check/SKILL.md) — pre-show file audit.

## Troubleshooting & runbooks

- [`feedback-investigator`](feedback-investigator/SKILL.md) — classify Telnet feedback failures.
- [`operator-recovery-runbook`](operator-recovery-runbook/SKILL.md) — stuck playback, contaminated programmer, wrong world.
- [`telnet-feedback-triage`](telnet-feedback-triage/SKILL.md) — feedback classification module.
- [`troubleshoot-no-output`](troubleshoot-no-output/SKILL.md) — diagnostic tree for fixtures producing no light.
- [`tracking-debugger`](tracking-debugger/SKILL.md) — tracking leak / unexpected block diagnosis.

## Worlds, filters, scoping

- [`world-filter-designer`](world-filter-designer/SKILL.md) — Worlds and Filters and how to apply them.

## Connection & setup

- [`companion-integration`](companion-integration/SKILL.md) — Companion button page mirror of MA2 executors.
- [`remote-monitoring`](remote-monitoring/SKILL.md) — SAFE_READ console state monitoring.
- [`training-mode`](training-mode/SKILL.md) — annotated SAFE_READ console tour.
- [`volunteer-operations`](volunteer-operations/SKILL.md) — tiered access for non-programmers.

## Advanced workflows

- [`compliance-documentation`](compliance-documentation/SKILL.md) — SB-132 / safety-audit report from session telemetry.
- [`ma2-command-rules`](ma2-command-rules/SKILL.md) — command construction, object resolution, safety.

---

## Notes

- This index is one of two skill-discovery surfaces. The other is the `suggest_skills_for_task(intent, top_k)` MCP tool, which ranks skills against a natural-language intent using the same corpus.
- Front-matter fields `tags`, `prerequisites`, `wraps_plugin`, and `use_instead_of` (added per the `list_skills` enrichment in T1) are optional. Skills without them still load cleanly.
- A `connection-setup-workflow` skill is scheduled to be added in Task 4 (T2 — console portability).
