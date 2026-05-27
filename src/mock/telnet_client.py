"""MockGMA2TelnetClient — implements the public surface of GMA2TelnetClient.

Methods covered: ``connect``, ``login``, ``send_command``, ``send_command_with_response``,
``disconnect``, ``is_connected`` property, and ``__aenter__`` / ``__aexit__``.

Tier 1 uses canned regex responses from :mod:`src.mock.responses`.
Tier 2 (``schema``) reads ``tests/fixtures/mock_show_state.json`` and answers
``list group`` / ``list executor`` / ``list preset`` from the fixture state.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from src.mock.responses import respond

logger = logging.getLogger(__name__)


class MockGMA2TelnetClient:
    """Drop-in mock for :class:`src.telnet_client.GMA2TelnetClient`."""

    DEFAULT_PORT = 30000
    DEFAULT_USER = "administrator"
    DEFAULT_PASSWORD = "admin"

    def __init__(
        self,
        host: str = "mock",
        port: int = DEFAULT_PORT,
        user: str = DEFAULT_USER,
        password: str = DEFAULT_PASSWORD,
        *,
        tier: str = "1",
        fixture_path: Path | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.tier = tier
        self._connected = False
        self._fixture: dict | None = None
        if tier == "schema" and fixture_path is not None and fixture_path.exists():
            try:
                self._fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                logger.warning("failed to load mock fixture %s: %s", fixture_path, e)

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        await asyncio.sleep(0)
        self._connected = True

    async def login(self) -> bool:
        await asyncio.sleep(0)
        return True

    async def send_command(self, command: str, delay: float = 0.0) -> None:
        await asyncio.sleep(0)
        # Strip line breaks per the real client's safety contract.
        _ = command.replace("\r", "").replace("\n", "")

    async def send_command_with_response(
        self,
        command: str,
        timeout: float = 2.0,
        delay: float = 0.0,
        subsequent_timeout: float = 0.10,
    ) -> str:
        await asyncio.sleep(0)
        clean = command.replace("\r", "").replace("\n", "")
        if self.tier == "schema" and self._fixture is not None:
            response = self._from_fixture(clean)
            if response is not None:
                return response
        return respond(clean)

    def _from_fixture(self, command: str) -> str | None:
        cmd = command.strip().lower()
        if not self._fixture:
            return None
        if cmd.startswith("list group"):
            groups = self._fixture.get("groups", [])
            return "Group\n" + "\n".join(
                f"    {g['id']} : {g['name']}" for g in groups
            ) + "\n"
        if cmd.startswith("list executor"):
            execs = self._fixture.get("executors", [])
            return "Executor\n" + "\n".join(
                f"  {e['slot']} : {e['label']} ({e['priority']})" for e in execs
            ) + "\n"
        if cmd.startswith("list preset"):
            presets = self._fixture.get("presets", [])
            return "Preset\n" + "\n".join(
                f"    {p['type']}.{p['id']} : {p['name']}" for p in presets
            ) + "\n"
        if cmd.startswith("list sequence"):
            seqs = self._fixture.get("sequences", [])
            return "Sequence\n" + "\n".join(
                f"    {s['id']} : {s['name']}" for s in seqs
            ) + "\n"
        return None

    async def disconnect(self) -> None:
        self._connected = False

    async def __aenter__(self) -> "MockGMA2TelnetClient":
        await self.connect()
        await self.login()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()


__all__ = ["MockGMA2TelnetClient"]
