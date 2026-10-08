"""
MCP protocol features used across tools: elicitation, progress, resource updates.

Every helper degrades silently when there is no active request or the client
lacks the capability — tools must behave exactly as before in that case.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Live resource listing recent console-changing tool calls (telemetry-backed).
ACTIVITY_RESOURCE_URI = "ma2://console/activity"


class ConfirmDestructive(BaseModel):
    """Elicitation form: one checkbox."""

    confirm: bool


def active_context(mcp: Any) -> Any | None:
    """The FastMCP Context of the request in progress, or None outside one."""
    try:
        ctx = mcp.get_context()
    except Exception:  # noqa: BLE001
        return None
    return ctx if getattr(ctx, "_request_context", None) is not None else None


def elicitation_enabled() -> bool:
    return os.getenv("GMA_ELICIT_CONFIRM", "1") != "0"


def client_supports_elicitation(ctx: Any) -> bool:
    try:
        from mcp.types import ClientCapabilities, ElicitationCapability

        return bool(ctx.session.check_client_capability(ClientCapabilities(elicitation=ElicitationCapability())))
    except Exception:  # noqa: BLE001
        return False


def needs_destructive_confirmation(result: str) -> bool:
    """True when a tool reply is a block that only asks for confirm_destructive."""
    try:
        data = json.loads(result)
    except (TypeError, ValueError):
        return False
    return (
        isinstance(data, dict)
        and data.get("blocked") is True
        and "confirm_destructive" in str(data.get("error", ""))
    )


def describe_call(tool_name: str, kwargs: dict[str, Any]) -> str:
    args = ", ".join(
        f"{k}={v!r}" for k, v in kwargs.items() if k != "confirm_destructive" and v is not None
    )
    return f"{tool_name}({args[:400]})"


async def ask_destructive_confirmation(ctx: Any, tool_name: str, kwargs: dict[str, Any], reason: str) -> bool | None:
    """Ask the human in the MCP client. None when elicitation is unavailable."""
    if ctx is None or not elicitation_enabled() or not client_supports_elicitation(ctx):
        return None
    message = (
        "A grandMA2 tool wants to make a DESTRUCTIVE change on the console.\n\n"
        f"{describe_call(tool_name, kwargs)}\n\n{reason}\n\nTick confirm and accept to run it."
    )
    try:
        result = await ctx.elicit(message=message, schema=ConfirmDestructive)
    except Exception as exc:  # noqa: BLE001
        logger.info("Elicitation failed for %s: %s", tool_name, exc)
        return None
    accepted = getattr(result, "action", None) == "accept"
    return bool(accepted and getattr(getattr(result, "data", None), "confirm", False))


async def report_progress(ctx: Any, done: float, total: float | None = None, message: str | None = None) -> None:
    if ctx is None:
        return
    try:
        await ctx.report_progress(done, total, message)
    except Exception:  # noqa: BLE001
        logger.debug("Progress notification failed", exc_info=True)


async def notify_resource_updated(ctx: Any, uri: str) -> bool:
    """Tell the requesting client a resource changed (if it subscribed)."""
    from src.subscriptions import has_subscribers

    if ctx is None or not has_subscribers(uri):
        return False
    try:
        from pydantic import AnyUrl

        await ctx.session.send_resource_updated(AnyUrl(uri))
        return True
    except Exception:  # noqa: BLE001
        logger.debug("Resource update notification failed for %s", uri, exc_info=True)
        return False
