"""
MCP Sampling Module

Server-initiated LLM calls via the connected MCP client's model.
Used to generate context-aware suggestions based on live console state.

Sampling requires client support — always check capability first and
degrade gracefully when unavailable.
"""

from __future__ import annotations

import json
import logging

from mcp.types import (
    CreateMessageResult,
    ModelHint,
    ModelPreferences,
    SamplingMessage,
    TextContent,
)

logger = logging.getLogger(__name__)

# Default model preferences: favor intelligence over speed/cost
_DEFAULT_PREFS = ModelPreferences(
    intelligencePriority=0.8,
    speedPriority=0.5,
    costPriority=0.3,
    hints=[ModelHint(name="claude-sonnet-4-6")],
)


async def check_sampling_support(session) -> bool:
    """Check if the connected client supports sampling.

    Returns True if sampling/createMessage is available.
    """
    try:
        from mcp.types import ClientCapabilities

        session.check_client_capability(ClientCapabilities(sampling={}))
        return True
    except Exception:
        return False


async def generate_cue_suggestions(
    session,
    console_state: dict[str, str],
    sequence_info: str,
) -> str | None:
    """Ask the client LLM to suggest next cues based on console state.

    Args:
        session: MCP ServerSession
        console_state: System variables dict from ListVar
        sequence_info: Description of existing sequence/cue structure

    Returns:
        LLM suggestion text, or None if sampling unavailable.
    """
    if not await check_sampling_support(session):
        return None

    state_summary = json.dumps(console_state, indent=2)

    result = await _create_message(
        session,
        system_prompt=(
            "You are a grandMA2 lighting programming assistant. "
            "Suggest next cues or programming steps based on the current "
            "console state. Be specific about fixture groups, presets, "
            "and timing. Reference MA2 tools by name."
        ),
        user_message=(
            f"Current console state:\n```json\n{state_summary}\n```\n\n"
            f"Current sequence info:\n{sequence_info}\n\n"
            "Suggest 2-3 next programming steps."
        ),
        max_tokens=500,
    )

    return _extract_text(result) if result else None


async def generate_troubleshooting_advice(
    session,
    error_message: str,
    recent_commands: list[str],
) -> str | None:
    """Ask the client LLM to suggest troubleshooting steps.

    Args:
        session: MCP ServerSession
        error_message: The error encountered
        recent_commands: Last N commands sent to the console

    Returns:
        Troubleshooting advice text, or None if sampling unavailable.
    """
    if not await check_sampling_support(session):
        return None

    commands_str = "\n".join(f"  - {cmd}" for cmd in recent_commands[-10:])

    result = await _create_message(
        session,
        system_prompt=(
            "You are a grandMA2 troubleshooting expert. Diagnose the error "
            "based on the command history and suggest fixes. Be concise."
        ),
        user_message=(
            f"Error: {error_message}\n\n"
            f"Recent commands:\n{commands_str}\n\n"
            "What went wrong and how to fix it?"
        ),
        max_tokens=300,
    )

    return _extract_text(result) if result else None


async def generate_lua_script(
    session,
    description: str,
    console_version: str = "3.9.60",
) -> str | None:
    """Ask the client LLM to generate a Lua script for MA2.

    Args:
        session: MCP ServerSession
        description: What the Lua script should do
        console_version: MA2 software version

    Returns:
        Generated Lua script text, or None if sampling unavailable.
    """
    if not await check_sampling_support(session):
        return None

    result = await _create_message(
        session,
        system_prompt=(
            f"You are a grandMA2 Lua scripting expert (version {console_version}). "
            "Generate clean, well-commented Lua scripts that use the gma2 "
            "Lua API. Use gma.cmd() for console commands. Always include "
            "error handling. Output only the Lua code block."
        ),
        user_message=f"Write a Lua script that: {description}",
        max_tokens=1000,
    )

    return _extract_text(result) if result else None


async def _create_message(
    session,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 500,
    preferences: ModelPreferences | None = None,
) -> CreateMessageResult | None:
    """Send a sampling request to the client.

    Returns the CreateMessageResult or None on failure.
    """
    try:
        messages = [
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=user_message),
            )
        ]

        result = await session.create_message(
            messages=messages,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            include_context="thisServer",
            model_preferences=preferences or _DEFAULT_PREFS,
        )

        logger.info(
            "Sampling response from model=%s, stopReason=%s",
            result.model,
            result.stopReason,
        )
        return result

    except Exception as exc:
        logger.warning("Sampling request failed: %s", exc)
        return None


def _extract_text(result: CreateMessageResult) -> str | None:
    """Extract text content from a CreateMessageResult."""
    if hasattr(result.content, "text"):
        return result.content.text
    return str(result.content) if result.content else None
