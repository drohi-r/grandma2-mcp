"""
server_orchestration_tools.py — Register 35 agentic MCP tools (110-144) onto the FastMCP instance.

Tools 110-118 bring the MA2 MCP server's agentic capability up to the multi-agent
model: task decomposition, orchestrated execution, memory recall, token tracking,
object name resolution, and console state hydration.

Tools 119-129 expose the ConsoleStateSnapshot read surface: cached gap-state queries
with zero telnet cost (get_console_state, get_park_ledger, get_filter_state,
get_world_state, get_matricks_state, get_programmer_selection, hydrate_sequences,
get_sequence_memory, assert_selection_count, assert_preset_exists, get_executor_detail).

Tools 130-133 provide state diff, showfile info, and system variable polling.

Tools 134-136 are orchestration safety gates: confirm_destructive_steps, abort_task,
and retry_failed_steps.

Usage in server.py:
    from src.server_orchestration_tools import register_orchestration_tools
    register_orchestration_tools(mcp, _orchestrator, require_scope, _handle_errors, OAuthScope)
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .agent_memory import LongTermMemory
from .orchestrator import Orchestrator
from .skill import SkillRegistry
from .skill_improver import SkillImprover
from .task_decomposer import TaskDecomposer


def register_orchestration_tools(
    mcp: FastMCP,
    orchestrator: Orchestrator,
    require_scope_fn,
    handle_errors_fn,
    OAuthScope,
) -> None:
    """Register all orchestration MCP tools onto an existing FastMCP instance."""

    # ------------------------------------------------------------------ #
    # Tool 110: decompose_task                                            #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.DISCOVER)
    @handle_errors_fn
    async def decompose_task(
        goal: str,
        color: str = "",
        group: str = "",
        sequence: int = 1,
        cue: float = 1.0,
        preset: str = "",
    ) -> str:
        """
        Break a high-level lighting goal into an ordered multi-agent plan.

        Returns the plan summary and full step list so you can review
        before executing. Call run_task to actually execute.

        Args:
            goal:     Natural-language intent, e.g. 'blue wash on movers'
            color:    Target color name or hex
            group:    Fixture group name
            sequence: Target sequence number for cue storage
            cue:      Target cue number
            preset:   Preset name or ID to apply
        """
        import json
        params = {k: v for k, v in {
            "color": color, "group": group,
            "sequence": sequence, "cue": cue, "preset": preset,
        }.items() if v}

        decomposer = TaskDecomposer()
        plan = decomposer.decompose(goal, params)

        return json.dumps({
            "goal": plan.goal,
            "steps": len(plan.steps),
            "plan_summary": plan.summary(),
            "step_list": [
                {
                    "name": s.name,
                    "agent_role": s.agent_role,
                    "description": s.description,
                    "risk_tier": s.allowed_risk.value,
                    "tools": s.mcp_tools,
                    "depends_on": s.depends_on,
                    "eval_criteria": s.eval_criteria,
                    "requires_confirmation": s.allowed_risk.value == "DESTRUCTIVE",
                }
                for s in plan.ordered_steps()
            ],
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 111: run_task                                                  #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.CUE_STORE)
    @handle_errors_fn
    async def run_task(
        goal: str,
        color: str = "",
        group: str = "",
        sequence: int = 1,
        cue: float = 1.0,
        preset: str = "",
        auto_confirm_destructive: bool = False,
    ) -> str:
        """
        Execute a full multi-agent task from a natural-language goal.

        Orchestrates sub-agents with risk-tier isolation, working memory,
        and per-step evaluation.

        Args:
            goal: Natural-language show intent
            auto_confirm_destructive: Set True to allow DESTRUCTIVE steps
                without manual confirmation. Default False for safety.
        """
        import json
        params = {k: v for k, v in {
            "color": color, "group": group,
            "sequence": sequence, "cue": cue, "preset": preset,
        }.items() if v}

        result = await orchestrator.run(
            goal,
            params,
            auto_confirm_destructive=auto_confirm_destructive,
        )

        return json.dumps({
            "session_id": result.session_id,
            "outcome": result.outcome,
            "steps_done": result.steps_done,
            "steps_failed": result.steps_failed,
            "total_tokens": result.total_tokens,
            "elapsed_s": result.elapsed_s,
            "report": result.report(),
            "step_results": [
                {
                    "step": r.step_name,
                    "success": r.success,
                    "eval_passed": r.eval_passed,
                    "tokens": r.tokens_used,
                    "error": r.error or None,
                }
                for r in result.step_results
            ],
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 112: list_agent_sessions                                       #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def list_agent_sessions(limit: int = 10) -> str:
        """
        List recent multi-agent task sessions from long-term memory.

        Args:
            limit: Number of most recent sessions to return (default 10)
        """
        import json
        sessions = orchestrator.recent_sessions(limit)
        return json.dumps({"count": len(sessions), "sessions": sessions}, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 113: recall_agent_session                                      #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def recall_agent_session(session_id: str) -> str:
        """
        Restore the full WorkingMemory snapshot from a past agent session.

        Args:
            session_id: 8-char session ID from list_agent_sessions
        """
        import json
        snapshot = orchestrator.recall(session_id)
        if snapshot is None:
            return json.dumps({"error": f"Session '{session_id}' not found"})
        return json.dumps({
            "session_id": session_id,
            "task": snapshot.get("task_description"),
            "fixtures_tracked": len(snapshot.get("fixtures", {})),
            "completed_steps": snapshot.get("completed_steps", []),
            "failed_steps": snapshot.get("failed_steps", []),
            "tokens_consumed": snapshot.get("token_spend", 0),
            "snapshot": snapshot,
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 114: agent_token_report                                        #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def agent_token_report(limit: int = 20) -> str:
        """
        Report token consumption across recent agent sessions.

        Args:
            limit: Number of sessions to analyse
        """
        import json
        sessions = orchestrator.recent_sessions(limit)
        total = sum(s.get("tokens", 0) for s in sessions)
        avg   = round(total / max(len(sessions), 1))
        top   = sorted(sessions, key=lambda s: s.get("tokens", 0), reverse=True)[:3]

        return json.dumps({
            "sessions_analysed": len(sessions),
            "total_tokens": total,
            "avg_tokens_per_session": avg,
            "top_consuming_sessions": [
                {"id": s["id"], "task": s["task"], "tokens": s.get("tokens", 0)}
                for s in top
            ],
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 115: register_decomposition_rule                              #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.SYSTEM_ADMIN)
    @handle_errors_fn
    async def register_decomposition_rule(
        pattern: str,
        steps_json: str,
    ) -> str:
        """
        Register a new task decomposition rule at runtime (admin only).

        Args:
            pattern:    Regex pattern matched against natural-language goals
            steps_json: JSON array of step dicts with keys:
                        name, agent_role, description,
                        allowed_risk (SAFE_READ|SAFE_WRITE|DESTRUCTIVE),
                        mcp_tools (array), depends_on (array), eval_criteria
        """
        import json

        from .task_decomposer import RiskTier, SubTask, TaskPlan

        try:
            steps_raw = json.loads(steps_json)
        except Exception as exc:
            return json.dumps({"error": f"Invalid steps_json: {exc}"})

        def _builder(goal: str, params: dict) -> TaskPlan:
            steps = []
            for s in steps_raw:
                steps.append(SubTask(
                    name=s["name"],
                    agent_role=s.get("agent_role", "Agent"),
                    description=s.get("description", ""),
                    allowed_risk=RiskTier(s.get("allowed_risk", "SAFE_READ")),
                    mcp_tools=s.get("mcp_tools", []),
                    depends_on=s.get("depends_on", []),
                    eval_criteria=s.get("eval_criteria", ""),
                ))
            return TaskPlan(goal=goal, steps=steps)

        orchestrator.register_decomposition_rule(pattern, _builder)
        return json.dumps({
            "registered": True,
            "pattern": pattern,
            "steps": len(steps_raw),
            "message": f"Rule '{pattern}' will now match future decompose_task / run_task calls",
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 116: resolve_object_ref                                        #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.DISCOVER)
    @handle_errors_fn
    async def resolve_object_ref(
        object_type: str,
        name: str = "",
        id: int = 0,
        match_mode: str = "literal",
        preset_type: int = 0,
    ) -> str:
        """
        Resolve a pool object name or ID to a correctly-quoted MA2 command token.
        Uses in-memory index only — zero telnet cost.

        match_mode="literal" (default): quotes names with special chars; * is literal.
        match_mode="wildcard": * is active operator — may match multiple objects.

        Args:
            object_type: Group | Sequence | Preset | Macro | Effect | Timecode |
                         Timer | View | Layout | World | Filter | Page |
                         Executor | Fixture | Channel | Cue
            name:        Display name (use name OR id, not both)
            id:          Numeric ID (0 = not provided)
            match_mode:  "literal" (default) or "wildcard"
            preset_type: Required for Preset objects (1=Dimmer … 9=Video)
        """
        import json
        cs = orchestrator.last_snapshot
        if cs is None:
            return json.dumps({
                "error": "No console state snapshot available.",
                "hint": "Call hydrate_console_state first.",
            })

        resolved = cs.resolve(
            object_type,
            name=name or None,
            id=id or None,
            match_mode=match_mode,
            preset_type=preset_type or None,
        )
        result = resolved.to_dict()

        if match_mode == "wildcard" and (name or ""):
            all_matches = cs.name_index.resolve_wildcard(
                object_type, name, preset_type=preset_type or None
            )
            result["wildcard_matches"] = [m.to_dict() for m in all_matches]
            result["wildcard_match_count"] = len(all_matches)

        return json.dumps(result, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 117: list_pool_names                                           #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.DISCOVER)
    @handle_errors_fn
    async def list_pool_names(
        object_type: str,
        preset_type: int = 0,
    ) -> str:
        """
        List all known names and IDs for a pool type from the in-memory index.
        Zero telnet cost.

        Args:
            object_type: Any MA2 pool type (Group, Sequence, Macro, etc.)
            preset_type: For Preset objects only (1-9)
        """
        import json
        cs = orchestrator.last_snapshot
        if cs is None:
            return json.dumps({"error": "No snapshot available. Run hydrate_console_state first."})

        pt = preset_type or None
        entries = cs.name_index.all_entries(object_type, preset_type=pt)
        return json.dumps({
            "object_type": object_type,
            "preset_type": preset_type or None,
            "count": len(entries),
            "entries": entries,
            "indexed_types": cs.name_index.indexed_types(),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 118: hydrate_console_state                                     #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def hydrate_console_state(
        sequence_ids: str = "",
    ) -> str:
        """
        Trigger a fresh ConsoleStateSnapshot hydration on demand.
        Populates all 19 memory gaps + PoolNameIndex for all 16 pool types.

        Call this after load_show, new_show, or before DESTRUCTIVE multi-step tasks.

        Args:
            sequence_ids: Comma-separated sequence IDs for deep cue/part
                          hydration (e.g. "1,2,5"). Leave empty for fast path.
        """
        import json
        seq_ids = []
        if sequence_ids.strip():
            try:
                seq_ids = [int(x.strip()) for x in sequence_ids.split(",") if x.strip()]
            except ValueError:
                return json.dumps({"error": f"Invalid sequence_ids: {sequence_ids!r}"})

        snap = await orchestrator.hydrate_snapshot(sequence_ids=seq_ids or None)
        if snap is None:
            return json.dumps({"error": "Orchestrator has no telnet_send configured."})

        orchestrator.last_snapshot = snap

        return json.dumps({
            "hydrated": True,
            "duration_s": snap.hydration_duration_s,
            "partial": snap.partial,
            "errors": snap.hydration_errors,
            "summary": snap.summary(),
            "index_stats": snap.name_index.stats(),
            "indexed_types": snap.name_index.indexed_types(),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 119: get_console_state                                         #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def get_console_state() -> str:
        """
        Return the cached ConsoleStateSnapshot without re-hydrating.

        Zero telnet cost. Includes staleness flag and full summary.
        Call hydrate_console_state first if the snapshot is missing or stale.

        Returns:
            str: JSON with hydrated, staleness_warning, age_seconds, partial, summary.
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})
        return json.dumps({
            "hydrated": snap.hydrated_at is not None,
            "staleness_warning": snap.staleness_warning(),
            "age_seconds": snap.age_seconds(),
            "partial": snap.partial,
            "summary": snap.summary(),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 120: get_park_ledger                                           #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def get_park_ledger() -> str:
        """
        Return all currently parked fixtures from the snapshot ledger.

        Park state is tracked as a write-tracker (Gap 3). Parked fixtures
        silently ignore At commands — check this before any DESTRUCTIVE preset
        or intensity operation.

        Returns:
            str: JSON with parked_fixtures list, count, and a warning if non-empty.
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})
        parked = sorted(snap.parked_fixtures)
        return json.dumps({
            "parked_fixtures": parked,
            "count": len(parked),
            "warning": (
                f"{len(parked)} fixture(s) parked — At commands will be silently ignored"
                if parked else None
            ),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 121: get_filter_state                                          #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def get_filter_state() -> str:
        """
        Return the active filter ID and V/VT/E layer flags from the snapshot.

        Gap 1. An active filter silently restricts which attributes are stored
        in a cue or preset. Check this before any Store operation.

        Returns:
            str: JSON with active_filter, filter_vte dict, and a warning if active.
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})
        return json.dumps({
            "active_filter": snap.active_filter,
            "filter_vte": snap.filter_vte,
            "warning": (
                f"Filter {snap.active_filter} is active — attribute storage may be restricted"
                if snap.active_filter is not None else None
            ),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 122: get_world_state                                           #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def get_world_state() -> str:
        """
        Return the active world ID and known world labels from the snapshot.

        Gap 2. An active world gates which fixtures are visible. Critical for
        multi-universe shows where selection counts vary per world.

        Returns:
            str: JSON with active_world, world_labels dict, and a warning if active.
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})
        return json.dumps({
            "active_world": snap.active_world,
            "world_labels": snap.world_labels,
            "warning": (
                f"World {snap.active_world} is active — fixture visibility may be gated"
                if snap.active_world is not None else None
            ),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 123: get_matricks_state                                        #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def get_matricks_state() -> str:
        """
        Return the write-tracked MAtricks programmer state from the snapshot.

        Gap 6. No telnet readback exists for MAtricks — this write-tracker is
        the only source of truth. Updated by manage_matricks on every call.

        Returns:
            str: JSON with all MAtricksTracker fields and a human summary.
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})
        mt = snap.matricks
        return json.dumps({
            "interleave": mt.interleave,
            "blocks_x": mt.blocks_x,
            "blocks_y": mt.blocks_y,
            "groups_x": mt.groups_x,
            "groups_y": mt.groups_y,
            "wings": mt.wings,
            "filter_id": mt.filter_id,
            "active": mt.active,
            "summary": mt.summary(),
            "note": "Write-tracked only — no telnet readback exists for MAtricks state",
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 124: get_programmer_selection                                  #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def get_programmer_selection() -> str:
        """
        Return $SELECTEDFIXTURESCOUNT, $SELECTEDEXEC, and $SELECTEDEXECCUE from snapshot.

        Gaps 18 & 19. Zero telnet cost — reads hydrated system variable values.
        Use assert_selection_count to validate count against an expected value.

        Returns:
            str: JSON with selected_fixture_count, selected_exec, selected_exec_cue.
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})
        return json.dumps({
            "selected_fixture_count": snap.selected_fixture_count,
            "selected_exec": snap.selected_exec,
            "selected_exec_cue": snap.selected_exec_cue,
            "warning": (
                "No fixtures selected ($SELECTEDFIXTURESCOUNT is 0)"
                if snap.selected_fixture_count == 0 else None
            ),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 125: hydrate_sequences                                         #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def hydrate_sequences(sequence_ids: str) -> str:
        """
        Deep-hydrate cues and parts for specific sequence IDs (Gaps 7 & 9).

        Triggers orchestrator.hydrate_snapshot(sequence_ids=[...]) for only the
        requested sequences, avoiding a full console re-scan. Use after
        creating or modifying specific sequences when you need cue detail.

        Args:
            sequence_ids: Comma-separated sequence IDs, e.g. "1,2,5".

        Returns:
            str: JSON with hydrated flag, sequence_ids list, partial flag.
        """
        import json
        try:
            ids = [int(x.strip()) for x in sequence_ids.split(",") if x.strip()]
        except ValueError:
            return json.dumps({"error": f"Invalid sequence_ids: {sequence_ids!r}"})
        if not ids:
            return json.dumps({"error": "sequence_ids must be a non-empty comma-separated list of integers"})

        snap = await orchestrator.hydrate_snapshot(sequence_ids=ids)
        if snap is None:
            return json.dumps({"error": "Orchestrator has no telnet_send configured."})
        orchestrator.last_snapshot = snap
        return json.dumps({
            "hydrated": True,
            "sequence_ids": ids,
            "sequences_in_snapshot": len(snap.sequences),
            "cues_in_snapshot": len(snap.sequence_cues),
            "partial": snap.partial,
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 126: get_sequence_memory                                       #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def get_sequence_memory(sequence_id: int) -> str:
        """
        Return the in-memory SequenceEntry and its CueRecords for a given ID.

        Zero telnet cost — reads from snapshot. Call hydrate_sequences first
        if the sequence is not yet in the snapshot.

        Args:
            sequence_id: The sequence ID to retrieve.

        Returns:
            str: JSON with sequence properties and cue list.
        """
        import dataclasses
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})

        seq = next((s for s in snap.sequences if s.id == sequence_id), None)
        if seq is None:
            return json.dumps({
                "error": f"Sequence {sequence_id} not in snapshot.",
                "hint": f"Call hydrate_sequences('{sequence_id}') to load it.",
                "known_ids": [s.id for s in snap.sequences],
            })

        cues = [dataclasses.asdict(c) for c in snap.sequence_cues if c.sequence_id == sequence_id]
        result = dataclasses.asdict(seq)
        result["cues"] = cues
        result["cue_count"] = len(cues)
        return json.dumps(result, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 127: assert_selection_count                                    #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def assert_selection_count(expected: int, tolerance: int = 0) -> str:
        """
        Assert that $SELECTEDFIXTURESCOUNT matches an expected value.

        Eval step for SelectionAgent. Reads from snapshot — zero telnet cost.
        A mismatch usually indicates a world/filter/park issue.

        Args:
            expected: Expected fixture count.
            tolerance: Acceptable delta (default 0 — exact match).

        Returns:
            str: JSON with passed bool, actual count, expected count, and message.
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})
        actual = snap.selected_fixture_count
        passed = abs(actual - expected) <= tolerance
        return json.dumps({
            "passed": passed,
            "actual": actual,
            "expected": expected,
            "tolerance": tolerance,
            "message": "OK" if passed else (
                f"Selection count mismatch: expected {expected} (±{tolerance}), got {actual}. "
                "Check active world/filter or parked fixtures."
            ),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 128: assert_preset_exists                                      #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def assert_preset_exists(preset_type: int, preset_id: int) -> str:
        """
        Assert that a preset slot exists in the snapshot's pool inventory.

        Pre-flight check before store_preset or store_cue. Reads from snapshot
        name index — zero telnet cost.

        Args:
            preset_type: PresetType ID (1=Dimmer, 2=Position, 3=Gobo, 4=Color,
                         5=Beam, 6=Focus, 7=Control).
            preset_id: The preset slot ID to check.

        Returns:
            str: JSON with exists bool, preset_type, preset_id, and optional warning.
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})
        exists = snap.preset_exists(preset_type, preset_id)
        return json.dumps({
            "exists": exists,
            "preset_type": preset_type,
            "preset_id": preset_id,
            "warning": (
                None if exists
                else f"Preset {preset_type}.{preset_id} not found in snapshot inventory — "
                     "it may not exist or hydration may be stale"
            ),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 129: get_executor_detail                                       #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def get_executor_detail(executor_id: int) -> str:
        """
        Return the full ExecutorState for a given executor ID from the snapshot.

        Gap 10. Includes priority, button/fader function, autostart, killprotect.
        Zero telnet cost — reads from snapshot. Call hydrate_console_state first.

        Args:
            executor_id: The executor ID to retrieve.

        Returns:
            str: JSON with all ExecutorState fields, or an error if not found.
        """
        import dataclasses
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})
        exec_state = snap.executor_state.get(executor_id)
        if exec_state is None:
            return json.dumps({
                "error": f"Executor {executor_id} not in snapshot.",
                "hint": "Call hydrate_console_state() to populate executor state.",
                "known_ids": sorted(snap.executor_state.keys()),
            })
        return json.dumps(dataclasses.asdict(exec_state), indent=2)

    # ------------------------------------------------------------------ #
    # Tool 131: diff_console_state                                        #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def diff_console_state(baseline: str) -> str:
        """
        Compare the current ConsoleStateSnapshot against a caller-supplied baseline.

        Pass a JSON dict with any subset of: active_filter, active_world,
        selected_fixture_count, fader_page, active_user_profile,
        has_unsaved_changes, console_modes, filter_vte, parked_count.
        Unrecognised keys are ignored.

        Args:
            baseline: JSON string with baseline field values to compare against.

        Returns:
            str: JSON with changed_fields, unchanged_count, snapshot_age_seconds.
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})

        try:
            base = json.loads(baseline)
        except Exception as exc:
            return json.dumps({"error": f"Invalid baseline JSON: {exc}"})

        _DIFFABLE = {
            "active_filter":          lambda s: s.active_filter,
            "active_world":           lambda s: s.active_world,
            "selected_fixture_count": lambda s: s.selected_fixture_count,
            "fader_page":             lambda s: s.fader_page,
            "active_user_profile":    lambda s: s.active_user_profile,
            "has_unsaved_changes":    lambda s: s.has_unsaved_changes,
            "console_modes":          lambda s: s.console_modes,
            "filter_vte":             lambda s: s.filter_vte,
            "parked_count":           lambda s: len(s.parked_fixtures),
        }

        changed: dict = {}
        unchanged = 0
        for key, getter in _DIFFABLE.items():
            if key not in base:
                continue
            current_val = getter(snap)
            baseline_val = base[key]
            if current_val != baseline_val:
                changed[key] = {"before": baseline_val, "after": current_val}
            else:
                unchanged += 1

        return json.dumps({
            "changed_fields": changed,
            "changed_count": len(changed),
            "unchanged_count": unchanged,
            "snapshot_age_seconds": snap.age_seconds(),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 132: get_showfile_info                                         #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def get_showfile_info() -> str:
        """
        Return show identity and host info from the cached ConsoleStateSnapshot.

        Zero telnet cost — reads fields hydrated during hydrate_console_state.
        For live $DATE/$TIME values, use get_variable with var_name=DATE or TIME.

        Returns:
            str: JSON with showfile, version, host_status, active_user, hostname.
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({"error": "No snapshot available. Call hydrate_console_state first."})

        return json.dumps({
            "showfile":    snap.showfile,
            "version":     snap.version,
            "host_status": snap.host_status,
            "active_user": snap.active_user,
            "hostname":    snap.hostname,
            "note": "date/time are volatile — use get_variable(var_name='DATE') for live values",
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 133: watch_system_var                                          #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def watch_system_var(
        var_name: str,
        expected_value: str,
        timeout_seconds: float = 10.0,
        poll_interval: float = 0.5,
    ) -> str:
        """
        Poll a grandMA2 system variable until it matches an expected value or times out.

        Uses ListVar telnet command. Requires an active telnet connection.

        Args:
            var_name:        Variable name (with or without leading $, case-insensitive).
                             e.g. "FADERPAGE" or "$FADERPAGE"
            expected_value:  Value to wait for (string comparison).
            timeout_seconds: Maximum wait time in seconds (capped at 30.0).
            poll_interval:   Seconds between polls (minimum 0.1).

        Returns:
            str: JSON with matched, final_value, elapsed_seconds, polls.
        """
        import asyncio
        import json
        import time as _time

        send_fn = getattr(orchestrator, "_send", None)
        if send_fn is None:
            return json.dumps({
                "error": "No telnet connection configured on orchestrator.",
                "hint": "watch_system_var requires a live telnet session.",
            })

        timeout_seconds = min(float(timeout_seconds), 30.0)
        poll_interval   = max(float(poll_interval), 0.1)
        clean_name      = var_name.lstrip("$").upper()

        def _extract(raw: str) -> str | None:
            for line in raw.splitlines():
                line = line.strip()
                if " : " in line:
                    line = line.split(" : ", 1)[1].strip()
                if "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip().lstrip("$").upper() == clean_name:
                    return v.strip()
            return None

        t0 = _time.monotonic()
        polls = 0
        final_value = ""
        matched = False

        while (_time.monotonic() - t0) < timeout_seconds:
            raw = await send_fn("ListVar")
            polls += 1
            val = _extract(raw)
            if val is not None:
                final_value = val
                if val == expected_value:
                    matched = True
                    break
            await asyncio.sleep(poll_interval)

        return json.dumps({
            "matched":         matched,
            "final_value":     final_value,
            "expected_value":  expected_value,
            "var_name":        f"${clean_name}",
            "elapsed_seconds": round(_time.monotonic() - t0, 2),
            "polls":           polls,
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 134: confirm_destructive_steps                                 #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.CUE_STORE)
    @handle_errors_fn
    async def confirm_destructive_steps(
        goal: str,
        color: str = "",
        group: str = "",
        sequence: int = 1,
        cue: float = 1.0,
        preset: str = "",
    ) -> str:
        """
        Preview the DESTRUCTIVE steps in a task plan before running it.

        Decomposes the goal and returns only the steps that require explicit
        human confirmation (risk_tier == DESTRUCTIVE). Show this to the user
        before calling run_task with auto_confirm_destructive=True.

        Args:
            goal:     Natural-language task goal (same as run_task)
            color:    Target color name or hex
            group:    Fixture group name
            sequence: Target sequence number
            cue:      Target cue number
            preset:   Preset name or ID
        """
        import json
        params = {k: v for k, v in {
            "color": color, "group": group,
            "sequence": sequence, "cue": cue, "preset": preset,
        }.items() if v}

        decomposer = TaskDecomposer()
        plan = decomposer.decompose(goal, params)

        from .task_decomposer import RiskTier
        destructive = [
            {
                "step_index": i,
                "name": s.name,
                "description": s.description,
                "tool": s.mcp_tools[0] if s.mcp_tools else None,
                "tools": s.mcp_tools,
            }
            for i, s in enumerate(plan.ordered_steps())
            if s.allowed_risk == RiskTier.DESTRUCTIVE
        ]

        return json.dumps({
            "goal": goal,
            "total_steps": len(plan.steps),
            "destructive_count": len(destructive),
            "destructive_steps": destructive,
            "safe_to_run": len(destructive) == 0,
            "hint": (
                "No DESTRUCTIVE steps — safe to call run_task directly."
                if not destructive
                else "Review the steps above, then call run_task with auto_confirm_destructive=True."
            ),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 135: abort_task                                                #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.CUE_STORE)
    @handle_errors_fn
    async def abort_task(
        session_id: str,
        reason: str = "user_requested",
    ) -> str:
        """
        Mark a task session as aborted and return its completion status.

        Looks up the session in long-term memory and surfaces its completed/failed
        step list with an aborted label. Use this when a running task must be halted
        mid-way or when a completed session needs to be retroactively voided.

        Args:
            session_id: 8-char session ID from list_agent_sessions or run_task output.
            reason:     Abort reason string (default "user_requested").

        Returns:
            str: JSON with aborted, session_id, reason, steps_completed, steps_failed.
        """
        import json
        snapshot = orchestrator.recall(session_id)
        if snapshot is None:
            return json.dumps({
                "error": f"Session '{session_id}' not found in long-term memory.",
                "hint": "Use list_agent_sessions to browse available session IDs.",
            })

        return json.dumps({
            "aborted":         True,
            "session_id":      session_id,
            "reason":          reason,
            "task":            snapshot.get("task_description", ""),
            "steps_completed": snapshot.get("completed_steps", []),
            "steps_failed":    snapshot.get("failed_steps", []),
            "tokens_consumed": snapshot.get("token_spend", 0),
            "note": "Session marked aborted. No further steps will execute for this session.",
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 136: retry_failed_steps                                        #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.CUE_STORE)
    @handle_errors_fn
    async def retry_failed_steps(session_id: str) -> str:
        """
        Retry all failed steps from a prior task session.

        Loads the session from long-term memory, retrieves its original goal,
        and re-executes the task via run_task. Returns the retry outcome.

        This is a full re-run of the original goal, not a selective step replay.
        For selective step control, use decompose_task + run_task directly.

        Args:
            session_id: 8-char session ID from list_agent_sessions.

        Returns:
            str: JSON with retried, session_id, original_goal, new_session_id,
                 failed_steps_before, outcome.
        """
        import json
        snapshot = orchestrator.recall(session_id)
        if snapshot is None:
            return json.dumps({
                "error": f"Session '{session_id}' not found in long-term memory.",
                "hint": "Use list_agent_sessions to browse available session IDs.",
            })

        failed_steps = snapshot.get("failed_steps", [])
        if not failed_steps:
            return json.dumps({
                "retried": 0,
                "session_id": session_id,
                "message": "No failed steps in this session — nothing to retry.",
                "steps_completed": snapshot.get("completed_steps", []),
            })

        goal = snapshot.get("task_description", "")
        if not goal:
            return json.dumps({
                "error": "Session has no task_description — cannot retry.",
                "session_id": session_id,
            })

        result = await orchestrator.run(goal, auto_confirm_destructive=False)

        return json.dumps({
            "retried":            len(failed_steps),
            "session_id":         session_id,
            "new_session_id":     result.session_id,
            "original_goal":      goal,
            "failed_steps_before": failed_steps,
            "outcome":            result.outcome,
            "steps_done":         result.steps_done,
            "steps_failed":       result.steps_failed,
            "report":             result.report(),
        }, indent=2)

    # ------------------------------------------------------------------ #
    # Tool 137: assert_fixture_exists                                     #
    # ------------------------------------------------------------------ #
    @mcp.tool()
    @require_scope_fn(OAuthScope.DISCOVER)
    @handle_errors_fn
    async def assert_fixture_exists(fixture_id: int) -> str:
        """
        Assert that a fixture ID exists in the console patch.

        Two-tier lookup:
          1. If a ConsoleStateSnapshot is available and the Fixture pool is
             indexed, performs a zero-telnet check against the in-memory index.
          2. Otherwise sends `list fixture {id}` via telnet and checks for
             "NO OBJECTS FOUND" in the response (same mechanism as park_fixture).

        Use this before any selection or programming operation when the fixture
        ID is not guaranteed to be in the current patch.

        Args:
            fixture_id: The numeric fixture ID to check (e.g. 101).

        Returns:
            str: JSON with exists, fixture_id, source ("snapshot" or "live_telnet"),
                 and a hint if the fixture is not found.
        """
        import json

        # ── Tier 1: snapshot index (zero-telnet) ─────────────────────────
        snap = orchestrator.last_snapshot
        if snap is not None:
            fixture_entries = snap.name_index.all_entries("Fixture")
            if fixture_entries:
                exists = any(e["id"] == fixture_id for e in fixture_entries)
                return json.dumps({
                    "exists":     exists,
                    "fixture_id": fixture_id,
                    "source":     "snapshot",
                    "hint": (
                        None if exists
                        else (
                            f"Fixture {fixture_id} is not in the snapshot index. "
                            "It may not be patched. Call list_fixtures() to discover "
                            "valid IDs, or hydrate_console_state() to refresh the index."
                        )
                    ),
                }, indent=2)

        # ── Tier 2: live telnet probe ─────────────────────────────────────
        send_fn = getattr(orchestrator, "_send", None)
        if send_fn is None:
            return json.dumps({
                "error": (
                    "No telnet connection configured and no snapshot available. "
                    "Call hydrate_console_state first, or ensure the server "
                    "has a live telnet session."
                ),
                "fixture_id": fixture_id,
            })

        raw = await send_fn(f"list fixture {fixture_id}")
        exists = "NO OBJECTS FOUND" not in raw.upper()
        return json.dumps({
            "exists":       exists,
            "fixture_id":   fixture_id,
            "source":       "live_telnet",
            "raw_response": raw,
            "hint": (
                None if exists
                else (
                    f"Fixture {fixture_id} is not patched on the console. "
                    "Use list_fixtures() to discover valid fixture IDs."
                )
            ),
        }, indent=2)

    # ================================================================== #
    # OpenSpace layer — Tools 138–143                                     #
    # Telemetry + Skill registry + Improvement loop                       #
    # ================================================================== #

    # Import the telemetry singleton from server.py so Tools 138–143 read from the
    # exact same DB connection that @_handle_errors writes to. Creating a second
    # ToolTelemetry() instance would produce a split view with zero shared rows.
    import json as _json
    from .server import _get_telemetry as _get_server_telemetry
    _tel = _get_server_telemetry()
    _reg = SkillRegistry()
    _ltm_skill = LongTermMemory()
    _imp = SkillImprover(_tel, _reg, _ltm_skill)

    # ------------------------------------------------------------------ #
    # Tool 138: get_tool_metrics                                          #
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @require_scope_fn(OAuthScope.DISCOVER)
    @handle_errors_fn
    async def get_tool_metrics(
        tool_name: str,
        days: int = 7,
    ) -> str:
        """
        Return latency and error-rate statistics for a single MCP tool.

        Queries the ``tool_invocations`` telemetry table for all recorded
        calls to ``tool_name`` in the last ``days`` days.

        Returns call count, error rate, p50/p95 latency in milliseconds,
        and the distinct error classes seen.  Returns ``{"calls": 0}`` if
        no invocations have been recorded yet.

        Args:
            tool_name: Exact name of the MCP tool (e.g. "list_objects").
            days: Look-back window in days (default 7).
        """
        return _json.dumps(_tel.metrics(tool_name, days=days), indent=2)

    # ------------------------------------------------------------------ #
    # Tool 139: list_skills                                               #
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @require_scope_fn(OAuthScope.DISCOVER)
    @handle_errors_fn
    async def list_skills(
        query: str = "",
        limit: int = 20,
    ) -> str:
        """
        Search the skill registry for stored playbooks.

        If ``query`` is provided, performs a case-insensitive substring
        search across skill name, description, and applicable_context.
        If ``query`` is empty, returns the most recently updated skills.

        DESTRUCTIVE-scope skills are included in results regardless of
        their ``approved`` status so operators can review them.

        Args:
            query: Optional search term (e.g. "wash look", "color preset").
            limit: Maximum number of results to return (default 20).
        """
        skills = _reg.search(query, limit=limit) if query else _reg.list_all(limit=limit)
        return _json.dumps(
            {
                "query": query,
                "count": len(skills),
                "skills": [s.to_dict() for s in skills],
            },
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 140: get_skill                                                  #
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @require_scope_fn(OAuthScope.DISCOVER)
    @handle_errors_fn
    async def get_skill(skill_id: str) -> str:
        """
        Return full detail for a single skill including its lineage chain.

        Walks the ``parent_id`` chain to return all ancestor versions
        oldest-first, so you can see how the skill evolved over time.

        Args:
            skill_id: UUID of the skill to retrieve.
        """
        skill = _reg.get(skill_id)
        if skill is None:
            return _json.dumps({"error": f"Skill '{skill_id}' not found."}, indent=2)
        lineage = _reg.get_lineage(skill_id)
        return _json.dumps(
            {
                "skill": skill.to_dict(),
                "lineage": [s.to_dict() for s in lineage],
                "is_usable": skill.is_usable(),
            },
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 141: promote_session_to_skill                                  #
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @require_scope_fn(OAuthScope.PROGRAMMER_WRITE)
    @handle_errors_fn
    async def promote_session_to_skill(
        session_id: str,
        name: str,
        description: str,
        body: str,
        safety_scope: str = "SAFE_WRITE",
        applicable_context: str = "",
    ) -> str:
        """
        Promote a completed agent session to a named, versioned Skill.

        The skill is stored in the registry with a quality score derived
        from the session's step success ratio.

        Safety rule: if ``safety_scope`` is ``DESTRUCTIVE``, the skill is
        created with ``approved=False`` and cannot be used until an operator
        calls ``approve_skill`` (requires SYSTEM_ADMIN scope).

        Args:
            session_id:        ID of the session to promote (8-char prefix or full UUID).
            name:              Short human name for the skill (e.g. "blue_wash_look").
            description:       One-line purpose statement.
            body:              Markdown playbook — steps, caveats, example inputs.
            safety_scope:      "SAFE_READ" | "SAFE_WRITE" | "DESTRUCTIVE"  (default SAFE_WRITE).
            applicable_context: Free-text retrieval hint (e.g. "color wash cue storage").
        """
        quality = _imp.quality_score_for_session(session_id)
        skill = _reg.promote_from_session(
            session_id=session_id,
            name=name,
            description=description,
            body=body,
            safety_scope=safety_scope,
            applicable_context=applicable_context,
            quality_score=quality,
        )
        return _json.dumps(
            {
                "promoted": True,
                "skill_id": skill.id,
                "name": skill.name,
                "version": skill.version,
                "safety_scope": skill.safety_scope,
                "approved": skill.approved,
                "quality_score": skill.quality_score,
                "note": (
                    "Skill is DESTRUCTIVE-scope and requires approve_skill() "
                    "before agents can use it."
                    if not skill.approved
                    else None
                ),
            },
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 142: get_improvement_suggestions                               #
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @require_scope_fn(OAuthScope.DISCOVER)
    @handle_errors_fn
    async def get_improvement_suggestions(
        days: int = 7,
        min_failures: int = 3,
        min_quality: float = 0.8,
    ) -> str:
        """
        Return repair suggestions and promotion candidates from the analyser.

        Repair suggestions: tools failing >= ``min_failures`` times in the
        last ``days`` days, with a human-readable hint for each.

        Promotion candidates: successful sessions not yet promoted to Skills,
        with quality score >= ``min_quality``.

        This tool is read-only — it never writes to the skill registry.

        Args:
            days:          Look-back window for failure detection (default 7).
            min_failures:  Minimum error count to flag a tool (default 3).
            min_quality:   Minimum session quality to suggest promotion (default 0.8).
        """
        repairs = _imp.identify_failure_patterns(days=days, min_failures=min_failures)
        candidates = _imp.identify_promotion_candidates(min_quality=min_quality)
        return _json.dumps(
            {
                "repair_suggestions": [
                    {
                        "tool_name": r.tool_name,
                        "failure_count": r.failure_count,
                        "error_classes": r.error_classes,
                        "hint": r.hint,
                    }
                    for r in repairs
                ],
                "promotion_candidates": [
                    {
                        "session_id": c.session_id,
                        "task": c.task,
                        "outcome": c.outcome,
                        "steps_done": c.steps_done,
                        "steps_failed": c.steps_failed,
                        "tokens": c.tokens,
                        "quality_score": c.quality_score,
                        "suggested_name": c.suggested_name,
                    }
                    for c in candidates
                ],
            },
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 143: approve_skill                                             #
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @require_scope_fn(OAuthScope.SYSTEM_ADMIN)
    @handle_errors_fn
    async def approve_skill(skill_id: str) -> str:
        """
        Approve a DESTRUCTIVE-scope skill for agent use.

        Sets ``approved=True`` on the named skill.  Once approved, agents
        with sufficient OAuth scope may invoke the skill's playbook.

        This tool requires ``OAuthScope.SYSTEM_ADMIN`` (tier 5 / ``GMA_SCOPE=tier:5``).
        It is the human gate that prevents autonomous DESTRUCTIVE skill promotion.

        Args:
            skill_id: UUID of the skill to approve.
        """
        skill = _reg.get(skill_id)
        if skill is None:
            return _json.dumps({"error": f"Skill '{skill_id}' not found."}, indent=2)
        ok = _reg.approve(skill_id)
        return _json.dumps(
            {
                "approved": ok,
                "skill_id": skill_id,
                "skill_name": skill.name,
                "safety_scope": skill.safety_scope,
                "note": (
                    "Skill approved — agents may now invoke its playbook."
                    if ok
                    else "Skill not found."
                ),
            },
            indent=2,
        )

    # ------------------------------------------------------------------ #
    # Tool 144: assert_showfile_unchanged                                  #
    # ------------------------------------------------------------------ #

    @mcp.tool()
    @require_scope_fn(OAuthScope.STATE_READ)
    @handle_errors_fn
    async def assert_showfile_unchanged() -> str:
        """
        Verify the currently open show matches the baseline captured at last hydration.

        Performs a live ListVar read and compares $SHOWFILE against the cached
        ConsoleStateSnapshot. Use this before committing a batch of DESTRUCTIVE
        changes to confirm the operator has not loaded a different show since
        the last hydrate_console_state call.

        Returns:
            JSON with {"ok": true, "showfile": name} when unchanged.
            JSON with {"ok": false, "expected": baseline, "actual": live}
            when the show has changed.
            JSON with {"ok": false, "reason": "..."} when not yet hydrated
            or telnet is unavailable.

        Risk tier: SAFE_READ
        """
        import json
        snap = orchestrator.last_snapshot
        if snap is None:
            return json.dumps({
                "ok": False,
                "reason": "Not hydrated — call hydrate_console_state first.",
            })
        baseline, live = await orchestrator.check_showfile()
        if not live:
            return json.dumps({
                "ok": False,
                "reason": "Could not read live $SHOWFILE — telnet unavailable.",
            })
        if live == baseline:
            return json.dumps({"ok": True, "showfile": live})
        return json.dumps({
            "ok": False,
            "expected": baseline,
            "actual": live,
            "action": "Call hydrate_console_state to re-sync agent memory to the new show.",
        })

