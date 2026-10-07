"""
Tool profiles — which MCP tools a client sees (GMA_TOOL_PROFILE).

Every registered tool costs context in clients that load all tool schemas up
front. Profiles expose a curated subset; ``full`` (the default) exposes all.
Smaller profiles pick one tool per overlapping cluster (e.g. get_executor_state
over get_executor_status/get_executor_detail). Hidden tools stay callable by
the agent harness — only the MCP-visible list shrinks. Pure module, no I/O.
"""

from __future__ import annotations

PROFILES = ("core", "standard", "full")
DEFAULT_PROFILE = "full"

# Inspect, safe entry points, the agent harness, and the escape hatches.
CORE_TOOLS: frozenset[str] = frozenset({
    "navigate_console", "list_console_destination", "get_object_info", "query_object_list",
    "discover_object_names", "list_system_variables", "get_variable",
    "suggest_tool_for_task", "list_skills", "get_skill",
    "plan_agent_goal", "run_agent_goal", "hydrate_console_state", "get_console_state",
    "send_raw_command", "run_command_batch", "answer_console_popup", "disconnect_console",
    "playback_action", "set_intensity", "clear_programmer",
    "get_executor_state", "scan_page_executor_layout", "list_fixtures", "list_sequence_cues",
    "save_show", "undo_last_action", "diagnose_no_output",
})

# Day-to-day programming on top of core.
STANDARD_TOOLS: frozenset[str] = CORE_TOOLS | frozenset({
    # store / edit
    "store_current_cue", "store_cue_with_timing", "store_new_preset", "store_object",
    "update_cue_data", "update_object", "delete_object", "copy_or_move_object",
    "label_or_appearance", "batch_label", "create_fixture_group",
    # selection / values
    "select_fixtures_by_group", "modify_selection", "set_attribute", "apply_preset",
    "highlight_fixtures", "park_fixture", "unpark_fixture", "get_park_ledger",
    # playback / executors
    "assign_object", "assign_executor_property", "set_executor_level", "set_executor_priority",
    "set_cue_timing", "set_sequence_property", "execute_sequence", "release_executor",
    "control_executor", "control_chaser", "navigate_page", "get_page_map",
    "master_control", "set_bpm", "toggle_console_mode", "blackout_toggle",
    # pools / effects / matricks
    "list_preset_pool", "list_pool_names", "list_effects_pool", "browse_effect_library",
    "assign_effect_to_executor", "set_effect_param", "manage_matricks", "get_matricks_state",
    "check_pool_slot_availability",
    # patch / fixture types
    "list_fixture_types", "patch_fixture", "unpatch_fixture", "import_fixture_type",
    "analyze_patch_types", "create_presets_for_patch", "build_show_from_patch",
    # timecode / macros / variables
    "list_timecode_events", "store_timecode_event", "control_timecode",
    "run_macro", "manage_variable", "run_lua_script",
    # show files
    "list_shows", "load_show", "new_show", "export_objects", "import_objects",
    # analysis / safety
    "diff_cues", "find_preset_usages", "validate_preset_references", "detect_tracking_leaks",
    "detect_programmer_contamination", "detect_console_divergence", "snapshot_console_baseline",
    "assert_showfile_unchanged", "incident_snapshot", "list_undo_history",
    # connection / users / docs
    "reconfigure_connection", "discover_consoles", "list_console_users", "search_codebase",
})

_TOOLS_BY_PROFILE: dict[str, frozenset[str] | None] = {
    "core": CORE_TOOLS,
    "standard": STANDARD_TOOLS,
    "full": None,  # everything registered
}


def resolve_profile(value: str | None) -> tuple[str, str | None]:
    """Normalize a GMA_TOOL_PROFILE value → (profile, warning or None)."""
    profile = (value or DEFAULT_PROFILE).strip().lower()
    if profile in PROFILES:
        return profile, None
    return DEFAULT_PROFILE, f"Unknown GMA_TOOL_PROFILE={value!r}; using '{DEFAULT_PROFILE}'. Valid: {PROFILES}"


def visible_tools(profile: str, registered: set[str]) -> set[str]:
    """Registered tool names a client sees under *profile*."""
    allowed = _TOOLS_BY_PROFILE[profile]
    return set(registered) if allowed is None else set(registered) & allowed


def tier_of(tool_name: str) -> str:
    """Smallest profile that includes *tool_name*."""
    if tool_name in CORE_TOOLS:
        return "core"
    if tool_name in STANDARD_TOOLS:
        return "standard"
    return "full"
