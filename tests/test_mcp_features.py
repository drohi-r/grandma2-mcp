"""MCP protocol features: elicitation for destructive confirms, progress, resource updates."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _ctx(action="accept", confirm=True):
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=SimpleNamespace(action=action, data=SimpleNamespace(confirm=confirm)))
    ctx.report_progress = AsyncMock()
    ctx.session.send_resource_updated = AsyncMock()
    return ctx


def _gated_tool():
    from src.server import _handle_errors

    calls = []

    @_handle_errors
    async def wipe_thing(thing_id: int, confirm_destructive: bool = False) -> str:
        calls.append(confirm_destructive)
        if not confirm_destructive:
            return json.dumps({"blocked": True, "error": "DESTRUCTIVE. Set confirm_destructive=True to proceed."})
        return json.dumps({"command_sent": f"delete thing {thing_id}", "raw_response": "[Channel]>"})

    return wipe_thing, calls


class TestElicitedConfirmation:
    @pytest.mark.asyncio
    async def test_accept_reruns_with_confirmation(self):
        tool, calls = _gated_tool()
        ctx = _ctx("accept", True)
        with patch("src.server.active_context", return_value=ctx), \
             patch("src.mcp_features.client_supports_elicitation", return_value=True):
            data = json.loads(await tool(thing_id=3))
        assert calls == [False, True]
        assert data["ok"] is True
        assert data["confirmed_by"] == "elicitation"
        assert "wipe_thing" in ctx.elicit.await_args.kwargs["message"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action,confirm", [("decline", False), ("accept", False), ("cancel", False)])
    async def test_anything_but_accept_and_tick_stays_blocked(self, action, confirm):
        tool, calls = _gated_tool()
        with patch("src.server.active_context", return_value=_ctx(action, confirm)), \
             patch("src.mcp_features.client_supports_elicitation", return_value=True):
            data = json.loads(await tool(thing_id=3))
        assert calls == [False]
        assert data["blocked"] is True
        assert data["elicitation"] == "declined"

    @pytest.mark.asyncio
    async def test_no_client_support_keeps_old_behaviour(self):
        tool, calls = _gated_tool()
        with patch("src.server.active_context", return_value=_ctx()), \
             patch("src.mcp_features.client_supports_elicitation", return_value=False):
            data = json.loads(await tool(thing_id=3))
        assert calls == [False]
        assert data["blocked"] is True
        assert "elicitation" not in data

    @pytest.mark.asyncio
    async def test_disabled_by_env(self, monkeypatch):
        monkeypatch.setenv("GMA_ELICIT_CONFIRM", "0")
        tool, calls = _gated_tool()
        with patch("src.server.active_context", return_value=_ctx()), \
             patch("src.mcp_features.client_supports_elicitation", return_value=True):
            await tool(thing_id=3)
        assert calls == [False]

    @pytest.mark.asyncio
    async def test_outside_a_request_nothing_is_asked(self):
        tool, calls = _gated_tool()
        with patch("src.server.active_context", return_value=None):
            data = json.loads(await tool(thing_id=3))
        assert calls == [False]
        assert data["blocked"] is True


class TestAgentRunConfirmation:
    @pytest.mark.asyncio
    async def test_run_agent_goal_asks_per_step_when_supported(self, monkeypatch):
        import src.server as server

        seen = {}

        class FakeRuntime:
            def __init__(self, tool_registry):
                pass

            async def run(self, goal, on_confirm=None):
                seen["on_confirm"] = on_confirm
                step = SimpleNamespace(tool_name="store_object", tool_args={"object_id": 1}, description="Store")
                seen["answer"] = await on_confirm(step) if on_confirm else None
                return SimpleNamespace(to_json=lambda: json.dumps({"status": "ok"}))

        monkeypatch.setattr("src.agent.runtime.AgentRuntime", FakeRuntime)
        ctx = _ctx("accept", True)
        with patch("src.server.active_context", return_value=ctx), \
             patch("src.mcp_features.client_supports_elicitation", return_value=True):
            await server.run_agent_goal("store a cue", auto_confirm=False)
        assert seen["on_confirm"] is not None
        assert seen["answer"] is True
        ctx.elicit.assert_awaited_once()


class TestProgressAndActivity:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_batch_reports_progress(self, mock_get_client):
        from src.server import run_command_batch

        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="[Channel]>")
        mock_get_client.return_value = client
        ctx = _ctx()
        with patch("src.server.active_context", return_value=ctx):
            await run_command_batch(commands=["List Cue", "List Group", "List Macro"])
        last = ctx.report_progress.await_args_list[-1].args
        assert last[0] == 3 and last[1] == 3

    @pytest.mark.asyncio
    async def test_changes_notify_activity_subscribers(self):
        from src.mcp_features import ACTIVITY_RESOURCE_URI
        from src.server import _handle_errors

        @_handle_errors
        async def set_thing(value: int) -> str:
            return json.dumps({"command_sent": f"at {value}", "raw_response": "[Channel]>"})

        ctx = _ctx()
        with patch("src.server.active_context", return_value=ctx), \
             patch("src.subscriptions.has_subscribers", return_value=True):
            await set_thing(value=50)
        ctx.session.send_resource_updated.assert_awaited_once()
        assert str(ctx.session.send_resource_updated.await_args.args[0]) == ACTIVITY_RESOURCE_URI

    @pytest.mark.asyncio
    async def test_reads_do_not_notify(self):
        from src.server import _handle_errors

        @_handle_errors
        async def list_things() -> str:
            return json.dumps({"command_sent": "list", "raw_response": "[Channel]>"})

        ctx = _ctx()
        with patch("src.server.active_context", return_value=ctx), \
             patch("src.subscriptions.has_subscribers", return_value=True):
            await list_things()
        ctx.session.send_resource_updated.assert_not_awaited()

    def test_activity_resource_lists_recent_changes(self, tmp_path):
        from src.telemetry import ToolTelemetry

        t = ToolTelemetry(db_path=tmp_path / "t.db")
        t.record_sync(tool_name="list_fixtures", inputs_json="{}", output_preview="", error_class=None,
                      latency_ms=1, risk_tier="SAFE_READ", operator="op", session_id=None)
        t.record_sync(tool_name="store_object", inputs_json='{"object_id": "5"}', output_preview="",
                      error_class=None, latency_ms=1, risk_tier="DESTRUCTIVE", operator="op", session_id=None)
        rows = t.recent_changes(limit=10)
        assert [r["tool_name"] for r in rows] == ["store_object"]
