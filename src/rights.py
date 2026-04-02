"""
rights.py — MA2-native rights enforcement and telnet feedback classification.

Provides:
  - RightsContext: per-session rights info derived from ConsoleStateSnapshot
  - FeedbackClass: classification of telnet/MCP tool responses
  - TelnetFeedback: parsed feedback from a single tool call
  - parse_telnet_feedback(): classify any tool response string
  - is_permitted(): check if a tool is allowed at a given rights level
  - min_right_for_tool(): lookup minimum MA2Right for a named tool
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

# Import MA2Right from its authoritative location — never redefine it here.
from .commands.constants import MA2Right

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Rights ordering — maps MA2Right value to a comparable integer tier
# ---------------------------------------------------------------------------

_RIGHT_ORDER: dict[str, int] = {
    MA2Right.NONE:     0,
    MA2Right.PLAYBACK: 1,
    MA2Right.PRESETS:  2,
    MA2Right.PROGRAM:  3,
    MA2Right.SETUP:    4,
    MA2Right.ADMIN:    5,
}


def _right_tier(right: MA2Right) -> int:
    return _RIGHT_ORDER.get(right, 0)


# ---------------------------------------------------------------------------
# Minimum-right lookup table (derived from doc/ma2-rights-matrix.json)
# ---------------------------------------------------------------------------

_OPERATION_MIN_RIGHT: dict[str, MA2Right] = {
    # none (0)
    "navigate_console":           MA2Right.NONE,
    "get_console_location":       MA2Right.NONE,
    "list_console_destination":   MA2Right.NONE,
    "scan_console_indexes":       MA2Right.NONE,
    "get_object_info":            MA2Right.NONE,
    "query_object_list":          MA2Right.NONE,
    "list_system_variables":      MA2Right.NONE,
    "search_codebase":            MA2Right.NONE,
    "browse_preset_type":         MA2Right.NONE,
    "get_executor_status":        MA2Right.NONE,
    "list_fixtures":              MA2Right.NONE,
    "list_sequence_cues":         MA2Right.NONE,
    "list_shows":                 MA2Right.NONE,
    "get_variable":               MA2Right.NONE,
    "list_preset_pool":           MA2Right.NONE,
    "list_undo_history":          MA2Right.NONE,
    "list_fixture_types":         MA2Right.NONE,
    "list_layers":                MA2Right.NONE,
    "list_universes":             MA2Right.NONE,
    "list_library":               MA2Right.NONE,
    "discover_filter_attributes": MA2Right.NONE,
    "browse_patch_schedule":      MA2Right.NONE,
    "check_pool_availability":    MA2Right.NONE,
    "discover_object_names":      MA2Right.NONE,
    "list_tool_categories":       MA2Right.NONE,
    "recluster_tools":            MA2Right.NONE,
    "get_similar_tools":          MA2Right.NONE,
    "suggest_tool_for_task":      MA2Right.NONE,
    "browse_effect_library":      MA2Right.NONE,
    "browse_macro_library":       MA2Right.NONE,
    "browse_plugin_library":      MA2Right.NONE,
    "list_fader_modules":         MA2Right.NONE,
    "list_update_history":        MA2Right.NONE,
    "generate_fixture_layer_xml": MA2Right.NONE,
    "decompose_task":             MA2Right.NONE,
    "resolve_object_ref":         MA2Right.NONE,
    "list_pool_names":            MA2Right.NONE,
    # playback (1)
    "execute_sequence":           MA2Right.PLAYBACK,
    "playback_action":            MA2Right.PLAYBACK,
    "run_macro":                  MA2Right.PLAYBACK,
    "set_executor_level":         MA2Right.PLAYBACK,
    "navigate_page":              MA2Right.PLAYBACK,
    "undo_last_action":           MA2Right.PLAYBACK,
    "toggle_console_mode":        MA2Right.PLAYBACK,
    "control_executor":           MA2Right.PLAYBACK,
    "load_cue":                   MA2Right.PLAYBACK,
    "select_executor":            MA2Right.PLAYBACK,
    "release_executor":           MA2Right.PLAYBACK,
    "blackout_toggle":            MA2Right.PLAYBACK,
    "save_show":                  MA2Right.PLAYBACK,
    "control_timecode":           MA2Right.PLAYBACK,
    "control_timer":              MA2Right.PLAYBACK,
    "assign_temp_fader":          MA2Right.PLAYBACK,
    "list_agent_sessions":        MA2Right.PLAYBACK,
    "recall_agent_session":       MA2Right.PLAYBACK,
    "agent_token_report":         MA2Right.PLAYBACK,
    "hydrate_console_state":      MA2Right.PLAYBACK,
    # presets (2)
    "set_intensity":              MA2Right.PRESETS,
    "apply_preset":               MA2Right.PRESETS,
    "clear_programmer":           MA2Right.PRESETS,
    "set_attribute":              MA2Right.PRESETS,
    "park_fixture":               MA2Right.PRESETS,
    "unpark_fixture":             MA2Right.PRESETS,
    "store_new_preset":           MA2Right.PRESETS,
    "manage_variable":            MA2Right.PRESETS,
    "select_feature":             MA2Right.PRESETS,
    "select_preset_type":         MA2Right.PRESETS,
    "modify_selection":           MA2Right.PRESETS,
    "adjust_value_relative":      MA2Right.PRESETS,
    "select_fixtures_by_group":   MA2Right.PRESETS,
    "fix_locate_fixture":         MA2Right.PRESETS,
    "manipulate_selection":       MA2Right.PRESETS,
    "remove_from_programmer":     MA2Right.PRESETS,
    "if_filter":                  MA2Right.PRESETS,
    "highlight_fixtures":         MA2Right.PRESETS,
    "manage_matricks":            MA2Right.PRESETS,
    # program (3)
    "create_fixture_group":       MA2Right.PROGRAM,
    "send_raw_command":           MA2Right.PROGRAM,
    "store_current_cue":          MA2Right.PROGRAM,
    "delete_object":              MA2Right.PROGRAM,
    "copy_or_move_object":        MA2Right.PROGRAM,
    "label_or_appearance":        MA2Right.PROGRAM,
    "assign_object":              MA2Right.PROGRAM,
    "edit_object":                MA2Right.PROGRAM,
    "remove_content":             MA2Right.PROGRAM,
    "store_object":               MA2Right.PROGRAM,
    "update_cue_data":            MA2Right.PROGRAM,
    "set_cue_timing":             MA2Right.PROGRAM,
    "block_unblock_cue":          MA2Right.PROGRAM,
    "store_timecode_event":       MA2Right.PROGRAM,
    "set_sequence_property":      MA2Right.PROGRAM,
    "store_cue_with_timing":      MA2Right.PROGRAM,
    "assign_cue_trigger":         MA2Right.PROGRAM,
    "cut_paste_object":           MA2Right.PROGRAM,
    "clone_object":               MA2Right.PROGRAM,
    "store_matricks_preset":      MA2Right.PROGRAM,
    "create_matricks_library":    MA2Right.PROGRAM,
    "create_filter_library":      MA2Right.PROGRAM,
    "save_recall_view":           MA2Right.PROGRAM,
    "export_objects":             MA2Right.PROGRAM,
    "run_task":                   MA2Right.PROGRAM,
    # setup (4)
    "set_node_property":          MA2Right.SETUP,
    "assign_executor_property":   MA2Right.SETUP,
    "import_objects":             MA2Right.SETUP,
    "import_fixture_type":        MA2Right.SETUP,
    "import_fixture_layer":       MA2Right.SETUP,
    "patch_fixture":              MA2Right.SETUP,
    "unpatch_fixture":            MA2Right.SETUP,
    "set_fixture_type_property":  MA2Right.SETUP,
    # admin (5)
    "load_show":                  MA2Right.ADMIN,
    "new_show":                   MA2Right.ADMIN,
    "delete_show":                MA2Right.ADMIN,
    "list_console_users":         MA2Right.ADMIN,
    "create_console_user":        MA2Right.ADMIN,
    "assign_world_to_user_profile": MA2Right.ADMIN,
    "inspect_sessions":           MA2Right.ADMIN,
    "delete_user":                MA2Right.ADMIN,
    "register_decomposition_rule": MA2Right.ADMIN,
    # ── Previously unmapped tools (added during hardening pass) ──────────
    # none (0) — read-only inspection / validation
    "classify_show_mode":           MA2Right.NONE,
    "diff_console_state":           MA2Right.NONE,
    "detect_dmx_address_conflicts": MA2Right.NONE,
    "validate_preset_references":   MA2Right.NONE,
    "check_pool_slot_availability": MA2Right.NONE,
    "rdm_get_info":                 MA2Right.NONE,
    "scan_page_executor_layout":    MA2Right.NONE,
    "generate_compliance_report":   MA2Right.NONE,
    "plan_agent_goal":              MA2Right.NONE,
    "watch_system_var":             MA2Right.NONE,
    # playback (1) — fader/effect/chaser control
    "control_chaser":               MA2Right.PLAYBACK,
    "control_special_master":       MA2Right.PLAYBACK,
    "master_control":               MA2Right.PLAYBACK,
    "modulate_effect":              MA2Right.PLAYBACK,
    "normalize_page_faders":        MA2Right.PLAYBACK,
    "clear_effects_on_page":        MA2Right.PLAYBACK,
    "set_effect_param":             MA2Right.PLAYBACK,
    "hydrate_sequences":            MA2Right.PLAYBACK,
    # presets (2) — executor config, UI lock
    "set_executor_priority":        MA2Right.PRESETS,
    "unlock_console_ui":            MA2Right.PRESETS,
    # program (3) — store/label/modify objects
    "store_world":                  MA2Right.PROGRAM,
    "store_agenda":                 MA2Right.PROGRAM,
    "label_world":                  MA2Right.PROGRAM,
    "update_object":                MA2Right.PROGRAM,
    "remap_fixture_ids":            MA2Right.PROGRAM,
    "programming_action":           MA2Right.PROGRAM,
    # setup (4) — patch, RDM, plugins, scripting
    "assign_effect_to_executor":    MA2Right.SETUP,
    "rdm_discover":                 MA2Right.SETUP,
    "rdm_patch":                    MA2Right.SETUP,
    "reload_all_plugins":           MA2Right.SETUP,
    "call_plugin_tool":             MA2Right.SETUP,
    "run_lua_script":               MA2Right.SETUP,
    "plugin_management":            MA2Right.SETUP,
    # admin (5) — auth, system admin, agent harness
    "console_login":                MA2Right.ADMIN,
    "console_logout":               MA2Right.ADMIN,
    "lock_console_ui":              MA2Right.ADMIN,
    "system_admin":                 MA2Right.ADMIN,
    "confirm_destructive_steps":    MA2Right.ADMIN,
    "abort_task":                   MA2Right.ADMIN,
    "retry_failed_steps":           MA2Right.ADMIN,
    "promote_session_to_skill":     MA2Right.ADMIN,
    "approve_skill":                MA2Right.ADMIN,
    "run_agent_goal":               MA2Right.ADMIN,
    # ── New tools (batch operations + diagnostics) ──────────────────────
    "batch_label":                  MA2Right.PROGRAM,
    "bulk_executor_assign":         MA2Right.SETUP,
    "auto_number_cues":             MA2Right.PROGRAM,
    "compare_cue_values":           MA2Right.NONE,
    "diagnose_no_output":           MA2Right.NONE,
    # ── Companion integration ───────────────────────────────────────────
    "generate_companion_config":    MA2Right.NONE,
    "companion_button_press":       MA2Right.PLAYBACK,
    # ── BPM sync ────────────────────────────────────────────────────────
    "set_bpm":                      MA2Right.PLAYBACK,
}

# MA2 console error code for rights denial
_RIGHTS_DENIAL_CODES = frozenset({"Error #72", "#72", "insufficient rights", "access denied"})
_RIGHTS_DENIAL_RE = re.compile(r"Error\s+#72|insufficient\s+rights|access\s+denied", re.IGNORECASE)


# ---------------------------------------------------------------------------
# FeedbackClass
# ---------------------------------------------------------------------------

class FeedbackClass(StrEnum):
    """Classification of a tool call's outcome relative to rights enforcement."""
    PASS_ALLOWED  = "PASS_ALLOWED"   # permitted and succeeded
    PASS_DENIED   = "PASS_DENIED"    # correctly blocked by MCP gate
    FAILED_OPEN   = "FAILED_OPEN"    # slipped past gate, console rejected — dangerous
    FAILED_CLOSED = "FAILED_CLOSED"  # blocked by gate, should have been allowed
    INCONCLUSIVE  = "INCONCLUSIVE"   # cannot determine outcome


# ---------------------------------------------------------------------------
# TelnetFeedback
# ---------------------------------------------------------------------------

@dataclass
class TelnetFeedback:
    """Parsed classification of a single tool call response."""
    feedback_class: FeedbackClass
    accepted: bool          # True if the response indicates success
    is_rights_denial: bool  # True if MA2 returned Error #72 or equivalent
    error_code: str = ""    # The specific error code if detected


# ---------------------------------------------------------------------------
# parse_telnet_feedback
# ---------------------------------------------------------------------------

def parse_telnet_feedback(
    response_str: str,
    tool_name: str = "",
    user_right: MA2Right = MA2Right.NONE,
) -> TelnetFeedback:
    """
    Classify a tool response string into a FeedbackClass.

    Decision tree:
    1. If response contains "blocked": True → PASS_DENIED (MCP scope gate fired)
    2. If response contains Error #72 or equivalent → FAILED_OPEN (console rejected
       after MCP gate let it through — review _OPERATION_MIN_RIGHT)
    3. If response contains "error" but NOT rights-related → INCONCLUSIVE
    4. Otherwise → PASS_ALLOWED
    """
    import json as _json

    # Try JSON parsing first for structured responses
    try:
        data = _json.loads(response_str)
        if isinstance(data, dict):
            if data.get("blocked") is True:
                return TelnetFeedback(
                    feedback_class=FeedbackClass.PASS_DENIED,
                    accepted=False,
                    is_rights_denial=False,
                )
            if "error" in data:
                # Check if it's a rights denial
                error_str = str(data["error"])
                rights_match = _RIGHTS_DENIAL_RE.search(error_str)
                if rights_match:
                    return TelnetFeedback(
                        feedback_class=FeedbackClass.FAILED_OPEN,
                        accepted=False,
                        is_rights_denial=True,
                        error_code=rights_match.group(0),
                    )
                return TelnetFeedback(
                    feedback_class=FeedbackClass.INCONCLUSIVE,
                    accepted=False,
                    is_rights_denial=False,
                )
            return TelnetFeedback(
                feedback_class=FeedbackClass.PASS_ALLOWED,
                accepted=True,
                is_rights_denial=False,
            )
    except (ValueError, TypeError):
        pass  # Not JSON — fall through to string matching

    s = response_str.lower()

    # Check for MCP scope block (string fallback)
    if '"blocked": true' in response_str or "'blocked': true" in s or '"blocked":true' in response_str:
        return TelnetFeedback(
            feedback_class=FeedbackClass.PASS_DENIED,
            accepted=False,
            is_rights_denial=False,
        )

    # Check for MA2 rights denial (Error #72)
    rights_match = _RIGHTS_DENIAL_RE.search(response_str)
    if rights_match:
        return TelnetFeedback(
            feedback_class=FeedbackClass.FAILED_OPEN,
            accepted=False,
            is_rights_denial=True,
            error_code=rights_match.group(0),
        )

    # Check for other errors
    if '"error"' in s or "error" in s:
        return TelnetFeedback(
            feedback_class=FeedbackClass.INCONCLUSIVE,
            accepted=False,
            is_rights_denial=False,
        )

    return TelnetFeedback(
        feedback_class=FeedbackClass.PASS_ALLOWED,
        accepted=True,
        is_rights_denial=False,
    )


# ---------------------------------------------------------------------------
# RightsContext
# ---------------------------------------------------------------------------

@dataclass
class RightsContext:
    """Active user's MA2 native rights level for a task session."""

    user_right: MA2Right = MA2Right.NONE
    username: str = ""

    def can_execute(self, tool_name: str) -> bool:
        """Return True if this rights level permits calling the named tool."""
        return is_permitted(tool_name, self.user_right)

    def denial_message(self, tool_name: str) -> str:
        min_r = min_right_for_tool(tool_name)
        return (
            f"Tool '{tool_name}' requires {min_r.value} rights "
            f"(current: {self.user_right.value} for user '{self.username}')"
        )

    def upr_flag(self) -> str:
        """Returns /UPR=N flag for playback commands scoped to this user profile."""
        tier = _right_tier(self.user_right)
        return f"/UPR={tier}"

    def summary(self) -> str:
        return f"RightsContext(user={self.username!r}, rights={self.user_right.value})"

    @classmethod
    def from_snapshot(cls, snapshot: Any) -> RightsContext:
        """Build a RightsContext from a ConsoleStateSnapshot."""
        return cls(
            user_right=snapshot.user_right,
            username=snapshot.active_user,
        )


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def min_right_for_tool(tool_name: str) -> MA2Right:
    """Return the minimum MA2Right required for a named tool."""
    return _OPERATION_MIN_RIGHT.get(tool_name, MA2Right.NONE)


def is_permitted(tool_name: str, user_right: MA2Right) -> bool:
    """Return True if user_right is >= the minimum required for tool_name."""
    required = _OPERATION_MIN_RIGHT.get(tool_name, MA2Right.NONE)
    return _right_tier(user_right) >= _right_tier(required)


@dataclass(frozen=True)
class PermissionResult:
    """Result of a unified permission check (scope ∩ MA2Right)."""
    allowed: bool
    tool_name: str
    required_right: MA2Right
    required_scope: str
    scope_ok: bool        # OAuth scope gate passed
    rights_ok: bool       # MA2Right gate passed
    denial_reason: str = ""

    def as_block_response(self) -> dict:
        """Return a JSON-serializable block dict matching the _handle_errors format."""
        return {
            "blocked": True,
            "error": self.denial_reason,
            "tool": self.tool_name,
            "required_ma2_right": self.required_right.value,
            "required_scope": self.required_scope,
            "scope_ok": self.scope_ok,
            "rights_ok": self.rights_ok,
        }


def check_permission(
    tool_name: str,
    granted_scopes: frozenset[str],
    user_right: MA2Right = MA2Right.NONE,
) -> PermissionResult:
    """
    Unified pre-execution permission gate: scope ∩ MA2Right = FINAL AUTHORITY.

    Enforces that BOTH layers agree before a tool is allowed to proceed:
      - Layer 1 (OAuth scope): the caller's granted scopes cover the required scope
      - Layer 3 (MA2 native rights): the console user's rights level is sufficient

    Layer 2 (policy / show-phase) is a future extension point; this function
    provides the choke point where it would be inserted.

    Args:
        tool_name:      MCP tool function name (looked up in _OPERATION_MIN_RIGHT)
        granted_scopes: frozenset of OAuth scope strings for the current session
        user_right:     MA2Right of the currently logged-in console user
                        (from ConsoleStateSnapshot.user_right; defaults to NONE
                        if console state has not been hydrated)

    Returns:
        PermissionResult — check .allowed before proceeding
    """
    from .commands.constants import MA2RIGHT_TO_OAUTH_SCOPE

    required_right = min_right_for_tool(tool_name)
    required_scope = str(MA2RIGHT_TO_OAUTH_SCOPE[required_right])

    scope_ok = required_scope in granted_scopes
    rights_ok = _right_tier(user_right) >= _right_tier(required_right)
    allowed = scope_ok and rights_ok

    if allowed:
        denial = ""
    elif not scope_ok and not rights_ok:
        denial = (
            f"Tool '{tool_name}' requires scope '{required_scope}' "
            f"and MA2 rights '{required_right.value}' — both denied."
        )
    elif not scope_ok:
        denial = (
            f"Tool '{tool_name}' requires OAuth scope '{required_scope}' "
            f"(MA2Right.{required_right.name})."
        )
    else:
        denial = (
            f"Tool '{tool_name}' requires MA2 rights '{required_right.value}' "
            f"(current: '{user_right.value}')."
        )

    return PermissionResult(
        allowed=allowed,
        tool_name=tool_name,
        required_right=required_right,
        required_scope=required_scope,
        scope_ok=scope_ok,
        rights_ok=rights_ok,
        denial_reason=denial,
    )
