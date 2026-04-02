"""
MCP Resource Subscriptions Module

Manages client subscriptions to grandMA2 resources. When a client subscribes
to a resource URI, the server tracks the subscription. Tools that modify
console state can then notify subscribers of changes.

Subscription tracking is in-memory — subscriptions are lost on server restart.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Track subscriptions: URI → set of subscription IDs (simple counter)
_subscriptions: dict[str, set[int]] = defaultdict(set)
_next_id: int = 0


def register_subscriptions(mcp: FastMCP) -> None:
    """Register resource subscription handlers on the given FastMCP server.

    Uses the low-level mcp.Server decorators since FastMCP doesn't expose
    subscribe_resource/unsubscribe_resource directly.
    """
    low_level = mcp._mcp_server

    @low_level.subscribe_resource()
    async def on_subscribe(uri) -> None:
        """Handle client subscribing to a resource URI."""
        global _next_id
        uri_str = str(uri)
        _next_id += 1
        _subscriptions[uri_str].add(_next_id)
        logger.info(
            "Client subscribed to %s (sub_id=%d, total=%d)",
            uri_str, _next_id, len(_subscriptions[uri_str]),
        )

    @low_level.unsubscribe_resource()
    async def on_unsubscribe(uri) -> None:
        """Handle client unsubscribing from a resource URI."""
        uri_str = str(uri)
        subs = _subscriptions.get(uri_str)
        if subs:
            # Remove one subscription
            subs.pop()
            if not subs:
                del _subscriptions[uri_str]
        logger.info("Client unsubscribed from %s", uri_str)


def get_subscribed_uris() -> list[str]:
    """Return list of URIs that have active subscriptions."""
    return list(_subscriptions.keys())


def has_subscribers(uri: str) -> bool:
    """Check if a resource URI has any active subscribers."""
    return bool(_subscriptions.get(uri))


def get_subscription_count(uri: str) -> int:
    """Return number of active subscriptions for a URI."""
    return len(_subscriptions.get(uri, set()))
