"""Credentials passed to tools never reach the telemetry log (or the activity resource)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.telemetry import ToolTelemetry, redact_inputs


def test_redact_inputs_masks_credential_keys():
    out = redact_inputs({"host": "1.2.3.4", "password": "s3cret", "API_TOKEN": "abc"})
    assert out == {"host": "1.2.3.4", "password": "***", "API_TOKEN": "***"}


def test_redact_inputs_does_not_mutate_its_argument():
    original = {"passwd": "x", "client_secret": "y", "api_key": "z", "user": "admin"}
    out = redact_inputs(original)
    assert original["passwd"] == "x"
    assert out == {"passwd": "***", "client_secret": "***", "api_key": "***", "user": "admin"}


@pytest.mark.asyncio
async def test_handle_errors_never_records_the_password(tmp_path, monkeypatch):
    from src.server import _handle_errors

    monkeypatch.setenv("GMA_TELEMETRY", "1")
    telemetry = ToolTelemetry(db_path=tmp_path / "t.db")

    @_handle_errors
    async def connect(host: str, password: str) -> str:
        return json.dumps({"connected": host})

    try:
        with patch("src.server._get_telemetry", return_value=telemetry):
            await connect(host="1.2.3.4", password="s3cret")

        changes = telemetry.recent_changes()
        assert [row["tool_name"] for row in changes] == ["connect"]
        assert "s3cret" not in json.dumps(changes)
        raw = telemetry._conn.execute("SELECT inputs_json FROM tool_invocations").fetchall()
        assert len(raw) == 1
        assert "s3cret" not in raw[0][0]
        assert json.loads(raw[0][0]) == {"host": "1.2.3.4", "password": "***"}
    finally:
        telemetry.close()
