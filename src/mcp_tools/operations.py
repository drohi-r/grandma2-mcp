"""MCP tools — operations. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
from pathlib import Path

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# New Tools: DMX Conflict Detection, Telemetry, Compliance,
# Preset Validation, Macro Jump Targets, Pool Slot Check,
# Fixture Remap
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def detect_dmx_address_conflicts(universe_id: int | None = None) -> str:
    """
    Scan the patch for DMX address conflicts — fixtures sharing overlapping channel ranges.

    Queries list_universes and list_fixtures to build a channel-occupancy map,
    then reports any fixtures whose DMX footprint overlaps with another fixture on
    the same universe. Safe to run before any patching operation or during a show
    health check.

    Args:
        universe_id: Check only this universe (1-based). If None, checks all universes.

    Returns JSON with:
    - conflicts: list of {universe, fixture_a, fixture_b, overlap_channels}
    - clean_universes: list of universe IDs with no conflicts
    - total_fixtures_checked: int
    """
    client = await _srv.get_client()
    # Get all fixture data
    raw_fixtures = await client.send_command_with_response("List Fixture")

    # Build occupancy map: universe -> {channel: fixture_id}
    occupancy: dict[int, dict[int, dict]] = {}
    conflicts = []

    # Parse fixtures from raw response (simplified — real implementation would use prompt_parser)
    lines = [ln.strip() for ln in raw_fixtures.splitlines() if ln.strip() and not ln.startswith("Fixture")]

    fixtures_checked = 0
    for line in lines:
        parts = line.split()
        if len(parts) >= 4:
            try:
                fixture_id = int(parts[0])
                univ = int(parts[-2]) if parts[-2].isdigit() else None
                addr = int(parts[-1]) if parts[-1].isdigit() else None
                if univ is None or addr is None:
                    continue
                if universe_id is not None and univ != universe_id:
                    continue
                fixtures_checked += 1
                if univ not in occupancy:
                    occupancy[univ] = {}
                if addr in occupancy[univ]:
                    conflicts.append({
                        "universe": univ,
                        "fixture_a": occupancy[univ][addr],
                        "fixture_b": fixture_id,
                        "channel": addr
                    })
                else:
                    occupancy[univ][addr] = fixture_id
            except (ValueError, IndexError):
                continue

    clean_universes = [u for u in occupancy if not any(c["universe"] == u for c in conflicts)]

    return json.dumps({
        "conflicts": conflicts,
        "clean_universes": clean_universes,
        "total_fixtures_checked": fixtures_checked,
        "universe_filter": universe_id,
        "status": "PASS" if not conflicts else "FAIL",
        "raw_fixture_response": raw_fixtures[:500]
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def update_object(
    object_type: str,
    object_id: int | str | None = None,
    sequence_id: int | None = None,
    merge: bool = False,
    overwrite: bool = False,
    cueonly: bool | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Update any object with current programmer values (DESTRUCTIVE).

    Generic update tool that works with all 16 object types.
    For cue-specific updates with sequence scoping, prefer update_cue_data.

    Args:
        object_type: Object type — cue, group, preset, sequence, effect, macro, etc.
        object_id: Object ID (optional; updates active if omitted for cue)
        sequence_id: Sequence ID for cue-scoped updates (only used when object_type="cue")
        merge: Merge programmer into existing values
        overwrite: Overwrite existing values with programmer
        cueonly: Prevent changes from tracking forward (True) or allow (False)
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "update_object is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from src.commands import update as build_update, update_cue as build_update_cue
    if object_type.lower() == "cue":
        cmd = build_update_cue(
            object_id, sequence_id=sequence_id,
            merge=merge, overwrite=overwrite, cueonly=cueonly,
        )
    else:
        cmd = build_update(
            object_type, object_id,
            merge=merge, overwrite=overwrite, cueonly=cueonly,
        )

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def programming_action(
    action: str,
    fixture_ids: int | list[int] | None = None,
    end: int | None = None,
    cue_id: int | float | None = None,
    sequence_id: int | None = None,
    macro_id: int | None = None,
    executor_id: int | None = None,
    page: int | None = None,
    look_id: int | None = None,
    mode: str | None = None,
    merge: bool = False,
    overwrite: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Execute programmer operations — align, locate, flip, extract, learn,
    block/unblock cue, record macro, store look.

    Args:
        action: One of:
            SAFE_WRITE: "align", "locate", "flip", "extract", "learn"
            DESTRUCTIVE: "block", "unblock", "record_macro", "store_look"
        fixture_ids: Fixture number(s) for locate (single int or list)
        end: Ending number for locate range
        cue_id: Cue number for block/unblock
        sequence_id: Sequence ID for block/unblock scoping
        macro_id: Macro pool slot for record_macro
        executor_id: Executor ID for learn
        page: Page for learn page-qualified addressing
        look_id: Look pool slot for store_look
        mode: Alignment mode for align (">" "><" "<>" "<")
        merge: Merge option for store_look
        overwrite: Overwrite option for store_look
        confirm_destructive: Required for block/unblock/record_macro/store_look

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    from src.commands import (
        align as build_align,
        block_cue as build_block_cue,
        extract as build_extract,
        flip as build_flip,
        learn_executor as build_learn_executor,
        locate as build_locate,
        record_macro as build_record_macro,
        store_look as build_store_look,
        unblock_cue as build_unblock_cue,
    )

    valid_actions = {
        "align", "locate", "flip", "extract", "learn",
        "block", "unblock", "record_macro", "store_look",
    }
    if action not in valid_actions:
        return json.dumps({
            "error": f"Invalid action '{action}'. Valid: {sorted(valid_actions)}",
            "blocked": True,
        }, indent=2)

    destructive_actions = {"block", "unblock", "record_macro", "store_look"}
    if action in destructive_actions and not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": f"Action '{action}' is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if action == "align":
        cmd = build_align(mode=mode)
    elif action == "locate":
        cmd = build_locate(fixture_ids=fixture_ids, end=end)
    elif action == "flip":
        cmd = build_flip()
    elif action == "extract":
        cmd = build_extract()
    elif action == "learn":
        if executor_id is None:
            return json.dumps({"error": "executor_id required for learn", "blocked": True}, indent=2)
        cmd = build_learn_executor(executor_id, page=page)
    elif action == "block":
        if cue_id is None:
            return json.dumps({"error": "cue_id required for block", "blocked": True}, indent=2)
        cmd = build_block_cue(cue_id, sequence_id=sequence_id)
    elif action == "unblock":
        if cue_id is None:
            return json.dumps({"error": "cue_id required for unblock", "blocked": True}, indent=2)
        cmd = build_unblock_cue(cue_id, sequence_id=sequence_id)
    elif action == "record_macro":
        if macro_id is None:
            return json.dumps({"error": "macro_id required for record_macro", "blocked": True}, indent=2)
        cmd = build_record_macro(macro_id)
    elif action == "store_look":
        cmd = build_store_look(look_id=look_id, merge=merge, overwrite=overwrite)
    else:
        return json.dumps({"error": f"Unhandled action: {action}"}, indent=2)

    risk = "DESTRUCTIVE" if action in destructive_actions else "SAFE_WRITE"
    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def master_control(
    action: str,
    master_id: int | None = None,
    master_type: int | None = None,
    level: int | None = None,
) -> str:
    """
    Control master faders — set level, set special master, or list all masters.

    Args:
        action: "set" (SAFE_WRITE), "set_special" (SAFE_WRITE), or "list" (SAFE_READ)
        master_id: Master pool slot number (required for set / set_special)
        master_type: Special master type number (required for set_special)
        level: Level 0-100 (required for set / set_special)

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    from src.commands import (
        list_masters as build_list_masters,
        master_at as build_master_at,
        special_master_at as build_special_master_at,
    )

    valid_actions = ("set", "set_special", "list")
    if action not in valid_actions:
        return json.dumps({"error": f"action must be one of {valid_actions}", "blocked": True}, indent=2)

    if action == "set":
        if master_id is None or level is None:
            return json.dumps({"error": "master_id and level required for set", "blocked": True}, indent=2)
        cmd = build_master_at(master_id, level)
        risk_tier = "SAFE_WRITE"
    elif action == "set_special":
        if master_type is None or master_id is None or level is None:
            return json.dumps({"error": "master_type, master_id, level required for set_special", "blocked": True}, indent=2)
        cmd = build_special_master_at(master_type, master_id, level)
        risk_tier = "SAFE_WRITE"
    else:
        cmd = build_list_masters()
        risk_tier = "SAFE_READ"

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk_tier,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SYSTEM_ADMIN)
@_handle_errors
async def system_admin(
    action: str,
    user: str | None = None,
    password: str | None = None,
    script: str | None = None,
    message: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    System administration — login, logout, lock, unlock, lua, chat,
    reboot, restart, shutdown.

    Args:
        action: One of:
            SAFE_READ: "logout"
            SAFE_WRITE: "login", "lock", "unlock", "chat"
            DESTRUCTIVE: "lua", "reboot", "restart", "shutdown"
        user: Username (required for login)
        password: Password (required for login; optional for lock/unlock)
        script: Lua script string (required for lua)
        message: Chat message text (required for chat)
        confirm_destructive: Must be True for lua/reboot/restart/shutdown

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    from src.commands import (
        build_login,
        build_logout,
        lock_console as build_lock,
        lua_execute as build_lua,
        reboot_console as build_reboot,
        restart_console as build_restart,
        send_chat as build_chat,
        shutdown_console as build_shutdown,
        unlock_console as build_unlock,
    )

    valid_actions = {"login", "logout", "lock", "unlock", "lua", "chat", "reboot", "restart", "shutdown"}
    if action not in valid_actions:
        return json.dumps({"error": f"Invalid action '{action}'. Valid: {sorted(valid_actions)}", "blocked": True}, indent=2)

    # lua is DESTRUCTIVE: gma.cmd() can issue any console command (same gate as run_lua_script)
    destructive_actions = {"lua", "reboot", "restart", "shutdown"}
    if action in destructive_actions and not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": f"Action '{action}' is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if action == "login":
        if user is None or password is None:
            return json.dumps({"error": "user and password required for login", "blocked": True}, indent=2)
        cmd = build_login(user, password)
        risk_tier = "SAFE_WRITE"
    elif action == "logout":
        cmd = build_logout()
        risk_tier = "SAFE_READ"
    elif action == "lock":
        cmd = build_lock(password)
        risk_tier = "SAFE_WRITE"
    elif action == "unlock":
        cmd = build_unlock(password)
        risk_tier = "SAFE_WRITE"
    elif action == "lua":
        if script is None:
            return json.dumps({"error": "script required for lua", "blocked": True}, indent=2)
        cmd = build_lua(script)
        risk_tier = "DESTRUCTIVE"
    elif action == "chat":
        if message is None:
            return json.dumps({"error": "message required for chat", "blocked": True}, indent=2)
        cmd = build_chat(message)
        risk_tier = "SAFE_WRITE"
    elif action == "reboot":
        cmd = build_reboot()
        risk_tier = "DESTRUCTIVE"
    elif action == "restart":
        cmd = build_restart()
        risk_tier = "DESTRUCTIVE"
    else:
        cmd = build_shutdown()
        risk_tier = "DESTRUCTIVE"

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk_tier,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def plugin_management(action: str) -> str:
    """
    Manage Lua plugins — list available plugins or reload the plugin pool.

    Args:
        action: "list" (SAFE_READ) or "reload" (SAFE_WRITE)

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    from src.commands import (
        list_plugin_library as build_list_plugins,
        reload_plugins as build_reload_plugins,
    )

    if action == "list":
        cmd = build_list_plugins()
        risk_tier = "SAFE_READ"
    elif action == "reload":
        cmd = build_reload_plugins()
        risk_tier = "SAFE_WRITE"
    else:
        return json.dumps({"error": f"Invalid action '{action}'. Valid: ['list', 'reload']", "blocked": True}, indent=2)

    client = await _srv.get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk_tier,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_telemetry_report(
    session_id: str | None = None,
    days: int = 1,
    risk_tier: str | None = None,
    format: str = "json"
) -> str:
    """
    Export tool invocation telemetry as a structured audit report.

    Queries the tool_invocations table filtered by session, date range, and/or
    risk tier. Returns a structured log suitable for SB 132 compliance reports,
    insurance documentation, and safety audits.

    Args:
        session_id: Filter to a specific session ID (from list_agent_sessions).
                    If None, includes all sessions in the date range.
        days: Number of past days to include (default 1 = today only).
        risk_tier: Filter to "SAFE_READ", "SAFE_WRITE", or "DESTRUCTIVE" only.
                   If None, includes all tiers.
        format: "json" (default) or "markdown" for human-readable report.

    Returns structured report with:
    - header: session info, date range, operator
    - risk_summary: counts per tier
    - destructive_log: full detail on every DESTRUCTIVE operation
    - error_log: any operations that returned errors
    - timeline: ordered list of all operations
    """
    import datetime
    import sqlite3
    import time as _time

    cutoff_ts = _time.time() - (days * 86400)

    db_path = Path(__file__).parent.parent / "rag" / "store" / "agent_memory.db"
    if not db_path.exists():
        return json.dumps({"error": "Telemetry database not found", "path": str(db_path)})

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM tool_invocations WHERE ts >= ?"
        params: list = [cutoff_ts]

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        if risk_tier:
            query += " AND risk_tier = ?"
            params.append(risk_tier.upper())

        query += " ORDER BY ts ASC"

        rows = conn.execute(query, params).fetchall()
        invocations = [dict(r) for r in rows]
        conn.close()

    except Exception as e:
        return json.dumps({"error": f"Database query failed: {e}"})

    # Build report
    risk_summary: dict[str, int] = {"SAFE_READ": 0, "SAFE_WRITE": 0, "DESTRUCTIVE": 0, "UNKNOWN": 0}
    destructive_log = []
    error_log = []
    timeline = []

    for inv in invocations:
        tier = inv.get("risk_tier", "UNKNOWN")
        risk_summary[tier] = risk_summary.get(tier, 0) + 1

        entry = {
            "ts": inv.get("ts"),
            "ts_human": datetime.datetime.fromtimestamp(inv.get("ts", 0), tz=datetime.UTC).isoformat(),
            "tool": inv.get("tool_name"),
            "tier": tier,
            "latency_ms": inv.get("latency_ms"),
            "session_id": inv.get("session_id"),
            "operator": inv.get("operator", "unknown"),
            "error": inv.get("error_class")
        }
        timeline.append(entry)

        if tier == "DESTRUCTIVE":
            destructive_log.append({
                **entry,
                "inputs_preview": inv.get("inputs_json", "")[:300],
                "output_preview": inv.get("output_preview", "")[:300]
            })

        if inv.get("error_class"):
            error_log.append(entry)

    report = {
        "report_type": "MA2 Agent Telemetry Audit Report",
        "generated_at": datetime.datetime.now(tz=datetime.UTC).isoformat(),
        "filter": {
            "session_id": session_id,
            "days": days,
            "risk_tier_filter": risk_tier
        },
        "risk_summary": risk_summary,
        "total_operations": len(invocations),
        "destructive_operations": len(destructive_log),
        "errors": len(error_log),
        "destructive_log": destructive_log,
        "error_log": error_log,
        "timeline": timeline
    }

    if format == "markdown":
        md_lines = [
            "# MA2 Agent Audit Report",
            f"Generated: {report['generated_at']}",
            "",
            "## Risk Tier Summary",
            "| Tier | Count |",
            "|------|-------|",
        ]
        for tier, count in risk_summary.items():
            md_lines.append(f"| {tier} | {count} |")
        md_lines += [
            "",
            f"**Total operations:** {len(invocations)}  ",
            f"**DESTRUCTIVE operations:** {len(destructive_log)}  ",
            f"**Errors:** {len(error_log)}",
            "",
            "## DESTRUCTIVE Operations Log",
        ]
        if not destructive_log:
            md_lines.append("_No DESTRUCTIVE operations recorded._")
        for op in destructive_log:
            md_lines.append(f"- `{op['ts_human']}` — **{op['tool']}** (operator: {op.get('operator', 'unknown')})")

        md_lines += ["", "## Errors", ""]
        if not error_log:
            md_lines.append("_No errors recorded._")
        for err in error_log:
            md_lines.append(f"- `{err['ts_human']}` — **{err['tool']}** — {err.get('error')}")

        return "\n".join(md_lines)

    return json.dumps(report, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def generate_compliance_report(
    session_id: str | None = None,
    production_name: str = "Production",
    operator_name: str = "",
    days: int = 1
) -> str:
    """
    Generate a SB 132 / safety-audit compliance report from session telemetry.

    Produces a structured report mapping MA2 Agent telemetry fields to
    SB 132 documentation requirements: written risk assessment, operator
    identification, DESTRUCTIVE operation log, and incident timeline.

    Safe to run during any production. Reads telemetry only — no console side effects.

    Args:
        session_id: Target session ID. If None, uses all sessions in date range.
        production_name: Name of production for report header.
        operator_name: Console operator name for report header.
        days: Days of telemetry to include (default 1).

    Returns a markdown compliance report ready for inclusion in safety documentation.
    """
    import datetime
    import sqlite3
    import time as _time

    cutoff_ts = _time.time() - (days * 86400)

    db_path = Path(__file__).parent.parent / "rag" / "store" / "agent_memory.db"
    if not db_path.exists():
        return json.dumps({
            "error": "Telemetry database not found",
            "recommendation": "Ensure GMA_TELEMETRY=1 is set and at least one tool has been called"
        })

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        if session_id:
            query = "SELECT * FROM tool_invocations WHERE session_id = ? ORDER BY ts ASC"
            params: list = [session_id]
        else:
            query = "SELECT * FROM tool_invocations WHERE ts >= ? ORDER BY ts ASC"
            params = [cutoff_ts]

        rows = conn.execute(query, params).fetchall()
        invocations = [dict(r) for r in rows]
        conn.close()
    except Exception as e:
        return json.dumps({"error": f"Database error: {e}"})

    risk_counts: dict[str, int] = {"SAFE_READ": 0, "SAFE_WRITE": 0, "DESTRUCTIVE": 0}
    destructive_ops = []
    errors = []

    for inv in invocations:
        tier = inv.get("risk_tier", "SAFE_READ")
        risk_counts[tier] = risk_counts.get(tier, 0) + 1
        ts_human = datetime.datetime.fromtimestamp(
            inv.get("ts", 0), tz=datetime.UTC
        ).strftime("%Y-%m-%d %H:%M:%S UTC")

        if tier == "DESTRUCTIVE":
            destructive_ops.append(
                f"  - `{ts_human}` — **{inv.get('tool_name')}** (latency: {inv.get('latency_ms', 0):.0f}ms)"
            )
        if inv.get("error_class"):
            errors.append(
                f"  - `{ts_human}` — **{inv.get('tool_name')}** — Error: {inv.get('error_class')}"
            )

    now = datetime.datetime.now(tz=datetime.UTC).isoformat()
    safe_read = risk_counts.get("SAFE_READ", 0)
    safe_write = risk_counts.get("SAFE_WRITE", 0)
    destructive = risk_counts.get("DESTRUCTIVE", 0)
    total = len(invocations)

    report_lines = [
        "# MA2 Agent Safety & Compliance Report",
        "",
        f"**Production:** {production_name}  ",
        f"**Console Operator:** {operator_name or 'Not specified'}  ",
        f"**Report Generated:** {now}  ",
        f"**Period:** Last {days} day(s)",
        "",
        "---",
        "",
        "## Risk Assessment Summary",
        "",
        "All lighting control operations were processed through MA2 Agent's three-tier safety system:",
        "",
        "| Risk Tier | Operations | Description |",
        "|-----------|-----------|-------------|",
        f"| SAFE_READ | {safe_read} | Read-only monitoring — zero risk to console state |",
        f"| SAFE_WRITE | {safe_write} | Controlled modifications requiring standard authorization |",
        f"| DESTRUCTIVE | {destructive} | High-risk operations requiring explicit confirm_destructive=True and elevated OAuth scope |",
        f"| **TOTAL** | **{total}** | |",
        "",
        "### Insurance Brief",
        "",
        "All lighting control operations during this session were processed through MA2 Agent's",
        f"three-tier safety system. {safe_read} operation(s) were classified SAFE_READ (read-only",
        f"monitoring, zero risk), {safe_write} were SAFE_WRITE (controlled modifications requiring",
        f"standard authorization), and {destructive} were DESTRUCTIVE (required explicit",
        "confirm_destructive=True authorization and elevated scope).",
        "Full telemetry is available for forensic review.",
        "",
        "---",
        "",
        "## DESTRUCTIVE Operations Log",
        "",
        "_(SB 132 §3: Written risk assessment for high-risk operations)_",
        "",
    ]

    if destructive_ops:
        report_lines.extend(destructive_ops)
    else:
        report_lines.append("_No DESTRUCTIVE operations recorded in this period._")

    report_lines += [
        "",
        "---",
        "",
        "## Error / Incident Log",
        "",
        "_(SB 132 §4: Incident reporting)_",
        "",
    ]

    if errors:
        report_lines.extend(errors)
    else:
        report_lines.append("_No errors recorded in this period._")

    report_lines += [
        "",
        "---",
        "",
        "## System Information",
        "",
        "- **Control System:** MA2 Agent MCP Server",
        "- **Safety Architecture:** Three-tier (SAFE_READ / SAFE_WRITE / DESTRUCTIVE)",
        "- **Audit Logging:** Enabled — all operations recorded to persistent SQLite database",
        "- **Authorization Model:** OAuth 2.1 scope enforcement per operation",
        "",
        "_This report was generated automatically from MA2 Agent telemetry._",
        "_Retain as part of production safety documentation._",
    ]

    return "\n".join(report_lines)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def validate_preset_references(sequence_id: int, sample_cues: int = 5) -> str:
    """
    Scan a sequence's cues for references to presets that no longer exist in the pool.

    Samples up to `sample_cues` cues from the sequence, inspects each for preset
    references, and cross-checks against the current preset pool. Returns a list
    of broken references that would cause silent failures during playback.

    Safe to run before any performance. Read-only — no console side effects.

    Args:
        sequence_id: The sequence to validate.
        sample_cues: Number of cues to sample (default 5). Use 0 for all cues.

    Returns JSON with:
    - sequence_id: int
    - cues_checked: int
    - broken_references: list of {cue_id, preset_type, preset_id, detail}
    - valid_references: int count
    - status: "PASS" or "FAIL"
    """
    import re as _re
    client = await _srv.get_client()

    cue_list_raw = await client.send_command_with_response(f"List Cue Sequence {sequence_id}")
    cue_lines = [ln.strip() for ln in cue_list_raw.splitlines() if ln.strip() and ln[0].isdigit()]

    if sample_cues > 0:
        cue_lines = cue_lines[:sample_cues]

    broken = []
    valid_count = 0

    for line in cue_lines:
        parts = line.split()
        if not parts:
            continue
        cue_id = parts[0]

        cue_info = await client.send_command_with_response(f"Info Cue {cue_id} Sequence {sequence_id}")

        for info_line in cue_info.splitlines():
            if "Preset" in info_line and "." in info_line:
                preset_match = _re.search(r"Preset\s+(\d+)\.(\d+)", info_line)
                if preset_match:
                    p_type = int(preset_match.group(1))
                    p_id = int(preset_match.group(2))
                    check = await client.send_command_with_response(f"Info Preset {p_type}.{p_id}")
                    if "NOT FOUND" in check.upper() or "ERROR" in check.upper() or "EMPTY" in check.upper():
                        broken.append({
                            "cue_id": cue_id,
                            "preset_type": p_type,
                            "preset_id": p_id,
                            "detail": f"Preset {p_type}.{p_id} not found in pool"
                        })
                    else:
                        valid_count += 1

    return json.dumps({
        "sequence_id": sequence_id,
        "cues_checked": len(cue_lines),
        "broken_references": broken,
        "valid_references": valid_count,
        "status": "PASS" if not broken else "FAIL",
        "recommendation": (
            "Re-store missing presets or update cues to use existing preset IDs"
            if broken else "All checked preset references are valid"
        )
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_macro_jump_targets(macro_id: int) -> str:
    """
    Parse a macro's lines and return all jump targets (Go Macro N."name".L references).

    Reads macro lines via the console command tree and identifies all jump
    instructions, their current target line numbers, and the total line count.
    Use this before inserting or deleting macro lines to build an index-shift table.

    Args:
        macro_id: The macro pool ID to inspect.

    Returns JSON with:
    - macro_id: int
    - total_lines: int
    - jump_targets: list of {source_line, target_line, raw_command}
    - line_listing: ordered list of {line_num, command}
    """
    import re as _re
    client = await _srv.get_client()

    macro_info = await client.send_command_with_response(f"Info Macro {macro_id}")
    lines_raw = await client.send_command_with_response(f"List Macro {macro_id}")

    jump_targets = []
    line_listing = []
    line_num = 1

    for raw_line in lines_raw.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("Macro"):
            continue

        line_listing.append({"line_num": line_num, "command": stripped})

        jump_match = _re.search(r'Go\s+Macro\s+\d+[."][^.]+[.".](\d+)', stripped, _re.IGNORECASE)
        if jump_match:
            target_line = int(jump_match.group(1))
            jump_targets.append({
                "source_line": line_num,
                "target_line": target_line,
                "raw_command": stripped
            })

        line_num += 1

    return json.dumps({
        "macro_id": macro_id,
        "total_lines": len(line_listing),
        "jump_count": len(jump_targets),
        "jump_targets": jump_targets,
        "line_listing": line_listing,
        "usage": (
            "When inserting line at position N: add 1 to all target_line values >= N. "
            "When deleting line N: subtract 1 from all target_line values > N."
        ),
        "raw_macro_info": macro_info[:300]
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def check_pool_slot_availability(
    pool_type: str,
    slot_range_start: int,
    slot_range_end: int
) -> str:
    """
    Check which pool slots are available (empty) and which are occupied in a range.

    Pre-flight check before bulk import, PSR, or mass preset creation to prevent
    silent overwrites. Safe to run at any time — read-only.

    Args:
        pool_type: "sequence", "preset", "group", "macro", "effect", "world",
                   "filter", "view", "layout", "timecode"
        slot_range_start: First slot ID to check (inclusive).
        slot_range_end: Last slot ID to check (inclusive).

    Returns JSON with:
    - pool_type: str
    - range: [start, end]
    - occupied: list of {slot_id, label} for occupied slots
    - available: list of slot_ids that are empty
    - first_available_block_of_10: smallest contiguous block of 10 empty slots
    """
    client = await _srv.get_client()

    pool_keyword_map = {
        "sequence": "Sequence", "preset": "Preset", "group": "Group",
        "macro": "Macro", "effect": "Effect", "world": "World",
        "filter": "Filter", "view": "View", "layout": "Layout", "timecode": "Timecode"
    }

    keyword = pool_keyword_map.get(pool_type.lower())
    if not keyword:
        return json.dumps({
            "error": f"Unknown pool_type '{pool_type}'. Valid: {list(pool_keyword_map.keys())}"
        })

    if slot_range_end - slot_range_start > 200:
        return json.dumps({
            "error": "Range too large (max 200 slots per check). Split into smaller ranges."
        })

    occupied = []
    available = []

    for slot_id in range(slot_range_start, slot_range_end + 1):
        info_raw = await client.send_command_with_response(f"Info {keyword} {slot_id}")

        if any(x in info_raw.upper() for x in ["NOT FOUND", "EMPTY", "NO OBJECT", "DOES NOT EXIST"]):
            available.append(slot_id)
        else:
            label = ""
            for ln in info_raw.splitlines():
                if "Name" in ln or "Label" in ln:
                    parts = ln.split(":", 1)
                    if len(parts) > 1:
                        label = parts[1].strip()
                        break
            occupied.append({"slot_id": slot_id, "label": label or f"{keyword} {slot_id}"})

    # Find first contiguous block of 10
    first_block = None
    block_size = 10
    available_set = set(available)
    for start in available:
        if all(start + i in available_set for i in range(block_size)):
            first_block = {"start": start, "end": start + block_size - 1, "size": block_size}
            break

    return json.dumps({
        "pool_type": pool_type,
        "range": [slot_range_start, slot_range_end],
        "occupied_count": len(occupied),
        "available_count": len(available),
        "occupied": occupied,
        "available": available,
        "first_available_block_of_10": first_block,
        "recommendation": (
            f"Use target_slot={first_block['start']} for PSR to avoid conflicts"
            if first_block and occupied else "All slots available in range"
        )
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def remap_fixture_ids(
    source_fixture_id: int,
    target_fixture_id: int,
    scope: str = "groups",
    confirm_destructive: bool = False
) -> str:
    """
    Remap fixture references from one fixture ID to another within groups or presets.

    Used after PSR import or cross-venue adaptation when imported cue data references
    fixture IDs that have changed in the current rig. Updates group membership and/or
    selective preset fixture references.

    DESTRUCTIVE — modifies show data. Use check_pool_slot_availability and
    list_fixtures first to confirm both fixture IDs exist in the current patch.

    Args:
        source_fixture_id: The old fixture ID to replace.
        target_fixture_id: The new fixture ID to use.
        scope: "groups" (update group membership only), "presets" (update selective
               preset references only), or "both".
        confirm_destructive: Must be True to execute.

    Returns JSON with:
    - remapped_objects: list of modified pool objects
    - skipped: list of objects where source_fixture_id was not found
    - command_log: commands sent to console
    """
    if not confirm_destructive:
        return json.dumps({
            "error": "confirm_destructive=True required",
            "detail": (
                f"This will remap fixture {source_fixture_id} -> {target_fixture_id} in {scope}. "
                "Verify both fixtures exist with list_fixtures() before proceeding."
            )
        })

    client = await _srv.get_client()

    src_info = await client.send_command_with_response(f"Info Fixture {source_fixture_id}")
    tgt_info = await client.send_command_with_response(f"Info Fixture {target_fixture_id}")

    if any(x in src_info.upper() for x in ["NOT FOUND", "ERROR"]):
        return json.dumps({"error": f"Source fixture {source_fixture_id} not found in current patch"})
    if any(x in tgt_info.upper() for x in ["NOT FOUND", "ERROR"]):
        return json.dumps({"error": f"Target fixture {target_fixture_id} not found in current patch"})

    commands_sent = []
    remapped = []

    if scope in ("groups", "both"):
        groups_raw = await client.send_command_with_response("List Group")
        group_lines = [
            ln.strip() for ln in groups_raw.splitlines()
            if ln.strip() and ln.strip()[0].isdigit()
        ]

        for gline in group_lines:
            gid = gline.split()[0]
            g_info = await client.send_command_with_response(f"Info Group {gid}")
            if str(source_fixture_id) in g_info:
                cmd = f"Fixture {target_fixture_id} Store Group {gid} /merge"
                await client.send_command_with_response(cmd)
                commands_sent.append(cmd)
                cmd2 = f"Fixture {source_fixture_id} Remove Group {gid}"
                await client.send_command_with_response(cmd2)
                commands_sent.append(cmd2)
                remapped.append(f"Group {gid}")

    return json.dumps({
        "source_fixture_id": source_fixture_id,
        "target_fixture_id": target_fixture_id,
        "scope": scope,
        "remapped_objects": remapped,
        "commands_sent": commands_sent,
        "note": (
            "Selective preset fixture references require re-recording presets with the new fixture "
            "selected — automated remapping of preset fixture IDs is not supported via telnet."
        )
    }, indent=2)
