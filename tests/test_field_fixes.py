"""
Regressions from the AvoidRafa show build (2026-10): chained-command safety,
line length, reply size, pop-ups, connection lock, batch execution,
disconnect/park, save_show, sequence properties.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.vocab import RiskTier, build_v39_spec, classify_command, split_command_chain

SPEC = build_v39_spec()


# --- chained commands: every part is classified ---


class TestClassifyCommand:
    def test_split_respects_quotes(self):
        assert split_command_chain('Label Group 1 "a;b" ; Go') == ['Label Group 1 "a;b"', "Go"]

    def test_destructive_hidden_behind_safe_prefix(self):
        result = classify_command("ClearAll ; Store Group 5", SPEC)
        assert result.risk == RiskTier.DESTRUCTIVE
        assert result.part.startswith("Store")

    def test_highest_tier_wins(self):
        assert classify_command("List Cue ; Go Executor 1.1", SPEC).risk == RiskTier.SAFE_WRITE
        assert classify_command("List Cue", SPEC).risk == RiskTier.SAFE_READ

    def test_quoted_semicolon_does_not_split(self):
        assert classify_command('List Group "x;Delete"', SPEC).risk == RiskTier.SAFE_READ

    @pytest.mark.parametrize("answer", ["1", "2", " 1 "])
    def test_bare_number_is_destructive(self, answer):
        """A bare number can answer an open console pop-up (e.g. confirm an overwrite)."""
        result = classify_command(answer, SPEC)
        assert result.risk == RiskTier.DESTRUCTIVE
        assert "pop-up" in result.reason


class TestSendRawCommandGates:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_chained_store_blocked_without_confirm(self, mock_get_client):
        from src.server import send_raw_command

        data = json.loads(await send_raw_command(command="ClearAll ; Store Group 5"))
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"
        mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_overlong_command_rejected(self, mock_get_client):
        from src.server import send_raw_command

        data = json.loads(await send_raw_command(command="List " + "x" * 1100))
        assert data["blocked"] is True
        assert "1023" in data["error"]
        mock_get_client.assert_not_called()


# --- reply hygiene: ANSI stripped, size capped, pop-ups flagged, list replies scanned ---


class TestReplyHygiene:
    def test_ansi_stripped_from_raw_response(self):
        from src.console_feedback import annotate_tool_result

        out, _ = annotate_tool_result(json.dumps({"raw_response": "\x1b[32mGroup 1\x1b[0m"}))
        assert json.loads(out)["raw_response"] == "Group 1"

    def test_oversized_reply_is_capped(self, monkeypatch):
        from src.console_feedback import annotate_tool_result

        monkeypatch.setenv("GMA_MAX_REPLY_CHARS", "1000")
        out, _ = annotate_tool_result(json.dumps({"raw_response": "row\n" * 5000}))
        data = json.loads(out)
        assert len(data["raw_response"]) <= 1100
        assert data["raw_response_truncated"] is True
        assert data["raw_response_chars"] == 20000

    def test_popup_is_reported_as_pending(self):
        from src.console_feedback import annotate_tool_result

        raw = "Patch Collision! Fixture 5 overlaps.\r\n[1]: Ok   2 : Cancel"
        out, _ = annotate_tool_result(json.dumps({"command_sent": "x", "raw_response": raw}))
        data = json.loads(out)
        assert data["ok"] is False
        assert data["pending_popup"]["options"]
        assert "answer_console_popup" in data["error"]

    def test_raw_responses_list_is_scanned(self):
        from src.console_feedback import annotate_tool_result

        out, _ = annotate_tool_result(json.dumps({
            "commands_sent": ["assign dmx 1.001 at fixture 1"],
            "raw_responses": ["[Channel]>", "Error #72 COMMAND NOT EXECUTED"],
        }))
        assert json.loads(out)["ok"] is False


# --- one command at a time per connection ---


class TestConnectionLock:
    @pytest.mark.asyncio
    async def test_concurrent_commands_do_not_interleave(self):
        from src.telnet_client import GMA2TelnetClient

        client = GMA2TelnetClient(host="127.0.0.1")
        active = 0
        peak = 0

        async def fake_read(n):
            await asyncio.sleep(0.01)
            raise TimeoutError

        client._reader = MagicMock()
        client._reader.read = AsyncMock(side_effect=fake_read)
        client._reader.at_eof = MagicMock(return_value=False)
        client._writer = MagicMock()
        client._writer.is_closing = MagicMock(return_value=False)
        client._connection = True

        original = client._exchange

        async def tracking_exchange(*a, **kw):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                return await original(*a, **kw)
            finally:
                active -= 1

        client._exchange = tracking_exchange
        await asyncio.gather(*[
            client.send_command_with_response(f"list cue {i}", timeout=0.01, delay=0, subsequent_timeout=0.01)
            for i in range(5)
        ])
        assert peak == 1

    @pytest.mark.asyncio
    async def test_exclusive_is_reentrant_for_the_owner(self):
        from src.telnet_client import GMA2TelnetClient

        client = GMA2TelnetClient(host="127.0.0.1")
        async with client.exclusive(), client.exclusive():
            pass  # must not deadlock


# --- reply framing: stale output from earlier commands is dropped ---


class TestReplyFraming:
    def test_frame_reply_starts_at_echo_of_sent_command(self):
        from src.telnet_client import frame_reply

        raw = "Store Sequence 136 Cue 124\r\n[Channel]>List Timecode\r\nTC 1 Show\r\n[Channel]>"
        assert frame_reply(raw, "List Timecode") == "List Timecode\r\nTC 1 Show\r\n[Channel]>"

    def test_frame_reply_without_echo_is_unchanged(self):
        from src.telnet_client import frame_reply

        assert frame_reply("TC 1 Show\r\n[Channel]>", "List Timecode") == "TC 1 Show\r\n[Channel]>"


# --- batch execution ---


class TestRunCommandBatch:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_batch_blocks_destructive_without_confirm(self, mock_get_client):
        from src.server import run_command_batch

        data = json.loads(await run_command_batch(commands=["List Cue", "Store Group 5"]))
        assert data["blocked"] is True
        assert data["destructive_lines"] == [2]
        mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_batch_runs_in_order_and_stops_on_error(self, mock_get_client):
        from src.server import run_command_batch

        replies = {
            "Fixture 1": "Fixture 1\r\n[Channel]>",
            "Bogus": "Bogus\r\nError #1: UNKNOWN COMMAND\r\n[Channel]>",
            "At 100": "At 100\r\n[Channel]>",
        }
        client = MagicMock()
        client.exclusive = MagicMock(return_value=_NullAsyncCtx())
        client.send_command_with_response = AsyncMock(side_effect=lambda cmd, **kw: replies[cmd])
        mock_get_client.return_value = client

        data = json.loads(await run_command_batch(commands=["Fixture 1", "Bogus", "At 100"]))
        assert data["executed"] == 2
        assert data["failed"][0]["line"] == 2
        assert data["stopped_early"] is True
        assert data["ok"] is False

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_batch_from_file_skips_comments(self, mock_get_client, tmp_path):
        from src.server import run_command_batch

        f = tmp_path / "cmds.txt"
        f.write_text("# header\nList Cue\n\nList Group\n", encoding="utf-8")
        client = MagicMock()
        client.exclusive = MagicMock(return_value=_NullAsyncCtx())
        client.send_command_with_response = AsyncMock(return_value="[Channel]>")
        mock_get_client.return_value = client

        data = json.loads(await run_command_batch(commands_file=str(f)))
        assert data["executed"] == 2
        assert data["ok"] is True


class _NullAsyncCtx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


# --- pop-up answers ---


class TestAnswerConsolePopup:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_ok_requires_confirm(self, mock_get_client):
        from src.server import answer_console_popup

        data = json.loads(await answer_console_popup(choice=1))
        assert data["blocked"] is True
        mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_cancel_is_allowed(self, mock_get_client):
        from src.server import answer_console_popup

        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="[Channel]>")
        mock_get_client.return_value = client
        data = json.loads(await answer_console_popup(choice=2, cancel_option=2))
        assert data["command_sent"] == "2"
        assert data["ok"] is True


# --- disconnect / park ---


class TestDisconnectConsole:
    @pytest.mark.asyncio
    async def test_disconnect_releases_session(self):
        import src.server as server

        manager = MagicMock()
        manager.release_all = AsyncMock(return_value=1)
        with patch.object(server, "_get_session_manager", AsyncMock(return_value=manager)):
            data = json.loads(await server.disconnect_console())
        assert data["ok"] is True
        assert data["sessions_closed"] == 1
        manager.release_all.assert_awaited_once()


# --- reconfigure_connection defaults ---


def test_reconfigure_connection_does_not_persist_by_default():
    import inspect

    from src.server import reconfigure_connection

    assert inspect.signature(reconfigure_connection).parameters["persist"].default is False


# --- save_show ---


class TestSaveShow:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_save_as_uses_saveshow_keyword(self, mock_get_client):
        from src.server import save_show

        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="[Channel]>")
        mock_get_client.return_value = client
        data = json.loads(await save_show(show_name="my show"))
        assert data["command_sent"].lower().startswith("saveshow")
