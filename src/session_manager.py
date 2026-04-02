"""
Per-Operator Telnet Session Manager

Pools GMA2TelnetClient connections keyed by operator identity. In stub mode
(no IdP), the identity is derived from GMA_USER or the effective scope tier.
When a real OAuth Authorization Server is integrated, the identity is the
JWT ``sub`` claim.

Each session authenticates with a console user whose rights level matches or
is more restrictive than the operator's OAuth scope tier, implementing the
dual-enforcement defense-in-depth described in the architecture document:

    Effective Permissions = OAuth Scopes ∩ ABAC Policy ∩ Console Native Rights

The intersection means no single layer can unilaterally escalate privileges.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field

from .telnet_client import GMA2TelnetClient

logger = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class OperatorSession:
    """A live Telnet session for one operator identity."""

    identity: str                  # OAuth subject or scope-tier key
    username: str                  # Console username used to authenticate
    client: GMA2TelnetClient
    created_at: float = field(default_factory=time.monotonic)
    last_used: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        self.last_used = time.monotonic()

    def idle_seconds(self) -> float:
        return time.monotonic() - self.last_used


# ── Session manager ───────────────────────────────────────────────────────────


class SessionManager:
    """
    Pool of per-operator Telnet sessions.

    Session lifecycle
    -----------------
    * Created on first ``get()`` for a given identity.
    * Cached until ``idle_timeout`` seconds of inactivity or explicit
      ``release()``.
    * Auto-reconnected (same credentials) if the Telnet connection drops.
    * Oldest session evicted when the pool reaches ``max_sessions``.
    * ``start_keepalive()`` launches a background task that pings sessions
      and evicts expired ones at ``keepalive_interval``-second intervals.
    """

    def __init__(
        self,
        host: str,
        port: int,
        max_sessions: int = 16,
        idle_timeout: float = 3600.0,
        keepalive_interval: float = 30.0,
    ) -> None:
        self._host = host
        self._port = port
        self._max_sessions = max_sessions
        self._idle_timeout = idle_timeout
        self._keepalive_interval = keepalive_interval
        self._sessions: dict[str, OperatorSession] = {}
        self._lock = asyncio.Lock()
        self._keepalive_task: asyncio.Task | None = None

    # ── Public API ───────────────────────────────────────────────────────────

    async def get(
        self,
        identity: str,
        username: str,
        password: str,
    ) -> GMA2TelnetClient:
        """
        Return a live Telnet client for *identity*.

        Creates a new session if none exists; reconnects with the same
        credentials if the Telnet connection dropped.
        """
        async with self._lock:
            session = self._sessions.get(identity)

            if session is not None:
                session.touch()
                if not session.client.is_connected:
                    logger.warning(
                        "Session for %r (console user %r) lost connection — reconnecting",
                        identity,
                        session.username,
                    )
                    await self._reconnect(session, username, password)
                return session.client

            # Pool full — evict the least-recently-used session
            if len(self._sessions) >= self._max_sessions:
                await self._evict_oldest()

            client = await self._create_client(username, password)
            self._sessions[identity] = OperatorSession(
                identity=identity,
                username=username,
                client=client,
            )
            logger.info(
                "Created session for operator %r as console user %r",
                identity,
                username,
            )
            return client

    async def release(self, identity: str) -> None:
        """Disconnect and remove the session for *identity*."""
        async with self._lock:
            session = self._sessions.pop(identity, None)
        if session is not None:
            await _safe_disconnect(session.client)
            logger.info("Released session for %r", identity)

    async def cleanup_expired(self) -> int:
        """
        Disconnect sessions idle longer than ``idle_timeout``.

        Returns the number of sessions removed.
        """
        async with self._lock:
            expired = [
                ident
                for ident, sess in self._sessions.items()
                if sess.idle_seconds() > self._idle_timeout
            ]
            removed = []
            for ident in expired:
                removed.append(self._sessions.pop(ident))

        for session in removed:
            await _safe_disconnect(session.client)

        if removed:
            logger.info("Expired %d idle Telnet session(s)", len(removed))
        return len(removed)

    async def close_all(self) -> None:
        """Disconnect all sessions. Called on server shutdown."""
        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            self._keepalive_task = None

        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()

        for session in sessions:
            await _safe_disconnect(session.client)
        logger.info("All Telnet sessions closed")

    def start_keepalive(self) -> None:
        """Start the background keepalive / expiry task."""
        if self._keepalive_task is None or self._keepalive_task.done():
            self._keepalive_task = asyncio.create_task(
                self._keepalive_loop(), name="session-keepalive"
            )

    # ── Introspection ────────────────────────────────────────────────────────

    def session_count(self) -> int:
        """Number of currently open sessions."""
        return len(self._sessions)

    def session_info(self) -> list[dict]:
        """Snapshot of active sessions for diagnostics / admin tools."""
        return [
            {
                "identity": s.identity,
                "username": s.username,
                "connected": s.client.is_connected,
                "idle_seconds": round(s.idle_seconds(), 1),
                "age_seconds": round(time.monotonic() - s.created_at, 1),
            }
            for s in self._sessions.values()
        ]

    # ── Private helpers ──────────────────────────────────────────────────────

    async def _create_client(self, username: str, password: str) -> GMA2TelnetClient:
        client = GMA2TelnetClient(
            host=self._host,
            port=self._port,
            user=username,
            password=password,
        )
        await client.connect()
        await client.login()
        return client

    async def _reconnect(
        self,
        session: OperatorSession,
        username: str,
        password: str,
    ) -> None:
        await _safe_disconnect(session.client)
        session.client = await self._create_client(username, password)
        session.username = username
        session.touch()

    async def _evict_oldest(self) -> None:
        oldest_key = min(self._sessions, key=lambda k: self._sessions[k].last_used)
        session = self._sessions.pop(oldest_key)
        await _safe_disconnect(session.client)
        logger.warning("Session pool full — evicted LRU session for %r", oldest_key)

    async def _keepalive_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._keepalive_interval)
                await self.cleanup_expired()
                # Send a no-op to each connected session to keep TCP alive
                async with self._lock:
                    sessions = list(self._sessions.values())
                for session in sessions:
                    if session.client.is_connected:
                        with contextlib.suppress(Exception):
                            # Empty-string send keeps the socket alive without
                            # any console side-effects; will reconnect on next get()
                            await session.client.send_command("")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Keepalive loop error: %s", exc)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _safe_disconnect(client: GMA2TelnetClient) -> None:
    with contextlib.suppress(Exception):
        await client.disconnect()
