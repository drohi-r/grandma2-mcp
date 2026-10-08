"""Console feedback classification and the uniform ``ok`` contract on tool replies."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.console_feedback import annotate_tool_result, find_console_errors, find_console_warnings


class TestFindConsoleErrors:
    @pytest.mark.parametrize("raw,code,message", [
        ("Error #66 CANNOT ASSIGN", 66, "CANNOT ASSIGN"),
        ("Error #1: UNKNOWN COMMAND\r\n[Channel]>", 1, "UNKNOWN COMMAND"),
        ("\x1b[31mError #72: COMMAND NOT EXECUTED\x1b[0m", 72, "COMMAND NOT EXECUTED"),
        ("ERROR #16 : RESIZE FORBIDDEN", 16, "RESIZE FORBIDDEN"),
    ])
    def test_numbered_errors(self, raw, code, message):
        errors = find_console_errors(raw)
        assert len(errors) == 1
        assert errors[0].code == code
        assert errors[0].message == message

    def test_kinds(self):
        assert find_console_errors("Error #1: UNKNOWN COMMAND")[0].kind == "syntax"
        assert find_console_errors("Error #72 COMMAND NOT EXECUTED")[0].kind == "rejected"
        assert find_console_errors("FILE NOT FOUND")[0].kind == "not_found"

    def test_bare_phrase_without_number(self):
        errors = find_console_errors("ILLEGAL CHARACTER \\")
        assert [(e.code, e.message) for e in errors] == [(None, "ILLEGAL CHARACTER")]

    def test_numbered_error_not_double_counted_by_phrase(self):
        assert len(find_console_errors("Error #66 CANNOT ASSIGN")) == 1

    def test_clean_response_has_no_errors(self):
        assert find_console_errors("Executing : Go Executor 1.1\r\n[Channel]>") == []
        assert find_console_errors("") == []

    def test_lowercase_label_is_not_an_error(self):
        assert find_console_errors('Group 3 "unknown command test"') == []

    def test_echoed_command_is_ignored(self):
        cmd = 'Label Group 3 "CANNOT ASSIGN"'
        assert find_console_errors(f"{cmd}\r\n[Channel]>", command=cmd) == []

    def test_no_objects_found_is_a_warning_not_an_error(self):
        raw = "NO OBJECTS FOUND FOR LIST"
        assert find_console_errors(raw) == []
        assert find_console_warnings(raw) == ["NO OBJECTS FOUND"]


class TestAnnotateToolResult:
    def test_console_error_marks_failure_and_sets_error(self):
        out, errors = annotate_tool_result(json.dumps({
            "command_sent": "Assign Fixture 1 /fixid=99",
            "raw_response": "Error #66 CANNOT ASSIGN",
        }))
        data = json.loads(out)
        assert data["ok"] is False
        assert data["console_errors"][0]["code"] == 66
        assert "CANNOT ASSIGN" in data["error"]
        assert errors

    def test_existing_error_message_is_kept(self):
        out, _ = annotate_tool_result(json.dumps({"raw_response": "Error #1: UNKNOWN COMMAND", "error": "mine"}))
        assert json.loads(out)["error"] == "mine"

    def test_success_gets_ok_true(self):
        out, errors = annotate_tool_result(json.dumps({"command_sent": "go", "raw_response": "[Channel]>"}))
        assert json.loads(out)["ok"] is True
        assert errors == []

    def test_blocked_gets_ok_false(self):
        out, _ = annotate_tool_result(json.dumps({"blocked": True, "error": "needs confirm"}))
        assert json.loads(out)["ok"] is False

    def test_response_key_is_scanned(self):
        out, _ = annotate_tool_result(json.dumps({"response": "Error #72 COMMAND NOT EXECUTED"}))
        assert json.loads(out)["ok"] is False

    def test_tool_supplied_ok_is_respected_without_console_errors(self):
        out, _ = annotate_tool_result(json.dumps({"ok": False, "reason": "custom"}))
        assert json.loads(out) == {"ok": False, "reason": "custom"}

    def test_warning_does_not_fail(self):
        out, _ = annotate_tool_result(json.dumps({"raw_response": "NO OBJECTS FOUND FOR LIST"}))
        data = json.loads(out)
        assert data["ok"] is True
        assert data["console_warnings"] == ["NO OBJECTS FOUND"]

    @pytest.mark.parametrize("raw", ["not json", "[1, 2]", '"text"'])
    def test_non_object_passthrough(self, raw):
        assert annotate_tool_result(raw) == (raw, [])


class TestHandleErrorsIntegration:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_tool_reply_reports_console_rejection(self, mock_get_client):
        from src.server import send_raw_command

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Error #1: UNKNOWN COMMAND\r\n[Channel]>")
        mock_get_client.return_value = mock_client

        data = json.loads(await send_raw_command(command="list foo"))
        assert data["ok"] is False
        assert data["console_errors"][0]["message"] == "UNKNOWN COMMAND"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_tool_reply_ok_on_success(self, mock_get_client):
        from src.server import send_raw_command

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[Channel]>")
        mock_get_client.return_value = mock_client

        assert json.loads(await send_raw_command(command="list cue"))["ok"] is True

    @pytest.mark.asyncio
    async def test_exception_reply_has_ok_false(self):
        from src.server import _handle_errors

        @_handle_errors
        async def boom() -> str:
            raise RuntimeError("nope")

        assert json.loads(await boom())["ok"] is False
