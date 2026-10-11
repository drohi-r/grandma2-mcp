"""MCP tools — fixture types. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
import re

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    store_preset as build_store_preset,
)
from src.server import (
    _handle_errors,
    logger,
    mcp,
)

# ============================================================
# Fixture-Type Intelligence — patch model, ID blocks, type-ordered
# selection, plugin orchestration, capability-aware presets
# ============================================================

_POOL_ID_RE_TMPL = r"^\s*{kw}\s+\d+\s+(\d+)"


def _parse_pool_ids(raw: str, keyword: str) -> list[int]:
    """Extract pool object IDs from a `list <keyword>` response."""
    pattern = re.compile(_srv._POOL_ID_RE_TMPL.format(kw=keyword), re.IGNORECASE | re.MULTILINE)
    return sorted({int(m.group(1)) for m in pattern.finditer(raw)})


async def _hydrate_fixture_type_model(discover_attributes: bool = False):
    """Read the patch and build a FixtureTypeModel (optionally with live
    per-type attribute discovery via the EditSetup tree)."""
    from src.fixture_types import build_fixture_type_model, parse_channel_type_rows
    from src.show_strategies.patch_reader import summarize_patch

    client = await _srv.get_client()
    patch = await summarize_patch(client)

    attributes_by_type: dict[str, set[str]] = {}
    if discover_attributes:
        for ft in patch.get("fixture_types", []):
            type_id = ft.get("id")
            long_name = ft.get("long_name", "")
            if not type_id or not long_name:
                continue
            try:
                await client.send_command_with_response("cd /")
                await client.send_command_with_response("cd EditSetup")
                await client.send_command_with_response("cd FixtureTypes")
                await client.send_command_with_response(f"cd {type_id}")
                await client.send_command_with_response("cd 1")
                await client.send_command_with_response("cd 1")
                raw = await client.send_command_with_response("list")
                attrs = parse_channel_type_rows(raw)
                if attrs:
                    attributes_by_type[long_name] = attrs
            except Exception as exc:  # noqa: BLE001 — per-type failure falls back
                logger.warning("Attribute discovery failed for %s: %s", long_name, exc)
            finally:
                await client.send_command_with_response("cd /")

    model = build_fixture_type_model(patch, attributes_by_type=attributes_by_type)
    return model, patch


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def analyze_patch_types(discover_attributes: bool = False) -> str:
    """
    Build a fixture-type model of the current patch (SAFE_READ).

    Groups patched fixtures by fixture type, classifies each type into a
    category (wash/mover/bar/strobe/blinder/conventional/other), and resolves
    attribute capabilities (dimmer/position/gobo/color_mix/beam/focus/control)
    either from live EditSetup attribute discovery or a curated fallback table.

    This is the foundation for verify_fixture_id_blocks,
    select_fixtures_by_type_order, run_preset_plugin, and
    create_presets_for_patch.

    Args:
        discover_attributes: When True, read each fixture type's ChannelType
            rows from the console (slower — several cd/list round-trips per
            type). When False, use the curated fallback capability table.

    Returns:
        str: JSON with types (capabilities, category, members), categories,
        unmatched_fixtures, fixture_count, risk_tier.
    """
    model, patch = await _srv._hydrate_fixture_type_model(discover_attributes)
    result = model.to_dict()
    result["showfile"] = patch.get("showfile", "")
    result["risk_tier"] = "SAFE_READ"
    return json.dumps(result, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def verify_fixture_id_blocks(discover_attributes: bool = False) -> str:
    """
    Verify fixture IDs against the 100-block numbering scheme (SAFE_READ).

    Scheme: 1-99 wash, 100-199 movers, 200-299 bars, 300-399 strobes,
    400-499 blinders. Reports per-category compliance, out-of-block fixtures,
    ID collisions, and a proposed renumbering plan (old_id -> new_id into the
    lowest free slot of the correct block).

    Preset/color-picker plugins depend on clean type blocks — run this before
    run_preset_plugin or plugin-driven preset creation.

    Args:
        discover_attributes: Passed through to the patch-model build.

    Returns:
        str: JSON report with categories, out_of_block, collisions,
        renumber_plan, proposed_commands, compliant, risk_tier.
    """
    from src.fixture_types import renumber_commands, verify_id_blocks

    model, _ = await _srv._hydrate_fixture_type_model(discover_attributes)
    report = verify_id_blocks(model)
    report["proposed_commands"] = renumber_commands(report["renumber_plan"])
    report["risk_tier"] = "SAFE_READ"
    return json.dumps(report, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def renumber_fixtures(
    dry_run: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """
    Plan renumbering of out-of-block fixtures into their category's 100-block (PLAN-ONLY).

    Re-reads the patch fresh (never acts on a stale model) and computes the
    renumbering plan from verify_fixture_id_blocks. This tool NEVER executes:
    fixture IDs cannot be changed over telnet — live-verified 2026-07-17
    (v3.9.60.50): ``Assign Fixture <old> /fixid=<new>`` and every
    property-assign variant (FixId/ChaId at root, in the EditSetup and
    LiveSetup layer contexts, and via ``Move``) return Error #66 CANNOT
    ASSIGN, while sibling properties like ``/name=`` apply fine — the FixId
    column is console-side read-only. Renumbering must be done by the
    operator in Setup → Patch & Fixture Schedule; the returned ``commands``
    are manual dialog steps.

    Args:
        dry_run: Retained for API compatibility; every call is a dry run.
        confirm_destructive: Retained for API compatibility; execution is
            never possible, so this flag has no effect.

    Returns:
        str: JSON with renumber_plan, commands (manual operator steps),
        executed (always 0), plan_only, blocked, risk_tier.
    """
    from src.fixture_types import renumber_commands, verify_id_blocks

    model, _ = await _srv._hydrate_fixture_type_model(False)
    report = verify_id_blocks(model)
    commands = renumber_commands(report["renumber_plan"])
    envelope = {
        "renumber_plan": report["renumber_plan"],
        "collisions": report["collisions"],
        "commands": commands,
        "warning": (
            "Renumbering changes fixture IDs referenced by groups, presets, "
            "and macros. Verify references before renumbering in the dialog."
        ),
        "plan_only": True,
        "plan_only_reason": (
            "Fixture IDs cannot be changed over telnet on grandMA2 "
            "(live-verified 2026-07-17, v3.9.60.50: every FixId assign "
            "variant returns Error #66 CANNOT ASSIGN). Apply the steps in "
            "Setup → Patch & Fixture Schedule, then re-run "
            "verify_fixture_id_blocks to confirm."
        ),
        "dry_run": True,
        "executed": 0,
        "risk_tier": "SAFE_READ",
    }
    if not dry_run:
        envelope["blocked"] = True
        envelope["error"] = envelope["plan_only_reason"]
    return json.dumps(envelope, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def select_fixtures_by_type_order(
    order: list[str] | None = None,
    execute: bool = False,
    clear_first: bool = True,
) -> str:
    """
    Build (and optionally execute) a type-ordered fixture selection (SAFE_WRITE).

    Emits one additive ``Fixture <ranges>`` command per fixture type, in
    canonical category order (wash, mover, bar, strobe, blinder,
    conventional, other) or a custom order — so the console's selection
    order matches fixture-type order, which is what preset/color-picker
    plugins require at runtime. Works even when ID blocks are dirty.

    Args:
        order: Optional custom category order (subset of the canonical list).
        execute: When True, send the commands to the console; when False
            (default) return them for embedding in a macro or workflow.
        clear_first: Prepend ClearAll so selection order is deterministic.

    Returns:
        str: JSON with commands, executed, selection_order (types in emission
        order), risk_tier.
    """
    from src.fixture_types import CATEGORY_ORDER, build_type_ordered_selection

    model, _ = await _srv._hydrate_fixture_type_model(False)
    commands = build_type_ordered_selection(model, order=order, clear_first=clear_first)
    by_cat = model.by_category()
    selection_order = [
        rec.name
        for cat in (order or CATEGORY_ORDER)
        for rec in by_cat.get(cat, [])
    ]

    executed = 0
    if execute:
        client = await _srv.get_client()
        for cmd in commands:
            await client.send_command_with_response(cmd)
            executed += 1

    return json.dumps({
        "commands": commands,
        "selection_order": selection_order,
        "executed": executed,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def run_preset_plugin(
    plugin_name: str,
    manifest_overrides: dict | None = None,
    dry_run: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """
    Orchestrate a preset/color-picker plugin run end-to-end (DESTRUCTIVE).

    Pipeline: (1) resolve the plugin in the pool; (2) verify preconditions
    from its manifest — required groups exist, declared pool ranges are free;
    (3) build the type-ordered fixture selection the plugin expects;
    (4) run the plugin; (5) diff the output pools and report what was created.

    Manifests for known plugins ship in src/plugin_manifests.py (e.g.
    "auto-layout-color-picker"); pass manifest_overrides to adjust pool
    ranges or required groups per show, or to describe an unknown plugin.

    Args:
        plugin_name: Plugin pool name or builtin manifest key.
        manifest_overrides: Optional dict overriding manifest fields
            (pool_ranges, required_groups, selection, outputs).
        dry_run: When True (default) run only phases 1-3 and report the plan.
        confirm_destructive: Must be True to execute with dry_run=False.

    Returns:
        str: JSON with plugin, preconditions, selection_commands, executed,
        outputs_created (per pool diff), blocked, risk_tier.
    """
    from src.fixture_types import build_type_ordered_selection
    from src.plugin_inventory import _default_inventory
    from src.plugin_manifests import get_manifest, merge_manifest, occupied_ids_in_range

    manifest = merge_manifest(get_manifest(plugin_name), manifest_overrides)
    lookup_name = manifest.get("name") or plugin_name

    inv = _default_inventory()
    availability = await inv.lookup(lookup_name, use_cache=False, cache_ttl=0)
    if not availability["available"]:
        return json.dumps({
            "plugin": lookup_name,
            "blocked": True,
            "error": f"Plugin {lookup_name!r} not found in the plugin pool.",
            "availability": availability,
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await _srv.get_client()

    # Precondition checks
    preconditions: list[dict] = []
    ok = True
    required_groups = manifest.get("required_groups") or []
    if required_groups:
        raw = await client.send_command_with_response("list group", timeout=3.0)
        existing = set(_srv._parse_pool_ids(raw, "Group"))
        for gid in required_groups:
            passed = gid in existing
            ok = ok and passed
            preconditions.append({
                "check": f"group {gid} exists", "passed": passed,
            })
    for pool_type, rng in (manifest.get("pool_ranges") or {}).items():
        start, end = int(rng[0]), int(rng[1])
        raw = await client.send_command_with_response(f"list {pool_type}", timeout=3.0)
        occupied = occupied_ids_in_range(_srv._parse_pool_ids(raw, pool_type), start, end)
        passed = not occupied
        ok = ok and passed
        preconditions.append({
            "check": f"{pool_type} pool {start}-{end} free",
            "passed": passed,
            "occupied": occupied,
        })

    selection_commands: list[str] = []
    if manifest.get("selection", "type-ordered") == "type-ordered":
        model, _ = await _srv._hydrate_fixture_type_model(False)
        selection_commands = build_type_ordered_selection(model)

    envelope: dict = {
        "plugin": lookup_name,
        "pool_id": availability["pool_id"],
        "preconditions": preconditions,
        "preconditions_ok": ok,
        "selection_commands": selection_commands,
        "dry_run": dry_run,
        "executed": False,
        "risk_tier": "DESTRUCTIVE",
    }
    if dry_run:
        return json.dumps(envelope, indent=2)
    if not confirm_destructive:
        envelope["blocked"] = True
        envelope["error"] = (
            "Running a plugin modifies show data. Set confirm_destructive=True to proceed."
        )
        return json.dumps(envelope, indent=2)
    if not ok:
        envelope["blocked"] = True
        envelope["error"] = "Preconditions failed — fix them or override the manifest."
        return json.dumps(envelope, indent=2)

    # Snapshot output pools before the run
    output_pools = manifest.get("outputs") or []
    before: dict[str, list[int]] = {}
    for pool_type in output_pools:
        raw = await client.send_command_with_response(f"list {pool_type}", timeout=3.0)
        before[pool_type] = _srv._parse_pool_ids(raw, pool_type)

    for cmd in selection_commands:
        await client.send_command_with_response(cmd)
    await client.send_command_with_response(f"Plugin {availability['pool_id']}")

    outputs_created: dict[str, list[int]] = {}
    for pool_type in output_pools:
        raw = await client.send_command_with_response(f"list {pool_type}", timeout=3.0)
        after = _srv._parse_pool_ids(raw, pool_type)
        outputs_created[pool_type] = sorted(set(after) - set(before[pool_type]))

    envelope["executed"] = True
    envelope["outputs_created"] = outputs_created
    envelope["output_verified"] = any(v for v in outputs_created.values())
    if output_pools and not envelope["output_verified"]:
        envelope["warning"] = (
            "Plugin ran but no new objects appeared in its output pools — "
            "check the precondition report and the plugin's own feedback."
        )
    return json.dumps(envelope, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PRESET_UPDATE)
@_handle_errors
async def create_presets_for_patch(
    strategy: str = "full-coverage",
    dry_run: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """
    Create presets natively from the patch, capability-aware (DESTRUCTIVE).

    Combines the preset-library architect plan (architect_preset_library)
    with the fixture-type model: each preset entry is only applied to
    fixtures whose type actually has the required capability (color presets
    to color-mixing fixtures, position to movers, etc.).

    Entries with concrete values (the cardinal color presets) are stored
    directly: selection of capable fixtures -> attribute values -> Store
    Preset. Entries declared without concrete values (position, gobo, MIB —
    which need operator-set reference values) are returned as ``declared``
    for manual completion, matching the declared-vs-stored calibration.

    Args:
        strategy: full-coverage | minimal-viable | color-first.
        dry_run: When True (default), return the command plan without executing.
        confirm_destructive: Must be True to execute with dry_run=False.

    Returns:
        str: JSON with stored_plan (per-preset command lists), declared_only,
        skipped (no capable fixtures), executed_presets, blocked, risk_tier.
    """
    from src.fixture_types import PRESET_TYPE_CAPABILITY, _compress_ranges
    from src.preset_strategies import architect_preset_library_for, get_preset_strategy

    try:
        get_preset_strategy(strategy)
    except ValueError as e:
        return json.dumps({
            "strategy": strategy, "blocked": True, "error": str(e),
            "stored_plan": [], "declared_only": [], "skipped": [],
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    model, patch = await _srv._hydrate_fixture_type_model(False)
    result = architect_preset_library_for(strategy=strategy, patch=patch, options=None)

    type_names = {1: "dimmer", 2: "position", 3: "gobo", 4: "color",
                  5: "beam", 6: "focus", 7: "control"}
    stored_plan: list[dict] = []
    declared_only: list[dict] = []
    skipped: list[dict] = []

    for entry in result["plan"]:
        ptype = entry.get("preset_type")
        flag = PRESET_TYPE_CAPABILITY.get(ptype)
        capable = model.types_with_capability(flag) if flag else []
        if not capable:
            skipped.append({**entry, "reason": f"no fixture type has {flag}"})
            continue
        values = entry.get("values") or {}
        rgb = values.get("rgb")
        if not rgb:
            declared_only.append({
                **entry,
                "capable_types": [r.name for r in capable],
                "reason": "no concrete values — needs operator reference store",
            })
            continue
        member_ids = sorted(i for r in capable for i in r.member_ids)
        spec = _compress_ranges(member_ids)
        commands = [
            "ClearAll",
            f"Fixture {spec}",
            f'Attribute "ColorRgb1" At {rgb[0]}',
            f'Attribute "ColorRgb2" At {rgb[1]}',
            f'Attribute "ColorRgb3" At {rgb[2]}',
            build_store_preset(
                type_names[ptype], entry["preset_id"],
                universal=(entry.get("scope") == "universal"),
                selective=(entry.get("scope") == "selective"),
                overwrite=True,
            ),
            f'Label Preset {ptype}.{entry["preset_id"]} "{entry["name"]}"',
            "ClearAll",
        ]
        stored_plan.append({
            "preset": f"{ptype}.{entry['preset_id']}",
            "name": entry["name"],
            "capable_types": [r.name for r in capable],
            "fixture_count": len(member_ids),
            "commands": commands,
        })

    envelope: dict = {
        "strategy": strategy,
        "stored_plan": stored_plan,
        "declared_only": declared_only,
        "skipped": skipped,
        "coverage_report": result["coverage_report"],
        "dry_run": dry_run,
        "executed_presets": 0,
        "risk_tier": "DESTRUCTIVE",
    }
    if dry_run:
        return json.dumps(envelope, indent=2)
    if not confirm_destructive:
        envelope["blocked"] = True
        envelope["error"] = (
            "Storing presets modifies show data. Set confirm_destructive=True to proceed."
        )
        return json.dumps(envelope, indent=2)

    client = await _srv.get_client()
    executed = 0
    for item in stored_plan:
        for cmd in item["commands"]:
            await client.send_command_with_response(cmd)
        executed += 1
    envelope["executed_presets"] = executed
    envelope["blocked"] = False
    return json.dumps(envelope, indent=2)
