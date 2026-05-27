"""MockSessionManager — implements SessionManager's public surface.

Methods: ``get``, ``release``, ``close_all``, ``start_keepalive``, ``session_count``,
``session_info``. Mirrors :class:`src.session_manager.SessionManager` so the
server's ``_get_session_manager()`` injection point can swap it in transparently.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.mock.telnet_client import MockGMA2TelnetClient

logger = logging.getLogger(__name__)

_FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "tests" / "fixtures" / "mock_show_state.json"
)


class MockSessionManager:
    """Drop-in mock for :class:`src.session_manager.SessionManager`."""

    def __init__(self, tier: str = "1") -> None:
        # Accept both "1"/"canned" and "schema"/"replay:<path>" tiers.
        self.tier = tier
        self._clients: dict[str, MockGMA2TelnetClient] = {}

    async def get(
        self, identity: str, username: str, password: str
    ) -> MockGMA2TelnetClient:
        """Return (or create) the mock client for ``identity``."""
        if identity not in self._clients:
            client = MockGMA2TelnetClient(
                host="mock",
                user=username,
                password=password,
                tier=self.tier,
                fixture_path=_FIXTURE_PATH if self.tier == "schema" else None,
            )
            await client.connect()
            await client.login()
            self._clients[identity] = client
        return self._clients[identity]

    async def release(self, identity: str) -> None:
        client = self._clients.pop(identity, None)
        if client is not None:
            await client.disconnect()

    async def close_all(self) -> None:
        for c in list(self._clients.values()):
            await c.disconnect()
        self._clients.clear()

    def start_keepalive(self) -> None:
        """No-op for mock — there is no real connection to keep alive."""

    def session_count(self) -> int:
        return len(self._clients)

    def session_info(self) -> list[dict]:
        return [{"identity": k, "tier": self.tier} for k in self._clients]


__all__ = ["MockSessionManager"]
