"""GMA_MOCK env var enables an in-memory SessionManager."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_mock_tier1_canned_listvar():
    from src.mock.session_manager import MockSessionManager
    mgr = MockSessionManager(tier="1")
    client = await mgr.get(identity="t", username="administrator", password="admin")
    resp = await client.send_command_with_response("ListVar")
    # Tier-1 canned response mentions a known system var
    assert "VERSION" in resp or "SHOWFILE" in resp
    await mgr.close_all()


@pytest.mark.asyncio
async def test_mock_tier1_unknown_command_returns_stub():
    from src.mock.session_manager import MockSessionManager
    mgr = MockSessionManager(tier="1")
    client = await mgr.get(identity="t", username="administrator", password="admin")
    resp = await client.send_command_with_response("Quibblefrobble")
    assert "MOCK" in resp.upper() or "STUBBED" in resp.upper()
    await mgr.close_all()


@pytest.mark.asyncio
async def test_mock_tier2_groups_from_fixture():
    from src.mock.session_manager import MockSessionManager
    mgr = MockSessionManager(tier="schema")
    client = await mgr.get(identity="t", username="administrator", password="admin")
    resp = await client.send_command_with_response("list group")
    # Fixture loads 12 groups; response should mention them
    assert "Wash" in resp or "Mover" in resp
    await mgr.close_all()


@pytest.mark.asyncio
async def test_mock_session_manager_implements_close_and_count():
    from src.mock.session_manager import MockSessionManager
    mgr = MockSessionManager(tier="1")
    assert mgr.session_count() == 0
    await mgr.get(identity="a", username="u", password="p")
    await mgr.get(identity="b", username="u", password="p")
    assert mgr.session_count() == 2
    await mgr.release("a")
    assert mgr.session_count() == 1
    await mgr.close_all()
    assert mgr.session_count() == 0


@pytest.mark.asyncio
async def test_server_uses_mock_when_env_set(monkeypatch):
    """_get_session_manager returns MockSessionManager when GMA_MOCK is set."""
    monkeypatch.setenv("GMA_MOCK", "1")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import _get_session_manager
    mgr = await _get_session_manager()
    assert mgr.__class__.__name__ == "MockSessionManager"
    # Cleanup: reset _session_manager so other tests don't see mock state
    import src.server
    src.server._session_manager = None
