"""Credentials passed to tools never reach the telemetry log (or the activity resource)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.telemetry import ToolTelemetry, redact_inputs, redact_text


def test_redact_text_masks_credential_values():
    text = 'Login "op" "s3cret"'
    assert redact_text(text, {"user": "op", "password": "s3cret"}) == 'Login "op" "***"'


def test_redact_text_masks_json_escaped_values_and_longest_first():
    text = json.dumps({"command_sent": 'Login "op" "pa\\ss"', "note": "token abc123"})
    out = redact_text(text, {"password": "pa\\ss", "api_key": "abc", "token": "abc123", "client_secret": ""})
    assert "pa" not in out
    assert "abc" not in out and "123" not in out  # abc123 masked whole, not as ***123
    assert out.count("***") == 2  # the empty secret is ignored


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


@pytest.mark.asyncio
async def test_password_echoed_in_the_reply_is_not_recorded(tmp_path, monkeypatch):
    from src.server import _handle_errors

    monkeypatch.setenv("GMA_TELEMETRY", "1")
    telemetry = ToolTelemetry(db_path=tmp_path / "t.db")

    @_handle_errors
    async def login(user: str, password: str) -> str:
        return json.dumps({"command_sent": f'Login "{user}" "{password}"'})

    try:
        with patch("src.server._get_telemetry", return_value=telemetry):
            reply = await login(user="op", password="s3cret")

        assert "s3cret" in reply  # the caller's reply is untouched
        rows = telemetry._conn.execute("SELECT inputs_json, output_preview FROM tool_invocations").fetchall()
        assert len(rows) == 1
        inputs_json, output_preview = rows[0]
        assert "s3cret" not in inputs_json
        assert "s3cret" not in output_preview
        assert "***" in output_preview
    finally:
        telemetry.close()
