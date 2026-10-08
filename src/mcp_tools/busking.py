"""MCP tools — busking. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    assign_effect_to_executor as build_assign_effect_to_executor,
    list_effect_library as build_list_effect_library,
    list_macro_library as build_list_macro_library,
    release_effects_on_page as build_release_effects_on_page,
    set_effect_rate as build_set_effect_rate,
    set_effect_speed as build_set_effect_speed,
    zero_page_faders as build_zero_page_faders,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Busking / Performance Layer Tools
# Live performance primitives: effect assignment, fader control, show mode
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def assign_effect_to_executor(
    effect_id: int,
    executor_id: int,
    page: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Assign an effect template to a fader executor slot (DESTRUCTIVE).

    Binds an effect from the effect library to an executor so the fader controls
    effect intensity in live busking mode. This is the core primitive for the
    fader-per-effect busking model.

    Args:
        effect_id: Effect pool ID to assign (1-based).
        executor_id: Target executor slot number on the page.
        page: Optional page number. When given, qualifies as 'Page {page}.{exec}'.
        confirm_destructive: Must be True to execute (DESTRUCTIVE — modifies executor assignment).

    Returns:
        JSON result with command sent and console response.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "assign_effect_to_executor is DESTRUCTIVE (modifies executor assignment). Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
            "command_preview": build_assign_effect_to_executor(effect_id, executor_id, page=page),
        }, indent=2)
    client = await _srv.get_client()
    cmd = build_assign_effect_to_executor(effect_id, executor_id, page=page)
    response = await client.send_command(cmd)
    return json.dumps({"command": cmd, "response": response, "effect_id": effect_id, "executor_id": executor_id}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def modulate_effect(
    mode: str,
    value: int,
) -> str:
    """
    Set rate or speed on active effects in real time (SAFE_WRITE).

    Used in busking to live-modulate effect tempo without stopping playback.
    Rate is a relative multiplier (100 = normal, 200 = double).
    Speed is an absolute BPM target (overrides rate).

    Args:
        mode: "rate" (relative 1–200, 100=normal) or "speed" (absolute BPM).
        value: Numeric value for the chosen mode.

    Returns:
        JSON result with command sent and console response.
    """
    if mode == "rate":
        cmd = build_set_effect_rate(value)
    else:
        cmd = build_set_effect_speed(value)
    client = await _srv.get_client()
    response = await client.send_command(cmd)
    return json.dumps({"command": cmd, "mode": mode, "value": value, "response": response}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def clear_effects_on_page(
    page: int,
    start_exec: int = 1,
    end_exec: int = 20,
) -> str:
    """
    Release (kill) all effect executors across a page range (SAFE_WRITE).

    Sends Off commands to every executor in the range, stopping all running
    effects. Use during song transitions to clean up the previous song's state.
    Does not change fader positions — use normalize_page_faders for that.

    Args:
        page: Fader page number.
        start_exec: First executor slot to release (default 1).
        end_exec: Last executor slot to release (default 20).

    Returns:
        JSON result with command count and console response.
    """
    client = await _srv.get_client()
    cmd = build_release_effects_on_page(page, start_exec=start_exec, end_exec=end_exec)
    response = await client.send_command(cmd)
    count = end_exec - start_exec + 1
    return json.dumps({"command_count": count, "page": page, "response": response}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def normalize_page_faders(
    page: int,
    start_exec: int = 1,
    end_exec: int = 20,
) -> str:
    """
    Set all faders on a page to 0 without releasing executors (SAFE_WRITE).

    Silences all effects while keeping them armed for instant recall — the
    standard busking blackout technique. Faders return to zero but executors
    remain active; pushing the fader up immediately restores the effect.

    Args:
        page: Fader page number.
        start_exec: First executor slot (default 1).
        end_exec: Last executor slot (default 20).

    Returns:
        JSON result with command count and console response.
    """
    client = await _srv.get_client()
    cmd = build_zero_page_faders(page, start_exec=start_exec, end_exec=end_exec)
    response = await client.send_command(cmd)
    count = end_exec - start_exec + 1
    return json.dumps({"command_count": count, "page": page, "zeroed": True, "response": response}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def classify_show_mode() -> str:
    """
    Inspect the show and classify its execution mode (SAFE_READ).

    Queries the effect and macro libraries to determine whether the current
    show is structured for busking (effect-fader model), sequence-driven
    playback, or a hybrid of both.

    Returns:
        JSON with mode classification and supporting evidence:
        - "busking"  — primarily effects assigned to fader executors
        - "sequence" — primarily cue sequences on executors
        - "hybrid"   — mix of effects and sequences
        - "empty"    — no content detected
    """
    client = await _srv.get_client()
    effect_response = await client.send_command(build_list_effect_library())
    macro_response = await client.send_command(build_list_macro_library())

    effect_lines = [line for line in effect_response.splitlines() if line.strip() and not line.startswith("[")]
    macro_lines = [line for line in macro_response.splitlines() if line.strip() and not line.startswith("[")]

    effect_count = len(effect_lines)
    macro_count = len(macro_lines)

    if effect_count == 0 and macro_count == 0:
        mode = "empty"
    elif effect_count > macro_count * 2:
        mode = "busking"
    elif macro_count > effect_count * 2:
        mode = "sequence"
    else:
        mode = "hybrid"

    return json.dumps({
        "mode": mode,
        "evidence": {"effects": effect_count, "macros": macro_count},
    }, indent=2)
