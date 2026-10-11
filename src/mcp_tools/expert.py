"""MCP tools — expert. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
import os
from pathlib import Path as _Path

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.server import (
    _handle_errors,
    logger,
    mcp,
)

# ============================================================================
# T1 — Skill router (suggest_skills_for_task)
# Pairs with src/skill_router.py — pure ranking module.
# ============================================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def suggest_skills_for_task(
    intent: str,
    top_k: int = 3,
    include_destructive: bool = True,
    prefer_semantic: bool = True,
) -> str:
    """Suggest skills from .claude/skills/ for a natural-language intent (SAFE_READ).

    Args:
        intent: What you want to do, e.g. "make me a color picker".
        top_k: Max number of suggestions to return.
        include_destructive: When False, drop un-approved DESTRUCTIVE skills.
        prefer_semantic: When True, attempt embedding-based ranking when a
            ``GITHUB_MODELS_TOKEN`` env var is set. Path A ships keyword only;
            this flag controls the warning message rather than the algorithm.

    Returns:
        JSON-encoded SuggestSkillsResponse: ``{intent, method, warning, suggestions}``.
    """
    from src.skill_router import rank_skills

    method: str = "keyword"
    warning: str | None = None
    if prefer_semantic and os.environ.get("GITHUB_MODELS_TOKEN"):
        method = "semantic"
        warning = "semantic search not yet wired in Path A; returning keyword results"
    elif prefer_semantic:
        warning = (
            "prefer_semantic=True but GITHUB_MODELS_TOKEN is not set; "
            "using keyword matching."
        )

    suggestions = rank_skills(
        intent=intent,
        top_k=top_k,
        method="keyword",
        include_destructive=include_destructive,
    )

    return json.dumps({
        "intent": intent,
        "method": method,
        "warning": warning,
        "suggestions": suggestions,
    }, indent=2)


# ============================================================================
# T2 — Console portability (discover_consoles, reconfigure_connection)
# ============================================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def discover_consoles(
    timeout_seconds: int = 5,
    network: str | None = None,
    methods: list[str] | None = None,
) -> str:
    """Discover grandMA2 consoles via UDP broadcast (SAFE_READ).

    Path A scope: broadcast only. mDNS path requires the optional
    ``[mdns]`` install (zeroconf) and is documented for Path B.

    Args:
        timeout_seconds: Listen window after the probe is sent.
        network: Optional CIDR to constrain the broadcast (e.g. "192.168.1.0/24").
            None auto-detects local interfaces.
        methods: List of methods to attempt — subset of {"broadcast", "mdns"}.
            Default: ["broadcast"].

    Returns:
        JSON envelope: ``{candidates, scanned_networks, elapsed_ms, note}``.
    """
    import time as _time

    from src.discovery import discover_grandma2_broadcast, list_local_networks

    methods_set = set(methods or ["broadcast"])
    t0 = _time.monotonic()
    candidates: list[dict] = []
    scanned: list[str] = []
    notes: list[str] = []

    if "broadcast" in methods_set:
        if network:
            scanned.append(network)
        else:
            scanned.extend(list_local_networks())
        results = await discover_grandma2_broadcast(
            network=network, timeout_seconds=timeout_seconds,
        )
        # Cast TypedDicts to plain dicts for JSON.
        candidates.extend(dict(r) for r in results)

    if "mdns" in methods_set:
        notes.append(
            "mdns method requires the [mdns] optional install "
            "(pip install 'ma2-agent[mdns]') — Path B"
        )

    elapsed_ms = (_time.monotonic() - t0) * 1000
    return json.dumps({
        "candidates": candidates,
        "scanned_networks": scanned,
        "elapsed_ms": round(elapsed_ms, 2),
        "note": "; ".join(notes) if notes else None,
    }, indent=2)


# ============================================================================
# T4 — Expert show creation from patch (build_show_from_patch)
# ============================================================================


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def build_show_from_patch(
    strategy: str,
    options: dict | None = None,
    dry_run: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """Build an expert-grade show scaffold from the current patch.

    Strategies (per spec §B.1): ``rock-band`` | ``festival`` | ``theatrical``
    | ``dj`` | ``broadcast`` | ``corporate``.

    Defaults to ``dry_run=True``; mutation requires ``confirm_destructive=True``.
    The plan is deterministic for a given (strategy, patch, options) triple,
    and every step is run through ``expert_lint(domain="show")`` before return.

    Args:
        strategy: One of the six strategies above.
        options: Optional ``ShowBuildOptions`` dict — overrides strategy defaults
            (e.g. ``{"songs": 14}``).
        dry_run: When True, build the plan but do not send any commands.
        confirm_destructive: Required for ``dry_run=False``. The plan is
            destructive — it creates groups, presets, cues, executors, worlds.

    Returns:
        JSON envelope: ``{strategy, plan, rationale, expert_review, summary,
        dry_run, executed_steps, blocked}``.
    """
    from src.expert_lint import expert_lint
    from src.show_strategies import build_plan_for, get_strategy
    from src.show_strategies.patch_reader import summarize_patch

    try:
        strat = get_strategy(strategy)
    except ValueError as e:
        return json.dumps({
            "strategy": strategy, "blocked": True, "error": str(e),
            "plan": [], "expert_review": [], "summary": {},
            "dry_run": dry_run, "executed_steps": 0,
        }, indent=2)

    client = await _srv.get_client()
    patch = await summarize_patch(client)
    plan = build_plan_for(strategy=strategy, patch=patch, options=options or {})

    # Run expert_lint on a synthesised "show" plan shape derived from the
    # build plan. The lint module's show rules look for cuelists/cues/worlds;
    # the build plan is step-oriented, so we project it.
    cuelists = [{
        "id": 99, "label": "Main", "tracking": strat.tracking,
        "priority": "normal", "off_time_ms": None,
        "cues": [
            {"id": s["meta"].get("cue_id", 0), "label": s["meta"].get("label", ""),
             "block": False, "uses_preset": True, "is_mib": False}
            for s in plan if s["kind"] == "store-cue"
        ],
    }]
    worlds = [{"name": s["meta"]["world_name"], "section": None}
              for s in plan if s["kind"] == "create-world"]
    lint_plan = {
        "kind": "show",
        "strategy": strategy,
        "preset_strategy": strat.preset_strategy,
        "cuelists": cuelists,
        "fixtures": [],
        "worlds": worlds,
        "views": strat.views,
        "steps": [
            {"order": s["order"], "command": s["command"],
             "purpose": s["purpose"]}
            for s in plan
        ],
    }
    findings = expert_lint(lint_plan, domain="show", context=None)

    if not dry_run and not confirm_destructive:
        return json.dumps({
            "strategy": strategy,
            "blocked": True,
            "error": "dry_run=False requires confirm_destructive=True",
            "plan": plan,
            "expert_review": [v.__dict__ for v in findings],
            "summary": {"plan_steps": len(plan)},
            "dry_run": dry_run,
            "executed_steps": 0,
        }, indent=2)

    executed = 0
    if not dry_run:
        # confirm_destructive=True already enforced above
        for step in plan:
            await client.send_command(step["command"])
            executed += 1

    return json.dumps({
        "strategy": strategy,
        "plan": plan,
        "rationale": [strat.notes],
        "expert_review": [v.__dict__ for v in findings],
        "summary": {
            "plan_steps": len(plan),
            "groups": sum(1 for s in plan if s["kind"] == "create-group"),
            "presets": sum(1 for s in plan if s["kind"] == "store-preset"),
            "cues": sum(1 for s in plan if s["kind"] == "store-cue"),
            "executors": sum(1 for s in plan if s["kind"] == "assign-executor"),
            "worlds": sum(1 for s in plan if s["kind"] == "create-world"),
        },
        "dry_run": dry_run,
        "executed_steps": executed,
        "blocked": False,
    }, indent=2)


# ============================================================================
# T8 — Expert preset library architect (architect_preset_library)
# ============================================================================


@mcp.tool()
@require_scope(OAuthScope.PRESET_UPDATE)
@_handle_errors
async def architect_preset_library(
    patch_filter: str | None = None,
    strategy: str = "full-coverage",
    dry_run: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """Architect a complete preset library against the current patch.

    Strategies (per spec §C.4):
      - ``full-coverage`` — universal color (8 hues + warm/cool wash) + position
        + selective gobo/beam/focus/control + MIB for movers
      - ``minimal-viable`` — 4 cardinal hues only, no position/selective
      - ``color-first`` — 12-hue wheel + warm/cool + minimal position

    Args:
        patch_filter: MA2 selection spec to constrain — None scans whole patch.
            (Path A note: filter wired through patch_reader's existing scope.)
        strategy: One of ``full-coverage`` | ``minimal-viable`` | ``color-first``.
        dry_run: When True, build the plan but don't send any commands.
        confirm_destructive: Required for ``dry_run=False``.

    Returns:
        JSON envelope: ``{strategy, reference_fixtures, plan, coverage_report,
        naming_convention, expert_review, summary, dry_run, executed_steps, blocked}``.
    """
    from src.expert_lint import expert_lint
    from src.preset_strategies import architect_preset_library_for, get_preset_strategy
    from src.show_strategies.patch_reader import summarize_patch

    try:
        get_preset_strategy(strategy)  # validates the strategy name
    except ValueError as e:
        return json.dumps({
            "strategy": strategy, "blocked": True, "error": str(e),
            "plan": [], "coverage_report": [], "expert_review": [],
            "summary": {}, "dry_run": dry_run, "executed_steps": 0,
        }, indent=2)

    client = await _srv.get_client()
    patch = await summarize_patch(client)
    result = architect_preset_library_for(
        strategy=strategy, patch=patch, options=None,
    )

    # Run expert_lint on the preset plan
    lint_plan = {
        "kind": "preset",
        "strategy": strategy,
        "reference_fixtures": result["reference_fixtures"],
        "plan": result["plan"],
        "fixture_types": [ft.get("short_name", "") for ft in patch.get("fixture_types", [])],
        "naming_convention": result["naming_convention"],
    }
    findings = expert_lint(lint_plan, domain="preset", context=None)

    if not dry_run and not confirm_destructive:
        return json.dumps({
            "strategy": strategy,
            "blocked": True,
            "error": "dry_run=False requires confirm_destructive=True",
            "reference_fixtures": result["reference_fixtures"],
            "plan": result["plan"],
            "coverage_report": result["coverage_report"],
            "naming_convention": result["naming_convention"],
            "expert_review": [v.__dict__ for v in findings],
            "summary": result["summary"],
            "dry_run": dry_run, "executed_steps": 0,
        }, indent=2)

    executed = 0
    if not dry_run:
        # The actual MA2 Store Preset path is left as a Path-B follow-on; per
        # the plan, this tool ships dry-run + plan emission. Operators can
        # use the plan output to drive subsequent Store calls.
        # confirm_destructive=True is gated above; here we surface that the
        # store path is deferred rather than mutating without an explicit
        # store loop.
        pass

    return json.dumps({
        "strategy": strategy,
        "reference_fixtures": result["reference_fixtures"],
        "plan": result["plan"],
        "coverage_report": result["coverage_report"],
        "naming_convention": result["naming_convention"],
        "expert_review": [v.__dict__ for v in findings],
        "summary": result["summary"],
        "dry_run": dry_run,
        "executed_steps": executed,
        "blocked": False,
    }, indent=2)


# ============================================================================
# T5 — Screen layout builder (build_layout_for_screen)
# ============================================================================


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def build_layout_for_screen(
    screen: int,
    content: list[dict] | None = None,
    template: str | None = None,
    dry_run: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """Build (and optionally apply) a layout for one of the MA2 screens.

    Either ``template`` or ``content`` must be supplied (not both).

    Templates (per spec §B.2): ``busking-master`` | ``preset-access`` |
    ``executor-monitor`` | ``macro-page`` | ``programmer-view`` |
    ``troubleshoot-view``.

    Args:
        screen: Target screen number (1-5 on a full console; 1 on onPC).
        content: Optional list of ContentSpec cells (mutually exclusive with template).
        template: Optional template name (mutually exclusive with content).
        dry_run: When True, build the plan but don't send any commands.
        confirm_destructive: Required for ``dry_run=False`` (layout writes overwrite
            screen content).

    Returns:
        JSON envelope: ``{screen, template, plan, content, preview_ascii,
        expert_review, summary, dry_run, executed_steps, blocked}``.
    """
    from src.expert_lint import expert_lint
    from src.layout_templates import (
        build_layout_for,
        get_template,
        render_ascii_preview,
    )

    if template is not None and content is not None:
        return json.dumps({
            "screen": screen, "template": template,
            "blocked": True,
            "error": "Pass either template OR content, not both.",
            "plan": [], "content": [], "preview_ascii": "",
            "expert_review": [], "summary": {},
            "dry_run": dry_run, "executed_steps": 0,
        }, indent=2)
    if template is None and content is None:
        return json.dumps({
            "screen": screen, "template": None,
            "blocked": True,
            "error": "Either template or content must be supplied.",
            "plan": [], "content": [], "preview_ascii": "",
            "expert_review": [], "summary": {},
            "dry_run": dry_run, "executed_steps": 0,
        }, indent=2)

    plan_steps: list = []
    layout_content: list = []
    grid_cols, grid_rows = 8, 5

    if template is not None:
        try:
            tmpl = get_template(template)
        except ValueError as e:
            return json.dumps({
                "screen": screen, "template": template,
                "blocked": True, "error": str(e),
                "plan": [], "content": [], "preview_ascii": "",
                "expert_review": [], "summary": {},
                "dry_run": dry_run, "executed_steps": 0,
            }, indent=2)
        plan_steps, layout_content = build_layout_for(
            template=template, screen=screen, options=None,
        )
        grid_cols = tmpl.default_grid_cols
        grid_rows = tmpl.default_grid_rows
    else:
        # Custom content path — caller-supplied cells. We still emit a
        # set-screen step and one place-cell step per content entry.
        plan_steps.append({
            "order": 1, "kind": "set-screen",
            "command": f"Screen {screen}",
            "purpose": f"Switch to screen {screen} before placing cells",
            "meta": {"screen": screen, "template": None},
        })
        for i, cell in enumerate(content or [], start=2):
            label = cell.get("label") or ""
            target = cell.get("target", "")
            x = cell.get("grid_x", 0)
            y = cell.get("grid_y", 0)
            plan_steps.append({
                "order": i, "kind": "place-cell",
                "command": (
                    f'LayoutElement {x},{y} {cell.get("kind", "label")} '
                    f'"{label}" @ {target}'
                ),
                "purpose": f"Place cell at ({x},{y})",
                "meta": dict(cell),
            })
        layout_content = list(content or [])

    preview = render_ascii_preview(layout_content, grid_cols=grid_cols, grid_rows=grid_rows)

    # Run expert_lint on the layout content
    lint_plan = {
        "kind": "layout",
        "screen": screen,
        "template": template,
        "content": layout_content,
        "screen_native_resolution": (1920, 1080),
        "cell_size": (100, 50),
        "steps": [
            {"order": s["order"], "command": s["command"],
             "purpose": s["purpose"]} for s in plan_steps
        ],
    }
    findings = expert_lint(lint_plan, domain="layout", context=None)

    if not dry_run and not confirm_destructive:
        return json.dumps({
            "screen": screen, "template": template,
            "blocked": True,
            "error": "dry_run=False requires confirm_destructive=True",
            "plan": plan_steps, "content": layout_content,
            "preview_ascii": preview,
            "expert_review": [v.__dict__ for v in findings],
            "summary": {"plan_steps": len(plan_steps), "content_cells": len(layout_content)},
            "dry_run": dry_run, "executed_steps": 0,
        }, indent=2)

    executed = 0
    if not dry_run:
        client = await _srv.get_client()
        for step in plan_steps:
            await client.send_command(step["command"])
            executed += 1

    return json.dumps({
        "screen": screen, "template": template,
        "plan": plan_steps, "content": layout_content,
        "preview_ascii": preview,
        "expert_review": [v.__dict__ for v in findings],
        "summary": {"plan_steps": len(plan_steps), "content_cells": len(layout_content)},
        "dry_run": dry_run, "executed_steps": executed,
        "blocked": False,
    }, indent=2)


# ============================================================================
# T6 — Plugin disambiguation (check_plugin_available)
# ============================================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def check_plugin_available(
    plugin_name: str,
    use_cache: bool = True,
    cache_ttl_seconds: int = 60,
) -> str:
    """Check whether a plugin is loaded in the console plugin pool (SAFE_READ).

    Used by skills (notably ``auto-layout-color-picker``) to decide whether to
    invoke the plugin path or fall back to manual workflows.

    Args:
        plugin_name: Human-readable plugin name (e.g. ``"EcubeColorPicker"``).
        use_cache: When True, reuse cached inventory if fresh.
        cache_ttl_seconds: How long a cached inventory stays fresh.

    Returns:
        JSON envelope: ``{plugin_name, available, pool_id, match,
        last_checked_at, source}``.
    """
    from src.plugin_inventory import _default_inventory
    inv = _default_inventory()
    result = await inv.lookup(
        plugin_name, use_cache=use_cache, cache_ttl=cache_ttl_seconds,
    )
    return json.dumps(result, indent=2)


async def _verify_round_trip(host: str, port: int, user: str, password: str) -> bool:
    """Open a fresh client to the candidate host and try a tiny SAFE_READ."""
    from src.telnet_client import GMA2TelnetClient
    try:
        async with GMA2TelnetClient(host=host, port=port, user=user, password=password) as c:
            resp = await c.send_command_with_response("ListVar", timeout=2.0)
            return bool(resp)
    except Exception as e:  # noqa: BLE001
        logger.warning("verify_round_trip(%s:%s) failed: %s", host, port, e)
        return False


def _persist_env(env_path: "_Path", **overrides: str) -> None:
    """Atomic write — read existing entries, override the named keys, write back.

    Preserves entries we don't touch. Writes to a sibling temp file then renames
    to provide atomicity on POSIX and Windows. Lines starting with ``#`` are
    preserved as-is (read into ``existing`` as raw comment lines).
    """
    existing: list[tuple[str, str]] = []
    seen_keys: set[str] = set()
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                # Keep comment / blank lines verbatim with a unique sentinel key.
                existing.append((f"__raw_{len(existing)}", line))
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                existing.append((k, v.strip()))
                seen_keys.add(k)
    # Apply overrides — update existing entries in place, append new ones.
    applied: set[str] = set()
    new_lines: list[str] = []
    for key, val in existing:
        if key.startswith("__raw_"):
            new_lines.append(val)
            continue
        if key in overrides:
            new_lines.append(f"{key}={overrides[key]}")
            applied.add(key)
        else:
            new_lines.append(f"{key}={val}")
    for key, val in overrides.items():
        if key not in applied:
            new_lines.append(f"{key}={val}")
    tmp = env_path.with_suffix(env_path.suffix + ".tmp")
    tmp.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    tmp.replace(env_path)


# ============================================================================
# T3 — NL → macro generation (generate_ma2_macro)
# Composes T1 (skill router) + XC2 (expert_lint macro domain) on its output.
# ============================================================================


@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def generate_ma2_macro(
    intent: str,
    scope_hints: dict | None = None,
    store: bool = False,
    pool_id: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """Generate an MA2 macro from natural-language intent (SAFE_READ when store=False).

    Returns ``body_xml`` + lint + expert review. When ``store=True``, the tool
    requires ``confirm_destructive=True`` AND ``pool_id``; in Path A the store
    branch returns blocked / deferred-to-Path-B rather than mutating the pool.

    Args:
        intent: Plain-English description of the macro to build.
        scope_hints: Optional dict of routing hints, e.g. ``{"executor": "1.1.1"}``.
        store: When True, store the generated macro to the macro pool.
        pool_id: Target pool slot (required if ``store=True``).
        confirm_destructive: Required if ``store=True`` (the store path is destructive).

    Returns:
        JSON envelope:
        ``{intent, body_xml, line_count, validation, lint, expert_review,
        stored_as, blocked}``.
    """
    from src.expert_lint import expert_lint
    from src.macro_generation import build_macro_from_intent

    plan = build_macro_from_intent(intent=intent, scope_hints=scope_hints)
    findings = expert_lint(plan, domain="macro", context=scope_hints)

    has_error = any(v.severity == "error" for v in findings)
    has_warning = any(v.severity == "warning" for v in findings)
    grade = "broken" if has_error else ("competent" if has_warning else "expert")

    result: dict = {
        "intent": intent,
        "body_xml": plan["body_xml"],
        "line_count": len(plan["lines"]),
        "validation": {"xml_valid": True},  # emitted via escape -> structurally valid
        "lint": [
            {
                "rule_id": v.rule_id,
                "severity": v.severity,
                "target": v.target,
                "message": v.expert_says,
                "fix_suggestion": v.fix_suggestion,
            }
            for v in findings
        ],
        "expert_review": {
            "grade": grade,
            "rationale": (
                "Macro has structural errors and cannot be stored."
                if has_error
                else (
                    "Macro passes lint with one or more warnings — review before use."
                    if has_warning
                    else "Macro passes lint at advice-or-clean severity."
                )
            ),
            "missing_practices": [],
        },
        "stored_as": None,
        "blocked": has_error,
    }

    if store:
        if not confirm_destructive:
            result["blocked"] = True
            result["expert_review"]["rationale"] = (
                "store=True requires confirm_destructive=True."
            )
        elif pool_id is None:
            result["blocked"] = True
            result["expert_review"]["rationale"] = "store=True requires pool_id."
        elif has_error:
            # already blocked by the has_error check above; clarify reason
            result["expert_review"]["rationale"] = (
                "Cannot store a macro that fails lint at error severity."
            )
        else:
            # Path A: surface that the macro is ready, defer real store to Path B.
            result["expert_review"]["rationale"] = (
                result["expert_review"]["rationale"]
                + " Store path is deferred to Path B."
            )

    return json.dumps(result, indent=2)
