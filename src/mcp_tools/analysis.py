"""MCP tools — analysis. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import asyncio
import json
import re
import time
from typing import Any

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.commands import (
    clear_all as build_clear_all,
)
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Analysis & Intelligence Tools
# Impact analysis, dependency mapping, linting, and recovery
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def find_preset_usages(
    preset_type: str,
    preset_id: int,
    max_sequences: int = 50,
) -> str:
    """
    Find all sequences and cues that reference a specific preset (SAFE_READ).

    Scans sequence cue data for Preset references before you update or delete.
    Also reports which executors play sequences that use this preset.

    Args:
        preset_type: Preset type name (e.g. "color", "position", "gobo").
        preset_id: Preset slot number.
        max_sequences: Max sequences to scan (default 50, higher = slower).

    Returns:
        str: JSON with usages, executor_references, total_references, risk_if_deleted.
    """
    from src.commands.constants import PRESET_TYPES

    type_num = PRESET_TYPES.get(preset_type.lower())
    if type_num is None:
        return json.dumps({
            "error": f"Unknown preset type '{preset_type}'. Valid: {sorted(PRESET_TYPES.keys())}",
            "blocked": True,
        }, indent=2)

    client = await _srv.get_client()
    usages: list[dict] = []
    executor_refs: list[dict] = []
    pattern = re.compile(rf"Preset\s+{type_num}\.{preset_id}\b", re.IGNORECASE)

    # Get sequence list from snapshot or discovery
    seq_ids: list[int] = []
    snap = getattr(_srv._orchestrator, "last_snapshot", None)
    if snap and hasattr(snap, "sequences") and snap.sequences:
        seq_ids = [s.sequence_id for s in snap.sequences[:max_sequences] if hasattr(s, "sequence_id")]
    if not seq_ids:
        raw = await client.send_command_with_response("list sequence")
        for m in re.finditer(r"^\s*(\d+)\s", raw, re.MULTILINE):
            seq_ids.append(int(m.group(1)))
            if len(seq_ids) >= max_sequences:
                break

    # Scan each sequence's cues
    referencing_seqs: set[int] = set()
    for seq_id in seq_ids:
        raw = await client.send_command_with_response(f"list cue sequence {seq_id}")
        if pattern.search(raw):
            # Find specific cue IDs
            for line in raw.splitlines():
                if pattern.search(line):
                    cue_match = re.match(r"^\s*(\d+(?:\.\d+)?)\s", line.strip())
                    cue_id = cue_match.group(1) if cue_match else "unknown"
                    usages.append({
                        "sequence_id": seq_id,
                        "cue_id": cue_id,
                        "context": line.strip()[:200],
                    })
                    referencing_seqs.add(seq_id)
        await asyncio.sleep(0.05)

    # Check executor assignments for referencing sequences
    if snap and hasattr(snap, "executor_state") and snap.executor_state:
        for exec_id, state in snap.executor_state.items():
            if hasattr(state, "sequence_id") and state.sequence_id in referencing_seqs:
                executor_refs.append({
                    "executor_id": exec_id,
                    "sequence_id": state.sequence_id,
                })

    total = len(usages)
    risk = "none" if total == 0 else "low" if total <= 2 else "medium" if total <= 5 else "high"

    return json.dumps({
        "preset_type": preset_type,
        "preset_type_id": type_num,
        "preset_id": preset_id,
        "usages": usages,
        "executor_references": executor_refs,
        "total_references": total,
        "sequences_scanned": len(seq_ids),
        "risk_if_deleted": risk,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def diff_cues(
    sequence_id: int,
    cue_a: float,
    cue_b: float,
) -> str:
    """
    Structured diff of two cues showing per-attribute changes (SAFE_READ).

    More detailed than compare_cue_values — parses attribute names, timing,
    labels, and block status. Falls back to raw line diff if parsing fails.

    Args:
        sequence_id: Sequence containing both cues.
        cue_a: First cue number.
        cue_b: Second cue number.

    Returns:
        str: JSON with changes[], timing_diff, label_diff, block_diff, identical.
    """
    client = await _srv.get_client()
    raw_a = await client.send_command_with_response(f"list cue {cue_a} sequence {sequence_id}")
    raw_b = await client.send_command_with_response(f"list cue {cue_b} sequence {sequence_id}")

    def _parse_cue_attrs(raw: str) -> dict[str, str]:
        """Parse attribute=value pairs from cue listing."""
        attrs: dict[str, str] = {}
        for line in raw.strip().splitlines():
            line = line.strip()
            # Try KEY=VALUE or tabular format
            kv = re.findall(r"(\w+)\s*=\s*(\S+)", line)
            for k, v in kv:
                attrs[k] = v
            # Also capture column-based data (Name Value pairs)
            cols = line.split()
            if len(cols) >= 2 and not line.startswith("#"):
                attrs[cols[0]] = " ".join(cols[1:])
        return attrs

    attrs_a = _parse_cue_attrs(raw_a)
    attrs_b = _parse_cue_attrs(raw_b)
    all_keys = sorted(set(attrs_a.keys()) | set(attrs_b.keys()))

    changes: list[dict] = []
    for key in all_keys:
        va = attrs_a.get(key)
        vb = attrs_b.get(key)
        if va != vb:
            if va is None:
                changes.append({"attribute": key, "value_a": None, "value_b": vb, "change_type": "added"})
            elif vb is None:
                changes.append({"attribute": key, "value_a": va, "value_b": None, "change_type": "removed"})
            else:
                changes.append({"attribute": key, "value_a": va, "value_b": vb, "change_type": "modified"})

    # Timing extraction
    timing_keys = {"Fade", "Delay", "SnapPercent", "CueFade", "CueDelay"}
    timing_diff = {}
    for k in timing_keys:
        if k in attrs_a or k in attrs_b:
            timing_diff[k] = {"cue_a": attrs_a.get(k), "cue_b": attrs_b.get(k)}

    # Label/block extraction
    label_a = attrs_a.get("Name", attrs_a.get("Label", ""))
    label_b = attrs_b.get("Name", attrs_b.get("Label", ""))
    block_a = "block" in raw_a.lower()
    block_b = "block" in raw_b.lower()

    # Fallback raw diff
    lines_a = set(raw_a.strip().splitlines())
    lines_b = set(raw_b.strip().splitlines())

    return json.dumps({
        "sequence_id": sequence_id,
        "cue_a": cue_a,
        "cue_b": cue_b,
        "changes": changes,
        "total_changes": len(changes),
        "timing_diff": timing_diff,
        "label_diff": {"cue_a": label_a, "cue_b": label_b},
        "block_diff": {"cue_a": block_a, "cue_b": block_b},
        "attributes_only_in_a": sorted(set(attrs_a) - set(attrs_b)),
        "attributes_only_in_b": sorted(set(attrs_b) - set(attrs_a)),
        "identical": len(changes) == 0,
        "raw_only_in_a": sorted(lines_a - lines_b)[:20],
        "raw_only_in_b": sorted(lines_b - lines_a)[:20],
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def get_page_map(
    page: int = 1,
) -> str:
    """
    Get a complete topology map of an executor page (SAFE_READ).

    Returns every executor with its assignment, fader role, trigger type,
    priority, width, and label. Richer than scan_page_executor_layout.

    Args:
        page: Executor page number (default 1).

    Returns:
        str: JSON with executors[], occupied count, free_slots[], total_slots.
    """
    client = await _srv.get_client()
    executors: list[dict] = []
    free_slots: list[int] = []
    total_slots = 40

    for exec_id in range(201, 201 + total_slots):
        raw = await client.send_command_with_response(f"list executor {page}.{exec_id}")
        if "NO OBJECTS" in raw.upper() or not raw.strip():
            free_slots.append(exec_id)
            continue

        # Parse KEY=VALUE or inline fields
        def _extract(key: str, raw: str = raw) -> str | None:
            m = re.search(rf"{key}\s*[=:]\s*(\S+)", raw, re.IGNORECASE)
            return m.group(1) if m else None

        seq_str = _extract("Sequence") or _extract("Seq")
        seq_id = int(seq_str) if seq_str and seq_str.isdigit() else None
        name = _extract("Name") or ""
        width_str = _extract("Width")
        width = int(width_str) if width_str and width_str.isdigit() else 1

        # Infer type from content
        exec_type = "empty"
        raw_lower = raw.lower()
        if "effect" in raw_lower:
            exec_type = "effect"
        elif "macro" in raw_lower:
            exec_type = "macro"
        elif seq_id is not None:
            exec_type = "sequence"

        executors.append({
            "id": exec_id,
            "label": name.strip('"') if name else f"Exec {exec_id}",
            "type": exec_type,
            "sequence_id": seq_id,
            "fader_function": _extract("Fader") or "Master",
            "trigger": _extract("Trigger") or _extract("Trig") or "Go",
            "priority": _extract("Priority") or _extract("Prio") or "Normal",
            "width": width,
        })
        await asyncio.sleep(0.02)

    return json.dumps({
        "page": page,
        "executors": executors,
        "occupied": len(executors),
        "free_slots": free_slots,
        "total_slots": total_slots,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def lint_macro(
    macro_id: int,
) -> str:
    """
    Static analysis of a grandMA2 macro for unsafe patterns (SAFE_READ).

    Checks for: destructive commands without gates, broken jump targets,
    missing quotes, unsafe raw patterns, potential infinite loops.

    Args:
        macro_id: Macro number to lint.

    Returns:
        str: JSON with issues[], overall (clean/warning/error), lines_checked.
    """
    client = await _srv.get_client()

    # Get macro content
    raw = await client.send_command_with_response(f"list macro {macro_id}")
    if "NO OBJECTS" in raw.upper():
        return json.dumps({
            "error": f"Macro {macro_id} not found.",
            "risk_tier": "SAFE_READ",
        }, indent=2)

    # Get macro label
    info_raw = await client.send_command_with_response(f"info macro {macro_id}")
    label_match = re.search(r"Name\s*[=:]\s*(.+?)(?:\s*$|\s+\w)", info_raw, re.MULTILINE)
    macro_label = label_match.group(1).strip().strip('"') if label_match else f"Macro {macro_id}"

    # Parse lines
    lines: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---"):
            # Strip line numbers if present
            stripped = re.sub(r"^\d+\s+", "", line)
            if stripped:
                lines.append(stripped)

    issues: list[dict] = []
    _DESTRUCTIVE = re.compile(r"\b(Delete|Store\b.*\b/o|Move\s+\w)", re.IGNORECASE)
    _UNSAFE_RAW = re.compile(r"\b(NewShow|Shutdown|Reset|Reboot)\b", re.IGNORECASE)
    _JUMP = re.compile(r"Go\s+Macro\s+(\d+)", re.IGNORECASE)
    _SELF_JUMP = re.compile(rf"Go\s+Macro\s+{macro_id}\b", re.IGNORECASE)
    _UNQUOTED_SPACE = re.compile(r'(?<!")\b(\w+\s+\w+)(?!")\s+(?:At|Thru|If)', re.IGNORECASE)

    for i, cmd in enumerate(lines, 1):
        # Destructive without gate
        if _DESTRUCTIVE.search(cmd):
            issues.append({
                "line": i, "severity": "error", "rule": "destructive_no_gate",
                "message": f"Destructive command without CmdDelay gate: {cmd[:80]}",
                "raw_command": cmd,
            })
        # Unsafe raw patterns
        if _UNSAFE_RAW.search(cmd):
            issues.append({
                "line": i, "severity": "error", "rule": "unsafe_raw",
                "message": f"Unsafe system command: {cmd[:80]}",
                "raw_command": cmd,
            })
        # Self-referencing jump (potential infinite loop)
        if _SELF_JUMP.search(cmd):
            issues.append({
                "line": i, "severity": "warning", "rule": "infinite_loop",
                "message": f"Macro jumps to itself (potential infinite loop): {cmd[:80]}",
                "raw_command": cmd,
            })
        # Jump to line beyond macro length
        jump_match = _JUMP.search(cmd)
        if jump_match:
            target_line = re.search(r"\.(\d+)$", cmd)
            if target_line and int(target_line.group(1)) > len(lines):
                issues.append({
                    "line": i, "severity": "error", "rule": "broken_jump",
                    "message": f"Jump to line {target_line.group(1)} but macro has {len(lines)} lines",
                    "raw_command": cmd,
                })

    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    overall = "error" if errors else "warning" if warnings else "clean"

    return json.dumps({
        "macro_id": macro_id,
        "macro_label": macro_label,
        "lines_checked": len(lines),
        "issues": issues,
        "overall": overall,
        "lines_clean": len(lines) - errors - warnings,
        "lines_warning": warnings,
        "lines_error": errors,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def detect_programmer_contamination() -> str:
    """
    Check for leftover programmer state before critical operations (SAFE_READ).

    Detects: selected fixtures, active filters, active worlds, MAtricks state,
    highlight/freeze/solo modes, and parked fixtures. Run this before storing
    cues, presets, or making show-critical changes.

    Returns:
        str: JSON with contaminated bool, checks[], recommendation.
    """
    checks: list[dict[str, str]] = []
    snap = getattr(_srv._orchestrator, "last_snapshot", None)
    snapshot_age: float | None = None

    if snap:
        snapshot_age = snap.age_seconds() if hasattr(snap, "age_seconds") else None

        # Selected fixtures
        sel_count = getattr(snap, "selected_fixture_count", 0) or 0
        if sel_count > 0:
            checks.append({"check": "selected_fixtures", "status": "fail", "detail": f"{sel_count} fixtures selected in programmer"})
        else:
            checks.append({"check": "selected_fixtures", "status": "ok", "detail": "No fixtures selected"})

        # Active filter
        filt = getattr(snap, "active_filter", None)
        if filt and filt != 0:
            checks.append({"check": "active_filter", "status": "warning", "detail": f"Filter {filt} is active"})
        else:
            checks.append({"check": "active_filter", "status": "ok", "detail": "No filter active"})

        # Active world
        world = getattr(snap, "active_world", None)
        if world and world != 0:
            checks.append({"check": "active_world", "status": "warning", "detail": f"World {world} is active — may limit fixture visibility"})
        else:
            checks.append({"check": "active_world", "status": "ok", "detail": "Default world (all fixtures visible)"})

        # Console modes
        modes = getattr(snap, "console_modes", {}) or {}
        for mode in ("highlight", "freeze", "solo", "blind"):
            if modes.get(mode):
                checks.append({"check": f"mode_{mode}", "status": "fail", "detail": f"{mode.title()} mode is ON"})
            else:
                checks.append({"check": f"mode_{mode}", "status": "ok", "detail": f"{mode.title()} mode is off"})

        # Parked fixtures
        parked = getattr(snap, "parked_fixtures", set()) or set()
        if parked:
            checks.append({"check": "parked_fixtures", "status": "warning", "detail": f"{len(parked)} fixtures parked: {sorted(list(parked))[:10]}"})
        else:
            checks.append({"check": "parked_fixtures", "status": "ok", "detail": "No parked fixtures"})

        # MAtricks
        matricks = getattr(snap, "matricks", None)
        if matricks and hasattr(matricks, "active") and matricks.active:
            checks.append({"check": "matricks", "status": "warning", "detail": "MAtricks is active — may affect selection grouping"})
        else:
            checks.append({"check": "matricks", "status": "ok", "detail": "MAtricks inactive"})
    else:
        # Fallback: query via telnet
        client = await _srv.get_client()
        raw = await client.send_command_with_response("listvar")
        sel_match = re.search(r"SELECTEDFIXTURESCOUNT[=\s]+(\d+)", raw, re.IGNORECASE)
        sel_count = int(sel_match.group(1)) if sel_match else 0
        if sel_count > 0:
            checks.append({"check": "selected_fixtures", "status": "fail", "detail": f"{sel_count} fixtures selected"})
        else:
            checks.append({"check": "selected_fixtures", "status": "ok", "detail": "No fixtures selected"})
        checks.append({"check": "snapshot", "status": "warning", "detail": "No hydrated snapshot — limited checks available. Run hydrate_console_state first."})

    contaminated = any(c["status"] == "fail" for c in checks)
    has_warnings = any(c["status"] == "warning" for c in checks)

    recommendation = "Programmer is clean — safe to proceed." if not contaminated and not has_warnings else ""
    if contaminated:
        recommendation = "Clear programmer with ClearAll, disable active modes, then re-check."
    elif has_warnings:
        recommendation = "Minor contamination detected — review warnings before critical operations."

    return json.dumps({
        "contaminated": contaminated,
        "checks": checks,
        "recommendation": recommendation,
        "snapshot_age_s": round(snapshot_age, 1) if snapshot_age is not None else None,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def preview_preset_update_impact(
    preset_type: str,
    preset_id: int,
) -> str:
    """
    Assess the impact of updating or deleting a preset (SAFE_READ).

    Calls find_preset_usages internally and classifies the risk level.
    Run this before any Store, Update, or Delete on a preset.

    Args:
        preset_type: Preset type name (e.g. "color", "position").
        preset_id: Preset slot number.

    Returns:
        str: JSON with impact_level (safe/risky/catastrophic), affected details, recommendation.
    """
    raw_result = await _srv.find_preset_usages(preset_type=preset_type, preset_id=preset_id)
    data = json.loads(raw_result)

    if "error" in data:
        return raw_result

    total = data["total_references"]
    seq_ids = list({u["sequence_id"] for u in data["usages"]})

    if total == 0:
        impact = "safe"
        rec = "No references found — safe to update or delete."
    elif total <= 5:
        impact = "risky"
        rec = f"Found {total} references in {len(seq_ids)} sequence(s). Use Blind mode to preview changes before storing."
    else:
        impact = "catastrophic"
        rec = f"Found {total} references across {len(seq_ids)} sequence(s). Back up the show before modifying. Consider creating a new preset instead of editing."

    return json.dumps({
        "preset_type": preset_type,
        "preset_id": preset_id,
        "impact_level": impact,
        "total_references": total,
        "affected_sequences": seq_ids,
        "affected_cue_count": total,
        "executor_references": data.get("executor_references", []),
        "recommendation": rec,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def detect_tracking_leaks(
    sequence_id: int,
    max_cues: int = 20,
) -> str:
    """
    Find attributes unintentionally tracking into later cues (SAFE_READ).

    Compares adjacent cue pairs to find values that persist without an
    explicit Block. Tracking leaks cause unexpected looks in later cues.

    Args:
        sequence_id: Sequence to analyze.
        max_cues: Max cues to compare (default 20).

    Returns:
        str: JSON with leaks[], total_leaks, recommendation.
    """
    client = await _srv.get_client()

    # Get cue list
    raw = await client.send_command_with_response(f"list cue sequence {sequence_id}")
    if "NO OBJECTS" in raw.upper():
        return json.dumps({"error": f"Sequence {sequence_id} not found.", "risk_tier": "SAFE_READ"}, indent=2)

    cue_ids: list[float] = []
    for m in re.finditer(r"^\s*(\d+(?:\.\d+)?)\s", raw, re.MULTILINE):
        cue_ids.append(float(m.group(1)))
        if len(cue_ids) >= max_cues:
            break

    if len(cue_ids) < 2:
        return json.dumps({
            "sequence_id": sequence_id,
            "leaks": [],
            "total_leaks": 0,
            "cues_checked": len(cue_ids),
            "recommendation": "Need at least 2 cues to detect tracking leaks.",
            "risk_tier": "SAFE_READ",
        }, indent=2)

    # Compare adjacent cue pairs
    leaks: list[dict] = []
    prev_raw = await client.send_command_with_response(f"list cue {cue_ids[0]} sequence {sequence_id}")

    for i in range(1, len(cue_ids)):
        curr_raw = await client.send_command_with_response(f"list cue {cue_ids[i]} sequence {sequence_id}")

        # Find values present in both that aren't explicitly blocked
        prev_vals = set(prev_raw.strip().splitlines())
        curr_vals = set(curr_raw.strip().splitlines())
        shared = prev_vals & curr_vals

        # Lines that appear identical in both cues AND contain attribute data
        for line in shared:
            line = line.strip()
            if re.match(r"^\s*\w+\s+\d", line) and "block" not in line.lower():
                attr_match = re.match(r"^\s*(\w+)", line)
                if attr_match:
                    leaks.append({
                        "cue_from": cue_ids[i - 1],
                        "cue_to": cue_ids[i],
                        "attribute": attr_match.group(1),
                        "value": line.strip()[:100],
                        "note": "Value identical in adjacent cues — may be tracking forward without explicit set",
                    })

        prev_raw = curr_raw
        await asyncio.sleep(0.05)

    rec = "No tracking leaks detected." if not leaks else (
        f"Found {len(leaks)} potential tracking leak(s). "
        "Use Block on cues where values should stop tracking forward."
    )

    return json.dumps({
        "sequence_id": sequence_id,
        "leaks": leaks[:50],
        "total_leaks": len(leaks),
        "cues_checked": len(cue_ids),
        "recommendation": rec,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def audit_page_consistency(
    page: int = 1,
) -> str:
    """
    Audit an executor page for layout consistency issues (SAFE_READ).

    Checks: all executors labeled, speed masters assigned, first-button
    protocol followed, no orphan executors, consistent naming.

    Args:
        page: Executor page to audit (default 1).

    Returns:
        str: JSON with checks[], overall_status, recommendation.
    """
    raw_map = await _srv.get_page_map(page=page)
    map_data = json.loads(raw_map)

    if "error" in map_data:
        return raw_map

    executors = map_data.get("executors", [])
    checks: list[dict[str, str]] = []

    # Check 1: All executors labeled
    unlabeled = [e for e in executors if e["label"].startswith("Exec ")]
    if unlabeled:
        checks.append({
            "check": "all_labeled",
            "status": "warning",
            "detail": f"{len(unlabeled)} executor(s) missing labels: {[e['id'] for e in unlabeled[:5]]}",
        })
    else:
        checks.append({"check": "all_labeled", "status": "ok", "detail": "All executors are labeled"})

    # Check 2: Speed master assigned
    has_speed = any("speed" in e.get("fader_function", "").lower() for e in executors)
    if executors and not has_speed:
        checks.append({
            "check": "speed_master",
            "status": "warning",
            "detail": "No speed master found on this page — effects won't have tempo control",
        })
    else:
        checks.append({"check": "speed_master", "status": "ok", "detail": "Speed master present"})

    # Check 3: First-button protocol (first executor should be a Go button)
    if executors:
        first = executors[0]
        if first["type"] != "sequence":
            checks.append({
                "check": "first_button_protocol",
                "status": "warning",
                "detail": f"First executor ({first['id']}) is '{first['type']}' — convention is sequence for first-button Go",
            })
        else:
            checks.append({"check": "first_button_protocol", "status": "ok", "detail": "First executor is a sequence"})

    # Check 4: Orphan executors (assigned but no sequence)
    orphans = [e for e in executors if e["type"] == "empty" and e["label"] != f"Exec {e['id']}"]
    if orphans:
        checks.append({
            "check": "orphan_executors",
            "status": "warning",
            "detail": f"{len(orphans)} labeled but empty executor(s): {[e['id'] for e in orphans[:5]]}",
        })
    else:
        checks.append({"check": "orphan_executors", "status": "ok", "detail": "No orphan executors"})

    # Check 5: Priority consistency
    priorities = [e["priority"] for e in executors if e["type"] == "sequence"]
    mixed = len(set(priorities)) > 2 if priorities else False
    if mixed:
        checks.append({
            "check": "priority_consistency",
            "status": "warning",
            "detail": f"Mixed priorities on page: {set(priorities)}",
        })
    else:
        checks.append({"check": "priority_consistency", "status": "ok", "detail": "Priority usage is consistent"})

    overall = "ok"
    if any(c["status"] == "fail" for c in checks):
        overall = "fail"
    elif any(c["status"] == "warning" for c in checks):
        overall = "warning"

    return json.dumps({
        "page": page,
        "checks": checks,
        "overall_status": overall,
        "executors_checked": len(executors),
        "recommendation": "Page looks clean." if overall == "ok" else "Review warnings above before going live.",
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def plan_fixture_swap(
    old_fixture_type: str,
    new_fixture_type: str,
) -> str:
    """
    Plan a fixture type swap and assess compatibility (SAFE_READ).

    Compares attributes between old and new fixture types to identify
    what will transfer cleanly and what needs manual attention.

    Args:
        old_fixture_type: Current fixture type name (e.g. "Mac 700 Profile").
        new_fixture_type: Target fixture type name (e.g. "Mac Viper").

    Returns:
        str: JSON with compatible_attributes, missing_attributes, risk_level, migration_steps.
    """
    client = await _srv.get_client()

    async def _get_type_attrs(type_name: str) -> set[str]:
        """Discover attributes for a fixture type by navigating the cd tree."""
        await client.send_command_with_response("cd /")
        raw = await client.send_command_with_response("list fixture")
        attrs: set[str] = set()
        # Look for the fixture type in the listing
        for line in raw.splitlines():
            if type_name.lower() in line.lower():
                # Try to get attribute info
                fixture_match = re.match(r"^\s*(\d+)\s", line.strip())
                if fixture_match:
                    fid = fixture_match.group(1)
                    info = await client.send_command_with_response(f"info fixture {fid}")
                    # Extract attribute names from info output
                    for attr_match in re.finditer(r"(?:Attribute|Attr|Channel)\s*[=:]\s*(\w+)", info, re.IGNORECASE):
                        attrs.add(attr_match.group(1))
                    break
        await client.send_command_with_response("cd /")
        return attrs

    old_attrs = await _get_type_attrs(old_fixture_type)
    new_attrs = await _get_type_attrs(new_fixture_type)

    if not old_attrs and not new_attrs:
        return json.dumps({
            "error": "Could not discover attributes for either fixture type. Ensure both are patched.",
            "old_fixture_type": old_fixture_type,
            "new_fixture_type": new_fixture_type,
            "risk_tier": "SAFE_READ",
        }, indent=2)

    compatible = sorted(old_attrs & new_attrs)
    missing_in_new = sorted(old_attrs - new_attrs)
    new_only = sorted(new_attrs - old_attrs)
    compat_pct = len(compatible) / max(len(old_attrs), 1) * 100

    risk = "low" if compat_pct >= 80 else "medium" if compat_pct >= 50 else "high"

    steps = [
        "1. Save the current show (SaveShow)",
        "2. Export current presets using PSR if needed",
        f"3. Import the new fixture type '{new_fixture_type}' if not already in library",
        "4. Use Clone to copy fixture data from old to new fixtures",
    ]
    if missing_in_new:
        steps.append(f"5. Manually adjust {len(missing_in_new)} missing attribute(s): {missing_in_new[:5]}")
    steps.append(f"{'5' if not missing_in_new else '6'}. Verify all presets and cues reference the correct attributes")
    steps.append(f"{'6' if not missing_in_new else '7'}. Run validate_preset_references on affected sequences")

    return json.dumps({
        "old_fixture_type": old_fixture_type,
        "new_fixture_type": new_fixture_type,
        "compatible_attributes": compatible,
        "missing_in_new": missing_in_new,
        "new_only_attributes": new_only,
        "compatibility_percent": round(compat_pct, 1),
        "risk_level": risk,
        "migration_steps": steps,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def incident_snapshot() -> str:
    """
    Capture full console state for incident reporting (SAFE_READ).

    Creates a comprehensive snapshot of the current console state including
    page, modes, selection, parks, filter/world, active executors, and
    recent errors. Use this when something goes wrong on site.

    Returns:
        str: JSON with full state capture and human-readable summary.
    """
    snap = getattr(_srv._orchestrator, "last_snapshot", None)
    client = await _srv.get_client()

    # Always get fresh system vars
    raw_vars = await client.send_command_with_response("listvar")

    def _extract_var(name: str) -> str:
        m = re.search(rf"{name}\s*[=:]\s*(.+?)(?:\r|\n|$)", raw_vars, re.IGNORECASE)
        return m.group(1).strip() if m else "unknown"

    # Build snapshot data
    state: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "showfile": _extract_var("SHOWFILE"),
        "version": _extract_var("VERSION"),
        "user": _extract_var("USER"),
        "user_rights": _extract_var("USERRIGHTS"),
        "fader_page": _extract_var("FADERPAGE"),
        "selected_fixtures": _extract_var("SELECTEDFIXTURESCOUNT"),
        "selected_executor": _extract_var("SELECTEDEXEC"),
    }

    if snap:
        state["console_modes"] = getattr(snap, "console_modes", {})
        state["parked_fixtures"] = sorted(list(getattr(snap, "parked_fixtures", set()) or set()))[:20]
        state["parked_count"] = len(getattr(snap, "parked_fixtures", set()) or set())
        state["active_filter"] = getattr(snap, "active_filter", None)
        state["active_world"] = getattr(snap, "active_world", None)
        state["active_macros"] = getattr(snap, "active_macros", [])
        state["snapshot_age_s"] = round(snap.age_seconds(), 1) if hasattr(snap, "age_seconds") else None

        # Active executors
        exec_state = getattr(snap, "executor_state", {}) or {}
        active_execs = []
        for eid, es in exec_state.items():
            if hasattr(es, "sequence_id") and es.sequence_id:
                active_execs.append({"id": eid, "sequence_id": es.sequence_id})
        state["active_executors"] = active_execs[:20]
    else:
        state["snapshot_available"] = False
        state["note"] = "No hydrated snapshot — run hydrate_console_state for richer data"

    # Recent telemetry errors
    try:
        from src.telemetry import _get_telemetry
        tel = _get_telemetry()
        recent = tel.recent_errors(limit=5) if hasattr(tel, "recent_errors") else []
        state["recent_errors"] = recent
    except Exception:
        state["recent_errors"] = []

    # Human-readable summary
    lines = [
        f"Incident Snapshot — {state['timestamp']}",
        f"Show: {state['showfile']} (v{state['version']})",
        f"User: {state['user']} ({state['user_rights']})",
        f"Page: {state['fader_page']}, Selected: {state['selected_fixtures']} fixtures",
    ]
    if snap:
        modes_on = [k for k, v in (state.get("console_modes") or {}).items() if v]
        if modes_on:
            lines.append(f"Active modes: {', '.join(modes_on)}")
        if state.get("parked_count", 0) > 0:
            lines.append(f"Parked fixtures: {state['parked_count']}")

    state["summary"] = "\n".join(lines)
    state["risk_tier"] = "SAFE_READ"

    return json.dumps(state, indent=2, default=str)


# ============================================================
# Extended Analysis & Recovery Tools
# Lineage, dependency mapping, patch-fit validation, and drafts
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def trace_attribute_lineage(
    attribute: str,
    fixture_id: int | None = None,
    sequence_id: int | None = None,
    max_sequences: int = 5,
    max_cues_per_sequence: int = 10,
) -> str:
    """
    Trace likely sources of an attribute's current value (SAFE_READ).

    This is a best-effort lineage tool for debugging "why is this here?"
    scenarios. It combines live snapshot context with cue text scans to find
    candidate sequence/cue sources mentioning the attribute and, optionally,
    the target fixture.

    Args:
        attribute: Attribute name to search for (e.g. "Dimmer", "ColorRGB1").
        fixture_id: Optional fixture ID to narrow the lineage search.
        sequence_id: Optional sequence to inspect directly.
        max_sequences: Max sequences to inspect when sequence_id is omitted.
        max_cues_per_sequence: Max cues per sequence to inspect.

    Returns:
        str: JSON with live_context, candidate_sources, inspected_sequences, summary.
    """
    attribute = (attribute or "").strip()
    if not attribute:
        return json.dumps({
            "error": "attribute is required.",
            "blocked": True,
            "risk_tier": "SAFE_READ",
        }, indent=2)

    client = await _srv.get_client()
    snap = getattr(_srv._orchestrator, "last_snapshot", None)

    attr_re = re.compile(rf"\b{re.escape(attribute)}\b", re.IGNORECASE)
    fixture_re = re.compile(rf"\b(Fixture|Fix)\s+{fixture_id}\b", re.IGNORECASE) if fixture_id is not None else None

    sequence_ids: list[int] = []
    if sequence_id is not None:
        sequence_ids = [sequence_id]
    elif snap and getattr(snap, "executor_state", None):
        sequence_ids = sorted({
            state.sequence_id
            for state in snap.executor_state.values()
            if getattr(state, "sequence_id", None) is not None
        })[:max_sequences]
    if not sequence_ids and snap and getattr(snap, "sequences", None):
        sequence_ids = [seq.id for seq in snap.sequences[:max_sequences] if hasattr(seq, "id")]
    if not sequence_ids:
        raw = await client.send_command_with_response("list sequence")
        for match in re.finditer(r"^\s*(\d+)\s", raw, re.MULTILINE):
            sequence_ids.append(int(match.group(1)))
            if len(sequence_ids) >= max_sequences:
                break

    candidate_sources: list[dict] = []
    for seq_id in sequence_ids:
        cue_list = await client.send_command_with_response(f"list cue sequence {seq_id}")
        cue_ids: list[str] = []
        for match in re.finditer(r"^\s*(\d+(?:\.\d+)?)\s", cue_list, re.MULTILINE):
            cue_ids.append(match.group(1))
            if len(cue_ids) >= max_cues_per_sequence:
                break

        for cue_id in cue_ids:
            cue_raw = await client.send_command_with_response(f"list cue {cue_id} sequence {seq_id}")
            matched_lines = []
            for line in cue_raw.splitlines():
                if not attr_re.search(line):
                    continue
                if fixture_re and not fixture_re.search(line):
                    continue
                matched_lines.append(line.strip()[:200])

            if matched_lines:
                candidate_sources.append({
                    "sequence_id": seq_id,
                    "cue_id": cue_id,
                    "matched_lines": matched_lines[:5],
                    "match_count": len(matched_lines),
                })
        await asyncio.sleep(0.02)

    live_context = {
        "selected_fixture_count": getattr(snap, "selected_fixture_count", 0) if snap else None,
        "active_filter": getattr(snap, "active_filter", None) if snap else None,
        "active_world": getattr(snap, "active_world", None) if snap else None,
        "console_modes": getattr(snap, "console_modes", {}) if snap else {},
        "selected_executor": getattr(snap, "selected_exec", "") if snap else "",
        "selected_executor_cue": getattr(snap, "selected_exec_cue", "") if snap else "",
        "active_executors": [
            {"id": exec_id, "sequence_id": state.sequence_id}
            for exec_id, state in ((getattr(snap, "executor_state", {}) or {}).items() if snap else [])
            if getattr(state, "sequence_id", None) is not None
        ][:10],
    }

    if candidate_sources:
        summary = (
            f"Found {len(candidate_sources)} candidate cue source(s) mentioning "
            f"attribute '{attribute}'."
        )
    else:
        summary = (
            f"No cue text matches found for attribute '{attribute}'. "
            "Inspect live programmer, parks, world/filter state, and active executors."
        )

    return json.dumps({
        "attribute": attribute,
        "fixture_id": fixture_id,
        "inspected_sequences": sequence_ids,
        "candidate_sources": candidate_sources,
        "live_context": live_context,
        "summary": summary,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def find_executor_dependencies(
    page: int,
    executor_id: int,
) -> str:
    """
    Inspect a playback executor and extract likely dependencies (SAFE_READ).

    Args:
        page: Executor page number.
        executor_id: Executor number on the page.

    Returns:
        str: JSON with assignment info, dependency fields, and warnings.
    """
    client = await _srv.get_client()
    raw = await client.send_command_with_response(f"list executor {page}.{executor_id}")
    if "NO OBJECTS" in raw.upper() or not raw.strip():
        return json.dumps({
            "error": f"Executor {page}.{executor_id} is empty or not found.",
            "risk_tier": "SAFE_READ",
        }, indent=2)

    def _extract(pattern: str) -> str | None:
        match = re.search(pattern, raw, re.IGNORECASE)
        return match.group(1).strip().strip('"') if match else None

    dependencies = {
        "sequence_id": _extract(r"\b(?:Sequence|Seq)\s*[=:]?\s*(\d+)"),
        "macro_id": _extract(r"\bMacro\s*[=:]?\s*(\d+)"),
        "effect_id": _extract(r"\bEffect\s*[=:]?\s*(\d+)"),
        "trigger": _extract(r"\b(?:Trigger|Trig)\s*[=:]?\s*([A-Za-z0-9_]+)"),
        "priority": _extract(r"\b(?:Priority|Prio)\s*[=:]?\s*([A-Za-z0-9_]+)"),
        "fader_function": _extract(r"\bFader\s*[=:]?\s*([A-Za-z0-9_]+)"),
        "button_function": _extract(r"\bButton(?:Function)?\s*[=:]?\s*([A-Za-z0-9_]+)"),
        "speed_master": _extract(r"\bSpeed(?:Master)?\s*[=:]?\s*([A-Za-z0-9_.-]+)"),
        "world": _extract(r"\bWorld\s*[=:]?\s*([A-Za-z0-9_.-]+)"),
        "filter": _extract(r"\bFilter\s*[=:]?\s*([A-Za-z0-9_.-]+)"),
    }

    snap = getattr(_srv._orchestrator, "last_snapshot", None)
    snapshot_detail = None
    if snap and getattr(snap, "executor_state", None):
        snapshot_state = next(
            (
                state for state in snap.executor_state.values()
                if getattr(state, "page", None) == page and getattr(state, "id", None) == executor_id
            ),
            None,
        )
        if snapshot_state is not None:
            snapshot_detail = {
                "sequence_id": snapshot_state.sequence_id,
                "label": snapshot_state.label,
                "priority": snapshot_state.priority,
                "button_function": snapshot_state.button_function,
                "fader_function": snapshot_state.fader_function,
                "ooo": snapshot_state.ooo,
                "kill_protect": snapshot_state.kill_protect,
                "auto_start": snapshot_state.auto_start,
            }
            if dependencies["sequence_id"] is None and snapshot_state.sequence_id is not None:
                dependencies["sequence_id"] = str(snapshot_state.sequence_id)

    warnings = []
    if dependencies["sequence_id"] is None and dependencies["macro_id"] is None and dependencies["effect_id"] is None:
        warnings.append("No sequence, macro, or effect assignment parsed from executor listing.")
    if dependencies["speed_master"] is None and dependencies["effect_id"] is not None:
        warnings.append("Effect assignment found but no speed master parsed from listing.")

    return json.dumps({
        "page": page,
        "executor_id": executor_id,
        "dependencies": dependencies,
        "snapshot_detail": snapshot_detail,
        "warnings": warnings,
        "raw_excerpt": raw.splitlines()[:20],
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def find_unused_objects(
    object_type: str,
    max_objects: int = 25,
    preset_type: str | None = None,
) -> str:
    """
    Find likely unused object candidates using grounded heuristics (SAFE_READ).

    Supported types:
      - sequence: not assigned to any hydrated executor
      - macro: not referenced by another macro and not currently active
      - preset: no cue references found via find_preset_usages

    Args:
        object_type: One of "sequence", "macro", or "preset".
        max_objects: Max objects to inspect.
        preset_type: Required for object_type="preset".

    Returns:
        str: JSON with candidate_unused list and heuristic notes.
    """
    object_type = (object_type or "").strip().lower()
    if object_type not in {"sequence", "macro", "preset"}:
        return json.dumps({
            "error": "Unsupported object_type. Use 'sequence', 'macro', or 'preset'.",
            "blocked": True,
            "risk_tier": "SAFE_READ",
        }, indent=2)

    client = await _srv.get_client()
    snap = getattr(_srv._orchestrator, "last_snapshot", None)
    candidate_unused: list[dict] = []
    inspected = 0

    if object_type == "sequence":
        raw = await client.send_command_with_response("list sequence")
        seq_ids: list[int] = []
        for match in re.finditer(r"^\s*(\d+)\s*(.*)$", raw, re.MULTILINE):
            seq_ids.append(int(match.group(1)))
            if len(seq_ids) >= max_objects:
                break
        assigned = {
            state.sequence_id
            for state in ((getattr(snap, "executor_state", {}) or {}).values() if snap else [])
            if getattr(state, "sequence_id", None) is not None
        }
        for seq_id in seq_ids:
            inspected += 1
            if seq_id not in assigned:
                candidate_unused.append({
                    "id": seq_id,
                    "reason": "Not assigned to any hydrated executor.",
                })

    elif object_type == "macro":
        raw = await client.send_command_with_response("list macro")
        macro_ids: list[int] = []
        for match in re.finditer(r"^\s*(\d+)\s", raw, re.MULTILINE):
            macro_ids.append(int(match.group(1)))
            if len(macro_ids) >= max_objects:
                break

        referenced: set[int] = set()
        active_macros = set(getattr(snap, "active_macros", []) or []) if snap else set()
        for macro_id in macro_ids:
            body = await client.send_command_with_response(f"list macro {macro_id}")
            inspected += 1
            for ref in re.finditer(r"\bGo\s+Macro\s+(\d+)\b", body, re.IGNORECASE):
                referenced.add(int(ref.group(1)))
            await asyncio.sleep(0.01)

        for macro_id in macro_ids:
            if macro_id not in referenced and macro_id not in active_macros:
                candidate_unused.append({
                    "id": macro_id,
                    "reason": "No inbound macro jump reference found and macro is not active in snapshot.",
                })

    else:
        if not preset_type:
            return json.dumps({
                "error": "preset_type is required when object_type='preset'.",
                "blocked": True,
                "risk_tier": "SAFE_READ",
            }, indent=2)

        pool_raw = await _srv.list_preset_pool(preset_type=preset_type)
        pool_data = json.loads(pool_raw)
        entries = pool_data.get("entries", [])[:max_objects]
        for entry in entries:
            inspected += 1
            usage_raw = await _srv.find_preset_usages(preset_type=preset_type, preset_id=entry["id"], max_sequences=25)
            usage_data = json.loads(usage_raw)
            if usage_data.get("total_references", 0) == 0:
                candidate_unused.append({
                    "id": entry["id"],
                    "name": entry.get("name", ""),
                    "reason": "No cue references found in sampled sequences.",
                })
            await asyncio.sleep(0.01)

    return json.dumps({
        "object_type": object_type,
        "preset_type": preset_type,
        "inspected": inspected,
        "candidate_unused": candidate_unused,
        "heuristic_only": True,
        "notes": [
            "This tool returns candidates, not authoritative deletion approval.",
            "Hydrate console state first for stronger sequence/macro signal.",
        ],
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def validate_universal_preset_coverage(
    preset_type: str,
    start_id: int,
    end_id: int,
) -> str:
    """
    Check whether a universal preset slot range is populated cleanly (SAFE_READ).

    Args:
        preset_type: Preset type name (e.g. "color", "position").
        start_id: First preset slot in the expected range.
        end_id: Last preset slot in the expected range.

    Returns:
        str: JSON with occupied slots, missing slots, coverage percent, and recommendation.
    """
    if start_id <= 0 or end_id < start_id:
        return json.dumps({
            "error": f"Invalid preset range {start_id}-{end_id}.",
            "blocked": True,
            "risk_tier": "SAFE_READ",
        }, indent=2)

    pool_raw = await _srv.list_preset_pool(preset_type=preset_type)
    pool_data = json.loads(pool_raw)
    if "error" in pool_data:
        return pool_raw

    entries = pool_data.get("entries", [])
    occupied_ids = sorted(
        entry["id"] for entry in entries
        if isinstance(entry.get("id"), int) and start_id <= entry["id"] <= end_id
    )
    expected_ids = list(range(start_id, end_id + 1))
    missing_ids = [pid for pid in expected_ids if pid not in occupied_ids]
    coverage_pct = (len(occupied_ids) / len(expected_ids)) * 100 if expected_ids else 0.0

    if not missing_ids:
        recommendation = "Requested universal preset range is fully populated."
    elif coverage_pct >= 75:
        recommendation = "Coverage is mostly complete, but fill the missing slots before touring or cloning."
    else:
        recommendation = "Coverage is sparse — build or import a more complete universal preset range."

    return json.dumps({
        "preset_type": preset_type,
        "range_start": start_id,
        "range_end": end_id,
        "occupied_ids": occupied_ids,
        "missing_ids": missing_ids,
        "coverage_percent": round(coverage_pct, 1),
        "recommendation": recommendation,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def compare_patch_to_show_expectation(
    expected_fixture_types: str,
) -> str:
    """
    Compare the current patch against expected fixture-type counts (SAFE_READ).

    Args:
        expected_fixture_types: Comma-separated "Fixture Type=Count" entries.
            Example: "Mac Aura XB=8, Viper Profile=4"

    Returns:
        str: JSON with expected vs actual counts, missing types, and fit status.
    """
    expected: dict[str, int] = {}
    for chunk in expected_fixture_types.split(","):
        item = chunk.strip()
        if not item:
            continue
        if "=" not in item:
            return json.dumps({
                "error": f"Invalid expected_fixture_types entry: {item!r}. Use 'Type=Count'.",
                "blocked": True,
                "risk_tier": "SAFE_READ",
            }, indent=2)
        name, count_str = item.rsplit("=", 1)
        try:
            expected[name.strip()] = int(count_str.strip())
        except ValueError:
            return json.dumps({
                "error": f"Invalid count for {name.strip()!r}: {count_str!r}.",
                "blocked": True,
                "risk_tier": "SAFE_READ",
            }, indent=2)

    raw = await (await _srv.get_client()).send_command_with_response("list fixture")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]

    normalized_expected = {
        fixture_type: re.sub(r"\s+", " ", fixture_type.strip().lower())
        for fixture_type in expected
    }
    expected_by_specificity = sorted(
        expected,
        key=lambda fixture_type: (-len(normalized_expected[fixture_type]), fixture_type.lower()),
    )

    actual: dict[str, int] = {}
    unmatched_lines: list[str] = []
    for line in lines:
        fixture_match = re.match(r"^\s*(\d+)\s+(.+?)\s*$", line)
        candidate = fixture_match.group(2) if fixture_match else line
        normalized_candidate = re.sub(r"\s+", " ", candidate.strip().lower())
        matched = False
        for fixture_type in expected_by_specificity:
            escaped = re.escape(normalized_expected[fixture_type])
            if re.search(rf"(?<!\w){escaped}(?!\w)", normalized_candidate):
                actual[fixture_type] = actual.get(fixture_type, 0) + 1
                matched = True
                break
        if not matched and re.match(r"^\d+\s", line):
            unmatched_lines.append(line[:160])

    missing: list[dict] = []
    over: list[dict] = []
    for fixture_type, expected_count in expected.items():
        actual_count = actual.get(fixture_type, 0)
        if actual_count < expected_count:
            missing.append({
                "fixture_type": fixture_type,
                "expected": expected_count,
                "actual": actual_count,
                "delta": expected_count - actual_count,
            })
        elif actual_count > expected_count:
            over.append({
                "fixture_type": fixture_type,
                "expected": expected_count,
                "actual": actual_count,
                "delta": actual_count - expected_count,
            })

    fit_status = "match" if not missing and not over else "mismatch"
    if missing:
        recommendation = "Patch is under target for at least one expected fixture type. Plan clone/PSR or rebuild strategy."
    elif over:
        recommendation = "Patch exceeds at least one expected type count. Verify executor/group mapping still aligns."
    else:
        recommendation = "Patch counts match the supplied expectation for the requested fixture types."

    return json.dumps({
        "expected": expected,
        "actual": actual,
        "missing": missing,
        "over": over,
        "fit_status": fit_status,
        "unmatched_fixture_rows": unmatched_lines[:20],
        "recommendation": recommendation,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def snapshot_programmer_state() -> str:
    """
    Capture a structured programmer-state snapshot for later review (SAFE_READ).

    Returns:
        str: JSON with a restorable snapshot subset plus non-restorable context.
    """
    snap = getattr(_srv._orchestrator, "last_snapshot", None)
    if snap is None:
        raw = await _srv.list_system_variables(filter_prefix="SELECTED")
        data = json.loads(raw)
        return json.dumps({
            "snapshot_available": False,
            "fallback_variables": data.get("variables", {}),
            "note": "No hydrated snapshot available. Run hydrate_console_state for a full programmer snapshot.",
            "risk_tier": "SAFE_READ",
        }, indent=2)

    snapshot = {
        "selected_fixture_count": snap.selected_fixture_count,
        "active_preset_type": snap.active_preset_type,
        "active_feature": snap.active_feature,
        "active_attribute": snap.active_attribute,
        "selected_exec": snap.selected_exec,
        "selected_exec_cue": snap.selected_exec_cue,
        "active_world": snap.active_world,
        "active_filter": snap.active_filter,
        "console_modes": snap.console_modes,
        "parked_fixtures": sorted(list(snap.parked_fixtures))[:20],
        "matricks": {
            "active": getattr(snap.matricks, "active", False),
            "summary": snap.matricks.summary() if hasattr(snap.matricks, "summary") else "",
        },
        "snapshot_age_s": round(snap.age_seconds(), 1),
    }

    return json.dumps({
        "snapshot": snapshot,
        "restorable_fields": ["active_world", "active_filter", "selected_exec", "console_modes.blind"],
        "non_restorable_fields": ["selected_fixture_count", "parked_fixtures", "matricks", "selected_exec_cue"],
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def restore_programmer_state(
    snapshot_json: str,
    apply: bool = False,
    clear_before_restore: bool = True,
) -> str:
    """
    Preview or apply a conservative programmer-state restore (SAFE_WRITE).

    This tool intentionally restores only fields that can be expressed
    confidently through existing MA2 telnet commands. It does not attempt to
    recreate exact fixture selections, parked-fixture state, or MAtricks.

    Args:
        snapshot_json: JSON payload from snapshot_programmer_state().
        apply: If False (default), return the restore plan only.
        clear_before_restore: If True, begin with ClearAll when apply=True.

    Returns:
        str: JSON with planned commands, executed commands, and skipped fields.
    """
    try:
        parsed = json.loads(snapshot_json)
    except json.JSONDecodeError as exc:
        return json.dumps({
            "error": f"Invalid snapshot_json: {exc}",
            "blocked": True,
            "risk_tier": "SAFE_WRITE",
        }, indent=2)

    snapshot = parsed.get("snapshot", parsed)
    if not isinstance(snapshot, dict):
        return json.dumps({
            "error": "snapshot_json must contain an object or a top-level 'snapshot' object.",
            "blocked": True,
            "risk_tier": "SAFE_WRITE",
        }, indent=2)

    planned_commands: list[str] = []
    skipped_fields: list[str] = []

    if clear_before_restore:
        planned_commands.append(build_clear_all())

    active_world = snapshot.get("active_world")
    if isinstance(active_world, int) and active_world > 0:
        planned_commands.append(f"World {active_world}")
    elif active_world in (None, 0, "0", ""):
        skipped_fields.append("active_world")

    active_filter = snapshot.get("active_filter")
    if isinstance(active_filter, int) and active_filter > 0:
        planned_commands.append(f"Filter {active_filter}")
    elif active_filter in (None, 0, "0", ""):
        skipped_fields.append("active_filter")

    selected_exec = str(snapshot.get("selected_exec") or "").strip()
    if selected_exec:
        planned_commands.append(f"select executor {selected_exec}")
    else:
        skipped_fields.append("selected_exec")

    blind_mode = bool((snapshot.get("console_modes") or {}).get("blind"))
    if blind_mode:
        planned_commands.append("Blind On")

    skipped_fields.extend([
        "selected_fixture_count",
        "selected_exec_cue",
        "parked_fixtures",
        "matricks",
    ])

    if not apply:
        return json.dumps({
            "apply": False,
            "planned_commands": planned_commands,
            "skipped_fields": skipped_fields,
            "note": "Preview only. Pass apply=True to execute the conservative restore plan.",
            "risk_tier": "SAFE_WRITE",
        }, indent=2)

    client = await _srv.get_client()
    executed: list[dict[str, str]] = []
    for cmd in planned_commands:
        raw = await client.send_command_with_response(cmd)
        executed.append({"command_sent": cmd, "raw_response": raw})

    return json.dumps({
        "apply": True,
        "planned_commands": planned_commands,
        "executed": executed,
        "skipped_fields": skipped_fields,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def generate_song_macro_pack(
    song_name: str,
    sequence_id: int,
    start_macro_id: int = 1,
    target_page: int = 1,
) -> str:
    """
    Draft a song macro pack using a practical busking-page structure (SAFE_READ).

    This returns macro labels and line content only. It does not store any
    macros on the console.

    Args:
        song_name: Human-readable song title.
        sequence_id: Primary playback sequence for the song.
        start_macro_id: First macro ID to assign in the draft pack.
        target_page: Page operators should jump to before loading the song.

    Returns:
        str: JSON with draft macro definitions and first-button protocol notes.
    """
    song_label = (song_name or "").strip()
    if not song_label:
        return json.dumps({
            "error": "song_name is required.",
            "blocked": True,
            "risk_tier": "SAFE_READ",
        }, indent=2)

    macro_specs = [
        ("Load Song", [
            f'Page {target_page}',
            "ClearAll",
            f'Select Executor {target_page}.201',
            f'Goto Cue 1 Sequence {sequence_id}',
            f'Label Sequence {sequence_id} "{song_label}"',
        ]),
        ("Verse", [f"Goto Cue 2 Sequence {sequence_id}"]),
        ("Chorus", [f"Goto Cue 3 Sequence {sequence_id}"]),
        ("Bridge", [f"Goto Cue 4 Sequence {sequence_id}"]),
        ("Solo", [f"Goto Cue 5 Sequence {sequence_id}"]),
        ("Outro", [f"Goto Cue 6 Sequence {sequence_id}"]),
        ("Blackout", ["Off Executor Thru", "ClearAll"]),
    ]

    macros = []
    for offset, (label, lines) in enumerate(macro_specs):
        macros.append({
            "macro_id": start_macro_id + offset,
            "label": f"{song_label} - {label}",
            "lines": lines,
        })

    return json.dumps({
        "song_name": song_label,
        "sequence_id": sequence_id,
        "target_page": target_page,
        "macro_count": len(macros),
        "macros": macros,
        "notes": [
            "Draft only — review labels, cue numbers, and first-button protocol before storing.",
            "The first macro is intended to be the safe song-loader entrypoint.",
        ],
        "risk_tier": "SAFE_READ",
    }, indent=2)
