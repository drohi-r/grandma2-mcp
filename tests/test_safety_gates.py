"""
Safety-gate regressions: confirmation bypasses, UI request guard, doc count drift.
"""

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parent.parent


# --- system_admin(action="lua") must be gated like run_lua_script ---


class TestSystemAdminLuaGate:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_lua_blocked_without_confirm(self, mock_get_client):
        from src.server import system_admin

        result = await system_admin(action="lua", script='gma.cmd("Delete Sequence 1")')
        data = json.loads(result)

        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"
        mock_get_client.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_lua_runs_with_confirm(self, mock_get_client):
        from src.server import system_admin

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        result = await system_admin(action="lua", script='gma.echo("hi")', confirm_destructive=True)
        data = json.loads(result)

        assert data["risk_tier"] == "DESTRUCTIVE"
        assert data["command_sent"].lower().startswith("lua")
        mock_client.send_command_with_response.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_chat_still_safe_write(self, mock_get_client):
        from src.server import system_admin

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="[channel]>")
        mock_get_client.return_value = mock_client

        data = json.loads(await system_admin(action="chat", message="hello"))
        assert data["risk_tier"] == "SAFE_WRITE"


# --- Web UI request guard (CSRF / DNS rebinding) ---


class TestUIRequestGuard:
    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.delenv("GMA_UI_HOST", raising=False)
        monkeypatch.delenv("GMA_UI_ALLOWED_HOSTS", raising=False)
        monkeypatch.setenv("GMA_UI_PORT", "8092")

    def _guard(self, method, headers):
        from src.ui import _request_guard

        return _request_guard(method, headers)

    def test_same_origin_json_post_allowed(self):
        assert self._guard("POST", {
            "Host": "127.0.0.1:8092",
            "Origin": "http://127.0.0.1:8092",
            "Content-Type": "application/json",
        }) is None

    def test_non_browser_json_post_without_origin_allowed(self):
        assert self._guard("POST", {"Host": "localhost:8092", "Content-Type": "application/json"}) is None

    def test_text_plain_post_rejected(self):
        """A cross-site 'simple request' uses text/plain to dodge CORS preflight."""
        err = self._guard("POST", {"Host": "127.0.0.1:8092", "Content-Type": "text/plain"})
        assert err and "application/json" in err

    def test_cross_origin_post_rejected(self):
        err = self._guard("POST", {
            "Host": "127.0.0.1:8092",
            "Origin": "https://evil.example",
            "Content-Type": "application/json",
        })
        assert err and "origin" in err.lower()

    def test_null_origin_rejected(self):
        err = self._guard("POST", {
            "Host": "127.0.0.1:8092",
            "Origin": "null",
            "Content-Type": "application/json",
        })
        assert err

    def test_dns_rebinding_host_rejected_on_get(self):
        err = self._guard("GET", {"Host": "attacker.example:8092"})
        assert err and "host" in err.lower()

    def test_missing_host_rejected(self):
        assert self._guard("GET", {})

    def test_extra_allowed_host_via_env(self, monkeypatch):
        monkeypatch.setenv("GMA_UI_ALLOWED_HOSTS", "192.168.1.50")
        assert self._guard("GET", {"Host": "192.168.1.50:8092"}) is None

    def test_explicit_bind_host_is_allowed(self, monkeypatch):
        monkeypatch.setenv("GMA_UI_HOST", "10.0.0.7")
        assert self._guard("GET", {"Host": "10.0.0.7:8092"}) is None

    def test_ipv6_loopback_allowed(self):
        assert self._guard("GET", {"Host": "[::1]:8092"}) is None


# --- Documented tool counts must match what the server registers ---


def _registered_tool_count() -> int:
    from src.server import mcp

    return len(mcp._tool_manager._tools)


def test_server_instructions_do_not_hardcode_a_tool_count():
    from src.server import mcp

    assert not re.search(r"\d+\s+tools", mcp.instructions or "")


@pytest.mark.parametrize("relpath", ["README.md", "pyproject.toml", "CLAUDE.md"])
def test_doc_tool_counts_match_registry(relpath):
    # Architecture-table rows give one component's share (server.py, mcp_tools/) — skip them.
    text = "\n".join(
        line for line in (REPO / relpath).read_text(encoding="utf-8").splitlines()
        if "src/server.py" not in line and "src/mcp_tools/" not in line
    )
    claims = {int(n) for n in re.findall(r"\b(\d{3})\s+(?:MCP\s+)?tools\b", text)}
    expected = _registered_tool_count()
    assert claims <= {expected}, f"{relpath} claims {sorted(claims)} tools; registry has {expected}"
