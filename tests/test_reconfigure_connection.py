"""reconfigure_connection — atomic swap + .env persist + verify."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def temp_env_file(tmp_path, monkeypatch):
    """Redirect _ENV_PATH to a temp file with a baseline .env content."""
    env = tmp_path / ".env"
    env.write_text(
        "GMA_HOST=127.0.0.1\nGMA_PORT=30000\nGMA_USER=administrator\n"
        "GMA_PASSWORD=admin\nGMA_TELEMETRY=1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("src.server._ENV_PATH", env)
    return env


@pytest.mark.asyncio
async def test_reconfigure_persists_to_env(temp_env_file, monkeypatch):
    monkeypatch.setattr("src.server._GMA_HOST", "127.0.0.1")
    monkeypatch.setattr("src.server._GMA_PORT", 30000)
    monkeypatch.setattr("src.server._GMA_USER", "administrator")
    monkeypatch.setattr("src.server._session_manager", None)

    with patch("src.server._verify_round_trip", new=AsyncMock(return_value=True)):
        from src.server import reconfigure_connection
        raw = await reconfigure_connection(
            host="10.0.0.5", port=30000, user="administrator",
            password="admin", persist=True, verify=True,
        )
    data = json.loads(raw)
    assert data["success"] is True
    assert data["new_host"] == "10.0.0.5"
    assert data["verified"] is True
    contents = temp_env_file.read_text(encoding="utf-8")
    assert "GMA_HOST=10.0.0.5" in contents
    # Pre-existing entries preserved
    assert "GMA_TELEMETRY=1" in contents


@pytest.mark.asyncio
async def test_reconfigure_idempotent_no_change(temp_env_file, monkeypatch):
    """Calling with the same host returns success without changes."""
    monkeypatch.setattr("src.server._GMA_HOST", "10.0.0.5")
    monkeypatch.setattr("src.server._GMA_PORT", 30000)
    monkeypatch.setattr("src.server._GMA_USER", "administrator")
    monkeypatch.setattr("src.server._session_manager", None)

    with patch("src.server._verify_round_trip", new=AsyncMock(return_value=True)):
        from src.server import reconfigure_connection
        raw = await reconfigure_connection(
            host="10.0.0.5", port=30000, user="administrator",
            password="admin", persist=False, verify=False,
        )
    data = json.loads(raw)
    assert data["success"] is True
    assert data["previous_host"] == data["new_host"] == "10.0.0.5"
    note = (data.get("note") or "").lower()
    assert "no change" in note


@pytest.mark.asyncio
async def test_reconfigure_verify_failure_blocks(temp_env_file, monkeypatch):
    """verify=True + round-trip failure -> success=False, no swap, no persist."""
    monkeypatch.setattr("src.server._GMA_HOST", "127.0.0.1")
    monkeypatch.setattr("src.server._GMA_PORT", 30000)
    monkeypatch.setattr("src.server._GMA_USER", "administrator")
    monkeypatch.setattr("src.server._session_manager", None)

    with patch("src.server._verify_round_trip", new=AsyncMock(return_value=False)):
        from src.server import reconfigure_connection
        raw = await reconfigure_connection(
            host="10.0.0.99", port=30000, user="administrator",
            password="admin", persist=True, verify=True,
        )
    data = json.loads(raw)
    assert data["success"] is False
    assert data["verified"] is False
    # Persist should not have happened
    contents = temp_env_file.read_text(encoding="utf-8")
    assert "GMA_HOST=127.0.0.1" in contents
    assert "GMA_HOST=10.0.0.99" not in contents


@pytest.mark.asyncio
async def test_reconfigure_skip_verify_swaps_immediately(temp_env_file, monkeypatch):
    """verify=False bypasses the round-trip check."""
    monkeypatch.setattr("src.server._GMA_HOST", "127.0.0.1")
    monkeypatch.setattr("src.server._GMA_PORT", 30000)
    monkeypatch.setattr("src.server._GMA_USER", "administrator")
    monkeypatch.setattr("src.server._session_manager", None)
    from src.server import reconfigure_connection
    raw = await reconfigure_connection(
        host="10.0.0.7", port=30000, user="administrator",
        password="admin", persist=False, verify=False,
    )
    data = json.loads(raw)
    assert data["success"] is True
    assert data["new_host"] == "10.0.0.7"
