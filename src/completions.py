"""
MCP Completions Module

Provides argument autocompletion for MCP prompts and resource templates.
Helps AI clients discover valid values for parameters like sequence IDs,
fixture groups, preset types, and prompt arguments.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    Completion,
    CompletionArgument,
    PromptReference,
    ResourceTemplateReference,
)

from src.commands.constants import PRESET_TYPES

logger = logging.getLogger(__name__)

# Known MA2 fixture types for prompt autocompletion
_FIXTURE_TYPES = [
    "Generic Dimmer",
    "Mac 700 Profile",
    "Mac 700 Wash",
    "Mac 2000 Profile",
    "Mac 2000 Wash",
    "Mac Aura",
    "Mac Viper",
    "VL3500 Spot",
    "VL3500 Wash",
    "Robin 600",
    "Sharpy",
]

# Preset type names (from constants)
_PRESET_TYPE_NAMES = sorted(PRESET_TYPES.keys())


def register_completions(mcp: FastMCP) -> None:
    """Register completion handler on the given FastMCP server."""

    @mcp.completion()
    async def handle_completion(
        ref: ResourceTemplateReference | PromptReference,
        argument: CompletionArgument,
    ) -> Completion | None:
        """Provide autocompletion for prompt and resource template arguments."""

        # Resource template completions
        if isinstance(ref, ResourceTemplateReference):
            return _complete_resource(ref, argument)

        # Prompt completions
        if isinstance(ref, PromptReference):
            return _complete_prompt(ref, argument)

        return None


def _complete_resource(
    ref: ResourceTemplateReference,
    argument: CompletionArgument,
) -> Completion | None:
    """Complete resource template parameters."""
    uri = str(ref.uri) if hasattr(ref, "uri") else ""

    # gma2://show/sequences/{seq_id}/cues → suggest sequence IDs
    if "sequences" in uri and argument.name == "seq_id":
        # Suggest common sequence ID ranges
        prefix = argument.value or ""
        candidates = [str(i) for i in range(1, 51)]
        matches = [c for c in candidates if c.startswith(prefix)][:100]
        return Completion(values=matches, total=len(matches), hasMore=False)

    return None


def _complete_prompt(
    ref: PromptReference,
    argument: CompletionArgument,
) -> Completion | None:
    """Complete prompt argument values."""
    name = ref.name or ""
    arg_name = argument.name
    prefix = (argument.value or "").lower()

    if name == "program-color-chase":
        if arg_name == "fixture_group":
            candidates = [str(i) for i in range(1, 21)]
            matches = [c for c in candidates if c.startswith(prefix)]
            return Completion(values=matches, total=len(matches), hasMore=False)
        if arg_name == "color_count":
            candidates = ["2", "3", "4", "5", "6", "8", "10", "12"]
            matches = [c for c in candidates if c.startswith(prefix)]
            return Completion(values=matches, total=len(matches), hasMore=False)

    elif name == "setup-moving-lights":
        if arg_name == "fixture_type":
            matches = [ft for ft in _FIXTURE_TYPES if ft.lower().startswith(prefix)]
            return Completion(values=matches, total=len(matches), hasMore=False)
        if arg_name == "start_address":
            candidates = [str(i) for i in range(1, 513, 32)]
            matches = [c for c in candidates if c.startswith(prefix)]
            return Completion(values=matches, total=len(matches), hasMore=False)
        if arg_name == "count":
            candidates = ["1", "2", "4", "6", "8", "10", "12", "16", "20", "24"]
            matches = [c for c in candidates if c.startswith(prefix)]
            return Completion(values=matches, total=len(matches), hasMore=False)

    elif name == "create-cue-sequence":
        if arg_name == "sequence_id":
            candidates = [str(i) for i in range(1, 51)]
            matches = [c for c in candidates if c.startswith(prefix)]
            return Completion(values=matches, total=len(matches), hasMore=False)
        if arg_name == "cue_count":
            candidates = ["1", "2", "3", "5", "8", "10", "15", "20"]
            matches = [c for c in candidates if c.startswith(prefix)]
            return Completion(values=matches, total=len(matches), hasMore=False)

    return None
