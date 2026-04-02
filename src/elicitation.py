"""
MCP Elicitation Module

Server-initiated user input requests. Used within MCP tools to ask
the user for confirmation or input via structured schemas.

The primary use case is confirming destructive operations: instead of
requiring `confirm_destructive=True` upfront, a tool can elicit
confirmation interactively.

Elicitation requires client support — graceful degradation is mandatory.
"""

from __future__ import annotations

import logging
from enum import Enum

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ElicitationAction(str, Enum):
    """Possible user responses to an elicitation request."""

    ACCEPT = "accept"
    DECLINE = "decline"
    CANCEL = "cancel"


class DestructiveConfirmation(BaseModel):
    """Schema for confirming a destructive operation."""

    confirmed: bool


class TargetSelection(BaseModel):
    """Schema for selecting a target object."""

    object_id: str
    object_name: str


class PageSelection(BaseModel):
    """Schema for selecting a page number."""

    page_number: int


async def elicit_destructive_confirmation(
    session,
    command: str,
    object_description: str,
) -> bool:
    """Ask the user to confirm a destructive operation.

    Args:
        session: MCP ServerSession (from ctx.session)
        command: The MA2 command that will be executed
        object_description: Human-readable description of what will be affected

    Returns:
        True if user confirmed, False if declined/cancelled or elicitation unsupported.
    """
    try:
        from mcp.server.elicitation import elicit_with_validation

        result = await elicit_with_validation(
            session=session,
            message=(
                f"Destructive operation requested:\n\n"
                f"Command: `{command}`\n"
                f"Affects: {object_description}\n\n"
                f"This action cannot be easily undone. Confirm?"
            ),
            schema=DestructiveConfirmation,
        )

        if result.action == ElicitationAction.ACCEPT:
            return result.data.confirmed
        return False

    except Exception as exc:
        logger.debug("Elicitation not available: %s", exc)
        return False


async def elicit_target_selection(
    session,
    message: str,
) -> tuple[str, str] | None:
    """Ask the user to specify a target object.

    Returns:
        (object_id, object_name) tuple if accepted, None otherwise.
    """
    try:
        from mcp.server.elicitation import elicit_with_validation

        result = await elicit_with_validation(
            session=session,
            message=message,
            schema=TargetSelection,
        )

        if result.action == ElicitationAction.ACCEPT:
            return (result.data.object_id, result.data.object_name)
        return None

    except Exception as exc:
        logger.debug("Elicitation not available: %s", exc)
        return None


async def check_elicitation_support(session) -> bool:
    """Check if the connected client supports elicitation.

    Returns True if elicitation is available, False otherwise.
    """
    try:
        from mcp.types import ClientCapabilities

        session.check_client_capability(ClientCapabilities(elicitation={}))
        return True
    except Exception:
        return False
