"""Plugin inventory — cached lookup over ``browse_plugin_library()``.

Mostly pure: the parser is fully pure; the :class:`PluginInventory` class
holds a short-lived cache and reaches out via :func:`src.tools.get_client`
for live fetches. Live fetches use the real Telnet client (or mock client
under ``GMA_MOCK``) transparently.

Public API:
    parse_plugin_listing(raw) -> list[PluginRecord]
    PluginInventory().lookup(plugin_name, *, use_cache, cache_ttl) -> PluginAvailability
    _default_inventory() -> PluginInventory   (process-global singleton)
"""

from __future__ import annotations

import datetime
import re
import time
from typing import TypedDict

# Matches ``Plugin <page> <pool_id> <name> [ExecuteOnLoad] [Info]`` lines.
#
# The MA2 plugin list is column-aligned; names may contain spaces
# (e.g. "Ecube Color Picker"), so the name field is delimited by the column
# boundary (2+ consecutive whitespace) rather than by a single space.
_PLUGIN_LINE_RE = re.compile(
    r"^\s*Plugin\s+\d+\s+(?P<pool_id>\d+)\s{2,}(?P<name>.+?)\s{2,}",
    re.MULTILINE,
)


class PluginRecord(TypedDict):
    pool_id: int
    name: str


class PluginAvailability(TypedDict):
    plugin_name: str        # echoed
    available: bool
    pool_id: int | None
    match: str              # "exact" | "substring" | "miss"
    last_checked_at: str    # ISO 8601
    source: str             # "cache" | "live_query"


def parse_plugin_listing(raw: str) -> list[PluginRecord]:
    """Parse ``list plugin`` output. Pure — no I/O."""
    records: list[PluginRecord] = []
    for match in _PLUGIN_LINE_RE.finditer(raw):
        try:
            records.append({
                "pool_id": int(match.group("pool_id")),
                "name": match.group("name"),
            })
        except (ValueError, KeyError):
            continue
    return records


class PluginInventory:
    """Cached plugin-presence lookup against the live console."""

    def __init__(self) -> None:
        self._records: list[PluginRecord] = []
        self._observed_at: float = 0.0

    async def _fetch_records(self) -> list[PluginRecord]:
        """Live fetch via Telnet — replaceable in tests.

        Uses ``src.server.get_client()`` (the async accessor that bootstraps
        the SessionManager) rather than ``src.tools.get_client`` (a sync
        global that requires prior initialisation).
        """
        from src.server import get_client
        client = await get_client()
        resp = await client.send_command_with_response("list plugin", timeout=3.0)
        return parse_plugin_listing(resp)

    def _is_fresh(self, cache_ttl: int) -> bool:
        return (time.time() - self._observed_at) < cache_ttl

    async def lookup(
        self,
        plugin_name: str,
        *,
        use_cache: bool = True,
        cache_ttl: int = 60,
    ) -> PluginAvailability:
        """Return availability info for ``plugin_name``.

        Match precedence: exact (case-insensitive) → substring (case-insensitive)
        → miss. On cache miss / stale / ``use_cache=False``, performs a live
        fetch and refreshes the cache before searching.
        """
        if not use_cache or not self._is_fresh(cache_ttl):
            self._records = await self._fetch_records()
            self._observed_at = time.time()
            source: str = "live_query"
        else:
            source = "cache"

        def _normalise(text: str) -> str:
            """Lowercase + strip all whitespace.

            MA2 plugins are stored with display names containing spaces
            (e.g. "Ecube Color Picker") while the underlying file and the
            human shorthand are space-free ("EcubeColorPicker"). Both should
            match — strip whitespace from both sides of every comparison.
            """
            return "".join(text.split()).lower()

        wanted_norm = _normalise(plugin_name)
        found: PluginRecord | None = None
        match_type = "miss"

        for record in self._records:
            if _normalise(record["name"]) == wanted_norm:
                found = record
                match_type = "exact"
                break
        if found is None:
            for record in self._records:
                if wanted_norm in _normalise(record["name"]):
                    found = record
                    match_type = "substring"
                    break

        iso_now = datetime.datetime.now(datetime.UTC).isoformat()

        return {
            "plugin_name": plugin_name,
            "available": found is not None,
            "pool_id": found["pool_id"] if found else None,
            "match": match_type,
            "last_checked_at": iso_now,
            "source": source,
        }


_DEFAULT_INVENTORY: PluginInventory | None = None


def _default_inventory() -> PluginInventory:
    """Return the process-global singleton inventory."""
    global _DEFAULT_INVENTORY
    if _DEFAULT_INVENTORY is None:
        _DEFAULT_INVENTORY = PluginInventory()
    return _DEFAULT_INVENTORY


__all__ = [
    "parse_plugin_listing",
    "PluginInventory",
    "PluginAvailability",
    "PluginRecord",
    "_default_inventory",
]
