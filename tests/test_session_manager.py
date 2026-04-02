"""
Session Manager Tests

Tests for src/session_manager.py and src/credentials.py.
All Telnet calls are mocked — no live console required.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from src.session_manager import OperatorSession, SessionManager, _safe_disconnect

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_mock_client(connected: bool = True) -> MagicMock:
    """Return a mock GMA2TelnetClient with is_connected defaulting to True."""
    client = MagicMock()
    type(client).is_connected = PropertyMock(return_value=connected)
    client.connect = AsyncMock()
    client.login = AsyncMock()
    client.disconnect = AsyncMock()
    client.send_command = AsyncMock()
    return client


def _make_manager(**kwargs) -> SessionManager:
    return SessionManager(host="127.0.0.1", port=30000, **kwargs)


# ── OperatorSession ───────────────────────────────────────────────────────────


class TestOperatorSession:

    def test_touch_updates_last_used(self):
        client = _make_mock_client()
        session = OperatorSession(identity="test", username="operator", client=client)
        t0 = session.last_used
        time.sleep(0.05)
        session.touch()
        assert session.last_used > t0

    def test_idle_seconds_increases_over_time(self):
        client = _make_mock_client()
        session = OperatorSession(identity="test", username="operator", client=client)
        time.sleep(0.05)
        assert session.idle_seconds() >= 0.04


# ── SessionManager.get ────────────────────────────────────────────────────────


class TestSessionManagerGet:

    @pytest.mark.asyncio
    async def test_creates_new_session(self):
        manager = _make_manager()
        mock_client = _make_mock_client()

        with patch("src.session_manager.GMA2TelnetClient", return_value=mock_client):
            client = await manager.get("operator_1", "operator", "pw")

        assert client is mock_client
        mock_client.connect.assert_awaited_once()
        mock_client.login.assert_awaited_once()
        assert manager.session_count() == 1

    @pytest.mark.asyncio
    async def test_returns_cached_session(self):
        manager = _make_manager()
        mock_client = _make_mock_client()

        with patch("src.session_manager.GMA2TelnetClient", return_value=mock_client):
            c1 = await manager.get("operator_1", "operator", "pw")
            c2 = await manager.get("operator_1", "operator", "pw")

        assert c1 is c2
        assert mock_client.connect.await_count == 1  # only created once

    @pytest.mark.asyncio
    async def test_different_identities_get_different_sessions(self):
        manager = _make_manager()
        client_a = _make_mock_client()
        client_b = _make_mock_client()

        with patch("src.session_manager.GMA2TelnetClient", side_effect=[client_a, client_b]):
            ca = await manager.get("alice", "programmer", "pw")
            cb = await manager.get("bob", "operator", "pw")

        assert ca is client_a
        assert cb is client_b
        assert manager.session_count() == 2

    @pytest.mark.asyncio
    async def test_reconnects_dropped_connection(self):
        manager = _make_manager()
        # First call: connected; second call: disconnected
        connected_client = _make_mock_client(connected=True)
        reconnected_client = _make_mock_client(connected=True)

        with patch("src.session_manager.GMA2TelnetClient", side_effect=[connected_client, reconnected_client]):
            await manager.get("user", "operator", "pw")

        # Simulate connection drop
        type(connected_client).is_connected = PropertyMock(return_value=False)

        with patch("src.session_manager.GMA2TelnetClient", return_value=reconnected_client):
            client = await manager.get("user", "operator", "pw")

        assert client is reconnected_client

    @pytest.mark.asyncio
    async def test_evicts_oldest_when_pool_full(self):
        manager = _make_manager(max_sessions=2)

        clients = [_make_mock_client() for _ in range(3)]

        with patch("src.session_manager.GMA2TelnetClient", side_effect=clients):
            await manager.get("alice", "operator", "pw")
            await asyncio.sleep(0.01)   # ensure different last_used
            await manager.get("bob", "operator", "pw")
            await asyncio.sleep(0.01)
            await manager.get("carol", "operator", "pw")

        # Pool capped at max_sessions=2
        assert manager.session_count() == 2
        # Alice (oldest) was evicted
        identities = {s["identity"] for s in manager.session_info()}
        assert "alice" not in identities
        assert "bob" in identities or "carol" in identities


# ── SessionManager.release ────────────────────────────────────────────────────


class TestSessionManagerRelease:

    @pytest.mark.asyncio
    async def test_release_disconnects_and_removes(self):
        manager = _make_manager()
        mock_client = _make_mock_client()

        with patch("src.session_manager.GMA2TelnetClient", return_value=mock_client):
            await manager.get("user", "operator", "pw")

        assert manager.session_count() == 1
        await manager.release("user")
        mock_client.disconnect.assert_awaited_once()
        assert manager.session_count() == 0

    @pytest.mark.asyncio
    async def test_release_nonexistent_is_noop(self):
        manager = _make_manager()
        await manager.release("nonexistent")  # should not raise


# ── SessionManager.cleanup_expired ───────────────────────────────────────────


class TestSessionManagerCleanup:

    @pytest.mark.asyncio
    async def test_removes_idle_sessions(self):
        manager = _make_manager(idle_timeout=0.05)
        mock_client = _make_mock_client()

        with patch("src.session_manager.GMA2TelnetClient", return_value=mock_client):
            await manager.get("user", "operator", "pw")

        await asyncio.sleep(0.1)
        removed = await manager.cleanup_expired()
        assert removed == 1
        assert manager.session_count() == 0

    @pytest.mark.asyncio
    async def test_keeps_active_sessions(self):
        manager = _make_manager(idle_timeout=60.0)
        mock_client = _make_mock_client()

        with patch("src.session_manager.GMA2TelnetClient", return_value=mock_client):
            await manager.get("user", "operator", "pw")

        removed = await manager.cleanup_expired()
        assert removed == 0
        assert manager.session_count() == 1


# ── SessionManager.close_all ─────────────────────────────────────────────────


class TestSessionManagerCloseAll:

    @pytest.mark.asyncio
    async def test_close_all_disconnects_all(self):
        manager = _make_manager()
        clients = [_make_mock_client(), _make_mock_client()]

        with patch("src.session_manager.GMA2TelnetClient", side_effect=clients):
            await manager.get("alice", "operator", "pw")
            await manager.get("bob", "programmer", "pw")

        await manager.close_all()

        assert manager.session_count() == 0
        for c in clients:
            c.disconnect.assert_awaited()


# ── SessionManager.session_info ──────────────────────────────────────────────


class TestSessionManagerInfo:

    @pytest.mark.asyncio
    async def test_session_info_format(self):
        manager = _make_manager()
        mock_client = _make_mock_client()

        with patch("src.session_manager.GMA2TelnetClient", return_value=mock_client):
            await manager.get("alice", "programmer", "pw")

        info = manager.session_info()
        assert len(info) == 1
        assert info[0]["identity"] == "alice"
        assert info[0]["username"] == "programmer"
        assert info[0]["connected"] is True
        assert "idle_seconds" in info[0]
        assert "age_seconds" in info[0]


# ── _safe_disconnect ──────────────────────────────────────────────────────────


class TestSafeDisconnect:

    @pytest.mark.asyncio
    async def test_does_not_raise_on_error(self):
        client = MagicMock()
        client.disconnect = AsyncMock(side_effect=Exception("already closed"))
        await _safe_disconnect(client)  # should not raise

    @pytest.mark.asyncio
    async def test_calls_disconnect(self):
        client = MagicMock()
        client.disconnect = AsyncMock()
        await _safe_disconnect(client)
        client.disconnect.assert_awaited_once()


# ── Credential resolver ───────────────────────────────────────────────────────


class TestResolveConsoleCredentials:

    def test_gma_user_env_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("GMA_USER", "myuser")
        monkeypatch.setenv("GMA_PASSWORD", "mypass")
        from src.credentials import resolve_console_credentials
        user, pw = resolve_console_credentials({"gma2:discover"})
        assert user == "myuser"
        assert pw == "mypass"

    def test_tier0_scopes_resolve_to_guest(self, monkeypatch):
        monkeypatch.delenv("GMA_USER", raising=False)
        from src.credentials import resolve_console_credentials
        user, pw = resolve_console_credentials({"gma2:discover", "gma2:state:read"})
        assert user == "guest"

    def test_tier1_scopes_resolve_to_operator(self, monkeypatch):
        monkeypatch.delenv("GMA_USER", raising=False)
        from src.credentials import resolve_console_credentials
        user, pw = resolve_console_credentials({"gma2:discover", "gma2:playback:go"})
        assert user == "operator"

    def test_tier3_scopes_resolve_to_programmer(self, monkeypatch):
        monkeypatch.delenv("GMA_USER", raising=False)
        from src.credentials import resolve_console_credentials
        user, pw = resolve_console_credentials({"gma2:discover", "gma2:cue:store"})
        assert user == "programmer"

    def test_tier5_scopes_resolve_to_administrator(self, monkeypatch):
        monkeypatch.delenv("GMA_USER", raising=False)
        from src.credentials import resolve_console_credentials
        user, pw = resolve_console_credentials({"gma2:user:manage"})
        assert user == "administrator"

    def test_env_var_overrides_default_username(self, monkeypatch):
        monkeypatch.delenv("GMA_USER", raising=False)
        monkeypatch.setenv("GMA_OPERATOR_USER", "custom_op")
        from src.credentials import resolve_console_credentials
        user, _ = resolve_console_credentials({"gma2:playback:go"})
        assert user == "custom_op"

    def test_empty_scopes_resolve_to_guest(self, monkeypatch):
        monkeypatch.delenv("GMA_USER", raising=False)
        from src.credentials import resolve_console_credentials
        user, _ = resolve_console_credentials(set())
        assert user == "guest"


# ── Operator identity ─────────────────────────────────────────────────────────


class TestGetOperatorIdentity:

    def test_gma_user_env_is_identity_when_set(self, monkeypatch):
        monkeypatch.setenv("GMA_USER", "alice")
        from src.credentials import get_operator_identity
        assert get_operator_identity(set()) == "alice"

    def test_tier_key_when_gma_user_unset(self, monkeypatch):
        monkeypatch.delenv("GMA_USER", raising=False)
        from src.credentials import get_operator_identity
        identity = get_operator_identity({"gma2:discover", "gma2:state:read"})
        assert identity == "tier:0"

    def test_tier3_key(self, monkeypatch):
        monkeypatch.delenv("GMA_USER", raising=False)
        from src.credentials import get_operator_identity
        identity = get_operator_identity({"gma2:cue:store"})
        assert identity == "tier:3"

    def test_tier5_key(self, monkeypatch):
        monkeypatch.delenv("GMA_USER", raising=False)
        from src.credentials import get_operator_identity
        identity = get_operator_identity({"gma2:user:manage"})
        assert identity == "tier:5"
