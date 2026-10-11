"""MCP tools — resources. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
from pathlib import Path

import src.server as _srv
from src.mcp_features import (
    ACTIVITY_RESOURCE_URI,
)
from src.server import (
    _get_telemetry,
    mcp,
)
from src.vocab import classify_token

# ============================================================
# MCP Resources
# Static and semi-static context exposed as URI-addressable docs
# ============================================================


@mcp.resource(ACTIVITY_RESOURCE_URI)
def resource_console_activity() -> str:
    """
    Recent console-changing tool calls made through this server (live).

    Read from the local telemetry log — no console I/O. Subscribe to get a
    notifications/resources/updated message after every change.
    """
    rows = _get_telemetry().recent_changes(limit=25)
    return json.dumps({"changes": rows, "count": len(rows)}, indent=2, default=str)


@mcp.resource("ma2://docs/rights-matrix")
def resource_rights_matrix() -> str:
    """
    MA2 OAuth scope → MA2Right mapping matrix (read-only reference).

    Returns the full JSON rights matrix from doc/ma2-rights-matrix.json.
    Use this resource to look up which OAuth scope is required for any
    MA2 operation before attempting to call a tool.
    """
    rights_path = Path(__file__).parent.parent / "doc" / "ma2-rights-matrix.json"
    try:
        return rights_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return json.dumps({"error": "rights matrix not found at doc/ma2-rights-matrix.json"})


@mcp.resource("ma2://docs/vocab-summary")
def resource_vocab_summary() -> str:
    """
    grandMA2 keyword vocabulary summary — all 141 keywords with RiskTier and category.

    Use this resource to look up the safety tier of any MA2 keyword before
    including it in a command string.  Tier determines whether confirm_destructive
    is required and which OAuthScope must be active.
    """
    from src.vocab import load_vocab
    spec = load_vocab()
    summary = {}
    all_keywords = list(spec.function_keywords.keys()) + list(spec.object_keywords.keys())
    for kw in all_keywords:
        resolved = classify_token(kw, spec)
        summary[kw] = {"category": resolved.category, "risk_tier": resolved.risk_tier}
    return json.dumps(summary, indent=2)


@mcp.resource("ma2://docs/tool-taxonomy")
def resource_tool_taxonomy() -> str:
    """
    ML-generated tool taxonomy — all registered tools clustered into categories.

    Each entry includes tool name, category, and docstring summary.
    Use this resource to understand the tool landscape before calling
    suggest_tool_for_task, or to verify a tool exists before invoking it.
    """
    taxonomy = _srv._load_taxonomy_cached()
    # Return a compact summary: category → tool names
    categories = taxonomy.get("categories", {})
    summary = {
        cat: [t["name"] for t in data.get("tools", [])]
        for cat, data in categories.items()
    }
    return json.dumps({"categories": summary, "total_tools": sum(len(v) for v in summary.values())}, indent=2)


@mcp.resource("ma2://docs/responsibility-map")
def resource_responsibility_map() -> str:
    """
    Module responsibility map — every file's primary role and architectural smells.

    Use this resource when making architectural decisions or when adding new
    modules, to ensure the new code is placed in the correct layer.
    """
    map_path = Path(__file__).parent.parent / "doc" / "responsibility-map.md"
    try:
        return map_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "# Responsibility map not found. Run the architecture audit to regenerate."


@mcp.resource("ma2://docs/tool-surface-tiers")
def resource_tool_surface_tiers() -> str:
    """
    Tool profiles (GMA_TOOL_PROFILE=core|standard|full) — which tools each one
    exposes, generated from src/tool_profiles.py so it can't drift.
    """
    from src.tool_profiles import PROFILES, tier_of

    names = sorted(_srv._ALL_TOOLS)
    by_tier: dict[str, list[str]] = {p: [] for p in PROFILES}
    for name in names:
        by_tier[tier_of(name)].append(name)
    lines = [
        "# Tool profiles",
        "",
        "Set GMA_TOOL_PROFILE to choose what MCP clients see (default: full).",
        "Each profile includes the ones above it. Hidden tools stay available to run_agent_goal.",
        "",
    ]
    total = 0
    for profile in PROFILES:
        total += len(by_tier[profile])
        lines += [f"## {profile} — {total} tools ({len(by_tier[profile])} added)", ""]
        lines += [", ".join(f"`{n}`" for n in by_tier[profile]), ""]
    return "\n".join(lines)


@mcp.resource("ma2://skills/{skill_id}")
def resource_skill_body(skill_id: str) -> str:
    """
    Retrieve a skill's formatted injection payload by ID.

    Returns the skill body formatted as a user message ready for injection,
    but only if the skill is usable (approved or non-DESTRUCTIVE).
    Returns an error message if the skill is not found or not yet approved.

    Use SkillRegistry.get_usable() for the same check with Python access.
    """
    from src.skill import SkillRegistry
    reg = SkillRegistry()
    skill = reg.get_usable(skill_id)
    if skill is None:
        sk = reg.get(skill_id)
        if sk is None:
            return f"Skill '{skill_id}' not found in registry."
        return f"Skill '{skill_id}' exists but is not usable (safety_scope=DESTRUCTIVE, approved=False). Requires SYSTEM_ADMIN approval."
    return skill.as_user_message()


@mcp.resource("ma2://busking/patterns")
def resource_busking_patterns() -> str:
    """
    Best-practice busking patterns for live performance lighting (read-only).

    Covers: fader-per-effect model, song macro page protocol, live recovery
    steps, and color lock technique. Use before designing a busking show.
    """
    return """\
# grandMA2 Busking Patterns

## Fader-Per-Effect Model
Each executor on a fader page runs one effect. The fader controls intensity
(0 = silent, 100 = full). Effects stay armed — zero fader silences, raise
fader restores. Never release effects mid-song; use normalize_page_faders.

Layout convention:
  - Column 1 (Exec 1): Song loader macro (first-button protocol)
  - Columns 2–8 (Exec 2–8): Effect faders (strobe, chase, color, beam...)
  - Columns 9–10: Group masters (intensity override for rig sections)
  - Fixed right page: Global effects that persist across songs

## Song Macro Page Protocol
Each song gets one page. Page name: `SNG_{n}_{SongName}` (e.g. SNG_3_Villains).

**First button (Exec 1) macro lines:**
1. `ClearAll` — reset programmer
2. `Go Preset 4.{palette_id}` — apply song color palette
3. `Go Macro {song_setup_macro}` — recall rig positions and timing
4. `SelectDrive {executor_page}` — jump to this song's effect page

**Remaining buttons:** effect executors — no macros, faders only.

## Live Recovery Protocol
When show state drifts (wrong levels, stuck effects):
1. `normalize_page_faders(page)` — zero all faders silently
2. `clear_effects_on_page(page)` — release stuck executors
3. Re-trigger song loader (Exec 1) to restore clean state
4. Gradually raise faders to rebuild look

## Color Lock Technique
Prevents color bleed when multiple effects are active:
1. Store song color as a Color preset (e.g. Preset 4.30 = deep amber)
2. Apply preset to all fixtures via Group masters before effects start
3. Effects modulate intensity/position only — color preset holds the hue
4. On song change: apply new color preset before raising new effect faders
"""


@mcp.resource("ma2://busking/effect-design")
def resource_effect_design() -> str:
    """
    Effect-to-executor assignment patterns and rate/speed semantics (read-only).

    Covers: assign_effect_to_executor usage, rate vs speed distinction,
    MAtricks layering for busking, and batch release safety.
    """
    return """\
# grandMA2 Effect Design for Busking

## Effect Assignment
Use `assign_effect_to_executor(effect_id, executor_id, page=N)` to bind an
effect from the library to a fader slot. This is DESTRUCTIVE — do during
pre-show programming, not during live performance.

Command generated: `Assign Effect {id} Executor {id}` or `Assign Effect {id} Page {n}.{exec}`

After assignment, the fader controls the effect's master intensity (0-100).
The effect runs continuously while the executor is active.

## Rate vs Speed
| Parameter | Command | Semantics | Range |
|-----------|---------|-----------|-------|
| Rate | `EffectRate {n}` | Relative multiplier — 100 = normal | 1–200 |
| Speed | `EffectSpeed {n}` | Absolute BPM — overrides rate | 20–300 |

Use `modulate_effect(mode="rate", value=150)` to push effects 1.5× faster.
Use `modulate_effect(mode="speed", value=120)` to lock effects to 120 BPM.

Speed and rate affect the *selected* effects globally. To target a specific
executor's effect, select it first with `select_executor(executor_id)`.

## MAtricks Layering
Layer MAtricks patterns over effects for per-fixture phase offsets:
1. Select group, apply MAtricks Interleave
2. Run effect — each fixture gets a phase offset proportional to its index
3. Adjust interleave with `modulate_effect` rate to control chase tightness

## Batch Release Safety
`clear_effects_on_page(page, start_exec=1, end_exec=20)` sends 20 Off
commands in a single chained string. On slow consoles this may cause a
brief flash as effects die in sequence. To avoid: use `normalize_page_faders`
first (silences without visual glitch), then `clear_effects_on_page`.
"""


@mcp.resource("ma2://busking/color-design")
def resource_color_design() -> str:
    """
    Constrained color palette design for busking shows (read-only).

    Covers: HSB palette strategy, preset numbering, monochromatic constraint,
    and color lock via group master. Use when designing song color palettes.
    """
    return """\
# grandMA2 Constrained Color Design for Busking

## HSB vs RGB
Always use HSB for live busking color design. MA2 HSB range: 0-100 (not 0-255).

| Parameter | Flag | Range | Notes |
|-----------|------|-------|-------|
| Hue | `/h=` | 0–360 | Degrees |
| Saturation | `/s=` | 0–100 | 0 = white, 100 = full color |
| Brightness | `/br=` | 0–100 | 0 = black, 100 = full |

Example: `store_preset 4.30 /h=30 /s=95 /br=100` = deep amber.

## Monochromatic Palette Strategy
Each song gets one hue with 4 brightness stops:
- Stop 1: Full intensity (br=100, s=90)
- Stop 2: Mid punch (br=70, s=85)
- Stop 3: Moody fill (br=40, s=80)
- Stop 4: Near-black accent (br=15, s=75)

## Preset Numbering Convention
`preset_id = song_id * 10 + stop_index`

| Song | Stop | Preset |
|------|------|--------|
| Song 1 | 1 (full) | 11 |
| Song 1 | 2 (mid) | 12 |
| Song 3 | 4 (accent) | 34 |

Recall with `apply_preset(preset_type="color", preset_id=34)`.

## Color Lock Technique
1. Before raising effect faders, apply the song's full-intensity color preset
   to all rig fixtures via group masters: `group_at(group_id=99, value=100)`
2. Effects that only modulate intensity/position inherit the locked color
3. Transition between songs: apply new color preset (step 1) BEFORE releasing
   the previous song's effect faders — avoids white flash on crossover
4. For fixtures with separate color channels (CMY movers): store color in a
   Color preset, not in the programmer, so it survives `ClearAll`
"""


@mcp.resource("ma2://docs/volunteer-guide")
def resource_volunteer_guide() -> str:
    """
    Volunteer operator guide — plain-language grandMA2 operation for non-programmers.

    Explains the three-tier access model, Sunday morning preflight procedure,
    and what to do when things go wrong. Designed for church technical directors
    training volunteers and any production environment with tiered staff skill levels.
    """
    return """\
# MA2 Agent Volunteer Operator Guide

## The Three Safety Tiers

MA2 Agent enforces three access levels automatically. You cannot accidentally break something outside your tier.

| Your Role | Tier | What You Can Do |
|-----------|------|-----------------|
| New volunteer | SAFE_READ | See console state, verify the show is correct. Zero risk. |
| Trained operator | SAFE_WRITE | Trigger go/pause, adjust faders, apply presets. With guidance. |
| Technical Director | DESTRUCTIVE | Store cues, modify show file, change patch. TD only. |

## Sunday Morning Preflight (Any Volunteer -- SAFE_READ)

Run in order before doors open:

1. Verify show file -- get_showfile_info() -- confirm show name matches expected
2. Check for changes -- assert_showfile_unchanged() -- if this fails, STOP and call TD
3. Hydrate -- hydrate_console_state() -- snapshot everything
4. Check presets -- list_preset_pool(preset_type="color") -- should have entries
5. Check executors -- get_executor_detail(executor_id="1.1") -- confirm sequence assigned
6. Check cues -- query_object_list(object_type="sequence", object_id=1) -- confirm cues present

All GREEN? You are ready. Any RED? Call your TD before service.

## During Service (Trained Volunteer -- SAFE_WRITE)

- Advance cues: playback_action(executor_id, action="go")
- Pause: playback_action(executor_id, action="pause")
- Jump to cue: goto_cue(executor_id, cue_id)

## When Things Go Wrong

| Problem | Action |
|---------|--------|
| Wrong look on stage | Do NOT touch anything. Note cue number. Call TD. |
| Console unresponsive | Run get_console_location(). If error, notify TD. |
| Show file looks different | Run assert_showfile_unchanged(). If fails, STOP, call TD immediately. |
| Executor shows wrong state | Run get_executor_detail(executor_id) and report to TD. |

Rule: If in doubt, do nothing and call your TD.
"""


@mcp.resource("ma2://docs/sb132-compliance")
def resource_sb132_compliance() -> str:
    """
    SB 132 compliance guide — California Film & Television Tax Credit safety documentation
    requirements mapped to MA2 Agent telemetry fields.

    For gaffers, safety officers, production managers, and insurance brokers on
    productions receiving the California Film & Television Tax Credit (effective July 2025).
    """
    return """\
# SB 132 Compliance Guide for MA2 Agent

## What SB 132 Requires (July 2025)

California SB 132 applies to productions receiving the CA Film & Television Tax Credit and requires:

1. Dedicated Safety Advisor -- on set daily
2. Written Risk Assessment -- before any high-risk operation
3. Daily Safety Meeting Notes -- documented
4. Final Safety Report -- within 60 days of wrap

## MA2 Agent Data to SB 132 Mapping

| SB 132 Requirement | MA2 Agent Source | Tool |
|---|---|---|
| Written risk assessment | risk_tier per operation (SAFE_READ/SAFE_WRITE/DESTRUCTIVE) | get_telemetry_report() |
| Operator identification | operator field in tool_invocations | get_telemetry_report() |
| Daily safety meeting notes | session_id grouped timeline with timestamps | generate_compliance_report() |
| Incident log | error_class field in tool_invocations | get_telemetry_report(risk_tier="DESTRUCTIVE") |
| Final safety report | Full session export | generate_compliance_report(session_id=...) |

## Three-Tier Risk Stratification (for Insurance Underwriters)

MA2 Agent classifies every lighting control operation:

- SAFE_READ -- Read-only monitoring. Zero risk to console state or physical hardware.
- SAFE_WRITE -- Controlled modifications (level adjustments, go/pause). Standard operational risk.
- DESTRUCTIVE -- High-risk operations (cue storage, show file changes, patch modifications).
  Requires explicit confirm_destructive=True AND elevated OAuth scope. All logged.

## Generating a Compliance Report

Use generate_compliance_report(session_id, production_name, operator_name, days=1)
for a markdown report ready for safety documentation.

Use get_telemetry_report(session_id, format="json") for archival JSON export.

## Insurance Brief Template

All lighting control operations during [PRODUCTION NAME] were processed through
MA2 Agent's three-tier safety system. [N] operations were classified SAFE_READ
(read-only monitoring, zero risk), [M] were SAFE_WRITE (controlled modifications
requiring standard authorization), and [K] were DESTRUCTIVE (required explicit
authorization and elevated scope). Full telemetry is retained for forensic review
and available upon request from the production safety advisor.

## IATSE Kit Rental

Under the 2024 IATSE-AMPTP contract, AI tools used by union members constitute "covered work"
and operators may charge a kit rental fee. MA2 Agent's operator field in telemetry
records which union member ran each session, supporting kit rental documentation.
"""


@mcp.resource("ma2://docs/rdm-workflow")
def resource_rdm_workflow() -> str:
    """
    RDM (Remote Device Management) workflow reference — discovery, device info,
    and autopatch best practices for grandMA2 via telnet.
    """
    return """\
# RDM Workflow Reference

## What is RDM?

RDM (Remote Device Management) is a bidirectional extension to DMX512 (ANSI E1.20)
that allows a lighting console to identify, configure, and report status from
intelligent fixtures without additional cabling.

## When to Use RDM

| Use Case | RDM Benefit |
|----------|------------|
| Unknown rig | Identify all fixtures and their current DMX addresses |
| Address conflicts | Read device-reported addresses vs. patch sheet |
| Fixture status | Get lamp hours, temperature, error status |
| Autopatch | Let MA2 suggest addresses based on discovered footprints |

## Tool Sequence

1. Discover all RDM devices on a universe: rdm_discover(universe_id=1)
   Returns: list of {uid, manufacturer, device_model, footprint, current_address}

2. Get detailed info for a specific device: rdm_get_info(uid="0x1234567890AB")
   Returns: full device profile including label, DMX footprint, current address, error status

3. Apply a DMX address (autopatch): rdm_patch(uid="0x1234567890AB", target_address=1, confirm_destructive=True)
   Assigns the fixture to channel 1 on its universe

## Limitations

- Not all fixtures support RDM. Most intelligent fixtures do; dimmers may not.
- RDM requires a proper terminator at the end of the DMX chain.
- RDM discovery can take 10-30 seconds per universe on large rigs.
- After RDM patch, verify with list_fixtures() and detect_dmx_address_conflicts().

## RDM vs Manual Patching

| | RDM | Manual |
|---|---|---|
| Speed | Fast for large rigs | Faster for small rigs |
| Accuracy | Device-reported | Human-verified |
| Risk | Overwrites existing addresses | You control every address |
| Recommended when | Unknown rental rig, >50 fixtures | Known rig, <20 fixtures |
"""


@mcp.resource("ma2://docs/lua-scripting")
def resource_lua_scripting() -> str:
    """
    grandMA2 Lua 5.2 scripting reference — gma.* namespace, plugin lifecycle,
    and common patterns for MCP-driven plugin development.
    """
    return """\
# grandMA2 Lua Scripting Reference

## Environment

grandMA2 uses Lua 5.2 with the gma.* namespace for console integration.
Standard Lua libraries (math, string, table, io) are available.

## Core gma.* Functions

| Function | Description |
|----------|-------------|
| gma.cmd(str) | Execute a MA2 command |
| gma.echo(str) | Print to feedback line |
| gma.show.getvar(name) | Read show variable |
| gma.show.setvar(name, val) | Write show variable |
| gma.user.confirm(msg) | Show OK/Cancel dialog |
| gma.timer.sleep(ms) | Pause execution (ms) |
| gma.gui.confirm(title, msg) | GUI confirmation |

## Plugin vs Macro: Decision Guide

| Need | Use |
|------|-----|
| Simple linear commands | Macro (MA2 command strings) |
| Loop (for/while) | Lua Plugin |
| Math calculation | Lua Plugin |
| Read/write variables | Either (SetVar in macro, gma.show.setvar in Lua) |
| User dialog (confirm/input) | Lua Plugin only |
| Conditional (if/else) | Lua Plugin |

## Common Patterns

Loop over fixture IDs:
  for i = 1, 20 do
      gma.cmd("Fixture " .. i .. " At 100")
      gma.timer.sleep(100)
  end

Read and branch on system variable:
  local pg = tonumber(gma.show.getvar("FADERPAGE"))
  if pg == 1 then gma.cmd("Page 2") else gma.cmd("Page 1") end

User confirmation gate:
  if gma.user.confirm("Delete all cues in Sequence 99?") then
      gma.cmd("Delete Cue 1 Thru 999 Sequence 99")
      gma.echo("Cues deleted.")
  else
      gma.echo("Cancelled.")
  end

## MCP Integration

Use run_lua_script(script_body) to execute inline Lua via MCP.
Use call_plugin_tool(plugin_name, args) to invoke a saved plugin by name.
Use reload_all_plugins() after uploading a new .lua file via USB.

Safety note: Lua scripts executed via gma.cmd() bypass MCP's safety gate.
Ensure scripts that call DESTRUCTIVE commands (Store, Delete, Assign) include
appropriate confirmations via gma.user.confirm().
"""
