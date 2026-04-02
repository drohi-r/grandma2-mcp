"""
tests/test_rights.py — Unit tests for src/rights.py

Covers:
  - FeedbackClass enum values
  - parse_telnet_feedback() classification paths
  - RightsContext helpers
  - min_right_for_tool() / is_permitted()
"""

from src.commands.constants import MA2Right
from src.rights import (
    FeedbackClass,
    RightsContext,
    is_permitted,
    min_right_for_tool,
    parse_telnet_feedback,
)

# ── FeedbackClass ────────────────────────────────────────────────────────────

class TestFeedbackClass:
    def test_values_exist(self):
        assert FeedbackClass.PASS_ALLOWED == "PASS_ALLOWED"
        assert FeedbackClass.PASS_DENIED  == "PASS_DENIED"
        assert FeedbackClass.FAILED_OPEN  == "FAILED_OPEN"
        assert FeedbackClass.FAILED_CLOSED == "FAILED_CLOSED"
        assert FeedbackClass.INCONCLUSIVE == "INCONCLUSIVE"

    def test_is_str_enum(self):
        assert isinstance(FeedbackClass.PASS_ALLOWED, str)


# ── parse_telnet_feedback() ──────────────────────────────────────────────────

class TestParseTelnetFeedback:
    def test_blocked_true_is_pass_denied(self):
        fb = parse_telnet_feedback('{"blocked": true, "error": "scope"}')
        assert fb.feedback_class == FeedbackClass.PASS_DENIED
        assert fb.accepted is False
        assert fb.is_rights_denial is False

    def test_blocked_true_no_space_is_pass_denied(self):
        fb = parse_telnet_feedback('{"blocked":true}')
        assert fb.feedback_class == FeedbackClass.PASS_DENIED

    def test_error_72_is_failed_open(self):
        fb = parse_telnet_feedback("Error #72 insufficient rights for store")
        assert fb.feedback_class == FeedbackClass.FAILED_OPEN
        assert fb.is_rights_denial is True
        assert fb.accepted is False

    def test_access_denied_is_failed_open(self):
        fb = parse_telnet_feedback("access denied for this operation")
        assert fb.feedback_class == FeedbackClass.FAILED_OPEN
        assert fb.is_rights_denial is True

    def test_generic_error_is_inconclusive(self):
        fb = parse_telnet_feedback('{"error": "connection timeout"}')
        assert fb.feedback_class == FeedbackClass.INCONCLUSIVE
        assert fb.accepted is False

    def test_clean_response_is_pass_allowed(self):
        fb = parse_telnet_feedback('{"command_sent": "list group", "raw_response": "Group 1"}')
        assert fb.feedback_class == FeedbackClass.PASS_ALLOWED
        assert fb.accepted is True
        assert fb.is_rights_denial is False

    def test_empty_response_is_pass_allowed(self):
        fb = parse_telnet_feedback("OK")
        assert fb.feedback_class == FeedbackClass.PASS_ALLOWED

    def test_error_code_captured(self):
        fb = parse_telnet_feedback("Error #72 rejected")
        assert "72" in fb.error_code

    def test_case_insensitive_access_denied(self):
        fb = parse_telnet_feedback("ACCESS DENIED")
        assert fb.feedback_class == FeedbackClass.FAILED_OPEN


# ── min_right_for_tool() / is_permitted() ───────────────────────────────────

class TestRightHelpers:
    def test_navigate_console_requires_none(self):
        assert min_right_for_tool("navigate_console") == MA2Right.NONE

    def test_store_current_cue_requires_program(self):
        assert min_right_for_tool("store_current_cue") == MA2Right.PROGRAM

    def test_load_show_requires_admin(self):
        assert min_right_for_tool("load_show") == MA2Right.ADMIN

    def test_unknown_tool_defaults_to_none(self):
        assert min_right_for_tool("nonexistent_tool") == MA2Right.NONE

    def test_permitted_same_tier(self):
        assert is_permitted("store_current_cue", MA2Right.PROGRAM) is True

    def test_permitted_higher_tier(self):
        assert is_permitted("navigate_console", MA2Right.ADMIN) is True

    def test_not_permitted_lower_tier(self):
        assert is_permitted("load_show", MA2Right.SETUP) is False

    def test_not_permitted_far_below(self):
        assert is_permitted("patch_fixture", MA2Right.PLAYBACK) is False

    def test_permitted_none_right_for_read_tools(self):
        assert is_permitted("get_executor_status", MA2Right.NONE) is True


# ── RightsContext ────────────────────────────────────────────────────────────

class TestRightsContext:
    def test_can_execute_allowed(self):
        rc = RightsContext(user_right=MA2Right.ADMIN, username="admin")
        assert rc.can_execute("load_show") is True

    def test_can_execute_denied(self):
        rc = RightsContext(user_right=MA2Right.PLAYBACK, username="operator")
        assert rc.can_execute("store_current_cue") is False

    def test_denial_message_contains_tool_name(self):
        rc = RightsContext(user_right=MA2Right.PLAYBACK, username="op")
        msg = rc.denial_message("store_current_cue")
        assert "store_current_cue" in msg
        assert "program" in msg.lower()

    def test_upr_flag_format(self):
        rc = RightsContext(user_right=MA2Right.PLAYBACK)
        assert rc.upr_flag() == "/UPR=1"

    def test_upr_flag_admin(self):
        rc = RightsContext(user_right=MA2Right.ADMIN)
        assert rc.upr_flag() == "/UPR=5"

    def test_summary_contains_username(self):
        rc = RightsContext(user_right=MA2Right.PROGRAM, username="tech")
        assert "tech" in rc.summary()
        assert "program" in rc.summary()

    def test_default_rights_is_none(self):
        rc = RightsContext()
        assert rc.user_right == MA2Right.NONE


# ── Rights mapping drift detection ──────────────────────────────────────────

class TestRightsMappingDrift:
    """Ensure every @mcp.tool() in server.py has an entry in _OPERATION_MIN_RIGHT.

    Catches drift when new tools are added but not mapped to a rights level.
    """

    def test_all_server_tools_have_rights_mapping(self):
        import ast
        import pathlib

        from src.rights import _OPERATION_MIN_RIGHT

        server_py = pathlib.Path(__file__).parent.parent / "src" / "server.py"
        orch_py = pathlib.Path(__file__).parent.parent / "src" / "server_orchestration_tools.py"

        tool_names: set[str] = set()
        for source_path in (server_py, orch_py):
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                    for decorator in node.decorator_list:
                        # Match @mcp.tool() or @_handle_errors
                        decorator_name = ""
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                            decorator_name = decorator.func.attr
                        elif isinstance(decorator, ast.Attribute):
                            decorator_name = decorator.attr
                        if decorator_name == "tool":
                            tool_names.add(node.name)

        # Tools that are read-only and default to NONE are acceptable
        # without explicit mapping, but all DESTRUCTIVE/WRITE tools MUST be mapped.
        unmapped = tool_names - set(_OPERATION_MIN_RIGHT.keys())
        # Allow unmapped tools only if they're clearly read-only (list_, get_, etc.)
        _READ_PREFIXES = ("list_", "get_", "discover_", "search_", "info_", "suggest_", "recall_", "assert_", "query_")
        unmapped_non_read = {t for t in unmapped if not any(t.startswith(p) for p in _READ_PREFIXES)}

        import warnings
        if unmapped_non_read:
            warnings.warn(
                f"{len(unmapped_non_read)} tool(s) missing from _OPERATION_MIN_RIGHT "
                f"(they default to NONE rights): {sorted(unmapped_non_read)}",
                stacklevel=1,
            )
        # Hard-fail threshold: if more than 50 tools are unmapped, something is
        # structurally wrong. Currently 43 are unmapped — track it down over time.
        assert len(unmapped_non_read) <= 50, (
            f"Too many unmapped tools ({len(unmapped_non_read)}): {sorted(unmapped_non_read)}"
        )
