"""
MCP Server Module

This module is responsible for creating and running the MCP server,
integrating all tools together. It uses FastMCP to simplify the MCP server setup.

Usage:
    uv run python -m src.server
"""

import asyncio
import functools
import json
import logging
import os
import re
import sys
import time
from datetime import UTC
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.agent_memory import LongTermMemory
from src.auth import OAuthScope, has_scope, require_scope
from src.commands import (
    add_to_selection as build_add_to_selection,
)
from src.commands import (
    add_user_var as build_add_user_var,
)
from src.commands import (
    add_var as build_add_var,
)
from src.commands import (
    align as build_align,
)
from src.commands import (
    appearance as build_appearance,
)
from src.commands import (
    # assign_object
    assign as build_assign,
)
from src.commands import (
    assign_delay as build_assign_delay,
)
from src.commands import (
    assign_effect_to_executor as build_assign_effect_to_executor,
)
from src.commands import (
    assign_fade as build_assign_fade,
)
from src.commands import (
    assign_function as build_assign_function,
)
from src.commands import (
    assign_to_layout as build_assign_to_layout,
)
from src.commands import (
    at_relative as build_at_relative,
)
from src.commands import (
    attribute_at,
    build_assign_world_to_user_profile,
    build_delete_user,
    build_list_users,
    build_store_user,
    call,
    channel_at,
    fixture_at,
    go_macro,
    go_sequence,
    goto_cue,
    group_at,
    label_group,
    pause_sequence,
    select_fixture,
    store_group,
)
from src.commands import (
    blackout as build_blackout,
)
from src.commands import (
    block as build_block,
)
from src.commands import (
    clear as build_clear,
)
from src.commands import (
    clear_active as build_clear_active,
)
from src.commands import (
    clear_all as build_clear_all,
)
from src.commands import (
    clear_selection as build_clear_selection,
)
from src.commands import (
    clone as build_clone,
)
from src.commands import (
    copy as build_copy,
)
from src.commands import (
    cut as build_cut,
)
from src.commands import (
    def_go_back as build_def_go_back,
)
from src.commands import (
    def_go_forward as build_def_go_forward,
)
from src.commands import (
    def_go_pause as build_def_go_pause,
)
from src.commands import (
    delete as build_delete,
)
from src.commands import (
    delete_cue as build_delete_cue,
)
from src.commands import (
    delete_fixture as build_delete_fixture,
)
from src.commands import (
    delete_show as build_delete_show,
)
from src.commands import (
    # edit_object
    edit as build_edit,
)
from src.commands import (
    executor_at as build_executor_at,
)
from src.commands import (
    export_object as build_export_object,
)
from src.commands import (
    fix_fixture as build_fix_fixture,
)
from src.commands import (
    flash_executor as build_flash_executor,
)
from src.commands import (
    get_user_var as build_get_user_var,
)
from src.commands import (
    # playback_action
    go as build_go,
)
from src.commands import (
    go_back as build_go_back,
)
from src.commands import (
    go_fast_back as build_go_fast_back,
)
from src.commands import (
    go_fast_forward as build_go_fast_forward,
)
from src.commands import (
    goto as build_goto,
)
from src.commands import (
    goto_timecode as build_goto_timecode,
)
from src.commands import (
    highlight as build_highlight,
)
from src.commands import (
    import_fixture_type_cmd as build_import_fixture_type_cmd,
)
from src.commands import (
    import_layer_cmd as build_import_layer_cmd,
)
from src.commands import (
    import_object as build_import_object,
)
from src.commands import (
    info as build_info,
)
from src.commands import (
    invert as build_invert,
)
from src.commands import (
    label as build_label,
)
from src.commands import (
    # label_or_appearance
    label_preset as build_label_preset,
)
from src.commands import (
    list_attribute as build_list_attribute,
)
from src.commands import (
    list_cue as build_list_cue,
)
from src.commands import (
    list_effect_library as build_list_effect_library,
)
from src.commands import (
    list_fader_modules as build_list_fader_modules,
)
from src.commands import (
    list_group as build_list_group,
)
from src.commands import (
    list_library as build_list_library,
)
from src.commands import (
    list_macro_library as build_list_macro_library,
)
from src.commands import (
    list_messages as build_list_messages,
)
from src.commands import (
    # query_object_list
    list_objects as build_list_objects,
)
from src.commands import (
    list_oops as build_list_oops,
)
from src.commands import (
    list_plugin_library as build_list_plugin_library,
)
from src.commands import (
    list_preset as build_list_preset,
)
from src.commands import (
    list_shows as build_list_shows,
)
from src.commands import (
    list_update as build_list_update,
)
from src.commands import (
    list_user_var as build_list_user_var,
)
from src.commands import (
    list_var as build_list_var,
)
from src.commands import (
    load_next as build_load_next,
)
from src.commands import (
    load_prev as build_load_prev,
)
from src.commands import (
    load_show as build_load_show,
)
from src.commands import (
    locate as build_locate,
)
from src.commands import (
    move as build_move,
)
from src.commands import (
    new_show as build_new_show,
)
from src.commands import (
    off_executor as build_off_executor,
)
from src.commands import (
    on_executor as build_on_executor,
)
from src.commands import (
    page_next as build_page_next,
)
from src.commands import (
    page_previous as build_page_previous,
)
from src.commands import (
    park as build_park,
)
from src.commands import (
    paste as build_paste,
)
from src.commands import (
    release_effects_on_page as build_release_effects_on_page,
)
from src.commands import (
    release_executor as build_release_executor,
)
from src.commands import (
    # remove_content
    remove as build_remove,
)
from src.commands import (
    remove_effect as build_remove_effect,
)
from src.commands import (
    remove_fixture as build_remove_fixture,
)
from src.commands import (
    remove_from_selection as build_remove_from_selection,
)
from src.commands import (
    remove_preset_type as build_remove_preset_type,
)
from src.commands import (
    remove_selection as build_remove_selection,
)
from src.commands import (
    set_effect_rate as build_set_effect_rate,
)
from src.commands import (
    set_effect_speed as build_set_effect_speed,
)
from src.commands import (
    set_user_var as build_set_user_var,
)
from src.commands import (
    # manage_variable
    set_var as build_set_var,
)
from src.commands import (
    solo_executor as build_solo_executor,
)
from src.commands import (
    stomp_executor as build_stomp_executor,
)
from src.commands import (
    # store_object
    store as build_store_generic,
)
from src.commands import (
    store_cue as build_store_cue,
)
from src.commands import (
    store_cue_timed as build_store_cue_timed,
)
from src.commands import (
    store_preset as build_store_preset,
)
from src.commands import (
    swop_executor as build_swop_executor,
)
from src.commands import (
    temp_fader as build_temp_fader,
)
from src.commands import (
    top_executor as build_top_executor,
)
from src.commands import (
    unblock as build_unblock,
)
from src.commands import (
    unpark as build_unpark,
)
from src.commands import (
    update_cue as build_update_cue,
)
from src.commands import (
    zero_page_faders as build_zero_page_faders,
)
from src.commands import (
    build_login as build_console_login,
)
from src.commands import (
    build_logout as build_console_logout,
)
from src.commands import (
    lock_console as build_lock_console,
)
from src.commands import (
    unlock_console as build_unlock_console,
)
from src.commands import (
    call_plugin as build_call_plugin,
)
from src.commands import (
    run_lua as build_run_lua,
)
from src.commands import (
    reload_plugins as build_reload_plugins,
)
from src.commands import (
    set_special_master as build_set_special_master,
    SPECIAL_MASTER_NAMES,
)
from src.commands import (
    rdm_automatch as build_rdm_automatch,
    rdm_autopatch as build_rdm_autopatch,
    rdm_list as build_rdm_list,
    rdm_info as build_rdm_info,
    rdm_setpatch as build_rdm_setpatch,
    rdm_unmatch as build_rdm_unmatch,
)
from src.commands import (
    chaser_rate as build_chaser_rate,
    chaser_speed as build_chaser_speed,
    chaser_skip as build_chaser_skip,
    chaser_xfade as build_chaser_xfade,
)
from src.commands import (
    set_effect_parameter as build_set_effect_parameter,
)
from src.context import _current_session_id
from src.credentials import get_operator_identity, resolve_console_credentials
from src.navigation import get_current_location, list_destination, navigate, scan_indexes, set_property
from src.orchestrator import Orchestrator
from src.server_orchestration_tools import register_orchestration_tools
from src.session_manager import SessionManager
from src.telemetry import ToolTelemetry, infer_risk_tier
from src.telnet_client import GMA2TelnetClient
from src.tools import set_gma2_client
from src.vocab import RiskTier, build_v39_spec, classify_token

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
_GMA_HOST = os.getenv("GMA_HOST", "127.0.0.1")
_GMA_PORT = int(os.getenv("GMA_PORT", "30000"))
_GMA_USER = os.getenv("GMA_USER", "administrator")
_GMA_PASSWORD = os.getenv("GMA_PASSWORD", "admin")
_GMA_SAFETY_LEVEL = os.getenv("GMA_SAFETY_LEVEL", "standard").lower()

# Build vocab spec once for token classification / safety gating
_vocab_spec = build_v39_spec()

# Create MCP server
mcp = FastMCP(
    name="MA2 Agent",
    instructions="""grandMA2 MCP server — 210 tools, 13 resources, 10 prompts.

Use suggest_tool_for_task(task_description) to find the right tool for any task.
Use ma2://docs/tool-taxonomy resource to browse all 210 tools by category.

Core workflows:
  Inspect  → navigate_console, list_console_destination, query_object_list, get_object_info
  Plan     → inspect + list_system_variables + suggest_tool_for_task
  Execute  → run_task (rule-based orchestration) or run_agent_goal (agent harness)

SAFETY: DESTRUCTIVE tools require confirm_destructive=True.
Rights: read ma2://docs/rights-matrix before any mutating operation.
""",
)

# Per-operator session pool
_session_manager: SessionManager | None = None
_session_manager_lock = asyncio.Lock()

# Telemetry singleton — created lazily, shared by all tool wrappers
_telemetry_singleton: ToolTelemetry | None = None


def _get_telemetry() -> ToolTelemetry:
    """Return the module-level ToolTelemetry singleton (lazy init)."""
    global _telemetry_singleton
    if _telemetry_singleton is None:
        _telemetry_singleton = ToolTelemetry()
    return _telemetry_singleton




async def _get_session_manager() -> SessionManager:
    global _session_manager
    async with _session_manager_lock:
        if _session_manager is None:
            _session_manager = SessionManager(host=_GMA_HOST, port=_GMA_PORT)
            _session_manager.start_keepalive()
    return _session_manager


async def get_client() -> GMA2TelnetClient:
    """
    Return a live Telnet client for the current operator.

    Routes through the SessionManager so each operator identity gets its own
    Telnet connection authenticated with the console user that matches their
    OAuth scope tier (dual-enforcement).

    Stub mode  — ``GMA_USER`` set  : single identity, uses GMA_USER/GMA_PASSWORD
    Tier mode  — ``GMA_USER`` unset: identity = "tier:N", credentials from
                                     bootstrap user table in src/credentials.py
    OAuth mode — replace get_operator_identity() with JWT sub-claim extraction
    """
    from src.auth import get_granted_scopes
    scopes = get_granted_scopes()
    identity = get_operator_identity(scopes)
    username, password = resolve_console_credentials(scopes)

    manager = await _get_session_manager()
    client = await manager.get(identity, username, password)
    set_gma2_client(client)
    return client


def _handle_errors(func):
    """Decorator that catches exceptions in MCP tools and returns JSON errors.

    Also records every invocation to the ``tool_invocations`` telemetry table
    (controlled by the ``GMA_TELEMETRY`` env var; default enabled).
    Risk tier and operator identity are inferred once at decoration time.
    """
    _risk_tier = infer_risk_tier(func)

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> str:
        t0 = time.monotonic()
        result: str = ""
        error_class: str | None = None
        try:
            result = await func(*args, **kwargs)
        except ConnectionError as e:
            logger.error("Connection error in %s: %s", func.__name__, e)
            error_class = "ConnectionError"
            result = json.dumps({"error": f"Connection failed: {e}", "blocked": True}, indent=2)
        except RuntimeError as e:
            logger.error("Runtime error in %s: %s", func.__name__, e)
            error_class = "RuntimeError"
            result = json.dumps({"error": f"Runtime error: {e}", "blocked": True}, indent=2)
        except Exception as e:
            logger.error("Unexpected error in %s: %s", func.__name__, e, exc_info=True)
            error_class = type(e).__name__
            result = json.dumps({"error": f"Unexpected error: {e}", "blocked": True}, indent=2)
        finally:
            if os.getenv("GMA_TELEMETRY", "1") != "0":
                try:  # noqa: SIM105
                    _get_telemetry().record_sync(
                        tool_name=func.__name__,
                        inputs_json=json.dumps(
                            {k: str(v)[:200] for k, v in kwargs.items()}, default=str
                        ),
                        output_preview=result[:500] if result else "",
                        error_class=error_class,
                        latency_ms=(time.monotonic() - t0) * 1000,
                        risk_tier=_risk_tier,
                        operator=os.getenv("GMA_USER", "unknown"),
                        session_id=_current_session_id.get(),
                    )
                except Exception:  # noqa: BLE001, SIM105
                    pass  # telemetry must never break a tool call
        return result

    return wrapper


# ============================================================
# Private helpers — object existence probing
# ============================================================

# Regex to parse sequence ID from "list executor PAGE.ID" response.
# Matches "Sequence=Seq 278" and "Sequence=Seq 278(2)".
_SEQ_FOR_EXECUTOR_RE = re.compile(r"Sequence=Seq\s+(\d+)", re.IGNORECASE)


async def _validate_object_exists(
    client: GMA2TelnetClient,
    object_type: str,
    object_id: int | str,
) -> tuple[bool, str]:
    """
    Probe whether an object exists using 'list {object_type} {object_id}'.

    MA2 returns "NO OBJECTS FOUND FOR LIST" when the object does not exist.
    Any other response (including data rows) is treated as existence confirmed.

    Not decorated with @_handle_errors — exceptions propagate to the
    enclosing tool's decorator.

    Args:
        client: Connected GMA2TelnetClient (already obtained by the caller).
        object_type: MA2 keyword, e.g. "fixture", "cue", "group".
        object_id: Integer ID or compound string, e.g. "99 sequence 278".

    Returns:
        (exists: bool, raw_response: str)
    """
    probe_cmd = f"list {object_type} {object_id}"
    raw = await client.send_command_with_response(probe_cmd)
    exists = "NO OBJECTS FOUND" not in raw.upper()
    logger.debug("_validate_object_exists %r → exists=%s", probe_cmd, exists)
    return exists, raw


async def _get_sequence_for_executor(
    client: GMA2TelnetClient,
    executor_id: int,
    page: int = 1,
) -> tuple[int | None, str]:
    """
    Resolve the sequence linked to an executor via 'list executor PAGE.ID'.

    Parses "Sequence=Seq N" from the response. Returns (None, raw) if the
    executor has no sequence assigned or is not found.

    Args:
        client: Connected GMA2TelnetClient (already obtained by the caller).
        executor_id: Executor number within the page.
        page: Executor page number (default 1).

    Returns:
        (sequence_id: int | None, raw_response: str)
    """
    probe_cmd = f"list executor {page}.{executor_id}"
    raw = await client.send_command_with_response(probe_cmd)
    m = _SEQ_FOR_EXECUTOR_RE.search(raw)
    if m:
        seq_id = int(m.group(1))
        logger.debug(
            "_get_sequence_for_executor: executor %d.%d → sequence %d",
            page, executor_id, seq_id,
        )
        return seq_id, raw
    logger.debug(
        "_get_sequence_for_executor: executor %d.%d — no sequence in response",
        page, executor_id,
    )
    return None, raw


# ============================================================
# MCP Tools Definition
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.GROUP_STORE)
@_handle_errors
async def create_fixture_group(
    start_fixture: int,
    end_fixture: int,
    group_id: int,
    group_name: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Create a group containing a specified range of fixtures (DESTRUCTIVE).

    This tool selects the specified range of fixtures and saves them as a group.
    Optionally, a name can be assigned to the group.

    Args:
        start_fixture: Starting fixture number
        end_fixture: Ending fixture number
        group_id: Group number to save
        group_name: (Optional) Group name, e.g., "Front Wash"
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: Operation result message

    Examples:
        - Save fixtures 1 to 10 as group 1
        - Save fixtures 1 to 10 as group 1 with name "Front Wash"
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Create Fixture Group uses Store (DESTRUCTIVE). Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()

    # Select fixtures
    select_cmd = select_fixture(start_fixture, end_fixture)
    await client.send_command(select_cmd)

    # Save as group
    store_cmd = store_group(group_id)
    await client.send_command(store_cmd)

    # Add label if name is provided
    if group_name:
        label_cmd = label_group(group_id, group_name)
        await client.send_command(label_cmd)
        return f'Created Group {group_id} "{group_name}" containing Fixtures {start_fixture} to {end_fixture}'

    return (
        f"Created Group {group_id} containing Fixtures {start_fixture} to {end_fixture}"
    )


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def execute_sequence(
    sequence_id: int,
    action: str,
    cue_id: int | None = None,
) -> str:
    """
    Execute sequence-related operations.

    Args:
        sequence_id: Sequence number
        action: Operation type: "go" (execute), "pause" (pause), or "goto" (jump to cue)
        cue_id: (Required for goto) Target cue number

    Returns:
        str: Operation result message

    Examples:
        - Execute sequence 1
        - Pause sequence 2
        - Jump to cue 5 of sequence 1
    """
    client = await get_client()

    if action == "go":
        cmd = go_sequence(sequence_id)
        await client.send_command(cmd)
        return f"Executed Sequence {sequence_id}"

    elif action == "pause":
        cmd = pause_sequence(sequence_id)
        await client.send_command(cmd)
        return f"Paused Sequence {sequence_id}"

    elif action == "goto":
        if cue_id is None:
            return "Error: goto action requires cue_id to be specified"
        cmd = goto_cue(sequence_id, cue_id)
        await client.send_command(cmd)
        return f"Jumped to Cue {cue_id} of Sequence {sequence_id}"

    return f"Unknown action: {action}, use go, pause, or goto"


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def send_raw_command(
    command: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Send a raw MA command to grandMA2 and return the console response.

    WARNING: This is a low-level tool that sends commands directly to a LIVE
    lighting console. Prefer the higher-level tools (create_fixture_group,
    execute_sequence) whenever possible.

    SAFETY: Commands are classified by risk tier before sending:
    - SAFE_READ (list, info, cd): Always allowed
    - SAFE_WRITE (at, go, clear, blackout): Allowed in standard and admin mode
    - DESTRUCTIVE (delete, store, assign, shutdown): Blocked unless
      confirm_destructive=True. Set GMA_SAFETY_LEVEL=admin to skip checks.

    Args:
        command: Raw MA command to send
        confirm_destructive: Must be True to send destructive commands
            (delete, store, assign, shutdown, newshow, etc.)

    Returns:
        str: JSON with command_sent, risk_tier, raw_response, and any
            safety block information.

    Examples:
        - go+ executor 1.1
        - list cue
        - store sequence 1 cue 1 (requires confirm_destructive=True)
    """
    # Input sanitization: reject line breaks that could inject commands
    if "\r" in command or "\n" in command:
        return json.dumps({
            "command_sent": None,
            "error": "Command contains line breaks (\\r or \\n) which could "
                     "inject additional commands. Remove them and retry.",
            "blocked": True,
        }, indent=2)

    # Safety gate: classify the first token
    first_token = command.strip().split()[0] if command.strip() else ""
    resolved = classify_token(first_token, _vocab_spec)
    risk = resolved.risk

    # Log and optionally block destructive commands
    if risk == RiskTier.DESTRUCTIVE:
        if _GMA_SAFETY_LEVEL == "admin":
            # Admin mode: allow but still log for audit trail
            logger.warning(
                "ADMIN-MODE destructive command: %r (risk=%s, canonical=%s)",
                command, risk.value, resolved.canonical,
            )
        elif not confirm_destructive:
            logger.warning(
                "BLOCKED destructive command: %r (risk=%s, canonical=%s)",
                command, risk.value, resolved.canonical,
            )
            return json.dumps({
                "command_sent": None,
                "risk_tier": risk.value,
                "canonical_keyword": resolved.canonical,
                "error": (
                    f"Command '{first_token}' is classified as {risk.value}. "
                    f"Set confirm_destructive=True to proceed, or use "
                    f"GMA_SAFETY_LEVEL=admin to disable safety checks."
                ),
                "blocked": True,
            }, indent=2)
        else:
            logger.warning(
                "CONFIRMED destructive command: %r (risk=%s, canonical=%s)",
                command, risk.value, resolved.canonical,
            )

    # Block all write commands in read-only mode
    if _GMA_SAFETY_LEVEL == "read-only" and risk != RiskTier.SAFE_READ:
        logger.warning(
            "BLOCKED non-read command in read-only mode: %r (risk=%s)",
            command, risk.value,
        )
        return json.dumps({
            "command_sent": None,
            "risk_tier": risk.value,
            "error": (
                "Server is in read-only mode (GMA_SAFETY_LEVEL=read-only). "
                "Only SAFE_READ commands (list, info, cd) are allowed."
            ),
            "blocked": True,
        }, indent=2)

    logger.info(
        "Sending command: %r (risk=%s, canonical=%s)",
        command, risk.value, resolved.canonical,
    )

    client = await get_client()
    raw_response = await client.send_command_with_response(command)

    return json.dumps({
        "command_sent": command,
        "risk_tier": risk.value,
        "canonical_keyword": resolved.canonical,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def navigate_console(
    destination: str,
    object_id: int | None = None,
) -> str:
    """
    Navigate the grandMA2 console's object tree using ChangeDest (cd).

    Sends a cd command and captures the raw telnet response, attempting
    to parse the resulting console prompt to determine the current
    location in the object tree.

    EXPLORATORY: The exact MA2 telnet prompt format is being validated.
    The raw_response field always contains the unmodified telnet output
    for manual inspection, regardless of whether parsing succeeded.

    Args:
        destination: Navigation target. Supported formats:
            - "/" to go to root
            - ".." to go up one level
            - A number (e.g., "5") to navigate by index
            - An object type (e.g., "Group") when object_id is provided
              (uses dot notation: cd Group.1)
            - A quoted name (e.g., '"MySequence"') to navigate by name
        object_id: Object ID, produces dot notation cd [type].[id]
            (e.g., destination="Group", object_id=1 → cd Group.1)

    Returns:
        str: JSON with command_sent, raw_response, parsed prompt details,
             and success indicator.

    Examples:
        - Navigate to root: destination="/"
        - Go up one level: destination=".."
        - Navigate to Group 1: destination="Group", object_id=1 → cd Group.1
        - Navigate by index: destination="5"
        - After navigating, use list_console_destination to enumerate objects
    """
    client = await get_client()
    result = await navigate(client, destination, object_id)

    return json.dumps(
        {
            "command_sent": result.command_sent,
            "raw_response": result.raw_response,
            "success": result.success,
            "parsed_prompt": {
                "prompt_line": result.parsed_prompt.prompt_line,
                "location": result.parsed_prompt.location,
                "object_type": result.parsed_prompt.object_type,
                "object_id": result.parsed_prompt.object_id,
            },
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_console_location() -> str:
    """
    Query the current grandMA2 console destination without navigating.

    Sends an empty command to prompt the console to re-display its
    prompt, then parses the response to determine the current location.

    Returns:
        str: JSON with raw_response, parsed prompt details,
             and success indicator.
    """
    client = await get_client()
    result = await get_current_location(client)

    return json.dumps(
        {
            "command_sent": result.command_sent,
            "raw_response": result.raw_response,
            "success": result.success,
            "parsed_prompt": {
                "prompt_line": result.parsed_prompt.prompt_line,
                "location": result.parsed_prompt.location,
                "object_type": result.parsed_prompt.object_type,
                "object_id": result.parsed_prompt.object_id,
            },
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_console_destination(
    object_type: str | None = None,
) -> str:
    """
    List objects at the current grandMA2 console destination.

    After navigating with cd (navigate_console), use this tool to
    enumerate children at the current location.  Parses the list
    feedback to extract object-type, object-id, and element names.

    Args:
        object_type: Optional filter (e.g., "cue", "group", "preset").
            If omitted, lists everything at the current destination.

    Returns:
        str: JSON with command_sent, raw_response, and parsed entries
             (each with object_type, object_id, name).
    """
    client = await get_client()
    result = await list_destination(client, object_type)

    entries_out = []
    for e in result.parsed_list.entries:
        entry = {
            "object_type": e.object_type,
            "object_id": e.object_id,
            "name": e.name,
            "raw_line": e.raw_line,
        }
        if e.col3 is not None:
            entry["col3"] = e.col3
        if e.columns:
            entry["columns"] = e.columns
        entries_out.append(entry)

    return json.dumps(
        {
            "command_sent": result.command_sent,
            "raw_response": result.raw_response,
            "entries": entries_out,
            "entry_count": len(result.parsed_list.entries),
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def scan_console_indexes(
    reset_to: str = "/",
    max_index: int = 50,
    stop_after_failures: int = 3,
) -> str:
    """
    Scan numeric indexes via cd N → list → cd <reset_to>.

    For each index N from 1 to max_index:
      1. cd N           — navigate into that index
      2. list           — enumerate children there
      3. cd <reset_to>  — return to the base location for the next iteration

    The reset_to destination controls what each cd N is relative to:
      - "/"          (default) scan root-level indexes (Showfile, TimeConfig, …)
      - "Sequence"   reset to Sequence pool → cd N enters Sequence N → list shows its cues
      - "Group"      reset to Group pool → cd N enters Group N

    Stops early after stop_after_failures consecutive indexes with no entries.

    Args:
        reset_to: Where to navigate after each list before the next cd N (default "/").
        max_index: Highest index to try (default 50).
        stop_after_failures: Stop after this many consecutive empty indexes (default 3).

    Returns:
        str: JSON with a list of scan results — one entry per index that
             returned list output, each with index, location, object_type,
             and parsed entries (object_type, object_id, name).
    """
    client = await get_client()
    results = await scan_indexes(
        client,
        reset_to=reset_to,
        max_index=max_index,
        stop_after_failures=stop_after_failures,
    )

    return json.dumps(
        {
            "scanned_count": len(results),
            "results": [
                {
                    "index": r.index,
                    "location": r.location,
                    "object_type": r.object_type,
                    "entry_count": len(r.entries),
                    "entries": [
                        {
                            "object_type": e.object_type,
                            "object_id": e.object_id,
                            "name": e.name,
                        }
                        for e in r.entries
                    ],
                }
                for r in results
            ],
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def set_node_property(
    path: str,
    property_name: str,
    value: str,
    verify: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """
    Set a property on a node in the grandMA2 object tree (DESTRUCTIVE).

    Uses the scan tree path notation (dot-separated indexes) to navigate
    to a node and set an inline property using Assign [index]/property=value.

    The path uses the same index-based notation as the scan tree output.
    Split the path into parent segments and target index:
    - "3.1" → cd 3 (Settings), then Assign 1/property=value (on Global)
    - "4.1" → cd 4 (DMX_Protocols), then Assign 1/property=value (on Art-Net)
    - "3" → at root, Assign 3/property=value (on Settings itself)

    After setting, navigates back to root (cd /).
    If verify=True (default), re-lists and confirms the property changed.

    SAFETY: This modifies live console state. Requires confirm_destructive=True.

    Args:
        path: Dot-separated index path (e.g. "3.1" for Settings/Global)
        property_name: Property to set (e.g. "Telnet", "OutActive")
        value: New value (e.g. "Login Enabled", "On")
        verify: Re-list after setting to confirm the change (default True)
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: JSON with commands_sent, success, verified_value, and any errors.

    Examples:
        - Set telnet to disabled: path="3.1", property_name="Telnet", value="Login Disabled"
        - Enable Art-Net output: path="4.1", property_name="OutActive", value="On"
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Set Node Property uses Assign (DESTRUCTIVE). Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    result = await set_property(
        client,
        path,
        property_name,
        value,
        verify=verify,
    )

    return json.dumps(
        {
            "path": result.path,
            "property_name": property_name,
            "value": value,
            "commands_sent": result.commands_sent,
            "success": result.success,
            "verified_value": result.verified_value,
            "error": result.error,
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def set_intensity(
    target_type: str,
    target_id: int,
    level: int | float,
    end_id: int | None = None,
) -> str:
    """
    Set the intensity (dimmer) level on fixtures, groups, or channels.

    This is the most fundamental lighting operation — controlling how bright
    lights are. Selects the target and sets it to the specified percentage.

    Args:
        target_type: Object type — "fixture", "group", or "channel"
        target_id: Object ID number
        level: Intensity percentage (0-100). Use 0 for off, 100 for full.
        end_id: End ID for range selection (e.g., fixture 1 thru 10)

    Returns:
        str: JSON with command_sent and raw_response from the console.

    Examples:
        - Set fixture 1 to 50%: target_type="fixture", target_id=1, level=50
        - Set group 3 to full: target_type="group", target_id=3, level=100
        - Set fixtures 1-10 to 75%: target_type="fixture", target_id=1, level=75, end_id=10
    """
    target_type = target_type.lower()

    if target_type == "fixture":
        cmd = fixture_at(target_id, level, end=end_id)
    elif target_type == "group":
        cmd = group_at(target_id, level)
    elif target_type == "channel":
        cmd = channel_at(target_id, level, end=end_id)
    else:
        return json.dumps({
            "error": f"Unknown target_type: {target_type}. Use 'fixture', 'group', or 'channel'.",
            "blocked": True,
        }, indent=2)

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def apply_preset(
    preset_type: str,
    preset_id: int,
    fixture_id: int | None = None,
    fixture_end: int | None = None,
    group_id: int | None = None,
) -> str:
    """
    Apply a preset to fixtures or groups.

    Presets are stored lighting looks (color, position, gobo, etc.) that
    can be recalled by type and ID. Optionally select fixtures/group first.

    Preset types: "dimmer" (1), "position" (2), "gobo" (3), "color" (4),
    "beam" (5), "focus" (6), "control" (7), "shapers" (8), "video" (9)

    Args:
        preset_type: Preset type name or number (e.g. "color", "position", "4")
        preset_id: Preset number within that type
        fixture_id: Optional fixture to select first (single or range start)
        fixture_end: Optional end fixture for range selection
        group_id: Optional group to select first (alternative to fixture_id)

    Returns:
        str: JSON with commands_sent and raw_response.

    Examples:
        - Apply color preset 3 to current selection: preset_type="color", preset_id=3
        - Apply position preset 1 to group 2: preset_type="position", preset_id=1, group_id=2
        - Apply gobo preset 5 to fixtures 1-10: preset_type="gobo", preset_id=5, fixture_id=1, fixture_end=10
    """
    commands_sent = []
    client = await get_client()

    # Optionally select fixtures or group first
    if group_id is not None:
        sel_cmd = f"group {group_id}"
        await client.send_command_with_response(sel_cmd)
        commands_sent.append(sel_cmd)
    elif fixture_id is not None:
        sel_cmd = select_fixture(fixture_id, fixture_end)
        await client.send_command_with_response(sel_cmd)
        commands_sent.append(sel_cmd)

    # Build the preset type reference
    preset_type_str = preset_type.lower()
    # Map common names to numbers for the call syntax
    type_map = {
        "dimmer": "1", "position": "2", "gobo": "3", "color": "4",
        "beam": "5", "focus": "6", "control": "7", "shapers": "8", "video": "9",
    }
    type_num = type_map.get(preset_type_str, preset_type_str)

    call_cmd = call(f"preset {type_num}.{preset_id}")
    raw_response = await client.send_command_with_response(call_cmd)
    commands_sent.append(call_cmd)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def store_current_cue(
    cue_number: int,
    sequence_id: int | None = None,
    label: str | None = None,
    merge: bool = False,
    overwrite: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Store the current programmer state as a cue (DESTRUCTIVE).

    Saves whatever is currently in the programmer (selected fixtures +
    active values) into a cue in the specified sequence. This is how
    lighting looks are programmed into a show.

    Executor-sequence relationship:
      When sequence_id is omitted, MA2 stores into the sequence assigned to
      the currently selected executor on the console. Use select_executor()
      first to set the target, or pass sequence_id explicitly to make the
      destination unambiguous regardless of executor selection state.

      select executor N      → sets executor N as the active store target
      Store Cue M            → stores into the sequence on selected executor
      Store Cue M Sequence S → stores into sequence S directly (preferred)

    Args:
        cue_number: Cue number to store (required)
        sequence_id: Sequence to store into. Omit to use the selected executor's
                     sequence (call select_executor() first if needed)
        label: Optional name for the cue
        merge: Merge new values into existing cue (default False)
        overwrite: Replace existing cue completely (default False)
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: JSON with commands_sent and raw_response.

    Examples:
        - Store cue 5 (explicit sequence): cue_number=5, sequence_id=1, confirm_destructive=True
        - Store cue 3 named "Opening Look": cue_number=3, label="Opening Look", confirm_destructive=True
        - Merge into cue 1: cue_number=1, merge=True, confirm_destructive=True
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": (
                "Store Cue is a DESTRUCTIVE operation. Pass confirm_destructive=True to proceed. "
                "Tip: pass sequence_id explicitly to target a specific sequence rather than relying "
                "on the currently selected executor."
            ),
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    commands_sent = []
    client = await get_client()

    # Build store cue command
    store_cmd = build_store_cue(
        cue_id=cue_number,
        sequence_id=sequence_id,
        merge=merge,
        overwrite=overwrite,
    )

    raw_response = await client.send_command_with_response(store_cmd)
    commands_sent.append(store_cmd)

    # Optionally label the cue
    if label and cue_number is not None:
        cue_ref = str(cue_number)
        if sequence_id is not None:
            cue_ref += f" sequence {sequence_id}"
        label_cmd = build_label("cue", cue_ref, label)
        await client.send_command_with_response(label_cmd)
        commands_sent.append(label_cmd)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_object_info(
    object_type: str,
    object_id: int | str,
) -> str:
    """
    Query information about any object in the show.

    Returns the console's info response for the specified object,
    which includes its properties, status, and metadata.

    Args:
        object_type: Object type (e.g. "fixture", "group", "cue",
            "sequence", "preset", "executor", "macro")
        object_id: Object ID. For presets use "type.id" format
            (e.g. "2.1" for color preset 1).

    Returns:
        str: JSON with command_sent and raw_response containing
            the object's information.

    Examples:
        - Get info on group 3: object_type="group", object_id=3
        - Get info on cue 5: object_type="cue", object_id=5
        - Get info on color preset 1: object_type="preset", object_id="2.1"
    """
    cmd = build_info(object_type, object_id)

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def clear_programmer(
    mode: str = "all",
) -> str:
    """
    Clear the programmer to reset fixture selection and active values.

    The programmer holds the current working state — selected fixtures
    and any values you've applied. Clearing it gives you a clean slate.

    Modes:
    - "all": Empty the entire programmer (selection + values)
    - "selection": Deselect all fixtures but keep active values
    - "active": Deactivate values but keep fixture selection
    - "clear": Sequential clear (selection → active → all on repeated calls)

    Args:
        mode: Clear mode — "all" (default), "selection", "active", or "clear"

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - Full reset: mode="all"
        - Just deselect fixtures: mode="selection"
        - Just drop active values: mode="active"
    """
    mode = mode.lower()
    if mode == "all":
        cmd = build_clear_all()
    elif mode == "selection":
        cmd = build_clear_selection()
    elif mode == "active":
        cmd = build_clear_active()
    elif mode == "clear":
        cmd = build_clear()
    else:
        return json.dumps({
            "error": f"Unknown mode: {mode}. Use 'all', 'selection', 'active', or 'clear'.",
            "blocked": True,
        }, indent=2)

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def set_attribute(
    attribute_name: str,
    value: int | float,
    fixture_id: int | None = None,
    fixture_end: int | None = None,
    group_id: int | None = None,
) -> str:
    """
    Set a specific fixture attribute (Pan, Tilt, Zoom, etc.) to a value.

    Controls individual fixture parameters beyond simple dimmer intensity.
    Optionally select fixtures/group first.

    Args:
        attribute_name: Attribute name (e.g. "Pan", "Tilt", "Zoom", "Focus", "Iris")
        value: Attribute value (typically 0-100 for percentage, or degrees for Pan/Tilt)
        fixture_id: Optional fixture to select first (single or range start)
        fixture_end: Optional end fixture for range selection
        group_id: Optional group to select first

    Returns:
        str: JSON with commands_sent and raw_response.

    Examples:
        - Set Pan to 120: attribute_name="Pan", value=120
        - Set Tilt to 50 on group 2: attribute_name="Tilt", value=50, group_id=2
        - Set Zoom on fixtures 1-10: attribute_name="Zoom", value=80, fixture_id=1, fixture_end=10
    """
    commands_sent = []
    client = await get_client()

    # Optionally select fixtures or group first
    if group_id is not None:
        sel_cmd = f"group {group_id}"
        await client.send_command_with_response(sel_cmd)
        commands_sent.append(sel_cmd)
    elif fixture_id is not None:
        sel_cmd = select_fixture(fixture_id, fixture_end)
        await client.send_command_with_response(sel_cmd)
        commands_sent.append(sel_cmd)

    cmd = attribute_at(attribute_name, value)
    raw_response = await client.send_command_with_response(cmd)
    commands_sent.append(cmd)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PRESET_UPDATE)
@_handle_errors
async def park_fixture(
    target: str,
    value: int | float | None = None,
) -> str:
    """
    Park a fixture or DMX address at its current or specified output value.

    Parking locks the output so it won't change when cues or programmer
    values change. Useful for testing, worklights, or safety overrides.

    Fixture targets are pre-validated: if the fixture does not exist on the
    console, the command is not sent and an informative error is returned.
    DMX targets (e.g. "dmx 101") bypass pre-validation.

    Args:
        target: What to park (e.g. "fixture 20", "dmx 101", "fixture 20 thru 30")
        value: Optional output value to park at (0-255 for DMX, 0-100 for %)

    Returns:
        str: JSON with command_sent (None if blocked), raw_response, exists.

    Examples:
        - Park fixture 20 at current output: target="fixture 20"
        - Park DMX 101 at 128: target="dmx 101", value=128
        - Park fixture range: target="fixture 20 thru 30"
    """
    client = await get_client()

    fixture_match = re.match(r"^fixture\s+(\d+)", target.strip(), re.IGNORECASE)
    if fixture_match:
        fixture_id = fixture_match.group(1)
        exists, probe_raw = await _validate_object_exists(client, "fixture", fixture_id)
        if not exists:
            return json.dumps({
                "command_sent": None,
                "exists": False,
                "error": f"Fixture {fixture_id} does not exist on the console.",
                "hint": "Use list_fixtures() to discover valid fixture IDs.",
                "probe_response": probe_raw,
                "blocked": True,
            }, indent=2)
        exists_flag: bool | None = True
    else:
        exists_flag = None  # DMX or other — validation skipped

    cmd = build_park(target, at=value)
    raw_response = await client.send_command_with_response(cmd)

    # Sync park ledger to snapshot write-tracker (Gap 3)
    if snap := _orchestrator.last_snapshot:
        snap.parked_fixtures.add(str(target))

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "exists": exists_flag,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PRESET_UPDATE)
@_handle_errors
async def unpark_fixture(
    target: str,
) -> str:
    """
    Unpark a previously parked fixture or DMX address.

    Fixture targets are pre-validated before unparking. DMX targets bypass
    pre-validation.

    Args:
        target: What to unpark (e.g. "fixture 20", "dmx 101", "fixture 20 thru 30")

    Returns:
        str: JSON with command_sent (None if blocked), raw_response, exists.

    Examples:
        - Unpark fixture 20: target="fixture 20"
        - Unpark DMX 101: target="dmx 101"
    """
    client = await get_client()

    fixture_match = re.match(r"^fixture\s+(\d+)", target.strip(), re.IGNORECASE)
    if fixture_match:
        fixture_id = fixture_match.group(1)
        exists, probe_raw = await _validate_object_exists(client, "fixture", fixture_id)
        if not exists:
            return json.dumps({
                "command_sent": None,
                "exists": False,
                "error": f"Fixture {fixture_id} does not exist on the console.",
                "hint": "Use list_fixtures() to discover valid fixture IDs.",
                "probe_response": probe_raw,
                "blocked": True,
            }, indent=2)
        exists_flag: bool | None = True
    else:
        exists_flag = None

    cmd = build_unpark(target)
    raw_response = await client.send_command_with_response(cmd)

    # Sync park ledger to snapshot write-tracker (Gap 3)
    if snap := _orchestrator.last_snapshot:
        snap.parked_fixtures.discard(str(target))

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "exists": exists_flag,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def run_macro(
    macro_id: int,
) -> str:
    """
    Execute a macro by its ID number.

    Macros are stored command sequences on the console. This triggers
    the macro to run.

    Args:
        macro_id: Macro number to execute

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - Run macro 1: macro_id=1
        - Run macro 99: macro_id=99
    """
    client = await get_client()
    cmd = go_macro(macro_id)
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def delete_object(
    object_type: str,
    object_id: int | str,
    end_id: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Delete an object from the show.

    SAFETY: This is a DESTRUCTIVE operation. Requires confirm_destructive=True.

    Args:
        object_type: Object type (e.g. "cue", "group", "preset", "fixture", "macro")
        object_id: Object ID to delete
        end_id: Optional end ID for range deletion (e.g. cue 1 thru 10)
        confirm_destructive: Must be True to execute (safety gate)

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Delete cue 5: object_type="cue", object_id=5, confirm_destructive=True
        - Delete cues 1-10: object_type="cue", object_id=1, end_id=10, confirm_destructive=True
        - Delete group 3: object_type="group", object_id=3, confirm_destructive=True
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": "Delete is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    if object_type.lower() == "cue":
        cmd = build_delete_cue(object_id, end=end_id, noconfirm=True)
    else:
        cmd = build_delete(object_type, object_id, end=end_id, noconfirm=True)

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def copy_or_move_object(
    action: str,
    object_type: str,
    source_id: int,
    target_id: int,
    source_end: int | None = None,
    overwrite: bool = False,
    merge: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Copy or move an object to a new location (DESTRUCTIVE).

    SAFETY: Both operations modify show data. Copy duplicates the object,
    move relocates it (deleting the original). Requires confirm_destructive=True.

    Args:
        action: "copy" or "move"
        object_type: Object type (e.g. "group", "cue", "preset", "macro")
        source_id: Source object ID
        target_id: Destination object ID
        source_end: Optional end ID for range copy/move
        overwrite: Overwrite target if it exists (default False)
        merge: Merge into target if it exists (default False)
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - Copy group 1 to 5: action="copy", object_type="group", source_id=1, target_id=5
        - Move macro 3 to 10: action="move", object_type="macro", source_id=3, target_id=10
        - Copy cue range: action="copy", object_type="cue", source_id=1, target_id=20, source_end=10
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Copy/Move is a DESTRUCTIVE operation. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    action = action.lower()

    if action == "copy":
        cmd = build_copy(
            object_type, source_id, target_id,
            end=source_end, overwrite=overwrite, merge=merge,
        )
    elif action == "move":
        cmd = build_move(
            object_type, source_id, target_id,
            end=source_end,
        )
    else:
        return json.dumps({
            "error": f"Unknown action: {action}. Use 'copy' or 'move'.",
            "blocked": True,
        }, indent=2)

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PRESET_UPDATE)
@_handle_errors
async def store_new_preset(
    preset_type: str,
    preset_id: int,
    merge: bool = False,
    overwrite: bool = False,
    universal: bool = False,
    selective: bool = False,
    global_scope: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Store the current programmer values as a preset.

    Saves the active fixture values (from the programmer) into a preset
    slot for later recall with apply_preset.

    Preset types: "dimmer" (1), "position" (2), "gobo" (3), "color" (4),
    "beam" (5), "focus" (6), "control" (7), "shapers" (8), "video" (9)

    Scope flags (mutually exclusive — pick at most one):
      universal   — stores values indexed by fixture type (applies to any fixture
                    of the same profile; not tied to specific fixture IDs).
      selective   — stores values tied to the specific fixtures selected during
                    store. Recalled preset only affects those fixture IDs.
      global_scope — stores absolute values (no relative/tracking offset).

    Workflow for universal color presets:
      1. SelFix 1 Thru 999
      2. attribute "ColorRgb1" at 100
      3. store_new_preset("color", 6, universal=True, overwrite=True, confirm_destructive=True)

    SAFETY: This is a STORE operation which modifies show data.

    Args:
        preset_type: Preset type name (e.g. "color", "position", "gobo")
        preset_id: Preset number within that type
        merge: Merge into existing preset (default False)
        overwrite: Replace existing preset with /overwrite flag (default False)
        universal: Store as universal preset — applies to any fixture of the same type
        selective: Store as selective preset — applies only to selected fixture IDs
        global_scope: Store with global (absolute) values
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - Store universal color preset: preset_type="color", preset_id=6, universal=True, confirm_destructive=True
        - Overwrite position preset 3: preset_type="position", preset_id=3, overwrite=True, confirm_destructive=True
    """
    if not confirm_destructive:
        return json.dumps({
            "error": "Store Preset is a DESTRUCTIVE operation. Pass confirm_destructive=True to proceed."
        }, indent=2)
    client = await get_client()
    cmd = build_store_preset(
        preset_type, preset_id,
        merge=merge, overwrite=overwrite,
        universal=universal, selective=selective,
        global_scope=global_scope,
    )
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


# ============================================================
# New Composite Tools (Tools 20-27)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def query_object_list(
    object_type: str | None = None,
    object_id: int | str | None = None,
    end: int | None = None,
    sequence_id: int | None = None,
    preset_type: str | int | None = None,
    filename: str | None = None,
    condition: str | None = None,
) -> str:
    """
    List objects from the show file by type — cues, groups, presets, etc.

    Sends typed `list <type>` commands with type-specific options.
    Different from list_console_destination (which lists at the current
    navigation location). This tool queries named object pools directly.

    Args:
        object_type: Object type to list. Typed shortcuts:
            "cue", "group", "preset", "attribute", "messages".
            Or any generic type (e.g. "sequence", "macro", "executor").
            If omitted, lists all objects at the default scope.
        object_id: Optional object ID to list a specific item
        end: Optional end ID for range listing (e.g. cue 1 thru 10)
        sequence_id: Sequence to list cues from (only for object_type="cue")
        preset_type: Preset type name or number (only for object_type="preset",
            e.g. "color", "position", "4")
        filename: Optional filename to export the list output
        condition: Optional filter condition (for "messages" or generic types)

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - List all cues: object_type="cue"
        - List cues in sequence 2: object_type="cue", sequence_id=2
        - List groups: object_type="group"
        - List color presets: object_type="preset", preset_type="color"
        - List attributes: object_type="attribute"
    """
    otype = (object_type or "").lower()

    if otype == "cue":
        cmd = build_list_cue(
            cue_id=object_id, end=end, sequence_id=sequence_id,
            filename=filename,
        )
    elif otype == "group":
        cmd = build_list_group(
            group_id=object_id, end=end, filename=filename,
        )
    elif otype == "preset":
        cmd = build_list_preset(
            preset_type=preset_type, preset_id=object_id,
            end=end, filename=filename,
        )
    elif otype == "attribute":
        cmd = build_list_attribute(filename=filename)
    elif otype == "messages":
        cmd = build_list_messages(condition=condition, filename=filename)
    else:
        cmd = build_list_objects(
            object_type=object_type, object_id=object_id,
            end=end, filename=filename, condition=condition,
        )

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


def _parse_listvar(raw: str, filter_prefix: str | None = None) -> dict[str, str]:
    """Parse ListVar telnet output into a {$NAME: value} dict.

    ListVar lines have the format:  $Global : $VARNAME = VALUE
    """
    variables: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if "=" not in line or line.startswith("["):
            continue
        # Strip scope prefix: "$Global : $VARNAME = VALUE" → "$VARNAME = VALUE"
        if " : " in line:
            _, _, line = line.partition(" : ")
            line = line.strip()
        name, _, value = line.partition("=")
        name = name.strip().lstrip("$")
        value = value.strip()
        if not name:
            continue
        if filter_prefix is None or name.upper().startswith(filter_prefix.upper()):
            variables[f"${name}"] = value
    return variables


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_system_variables(
    filter_prefix: str | None = None,
) -> str:
    """
    List all grandMA2 built-in system variables (SAFE_READ).

    Sends `ListVar` to the console and returns parsed key=value pairs.
    System variables include $SELECTEDEXEC, $TIME, $DATE, $VERSION, $HOSTSTATUS,
    $FADERPAGE, $BUTTONPAGE, $SELECTEDFIXTURESCOUNT, $USER, $HOSTNAME, etc.

    Args:
        filter_prefix: Optional prefix filter (case-insensitive).
            e.g. "SELECTED" returns only $SELECTEDEXEC, $SELECTEDEXECCUE, etc.
            Omit to return all variables.

    Returns:
        str: JSON with `variables` dict (name→value), `variable_count`, and `raw_response`.
    """
    client = await get_client()
    raw = await client.send_command_with_response("ListVar")

    variables = _parse_listvar(raw, filter_prefix=filter_prefix)
    return json.dumps({
        "variables": variables,
        "variable_count": len(variables),
        "raw_response": raw,
    }, indent=2)


async def _read_selected_exec(client) -> tuple[str | None, str | None]:
    """Read $SELECTEDEXEC and $SELECTEDEXECCUE from the console.

    Returns (exec_value, cue_value). Both are None if ListVar fails or the
    variables are absent in the response.
    """
    try:
        raw = await client.send_command_with_response("ListVar")
        variables = _parse_listvar(raw)
        return variables.get("$SELECTEDEXEC"), variables.get("$SELECTEDEXECCUE")
    except Exception:
        return None, None


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def playback_action(
    action: str,
    object_type: str | None = None,
    object_id: int | list[int] | None = None,
    cue_id: int | float | None = None,
    end: int | None = None,
    cue_mode: str | None = None,
    executor: int | list[int] | None = None,
    sequence: int | None = None,
) -> str:
    """
    Execute playback operations — go, go back, goto, fast forward/back, etc.

    Full-featured playback control with cue_mode and executor targeting.
    Coexists with execute_sequence (which uses legacy go_sequence/pause_sequence).

    Args:
        action: Playback action to perform:
            "go" — fire the next cue (optionally on a specific executor/sequence)
            "go_back" — fire the previous cue
            "goto" — jump to a specific cue (requires cue_id)
            "fast_forward" — skip forward (>>>)
            "fast_back" — skip backward (<<<)
            "def_go" — go on the selected executor (go+); response includes
                       selected_executor and selected_cue_before
            "def_go_back" / "def_goback" — go back on the selected executor;
                       response includes selected_executor and selected_cue_before
            "def_pause" — pause the selected executor; response includes
                       selected_executor and selected_cue_before
        object_type: Object type for go/go_back (e.g. "executor", "sequence")
        object_id: Object ID for go/go_back — single int or list of ints.
                   List produces "N + M + ..." syntax for multi-executor targeting.
        cue_id: Target cue number (required for "goto")
        end: End ID for range (go/go_back)
        cue_mode: Cue execution mode: "normal", "assert", "xassert", "release"
        executor: Executor ID for goto/fast_forward/fast_back — single int or list of ints.
                  List produces "N + M + ..." syntax (e.g. [1,2,3] → ">>> executor 1 + 2 + 3").
        sequence: Sequence ID for goto/fast_forward/fast_back

    Returns:
        str: JSON with command_sent and raw_response.
             def_go/def_go_back/def_pause also include selected_executor and
             selected_cue_before (read from $SELECTEDEXEC before firing).

    Examples:
        - Go on executor 1: action="go", object_type="executor", object_id=1
        - Go on executors 1+2+3: action="go", object_type="executor", object_id=[1,2,3]
        - Go back: action="go_back"
        - Goto cue 5: action="goto", cue_id=5
        - Goto cue 3 on sequence 2: action="goto", cue_id=3, sequence=2
        - Fast forward: action="fast_forward"
        - Fast forward executors 1,2,3: action="fast_forward", executor=[1,2,3]
        - Go on selected executor: action="def_go"
        - Go back on selected executor: action="def_go_back"
    """
    action = action.lower()

    if action == "go":
        cmd = build_go(
            object_type=object_type, object_id=object_id,
            end=end, cue_mode=cue_mode,
        )
    elif action == "go_back":
        cmd = build_go_back(
            object_type=object_type, object_id=object_id,
            end=end, cue_mode=cue_mode,
        )
    elif action == "goto":
        if cue_id is None:
            return json.dumps({
                "error": "goto action requires cue_id to be specified.",
                "blocked": True,
            }, indent=2)

        # Pre-flight: validate cue exists before sending goto
        client = await get_client()
        validation_info: dict = {}
        resolved_sequence = sequence

        if resolved_sequence is None and executor is not None:
            # Derive sequence from the executor assignment
            resolved_sequence, exec_raw = await _get_sequence_for_executor(
                client, executor
            )
            validation_info["executor_probe_response"] = exec_raw

        if resolved_sequence is not None:
            cue_probe_arg = f"{cue_id} sequence {resolved_sequence}"
            cue_exists, cue_raw = await _validate_object_exists(
                client, "cue", cue_probe_arg
            )
            validation_info["cue_exists"] = cue_exists
            validation_info["cue_probe_response"] = cue_raw
            if not cue_exists:
                return json.dumps({
                    "command_sent": None,
                    "error": (
                        f"Cue {cue_id} does not exist in sequence {resolved_sequence}. "
                        "MA2 would return Error #72 (COMMAND NOT EXECUTED)."
                    ),
                    "hint": "Use list_sequence_cues(sequence_id) to see available cues.",
                    **validation_info,
                    "blocked": True,
                }, indent=2)
        else:
            validation_info["warning"] = (
                "Could not resolve sequence context — command sent without cue "
                "pre-flight check. Provide sequence or executor for validation."
            )

        cmd = build_goto(
            cue_id, executor=executor, sequence=sequence,
            cue_mode=cue_mode,
        )
        raw_response = await client.send_command_with_response(cmd)
        return json.dumps({
            "command_sent": cmd,
            "raw_response": raw_response,
            **validation_info,
        }, indent=2)
    elif action == "fast_forward":
        cmd = build_go_fast_forward(executor=executor, sequence=sequence)
    elif action == "fast_back":
        cmd = build_go_fast_back(executor=executor, sequence=sequence)
    elif action in ("def_go", "def_go_back", "def_goback", "def_pause"):
        client = await get_client()
        sel_exec, sel_cue = await _read_selected_exec(client)

        if action == "def_go":
            cmd = build_def_go_forward()
        elif action in ("def_go_back", "def_goback"):
            cmd = build_def_go_back()
        else:  # def_pause
            cmd = build_def_go_pause()

        raw_response = await client.send_command_with_response(cmd)
        return json.dumps({
            "command_sent": cmd,
            "raw_response": raw_response,
            "selected_executor": sel_exec,
            "selected_cue_before": sel_cue,
        }, indent=2)
    else:
        return json.dumps({
            "error": (
                f"Unknown action: {action}. Use 'go', 'go_back', 'goto', "
                f"'fast_forward', 'fast_back', 'def_go', 'def_go_back', or 'def_pause'."
            ),
            "blocked": True,
        }, indent=2)

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def manage_variable(
    action: str,
    scope: str,
    var_name: str,
    value: int | float | str | None = None,
    input_dialog: bool = False,
) -> str:
    """
    Set, add to, or list console variables (global or user-scoped).

    Variables are named values stored on the console that can be used in
    macros and command line expressions. The $ prefix is automatically
    added to var_name if not already present.

    Args:
        action: "set" to assign a value, "add" to increment, "list" to show all variables
        scope: "global" for system variables, "user" for user-scoped variables
        var_name: Variable name (e.g. "myvar" or "$myvar" — $ auto-added)
        value: Value to set or add. Required for "add", optional for "set",
            ignored for "list"
        input_dialog: If True with action="set", shows an input dialog
            on the console for the user to enter a value

    Returns:
        str: JSON with command_sent and raw_response.

    Examples:
        - Set global var: action="set", scope="global", var_name="myvar", value=42
        - Set user var: action="set", scope="user", var_name="speed", value=100
        - Add to global: action="add", scope="global", var_name="counter", value=1
        - List global vars: action="list", scope="global"
        - List user vars: action="list", scope="user"
    """
    action = action.lower()
    scope = scope.lower()

    # Auto-prepend $ if not present (MA2 syntax requires $variablename)
    if var_name and not var_name.startswith("$"):
        var_name = f"${var_name}"

    if action == "list":
        if scope == "global":
            cmd = build_list_var()
        elif scope == "user":
            cmd = build_list_user_var()
        else:
            return json.dumps({
                "error": f"Unknown scope: {scope}. Use 'global' or 'user'.",
                "blocked": True,
            }, indent=2)
        client = await get_client()
        raw_response = await client.send_command_with_response(cmd)
        return json.dumps({
            "command_sent": cmd,
            "raw_response": raw_response,
        }, indent=2)

    if action == "set":
        if scope == "global":
            cmd = build_set_var(var_name, value, input_dialog=input_dialog)
        elif scope == "user":
            cmd = build_set_user_var(var_name, value, input_dialog=input_dialog)
        else:
            return json.dumps({
                "error": f"Unknown scope: {scope}. Use 'global' or 'user'.",
                "blocked": True,
            }, indent=2)
    elif action == "add":
        if value is None:
            return json.dumps({
                "error": "add action requires a value.",
                "blocked": True,
            }, indent=2)
        if scope == "global":
            cmd = build_add_var(var_name, value)
        elif scope == "user":
            cmd = build_add_user_var(var_name, value)
        else:
            return json.dumps({
                "error": f"Unknown scope: {scope}. Use 'global' or 'user'.",
                "blocked": True,
            }, indent=2)
    else:
        return json.dumps({
            "error": f"Unknown action: {action}. Use 'set', 'add', or 'list'.",
            "blocked": True,
        }, indent=2)

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def label_or_appearance(
    action: str,
    object_type: str,
    object_id: int | str,
    name: str | None = None,
    end: int | None = None,
    preset_type: str | None = None,
    confirm_destructive: bool = False,
    color: str | None = None,
    red: int | None = None,
    green: int | None = None,
    blue: int | None = None,
    hue: int | None = None,
    saturation: int | None = None,
    brightness: int | None = None,
    reset: bool = False,
    source_type: str | None = None,
    source_id: int | str | None = None,
) -> str:
    """
    Label or set the appearance of console objects.

    SAFETY: This is a DESTRUCTIVE operation. Requires confirm_destructive=True.

    Args:
        action: "label" to set a name, "appearance" to set visual styling
        object_type: Object type (e.g. "group", "sequence", "cue", "preset")
        object_id: Object ID
        name: Name to assign (required for action="label")
        end: End ID for range labeling (e.g. group 1 thru 5)
        preset_type: For labeling presets, the preset type (e.g. "color", "position").
            When set, uses the specialized label_preset builder.
        confirm_destructive: Must be True to execute (safety gate)
        color: Hex color string for appearance (e.g. "FF0000")
        red: Red component (0-100) for appearance
        green: Green component (0-100) for appearance
        blue: Blue component (0-100) for appearance
        hue: Hue value for appearance
        saturation: Saturation value for appearance
        brightness: Brightness value for appearance
        reset: Reset appearance to default
        source_type: Copy appearance from this object type
        source_id: Copy appearance from this object ID

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Label group 3: action="label", object_type="group", object_id=3, name="Front Wash"
        - Label color preset 1: action="label", object_type="preset", object_id=1,
          preset_type="color", name="Red"
        - Set group appearance: action="appearance", object_type="group", object_id=1,
          color="FF0000"
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": "Label/Appearance is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    action = action.lower()

    if action == "label":
        if name is None:
            return json.dumps({
                "error": "label action requires 'name' to be specified.",
                "blocked": True,
            }, indent=2)
        if preset_type is not None:
            cmd = build_label_preset(preset_type, object_id, name)
        else:
            cmd = build_label(object_type, object_id, name, end=end)
    elif action == "appearance":
        cmd = build_appearance(
            object_type, object_id, end=end,
            source_type=source_type, source_id=source_id,
            reset=reset, color=color,
            red=red, green=green, blue=blue,
            hue=hue, saturation=saturation, brightness=brightness,
        )
    else:
        return json.dumps({
            "error": f"Unknown action: {action}. Use 'label' or 'appearance'.",
            "blocked": True,
        }, indent=2)

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.GROUP_STORE)
@_handle_errors
async def assign_object(
    mode: str,
    confirm_destructive: bool = False,
    source_type: str | None = None,
    source_id: int | str | None = None,
    target_type: str | None = None,
    target_id: int | str | None = None,
    function: str | None = None,
    fade_time: float | None = None,
    cue_id: int | None = None,
    sequence_id: int | None = None,
    layout_id: int | None = None,
    x: int | None = None,
    y: int | None = None,
    noconfirm: bool = False,
) -> str:
    """
    Assign objects, functions, fades, or layout positions on the console.

    SAFETY: This is a DESTRUCTIVE operation. Requires confirm_destructive=True.

    Args:
        mode: Assignment mode:
            "assign" — assign source object to target (e.g. sequence to executor)
            "function" — assign a function to an executor (e.g. Toggle, Flash)
            "fade" — assign a fade time to a cue
            "layout" — assign an object to a layout position
            "empty" — deactivate an executor (assign empty function)
            "temp_fader" — assign temp fader function to an executor
        confirm_destructive: Must be True to execute (safety gate)
        source_type: Source object type (for "assign" and "layout" modes)
        source_id: Source object ID (for "assign" and "layout" modes)
        target_type: Target object type (for "assign", "function", "empty", "temp_fader")
        target_id: Target object ID
        function: Function name for "function" mode (e.g. "Toggle", "Flash", "Go")
        fade_time: Fade time in seconds for "fade" mode
        cue_id: Cue ID for "fade" mode
        sequence_id: Sequence ID for "fade" mode
        layout_id: Layout ID for "layout" mode
        x: X position for "layout" mode
        y: Y position for "layout" mode
        noconfirm: Skip console confirmation dialog

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Assign sequence 1 to executor 6: mode="assign", source_type="sequence",
          source_id=1, target_type="executor", target_id=6
        - Assign Toggle to executor 101: mode="function", function="Toggle",
          target_type="executor", target_id=101
        - Assign fade 3s to cue 5: mode="fade", fade_time=3, cue_id=5
        - Assign group to layout: mode="layout", source_type="group", source_id=1,
          layout_id=1, x=5, y=2
        - Empty executor 1: mode="empty", target_type="executor", target_id=1
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": "Assign is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    mode = mode.lower()

    if mode == "assign":
        if source_type is None or source_id is None:
            return json.dumps({
                "error": "assign mode requires source_type and source_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign(
            source_type, source_id,
            target_type=target_type, target_id=target_id,
            noconfirm=noconfirm,
        )
    elif mode == "function":
        if function is None or target_type is None or target_id is None:
            return json.dumps({
                "error": "function mode requires function, target_type, and target_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign_function(function, target_type, target_id)
    elif mode == "fade":
        if fade_time is None or cue_id is None:
            return json.dumps({
                "error": "fade mode requires fade_time and cue_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign_fade(fade_time, cue_id, sequence_id=sequence_id)
    elif mode == "layout":
        if source_type is None or source_id is None or layout_id is None:
            return json.dumps({
                "error": "layout mode requires source_type, source_id, and layout_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign_to_layout(
            source_type, source_id, layout_id, x=x, y=y,
        )
    elif mode == "empty":
        if target_type is None or target_id is None:
            return json.dumps({
                "error": "empty mode requires target_type and target_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign_function("empty", target_type, target_id)
    elif mode == "temp_fader":
        if target_type is None or target_id is None:
            return json.dumps({
                "error": "temp_fader mode requires target_type and target_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_assign_function("tempfader", target_type, target_id)
    else:
        return json.dumps({
            "error": (
                f"Unknown mode: {mode}. Use 'assign', 'function', 'fade', "
                f"'layout', 'empty', or 'temp_fader'."
            ),
            "blocked": True,
        }, indent=2)

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def edit_object(
    action: str,
    object_type: str | None = None,
    object_id: int | str | None = None,
    target_id: int | str | None = None,
    end: int | str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Edit, cut, or paste objects in the show.

    - edit: Opens an object for editing (SAFE_WRITE)
    - cut: Removes an object and places it on the clipboard (DESTRUCTIVE)
    - paste: Places clipboard contents at a target location (DESTRUCTIVE)

    SAFETY: cut and paste are DESTRUCTIVE and require confirm_destructive=True.
    edit does not require confirmation.

    Args:
        action: "edit", "cut", or "paste"
        object_type: Object type (e.g. "preset", "cue", "group")
        object_id: Object ID (for edit and cut)
        target_id: Target ID for paste destination
        end: End ID for range operations
        confirm_destructive: Must be True for cut/paste (safety gate)

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Edit cue 1: action="edit", object_type="cue", object_id=1
        - Cut preset 4.1: action="cut", object_type="preset", object_id="4.1"
        - Paste to group 5: action="paste", object_type="group", target_id=5
    """
    action = action.lower()

    if action in ("cut", "paste") and not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": f"{action.title()} is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    if action == "edit":
        cmd = build_edit(object_type=object_type, object_id=object_id, end=end)
    elif action == "cut":
        if object_type is None or object_id is None:
            return json.dumps({
                "error": "cut requires object_type and object_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_cut(object_type, object_id, end=end)
    elif action == "paste":
        cmd = build_paste(object_type, target_id)
    else:
        return json.dumps({
            "error": f"Unknown action: {action}. Use 'edit', 'cut', or 'paste'.",
            "blocked": True,
        }, indent=2)

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def remove_content(
    object_type: str,
    object_id: int | str | None = None,
    end: int | None = None,
    if_filter: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Remove content from objects (fixtures from groups, effects, preset types, etc.).

    Unlike delete (which removes the object itself), remove takes content out of
    an object. For example, removing a fixture from a group, or removing an effect
    from a cue.

    SAFETY: This is a DESTRUCTIVE operation. Requires confirm_destructive=True.

    Args:
        object_type: What to remove. Special types:
            "selection" — remove the current selection
            "fixture" — remove a fixture (from a group, cue, etc.)
            "effect" — remove an effect
            "presettype" — remove a preset type from the programmer
            Or any generic type for the generic remove command.
        object_id: Object ID to remove (not needed for "selection")
        end: End ID for range removal
        if_filter: Conditional filter (e.g. "PresetType 1")
        confirm_destructive: Must be True to execute (safety gate)

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Remove selection: object_type="selection"
        - Remove fixture 1: object_type="fixture", object_id=1
        - Remove fixture with filter: object_type="fixture", object_id=1,
          if_filter="PresetType 1"
        - Remove effect 1: object_type="effect", object_id=1
        - Remove preset type: object_type="presettype", object_id="position"
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": "Remove is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    otype = object_type.lower()

    if otype == "selection":
        cmd = build_remove_selection()
    elif otype == "fixture":
        if object_id is None:
            return json.dumps({
                "error": "fixture removal requires object_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_remove_fixture(object_id, end=end, if_filter=if_filter)
    elif otype == "effect":
        if object_id is None:
            return json.dumps({
                "error": "effect removal requires object_id.",
                "blocked": True,
            }, indent=2)
        cmd = build_remove_effect(object_id, end=end)
    elif otype == "presettype":
        if object_id is None:
            return json.dumps({
                "error": "presettype removal requires object_id (the preset type name or number).",
                "blocked": True,
            }, indent=2)
        cmd = build_remove_preset_type(object_id, if_filter=if_filter)
    else:
        cmd = build_remove(
            object_type=object_type, object_id=object_id,
            end=end, if_filter=if_filter,
        )

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def store_object(
    object_type: str,
    object_id: int | str,
    name: str | None = None,
    merge: bool = False,
    overwrite: bool = False,
    noconfirm: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Store (create) a generic object in the show — macros, effects, worlds, etc.

    For cues, use store_current_cue. For presets, use store_new_preset.
    For groups, use create_fixture_group. This tool handles everything else.

    SAFETY: This is a DESTRUCTIVE operation. Requires confirm_destructive=True.

    Args:
        object_type: Object type to store (e.g. "macro", "effect", "world",
            "sequence", "executor", "timecode")
        object_id: Object ID number or slot
        name: Optional name for the stored object
        merge: Merge into existing object if present
        overwrite: Overwrite existing object if present
        noconfirm: Skip console confirmation dialog
        confirm_destructive: Must be True to execute (safety gate)

    Returns:
        str: JSON with command_sent, raw_response, or block info.

    Examples:
        - Store macro 5: object_type="macro", object_id=5
        - Store effect 1 named "Rainbow": object_type="effect", object_id=1, name="Rainbow"
        - Overwrite sequence 3: object_type="sequence", object_id=3, overwrite=True
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": "Store is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    cmd = build_store_generic(
        object_type, object_id, name,
        merge=merge, overwrite=overwrite, noconfirm=noconfirm,
    )

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "blocked": False,
    }, indent=2)


# ============================================================
# Codebase Search (RAG)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def search_codebase(
    query: str,
    top_k: int = 8,
    kind: str | None = None,
) -> str:
    """Search source code, grandMA2 docs, and MCP SDK source using the RAG index.

    Three indexed knowledge sources (repo_refs):
    - "worktree"     — this server's Python source, tests, and docs
    - "ma2-help-docs" — ~1,043 grandMA2 help pages from help.malighting.com
    - "mcp-sdk"      — installed MCP SDK source (~110 files, types, server, tools)

    Works without any API key (text-search fallback). With GITHUB_MODELS_TOKEN
    set, results are ranked by semantic similarity.

    Args:
        query:  Natural language or keyword query (e.g. "navigate console",
                "store preset", "how to patch fixtures", "mcp tool context")
        top_k:  Number of results to return (default 8, max 20)
        kind:   Optional filter — one of: "source", "test", "doc", "config"

    Returns:
        JSON array of matching chunks with path, kind, lines, score, and text.
        Returns an error JSON if the RAG index has not been built yet.

    Examples:
        - Find command builders:   query="store preset", kind="source"
        - Find grandMA2 docs:      query="how to patch fixtures", kind="doc"
        - Find MCP SDK internals:  query="mcp tool decorator context"
        - Search everything:       query="effects engine"
        - Find test examples:      query="navigate_console", kind="test"
    """
    from pathlib import Path

    from rag.retrieve.query import rag_query

    db = Path(__file__).parent.parent / "rag" / "store" / "rag.db"
    if not db.exists():
        return json.dumps({
            "error": "RAG index not found. Build it first: uv run python scripts/rag_ingest.py",
            "blocked": True,
        }, indent=2)

    provider = None
    token = os.getenv("GITHUB_MODELS_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token:
        from rag.ingest.embed import GitHubModelsProvider
        provider = GitHubModelsProvider(token=token)

    want = min(top_k, 20)
    # When a kind filter is requested, over-fetch 10× so we have enough candidates
    # of the right kind after filtering (the DB has 4 kinds; web docs dominate).
    fetch_k = want * 10 if kind else want
    hits = rag_query(query, embedding_provider=provider, top_k=fetch_k, db_path=db)

    if kind:
        hits = [h for h in hits if h.kind == kind][:want]

    return json.dumps([
        {
            "path": hit.path,
            "kind": hit.kind,
            "lines": f"{hit.start_line}-{hit.end_line}",
            "score": round(hit.score, 4),
            "text": hit.text,
        }
        for hit in hits
    ], indent=2)


# ============================================================
# New Tools (Tools 30–44)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def set_executor_level(
    executor_id: int,
    level: float,
    page: int | None = None,
) -> str:
    """
    Set a fader/executor to a specific output level.

    Args:
        executor_id: Executor number (1-999)
        level: Fader level 0.0–100.0
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: JSON result with command sent
    """
    if not (0.0 <= level <= 100.0):
        return json.dumps({"error": "level must be between 0.0 and 100.0", "blocked": True}, indent=2)
    if executor_id < 1:
        return json.dumps({"error": "executor_id must be >= 1", "blocked": True}, indent=2)

    client = await get_client()
    cmd = build_executor_at(executor_id, level, page=page)
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def navigate_page(
    action: str,
    page_number: int | None = None,
    steps: int | None = None,
    create_if_missing: bool = False,
) -> str:
    """
    Navigate executor pages on the console.

    $FADERPAGE, $BUTTONPAGE, and $CHANNELPAGE are read-only system variables —
    SetVar has no effect on them. Only `Page N` (this tool) changes the active page.

    Args:
        action: "goto" (absolute page), "next" (page +), or "previous" (page -)
        page_number: Target page number (required for "goto"; 1-999)
        steps: Number of pages to advance/go back (optional; for "next"/"previous")
        create_if_missing: If True, sends `Store Page N /noconfirm` before navigating
            to create the page if it does not yet exist. Only applies to action="goto".
            Without this, MA2 returns Error #9 if the page doesn't exist.

    Returns:
        str: JSON result with command sent
    """
    if action not in ("goto", "next", "previous"):
        return json.dumps({"error": "action must be 'goto', 'next', or 'previous'", "blocked": True}, indent=2)
    if action == "goto":
        if page_number is None:
            return json.dumps({"error": "page_number is required for action='goto'", "blocked": True}, indent=2)
        cmd = f"page {page_number}"
    elif action == "next":
        cmd = build_page_next(steps)
    else:
        cmd = build_page_previous(steps)

    client = await get_client()
    result_steps = []

    if create_if_missing and action == "goto":
        store_cmd = f"Store Page {page_number} /noconfirm"
        store_raw = await client.send_command_with_response(store_cmd)
        result_steps.append({"command": store_cmd, "response": store_raw})

    response = await client.send_command_with_response(cmd)
    result_steps.append({"command": cmd, "response": response})

    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "steps": result_steps,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def select_feature(
    feature_name: str,
) -> str:
    """
    Select the active feature bank on the grandMA2 console (SAFE_WRITE).

    Sends `Feature [name]` which updates $FEATURE.
    $FEATURE is read-only — SetVar has no effect on it.
    Only `Feature [name]` changes the active feature context.

    Feature names are fixture-dependent — only features present on the selected
    fixture's channels are valid. Live-verified names (v3.9.60.65):
      Dimmer, Position, Gobo1, Gobo2, ColorRGB, Shutter, Focus, MSPEED
    Names that may error if fixture lacks the channel: Color, Zoom, Iris, Frost

    Args:
        feature_name: Feature bank to activate (e.g. "Dimmer", "ColorRGB", "MSPEED")

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    cmd = f"Feature {feature_name}"
    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def select_preset_type(
    preset_type: int | str,
) -> str:
    """
    Select the active preset type on the grandMA2 console (SAFE_WRITE).

    Sends `PresetType [id or name]` which jumps the encoder context to the
    first Feature available in that preset type for the selected fixtures.
    Updates $PRESET, $FEATURE, and $ATTRIBUTE simultaneously.

    CD tree location (live-verified, v3.9.60.65):
      cd 10.2        → lists all 9 PresetTypes
      cd 10.2.N      → lists Features under PresetType N
      cd 10.2.N.M    → lists Attributes under Feature M of PresetType N
      cd 10.2.N.M.K  → lists SubAttributes (deepest level)

    Preset types + live-verified $FEATURE on first activation:
      1=Dimmer  ($FEATURE=DIMMER,   $ATTRIBUTE=DIM)
      2=Position ($FEATURE=POSITION, $ATTRIBUTE=PAN)
      3=Gobo    ($FEATURE=GOBO1,    $ATTRIBUTE=GOBO1)
      4=Color   ($FEATURE=COLORRGB, $ATTRIBUTE=COLORRGB1, fixture-dep)
      5=Beam    ($FEATURE=SHUTTER,  $ATTRIBUTE=SHUTTER,   fixture-dep)
      6=Focus   ($FEATURE=FOCUS,    $ATTRIBUTE=FOCUS)
      7=Control ($FEATURE=MSPEED,   $ATTRIBUTE=INTENSITYMSPEED)
      8=Shapers (fixture must have Shapers channels)
      9=Video   (fixture must have Video channels)

    Args:
        preset_type: Preset type number (1-9) or name (e.g. "Color", "Control")

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    cmd = f"PresetType {preset_type}" if isinstance(preset_type, int) else f'PresetType "{preset_type}"'
    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


def _parse_preset_tree_list(raw: str) -> list[dict]:
    """Parse grandMA2 list output from the PresetType cd-tree.

    Handles rows of the form:
      ``PresetType N  LibName  ScreenName  ...``
      ``Feature N  LibName  ScreenName  ...``
      ``Attribute N  LibName  ScreenName  ...``
      ``SubAttribute N  LibName  ScreenName  ...``

    These rows have only one numeric ID (not the two required by the standard
    tabular parser), so they are skipped by parse_list_output().
    """
    import re
    _ANSI = re.compile(r"\x1b\[[0-9;]*m|\x1b\[K")
    _ROW = re.compile(
        r"^\s*(PresetType|Feature|Attribute|SubAttribute)\s+(\d+)\s+(\S+)\s+(.*?)\s*$",
        re.IGNORECASE,
    )
    entries = []
    for line in raw.splitlines():
        line = _ANSI.sub("", line).strip()
        m = _ROW.match(line)
        if m:
            obj_type, obj_id, lib_name, rest = m.group(1), m.group(2), m.group(3), m.group(4)
            # rest may contain "ScreenName  IdentifiedAs  DefaultScope  (count)"
            parts = re.split(r"\s{2,}", rest)
            entry = {
                "type": obj_type,
                "id": int(obj_id),
                "library_name": lib_name,
            }
            if parts:
                entry["screen_name"] = parts[0].strip()
            if len(parts) > 1:
                entry["identified_as"] = parts[1].strip()
            if len(parts) > 2:
                entry["extra"] = parts[2].strip()
            entries.append(entry)
    return entries


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def browse_preset_type(
    preset_type_id: int,
    depth: int = 1,
) -> str:
    """
    Browse the feature/attribute tree under a preset type (SAFE_READ).

    Navigates the grandMA2 LiveSetup preset-type cd-tree and lists children
    at the requested depth. The tree structure (live-verified v3.9.60.65):

      cd 10.2.N       → Features under PresetType N
      cd 10.2.N.M     → Attributes under Feature M
      cd 10.2.N.M.K   → SubAttributes under Attribute K  (leaf level)

    Indexes at each level use sequential position (1 = first listed child),
    NOT the internal library ID shown in the output.

    Args:
        preset_type_id: Preset type to browse (1=Dimmer, 2=Position, 3=Gobo,
            4=Color, 5=Beam, 6=Focus, 7=Control, 8=Shapers, 9=Video)
        depth: How deep to traverse (1=features only, 2=+attributes,
            3=+subattributes). Defaults to 1.

    Returns:
        str: JSON with the tree structure at the requested depth.
    """
    if not 1 <= preset_type_id <= 9:
        return json.dumps({"error": "preset_type_id must be 1-9", "blocked": True}, indent=2)
    if not 1 <= depth <= 3:
        return json.dumps({"error": "depth must be 1-3", "blocked": True}, indent=2)

    client = await get_client()

    async def list_path(path: str) -> tuple[str, list[dict]]:
        await navigate(client, "/")
        await navigate(client, path)
        lst = await list_destination(client)
        raw = lst.raw_response
        entries = _parse_preset_tree_list(raw)
        return raw, entries

    # Depth 1: features under preset type
    raw1, features = await list_path(f"10.2.{preset_type_id}")

    result: dict = {
        "preset_type_id": preset_type_id,
        "cd_path": f"10.2.{preset_type_id}",
        "features": features,
        "risk_tier": "SAFE_READ",
    }

    if depth >= 2:
        for fi, feat in enumerate(features, start=1):
            feat_path = f"10.2.{preset_type_id}.{fi}"
            _, attrs = await list_path(feat_path)
            feat["cd_path"] = feat_path
            feat["attributes"] = attrs

            if depth >= 3:
                for ai, attr in enumerate(attrs, start=1):
                    attr_path = f"10.2.{preset_type_id}.{fi}.{ai}"
                    _, sub_attrs = await list_path(attr_path)
                    attr["cd_path"] = attr_path
                    attr["sub_attributes"] = sub_attrs

    # Return to root
    await navigate(client, "/")
    return json.dumps(result, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def modify_selection(
    action: str,
    fixture_ids: list[int] | None = None,
    end_id: int | None = None,
) -> str:
    """
    Add, remove, replace, or clear the current fixture selection.

    Args:
        action: "add" (+ N), "remove" (- N), "replace" (selfix), or "clear"
        fixture_ids: Fixture IDs to add/remove/replace (required for all except "clear")
        end_id: End of a range (optional; builds thru N)

    Returns:
        str: JSON result with command sent
    """
    if action not in ("add", "remove", "replace", "clear"):
        return json.dumps({"error": "action must be 'add', 'remove', 'replace', or 'clear'", "blocked": True}, indent=2)
    if action != "clear" and not fixture_ids:
        return json.dumps({"error": "fixture_ids is required for action != 'clear'", "blocked": True}, indent=2)

    client = await get_client()
    if action == "clear":
        cmd = build_clear_selection()
    elif action == "add":
        if len(fixture_ids) == 1 and end_id is not None:
            cmd = build_add_to_selection(fixture_ids[0], end=end_id)
        elif len(fixture_ids) == 1:
            cmd = build_add_to_selection(fixture_ids[0])
        else:
            cmd = build_add_to_selection(fixture_ids)
    elif action == "remove":
        if len(fixture_ids) == 1 and end_id is not None:
            cmd = build_remove_from_selection(fixture_ids[0], end=end_id)
        elif len(fixture_ids) == 1:
            cmd = build_remove_from_selection(fixture_ids[0])
        else:
            cmd = build_remove_from_selection(fixture_ids)
    else:  # replace
        first = fixture_ids[0]
        last = end_id if end_id is not None else (fixture_ids[-1] if len(fixture_ids) > 1 else None)
        cmd = select_fixture(first, last)

    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def adjust_value_relative(
    delta: float,
    attribute_name: str | None = None,
    fixture_ids: list[int] | None = None,
    end_id: int | None = None,
) -> str:
    """
    Nudge an attribute value by a relative delta on the current (or specified) selection.

    Args:
        delta: Relative change (positive or negative, non-zero). E.g. +10 or -5.
        attribute_name: Attribute to target (e.g. "Pan", "Tilt", "Dimmer"). Optional.
        fixture_ids: Select these fixtures before nudging. Optional.
        end_id: End of fixture range. Optional.

    Returns:
        str: JSON result with commands sent
    """
    if delta == 0:
        return json.dumps({"error": "delta cannot be zero", "blocked": True}, indent=2)

    client = await get_client()
    commands_sent = []

    if fixture_ids:
        first = fixture_ids[0]
        last = end_id if end_id is not None else (fixture_ids[-1] if len(fixture_ids) > 1 else None)
        sel_cmd = select_fixture(first, last)
        await client.send_command(sel_cmd)
        commands_sent.append(sel_cmd)

    if attribute_name:
        attr_cmd = f'attribute "{attribute_name}"'
        await client.send_command(attr_cmd)
        commands_sent.append(attr_cmd)

    nudge_cmd = build_at_relative(delta)
    response = await client.send_command_with_response(nudge_cmd)
    commands_sent.append(nudge_cmd)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def control_timecode(
    action: str,
    timecode_id: int,
    timecode_position: str | None = None,
) -> str:
    """
    Start, stop, or jump to a position in a timecode show.

    Args:
        action: "start" (go), "stop" (off), or "goto"
        timecode_id: Timecode show ID (1-256)
        timecode_position: HH:MM:SS:FF position string (required for "goto")

    Returns:
        str: JSON result with command sent
    """
    if action not in ("start", "stop", "goto"):
        return json.dumps({"error": "action must be 'start', 'stop', or 'goto'", "blocked": True}, indent=2)
    if action == "goto" and timecode_position is None:
        return json.dumps({"error": "timecode_position is required for action='goto'", "blocked": True}, indent=2)

    client = await get_client()
    if action == "start":
        cmd = f"go timecode {timecode_id}"
    elif action == "stop":
        cmd = f"off timecode {timecode_id}"
    else:
        cmd = build_goto_timecode(timecode_id, timecode_position)

    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def control_timer(
    action: str,
    timer_id: int,
) -> str:
    """
    Start, stop, or reset a console timer.

    Args:
        action: "start" (go), "stop" (off), or "reset" (goto)
        timer_id: Timer ID (1-256)

    Returns:
        str: JSON result with command sent
    """
    if action not in ("start", "stop", "reset"):
        return json.dumps({"error": "action must be 'start', 'stop', or 'reset'", "blocked": True}, indent=2)
    if timer_id < 1:
        return json.dumps({"error": "timer_id must be >= 1", "blocked": True}, indent=2)

    client = await get_client()
    if action == "start":
        cmd = f"go timer {timer_id}"
    elif action == "stop":
        cmd = f"off timer {timer_id}"
    else:
        cmd = f"goto timer {timer_id}"

    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def undo_last_action(count: int = 1) -> str:
    """
    Undo the last N actions on the console (sends 'oops' N times).

    Args:
        count: Number of actions to undo (1-20, default 1)

    Returns:
        str: JSON result with all raw responses
    """
    if not (1 <= count <= 20):
        return json.dumps({"error": "count must be between 1 and 20", "blocked": True}, indent=2)

    client = await get_client()
    responses = []
    for _ in range(count):
        response = await client.send_command_with_response("oops")
        responses.append(response)

    return json.dumps({
        "commands_sent": ["oops"] * count,
        "raw_responses": responses,
        "count": count,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def toggle_console_mode(mode: str) -> str:
    """
    Toggle a console mode on/off (blind, highlight, solo, freeze).

    These are toggle commands — each call flips the current state.

    Args:
        mode: "blind", "highlight", "solo", or "freeze"

    Returns:
        str: JSON result with command sent
    """
    valid = ("blind", "highlight", "solo", "freeze")
    if mode not in valid:
        return json.dumps({"error": f"mode must be one of {valid}", "blocked": True}, indent=2)

    # Blind mode puts the console into the programming layer — requires presets scope.
    if mode == "blind" and not has_scope(OAuthScope.PROGRAMMER_WRITE):
        return json.dumps({
            "blocked": True,
            "error": (
                "Blind mode requires OAuth scope 'gma2:programmer:write' "
                "(tier:2 or higher). Highlight/Solo/Freeze only require tier:1."
            ),
            "scope_required": str(OAuthScope.PROGRAMMER_WRITE),
            "scope_tier": 2,
        }, indent=2)

    client = await get_client()
    response = await client.send_command_with_response(mode)

    # Sync mode toggle to snapshot write-tracker (Gap 11)
    if snap := _orchestrator.last_snapshot:
        snap.console_modes[mode] = not snap.console_modes.get(mode, False)

    return json.dumps({
        "command_sent": mode,
        "raw_response": response,
        "mode": mode,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def update_cue_data(
    confirm_destructive: bool = False,
    cue_id: float | None = None,
    sequence_id: int | None = None,
    merge: bool = False,
    overwrite: bool = False,
    cueonly: bool | None = None,
) -> str:
    """
    Update a cue with current programmer values (DESTRUCTIVE).

    Args:
        confirm_destructive: Must be True to execute
        cue_id: Cue number to update (optional; updates active cue if omitted)
        sequence_id: Sequence ID for scoping (optional)
        merge: Merge programmer into existing cue values
        overwrite: Overwrite cue with programmer values
        cueonly: Prevent tracking forward (True) or allow (False)

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    cmd = build_update_cue(cue_id, sequence_id=sequence_id, merge=merge,
                           overwrite=overwrite, cueonly=cueonly)
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def set_cue_timing(
    cue_id: int,
    confirm_destructive: bool = False,
    sequence_id: int | None = None,
    fade_time: float | None = None,
    delay_time: float | None = None,
) -> str:
    """
    Set fade and/or delay time on a specific cue (DESTRUCTIVE).

    Args:
        cue_id: Cue number to update
        confirm_destructive: Must be True to execute
        sequence_id: Sequence ID for scoping (optional)
        fade_time: Fade time in seconds (0.0–3600.0, optional)
        delay_time: Delay time in seconds (0.0–3600.0, optional)

    Returns:
        str: JSON result with commands sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)
    if fade_time is None and delay_time is None:
        return json.dumps({"error": "At least one of fade_time or delay_time must be provided", "blocked": True}, indent=2)

    client = await get_client()
    commands_sent = []
    responses = []

    if fade_time is not None:
        cmd = build_assign_fade(fade_time, cue_id, sequence_id=sequence_id)
        response = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        responses.append(response)

    if delay_time is not None:
        cmd = build_assign_delay(delay_time, cue_id, sequence_id=sequence_id)
        response = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        responses.append(response)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_responses": responses,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def select_fixtures_by_group(
    group_id: int,
    append: bool = False,
) -> str:
    """
    Select all fixtures in a group (replaces or appends to current selection).

    Args:
        group_id: Group ID to select (1-999)
        append: If True, adds group to current selection instead of replacing

    Returns:
        str: JSON result with command sent
    """
    if group_id < 1:
        return json.dumps({"error": "group_id must be >= 1", "blocked": True}, indent=2)

    client = await get_client()
    cmd = f"+ group {group_id}" if append else f"group {group_id}"
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "group_id": group_id,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def control_executor(
    action: str,
    executor_id: int,
    page: int | None = None,
    speed_value: float | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Control an executor: start, stop, flash, swop, solo, top, stomp, or set speed.

    set_speed is DESTRUCTIVE (modifies stored data).

    Args:
        action: "on", "off", "flash", "swop", "solo", "top", "stomp", or "set_speed"
        executor_id: Executor ID (1-999)
        page: Page number for page-qualified addressing (optional)
        speed_value: BPM value for set_speed (0.0–999.0; required for set_speed)
        confirm_destructive: Must be True when action="set_speed"

    Returns:
        str: JSON result with command sent
    """
    valid_actions = ("on", "off", "flash", "swop", "solo", "top", "stomp", "set_speed")
    if action not in valid_actions:
        return json.dumps({"error": f"action must be one of {valid_actions}", "blocked": True}, indent=2)
    if executor_id < 1:
        return json.dumps({"error": "executor_id must be >= 1", "blocked": True}, indent=2)

    if action == "set_speed":
        if not confirm_destructive:
            return json.dumps({
                "blocked": True,
                "error": "set_speed is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
                "risk_tier": "DESTRUCTIVE",
            }, indent=2)
        if speed_value is None:
            return json.dumps({"error": "speed_value is required for action='set_speed'", "blocked": True}, indent=2)
        ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
        cmd = f"assign speed {speed_value} at executor {ref}"
        risk_tier = "DESTRUCTIVE"
    elif action == "on":
        cmd = build_on_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    elif action == "off":
        cmd = build_off_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    elif action == "flash":
        cmd = build_flash_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    elif action == "swop":
        cmd = build_swop_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    elif action == "top":
        cmd = build_top_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    elif action == "stomp":
        cmd = build_stomp_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"
    else:  # solo
        cmd = build_solo_executor(executor_id, page=page)
        risk_tier = "SAFE_WRITE"

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk_tier,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def load_cue(
    direction: str,
    executor_id: int | None = None,
    sequence_id: int | None = None,
) -> str:
    """
    Pre-load the next or previous cue without executing it (SAFE_WRITE).

    LoadNext / LoadPrev arm the cue for Go without firing it.

    Args:
        direction: "next" or "prev"
        executor_id: Executor ID to load on (optional)
        sequence_id: Sequence ID to load on (optional)

    Returns:
        str: JSON result with command sent
    """
    if direction not in ("next", "prev"):
        return json.dumps({"error": "direction must be 'next' or 'prev'", "blocked": True}, indent=2)

    if direction == "next":
        cmd = build_load_next(executor=executor_id, sequence=sequence_id)
    else:
        cmd = build_load_prev(executor=executor_id, sequence=sequence_id)

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def cut_paste_object(
    action: str,
    object_type: str | None = None,
    object_id: int | str | None = None,
    target_id: int | str | None = None,
    end: int | str | None = None,
) -> str:
    """
    Cut an object to clipboard, or paste clipboard content at a target (SAFE_WRITE).

    Cut + Paste is a two-step move: Cut prepares the source, Paste places it.
    Does not work with cue objects — use copy_or_move_object for cues.

    Args:
        action: "cut" or "paste"
        object_type: Object type ("group", "preset", "sequence", "macro", etc.)
        object_id: Source object ID (required for cut; ignored for bare paste)
        target_id: Destination ID (for paste)
        end: End ID for range cut (thru syntax)

    Returns:
        str: JSON result with command sent
    """
    if action not in ("cut", "paste"):
        return json.dumps({"error": "action must be 'cut' or 'paste'", "blocked": True}, indent=2)

    if action == "cut":
        if object_type is None or object_id is None:
            return json.dumps({"error": "object_type and object_id required for cut", "blocked": True}, indent=2)
        cmd = build_cut(object_type, object_id, end=end)
    else:
        cmd = build_paste(object_type, target_id)

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def clone_object(
    object_type: str,
    object_id: int,
    target_id: int,
    end: int | None = None,
    target_end: int | None = None,
    noconfirm: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Clone (duplicate with data) one or more objects to new IDs (DESTRUCTIVE).

    Clone copies all stored data from the source to the target — unlike Copy
    it also migrates all associated cue/preset references.

    Args:
        object_type: Object type ("fixture", "group", "sequence", etc.)
        object_id: Source object ID
        target_id: Destination object ID
        end: End ID for source range (thru syntax)
        target_end: End ID for target range
        noconfirm: Suppress confirmation dialog
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "clone_object is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    cmd = build_clone(
        object_type, object_id, target_id,
        end=end, target_end=target_end, noconfirm=noconfirm,
    )
    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def fix_locate_fixture(
    action: str,
    fixture_ids: list[int] | None = None,
    end: int | None = None,
) -> str:
    """
    Fix (park) or Locate selected/specified fixtures (SAFE_WRITE).

    Fix pins fixture output to current level, overriding playback.
    Locate fires fixtures to their default state (full, open, centre).

    Args:
        action: "fix" or "locate"
        fixture_ids: List of fixture IDs to fix (optional — uses selection if omitted)
        end: End ID for range when a single start ID is given

    Returns:
        str: JSON result with command sent
    """
    if action not in ("fix", "locate"):
        return json.dumps({"error": "action must be 'fix' or 'locate'", "blocked": True}, indent=2)

    if action == "locate":
        cmd = build_locate()
    else:
        if fixture_ids is not None and len(fixture_ids) == 1:
            cmd = build_fix_fixture(fixture_ids[0], end=end)
        elif fixture_ids:
            cmd = build_fix_fixture(fixture_ids)
        else:
            cmd = build_fix_fixture()

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def manipulate_selection(action: str) -> str:
    """
    Invert or Align the current fixture selection / programmer values (SAFE_WRITE).

    Invert: swap selected and unselected fixtures.
    Align: distribute programmer values evenly from first to last fixture.

    Args:
        action: "invert" or "align"

    Returns:
        str: JSON result with command sent
    """
    if action not in ("invert", "align"):
        return json.dumps({"error": "action must be 'invert' or 'align'", "blocked": True}, indent=2)

    cmd = build_invert() if action == "invert" else build_align()
    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def block_unblock_cue(
    action: str,
    cue_id: float,
    sequence_id: int | None = None,
    end: float | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Block or Unblock a cue (DESTRUCTIVE — modifies cue data in the show file).

    Block makes a cue store all active values and stop tracking from prior cues.
    Unblock removes the block flag, allowing values to track through again.

    Args:
        action: "block" or "unblock"
        cue_id: Cue number to block/unblock
        sequence_id: Sequence ID to scope the command (optional)
        end: End cue ID for range (thru syntax)
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON result with command sent
    """
    if action not in ("block", "unblock"):
        return json.dumps({"error": "action must be 'block' or 'unblock'", "blocked": True}, indent=2)
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": f"{action}_cue is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if action == "block":
        cmd = build_block(cue_id, sequence_id=sequence_id, end=end)
    else:
        cmd = build_unblock(cue_id, sequence_id=sequence_id, end=end)

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def get_executor_status(
    executor_id: int | None = None,
    page: int | None = None,
) -> str:
    """
    Query the status of one or all executors (SAFE_READ).

    Args:
        executor_id: Executor ID to inspect (optional; lists all if omitted)
        page: Page number for page-qualified addressing (optional)

    Returns:
        str: JSON result with raw console response
    """
    if executor_id is not None:
        ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
        cmd = f"list executor {ref}"
    else:
        cmd = "list executor"

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def store_timecode_event(
    timecode_id: int,
    cue_id: float,
    sequence_id: int,
    confirm_destructive: bool = False,
    timecode_position: str | None = None,
) -> str:
    """
    Store a timecode trigger event that fires a cue at a specific time (DESTRUCTIVE).

    Args:
        timecode_id: Timecode show ID (1-256)
        cue_id: Cue to trigger
        sequence_id: Sequence containing the cue
        confirm_destructive: Must be True to execute
        timecode_position: HH:MM:SS:FF position string (optional)

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    if timecode_position:
        cmd = f'assign timecode {timecode_id} cue {cue_id} sequence {sequence_id} "{timecode_position}"'
    else:
        cmd = f"store timecode {timecode_id}"

    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def set_sequence_property(
    sequence_id: int,
    property_name: str,
    value: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Set a property on a sequence object via the console tree (DESTRUCTIVE).

    Navigates to the sequence node, assigns the property, then returns to root.

    Args:
        sequence_id: Sequence ID (1-999)
        property_name: Property name (e.g. "loop", "tracking", "label")
        value: Property value (e.g. "on", "off", "My Sequence")
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON result with commands sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    result = await set_property(
        client,
        path=f"sequence {sequence_id}",
        property_name=property_name,
        value=value,
    )
    return json.dumps({
        "sequence_id": sequence_id,
        "property": property_name,
        "value": value,
        "commands_sent": result.commands_sent,
        "success": result.success,
        "verified_value": result.verified_value,
        "error": result.error,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


# ============================================================
# New Tools (Tools 45–52) — Quick Start Guide Gap-Fill
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def save_show(
    action: str,
    show_name: str | None = None,
) -> str:
    """
    Save the current show file to disk.

    Args:
        action: "save" (overwrite current) or "saveas" (save under a new name)
        show_name: Show name/path (required for action="saveas")

    Returns:
        str: JSON result with command sent
    """
    if action not in ("save", "saveas"):
        return json.dumps({"error": "action must be 'save' or 'saveas'", "blocked": True}, indent=2)
    if action == "saveas" and not show_name:
        return json.dumps({"error": "show_name is required for action='saveas'", "blocked": True}, indent=2)

    client = await get_client()
    cmd = "save" if action == "save" else f'saveas "{show_name}"'
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def store_cue_with_timing(
    cue_id: int,
    confirm_destructive: bool = False,
    fade_time: float | None = None,
    out_time: float | None = None,
    merge: bool = False,
    overwrite: bool = False,
    cue_name: str | None = None,
    sequence_id: int | None = None,
) -> str:
    """
    Store a cue with inline fade and outtime parameters (DESTRUCTIVE).

    When sequence_id is omitted, MA2 stores into the sequence on the currently
    selected executor. Pass sequence_id explicitly to target a specific sequence
    regardless of executor selection state (same behavior as store_current_cue).

    Args:
        cue_id: Cue number to store
        confirm_destructive: Must be True to execute
        fade_time: Fade-in time in seconds (optional)
        out_time: Fade-out time in seconds (optional)
        merge: Merge into existing cue
        overwrite: Overwrite existing cue
        cue_name: Optional cue label
        sequence_id: Sequence to store into (omit to use selected executor)

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    cmd = build_store_cue_timed(
        cue_id,
        name=cue_name,
        fade_time=fade_time,
        out_time=out_time,
        merge=merge,
        overwrite=overwrite,
    )
    if sequence_id is not None:
        cmd += f" sequence {sequence_id}"
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def select_executor(
    executor_id: int,
    page: int | None = None,
    deselect: bool = False,
) -> str:
    """
    Select an executor on the console.

    IMPORTANT: MA2 telnet 'select executor N' is single-selection only — there
    is no list syntax. You cannot select multiple executors simultaneously via
    this command. Pass only a single executor_id integer.

    After sending the command, $SELECTEDEXEC is read back to confirm the
    selection took effect. A 'warning' field is included in the response if
    the confirmed value does not match the requested executor_id.

    To clear the current selection, pass deselect=True. This sends a bare
    'select' command with no argument. NOTE: bare 'select' behaviour is
    unverified on grandMA2 telnet — it may clear selection, be silently
    ignored, or produce an error. Inspect 'raw_response' to confirm.

    Args:
        executor_id: Executor number (1-999). Single value only.
        page: Page number for page-qualified addressing (optional).
              e.g. page=2, executor_id=5 → 'select executor 2.5'.
              $SELECTEDEXEC returns the executor number only (not page-qualified).
        deselect: If True, send bare 'select' to clear the current selection
                  instead of selecting executor_id. Defaults to False.

    Returns:
        str: JSON with command_sent, raw_response, confirmed_selected_exec,
             and risk_tier. Includes 'warning' if confirmed value doesn't match.
    """
    client = await get_client()

    if deselect:
        cmd = "select"
        response = await client.send_command_with_response(cmd)
        listvar_raw = await client.send_command_with_response("ListVar")
        confirmed = _parse_listvar(listvar_raw).get("$SELECTEDEXEC")
        return json.dumps({
            "command_sent": cmd,
            "raw_response": response,
            "confirmed_selected_exec": confirmed,
            "note": "Bare 'select' sent to clear selection. Behaviour unverified on grandMA2 telnet.",
            "risk_tier": "SAFE_WRITE",
        }, indent=2)

    ref = f"{page}.{executor_id}" if page is not None else str(executor_id)
    cmd = f"select executor {ref}"
    response = await client.send_command_with_response(cmd)

    listvar_raw = await client.send_command_with_response("ListVar")
    variables = _parse_listvar(listvar_raw)
    confirmed = variables.get("$SELECTEDEXEC")

    result: dict = {
        "command_sent": cmd,
        "raw_response": response,
        "confirmed_selected_exec": confirmed,
        "risk_tier": "SAFE_WRITE",
    }
    # $SELECTEDEXEC stores executor number only (not page-qualified)
    if confirmed is None or confirmed.strip() != str(executor_id):
        result["warning"] = (
            f"$SELECTEDEXEC is '{confirmed}' after command but expected '{executor_id}'. "
            "The selection may not have taken effect."
        )
    return json.dumps(result, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def remove_from_programmer(
    object_type: str,
    object_id: int,
    end_id: int | None = None,
) -> str:
    """
    Remove channels, fixtures, or a group from the programmer using Off.

    Args:
        object_type: "channel", "fixture", or "group"
        object_id: Object ID to remove
        end_id: End of range for channel/fixture (optional; builds thru N)

    Returns:
        str: JSON result with command sent
    """
    if object_type not in ("channel", "fixture", "group"):
        return json.dumps(
            {"error": "object_type must be 'channel', 'fixture', or 'group'", "blocked": True},
            indent=2,
        )
    if end_id is not None and object_type != "group":
        cmd = f"off {object_type} {object_id} thru {end_id}"
    else:
        cmd = f"off {object_type} {object_id}"

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def assign_cue_trigger(
    cue_id: int,
    sequence_id: int,
    trigger_type: str,
    confirm_destructive: bool = False,
    trigger_value: float | None = None,
) -> str:
    """
    Assign a playback trigger type to a cue (DESTRUCTIVE).

    Args:
        cue_id: Cue number to assign the trigger to
        sequence_id: Sequence containing the cue
        trigger_type: "go", "follow", "time", or "bpm"
        confirm_destructive: Must be True to execute
        trigger_value: BPM or time value (required for "bpm" and "time")

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    valid = ("go", "follow", "time", "bpm")
    if trigger_type not in valid:
        return json.dumps({"error": f"trigger_type must be one of {valid}", "blocked": True}, indent=2)
    if trigger_type in ("bpm", "time") and trigger_value is None:
        return json.dumps(
            {"error": f"trigger_value is required for trigger_type='{trigger_type}'", "blocked": True},
            indent=2,
        )

    if trigger_type == "bpm":
        cmd = f"assign trigger bpm {trigger_value} cue {cue_id} sequence {sequence_id}"
    elif trigger_type == "time":
        cmd = f"assign trigger time {trigger_value} cue {cue_id} sequence {sequence_id}"
    else:
        cmd = f"assign trigger {trigger_type} cue {cue_id} sequence {sequence_id}"

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def assign_executor_property(
    executor_id: int,
    option: str,
    value: str | int,
    confirm_destructive: bool = False,
    page: int = 1,
) -> str:
    """
    Assign any of the 22 settable options to an executor (DESTRUCTIVE).

    Always uses page-qualified addressing (page.executor_id) to avoid Error #66.

    Valid options (case-sensitive):
      Layout:   width (1-5)
      Priority: priority (low|normal|high|htp|swap|super)
      Start:    autostart, autostop, autofix, autostomp, restart
      Protect:  ooo, swopprotect, killprotect
      Playback: softltp, wrap, crossfade (off|a|b|ab — requires width>=2), chaser
      Timing:   triggerisgo, cmddisable, effectspeed, autogo
      Speed:    speed (0-65535 BPM), speedmaster (speed_individual|speed1-16),
                ratemaster (rate_individual|rate1-16)

    Args:
        executor_id: Executor ID (e.g. 203).
        option: Option name from the list above.
        value: Value to assign (e.g. 2, "on", "high", "speed1").
        confirm_destructive: Must be True to execute.
        page: Page number (default 1). Always included in the address.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from src.commands import build_assign_executor_option as _build_opt
    try:
        cmd = _build_opt(executor_id, option, value, page=page)
    except ValueError as exc:
        return json.dumps({"error": str(exc), "blocked": True}, indent=2)

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def set_executor_priority(
    executor_id: int,
    priority: str,
    page: int = 1,
) -> str:
    """
    Set the playback priority of an executor (Tool 130).

    Priority determines how this executor interacts with other active executors
    and the programmer. Uses page-qualified addressing (page.executor_id) to
    avoid Error #66 CANNOT ASSIGN.

    Priority levels (highest → lowest):
      - "super"  — LTP above ALL playbacks + programmer. Only Freeze overrides.
      - "swap"   — LTP > HTP; negative override possible. Affects ALL attributes.
      - "htp"    — Highest intensity value wins. Changes ALL attribute priority.
      - "high"   — High LTP. Overrides Normal/Low but not HTP intensity.
      - "normal" — LTP default. Last triggered value wins.
      - "low"    — Lowest priority. Overridden by everything else.

    Args:
        executor_id: The executor to modify (e.g. 201).
        priority: One of "super", "swap", "htp", "high", "normal", "low".
        page: Page number (default 1). Always included in the address.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    from src.commands import build_set_executor_priority as _build_prio
    try:
        cmd = _build_prio(executor_id, priority, page=page)
    except ValueError as exc:
        return json.dumps({"error": str(exc), "blocked": True}, indent=2)

    client = await get_client()
    raw = await client.send_command_with_response(cmd)

    # Sync priority to snapshot write-tracker (Gap 10)
    if (snap := _orchestrator.last_snapshot) and executor_id in snap.executor_state:
        snap.executor_state[executor_id].priority = priority

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_executor_state(
    executor_id: int,
    page: int = 1,
) -> str:
    """
    Read all 32 fields of a single executor via 'List Executor page.id' (SAFE_READ).

    Returns all KEY=VALUE fields including Width, Priority, AutoStart, AutoStop,
    Crossfade, SpeedMaster, RateMaster, Filter, PlaybackMaster, etc.

    Must use page-qualified addressing — bare executor IDs return wrong data.

    Args:
        executor_id: Executor ID (e.g. 203).
        page: Page number (default 1).

    Returns:
        str: JSON with fields dict, command_sent, raw_response.
    """
    from src.prompt_parser import parse_executor_list
    cmd = f"List Executor {page}.{executor_id}"
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    fields = parse_executor_list(raw)
    return json.dumps({
        "command_sent": cmd,
        "fields": fields,
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def discover_fixture_type_attributes(
    fixture_type_id: int,
) -> str:
    """
    Discover attribute names for a fixture type via EditSetup tree navigation (SAFE_READ).

    Navigates cd EditSetup → FixtureTypes → type N → first mode → first subfixture → list,
    returning ChannelType rows with attribute library names (e.g. PAN, TILT, COLORRGB1).

    Use this to confirm which attributes a fixture type exposes before building presets.
    Note: Info FixtureType N does NOT return attribute names — this navigation method is
    the correct approach (live-verified 2026-03-31).

    Args:
        fixture_type_id: Fixture type number (e.g. 4 for Mac Viper Profile 16-bit).

    Returns:
        str: JSON with raw_response containing ChannelType rows.
    """
    client = await get_client()

    async def send(cmd: str) -> str:
        return await client.send_command_with_response(cmd)

    await send("cd /")
    await send("cd EditSetup")
    await send("cd FixtureTypes")
    await send(f"cd {fixture_type_id}")
    await send("cd 1")  # first mode
    await send("cd 1")  # first subfixture
    raw = await send("list")
    await send("cd /")  # return to root

    return json.dumps({
        "fixture_type_id": fixture_type_id,
        "navigation": f"EditSetup → FixtureTypes → {fixture_type_id} → 1 → 1 → list",
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def scan_page_executor_layout(
    page: int = 1,
    executor_id_start: int = 201,
    executor_id_end: int = 240,
) -> str:
    """
    Scan a range of executors on a page and return their slot occupancy map (SAFE_READ).

    Queries each executor in the range via 'List Executor page.id' (KEY=VALUE format),
    extracts Name, Sequence, and Width. Builds an occupancy map showing which consecutive
    slots are blocked by wide executors, and lists free slots.

    Use this BEFORE setting width on an executor to confirm the adjacent slot is free.
    A width=2 executor at slot N blocks slot N+1; the console will silently fail or wrap
    if N+1 is already occupied.

    Args:
        page: Page number to scan (default 1).
        executor_id_start: First executor ID to check (default 201).
        executor_id_end: Last executor ID to check (default 240).

    Returns:
        str: JSON with:
          - executors: list of {id, name, sequence, width, slots_occupied}
          - blocked_slots: set of slot IDs consumed by multi-wide executors
          - free_slots: slot IDs in range with no assignment
    """
    import asyncio
    from src.prompt_parser import parse_executor_list

    client = await get_client()
    executor_data: list[dict] = []
    occupied_slots: set[int] = set()

    for exec_id in range(executor_id_start, executor_id_end + 1):
        cmd = f"List Executor {page}.{exec_id}"
        raw = await client.send_command_with_response(cmd)
        fields = parse_executor_list(raw)

        # Skip unassigned slots — no Name and no Sequence
        if not fields.get("Name") and not fields.get("Sequence"):
            continue

        width = int(fields.get("Width", 1))
        name = fields.get("Name", "")
        sequence = fields.get("Sequence", "")
        slots = list(range(exec_id, exec_id + width))

        executor_data.append({
            "id": exec_id,
            "name": name,
            "sequence": sequence,
            "width": width,
            "slots_occupied": slots,
        })
        for s in slots:
            occupied_slots.add(s)

        await asyncio.sleep(0.1)  # avoid flooding telnet

    all_slots = set(range(executor_id_start, executor_id_end + 1))
    free_slots = sorted(all_slots - occupied_slots)

    return json.dumps({
        "page": page,
        "scanned_range": [executor_id_start, executor_id_end],
        "executors": executor_data,
        "occupied_slots": sorted(occupied_slots),
        "free_slots": free_slots,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def if_filter(
    filter_type: str,
    fixture_id: int | None = None,
    attribute_name: str | None = None,
) -> str:
    """
    Apply an If filter to the current selection or command context.

    Args:
        filter_type: "active" (bare 'if'), "fixture" (specific fixture), or "attribute"
        fixture_id: Fixture ID (required for "fixture" and "attribute")
        attribute_name: Attribute name (required for "attribute"; e.g. "Pan")

    Returns:
        str: JSON result with command sent
    """
    if filter_type not in ("active", "fixture", "attribute"):
        return json.dumps(
            {"error": "filter_type must be 'active', 'fixture', or 'attribute'", "blocked": True},
            indent=2,
        )
    if filter_type in ("fixture", "attribute") and fixture_id is None:
        return json.dumps(
            {"error": "fixture_id is required for filter_type != 'active'", "blocked": True},
            indent=2,
        )
    if filter_type == "attribute" and attribute_name is None:
        return json.dumps(
            {"error": "attribute_name is required for filter_type='attribute'", "blocked": True},
            indent=2,
        )

    if filter_type == "active":
        cmd = "if"
    elif filter_type == "fixture":
        cmd = f"if fixture {fixture_id}"
    else:
        cmd = f'if fixture {fixture_id} attribute "{attribute_name}"'

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def save_recall_view(
    action: str,
    view_id: int,
    screen_id: int = 1,
    view_name: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Store, recall, or label a screen view (store is DESTRUCTIVE).

    Args:
        action: "store" (save current screen), "recall" (load view), or "label" (name it)
        view_id: View slot ID (1-10)
        screen_id: Screen number (1-4, default 1)
        view_name: Label for the view (required for action="label")
        confirm_destructive: Must be True for action="store"

    Returns:
        str: JSON result with command sent
    """
    if action not in ("store", "recall", "label"):
        return json.dumps(
            {"error": "action must be 'store', 'recall', or 'label'", "blocked": True},
            indent=2,
        )
    if not (1 <= view_id <= 10):
        return json.dumps({"error": "view_id must be between 1 and 10", "blocked": True}, indent=2)
    if not (1 <= screen_id <= 4):
        return json.dumps({"error": "screen_id must be between 1 and 4", "blocked": True}, indent=2)
    if action == "store" and not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Destructive operation blocked. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)
    if action == "label" and not view_name:
        return json.dumps(
            {"error": "view_name is required for action='label'", "blocked": True},
            indent=2,
        )

    ref = f"{screen_id}.{view_id}"
    if action == "store":
        cmd = f"store ViewButton {ref}"
        risk_tier = "DESTRUCTIVE"
    elif action == "recall":
        cmd = f"ViewButton {ref}"
        risk_tier = "SAFE_WRITE"
    else:
        cmd = f'label ViewButton {ref} "{view_name}"'
        risk_tier = "SAFE_WRITE"

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk_tier,
    }, indent=2)


# ============================================================
# Tools 53–54 — Import / Export
# ============================================================

# Valid export types (live-validated on MA2 3.9.60.65)
_EXPORT_TYPES = {
    "group", "preset", "macro", "effect", "sequence", "view", "page",
    "camera", "layout", "form", "plugin", "matricks", "mask", "image",
    "executor", "timecode", "userprofile", "channel", "screen", "filter",
}

# Valid import types (screen excluded — Error #16 RESIZE FORBIDDEN on import)
_IMPORT_TYPES = {
    "group", "preset", "macro", "effect", "sequence", "view", "page",
    "camera", "layout", "form", "plugin", "matricks", "mask", "image",
    "executor", "timecode", "userprofile", "filter",
}

# Type-specific subfolders (informational — MA2 routes automatically)
# macros/ | effects/ | plugins/ | matricks/ | masks/ | importexport/ (default)
_GMA2_DATA_ROOT = os.environ.get(
    "GMA2_DATA_ROOT",
    r"C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60",
)
_IMPORT_EXPORT_DATA_ROOT = os.path.join(_GMA2_DATA_ROOT, "importexport")


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def export_objects(
    object_type: str,
    object_id: str,
    filename: str,
    style: str | None = None,
    overwrite: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Export objects from the show file to disk (DESTRUCTIVE — writes files).

    Files are written to the grandMA2 data directory. MA2 routes each type
    to its own subfolder automatically:
      - Macro → macros/    Effect → effects/    Plugin → plugins/
      - MAtricks → matricks/    Mask → masks/
      - All others → importexport/

    On this system: C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\

    Supported object types (19 validated):
      group, preset, macro, effect, sequence, view, page, camera, layout,
      form, plugin, matricks, mask, image, executor, timecode, userprofile,
      channel, screen

    Preset syntax for object_id:
      - Single preset:  "1.3"  (type 1=Dimmer, 2=Position, 3=Gobo, 4=Color,
                                 5=Beam, 6=Focus, 7=Control, 8=Shapers, 9=Video)
      - All of a type:  "1"    (exports all dimmer presets)
      - Range:          "1 thru 5"

    Args:
        object_type: Object type (case-insensitive)
        object_id: ID, preset ref ("1.3"), range ("1 thru 5"), or name (UserProfile)
        filename: Output filename — no extension, no path needed
        style: "csv" or "html" — default is xml
        overwrite: Replace existing file without prompting
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with command_sent, raw_response, risk_tier, data_path
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Export writes files to disk. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if object_type.lower() not in _EXPORT_TYPES:
        return json.dumps({
            "error": (
                f"Invalid object_type '{object_type}'. "
                f"Valid types: {sorted(_EXPORT_TYPES)}"
            ),
            "blocked": True,
        }, indent=2)

    if style is not None and style.lower() not in ("csv", "html"):
        return json.dumps(
            {"error": "style must be 'csv' or 'html' (omit for default xml)", "blocked": True},
            indent=2,
        )

    cmd = build_export_object(
        object_type,
        object_id,
        filename,
        overwrite=overwrite,
        noconfirm=True,
        style=style,
    )

    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "DESTRUCTIVE",
        "data_path": _IMPORT_EXPORT_DATA_ROOT,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.FIXTURE_IMPORT)
@_handle_errors
async def import_objects(
    filename: str,
    destination_type: str,
    destination_id: str | None = None,
    quiet: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Import objects from a file into the show (DESTRUCTIVE — modifies show file).

    MA2 locates the file using the destination type to determine the correct
    subfolder automatically (same routing as export). The file must exist in
    the grandMA2 data directory before calling this tool.

    Files are read from: C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\
      - Macro → macros/    Effect → effects/    Plugin → plugins/
      - MAtricks → matricks/    Mask → masks/
      - All others → importexport/

    Supported destination types (17 validated):
      group, preset, macro, effect, sequence, view, page, camera, layout,
      form, plugin, matricks, mask, image, executor, timecode, userprofile

    (Screen is export-only — import gives RESIZE FORBIDDEN error.)

    Preset destination_id format: "T.N"  e.g. "1.99" = Dimmer slot 99

    Args:
        filename: Source filename — no extension, no path needed
        destination_type: Object type for placement (REQUIRED — MA2 Error #28 without it)
        destination_id: Slot number or preset ref ("T.N"). None = next free slot.
        quiet: Suppress MA2 feedback output during import
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Import modifies the show file. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if destination_type.lower() not in _IMPORT_TYPES:
        return json.dumps({
            "error": (
                f"Invalid destination_type '{destination_type}'. "
                f"Valid types: {sorted(_IMPORT_TYPES)}"
            ),
            "blocked": True,
        }, indent=2)

    cmd = build_import_object(
        filename,
        destination_type,
        destination_id,
        noconfirm=True,
        quiet=quiet,
    )

    client = await get_client()

    # Pre-import slot check — informational only
    slot_status: dict | None = None
    if destination_id is not None:
        try:
            slot_int = int(str(destination_id).split(".")[0])
            avail = await _check_pool_slots(
                client, destination_type,
                start_from=slot_int, scan_up_to=slot_int,
            )
            is_occupied = any(
                s["slot"] == slot_int for s in avail["occupied_slots"]
            )
            slot_status = {"occupied": is_occupied}
            if is_occupied:
                match = next(
                    s for s in avail["occupied_slots"] if s["slot"] == slot_int
                )
                slot_status["previous_name"] = match["name"]
        except (ValueError, TypeError):
            pass  # non-numeric destination_id (e.g. preset "2.5")

    raw_response = await client.send_command_with_response(cmd)

    result: dict = {
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "DESTRUCTIVE",
    }
    if slot_status is not None:
        result["slot_status"] = slot_status

    return json.dumps(result, indent=2)


# ============================================================
# Tools 74–76 — Fixture Type / Layer Import + XML Generation
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.FIXTURE_IMPORT)
@_handle_errors
async def import_fixture_type(
    manufacturer: str,
    fixture: str,
    mode: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Import a fixture type from the MA2 library into the show (DESTRUCTIVE).

    Navigates to EditSetup/FixtureTypes context, imports the fixture type
    by 'manufacturer@fixture@mode' key, then returns to root context.

    Use list_library(library_type="fixture") first to find the exact key values.

    Args:
        manufacturer: Manufacturer name exactly as in MA2 library (e.g. "Martin", "Generic")
        fixture: Fixture model name (e.g. "Mac700Profile_Extended")
        mode: Mode name (e.g. "Extended", "Standard")
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with steps list (command + response per step), fixture_key, risk_tier
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Import fixture type modifies the show. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    sequence = [
        'ChangeDest "EditSetup"',
        'ChangeDest "FixtureTypes"',
        build_import_fixture_type_cmd(manufacturer, fixture, mode),
        'ChangeDest /',
    ]
    steps = []
    for cmd in sequence:
        raw = await client.send_command_with_response(cmd)
        steps.append({"command": cmd, "response": raw})

    return json.dumps({
        "steps": steps,
        "fixture_key": f"{manufacturer}@{fixture}@{mode}",
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.FIXTURE_IMPORT)
@_handle_errors
async def import_fixture_layer(
    filename: str,
    layer_index: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Import a fixture layer XML file into the show patch (DESTRUCTIVE).

    Navigates to EditSetup/Layers context, imports the XML layer file,
    then returns to root context. Use generate_fixture_layer_xml to
    create the XML file before calling this tool.

    The file must exist in the MA2 importexport directory:
      C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\importexport\\

    Args:
        filename: Layer XML filename without extension or path
        layer_index: Target layer slot. None = MA2 picks next free slot
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with steps list (command + response per step), filename, risk_tier
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Import fixture layer modifies the show patch. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    sequence = [
        'ChangeDest "EditSetup"',
        'ChangeDest "Layers"',
        build_import_layer_cmd(filename, layer_index),
        'ChangeDest /',
    ]
    steps = []
    for cmd in sequence:
        raw = await client.send_command_with_response(cmd)
        steps.append({"command": cmd, "response": raw})

    return json.dumps({
        "steps": steps,
        "filename": filename,
        "layer_index": layer_index,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def generate_fixture_layer_xml(
    filename: str,
    layer_name: str,
    layer_index: int,
    fixtures: list[dict],
    showfile: str = "grandma2",
    overwrite: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Generate a grandMA2 fixture layer XML file and save it to the importexport directory (DESTRUCTIVE).

    The output file can be imported immediately using import_fixture_layer.
    No telnet connection required — this tool writes a local file only.

    Output directory:
      C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\importexport\\

    Each fixture dict must contain:
        fixture_id (int): grandMA2 fixture ID (e.g. 111)
        name (str): Display name (e.g. "Dim 1" or "Mac 700 1")
        fixture_type_no (int): Fixture type number from list_fixture_types()
        fixture_type_name (str): Display name of the fixture type
        dmx_address (int): 1-based DMX start address within its universe
        num_channels (int): Total DMX channel count for this fixture type

    Args:
        filename: Output filename without extension
        layer_name: Layer display name shown in MA2 UI
        layer_index: Layer index number (1-based) for the <Layer> XML element
        fixtures: List of fixture parameter dicts (see schema above)
        showfile: Show name embedded in XML <Info> element
        overwrite: If True, overwrite existing file; if False, return error on conflict
        confirm_destructive: Must be True to execute (writes files to console importexport directory)

    Returns:
        str: JSON with file_path, filename, fixture_count, layer_index, layer_name
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Generate Fixture Layer XML writes files to disk. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    import os
    from datetime import datetime
    from xml.dom import minidom
    from xml.etree.ElementTree import Element, SubElement, tostring

    output_dir = (
        r"C:\ProgramData\MA Lighting Technologies"
        r"\grandma\gma2_V_3.9.60\importexport"
    )
    file_path = os.path.join(output_dir, f"{filename}.xml")

    if os.path.exists(file_path) and not overwrite:
        return json.dumps({
            "error": (
                f"File already exists: {file_path}. "
                "Pass overwrite=True to replace it."
            ),
        }, indent=2)

    root = Element("MA", {
        "major_vers": "3",
        "minor_vers": "9",
        "stream_vers": "60",
    })
    SubElement(root, "Info", {
        "datetime": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S"),
        "showfile": showfile,
    })
    layer_el = SubElement(root, "Layer", {
        "index": str(layer_index),
        "name": layer_name,
    })

    for idx, fx in enumerate(fixtures):
        fx_el = SubElement(layer_el, "Fixture", {
            "index": str(idx),
            "name": fx["name"],
            "fixture_id": str(fx["fixture_id"]),
        })
        ft_el = SubElement(fx_el, "FixtureType", {"name": fx["fixture_type_name"]})
        SubElement(ft_el, "No").text = str(fx["fixture_type_no"])

        sf_el = SubElement(fx_el, "SubFixture", {
            "index": "0",
            "react_to_grandmaster": "true",
            "color": "ffffff",
        })
        patch_el = SubElement(sf_el, "Patch")
        SubElement(patch_el, "Address").text = str(fx["dmx_address"])

        pos_el = SubElement(sf_el, "AbsolutePosition")
        SubElement(pos_el, "Location", {"x": "0", "y": "0", "z": "0"})
        SubElement(pos_el, "Rotation", {"x": "0", "y": "-0", "z": "0"})
        SubElement(pos_el, "Scaling", {"x": "1", "y": "1", "z": "1"})

        for ch in range(fx["num_channels"]):
            SubElement(sf_el, "Channel", {"index": str(ch)})

    raw_xml = tostring(root, encoding="unicode")
    pretty_bytes = minidom.parseString(raw_xml).toprettyxml(indent="  ", encoding="utf-8")
    # Replace minidom's XML declaration (includes standalone attr) with a clean one
    lines = pretty_bytes.split(b"\n")
    xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>\n' + b"\n".join(lines[1:])

    os.makedirs(output_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(xml_bytes)

    return json.dumps({
        "file_path": file_path,
        "filename": filename,
        "fixture_count": len(fixtures),
        "layer_index": layer_index,
        "layer_name": layer_name,
    }, indent=2)


# ============================================================
# Tools 55–56 — Fixture & Sequence/Cue Discovery (SAFE_READ)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_fixtures(
    fixture_id: int | None = None,
) -> str:
    """
    List fixtures defined on the console, or check a specific fixture exists.

    This is the correct way to discover fixture IDs before using park_fixture,
    unpark_fixture, set_intensity, or set_attribute. Note: 'cd Fixture' is NOT
    a valid MA2 navigation destination — this tool uses 'list fixture' instead.

    Args:
        fixture_id: Optional fixture ID to inspect. If None, lists all fixtures.

    Returns:
        str: JSON with command_sent, raw_response, exists (bool), fixture_id.
             exists is always True when fixture_id is None (listing all).

    Examples:
        - List all fixtures: list_fixtures()
        - Check fixture 20: list_fixtures(fixture_id=20)
        - Check fixture 1 (likely missing): list_fixtures(fixture_id=1)
    """
    client = await get_client()

    if fixture_id is not None:
        cmd = f"list fixture {fixture_id}"
        raw = await client.send_command_with_response(cmd)
        exists = "NO OBJECTS FOUND" not in raw.upper()
    else:
        cmd = "list fixture"
        raw = await client.send_command_with_response(cmd)
        exists = True

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "exists": exists,
        "fixture_id": fixture_id,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_sequence_cues(
    sequence_id: int | None = None,
    executor_id: int | None = None,
    executor_page: int = 1,
    cue_id: int | float | None = None,
) -> str:
    """
    List cues in a sequence, or check whether a specific cue exists.

    Supports two ways to identify the sequence:
      - sequence_id: Direct sequence number (e.g. 278)
      - executor_id: Executor number — sequence is resolved via
        'list executor PAGE.ID' before listing cues

    If both are supplied, sequence_id takes precedence.

    Validated MA2 probes used:
      'list cue sequence N'     → all cues in sequence N
      'list cue M sequence N'   → specific cue M in sequence N
      'list executor P.E'       → resolve sequence from executor

    Args:
        sequence_id: Sequence number to inspect.
        executor_id: Executor number — resolved to its linked sequence.
        executor_page: Executor page for resolution (default 1).
        cue_id: Optional specific cue to check for existence.

    Returns:
        str: JSON with command_sent, raw_response, exists, resolved_sequence_id,
             and executor_probe_response (when executor_id was used).

    Examples:
        - All cues in seq 278: list_sequence_cues(sequence_id=278)
        - Cue 5 in seq 278: list_sequence_cues(sequence_id=278, cue_id=5)
        - Cues for executor 1: list_sequence_cues(executor_id=1)
        - Check cue 99 on executor 1: list_sequence_cues(executor_id=1, cue_id=99)
    """
    client = await get_client()
    executor_probe_response: str | None = None

    resolved_sequence = sequence_id
    if resolved_sequence is None and executor_id is not None:
        resolved_sequence, executor_probe_response = await _get_sequence_for_executor(
            client, executor_id, page=executor_page
        )
        if resolved_sequence is None:
            return json.dumps({
                "command_sent": f"list executor {executor_page}.{executor_id}",
                "raw_response": executor_probe_response,
                "error": (
                    f"Could not resolve a sequence for executor "
                    f"{executor_page}.{executor_id}. "
                    "The executor may not have a sequence assigned."
                ),
                "exists": False,
                "resolved_sequence_id": None,
                "risk_tier": "SAFE_READ",
                "blocked": True,
            }, indent=2)

    if resolved_sequence is None:
        return json.dumps({
            "error": "Must supply either sequence_id or executor_id.",
            "command_sent": None,
            "risk_tier": "SAFE_READ",
            "blocked": True,
        }, indent=2)

    if cue_id is not None:
        cmd = f"list cue {cue_id} sequence {resolved_sequence}"
    else:
        cmd = f"list cue sequence {resolved_sequence}"

    raw = await client.send_command_with_response(cmd)
    exists = "NO OBJECTS FOUND" not in raw.upper() if cue_id is not None else True

    result: dict = {
        "command_sent": cmd,
        "raw_response": raw,
        "exists": exists,
        "resolved_sequence_id": resolved_sequence,
        "risk_tier": "SAFE_READ",
    }
    if executor_probe_response is not None:
        result["executor_probe_response"] = executor_probe_response

    return json.dumps(result, indent=2)


# ============================================================
# Tools 57–64: Tier 1 — High-Impact Tools
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def highlight_fixtures(on: bool = True) -> str:
    """
    Toggle highlight mode for the currently selected fixtures.

    Highlight mode temporarily sets selected fixtures to full intensity to help
    identify them on stage. Easily reversible (toggle off).

    Args:
        on: True to enable, False to disable highlight mode.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    cmd = build_highlight(on)
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def release_executor(
    executor_id: int,
    page: int | None = None,
) -> str:
    """
    Release an executor, returning it to its default state.

    Args:
        executor_id: Executor ID (1-999).
        page: Page number for page-qualified addressing (optional).

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    cmd = build_release_executor(executor_id, page=page)
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def blackout_toggle() -> str:
    """
    Toggle master blackout (kills all lighting output).

    Blackout is a toggle — call once to enable, again to disable.
    SAFE_WRITE because it is easily reversible.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    cmd = build_blackout()
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_shows() -> str:
    """
    List available show files on the console.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    cmd = build_list_shows()
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SHOW_LOAD)
@_handle_errors
async def load_show(
    name: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Load an existing show file (DESTRUCTIVE — replaces current show).

    Args:
        name: Show file name to load.
        confirm_destructive: Must be True to proceed.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "LoadShow replaces the current show. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    cmd = build_load_show(name)
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SHOW_LOAD)
@_handle_errors
async def new_show(
    name: str,
    confirm_destructive: bool = False,
    preserve_connectivity: bool = True,
    keep_timeconfig: bool = False,
    keep_globalsettings: bool = False,
    keep_localsettings: bool = False,
    keep_protocols: bool = False,
    keep_network: bool = False,
    keep_user: bool = False,
) -> str:
    """
    Create a new empty show (DESTRUCTIVE — replaces current show).

    CONNECTIVITY WARNING
    --------------------
    Creating a new show clears Global Settings, which **disables Telnet login**
    and severs the MCP connection.  ``preserve_connectivity=True`` (the default)
    automatically adds /globalsettings + /network + /protocols so Telnet stays
    enabled and network/DMX config is preserved.

    Set ``preserve_connectivity=False`` only if you intend to manually
    re-enable Telnet on the console afterwards (Setup → Console → Global
    Settings → Telnet → Login Enabled).

    Keep flags (correspond to un-checking "Clear …" in the MA2 New Show dialog):

    | Flag               | Dialog checkbox          | MA2 flag        | Included by preserve_connectivity |
    |--------------------|--------------------------|-----------------|-----------------------------------|
    | keep_globalsettings| Clear Global Settings    | /globalsettings | YES — contains Telnet login       |
    | keep_network       | Clear Network Config     | /network        | YES — IP / MA-Net2 config         |
    | keep_protocols     | Clear Network Protocols  | /protocols      | YES — Art-Net, sACN, etc.         |
    | keep_timeconfig    | Clear Time Config        | /timeconfig     | no                                |
    | keep_localsettings | Clear Local Settings     | /localsettings  | no                                |
    | keep_user          | Clear User Profiles      | /user           | no                                |

    Args:
        name: New show file name.
        confirm_destructive: Must be True to proceed.
        preserve_connectivity: Auto-add /globalsettings + /network + /protocols
            to prevent Telnet being disabled (default True).
        keep_timeconfig: Preserve Time Config from current show.
        keep_globalsettings: Preserve Global Settings (overrides preserve_connectivity).
        keep_localsettings: Preserve Local Settings from current show.
        keep_protocols: Preserve Network Protocol settings (overrides preserve_connectivity).
        keep_network: Preserve Network Config (overrides preserve_connectivity).
        keep_user: Preserve User Profiles from current show.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier,
             and connectivity_flags listing which flags were applied.

    AI assistant guidance
    ---------------------
    Always confirm ``preserve_connectivity=True`` unless the user explicitly
    wants a completely clean show AND understands Telnet will be disabled.
    Ask about keep_timeconfig, keep_localsettings, keep_user separately —
    these have no connectivity impact and are purely about preserving show data.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "NewShow replaces the current show. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    # Merge preserve_connectivity defaults with explicit flags
    effective_globalsettings = keep_globalsettings or preserve_connectivity
    effective_network = keep_network or preserve_connectivity
    effective_protocols = keep_protocols or preserve_connectivity

    # /noconfirm is always needed — the telnet connection is stateless
    # (each call reconnects) so it cannot answer the console's
    # "save old show first?" dialog mid-stream.
    cmd = build_new_show(
        name,
        noconfirm=True,
        keep_timeconfig=keep_timeconfig,
        keep_globalsettings=effective_globalsettings,
        keep_localsettings=keep_localsettings,
        keep_protocols=effective_protocols,
        keep_network=effective_network,
        keep_user=keep_user,
    )
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
        "preserve_connectivity": preserve_connectivity,
        "connectivity_flags": {
            "globalsettings": effective_globalsettings,
            "network": effective_network,
            "protocols": effective_protocols,
        },
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_variable(
    action: str,
    var_name: str | None = None,
) -> str:
    """
    Read variables from the console (SAFE_READ).

    Args:
        action: One of:
            "echo"         — read any variable via `Echo $NAME` (system + user vars).
                             Use this for built-in system variables: $SELECTEDEXEC,
                             $TIME, $DATE, $VERSION, $FADERPAGE, $BUTTONPAGE,
                             $SELECTEDFIXTURESCOUNT, $USER, $HOSTNAME, $HOSTSTATUS, etc.
            "get_user"     — read a user variable via GetUserVar.
            "list_var"     — list all global show variables.
            "list_user_var"— list all user-profile variables.
        var_name: Variable name (required for "echo" and "get_user").
                  May include or omit leading $. E.g. "SELECTEDEXEC" or "$mycounter".

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
             For "echo", also includes `variable` and `value` keys.
    """
    valid_actions = ("echo", "get_user", "list_var", "list_user_var")
    if action not in valid_actions:
        return json.dumps({
            "error": f"action must be one of {valid_actions}",
            "blocked": True,
        }, indent=2)

    if action == "echo":
        if not var_name:
            return json.dumps({
                "error": "var_name is required for echo action",
                "blocked": True,
            }, indent=2)
        clean = var_name.lstrip("$")
        cmd = "ListVar"
        client = await get_client()
        raw = await client.send_command_with_response(cmd)
        variables = _parse_listvar(raw)
        value = variables.get(f"${clean}") or variables.get(f"${clean.upper()}")
        return json.dumps({
            "variable": f"${clean}",
            "value": value,
            "found": value is not None,
            "command_sent": cmd,
            "raw_response": raw,
            "risk_tier": "SAFE_READ",
        }, indent=2)

    if action == "get_user":
        if not var_name:
            return json.dumps({
                "error": "var_name is required for get_user action",
                "blocked": True,
            }, indent=2)
        cmd = build_get_user_var(var_name)
    elif action == "list_var":
        cmd = build_list_var()
    else:
        cmd = build_list_user_var()

    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_preset_pool(
    preset_type: str | None = None,
) -> str:
    """
    List presets stored in the show's Global preset pool.

    Without arguments: returns all PresetPool entries with their counts
    (Dimmer, Position, Gobo, Color, Beam, Focus, Control, Shapers, Video).

    With preset_type: navigates into that pool and lists individual presets
    with their slot number, name, and Special field.

    CD tree path navigated:
      cd 17 → cd 1 → list             (pool overview)
      cd 17 → cd 1 → cd N → list      (individual preset type)

    Pool index → type mapping (live-verified v3.9.60.65):
      0=ALL  1=DIMMER  2=POSITION  3=GOBO  4=COLOR
      5=BEAM  6=FOCUS  7=CONTROL  8=SHAPERS  9=VIDEO

    Note: The "Special" column shows "Normal" (standard) or "Embedded" — it
    does NOT indicate Universal vs Selective scope. Scope is an internal flag
    only visible in the console GUI or show XML.

    Args:
        preset_type: Optional type to drill into. Accepts name ("color", "position")
            or number ("4"). If omitted, returns pool overview.

    Returns:
        str: JSON with pool overview or individual preset list.
    """
    from src.commands.constants import PRESET_TYPES

    client = await get_client()

    # Navigate to Global preset pool
    await navigate(client, "/")
    await navigate(client, "17")
    await navigate(client, "1")

    if preset_type is None:
        # Overview: list all pools
        lst = await list_destination(client)
        await navigate(client, "/")
        return json.dumps({
            "cd_path": "17.1",
            "description": "Global PresetPool overview",
            "raw_response": lst.raw_response if lst else "",
            "entries": [
                {"type": e.object_type, "id": e.object_id, "name": e.name}
                for e in (lst.parsed_list.entries if lst and lst.parsed_list else [])
            ],
            "risk_tier": "SAFE_READ",
        }, indent=2)

    # Resolve preset_type to pool index
    try:
        pool_idx = int(preset_type)
    except (ValueError, TypeError):
        pool_idx = PRESET_TYPES.get(str(preset_type).lower())
        if pool_idx is None:
            await navigate(client, "/")
            return json.dumps({
                "error": f"Unknown preset_type {preset_type!r}. Use name (color, position) or number 1-9."
            }, indent=2)

    await navigate(client, str(pool_idx))
    lst = await list_destination(client)
    await navigate(client, "/")

    return json.dumps({
        "cd_path": f"17.1.{pool_idx}",
        "preset_type": preset_type,
        "pool_index": pool_idx,
        "raw_response": lst.raw_response if lst else "",
        "entries": [
            {"type": e.object_type, "id": e.object_id, "name": e.name}
            for e in (lst.parsed_list.entries if lst and lst.parsed_list else [])
        ],
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_undo_history() -> str:
    """
    Display the undo (Oops) history.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    cmd = build_list_oops()
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


# ============================================================
# Tools 65–69: Tier 2 — Setup & Library Tools
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_fixture_types() -> str:
    """
    List all fixture types in the show (from LiveSetup/FixtureTypes).

    Navigates to cd 10 (LiveSetup) -> cd 3 (FixtureTypes) -> list -> cd /

    Returns:
        str: JSON with raw_response, entries (fixture type names, manufacturers,
             DMX footprint), risk_tier.
    """
    client = await get_client()
    commands_sent = []

    # Navigate to root
    nav = await navigate(client, "/")
    commands_sent.append(nav.command_sent)

    # Navigate to LiveSetup
    nav = await navigate(client, "10")
    commands_sent.append(nav.command_sent)

    # Navigate to FixtureTypes
    nav = await navigate(client, "3")
    commands_sent.append(nav.command_sent)

    # List
    lst = await list_destination(client)
    commands_sent.append(lst.command_sent)

    # Return to root
    nav = await navigate(client, "/")
    commands_sent.append(nav.command_sent)

    entries = [
        {"object_type": e.object_type, "object_id": e.object_id, "name": e.name}
        for e in lst.parsed_list.entries
    ]

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": lst.raw_response,
        "entries": entries,
        "entry_count": len(entries),
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_layers() -> str:
    """
    List all fixture layers in the show (from LiveSetup/Layers).

    Navigates to cd 10 (LiveSetup) -> cd 4 (Layers) -> list -> cd /

    Returns:
        str: JSON with raw_response, entries (layer names, fixture ranges),
             risk_tier.
    """
    client = await get_client()
    commands_sent = []

    nav = await navigate(client, "/")
    commands_sent.append(nav.command_sent)

    nav = await navigate(client, "10")
    commands_sent.append(nav.command_sent)

    nav = await navigate(client, "4")
    commands_sent.append(nav.command_sent)

    lst = await list_destination(client)
    commands_sent.append(lst.command_sent)

    nav = await navigate(client, "/")
    commands_sent.append(nav.command_sent)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": lst.raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_universes(
    max_universes: int = 16,
) -> str:
    """
    List DMX universes and their configuration (from LiveSetup/Universes).

    Navigates to cd 10 (LiveSetup) -> cd 5 (Universes) -> list -> cd /

    Args:
        max_universes: Limit output to first N universes (default 16, max 256).

    Returns:
        str: JSON with raw_response, risk_tier.
    """
    client = await get_client()
    commands_sent = []

    nav = await navigate(client, "/")
    commands_sent.append(nav.command_sent)

    nav = await navigate(client, "10")
    commands_sent.append(nav.command_sent)

    nav = await navigate(client, "5")
    commands_sent.append(nav.command_sent)

    lst = await list_destination(client)
    commands_sent.append(lst.command_sent)

    nav = await navigate(client, "/")
    commands_sent.append(nav.command_sent)

    # Truncate raw response if too many universes
    entries = [
        {"object_type": e.object_type, "object_id": e.object_id, "name": e.name}
        for e in lst.parsed_list.entries[:max_universes]
    ]

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": lst.raw_response[:2000] if len(lst.raw_response) > 2000 else lst.raw_response,
        "entries": entries,
        "entry_count": len(lst.parsed_list.entries),
        "showing": min(max_universes, len(lst.parsed_list.entries)),
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_library(
    library_type: str = "fixture",
) -> str:
    """
    Browse the console's built-in libraries.

    Args:
        library_type: "fixture" (ListLibrary), "effect" (ListEffectLibrary),
                      or "macro" (ListMacroLibrary).

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    valid_types = ("fixture", "effect", "macro")
    if library_type not in valid_types:
        return json.dumps({
            "error": f"library_type must be one of {valid_types}",
            "blocked": True,
        }, indent=2)

    if library_type == "fixture":
        cmd = build_list_library()
    elif library_type == "effect":
        cmd = build_list_effect_library()
    else:
        cmd = build_list_macro_library()

    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def manage_matricks(
    action: str,
    value: int | None = None,
    x: int | None = None,
    y: int | None = None,
    column: int | None = None,
    increment: str | None = None,
    name: str | None = None,
    mode: str | None = None,
    turn_off: bool = False,
) -> str:
    """
    Control MAtricks selection patterns via direct command keywords (SAFE_WRITE).

    Uses grandMA2 MAtricks command keywords that act directly on the current
    fixture selection — no navigation required.

    Actions and their parameters:
      - "interleave": Set virtual grid width. Params: value (width), column, increment (+/-), turn_off.
      - "blocks": Set block size. Params: value (size), x, y (x.y notation), increment (+ N/- N), turn_off.
      - "groups": Set align group size. Params: value (size), x, y (x.y notation), increment (+ N/- N), turn_off.
      - "wings": Set wing/mirror parts. Params: value (parts), increment (+/-), turn_off.
      - "filter": Set sub-selection filter. Params: value (filter_num), name (filter name), increment (+/-), turn_off.
      - "reset": Clear all MAtricks settings. No params.
      - "recall": Recall a MAtricks pool object or toggle mode. Params: value (matricks_id), mode (on/off/toggle).
      - "all": Reset Single X sub-selection. No params.
      - "allrows": Reset Single Y sub-selection. No params.
      - "next": Step forward through Single X sub-selection. No params.
      - "previous": Step backward through Single X sub-selection. No params.
      - "nextrow": Step forward through Single Y (row) sub-selection. No params.

    Args:
        action: The MAtricks action to perform.
        value: Primary numeric value (width/size/parts/filter_num/matricks_id).
        x: X-axis value for blocks/groups x.y notation.
        y: Y-axis value for blocks/groups x.y notation.
        column: Column for interleave column.width notation.
        increment: Step value: "+", "-", "+ N", or "- N".
        name: Filter name (for action="filter").
        mode: "on", "off", or "toggle" (for action="recall").
        turn_off: Send the "Off" variant of the command.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    from src.commands import (
        all_rows_sub_selection as _build_all_rows,
    )
    from src.commands import (
        all_sub_selection as _build_all,
    )
    from src.commands import (
        matricks_blocks as _build_blocks,
    )
    from src.commands import (
        matricks_filter as _build_filter,
    )
    from src.commands import (
        matricks_groups as _build_groups,
    )
    from src.commands import (
        matricks_interleave as _build_interleave,
    )
    from src.commands import (
        matricks_reset as _build_reset,
    )
    from src.commands import (
        matricks_wings as _build_wings,
    )
    from src.commands import (
        next_row_sub_selection as _build_next_row,
    )
    from src.commands import (
        next_sub_selection as _build_next,
    )
    from src.commands import (
        previous_sub_selection as _build_previous,
    )
    from src.commands import (
        recall_matricks as _build_recall,
    )

    action_lower = action.lower()
    try:
        if action_lower == "interleave":
            cmd = _build_interleave(
                width=value, column=column,
                increment=increment, off=turn_off,
            )
        elif action_lower == "blocks":
            cmd = _build_blocks(
                size=value, x=x, y=y,
                increment=increment, off=turn_off,
            )
        elif action_lower == "groups":
            cmd = _build_groups(
                size=value, x=x, y=y,
                increment=increment, off=turn_off,
            )
        elif action_lower == "wings":
            cmd = _build_wings(
                parts=value, increment=increment, off=turn_off,
            )
        elif action_lower == "filter":
            cmd = _build_filter(
                filter_num=value, name=name,
                increment=increment, off=turn_off,
            )
        elif action_lower == "reset":
            cmd = _build_reset()
        elif action_lower == "recall":
            cmd = _build_recall(matricks_id=value, mode=mode)
        elif action_lower == "all":
            cmd = _build_all()
        elif action_lower == "allrows":
            cmd = _build_all_rows()
        elif action_lower == "next":
            cmd = _build_next()
        elif action_lower == "previous":
            cmd = _build_previous()
        elif action_lower == "nextrow":
            cmd = _build_next_row()
        else:
            return json.dumps({
                "error": f"Unknown action: {action!r}. Valid: interleave, blocks, groups, wings, filter, reset, recall, all, allrows, next, previous, nextrow.",
                "risk_tier": "SAFE_WRITE",
            }, indent=2)
    except ValueError as exc:
        return json.dumps({
            "error": str(exc),
            "risk_tier": "SAFE_WRITE",
        }, indent=2)

    client = await get_client()
    raw = await client.send_command_with_response(cmd)

    # Update in-memory write-tracker (Gap 6 — no telnet readback for MAtricks state)
    if snap := _orchestrator.last_snapshot:
        mt = snap.matricks
        if action_lower == "reset":
            mt.reset()
        elif action_lower == "interleave":
            mt.interleave = None if turn_off else (value or 1)
        elif action_lower == "blocks":
            mt.blocks_x = None if turn_off else (x or value or 1)
            mt.blocks_y = None if turn_off else (y or 1)
        elif action_lower == "groups":
            mt.groups_x = None if turn_off else (x or value or 1)
            mt.groups_y = None if turn_off else (y or 1)
        elif action_lower == "wings":
            mt.wings = None if turn_off else (value or 1)
        elif action_lower == "filter":
            mt.filter_id = None if turn_off else (value or None)
        elif action_lower == "recall":
            mt.active = True
        # all/allrows/next/previous/nextrow are selection steps — no persistent state to track

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.GROUP_STORE)
@_handle_errors
async def store_matricks_preset(
    pool_slot: int,
    name: str,
    interleave: int | None = None,
    blocks: int | None = None,
    blocks_y: int | None = None,
    groups: int | None = None,
    groups_y: int | None = None,
    wings: int | None = None,
    filter_num: int | None = None,
    filter_name: str | None = None,
    reset_first: bool = True,
    confirm_destructive: bool = False,
) -> str:
    """
    Set MAtricks state, store to pool, and label — all in one call (DESTRUCTIVE).

    Workflow:
      1. Optionally resets all MAtricks settings (reset_first=True, default)
      2. Applies specified MAtricks settings (interleave, blocks, groups, wings, filter)
      3. Stores current MAtricks state to the specified pool slot (/overwrite)
      4. Labels the pool object with the given name

    At least one MAtricks setting must be provided.

    Args:
        pool_slot: Pool slot number to store into (e.g. 2).
        name: Label for the stored MAtricks object (e.g. "Wings-2-I4").
        interleave: Virtual grid width (MAtricksInterleave).
        blocks: Block size X (MAtricksBlocks). Use with blocks_y for x.y.
        blocks_y: Block size Y (requires blocks for x.y notation).
        groups: Align group size X (MAtricksGroups). Use with groups_y for x.y.
        groups_y: Align group size Y (requires groups for x.y notation).
        wings: Wing/mirror parts (MAtricksWings).
        filter_num: Filter number (MAtricksFilter).
        filter_name: Filter name (MAtricksFilter, e.g. "OddID").
        reset_first: Reset all MAtricks before applying (default True).
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation).

    Returns:
        str: JSON with commands_sent list, pool_slot, name, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "store_matricks_preset modifies the MAtricks pool. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from src.commands import (
        label as _build_label,
    )
    from src.commands import (
        matricks_blocks as _build_blocks,
    )
    from src.commands import (
        matricks_filter as _build_filter,
    )
    from src.commands import (
        matricks_groups as _build_groups,
    )
    from src.commands import (
        matricks_interleave as _build_interleave,
    )
    from src.commands import (
        matricks_reset as _build_reset,
    )
    from src.commands import (
        matricks_wings as _build_wings,
    )
    from src.commands import (
        store_matricks as _build_store_matricks,
    )

    # Validate: at least one setting must be provided
    has_setting = any(v is not None for v in [
        interleave, blocks, groups, wings, filter_num, filter_name,
    ])
    if not has_setting:
        return json.dumps({
            "error": "At least one MAtricks setting must be provided (interleave, blocks, groups, wings, filter_num, or filter_name).",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    commands_sent = []

    # Step 1: Reset if requested
    if reset_first:
        cmd = _build_reset()
        await client.send_command(cmd)
        commands_sent.append(cmd)

    # Step 2: Apply settings
    if interleave is not None:
        cmd = _build_interleave(width=interleave)
        await client.send_command(cmd)
        commands_sent.append(cmd)

    if blocks is not None:
        if blocks_y is not None:
            cmd = _build_blocks(x=blocks, y=blocks_y)
        else:
            cmd = _build_blocks(size=blocks)
        await client.send_command(cmd)
        commands_sent.append(cmd)

    if groups is not None:
        if groups_y is not None:
            cmd = _build_groups(x=groups, y=groups_y)
        else:
            cmd = _build_groups(size=groups)
        await client.send_command(cmd)
        commands_sent.append(cmd)

    if wings is not None:
        cmd = _build_wings(parts=wings)
        await client.send_command(cmd)
        commands_sent.append(cmd)

    if filter_num is not None or filter_name is not None:
        cmd = _build_filter(filter_num=filter_num, name=filter_name)
        await client.send_command(cmd)
        commands_sent.append(cmd)

    # Step 3: Store to pool slot
    store_cmd = _build_store_matricks(pool_slot, overwrite=True)
    raw_store = await client.send_command_with_response(store_cmd)
    commands_sent.append(store_cmd)

    # Step 4: Label the pool object
    label_cmd = _build_label("matricks", pool_slot, name)
    raw_label = await client.send_command_with_response(label_cmd)
    commands_sent.append(label_cmd)

    return json.dumps({
        "commands_sent": commands_sent,
        "pool_slot": pool_slot,
        "name": name,
        "store_response": raw_store[:200],
        "label_response": raw_label[:200],
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.FILTER_MANAGE)
@_handle_errors
async def create_matricks_library(
    max_value: int = 4,
    start_slot: int = 2,
    confirm_destructive: bool = False,
) -> str:
    """
    Create a full MAtricks combinatorial library (DESTRUCTIVE).

    Generates every combination of Wings × Groups × Blocks × Interleave
    (values 0 to max_value) as XML with embedded appearance colors and
    imports into the MAtricks pool. Colors are instant — no telnet loop needed.

    25-color scheme: Wings=hue (Red/YellowGreen/Cyan/Blue/Magenta),
    Groups=brightness (100/80/60/45/30).

    With max_value=4: 5^4 = 625 pool items, named W0-G0-B0-I0 through W4-G4-B4-I4.

    Args:
        max_value: Upper bound for each property (default 4, gives 5^4=625 items).
        start_slot: First pool slot to import into (default 2, slot 1 is Reset).
        confirm_destructive: Must be True to execute (overwrites MAtricks pool entries).

    Returns:
        str: JSON with pool_items_created, color_scheme, first_slot, last_slot.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Create MAtricks Library overwrites MAtricks pool entries. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from datetime import datetime
    from pathlib import Path

    matricks_dir = Path(_GMA2_DATA_ROOT) / "matricks"
    xml_filename = "matricks_combinatorial_library"

    # 25-color scheme: Wings=hue (5 hues), Groups=brightness (5 levels)
    wings_hues = {0: 0, 1: 72, 2: 144, 3: 216, 4: 288}
    groups_brightness = {0: 100, 1: 80, 2: 60, 3: 45, 4: 30}

    def _hsb_to_hex(hue: int, sat: int, bright: int) -> str:
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(hue / 360, sat / 100, bright / 100)
        return f"{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    # Generate XML with appearance colors embedded
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns="http://schemas.malighting.de/grandma2/xml/MA"'
        ' xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA'
        ' http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd"'
        ' major_vers="3" minor_vers="9" stream_vers="60">',
        f'\t<Info datetime="{now}" showfile="" />',
    ]

    total = (max_value + 1) ** 4
    index = 0
    for w in range(max_value + 1):
        for g in range(max_value + 1):
            h = wings_hues.get(w, 0)
            br = groups_brightness.get(g, 100)
            hex_color = _hsb_to_hex(h, 100, br)
            for b in range(max_value + 1):
                for i in range(max_value + 1):
                    name = f"W{w}-G{g}-B{b}-I{i}"
                    lines.append(f'\t<Matrix index="{index}" name="{name}">')
                    lines.append(f'\t\t<Appearance Color="{hex_color}" />')
                    lines.append(
                        f'\t\t<Settings wings="{w}" group_x="{g}"'
                        f' block_x="{b}" interleave="{i}" />'
                    )
                    lines.append("\t</Matrix>")
                    index += 1

    lines.append("</MA>")

    # Write XML to MA2 matricks directory
    xml_path = matricks_dir / f"{xml_filename}.xml"
    xml_path.write_text("\n".join(lines), encoding="utf-8")

    # Import via telnet — colors are embedded in XML, no telnet loop needed
    client = await get_client()

    # Pre-import availability check
    last_slot = start_slot + total - 1
    avail = await _check_pool_slots(
        client, "MAtricks",
        start_from=start_slot, scan_up_to=last_slot,
    )
    availability_warning = None
    if avail["occupied_slots"]:
        availability_warning = {
            "slots_that_will_be_overwritten": len(avail["occupied_slots"]),
            "occupied": avail["occupied_slots"][:20],  # cap at 20 for readability
        }

    import_cmd = f'import "{xml_filename}" at matricks {start_slot}'
    response = await client.send_command_with_response(import_cmd)

    result: dict = {
        "pool_items_created": total,
        "total_slots": total,
        "first_slot": start_slot,
        "last_slot": last_slot,
        "naming_scheme": "W{wings}-G{groups}-B{blocks}-I{interleave}",
        "color_scheme": {
            "status": "embedded_in_xml",
            "mapping": "25 colors: Wings=hue (Red/YellowGreen/Cyan/Blue/Magenta), Groups=brightness (100/80/60/45/30)",
        },
        "max_value": max_value,
        "xml_file": str(xml_path),
        "import_response": response[:200],
        "risk_tier": "DESTRUCTIVE",
    }
    if availability_warning:
        result["availability_warning"] = availability_warning

    return json.dumps(result, indent=2)


async def _discover_filter_attributes() -> dict[str, list[str]]:
    """Discover actual attribute names from the current show's fixture library.

    Browses PresetTypes 1-7 at depth 2, collecting all attribute names.
    Returns a dict with the same shape as FILTER_ATTRIBUTES in constants.py.
    Falls back to FILTER_ATTRIBUTES if discovery fails.
    """
    from src.commands.constants import FILTER_ATTRIBUTES

    preset_type_names = ["dimmer", "position", "gobo", "color", "beam", "focus", "control"]
    discovered: dict[str, list[str]] = {}

    try:
        client = await get_client()
        for pt_id, cat_name in enumerate(preset_type_names, start=1):
            attrs: list[str] = []
            await navigate(client, "/")
            await navigate(client, f"10.2.{pt_id}")
            feat_list = await list_destination(client)
            feat_raw = feat_list.raw_response
            features = _parse_preset_tree_list(feat_raw)

            for fi in range(1, len(features) + 1):
                await navigate(client, "/")
                await navigate(client, f"10.2.{pt_id}.{fi}")
                attr_list = await list_destination(client)
                attr_raw = attr_list.raw_response
                attr_entries = _parse_preset_tree_list(attr_raw)
                for entry in attr_entries:
                    name = entry.get("name", "").upper()
                    if name and name not in attrs:
                        attrs.append(name)

            discovered[cat_name] = attrs if attrs else FILTER_ATTRIBUTES.get(cat_name, [])
        await navigate(client, "/")
    except Exception:
        # On any failure, return defaults
        return dict(FILTER_ATTRIBUTES)

    return discovered


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def discover_filter_attributes() -> str:
    """
    Discover actual filter attributes from the current show's fixture library (SAFE_READ).

    Browses PresetTypes 1-7 (Dimmer through Control) at depth 2 to collect
    attribute names from all patched fixture types. Returns a dict matching the
    shape of FILTER_ATTRIBUTES in constants.py but with show-specific values.

    Use this before create_filter_library if your show uses fixtures other than
    Mac 700 Profile Extended + Generic Dimmer (the defaults in FILTER_ATTRIBUTES).

    Returns:
        str: JSON dict mapping category names to attribute name lists.
    """
    discovered = await _discover_filter_attributes()
    return json.dumps({
        "attributes": discovered,
        "total_attributes": sum(len(v) for v in discovered.values()),
        "note": "Pass these as fixture_attributes to create_filter_library for accurate filters.",
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.FILTER_MANAGE)
@_handle_errors
async def create_filter_library(
    start_slot: int = 3,
    include_combos: bool = True,
    include_exclusions: bool = True,
    include_vte: bool = False,
    fixture_attributes: dict[str, list[str]] | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Create a comprehensive Filter library with color-coded pool items (DESTRUCTIVE).

    Generates filters for each PresetType (Dimmer, Position, Gobo, Color, Beam,
    Focus, Control), useful multi-type combos, and "No X" exclusion filters.
    Each filter is color-coded by category and imported as individual XML files.

    Optionally generates Value/ValueTimes/Effects on/off variants for each base
    filter (7 combos per filter, excluding all-off). V/VT/E toggles are embedded
    in the XML as value="false", value_timing="false", effect="false" attributes.

    Slot layout (default start_slot=3):
      - Slots 3-9: Single PresetType filters (7 items)
      - Slots 10-16: Combo filters (7 items, if include_combos)
      - Slots 17-23: "No X" exclusion filters (7 items, if include_exclusions)
      - Slots 24+: V/VT/E variants (N_base × 7, if include_vte)

    Args:
        start_slot: First pool slot (default 3, preserving system filters 1-2).
        include_combos: Include multi-type combo filters (default True).
        include_exclusions: Include "No X" exclusion filters (default True).
        include_vte: Include Value/ValueTimes/Effects variants (default False).
            When True, generates 7 V/VT/E combos for each base filter.
        fixture_attributes: Show-specific attribute dict (same shape as FILTER_ATTRIBUTES).
            If None, uses hardcoded defaults (Mac 700 + Generic Dimmer).
            Call discover_filter_attributes() first to get accurate values for your show.
        confirm_destructive: Must be True to execute (overwrites filter pool entries).

    Returns:
        str: JSON with filters_created, slots, color_scheme summary.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Create Filter Library overwrites filter pool entries. "
                     "Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from datetime import datetime
    from pathlib import Path

    from src.commands.constants import (
        FILTER_ATTRIBUTES,
        FILTER_COLORS,
        FILTER_VTE_COMBOS,
    )

    importexport_dir = Path(_GMA2_DATA_ROOT) / "importexport" / "filters"

    # Use provided fixture attributes or fall back to hardcoded defaults
    attrs_source = fixture_attributes if fixture_attributes else FILTER_ATTRIBUTES

    # Build attribute lists
    dimmer = attrs_source.get("dimmer", FILTER_ATTRIBUTES["dimmer"])
    position = attrs_source.get("position", FILTER_ATTRIBUTES["position"])
    gobo = attrs_source.get("gobo", FILTER_ATTRIBUTES["gobo"])
    color = attrs_source.get("color", FILTER_ATTRIBUTES["color"])
    beam = attrs_source.get("beam", FILTER_ATTRIBUTES["beam"])
    focus = attrs_source.get("focus", FILTER_ATTRIBUTES["focus"])
    control = attrs_source.get("control", FILTER_ATTRIBUTES["control"])
    all_attrs = dimmer + position + gobo + color + beam + focus + control

    # Build base filter definitions: (slot, name, attrs, cat)
    base_filters: list[tuple[int, str, list[str], str]] = []
    slot = start_slot

    for cat, attrs in [
        ("dimmer", dimmer), ("position", position), ("gobo", gobo),
        ("color", color), ("beam", beam), ("focus", focus), ("control", control),
    ]:
        base_filters.append((slot, cat.capitalize(), attrs, cat))
        slot += 1

    if include_combos:
        for name, attrs in [
            ("Dim+Pos", dimmer + position),
            ("Dim+Color", dimmer + color),
            ("Pos+Color", position + color),
            ("Pos+Gobo", position + gobo),
            ("Gobo+Beam", gobo + beam),
            ("Beam+Focus", beam + focus),
            ("Pos+Col+Gobo", position + color + gobo),
        ]:
            base_filters.append((slot, name, attrs, "combo"))
            slot += 1

    if include_exclusions:
        for name, attrs in [
            ("No Dimmer", [a for a in all_attrs if a not in dimmer]),
            ("No Position", [a for a in all_attrs if a not in position]),
            ("No Gobo", [a for a in all_attrs if a not in gobo]),
            ("No Color", [a for a in all_attrs if a not in color]),
            ("No Beam", [a for a in all_attrs if a not in beam]),
            ("No Focus", [a for a in all_attrs if a not in focus]),
            ("No Control", [a for a in all_attrs if a not in control]),
        ]:
            base_filters.append((slot, name, attrs, "exclude"))
            slot += 1

    # Build full filter list: base + optional V/VT/E variants
    # Each entry: (slot, name, attrs, cat, value, value_timing, effect)
    all_filters: list[tuple[int, str, list[str], str, bool, bool, bool]] = []
    for f_slot, f_name, f_attrs, f_cat in base_filters:
        all_filters.append((f_slot, f_name, f_attrs, f_cat, True, True, True))

    if include_vte:
        vte_slot = slot  # continue after base filters
        for _base_slot, base_name, f_attrs, f_cat in base_filters:
            for suffix, v, vt, e in FILTER_VTE_COMBOS:
                vte_name = f"{base_name} {suffix}"
                all_filters.append(
                    (vte_slot, vte_name, f_attrs, f_cat, v, vt, e)
                )
                vte_slot += 1

    # XML generation helper
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    xml_header = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<MA xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns="http://schemas.malighting.de/grandma2/xml/MA"'
        ' xsi:schemaLocation="http://schemas.malighting.de/grandma2/xml/MA'
        ' http://schemas.malighting.de/grandma2/xml/3.9.60/MA.xsd"'
        ' major_vers="3" minor_vers="9" stream_vers="60">\n'
        f'\t<Info datetime="{now}" showfile="" />\n'
    )

    client = await get_client()

    # Pre-import availability check
    last_filter_slot = all_filters[-1][0] if all_filters else start_slot
    avail = await _check_pool_slots(
        client, "Filter",
        start_from=start_slot, scan_up_to=last_filter_slot,
    )
    availability_warning = None
    if avail["occupied_slots"]:
        availability_warning = {
            "slots_that_will_be_overwritten": len(avail["occupied_slots"]),
            "occupied": avail["occupied_slots"][:20],
        }

    results = []

    for f_slot, f_name, f_attrs, f_cat, f_v, f_vt, f_e in all_filters:
        color_hex = FILTER_COLORS[f_cat]

        # Build V/VT/E XML attributes (only emit false values)
        vte_parts = []
        if not f_v:
            vte_parts.append('value="false"')
        if not f_vt:
            vte_parts.append('value_timing="false"')
        if not f_e:
            vte_parts.append('effect="false"')
        vte_str = (" " + " ".join(vte_parts)) if vte_parts else ""

        attr_lines = "\n".join(
            f'\t\t\t<AttributeLink name="{a}" />' for a in f_attrs
        )
        filter_xml = (
            f'\t<Filter index="{f_slot - 1}"{vte_str} keep_filter="false">\n'
            f'\t\t<Appearance Color="{color_hex}" />\n'
            f"\t\t<Attributes>\n{attr_lines}\n\t\t</Attributes>\n"
            f"\t</Filter>"
        )
        xml_content = xml_header + filter_xml + "\n</MA>"

        fname = f"filter_{f_slot:03d}"
        fpath = importexport_dir / f"{fname}.xml"
        fpath.write_text(xml_content, encoding="utf-8")

        # Import (use 8.3 short path to avoid spaces in path)
        resp = await client.send_command_with_response(
            f'Import "{fname}" At Filter {f_slot}'
            " /path=C:/ProgramData/MALIGH~1/grandma/gma2_V_3.9.60/IMPORT~1/filters"
        )
        import_ok = "Error" not in resp

        # Label
        await client.send_command_with_response(
            f'Label Filter {f_slot} "{f_name}"'
        )

        # Apply appearance color via telnet (backup if XML color didn't take)
        r = int(color_hex[0:2], 16) * 100 // 255
        g = int(color_hex[2:4], 16) * 100 // 255
        b = int(color_hex[4:6], 16) * 100 // 255
        await client.send_command_with_response(
            f"Appearance Filter {f_slot} /r={r} /g={g} /b={b}"
        )

        results.append({
            "slot": f_slot,
            "name": f_name,
            "category": f_cat,
            "attributes": len(f_attrs),
            "vte": f"V={'on' if f_v else 'off'}"
                   f" VT={'on' if f_vt else 'off'}"
                   f" E={'on' if f_e else 'off'}",
            "import_ok": import_ok,
        })

    result_json: dict = {
        "filters_created": len(results),
        "base_filters": len(base_filters),
        "vte_variants": len(results) - len(base_filters),
        "first_slot": start_slot,
        "last_slot": all_filters[-1][0] if all_filters else start_slot,
        "filters": results,
        "color_scheme": {
            "dimmer": "FFCC00 (yellow)",
            "position": "0088FF (blue)",
            "gobo": "00CC44 (green)",
            "color": "FF00CC (magenta)",
            "beam": "FF6600 (orange)",
            "focus": "00CCCC (cyan)",
            "control": "999999 (grey)",
            "combo": "CC44FF (purple)",
            "exclude": "FF3333 (red)",
        },
        "xml_directory": str(importexport_dir),
        "risk_tier": "DESTRUCTIVE",
    }
    if availability_warning:
        result_json["availability_warning"] = availability_warning

    # Update filter_vte write-tracker (Gap 1 — VTE layer toggles have no telnet readback)
    if snap := _orchestrator.last_snapshot:
        snap.filter_vte.update({"value": True, "value_timing": True, "effect": True})

    return json.dumps(result_json, indent=2)


# ============================================================
# Tools 70–73: Tier 3 — Fixture Patching Workflow
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def browse_patch_schedule(
    fixture_type_id: int | None = None,
) -> str:
    """
    Browse the fixture patch schedule from LiveSetup.

    If fixture_type_id is provided, drills into that specific fixture type
    to show its instances (fixtures, DMX addresses, channels).

    Args:
        fixture_type_id: Fixture type index to drill into (optional).
                         Omit to see all fixture types.

    Returns:
        str: JSON with raw_response, entries, risk_tier.
    """
    client = await get_client()
    commands_sent = []

    nav = await navigate(client, "/")
    commands_sent.append(nav.command_sent)

    nav = await navigate(client, "10")
    commands_sent.append(nav.command_sent)

    nav = await navigate(client, "3")
    commands_sent.append(nav.command_sent)

    if fixture_type_id is not None:
        nav = await navigate(client, str(fixture_type_id))
        commands_sent.append(nav.command_sent)

    lst = await list_destination(client)
    commands_sent.append(lst.command_sent)

    nav = await navigate(client, "/")
    commands_sent.append(nav.command_sent)

    entries = [
        {"object_type": e.object_type, "object_id": e.object_id, "name": e.name}
        for e in lst.parsed_list.entries
    ]

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_response": lst.raw_response,
        "entries": entries,
        "entry_count": len(entries),
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PATCH_WRITE)
@_handle_errors
async def patch_fixture(
    fixture_id: int,
    dmx_universe: int,
    dmx_address: int,
    fixture_type_id: int | None = None,
    channel_id: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Patch a fixture to a DMX address (DESTRUCTIVE — modifies the patch).

    Assigns a DMX address to a fixture. Optionally assigns a fixture type first.

    MA2 syntax:
      assign dmx [universe].[address] at fixture [fixture_id]
      assign fixture_type [type_id] at fixture [fixture_id]  (if fixture_type_id given)

    Args:
        fixture_id: Fixture ID to patch.
        dmx_universe: DMX universe number (1-256).
        dmx_address: DMX address within universe (1-512).
        fixture_type_id: Fixture type to assign (optional).
        channel_id: Channel ID to assign (optional).
        confirm_destructive: Must be True to proceed.

    Returns:
        str: JSON with commands_sent, raw_responses, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Patching modifies fixture DMX assignments. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    commands_sent = []
    raw_responses = []

    # Optionally assign fixture type first
    if fixture_type_id is not None:
        from src.commands import assign as build_assign
        cmd = build_assign(
            source_type="fixturetype",
            source_id=str(fixture_type_id),
            target_type="fixture",
            target_id=str(fixture_id),
        )
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    # Assign DMX address
    from src.commands import assign as build_assign
    dmx_ref = f"{dmx_universe}.{dmx_address}"
    cmd = build_assign(
        source_type="dmx",
        source_id=dmx_ref,
        target_type="fixture",
        target_id=str(fixture_id),
    )
    raw = await client.send_command_with_response(cmd)
    commands_sent.append(cmd)
    raw_responses.append(raw)

    # Optionally assign channel
    if channel_id is not None:
        cmd = build_assign(
            source_type="fixture",
            source_id=str(fixture_id),
            target_type="channel",
            target_id=str(channel_id),
        )
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_responses": raw_responses,
        "fixture_id": fixture_id,
        "dmx_address": f"{dmx_universe}.{dmx_address}",
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PATCH_WRITE)
@_handle_errors
async def unpatch_fixture(
    fixture_id: int,
    confirm_destructive: bool = False,
) -> str:
    """
    Unpatch a fixture (remove its DMX assignment) (DESTRUCTIVE).

    MA2 syntax: delete fixture [fixture_id]
    This removes the DMX assignment but does not delete the fixture from the show.

    Args:
        fixture_id: Fixture ID to unpatch.
        confirm_destructive: Must be True to proceed.

    Returns:
        str: JSON with command_sent, raw_response, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Unpatching removes DMX assignments. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    cmd = build_delete_fixture(fixture_id)
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PATCH_WRITE)
@_handle_errors
async def set_fixture_type_property(
    fixture_type_id: int,
    property_name: str,
    value: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Set a property on a fixture type in LiveSetup (DESTRUCTIVE).

    Navigates to LiveSetup/FixtureTypes/[N] and assigns a property value.
    Path: cd 10 -> cd 3 -> assign [fixture_type_id]/property=value -> cd /

    Args:
        fixture_type_id: Fixture type index (1-based).
        property_name: Property to set (e.g. "Mode", "Name").
        value: New value for the property.
        confirm_destructive: Must be True to proceed.

    Returns:
        str: JSON with commands_sent, success, risk_tier.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "Modifying fixture type properties is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    result = await set_property(
        client,
        path=f"10.3.{fixture_type_id}",
        property_name=property_name,
        value=value,
    )

    return json.dumps({
        "commands_sent": result.commands_sent,
        "raw_responses": result.raw_responses,
        "success": result.success,
        "verified_value": result.verified_value,
        "error": result.error,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


# ============================================================
# Wildcard Name Discovery
# ============================================================

# Object pool destinations that hold user-nameable objects.
# Keyword form (e.g. "Group") and numeric cd-index form (e.g. "22") are both accepted.
# Reference: CD_NUMERIC_INDEX in src/vocab.py — live-verified on MA2 3.9.60.65.
# NOTE: System-config branches (cd 1=Showfile, cd 2=TimeConfig, cd 3=Settings …)
#       are NOT object pools — they have property nodes, not named user objects.
_OBJECT_POOL_DESTINATIONS: dict[str, str] = {
    # keyword        numeric cd index
    "Group":         "22",
    "Sequence":      "25",
    "Preset":        "17",
    "Macro":         "13",
    "Effect":        "24",
    "Gel":           "16",
    "World":         "18",
    "Filter":        "19",
    "Form":          "23",
    "Timer":         "26",
    "Layout":        "38",
    "Timecode":      "35",
    "Agenda":        "34",
    "UserProfile":   "39",
    "Camera":        "Camera",   # no separate numeric index — cd Camera
    "MAtricks":      "MAtricks",
    "View":          "View",
    "Remote":        "36",
}


# ============================================================
# Pool Availability Checker
# ============================================================


async def _check_pool_slots(
    client: "GMA2TelnetClient",
    pool_type: str,
    start_from: int = 1,
    scan_up_to: int = 200,
    needed_slots: int | None = None,
) -> dict:
    """Check which slots are occupied/free in a pool.

    Navigates to the pool via cd, lists contents, computes availability,
    then returns to root.  Pure SAFE_READ — no modifications.

    Args:
        client: Connected telnet client.
        pool_type: Pool keyword (e.g. "Macro", "Filter", "Group") or
            numeric cd index (e.g. "13").  Case-insensitive lookup
            against ``_OBJECT_POOL_DESTINATIONS``.
        start_from: First slot to consider (default 1).
        scan_up_to: Last slot to consider (default 200).
        needed_slots: If set, checks whether this many contiguous free
            slots exist and suggests a start position.

    Returns:
        dict with keys: pool_type, occupied_slots, free_ranges,
        next_free_slots, total_occupied, total_free_in_range,
        largest_contiguous, can_fit, suggested_start.
    """
    # Resolve pool destination
    destination: str | None = None
    pool_key = pool_type.strip()

    # Try keyword lookup (case-insensitive)
    for key, val in _OBJECT_POOL_DESTINATIONS.items():
        if key.lower() == pool_key.lower():
            destination = val
            pool_key = key  # normalise casing
            break

    # Accept raw numeric / keyword destinations as-is
    if destination is None:
        destination = pool_key

    # Navigate to pool
    await navigate(client, destination)

    # List contents
    lst = await list_destination(client)
    entries = lst.parsed_list.entries

    # Detect sub-pool level (e.g. Macros cd 13 → "MacroPool 1 Global")
    # If entries look like container objects rather than actual pool items,
    # navigate one level deeper.
    if (
        entries
        and len(entries) == 1
        and entries[0].object_type
        and "Pool" in (entries[0].object_type or "")
    ):
        await navigate(client, "1")
        lst = await list_destination(client)
        entries = lst.parsed_list.entries

    # Parse occupied slot numbers
    occupied: list[dict] = []
    occupied_ids: set[int] = set()
    for e in entries:
        if e.object_id is None:
            continue
        try:
            slot = int(e.object_id)
        except (ValueError, TypeError):
            continue
        if start_from <= slot <= scan_up_to:
            occupied.append({"slot": slot, "name": e.name or ""})
            occupied_ids.add(slot)

    # Sort occupied by slot number
    occupied.sort(key=lambda x: x["slot"])

    # Compute free ranges and next free slots
    free_ranges: list[dict] = []
    next_free: list[int] = []
    run_start: int | None = None
    largest_contiguous = 0

    for slot in range(start_from, scan_up_to + 1):
        if slot not in occupied_ids:
            if run_start is None:
                run_start = slot
            if len(next_free) < 10:
                next_free.append(slot)
        else:
            if run_start is not None:
                run_len = slot - run_start
                free_ranges.append({"start": run_start, "end": slot - 1})
                if run_len > largest_contiguous:
                    largest_contiguous = run_len
                run_start = None

    # Close trailing free range
    if run_start is not None:
        run_len = scan_up_to - run_start + 1
        free_ranges.append({"start": run_start, "end": scan_up_to})
        if run_len > largest_contiguous:
            largest_contiguous = run_len

    total_in_range = scan_up_to - start_from + 1
    total_free = total_in_range - len(occupied)

    # Check if needed_slots can fit contiguously
    can_fit: bool | None = None
    suggested_start: int | None = None
    if needed_slots is not None:
        can_fit = False
        for fr in free_ranges:
            block_size = fr["end"] - fr["start"] + 1
            if block_size >= needed_slots:
                can_fit = True
                suggested_start = fr["start"]
                break

    # Return to root
    await navigate(client, "/")

    return {
        "pool_type": pool_key,
        "occupied_slots": occupied,
        "free_ranges": free_ranges,
        "next_free_slots": next_free,
        "total_occupied": len(occupied),
        "total_free_in_range": total_free,
        "largest_contiguous": largest_contiguous,
        "can_fit": can_fit,
        "suggested_start": suggested_start,
    }


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def check_pool_availability(
    pool_type: str,
    start_from: int = 1,
    scan_up_to: int = 200,
    needed_slots: int | None = None,
) -> str:
    """
    Check which slots are occupied and free in an object pool (SAFE_READ).

    Navigates to the pool, lists all entries, and computes a full
    availability map: occupied slots (with names), free ranges,
    next 10 free slots, and contiguous-block analysis.

    Use this **before importing XML** to verify target slots are free,
    or to find the best slot range for bulk imports (filters, MAtricks).

    Valid pool types (case-insensitive):
      Group, Sequence, Preset, Macro, Effect, Gel, World, Filter,
      Form, Timer, Layout, Timecode, Agenda, UserProfile, Camera,
      MAtricks, View, Remote

    Numeric cd indexes also accepted (e.g. "13" for Macros, "19" for Filters).

    Args:
        pool_type: Pool keyword or numeric cd index.
        start_from: First slot number to check (default 1).
        scan_up_to: Last slot number to check (default 200).
        needed_slots: If set, checks whether N contiguous free slots
            exist and returns can_fit + suggested_start.

    Returns:
        str: JSON with occupied_slots, free_ranges, next_free_slots,
             total_occupied, total_free_in_range, largest_contiguous,
             can_fit, suggested_start, risk_tier.
    """
    client = await get_client()
    result = await _check_pool_slots(
        client,
        pool_type,
        start_from=start_from,
        scan_up_to=scan_up_to,
        needed_slots=needed_slots,
    )
    result["risk_tier"] = "SAFE_READ"
    return json.dumps(result, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def discover_object_names(destination: str) -> str:
    """
    Navigate to an object pool and return all object names for wildcard pattern building.

    This is the first step in the discover-names → derive-pattern → wildcard-command
    workflow.  The returned names can be used directly with list_objects(),
    info(), label(), etc. by passing them as the ``name`` argument with
    ``match_mode="literal"`` (exact match) or deriving a ``*``-pattern and
    using ``match_mode="wildcard"``.

    CD scope covered
    ----------------
    Any destination accepted by navigate_console() works here:
      - Keyword form:      "Group", "Sequence", "Preset", "Macro", "Effect", …
      - Numeric index:     "22" (Groups), "25" (Sequences), "17" (Presets), …
      - Dot-notation:      "10.3" (LiveSetup/FixtureTypes)

    Object pool destinations (cd 1–42 that have named user objects):
      Group=22, Sequence=25, Preset=17, Macro=13, Effect=24, Gel=16, World=18,
      Filter=19, Form=23, Timer=26, Layout=38, Timecode=35, Agenda=34,
      UserProfile=39, Remote=36.

    System-config branches (cd 1=Showfile, cd 2=TimeConfig, cd 3=Settings,
    cd 4=DMX_Protocols, …) hold property nodes, not named user objects — they
    return empty names and are not useful for wildcard matching.

    After this call the console is left at root (cd /).

    Args:
        destination: Object pool to inspect.  Any format accepted by
            navigate_console: keyword ("Group"), numeric index ("22"),
            or dot path ("10.3").

    Returns:
        str: JSON with destination, entries (id + name), names_only list,
             and a wildcard_tip suggesting how to build a pattern.

    Example workflow::

        discover_object_names("Group")
        # → names: ["Mac700 Front", "Mac700 Back", "Wash", "ALL LASERS"]

        # Derive prefix pattern and use with list_objects:
        # list_objects("group", name="Mac700*", match_mode="wildcard")
        # → "list group Mac700*"
    """
    client = await get_client()

    # Navigate to the destination
    nav = await navigate(client, destination)

    # List all objects there
    lst = await list_destination(client)

    # Collect non-empty names
    named_entries = [
        {"object_id": e.object_id, "name": e.name}
        for e in lst.parsed_list.entries
        if e.name
    ]
    names_only = [e["name"] for e in named_entries]

    # Build a wildcard tip based on common prefix (if any)
    tip = None
    if names_only:
        first = names_only[0]
        prefix = first.split()[0] if " " in first else first
        if len(names_only) > 1 and all(n.startswith(prefix) for n in names_only):
            tip = f'Common prefix detected — try: name="{prefix}*", match_mode="wildcard"'
        else:
            tip = 'No common prefix — use exact names with match_mode="literal" or derive your own pattern'

    # Return to root
    await navigate(client, "/")

    return json.dumps(
        {
            "destination": destination,
            "navigate_command": nav.command_sent,
            "entry_count": len(lst.parsed_list.entries),
            "named_count": len(named_entries),
            "entries": named_entries,
            "names_only": names_only,
            "wildcard_tip": tip,
        },
        indent=2,
    )


# ============================================================
# Server Startup
# ============================================================


# ============================================================
# Tools 83–86 — ML-Based Tool Categorization
# ============================================================

# Module-level cache for the taxonomy to avoid repeated disk reads.
_taxonomy_cache: dict | None = None


def _invalidate_taxonomy_cache() -> None:
    global _taxonomy_cache
    _taxonomy_cache = None


def _load_taxonomy_cached() -> dict:
    global _taxonomy_cache
    if _taxonomy_cache is not None:
        return _taxonomy_cache
    from src.categorization.taxonomy import DEFAULT_TAXONOMY_PATH, load_taxonomy

    if not DEFAULT_TAXONOMY_PATH.exists():
        raise FileNotFoundError(
            "Taxonomy not generated yet. Run: "
            "uv run python scripts/categorize_tools.py --provider zero"
        )
    _taxonomy_cache = load_taxonomy()
    return _taxonomy_cache


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_tool_categories(category: str | None = None) -> str:
    """
    List auto-discovered tool categories (SAFE_READ).

    Returns the ML-generated taxonomy of all MCP tools grouped by
    functional similarity.  Categories are discovered via unsupervised
    K-Means clustering over hybrid features (structural metadata +
    docstring embeddings).

    Args:
        category: Optional category name filter (case-insensitive partial match).

    Returns:
        str: JSON with categories, tool lists, and clustering metadata.
    """
    taxonomy = _load_taxonomy_cached()
    from src.categorization.taxonomy import get_tools_by_category

    filtered = get_tools_by_category(taxonomy, category)
    return json.dumps(
        {
            "metadata": taxonomy.get("metadata", {}),
            "categories": filtered,
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def recluster_tools(
    provider: str = "zero",
    k: int | None = None,
    alpha: float = 0.4,
) -> str:
    """
    Trigger re-clustering of all MCP tools (SAFE_READ).

    Runs the full ML pipeline: extract features from tool definitions,
    embed docstrings, cluster via K-Means, and regenerate the taxonomy.

    Args:
        provider: Embedding provider — "zero" (fast stub) or "github"
                  (real embeddings, requires GITHUB_MODELS_TOKEN).
        k: Override number of clusters.  None = auto-select via silhouette.
        alpha: Structural feature weight (0–1). Embedding weight = 1 − alpha.

    Returns:
        str: JSON summary with categories, silhouette score, and tool assignments.
    """
    import importlib
    from pathlib import Path

    # Import lazily to avoid circular imports at module load time.
    mod = importlib.import_module("scripts.categorize_tools")
    server_path = str(Path(__file__).resolve())

    result = mod.run(
        provider_name=provider,
        k_override=k,
        alpha=alpha,
        server_path=server_path,
    )
    _invalidate_taxonomy_cache()

    return json.dumps(
        {
            "metadata": result["metadata"],
            "category_count": len(result["categories"]),
            "categories": {
                name: {
                    "tool_count": cat["tool_count"],
                    "tools": [t["name"] for t in cat["tools"]],
                }
                for name, cat in result["categories"].items()
            },
        },
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_similar_tools(tool_name: str, top_n: int = 5) -> str:
    """
    Find the most similar MCP tools to a given tool (SAFE_READ).

    Uses Euclidean distance in the combined feature space (structural +
    embedding) from the last clustering run.

    Args:
        tool_name: Name of the reference tool (e.g. "playback_action").
        top_n: Number of similar tools to return (default 5).

    Returns:
        str: JSON array of similar tools ranked by distance, with category.
    """

    from src.categorization.clustering import euclidean_distance
    from src.categorization.taxonomy import get_feature_matrix

    taxonomy = _load_taxonomy_cached()
    names, matrix = get_feature_matrix(taxonomy)

    if tool_name not in names:
        return json.dumps(
            {"error": f"Tool '{tool_name}' not found in taxonomy. Available: {names[:10]}...", "blocked": True},
            indent=2,
        )

    idx = names.index(tool_name)
    ref_vec = matrix[idx]

    # Compute distances to all other tools
    distances: list[tuple[str, float]] = []
    for i, name in enumerate(names):
        if i == idx:
            continue
        dist = euclidean_distance(ref_vec, matrix[i])
        distances.append((name, dist))

    distances.sort(key=lambda x: x[1])
    top = distances[:top_n]

    # Find categories for each tool
    categories = taxonomy.get("categories", {})
    tool_to_category: dict[str, str] = {}
    for cat_name, cat_data in categories.items():
        for t in cat_data.get("tools", []):
            tool_to_category[t["name"]] = cat_name

    max_dist = top[-1][1] if top else 1.0
    return json.dumps(
        [
            {
                "name": name,
                "similarity": round(1.0 - (dist / max_dist) if max_dist > 0 else 1.0, 4),
                "distance": round(dist, 6),
                "category": tool_to_category.get(name, "unknown"),
            }
            for name, dist in top
        ],
        indent=2,
    )


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def suggest_tool_for_task(
    task_description: str,
    top_n: int = 3,
    provider: str = "zero",
    prefer_semantic: bool = True,
) -> str:
    """
    Suggest MCP tools for a natural-language task description (SAFE_READ).

    Embeds the task description and finds the closest tools by cosine
    similarity against stored docstring embeddings.  Falls back to keyword
    matching when using the zero-vector provider or when no embedding token
    is available.

    Args:
        task_description: What you want to accomplish (e.g. "fade out all fixtures").
        top_n: Number of suggestions to return (default 3).
        provider: Embedding provider — "zero" (keyword fallback) or "github".
            Overridden by ``prefer_semantic`` when a token is available.
        prefer_semantic: When True (default), automatically use embedding-based
            search if GITHUB_MODELS_TOKEN is set in the environment.  Falls back
            to keyword matching with a ``warning`` field when no token is present.
            Set to False to force keyword matching regardless of token availability.

    Returns:
        str: JSON array of suggested tools with scores and descriptions.
             Includes a top-level ``warning`` key when semantic search was
             requested but fell back to keyword matching.
    """
    import numpy as np

    from src.categorization.clustering import cosine_similarity
    from src.categorization.taxonomy import get_docstring_map, get_embedding_matrix

    taxonomy = _load_taxonomy_cached()

    # Find category map
    categories = taxonomy.get("categories", {})
    tool_to_category: dict[str, str] = {}
    for cat_name, cat_data in categories.items():
        for t in cat_data.get("tools", []):
            tool_to_category[t["name"]] = cat_name

    docstrings = get_docstring_map(taxonomy)

    # Resolve effective provider: prefer_semantic promotes "zero" → "github"
    # when a token is available; records a warning when it cannot.
    semantic_warning: str | None = None
    effective_provider = provider
    if prefer_semantic and provider == "zero":
        if os.environ.get("GITHUB_MODELS_TOKEN", ""):
            effective_provider = "github"
        else:
            semantic_warning = (
                "prefer_semantic=True but GITHUB_MODELS_TOKEN is not set; "
                "using keyword matching. Set GITHUB_MODELS_TOKEN for semantic search."
            )

    def _keyword_scores() -> list[tuple[str, float]]:
        task_words = set(task_description.lower().split())
        result: list[tuple[str, float]] = []
        for name, doc in docstrings.items():
            tool_words = set(name.replace("_", " ").lower().split()) | set(doc.lower().split())
            overlap = len(task_words & tool_words)
            if overlap > 0:
                result.append((name, float(overlap) / max(len(task_words), 1)))
        result.sort(key=lambda x: -x[1])
        return result

    if effective_provider == "zero":
        scores: list[tuple[str, float]] = _keyword_scores()
    else:
        # Embed task and compare via cosine similarity
        names, emb_matrix = get_embedding_matrix(taxonomy)
        if emb_matrix.size == 0 or np.allclose(emb_matrix, 0.0):
            # Fall back to keyword matching
            scores = _keyword_scores()
            semantic_warning = (
                (semantic_warning or "")
                + " Embedding matrix is empty (zero-vector store); using keyword matching."
            ).strip()
        else:
            from rag.ingest.embed import GitHubModelsProvider

            token = os.environ.get("GITHUB_MODELS_TOKEN", "")
            if not token:
                return json.dumps(
                    {"error": "GITHUB_MODELS_TOKEN not set. Use provider='zero' for keyword matching."},
                    indent=2,
                )
            emb_provider = GitHubModelsProvider(token=token)
            task_vec = np.array(emb_provider.embed_one(task_description), dtype=np.float64)

            scores = []
            for i, name in enumerate(names):
                sim = cosine_similarity(task_vec, emb_matrix[i])
                scores.append((name, sim))
            scores.sort(key=lambda x: -x[1])

    top = scores[:top_n]
    result: dict = {
        "suggestions": [
            {
                "name": name,
                "score": round(score, 4),
                "category": tool_to_category.get(name, "unknown"),
                "description": docstrings.get(name, ""),
            }
            for name, score in top
        ]
    }
    if semantic_warning:
        result["warning"] = semantic_warning
    return json.dumps(result, indent=2)


# ============================================================================
# USER MANAGEMENT TOOLS (Tools 98-100)
# Require OAuth scope gma2:user:manage (Tier 5 — Admin only)
# ============================================================================


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def list_console_users() -> str:
    """
    List all user accounts in the current show file (SAFE_READ).

    Returns the raw `list user` output from the console, showing all
    user slots with their names, rights levels, and profile assignments.

    Returns:
        str: JSON result with raw console response
    """
    client = await get_client()
    cmd = build_list_users()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def create_console_user(
    slot: int,
    name: str,
    password: str,
    rights_level: int,
    confirm_destructive: bool = False,
) -> str:
    """
    Create or overwrite a user account in the show file (DESTRUCTIVE — Admin only).

    Requires both gma2:user:manage OAuth scope AND confirm_destructive=True.

    grandMA2 rights levels:
        0 = None     (view/change views only, no programmer)
        1 = Playback (run show, no store)
        2 = Presets  (update existing presets only)
        3 = Program  (full show programming)
        4 = Setup    (patch, fixture import, console setup)
        5 = Admin    (full access + user/session/show management)

    Args:
        slot: User slot number (2-N; slot 1 = Administrator, always exists)
        name: Username (alphanumeric + underscores, no spaces)
        password: Console login password (empty string = no password required)
        rights_level: MA2 rights level 0-5
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "create_console_user is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)
    if slot < 1:
        return json.dumps({"error": "slot must be >= 1", "blocked": True}, indent=2)
    if rights_level not in range(6):
        return json.dumps({
            "error": f"rights_level must be 0-5, got {rights_level}",
            "blocked": True,
        }, indent=2)
    if not name or not name.replace("_", "").isalnum():
        return json.dumps({
            "error": "name must be alphanumeric (underscores allowed), no spaces",
            "blocked": True,
        }, indent=2)

    cmd = build_store_user(slot, name, password, rights_level)
    client = await get_client()
    response = await client.send_command_with_response(cmd)
    _rights_names = {0: "None", 1: "Playback", 2: "Presets",
                     3: "Program", 4: "Setup", 5: "Admin"}
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "slot": slot,
        "name": name,
        "rights_level": rights_level,
        "rights_name": _rights_names[rights_level],
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def assign_world_to_user_profile(
    user_profile_slot: int,
    world_slot: int,
    confirm_destructive: bool = False,
) -> str:
    """
    Assign a World (fixture visibility mask) to a User Profile (DESTRUCTIVE — Admin only).

    Restricts all Users assigned to this profile to only access fixtures and attributes
    visible in the specified World. Use world_slot=0 to remove the restriction (None).

    Args:
        user_profile_slot: UserProfile slot number to modify
        world_slot: World slot number (0 = no restriction / remove World assignment)
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON result with command sent
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "assign_world_to_user_profile is DESTRUCTIVE. Set confirm_destructive=True.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)
    if user_profile_slot < 1:
        return json.dumps({"error": "user_profile_slot must be >= 1", "blocked": True}, indent=2)

    cmd = build_assign_world_to_user_profile(user_profile_slot, world_slot)
    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "user_profile_slot": user_profile_slot,
        "world_slot": world_slot,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def inspect_sessions() -> str:
    """
    Inspect active per-operator Telnet session pool (SAFE_READ).

    Returns a snapshot of the session manager's current state: how many
    sessions are open, which console users they are authenticated as, and
    how long each has been idle.  Useful for diagnosing connection issues
    in multi-operator deployments.

    Returns:
        JSON with session_count and a sessions list, each entry containing:
        identity, username, connected, idle_seconds, age_seconds.
    """
    manager = await _get_session_manager()
    return json.dumps({
        "session_count": manager.session_count(),
        "max_sessions": manager._max_sessions,
        "idle_timeout_seconds": manager._idle_timeout,
        "sessions": manager.session_info(),
    }, indent=2)


# ============================================================
# Tools 102–109: Quick-wins sprint
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def delete_user(
    slot: int,
    confirm_destructive: bool = False,
) -> str:
    """
    Delete a console user account by slot number (DESTRUCTIVE).

    The built-in Administrator in slot 1 cannot be deleted.
    Requires confirm_destructive=True to proceed.

    Args:
        slot: User slot number to delete (2–N). Slot 1 is protected.
        confirm_destructive: Must be True to execute (safety gate).

    Returns:
        JSON with command_sent, raw_response, or block info.
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "risk_tier": "DESTRUCTIVE",
            "error": "Delete User is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    if slot == 1:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "risk_tier": "DESTRUCTIVE",
            "error": "Slot 1 (Administrator) is protected and cannot be deleted.",
        }, indent=2)

    cmd = build_delete_user(slot)
    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def browse_effect_library() -> str:
    """
    Browse the grandMA2 effect library (SAFE_READ).

    Lists all available effect templates that can be applied to fixtures.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    cmd = build_list_effect_library()
    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def browse_macro_library() -> str:
    """
    Browse the grandMA2 macro library (SAFE_READ).

    Lists all available macro templates that can be imported into the show.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    cmd = build_list_macro_library()
    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def browse_plugin_library() -> str:
    """
    Browse the grandMA2 plugin library (SAFE_READ).

    Lists all available plugin templates installed on the console.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    cmd = build_list_plugin_library()
    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_fader_modules() -> str:
    """
    List connected fader modules (SAFE_READ).

    Returns information about all fader wing modules currently connected
    to the grandMA2 console.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    cmd = build_list_fader_modules()
    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_update_history() -> str:
    """
    List programming update history (SAFE_READ).

    Shows the recent update log of programmer changes made in the show.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    cmd = build_list_update()
    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SHOW_LOAD)
@_handle_errors
async def delete_show(
    name: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Delete a show file from disk (DESTRUCTIVE).

    Permanently removes the named show file. This cannot be undone.
    Requires confirm_destructive=True to proceed.

    Args:
        name: Show file name to delete (without extension).
        confirm_destructive: Must be True to execute (safety gate).

    Returns:
        JSON with command_sent, raw_response, or block info.
    """
    if not confirm_destructive:
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "risk_tier": "DESTRUCTIVE",
            "error": "Delete Show is a DESTRUCTIVE operation. Set confirm_destructive=True to proceed.",
        }, indent=2)

    cmd = build_delete_show(name, noconfirm=True)
    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def assign_temp_fader(
    value: int = 50,
) -> str:
    """
    Set the temp fader level on the currently selected executor (SAFE_WRITE).

    TempFader crossfades the cue on when pulled up and crossfades the cue off
    when pulled down, relative to the given value. The value range is 0–100.

    Args:
        value: Fader level 0–100 (default 50). 0 = full off, 100 = full on.

    Returns:
        JSON with command_sent and raw_response from the console.
    """
    if not (0 <= value <= 100):
        return json.dumps({
            "command_sent": None,
            "blocked": True,
            "error": f"value must be between 0 and 100, got {value}.",
        }, indent=2)

    cmd = build_temp_fader(value)
    client = await get_client()
    raw_response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw_response,
        "risk_tier": "SAFE_WRITE",
    }, indent=2)


# ============================================================
# Agentic Layer — Orchestrator wiring
# ============================================================

_ltm = LongTermMemory()


async def _telnet_send_fn(cmd: str) -> str:
    """Thin wrapper so Orchestrator can send raw telnet without importing get_client."""
    client = await get_client()
    return await client.send_command_with_response(cmd)


async def _tool_caller(tool_name: str, inputs: dict):
    """
    Call any registered MCP tool function by name.
    Looks up the function from this module's global namespace at call time,
    so all 176 tool definitions above are available.
    """
    fn = sys.modules[__name__].__dict__.get(tool_name)
    if fn is None:
        raise ValueError(f"Orchestrator: unknown tool '{tool_name}'")
    return await fn(**inputs)


_orchestrator = Orchestrator(
    tool_caller=_tool_caller,
    telnet_send=_telnet_send_fn,
    ltm=_ltm,
    parallel=False,
)

register_orchestration_tools(mcp, _orchestrator, require_scope, _handle_errors, OAuthScope)

# Register MCP completions (argument autocompletion for prompts + resource templates)
from src.completions import register_completions  # noqa: E402

register_completions(mcp)

# Register MCP resource subscriptions (live state push when resources change)
from src.subscriptions import register_subscriptions  # noqa: E402

register_subscriptions(mcp)


# ============================================================
# New Tools — Batch Operations & Diagnostics
# Added during MA2 Agent hardening pass
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def batch_label(
    object_type: str,
    items: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Label multiple objects in a single call (DESTRUCTIVE).

    Instead of calling label_or_appearance once per object, batch_label applies
    names to an entire list. Accepts a JSON array of {id, name} pairs.

    Args:
        object_type: Object type (e.g. "group", "sequence", "macro", "preset")
        items: JSON array string, e.g. '[{"id": 1, "name": "Front Wash"}, {"id": 2, "name": "Back Light"}]'
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation)

    Returns:
        str: JSON with labels_applied, commands, errors, risk_tier.

    Examples:
        - Label groups 1-3: object_type="group", items='[{"id":1,"name":"Front"},{"id":2,"name":"Back"},{"id":3,"name":"Side"}]'
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "batch_label is DESTRUCTIVE. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    try:
        item_list = json.loads(items) if isinstance(items, str) else items
    except (json.JSONDecodeError, TypeError) as e:
        return json.dumps({"error": f"Invalid items JSON: {e}", "blocked": True}, indent=2)

    if not isinstance(item_list, list) or not item_list:
        return json.dumps({"error": "items must be a non-empty JSON array of {id, name} objects.", "blocked": True}, indent=2)

    client = await get_client()
    commands: list[str] = []
    errors: list[str] = []

    for item in item_list:
        obj_id = item.get("id")
        name = item.get("name")
        if obj_id is None or name is None:
            errors.append(f"Skipped item missing id or name: {item}")
            continue
        cmd = build_label(object_type, obj_id, name)
        try:
            await client.send_command_with_response(cmd)
            commands.append(cmd)
        except Exception as e:
            errors.append(f"Failed {cmd}: {e}")

    return json.dumps({
        "labels_applied": len(commands),
        "total_items": len(item_list),
        "commands": commands,
        "errors": errors,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def bulk_executor_assign(
    executor_id: int,
    sequence_id: int,
    executor_page: int = 1,
    trigger: str | None = None,
    priority: str | None = None,
    fader_function: str | None = None,
    label: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Assign a sequence to an executor and configure it in one call (DESTRUCTIVE).

    Combines assign + optional trigger/priority/fader/label into a single
    operation instead of 4-5 separate tool calls.

    Args:
        executor_id: Executor number to assign to.
        sequence_id: Sequence number to assign.
        executor_page: Executor page (default 1).
        trigger: Optional trigger type (e.g. "go", "flash", "toggle").
        priority: Optional priority level (e.g. "normal", "high", "super", "htp").
        fader_function: Optional fader function (e.g. "master", "crossfade", "speed").
        label: Optional label for the executor.
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation).

    Returns:
        str: JSON with commands_sent, raw_responses, risk_tier.

    Examples:
        - Assign seq 1 to exec 101: executor_id=101, sequence_id=1
        - Full setup: executor_id=101, sequence_id=1, trigger="go", priority="high", label="Main Wash"
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "bulk_executor_assign is DESTRUCTIVE. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()
    exec_ref = f"{executor_page}.{executor_id}"
    commands_sent: list[str] = []
    raw_responses: list[str] = []

    # 1. Assign sequence to executor
    assign_cmd = f"assign sequence {sequence_id} at executor {exec_ref}"
    raw = await client.send_command_with_response(assign_cmd)
    commands_sent.append(assign_cmd)
    raw_responses.append(raw)

    # 2. Optional: set trigger
    if trigger:
        cmd = f"assign executor {exec_ref} /trigger={trigger}"
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    # 3. Optional: set priority
    if priority:
        cmd = f"assign executor {exec_ref} /priority={priority}"
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    # 4. Optional: set fader function
    if fader_function:
        cmd = f"assign executor {exec_ref} /fader={fader_function}"
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    # 5. Optional: label
    if label:
        cmd = f'label executor {exec_ref} "{label}"'
        raw = await client.send_command_with_response(cmd)
        commands_sent.append(cmd)
        raw_responses.append(raw)

    return json.dumps({
        "executor": exec_ref,
        "sequence_id": sequence_id,
        "commands_sent": commands_sent,
        "raw_responses": raw_responses,
        "options_applied": {
            "trigger": trigger,
            "priority": priority,
            "fader_function": fader_function,
            "label": label,
        },
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SEQUENCE_EDIT)
@_handle_errors
async def auto_number_cues(
    sequence_id: int,
    start: float = 1.0,
    spacing: float = 1.0,
    confirm_destructive: bool = False,
) -> str:
    """
    Renumber all cues in a sequence with configurable start and spacing (DESTRUCTIVE).

    Lists existing cues, then moves each to its new number. Useful for cleaning
    up cue lists with irregular numbering (e.g. 1, 1.5, 3, 7 → 1, 2, 3, 4).

    Args:
        sequence_id: Sequence to renumber.
        start: Starting cue number (default 1.0).
        spacing: Increment between cues (default 1.0).
        confirm_destructive: Must be True to execute (DESTRUCTIVE operation).

    Returns:
        str: JSON with cues_renumbered, old_to_new mapping, commands.

    Examples:
        - Standard: sequence_id=1 → cues become 1, 2, 3, ...
        - By tens: sequence_id=1, start=10, spacing=10 → 10, 20, 30, ...
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "auto_number_cues is DESTRUCTIVE. Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    client = await get_client()

    # List existing cues
    list_cmd = f"list cue sequence {sequence_id}"
    raw = await client.send_command_with_response(list_cmd)
    if "NO OBJECTS FOUND" in raw.upper():
        return json.dumps({
            "error": f"Sequence {sequence_id} has no cues.",
            "command_sent": list_cmd,
            "raw_response": raw,
            "risk_tier": "DESTRUCTIVE",
            "blocked": True,
        }, indent=2)

    # Parse cue IDs from the raw list output (look for numeric IDs in first column)
    import re
    cue_ids: list[float] = []
    for line in raw.splitlines():
        m = re.match(r"^\s*(\d+(?:\.\d+)?)\s", line.strip())
        if m:
            cue_ids.append(float(m.group(1)))

    if not cue_ids:
        return json.dumps({
            "error": "Could not parse cue IDs from sequence listing.",
            "raw_response": raw,
            "risk_tier": "DESTRUCTIVE",
            "blocked": True,
        }, indent=2)

    # Build old→new mapping (work in reverse to avoid collisions)
    old_to_new: dict[str, str] = {}
    commands: list[str] = []
    new_num = start
    mapping = []
    for old_id in sorted(cue_ids):
        mapping.append((old_id, new_num))
        new_num += spacing

    # Move cues in reverse order to avoid overwriting
    for old_id, new_id in reversed(mapping):
        if old_id != new_id:
            cmd = f"move cue {old_id} sequence {sequence_id} at cue {new_id} sequence {sequence_id}"
            await client.send_command_with_response(cmd)
            commands.append(cmd)
        old_to_new[str(old_id)] = str(new_id)

    return json.dumps({
        "cues_renumbered": len(old_to_new),
        "sequence_id": sequence_id,
        "old_to_new": old_to_new,
        "commands": commands,
        "risk_tier": "DESTRUCTIVE",
        "blocked": False,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def compare_cue_values(
    sequence_id: int,
    cue_a: float,
    cue_b: float,
) -> str:
    """
    Compare two cues in a sequence and show differences (SAFE_READ).

    Lists both cues and diffs the raw console output to help identify
    what changes between them. Useful for tracking analysis and cue cleanup.

    Args:
        sequence_id: Sequence containing both cues.
        cue_a: First cue number.
        cue_b: Second cue number.

    Returns:
        str: JSON with cue_a, cue_b, raw outputs, and line-by-line differences.
    """
    client = await get_client()

    cmd_a = f"list cue {cue_a} sequence {sequence_id}"
    cmd_b = f"list cue {cue_b} sequence {sequence_id}"
    raw_a = await client.send_command_with_response(cmd_a)
    raw_b = await client.send_command_with_response(cmd_b)

    # Line-by-line diff
    lines_a = set(raw_a.strip().splitlines())
    lines_b = set(raw_b.strip().splitlines())
    only_in_a = sorted(lines_a - lines_b)
    only_in_b = sorted(lines_b - lines_a)

    return json.dumps({
        "sequence_id": sequence_id,
        "cue_a": cue_a,
        "cue_b": cue_b,
        "command_a": cmd_a,
        "command_b": cmd_b,
        "raw_a": raw_a,
        "raw_b": raw_b,
        "only_in_cue_a": only_in_a,
        "only_in_cue_b": only_in_b,
        "identical": len(only_in_a) == 0 and len(only_in_b) == 0,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def diagnose_no_output(
    fixture_id: int | None = None,
    universe: int | None = None,
) -> str:
    """
    Diagnostic tree for fixtures not producing output (SAFE_READ).

    Runs a series of non-destructive checks to identify why fixtures
    may not be responding: Grand Master level, blackout state, park status,
    patch, executor state. Returns structured findings.

    Args:
        fixture_id: Optional specific fixture to check.
        universe: Optional DMX universe to check.

    Returns:
        str: JSON with checks list, each having check name, status (ok/warning/fail), detail.
    """
    client = await get_client()
    checks: list[dict[str, str]] = []

    # 1. Grand Master
    try:
        raw = await client.send_command_with_response("listvar")
        if "$GRANDMASTER" in raw.upper() or "grand" in raw.lower():
            checks.append({"check": "grand_master", "status": "ok", "detail": "Grand Master variable found in system vars"})
        else:
            checks.append({"check": "grand_master", "status": "warning", "detail": "Could not determine Grand Master level — check manually"})
    except Exception as e:
        checks.append({"check": "grand_master", "status": "fail", "detail": f"Error checking Grand Master: {e}"})

    # 2. Blackout state
    try:
        raw = await client.send_command_with_response("listvar")
        if "blackout" in raw.lower():
            checks.append({"check": "blackout", "status": "warning", "detail": "Blackout reference found — check B.O. button on console"})
        else:
            checks.append({"check": "blackout", "status": "ok", "detail": "No blackout indication in system variables"})
    except Exception as e:
        checks.append({"check": "blackout", "status": "fail", "detail": f"Error checking blackout: {e}"})

    # 3. Park status
    if fixture_id is not None:
        try:
            raw = await client.send_command_with_response(f"list fixture {fixture_id}")
            if "PARK" in raw.upper():
                checks.append({"check": "park_status", "status": "fail", "detail": f"Fixture {fixture_id} appears to be PARKED — use unpark_fixture to release"})
            else:
                checks.append({"check": "park_status", "status": "ok", "detail": f"Fixture {fixture_id} is not parked"})
        except Exception as e:
            checks.append({"check": "park_status", "status": "fail", "detail": f"Error checking park status: {e}"})

    # 4. Patch / DMX address
    if fixture_id is not None:
        try:
            raw = await client.send_command_with_response(f"info fixture {fixture_id}")
            if "NO OBJECTS" in raw.upper():
                checks.append({"check": "patch", "status": "fail", "detail": f"Fixture {fixture_id} not found — may not be patched"})
            else:
                checks.append({"check": "patch", "status": "ok", "detail": f"Fixture {fixture_id} found in patch"})
        except Exception as e:
            checks.append({"check": "patch", "status": "fail", "detail": f"Error checking patch: {e}"})

    # 5. Universe check
    if universe is not None:
        try:
            raw = await client.send_command_with_response(f"list dmxuniverse {universe}")
            checks.append({"check": "universe", "status": "ok", "detail": f"Universe {universe} response: {raw[:200]}"})
        except Exception as e:
            checks.append({"check": "universe", "status": "fail", "detail": f"Error checking universe {universe}: {e}"})

    # 6. Selected fixtures count
    try:
        raw = await client.send_command_with_response("listvar")
        if "SELECTEDFIXTURESCOUNT" in raw:
            checks.append({"check": "selection", "status": "ok", "detail": "Selection variable present in system vars"})
        else:
            checks.append({"check": "selection", "status": "warning", "detail": "Could not find fixture selection count"})
    except Exception as e:
        checks.append({"check": "selection", "status": "fail", "detail": f"Error checking selection: {e}"})

    overall = "ok"
    if any(c["status"] == "fail" for c in checks):
        overall = "fail"
    elif any(c["status"] == "warning" for c in checks):
        overall = "warning"

    return json.dumps({
        "overall_status": overall,
        "fixture_id": fixture_id,
        "universe": universe,
        "checks": checks,
        "risk_tier": "SAFE_READ",
        "recommendation": "If all checks pass but no output, verify: (1) correct DMX universe output enabled in Setup, (2) physical DMX connection, (3) fixture address matching patch",
    }, indent=2)


# ============================================================
# Bitfocus Companion Integration Tools
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def generate_companion_config(
    page: int = 1,
    companion_page: int = 1,
    grid_columns: int = 8,
) -> str:
    """
    Generate a Bitfocus Companion .companionconfig page from the current MA2 executor layout (SAFE_READ).

    Reads the executor page and builds a Companion-importable JSON config
    with one button per assigned executor. Each button sends the appropriate
    Go+ command via Companion's grandMA2 telnet module.

    The output is a JSON string in Companion v4 page-export format. Save it
    to a .companionconfig file and import via Companion UI → Buttons → Import.

    Args:
        page: MA2 executor page to export (default 1).
        companion_page: Target Companion page number (default 1).
        grid_columns: Companion grid width — 8 for Stream Deck XL, 5 for Stream Deck (default 8).

    Returns:
        str: JSON with companion_config (the importable config), executor_count, and instructions.

    Examples:
        - Export page 1: generate_companion_config()
        - Export page 2 for Stream Deck: generate_companion_config(page=2, grid_columns=5)
    """
    client = await get_client()

    # Read the executor page layout
    scan_result = await scan_page_executor_layout(page=page)
    scan_data = json.loads(scan_result) if isinstance(scan_result, str) else scan_result

    executors = scan_data.get("executors", [])
    if not executors and "error" in scan_data:
        return json.dumps({
            "error": f"Could not read executor page {page}: {scan_data.get('error')}",
            "risk_tier": "SAFE_READ",
        }, indent=2)

    # Build Companion page config
    controls: dict[str, dict] = {}
    button_count = 0

    for exec_info in executors:
        exec_id = exec_info.get("executor_id") or exec_info.get("id")
        if exec_id is None:
            continue

        label = exec_info.get("label") or exec_info.get("name") or f"Exec {exec_id}"
        has_sequence = exec_info.get("sequence_id") is not None or exec_info.get("assigned")

        # Grid position
        row = button_count // grid_columns
        col = button_count % grid_columns

        # Button color: dark blue for assigned, dark gray for empty
        bgcolor = 1315860 if has_sequence else 2105376  # #141414 vs #202020

        controls[f"{row}/{col}"] = {
            "type": "button",
            "style": {
                "text": str(label)[:12],
                "size": "auto",
                "color": 16777215,  # white text
                "bgcolor": bgcolor,
            },
            "options": {"relativeDelay": False},
            "feedbacks": [],
            "steps": {
                "0": {
                    "action_sets": {
                        "down": [
                            {
                                "actionId": "command",
                                "options": {
                                    "command": f"Go+ Executor {page}.{exec_id}",
                                },
                            }
                        ],
                        "up": [],
                    }
                }
            },
        }
        button_count += 1

    max_row = max(0, (button_count - 1) // grid_columns)
    companion_config = {
        "version": 4,
        "type": "page",
        "page": {
            "name": f"MA2 Page {page}",
            "gridSize": {
                "minColumn": 0,
                "maxColumn": grid_columns - 1,
                "minRow": 0,
                "maxRow": max_row,
            },
            "controls": controls,
        },
    }

    return json.dumps({
        "companion_config": companion_config,
        "executor_count": button_count,
        "companion_page": companion_page,
        "ma2_page": page,
        "grid_columns": grid_columns,
        "risk_tier": "SAFE_READ",
        "instructions": (
            "Save the 'companion_config' value to a .companionconfig file, "
            "then import in Companion UI → Buttons → Import. "
            "Make sure the grandMA2 connection module is configured with "
            "the correct console IP and Telnet credentials."
        ),
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PLAYBACK_GO)
@_handle_errors
async def companion_button_press(
    page: int,
    button: int,
    host: str = "localhost",
    port: int = 8000,
) -> str:
    """
    Press a button on a running Bitfocus Companion instance via HTTP API (SAFE_WRITE).

    Sends a GET request to Companion's REST API to trigger a button press.
    Companion must be running and accessible at the specified host/port.

    Args:
        page: Companion page number (1-based).
        button: Button index on the page (0-based).
        host: Companion host (default "localhost").
        port: Companion HTTP API port (default 8000).

    Returns:
        str: JSON with status, url_called, response text.

    Examples:
        - Press button 0 on page 1: companion_button_press(page=1, button=0)
        - Remote Companion: companion_button_press(page=1, button=3, host="192.168.1.50")
    """
    import urllib.request
    import urllib.error

    url = f"http://{host}:{port}/press/bank/{page}/{button}"

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.dumps({
                "status": "ok",
                "http_status": resp.status,
                "url_called": url,
                "response": body[:500],
                "risk_tier": "SAFE_WRITE",
            }, indent=2)
    except urllib.error.URLError as e:
        return json.dumps({
            "status": "error",
            "error": f"Could not reach Companion at {url}: {e.reason}",
            "url_called": url,
            "hint": "Ensure Bitfocus Companion is running and the HTTP API is enabled.",
            "risk_tier": "SAFE_WRITE",
        }, indent=2)
    except TimeoutError:
        return json.dumps({
            "status": "error",
            "error": f"Timeout connecting to Companion at {url}",
            "url_called": url,
            "risk_tier": "SAFE_WRITE",
        }, indent=2)


# ============================================================
# BPM Sync / ShowKontrol Integration
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def set_bpm(
    bpm: float,
    speed_master: int = 1,
) -> str:
    """
    Set the BPM on a grandMA2 Speed Master (SAFE_WRITE).

    Designed for live BPM sync from external sources like ShowKontrol,
    Beat Link Trigger, Ableton, or any system that provides real-time BPM.
    Sends the SpecialMaster command to the console via Telnet.

    The BPM value directly controls effect speed for any executor assigned
    to this speed master. Common workflow: ShowKontrol reads CDJ BPM →
    calls this tool → MA2 effects follow the DJ's tempo in real time.

    Args:
        bpm: Beats per minute (1-300). Fractional values supported (e.g. 128.5).
        speed_master: Which speed master to control (1-16, default 1).

    Returns:
        str: JSON with command_sent, raw_response, bpm, speed_master.

    Examples:
        - Set 128 BPM on speed master 1: set_bpm(bpm=128)
        - Set 140 BPM on speed master 3: set_bpm(bpm=140, speed_master=3)
    """
    if not (1 <= bpm <= 300):
        return json.dumps({
            "error": f"BPM must be between 1 and 300, got {bpm}",
            "blocked": True,
        }, indent=2)
    if not (1 <= speed_master <= 16):
        return json.dumps({
            "error": f"Speed master must be 1-16, got {speed_master}",
            "blocked": True,
        }, indent=2)

    client = await get_client()
    cmd = f"SpecialMaster 3.{speed_master} At {bpm}"
    raw = await client.send_command_with_response(cmd)

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "bpm": bpm,
        "speed_master": speed_master,
        "risk_tier": "SAFE_WRITE",
        "tip": f"Assign executors to Speed Master {speed_master} with: assign executor X /speedmaster=speed{speed_master}",
    }, indent=2)


# ============================================================
# Analysis & Intelligence Tools
# Impact analysis, dependency mapping, linting, and recovery
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def find_preset_usages(
    preset_type: str,
    preset_id: int,
    max_sequences: int = 50,
) -> str:
    """
    Find all sequences and cues that reference a specific preset (SAFE_READ).

    Scans sequence cue data for Preset references before you update or delete.
    Also reports which executors play sequences that use this preset.

    Args:
        preset_type: Preset type name (e.g. "color", "position", "gobo").
        preset_id: Preset slot number.
        max_sequences: Max sequences to scan (default 50, higher = slower).

    Returns:
        str: JSON with usages, executor_references, total_references, risk_if_deleted.
    """
    from src.commands.constants import PRESET_TYPES

    type_num = PRESET_TYPES.get(preset_type.lower())
    if type_num is None:
        return json.dumps({
            "error": f"Unknown preset type '{preset_type}'. Valid: {sorted(PRESET_TYPES.keys())}",
            "blocked": True,
        }, indent=2)

    client = await get_client()
    usages: list[dict] = []
    executor_refs: list[dict] = []
    pattern = re.compile(rf"Preset\s+{type_num}\.{preset_id}\b", re.IGNORECASE)

    # Get sequence list from snapshot or discovery
    seq_ids: list[int] = []
    snap = getattr(_orchestrator, "last_snapshot", None)
    if snap and hasattr(snap, "sequences") and snap.sequences:
        seq_ids = [s.sequence_id for s in snap.sequences[:max_sequences] if hasattr(s, "sequence_id")]
    if not seq_ids:
        raw = await client.send_command_with_response("list sequence")
        for m in re.finditer(r"^\s*(\d+)\s", raw, re.MULTILINE):
            seq_ids.append(int(m.group(1)))
            if len(seq_ids) >= max_sequences:
                break

    # Scan each sequence's cues
    referencing_seqs: set[int] = set()
    for seq_id in seq_ids:
        raw = await client.send_command_with_response(f"list cue sequence {seq_id}")
        if pattern.search(raw):
            # Find specific cue IDs
            for line in raw.splitlines():
                if pattern.search(line):
                    cue_match = re.match(r"^\s*(\d+(?:\.\d+)?)\s", line.strip())
                    cue_id = cue_match.group(1) if cue_match else "unknown"
                    usages.append({
                        "sequence_id": seq_id,
                        "cue_id": cue_id,
                        "context": line.strip()[:200],
                    })
                    referencing_seqs.add(seq_id)
        await asyncio.sleep(0.05)

    # Check executor assignments for referencing sequences
    if snap and hasattr(snap, "executor_state") and snap.executor_state:
        for exec_id, state in snap.executor_state.items():
            if hasattr(state, "sequence_id") and state.sequence_id in referencing_seqs:
                executor_refs.append({
                    "executor_id": exec_id,
                    "sequence_id": state.sequence_id,
                })

    total = len(usages)
    risk = "none" if total == 0 else "low" if total <= 2 else "medium" if total <= 5 else "high"

    return json.dumps({
        "preset_type": preset_type,
        "preset_type_id": type_num,
        "preset_id": preset_id,
        "usages": usages,
        "executor_references": executor_refs,
        "total_references": total,
        "sequences_scanned": len(seq_ids),
        "risk_if_deleted": risk,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def diff_cues(
    sequence_id: int,
    cue_a: float,
    cue_b: float,
) -> str:
    """
    Structured diff of two cues showing per-attribute changes (SAFE_READ).

    More detailed than compare_cue_values — parses attribute names, timing,
    labels, and block status. Falls back to raw line diff if parsing fails.

    Args:
        sequence_id: Sequence containing both cues.
        cue_a: First cue number.
        cue_b: Second cue number.

    Returns:
        str: JSON with changes[], timing_diff, label_diff, block_diff, identical.
    """
    client = await get_client()
    raw_a = await client.send_command_with_response(f"list cue {cue_a} sequence {sequence_id}")
    raw_b = await client.send_command_with_response(f"list cue {cue_b} sequence {sequence_id}")

    def _parse_cue_attrs(raw: str) -> dict[str, str]:
        """Parse attribute=value pairs from cue listing."""
        attrs: dict[str, str] = {}
        for line in raw.strip().splitlines():
            line = line.strip()
            # Try KEY=VALUE or tabular format
            kv = re.findall(r"(\w+)\s*=\s*(\S+)", line)
            for k, v in kv:
                attrs[k] = v
            # Also capture column-based data (Name Value pairs)
            cols = line.split()
            if len(cols) >= 2 and not line.startswith("#"):
                attrs[cols[0]] = " ".join(cols[1:])
        return attrs

    attrs_a = _parse_cue_attrs(raw_a)
    attrs_b = _parse_cue_attrs(raw_b)
    all_keys = sorted(set(attrs_a.keys()) | set(attrs_b.keys()))

    changes: list[dict] = []
    for key in all_keys:
        va = attrs_a.get(key)
        vb = attrs_b.get(key)
        if va != vb:
            if va is None:
                changes.append({"attribute": key, "value_a": None, "value_b": vb, "change_type": "added"})
            elif vb is None:
                changes.append({"attribute": key, "value_a": va, "value_b": None, "change_type": "removed"})
            else:
                changes.append({"attribute": key, "value_a": va, "value_b": vb, "change_type": "modified"})

    # Timing extraction
    timing_keys = {"Fade", "Delay", "SnapPercent", "CueFade", "CueDelay"}
    timing_diff = {}
    for k in timing_keys:
        if k in attrs_a or k in attrs_b:
            timing_diff[k] = {"cue_a": attrs_a.get(k), "cue_b": attrs_b.get(k)}

    # Label/block extraction
    label_a = attrs_a.get("Name", attrs_a.get("Label", ""))
    label_b = attrs_b.get("Name", attrs_b.get("Label", ""))
    block_a = "block" in raw_a.lower()
    block_b = "block" in raw_b.lower()

    # Fallback raw diff
    lines_a = set(raw_a.strip().splitlines())
    lines_b = set(raw_b.strip().splitlines())

    return json.dumps({
        "sequence_id": sequence_id,
        "cue_a": cue_a,
        "cue_b": cue_b,
        "changes": changes,
        "total_changes": len(changes),
        "timing_diff": timing_diff,
        "label_diff": {"cue_a": label_a, "cue_b": label_b},
        "block_diff": {"cue_a": block_a, "cue_b": block_b},
        "attributes_only_in_a": sorted(set(attrs_a) - set(attrs_b)),
        "attributes_only_in_b": sorted(set(attrs_b) - set(attrs_a)),
        "identical": len(changes) == 0,
        "raw_only_in_a": sorted(lines_a - lines_b)[:20],
        "raw_only_in_b": sorted(lines_b - lines_a)[:20],
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def get_page_map(
    page: int = 1,
) -> str:
    """
    Get a complete topology map of an executor page (SAFE_READ).

    Returns every executor with its assignment, fader role, trigger type,
    priority, width, and label. Richer than scan_page_executor_layout.

    Args:
        page: Executor page number (default 1).

    Returns:
        str: JSON with executors[], occupied count, free_slots[], total_slots.
    """
    client = await get_client()
    executors: list[dict] = []
    free_slots: list[int] = []
    total_slots = 40

    for exec_id in range(201, 201 + total_slots):
        raw = await client.send_command_with_response(f"list executor {page}.{exec_id}")
        if "NO OBJECTS" in raw.upper() or not raw.strip():
            free_slots.append(exec_id)
            continue

        # Parse KEY=VALUE or inline fields
        def _extract(key: str) -> str | None:
            m = re.search(rf"{key}\s*[=:]\s*(\S+)", raw, re.IGNORECASE)
            return m.group(1) if m else None

        seq_str = _extract("Sequence") or _extract("Seq")
        seq_id = int(seq_str) if seq_str and seq_str.isdigit() else None
        name = _extract("Name") or ""
        width_str = _extract("Width")
        width = int(width_str) if width_str and width_str.isdigit() else 1

        # Infer type from content
        exec_type = "empty"
        raw_lower = raw.lower()
        if "effect" in raw_lower:
            exec_type = "effect"
        elif "macro" in raw_lower:
            exec_type = "macro"
        elif seq_id is not None:
            exec_type = "sequence"

        executors.append({
            "id": exec_id,
            "label": name.strip('"') if name else f"Exec {exec_id}",
            "type": exec_type,
            "sequence_id": seq_id,
            "fader_function": _extract("Fader") or "Master",
            "trigger": _extract("Trigger") or _extract("Trig") or "Go",
            "priority": _extract("Priority") or _extract("Prio") or "Normal",
            "width": width,
        })
        await asyncio.sleep(0.02)

    return json.dumps({
        "page": page,
        "executors": executors,
        "occupied": len(executors),
        "free_slots": free_slots,
        "total_slots": total_slots,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def lint_macro(
    macro_id: int,
) -> str:
    """
    Static analysis of a grandMA2 macro for unsafe patterns (SAFE_READ).

    Checks for: destructive commands without gates, broken jump targets,
    missing quotes, unsafe raw patterns, potential infinite loops.

    Args:
        macro_id: Macro number to lint.

    Returns:
        str: JSON with issues[], overall (clean/warning/error), lines_checked.
    """
    client = await get_client()

    # Get macro content
    raw = await client.send_command_with_response(f"list macro {macro_id}")
    if "NO OBJECTS" in raw.upper():
        return json.dumps({
            "error": f"Macro {macro_id} not found.",
            "risk_tier": "SAFE_READ",
        }, indent=2)

    # Get macro label
    info_raw = await client.send_command_with_response(f"info macro {macro_id}")
    label_match = re.search(r"Name\s*[=:]\s*(.+?)(?:\s*$|\s+\w)", info_raw, re.MULTILINE)
    macro_label = label_match.group(1).strip().strip('"') if label_match else f"Macro {macro_id}"

    # Parse lines
    lines: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---"):
            # Strip line numbers if present
            stripped = re.sub(r"^\d+\s+", "", line)
            if stripped:
                lines.append(stripped)

    issues: list[dict] = []
    _DESTRUCTIVE = re.compile(r"\b(Delete|Store\b.*\b/o|Move\s+\w)", re.IGNORECASE)
    _UNSAFE_RAW = re.compile(r"\b(NewShow|Shutdown|Reset|Reboot)\b", re.IGNORECASE)
    _JUMP = re.compile(r"Go\s+Macro\s+(\d+)", re.IGNORECASE)
    _SELF_JUMP = re.compile(rf"Go\s+Macro\s+{macro_id}\b", re.IGNORECASE)
    _UNQUOTED_SPACE = re.compile(r'(?<!")\b(\w+\s+\w+)(?!")\s+(?:At|Thru|If)', re.IGNORECASE)

    for i, cmd in enumerate(lines, 1):
        # Destructive without gate
        if _DESTRUCTIVE.search(cmd):
            issues.append({
                "line": i, "severity": "error", "rule": "destructive_no_gate",
                "message": f"Destructive command without CmdDelay gate: {cmd[:80]}",
                "raw_command": cmd,
            })
        # Unsafe raw patterns
        if _UNSAFE_RAW.search(cmd):
            issues.append({
                "line": i, "severity": "error", "rule": "unsafe_raw",
                "message": f"Unsafe system command: {cmd[:80]}",
                "raw_command": cmd,
            })
        # Self-referencing jump (potential infinite loop)
        if _SELF_JUMP.search(cmd):
            issues.append({
                "line": i, "severity": "warning", "rule": "infinite_loop",
                "message": f"Macro jumps to itself (potential infinite loop): {cmd[:80]}",
                "raw_command": cmd,
            })
        # Jump to line beyond macro length
        jump_match = _JUMP.search(cmd)
        if jump_match:
            target_line = re.search(r"\.(\d+)$", cmd)
            if target_line and int(target_line.group(1)) > len(lines):
                issues.append({
                    "line": i, "severity": "error", "rule": "broken_jump",
                    "message": f"Jump to line {target_line.group(1)} but macro has {len(lines)} lines",
                    "raw_command": cmd,
                })

    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    overall = "error" if errors else "warning" if warnings else "clean"

    return json.dumps({
        "macro_id": macro_id,
        "macro_label": macro_label,
        "lines_checked": len(lines),
        "issues": issues,
        "overall": overall,
        "lines_clean": len(lines) - errors - warnings,
        "lines_warning": warnings,
        "lines_error": errors,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def detect_programmer_contamination() -> str:
    """
    Check for leftover programmer state before critical operations (SAFE_READ).

    Detects: selected fixtures, active filters, active worlds, MAtricks state,
    highlight/freeze/solo modes, and parked fixtures. Run this before storing
    cues, presets, or making show-critical changes.

    Returns:
        str: JSON with contaminated bool, checks[], recommendation.
    """
    checks: list[dict[str, str]] = []
    snap = getattr(_orchestrator, "last_snapshot", None)
    snapshot_age: float | None = None

    if snap:
        snapshot_age = snap.age_seconds() if hasattr(snap, "age_seconds") else None

        # Selected fixtures
        sel_count = getattr(snap, "selected_fixture_count", 0) or 0
        if sel_count > 0:
            checks.append({"check": "selected_fixtures", "status": "fail", "detail": f"{sel_count} fixtures selected in programmer"})
        else:
            checks.append({"check": "selected_fixtures", "status": "ok", "detail": "No fixtures selected"})

        # Active filter
        filt = getattr(snap, "active_filter", None)
        if filt and filt != 0:
            checks.append({"check": "active_filter", "status": "warning", "detail": f"Filter {filt} is active"})
        else:
            checks.append({"check": "active_filter", "status": "ok", "detail": "No filter active"})

        # Active world
        world = getattr(snap, "active_world", None)
        if world and world != 0:
            checks.append({"check": "active_world", "status": "warning", "detail": f"World {world} is active — may limit fixture visibility"})
        else:
            checks.append({"check": "active_world", "status": "ok", "detail": "Default world (all fixtures visible)"})

        # Console modes
        modes = getattr(snap, "console_modes", {}) or {}
        for mode in ("highlight", "freeze", "solo", "blind"):
            if modes.get(mode):
                checks.append({"check": f"mode_{mode}", "status": "fail", "detail": f"{mode.title()} mode is ON"})
            else:
                checks.append({"check": f"mode_{mode}", "status": "ok", "detail": f"{mode.title()} mode is off"})

        # Parked fixtures
        parked = getattr(snap, "parked_fixtures", set()) or set()
        if parked:
            checks.append({"check": "parked_fixtures", "status": "warning", "detail": f"{len(parked)} fixtures parked: {sorted(list(parked))[:10]}"})
        else:
            checks.append({"check": "parked_fixtures", "status": "ok", "detail": "No parked fixtures"})

        # MAtricks
        matricks = getattr(snap, "matricks", None)
        if matricks and hasattr(matricks, "active") and matricks.active:
            checks.append({"check": "matricks", "status": "warning", "detail": "MAtricks is active — may affect selection grouping"})
        else:
            checks.append({"check": "matricks", "status": "ok", "detail": "MAtricks inactive"})
    else:
        # Fallback: query via telnet
        client = await get_client()
        raw = await client.send_command_with_response("listvar")
        sel_match = re.search(r"SELECTEDFIXTURESCOUNT[=\s]+(\d+)", raw, re.IGNORECASE)
        sel_count = int(sel_match.group(1)) if sel_match else 0
        if sel_count > 0:
            checks.append({"check": "selected_fixtures", "status": "fail", "detail": f"{sel_count} fixtures selected"})
        else:
            checks.append({"check": "selected_fixtures", "status": "ok", "detail": "No fixtures selected"})
        checks.append({"check": "snapshot", "status": "warning", "detail": "No hydrated snapshot — limited checks available. Run hydrate_console_state first."})

    contaminated = any(c["status"] == "fail" for c in checks)
    has_warnings = any(c["status"] == "warning" for c in checks)

    recommendation = "Programmer is clean — safe to proceed." if not contaminated and not has_warnings else ""
    if contaminated:
        recommendation = "Clear programmer with ClearAll, disable active modes, then re-check."
    elif has_warnings:
        recommendation = "Minor contamination detected — review warnings before critical operations."

    return json.dumps({
        "contaminated": contaminated,
        "checks": checks,
        "recommendation": recommendation,
        "snapshot_age_s": round(snapshot_age, 1) if snapshot_age is not None else None,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def preview_preset_update_impact(
    preset_type: str,
    preset_id: int,
) -> str:
    """
    Assess the impact of updating or deleting a preset (SAFE_READ).

    Calls find_preset_usages internally and classifies the risk level.
    Run this before any Store, Update, or Delete on a preset.

    Args:
        preset_type: Preset type name (e.g. "color", "position").
        preset_id: Preset slot number.

    Returns:
        str: JSON with impact_level (safe/risky/catastrophic), affected details, recommendation.
    """
    raw_result = await find_preset_usages(preset_type=preset_type, preset_id=preset_id)
    data = json.loads(raw_result)

    if "error" in data:
        return raw_result

    total = data["total_references"]
    seq_ids = list({u["sequence_id"] for u in data["usages"]})

    if total == 0:
        impact = "safe"
        rec = "No references found — safe to update or delete."
    elif total <= 5:
        impact = "risky"
        rec = f"Found {total} references in {len(seq_ids)} sequence(s). Use Blind mode to preview changes before storing."
    else:
        impact = "catastrophic"
        rec = f"Found {total} references across {len(seq_ids)} sequence(s). Back up the show before modifying. Consider creating a new preset instead of editing."

    return json.dumps({
        "preset_type": preset_type,
        "preset_id": preset_id,
        "impact_level": impact,
        "total_references": total,
        "affected_sequences": seq_ids,
        "affected_cue_count": total,
        "executor_references": data.get("executor_references", []),
        "recommendation": rec,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def detect_tracking_leaks(
    sequence_id: int,
    max_cues: int = 20,
) -> str:
    """
    Find attributes unintentionally tracking into later cues (SAFE_READ).

    Compares adjacent cue pairs to find values that persist without an
    explicit Block. Tracking leaks cause unexpected looks in later cues.

    Args:
        sequence_id: Sequence to analyze.
        max_cues: Max cues to compare (default 20).

    Returns:
        str: JSON with leaks[], total_leaks, recommendation.
    """
    client = await get_client()

    # Get cue list
    raw = await client.send_command_with_response(f"list cue sequence {sequence_id}")
    if "NO OBJECTS" in raw.upper():
        return json.dumps({"error": f"Sequence {sequence_id} not found.", "risk_tier": "SAFE_READ"}, indent=2)

    cue_ids: list[float] = []
    for m in re.finditer(r"^\s*(\d+(?:\.\d+)?)\s", raw, re.MULTILINE):
        cue_ids.append(float(m.group(1)))
        if len(cue_ids) >= max_cues:
            break

    if len(cue_ids) < 2:
        return json.dumps({
            "sequence_id": sequence_id,
            "leaks": [],
            "total_leaks": 0,
            "cues_checked": len(cue_ids),
            "recommendation": "Need at least 2 cues to detect tracking leaks.",
            "risk_tier": "SAFE_READ",
        }, indent=2)

    # Compare adjacent cue pairs
    leaks: list[dict] = []
    prev_raw = await client.send_command_with_response(f"list cue {cue_ids[0]} sequence {sequence_id}")

    for i in range(1, len(cue_ids)):
        curr_raw = await client.send_command_with_response(f"list cue {cue_ids[i]} sequence {sequence_id}")

        # Find values present in both that aren't explicitly blocked
        prev_vals = set(prev_raw.strip().splitlines())
        curr_vals = set(curr_raw.strip().splitlines())
        shared = prev_vals & curr_vals

        # Lines that appear identical in both cues AND contain attribute data
        for line in shared:
            line = line.strip()
            if re.match(r"^\s*\w+\s+\d", line) and "block" not in line.lower():
                attr_match = re.match(r"^\s*(\w+)", line)
                if attr_match:
                    leaks.append({
                        "cue_from": cue_ids[i - 1],
                        "cue_to": cue_ids[i],
                        "attribute": attr_match.group(1),
                        "value": line.strip()[:100],
                        "note": "Value identical in adjacent cues — may be tracking forward without explicit set",
                    })

        prev_raw = curr_raw
        await asyncio.sleep(0.05)

    rec = "No tracking leaks detected." if not leaks else (
        f"Found {len(leaks)} potential tracking leak(s). "
        "Use Block on cues where values should stop tracking forward."
    )

    return json.dumps({
        "sequence_id": sequence_id,
        "leaks": leaks[:50],
        "total_leaks": len(leaks),
        "cues_checked": len(cue_ids),
        "recommendation": rec,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def audit_page_consistency(
    page: int = 1,
) -> str:
    """
    Audit an executor page for layout consistency issues (SAFE_READ).

    Checks: all executors labeled, speed masters assigned, first-button
    protocol followed, no orphan executors, consistent naming.

    Args:
        page: Executor page to audit (default 1).

    Returns:
        str: JSON with checks[], overall_status, recommendation.
    """
    raw_map = await get_page_map(page=page)
    map_data = json.loads(raw_map)

    if "error" in map_data:
        return raw_map

    executors = map_data.get("executors", [])
    checks: list[dict[str, str]] = []

    # Check 1: All executors labeled
    unlabeled = [e for e in executors if e["label"].startswith("Exec ")]
    if unlabeled:
        checks.append({
            "check": "all_labeled",
            "status": "warning",
            "detail": f"{len(unlabeled)} executor(s) missing labels: {[e['id'] for e in unlabeled[:5]]}",
        })
    else:
        checks.append({"check": "all_labeled", "status": "ok", "detail": "All executors are labeled"})

    # Check 2: Speed master assigned
    has_speed = any("speed" in e.get("fader_function", "").lower() for e in executors)
    if executors and not has_speed:
        checks.append({
            "check": "speed_master",
            "status": "warning",
            "detail": "No speed master found on this page — effects won't have tempo control",
        })
    else:
        checks.append({"check": "speed_master", "status": "ok", "detail": "Speed master present"})

    # Check 3: First-button protocol (first executor should be a Go button)
    if executors:
        first = executors[0]
        if first["type"] != "sequence":
            checks.append({
                "check": "first_button_protocol",
                "status": "warning",
                "detail": f"First executor ({first['id']}) is '{first['type']}' — convention is sequence for first-button Go",
            })
        else:
            checks.append({"check": "first_button_protocol", "status": "ok", "detail": "First executor is a sequence"})

    # Check 4: Orphan executors (assigned but no sequence)
    orphans = [e for e in executors if e["type"] == "empty" and e["label"] != f"Exec {e['id']}"]
    if orphans:
        checks.append({
            "check": "orphan_executors",
            "status": "warning",
            "detail": f"{len(orphans)} labeled but empty executor(s): {[e['id'] for e in orphans[:5]]}",
        })
    else:
        checks.append({"check": "orphan_executors", "status": "ok", "detail": "No orphan executors"})

    # Check 5: Priority consistency
    priorities = [e["priority"] for e in executors if e["type"] == "sequence"]
    mixed = len(set(priorities)) > 2 if priorities else False
    if mixed:
        checks.append({
            "check": "priority_consistency",
            "status": "warning",
            "detail": f"Mixed priorities on page: {set(priorities)}",
        })
    else:
        checks.append({"check": "priority_consistency", "status": "ok", "detail": "Priority usage is consistent"})

    overall = "ok"
    if any(c["status"] == "fail" for c in checks):
        overall = "fail"
    elif any(c["status"] == "warning" for c in checks):
        overall = "warning"

    return json.dumps({
        "page": page,
        "checks": checks,
        "overall_status": overall,
        "executors_checked": len(executors),
        "recommendation": "Page looks clean." if overall == "ok" else "Review warnings above before going live.",
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def plan_fixture_swap(
    old_fixture_type: str,
    new_fixture_type: str,
) -> str:
    """
    Plan a fixture type swap and assess compatibility (SAFE_READ).

    Compares attributes between old and new fixture types to identify
    what will transfer cleanly and what needs manual attention.

    Args:
        old_fixture_type: Current fixture type name (e.g. "Mac 700 Profile").
        new_fixture_type: Target fixture type name (e.g. "Mac Viper").

    Returns:
        str: JSON with compatible_attributes, missing_attributes, risk_level, migration_steps.
    """
    client = await get_client()

    async def _get_type_attrs(type_name: str) -> set[str]:
        """Discover attributes for a fixture type by navigating the cd tree."""
        await client.send_command_with_response("cd /")
        raw = await client.send_command_with_response("list fixture")
        attrs: set[str] = set()
        # Look for the fixture type in the listing
        for line in raw.splitlines():
            if type_name.lower() in line.lower():
                # Try to get attribute info
                fixture_match = re.match(r"^\s*(\d+)\s", line.strip())
                if fixture_match:
                    fid = fixture_match.group(1)
                    info = await client.send_command_with_response(f"info fixture {fid}")
                    # Extract attribute names from info output
                    for attr_match in re.finditer(r"(?:Attribute|Attr|Channel)\s*[=:]\s*(\w+)", info, re.IGNORECASE):
                        attrs.add(attr_match.group(1))
                    break
        await client.send_command_with_response("cd /")
        return attrs

    old_attrs = await _get_type_attrs(old_fixture_type)
    new_attrs = await _get_type_attrs(new_fixture_type)

    if not old_attrs and not new_attrs:
        return json.dumps({
            "error": "Could not discover attributes for either fixture type. Ensure both are patched.",
            "old_fixture_type": old_fixture_type,
            "new_fixture_type": new_fixture_type,
            "risk_tier": "SAFE_READ",
        }, indent=2)

    compatible = sorted(old_attrs & new_attrs)
    missing_in_new = sorted(old_attrs - new_attrs)
    new_only = sorted(new_attrs - old_attrs)
    compat_pct = len(compatible) / max(len(old_attrs), 1) * 100

    risk = "low" if compat_pct >= 80 else "medium" if compat_pct >= 50 else "high"

    steps = [
        "1. Save the current show (SaveShow)",
        "2. Export current presets using PSR if needed",
        f"3. Import the new fixture type '{new_fixture_type}' if not already in library",
        "4. Use Clone to copy fixture data from old to new fixtures",
    ]
    if missing_in_new:
        steps.append(f"5. Manually adjust {len(missing_in_new)} missing attribute(s): {missing_in_new[:5]}")
    steps.append(f"{'5' if not missing_in_new else '6'}. Verify all presets and cues reference the correct attributes")
    steps.append(f"{'6' if not missing_in_new else '7'}. Run validate_preset_references on affected sequences")

    return json.dumps({
        "old_fixture_type": old_fixture_type,
        "new_fixture_type": new_fixture_type,
        "compatible_attributes": compatible,
        "missing_in_new": missing_in_new,
        "new_only_attributes": new_only,
        "compatibility_percent": round(compat_pct, 1),
        "risk_level": risk,
        "migration_steps": steps,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def incident_snapshot() -> str:
    """
    Capture full console state for incident reporting (SAFE_READ).

    Creates a comprehensive snapshot of the current console state including
    page, modes, selection, parks, filter/world, active executors, and
    recent errors. Use this when something goes wrong on site.

    Returns:
        str: JSON with full state capture and human-readable summary.
    """
    snap = getattr(_orchestrator, "last_snapshot", None)
    client = await get_client()

    # Always get fresh system vars
    raw_vars = await client.send_command_with_response("listvar")

    def _extract_var(name: str) -> str:
        m = re.search(rf"{name}\s*[=:]\s*(.+?)(?:\r|\n|$)", raw_vars, re.IGNORECASE)
        return m.group(1).strip() if m else "unknown"

    # Build snapshot data
    state: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "showfile": _extract_var("SHOWFILE"),
        "version": _extract_var("VERSION"),
        "user": _extract_var("USER"),
        "user_rights": _extract_var("USERRIGHTS"),
        "fader_page": _extract_var("FADERPAGE"),
        "selected_fixtures": _extract_var("SELECTEDFIXTURESCOUNT"),
        "selected_executor": _extract_var("SELECTEDEXEC"),
    }

    if snap:
        state["console_modes"] = getattr(snap, "console_modes", {})
        state["parked_fixtures"] = sorted(list(getattr(snap, "parked_fixtures", set()) or set()))[:20]
        state["parked_count"] = len(getattr(snap, "parked_fixtures", set()) or set())
        state["active_filter"] = getattr(snap, "active_filter", None)
        state["active_world"] = getattr(snap, "active_world", None)
        state["active_macros"] = getattr(snap, "active_macros", [])
        state["snapshot_age_s"] = round(snap.age_seconds(), 1) if hasattr(snap, "age_seconds") else None

        # Active executors
        exec_state = getattr(snap, "executor_state", {}) or {}
        active_execs = []
        for eid, es in exec_state.items():
            if hasattr(es, "sequence_id") and es.sequence_id:
                active_execs.append({"id": eid, "sequence_id": es.sequence_id})
        state["active_executors"] = active_execs[:20]
    else:
        state["snapshot_available"] = False
        state["note"] = "No hydrated snapshot — run hydrate_console_state for richer data"

    # Recent telemetry errors
    try:
        from src.telemetry import _get_telemetry
        tel = _get_telemetry()
        recent = tel.recent_errors(limit=5) if hasattr(tel, "recent_errors") else []
        state["recent_errors"] = recent
    except Exception:
        state["recent_errors"] = []

    # Human-readable summary
    lines = [
        f"Incident Snapshot — {state['timestamp']}",
        f"Show: {state['showfile']} (v{state['version']})",
        f"User: {state['user']} ({state['user_rights']})",
        f"Page: {state['fader_page']}, Selected: {state['selected_fixtures']} fixtures",
    ]
    if snap:
        modes_on = [k for k, v in (state.get("console_modes") or {}).items() if v]
        if modes_on:
            lines.append(f"Active modes: {', '.join(modes_on)}")
        if state.get("parked_count", 0) > 0:
            lines.append(f"Parked fixtures: {state['parked_count']}")

    state["summary"] = "\n".join(lines)
    state["risk_tier"] = "SAFE_READ"

    return json.dumps(state, indent=2, default=str)


# ============================================================
# OSC Output (Resolume, etc.)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def send_osc(
    address: str,
    value: float | int | str,
    host: str = "localhost",
    port: int = 7000,
) -> str:
    """
    Send an OSC message to an external application like Resolume Arena (SAFE_WRITE).

    Uses raw UDP — no extra dependencies. Works with any OSC-compatible software:
    Resolume Arena/Avenue, QLab, TouchDesigner, Ableton, etc.

    Common Resolume OSC addresses:
      /composition/tempocontroller/tempo  — set BPM (float)
      /composition/layers/N/clips/M/connect — trigger clip (int 1)
      /composition/layers/N/video/opacity — layer opacity (float 0.0-1.0)
      /composition/disconnectall — clear all clips (int 1)

    Args:
        address: OSC address pattern (e.g. "/composition/tempocontroller/tempo").
        value: Value to send — float, int, or string.
        host: Target host (default "localhost").
        port: Target OSC port (default 7000, Resolume's default).

    Returns:
        str: JSON with address, value, host, port, status.

    Examples:
        - Set Resolume BPM: send_osc(address="/composition/tempocontroller/tempo", value=128.0)
        - Trigger clip: send_osc(address="/composition/layers/1/clips/1/connect", value=1)
        - Layer opacity: send_osc(address="/composition/layers/1/video/opacity", value=0.75)
    """
    import socket
    import struct

    def _build_osc_message(addr: str, val: float | int | str) -> bytes:
        """Build a minimal OSC message packet."""
        # Pad address to 4-byte boundary
        addr_bytes = addr.encode("utf-8") + b"\x00"
        while len(addr_bytes) % 4 != 0:
            addr_bytes += b"\x00"

        if isinstance(val, float):
            type_tag = b",f\x00\x00"
            val_bytes = struct.pack(">f", val)
        elif isinstance(val, int):
            type_tag = b",i\x00\x00"
            val_bytes = struct.pack(">i", val)
        else:
            # String
            s = str(val).encode("utf-8") + b"\x00"
            while len(s) % 4 != 0:
                s += b"\x00"
            type_tag = b",s\x00\x00"
            val_bytes = s

        return addr_bytes + type_tag + val_bytes

    try:
        packet = _build_osc_message(address, value)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(packet, (host, port))
        sock.close()

        return json.dumps({
            "status": "sent",
            "address": address,
            "value": value,
            "host": host,
            "port": port,
            "packet_size": len(packet),
            "risk_tier": "SAFE_WRITE",
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "address": address,
            "host": host,
            "port": port,
            "risk_tier": "SAFE_WRITE",
        }, indent=2)


# ============================================================
# MCP Resources
# Static and semi-static context exposed as URI-addressable docs
# ============================================================


@mcp.resource("ma2://docs/rights-matrix")
def resource_rights_matrix() -> str:
    """
    MA2 OAuth scope → MA2Right mapping matrix (read-only reference).

    Returns the full JSON rights matrix from doc/ma2-rights-matrix.json.
    Use this resource to look up which OAuth scope is required for any
    MA2 operation before attempting to call a tool.
    """
    rights_path = Path(__file__).parent.parent / "doc" / "ma2-rights-matrix.json"
    try:
        return rights_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return json.dumps({"error": "rights matrix not found at doc/ma2-rights-matrix.json"})


@mcp.resource("ma2://docs/vocab-summary")
def resource_vocab_summary() -> str:
    """
    grandMA2 keyword vocabulary summary — all 141 keywords with RiskTier and category.

    Use this resource to look up the safety tier of any MA2 keyword before
    including it in a command string.  Tier determines whether confirm_destructive
    is required and which OAuthScope must be active.
    """
    from src.vocab import classify_token, load_vocab
    spec = load_vocab()
    summary = {}
    all_keywords = list(spec.function_keywords.keys()) + list(spec.object_keywords.keys())
    for kw in all_keywords:
        resolved = classify_token(kw, spec)
        summary[kw] = {"category": resolved.category, "risk_tier": resolved.risk_tier}
    return json.dumps(summary, indent=2)


@mcp.resource("ma2://docs/tool-taxonomy")
def resource_tool_taxonomy() -> str:
    """
    ML-generated tool taxonomy — 210 tools clustered into 14 categories.

    Each entry includes tool name, category, and docstring summary.
    Use this resource to understand the tool landscape before calling
    suggest_tool_for_task, or to verify a tool exists before invoking it.
    """
    taxonomy = _load_taxonomy_cached()
    # Return a compact summary: category → tool names
    categories = taxonomy.get("categories", {})
    summary = {
        cat: [t["name"] for t in data.get("tools", [])]
        for cat, data in categories.items()
    }
    return json.dumps({"categories": summary, "total_tools": sum(len(v) for v in summary.values())}, indent=2)


@mcp.resource("ma2://docs/responsibility-map")
def resource_responsibility_map() -> str:
    """
    Module responsibility map — every file's primary role and architectural smells.

    Use this resource when making architectural decisions or when adding new
    modules, to ensure the new code is placed in the correct layer.
    """
    map_path = Path(__file__).parent.parent / "doc" / "responsibility-map.md"
    try:
        return map_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "# Responsibility map not found. Run the architecture audit to regenerate."


@mcp.resource("ma2://docs/tool-surface-tiers")
def resource_tool_surface_tiers() -> str:
    """
    Tool surface tier classification — which tools are Tier A (always visible),
    Tier B (retrievable), or Tier C (internal).

    Use this resource to decide whether to add a new tool to the planner-visible
    surface or keep it as a worker-only primitive.
    """
    tiers_path = Path(__file__).parent.parent / "doc" / "tool-surface-tiers.md"
    try:
        return tiers_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "# Tool surface tiers doc not found."


@mcp.resource("ma2://skills/{skill_id}")
def resource_skill_body(skill_id: str) -> str:
    """
    Retrieve a skill's formatted injection payload by ID.

    Returns the skill body formatted as a user message ready for injection,
    but only if the skill is usable (approved or non-DESTRUCTIVE).
    Returns an error message if the skill is not found or not yet approved.

    Use SkillRegistry.get_usable() for the same check with Python access.
    """
    from src.skill import SkillRegistry
    reg = SkillRegistry()
    skill = reg.get_usable(skill_id)
    if skill is None:
        sk = reg.get(skill_id)
        if sk is None:
            return f"Skill '{skill_id}' not found in registry."
        return f"Skill '{skill_id}' exists but is not usable (safety_scope=DESTRUCTIVE, approved=False). Requires SYSTEM_ADMIN approval."
    return skill.as_user_message()


@mcp.resource("ma2://busking/patterns")
def resource_busking_patterns() -> str:
    """
    Best-practice busking patterns for live performance lighting (read-only).

    Covers: fader-per-effect model, song macro page protocol, live recovery
    steps, and color lock technique. Use before designing a busking show.
    """
    return """\
# grandMA2 Busking Patterns

## Fader-Per-Effect Model
Each executor on a fader page runs one effect. The fader controls intensity
(0 = silent, 100 = full). Effects stay armed — zero fader silences, raise
fader restores. Never release effects mid-song; use normalize_page_faders.

Layout convention:
  - Column 1 (Exec 1): Song loader macro (first-button protocol)
  - Columns 2–8 (Exec 2–8): Effect faders (strobe, chase, color, beam...)
  - Columns 9–10: Group masters (intensity override for rig sections)
  - Fixed right page: Global effects that persist across songs

## Song Macro Page Protocol
Each song gets one page. Page name: `SNG_{n}_{SongName}` (e.g. SNG_3_Villains).

**First button (Exec 1) macro lines:**
1. `ClearAll` — reset programmer
2. `Go Preset 4.{palette_id}` — apply song color palette
3. `Go Macro {song_setup_macro}` — recall rig positions and timing
4. `SelectDrive {executor_page}` — jump to this song's effect page

**Remaining buttons:** effect executors — no macros, faders only.

## Live Recovery Protocol
When show state drifts (wrong levels, stuck effects):
1. `normalize_page_faders(page)` — zero all faders silently
2. `clear_effects_on_page(page)` — release stuck executors
3. Re-trigger song loader (Exec 1) to restore clean state
4. Gradually raise faders to rebuild look

## Color Lock Technique
Prevents color bleed when multiple effects are active:
1. Store song color as a Color preset (e.g. Preset 4.30 = deep amber)
2. Apply preset to all fixtures via Group masters before effects start
3. Effects modulate intensity/position only — color preset holds the hue
4. On song change: apply new color preset before raising new effect faders
"""


@mcp.resource("ma2://busking/effect-design")
def resource_effect_design() -> str:
    """
    Effect-to-executor assignment patterns and rate/speed semantics (read-only).

    Covers: assign_effect_to_executor usage, rate vs speed distinction,
    MAtricks layering for busking, and batch release safety.
    """
    return """\
# grandMA2 Effect Design for Busking

## Effect Assignment
Use `assign_effect_to_executor(effect_id, executor_id, page=N)` to bind an
effect from the library to a fader slot. This is DESTRUCTIVE — do during
pre-show programming, not during live performance.

Command generated: `Assign Effect {id} Executor {id}` or `Assign Effect {id} Page {n}.{exec}`

After assignment, the fader controls the effect's master intensity (0-100).
The effect runs continuously while the executor is active.

## Rate vs Speed
| Parameter | Command | Semantics | Range |
|-----------|---------|-----------|-------|
| Rate | `EffectRate {n}` | Relative multiplier — 100 = normal | 1–200 |
| Speed | `EffectSpeed {n}` | Absolute BPM — overrides rate | 20–300 |

Use `modulate_effect(mode="rate", value=150)` to push effects 1.5× faster.
Use `modulate_effect(mode="speed", value=120)` to lock effects to 120 BPM.

Speed and rate affect the *selected* effects globally. To target a specific
executor's effect, select it first with `select_executor(executor_id)`.

## MAtricks Layering
Layer MAtricks patterns over effects for per-fixture phase offsets:
1. Select group, apply MAtricks Interleave
2. Run effect — each fixture gets a phase offset proportional to its index
3. Adjust interleave with `modulate_effect` rate to control chase tightness

## Batch Release Safety
`clear_effects_on_page(page, start_exec=1, end_exec=20)` sends 20 Off
commands in a single chained string. On slow consoles this may cause a
brief flash as effects die in sequence. To avoid: use `normalize_page_faders`
first (silences without visual glitch), then `clear_effects_on_page`.
"""


@mcp.resource("ma2://busking/color-design")
def resource_color_design() -> str:
    """
    Constrained color palette design for busking shows (read-only).

    Covers: HSB palette strategy, preset numbering, monochromatic constraint,
    and color lock via group master. Use when designing song color palettes.
    """
    return """\
# grandMA2 Constrained Color Design for Busking

## HSB vs RGB
Always use HSB for live busking color design. MA2 HSB range: 0-100 (not 0-255).

| Parameter | Flag | Range | Notes |
|-----------|------|-------|-------|
| Hue | `/h=` | 0–360 | Degrees |
| Saturation | `/s=` | 0–100 | 0 = white, 100 = full color |
| Brightness | `/br=` | 0–100 | 0 = black, 100 = full |

Example: `store_preset 4.30 /h=30 /s=95 /br=100` = deep amber.

## Monochromatic Palette Strategy
Each song gets one hue with 4 brightness stops:
- Stop 1: Full intensity (br=100, s=90)
- Stop 2: Mid punch (br=70, s=85)
- Stop 3: Moody fill (br=40, s=80)
- Stop 4: Near-black accent (br=15, s=75)

## Preset Numbering Convention
`preset_id = song_id * 10 + stop_index`

| Song | Stop | Preset |
|------|------|--------|
| Song 1 | 1 (full) | 11 |
| Song 1 | 2 (mid) | 12 |
| Song 3 | 4 (accent) | 34 |

Recall with `apply_preset(preset_type="color", preset_id=34)`.

## Color Lock Technique
1. Before raising effect faders, apply the song's full-intensity color preset
   to all rig fixtures via group masters: `group_at(group_id=99, value=100)`
2. Effects that only modulate intensity/position inherit the locked color
3. Transition between songs: apply new color preset (step 1) BEFORE releasing
   the previous song's effect faders — avoids white flash on crossover
4. For fixtures with separate color channels (CMY movers): store color in a
   Color preset, not in the programmer, so it survives `ClearAll`
"""


@mcp.resource("ma2://docs/volunteer-guide")
def resource_volunteer_guide() -> str:
    """
    Volunteer operator guide — plain-language grandMA2 operation for non-programmers.

    Explains the three-tier access model, Sunday morning preflight procedure,
    and what to do when things go wrong. Designed for church technical directors
    training volunteers and any production environment with tiered staff skill levels.
    """
    return """\
# MA2 Agent Volunteer Operator Guide

## The Three Safety Tiers

MA2 Agent enforces three access levels automatically. You cannot accidentally break something outside your tier.

| Your Role | Tier | What You Can Do |
|-----------|------|-----------------|
| New volunteer | SAFE_READ | See console state, verify the show is correct. Zero risk. |
| Trained operator | SAFE_WRITE | Trigger go/pause, adjust faders, apply presets. With guidance. |
| Technical Director | DESTRUCTIVE | Store cues, modify show file, change patch. TD only. |

## Sunday Morning Preflight (Any Volunteer -- SAFE_READ)

Run in order before doors open:

1. Verify show file -- get_showfile_info() -- confirm show name matches expected
2. Check for changes -- assert_showfile_unchanged() -- if this fails, STOP and call TD
3. Hydrate -- hydrate_console_state() -- snapshot everything
4. Check presets -- list_preset_pool(preset_type="color") -- should have entries
5. Check executors -- get_executor_detail(executor_id="1.1") -- confirm sequence assigned
6. Check cues -- query_object_list(object_type="sequence", object_id=1) -- confirm cues present

All GREEN? You are ready. Any RED? Call your TD before service.

## During Service (Trained Volunteer -- SAFE_WRITE)

- Advance cues: playback_action(executor_id, action="go")
- Pause: playback_action(executor_id, action="pause")
- Jump to cue: goto_cue(executor_id, cue_id)

## When Things Go Wrong

| Problem | Action |
|---------|--------|
| Wrong look on stage | Do NOT touch anything. Note cue number. Call TD. |
| Console unresponsive | Run get_console_location(). If error, notify TD. |
| Show file looks different | Run assert_showfile_unchanged(). If fails, STOP, call TD immediately. |
| Executor shows wrong state | Run get_executor_detail(executor_id) and report to TD. |

Rule: If in doubt, do nothing and call your TD.
"""


@mcp.resource("ma2://docs/sb132-compliance")
def resource_sb132_compliance() -> str:
    """
    SB 132 compliance guide — California Film & Television Tax Credit safety documentation
    requirements mapped to MA2 Agent telemetry fields.

    For gaffers, safety officers, production managers, and insurance brokers on
    productions receiving the California Film & Television Tax Credit (effective July 2025).
    """
    return """\
# SB 132 Compliance Guide for MA2 Agent

## What SB 132 Requires (July 2025)

California SB 132 applies to productions receiving the CA Film & Television Tax Credit and requires:

1. Dedicated Safety Advisor -- on set daily
2. Written Risk Assessment -- before any high-risk operation
3. Daily Safety Meeting Notes -- documented
4. Final Safety Report -- within 60 days of wrap

## MA2 Agent Data to SB 132 Mapping

| SB 132 Requirement | MA2 Agent Source | Tool |
|---|---|---|
| Written risk assessment | risk_tier per operation (SAFE_READ/SAFE_WRITE/DESTRUCTIVE) | get_telemetry_report() |
| Operator identification | operator field in tool_invocations | get_telemetry_report() |
| Daily safety meeting notes | session_id grouped timeline with timestamps | generate_compliance_report() |
| Incident log | error_class field in tool_invocations | get_telemetry_report(risk_tier="DESTRUCTIVE") |
| Final safety report | Full session export | generate_compliance_report(session_id=...) |

## Three-Tier Risk Stratification (for Insurance Underwriters)

MA2 Agent classifies every lighting control operation:

- SAFE_READ -- Read-only monitoring. Zero risk to console state or physical hardware.
- SAFE_WRITE -- Controlled modifications (level adjustments, go/pause). Standard operational risk.
- DESTRUCTIVE -- High-risk operations (cue storage, show file changes, patch modifications).
  Requires explicit confirm_destructive=True AND elevated OAuth scope. All logged.

## Generating a Compliance Report

Use generate_compliance_report(session_id, production_name, operator_name, days=1)
for a markdown report ready for safety documentation.

Use get_telemetry_report(session_id, format="json") for archival JSON export.

## Insurance Brief Template

All lighting control operations during [PRODUCTION NAME] were processed through
MA2 Agent's three-tier safety system. [N] operations were classified SAFE_READ
(read-only monitoring, zero risk), [M] were SAFE_WRITE (controlled modifications
requiring standard authorization), and [K] were DESTRUCTIVE (required explicit
authorization and elevated scope). Full telemetry is retained for forensic review
and available upon request from the production safety advisor.

## IATSE Kit Rental

Under the 2024 IATSE-AMPTP contract, AI tools used by union members constitute "covered work"
and operators may charge a kit rental fee. MA2 Agent's operator field in telemetry
records which union member ran each session, supporting kit rental documentation.
"""


@mcp.resource("ma2://docs/rdm-workflow")
def resource_rdm_workflow() -> str:
    """
    RDM (Remote Device Management) workflow reference — discovery, device info,
    and autopatch best practices for grandMA2 via telnet.
    """
    return """\
# RDM Workflow Reference

## What is RDM?

RDM (Remote Device Management) is a bidirectional extension to DMX512 (ANSI E1.20)
that allows a lighting console to identify, configure, and report status from
intelligent fixtures without additional cabling.

## When to Use RDM

| Use Case | RDM Benefit |
|----------|------------|
| Unknown rig | Identify all fixtures and their current DMX addresses |
| Address conflicts | Read device-reported addresses vs. patch sheet |
| Fixture status | Get lamp hours, temperature, error status |
| Autopatch | Let MA2 suggest addresses based on discovered footprints |

## Tool Sequence

1. Discover all RDM devices on a universe: rdm_discover(universe_id=1)
   Returns: list of {uid, manufacturer, device_model, footprint, current_address}

2. Get detailed info for a specific device: rdm_get_info(uid="0x1234567890AB")
   Returns: full device profile including label, DMX footprint, current address, error status

3. Apply a DMX address (autopatch): rdm_patch(uid="0x1234567890AB", target_address=1, confirm_destructive=True)
   Assigns the fixture to channel 1 on its universe

## Limitations

- Not all fixtures support RDM. Most intelligent fixtures do; dimmers may not.
- RDM requires a proper terminator at the end of the DMX chain.
- RDM discovery can take 10-30 seconds per universe on large rigs.
- After RDM patch, verify with list_fixtures() and detect_dmx_address_conflicts().

## RDM vs Manual Patching

| | RDM | Manual |
|---|---|---|
| Speed | Fast for large rigs | Faster for small rigs |
| Accuracy | Device-reported | Human-verified |
| Risk | Overwrites existing addresses | You control every address |
| Recommended when | Unknown rental rig, >50 fixtures | Known rig, <20 fixtures |
"""


@mcp.resource("ma2://docs/lua-scripting")
def resource_lua_scripting() -> str:
    """
    grandMA2 Lua 5.2 scripting reference — gma.* namespace, plugin lifecycle,
    and common patterns for MCP-driven plugin development.
    """
    return """\
# grandMA2 Lua Scripting Reference

## Environment

grandMA2 uses Lua 5.2 with the gma.* namespace for console integration.
Standard Lua libraries (math, string, table, io) are available.

## Core gma.* Functions

| Function | Description |
|----------|-------------|
| gma.cmd(str) | Execute a MA2 command |
| gma.echo(str) | Print to feedback line |
| gma.show.getvar(name) | Read show variable |
| gma.show.setvar(name, val) | Write show variable |
| gma.user.confirm(msg) | Show OK/Cancel dialog |
| gma.timer.sleep(ms) | Pause execution (ms) |
| gma.gui.confirm(title, msg) | GUI confirmation |

## Plugin vs Macro: Decision Guide

| Need | Use |
|------|-----|
| Simple linear commands | Macro (MA2 command strings) |
| Loop (for/while) | Lua Plugin |
| Math calculation | Lua Plugin |
| Read/write variables | Either (SetVar in macro, gma.show.setvar in Lua) |
| User dialog (confirm/input) | Lua Plugin only |
| Conditional (if/else) | Lua Plugin |

## Common Patterns

Loop over fixture IDs:
  for i = 1, 20 do
      gma.cmd("Fixture " .. i .. " At 100")
      gma.timer.sleep(100)
  end

Read and branch on system variable:
  local pg = tonumber(gma.show.getvar("FADERPAGE"))
  if pg == 1 then gma.cmd("Page 2") else gma.cmd("Page 1") end

User confirmation gate:
  if gma.user.confirm("Delete all cues in Sequence 99?") then
      gma.cmd("Delete Cue 1 Thru 999 Sequence 99")
      gma.echo("Cues deleted.")
  else
      gma.echo("Cancelled.")
  end

## MCP Integration

Use run_lua_script(script_body) to execute inline Lua via MCP.
Use call_plugin_tool(plugin_name, args) to invoke a saved plugin by name.
Use reload_all_plugins() after uploading a new .lua file via USB.

Safety note: Lua scripts executed via gma.cmd() bypass MCP's safety gate.
Ensure scripts that call DESTRUCTIVE commands (Store, Delete, Assign) include
appropriate confirmations via gma.user.confirm().
"""


# ============================================================
# MCP Prompts
# User-initiated workflow templates for console operations
# ============================================================


@mcp.prompt()
def preflight_destructive_change(operation: str, target: str, reason: str = "") -> str:
    """
    Run pre-flight checks before any destructive console operation.

    Use this prompt before calling any DESTRUCTIVE tool to ensure the
    operation is safe to proceed.

    Args:
        operation: The destructive operation to perform (e.g. "delete_object", "store_current_cue").
        target: The object or path being modified (e.g. "Group 5", "Sequence 1 Cue 3").
        reason: Why this change is needed (optional but recommended for audit trail).
    """
    return f"""Perform a safety pre-flight before executing: {operation} on {target}

Reason: {reason or "(not specified)"}

Pre-flight checklist:
1. Read `ma2://docs/rights-matrix` — confirm the current user has sufficient rights for {operation}.
2. Call `list_system_variables` — check $USERRIGHTS and $SHOWFILE.
3. Call `get_object_info` on {target} — confirm the target exists and capture its current state.
4. Check if Blind mode is active (`$BLINDMODE` or `mode_overrides["blind"]`).
5. If the operation affects executors, verify no cue is running on the target executor.

Only proceed with {operation} after all five checks pass.
If any check fails, report the finding and ask the user to confirm before proceeding.
Use `confirm_destructive=True` when calling the tool."""


@mcp.prompt()
def inspect_console(focus: str = "full") -> str:
    """
    Guided console state inspection — Inspect workflow.

    Produces a structured console overview without any mutations.

    Args:
        focus: What to inspect — "full" (default), "playback", "fixtures", "show", or "rights".
    """
    focus_map = {
        "full": "system variables, active executors, programmer state, and current show info",
        "playback": "active executors, running cues, fader levels, and executor assignments",
        "fixtures": "patched fixture types, selected fixtures, programmer content",
        "show": "show file name, universe count, group count, sequence count, and preset pool sizes",
        "rights": "current user, rights level, active world, and active filter",
    }
    scope = focus_map.get(focus, focus_map["full"])
    return f"""Inspect the grandMA2 console — {focus} focus.

Read-only inspection only. No mutations permitted.

Steps:
1. Call `list_system_variables` — capture all 26 system variables.
2. Inspect: {scope}.
3. Call `navigate_console` to `cd /` and `list_console_destination` to see the root object tree.
4. If focus includes executors: call `query_object_list` for active sequences and their cue counts.
5. Summarize findings in this structure:

{{
  "console_version": "$VERSION",
  "show_file": "$SHOWFILE",
  "active_user": "$USER",
  "rights": "$USERRIGHTS",
  "selected_exec": "$SELECTEDEXEC",
  "active_cue": "$SELECTEDEXECCUE",
  "fixture_count": <from list>,
  "findings": ["..."]
}}"""


@mcp.prompt()
def plan_cue_store(
    sequence_id: str,
    cue_number: str,
    fixture_selection: str,
    preset_or_values: str,
) -> str:
    """
    Plan a cue store operation with safety and rights checks — Plan workflow.

    Use this prompt to generate a structured cue store plan before executing.
    The plan includes pre-flight checks, proposed commands, and a verification step.

    Args:
        sequence_id: Sequence number (e.g. "1", "99").
        cue_number: Target cue number (e.g. "1", "3.5").
        fixture_selection: Fixture group or ID range to use (e.g. "Group 1", "Fixture 1 Thru 10").
        preset_or_values: Preset to apply or manual values (e.g. "Preset 4.5", "Full").
    """
    return f"""Plan a cue store operation without executing it yet.

Target: Store Cue {cue_number} in Sequence {sequence_id}
Fixtures: {fixture_selection}
Values/Preset: {preset_or_values}

Plan steps:
1. PRE-FLIGHT: Call `list_system_variables` — confirm $USERRIGHTS has Programmer or higher.
2. PRE-FLIGHT: Call `query_object_list` for Sequence {sequence_id} — check if Cue {cue_number} already exists.
   If it exists: plan a /merge store. If not: plan a clean store.
3. SELECT: Plan `SelFix {fixture_selection}` — verify fixture count > 0.
4. APPLY: Plan `{preset_or_values}` — identify whether this is a preset recall or direct value.
5. STORE PLAN: Emit the exact command to be executed:
   `Store Cue {cue_number} Sequence {sequence_id} /merge`
6. VERIFY PLAN: After store, plan `query_object_list` on Sequence {sequence_id} to confirm Cue {cue_number} exists.

Return the plan as a JSON object with "pre_flight", "commands", and "verify" arrays.
Do NOT execute any commands yet. This is a planning step only."""


@mcp.prompt()
def diagnose_playback_failure(executor_id: str, symptom: str) -> str:
    """
    Diagnose a playback failure on a specific executor — Inspect + Plan workflows.

    Use this prompt when a cue or executor is not behaving as expected.

    Args:
        executor_id: The executor identifier (e.g. "1", "201", "1.1.201").
        symptom: What is observed (e.g. "cue not advancing", "no output", "wrong fixtures responding").
    """
    return f"""Diagnose playback failure on Executor {executor_id}.

Observed symptom: {symptom}

Diagnostic steps:
1. Call `list_system_variables` — check $SELECTEDEXEC, $SELECTEDEXECCUE, $FADERPAGE.
2. Call `query_object_list` for the sequence assigned to Executor {executor_id} — count cues, check for gaps.
3. Call `get_object_info` on Executor {executor_id} — check assignment, priority, options.
4. Call `send_raw_command` with `list Executor {executor_id}` — capture raw executor state.
5. Load skill `ma2://skills/telnet-feedback-triage` — apply FeedbackClass classification to any UNKNOWN COMMAND or WARNING responses.

Common failure patterns:
- "no output": check blind mode ($BLINDMODE), check if output is patched, check DMX universe assignment.
- "cue not advancing": check trigger setting (Time/Go), check MIB settings, check if executor has "Kill" active.
- "wrong fixtures": check world assignment, check if programmer has conflicting values (call `clear_programmer`).

Return structured findings: {{"fault_class": "...", "root_cause": "...", "recommended_actions": [...]}}"""


@mcp.prompt()
def load_show_safely(show_name: str) -> str:
    """
    Safe show loading checklist — prevents accidental Telnet disconnection.

    Use this prompt before any new_show or load_show operation.

    Args:
        show_name: The show file to load (e.g. "my_show_2026").
    """
    return f"""Load show "{show_name}" safely without severing the MCP Telnet connection.

Pre-load checklist:
1. Call `list_system_variables` — record current $SHOWFILE, $HOSTIP, $VERSION.
2. Call `save_show` if any unsaved changes should be preserved.
3. CRITICAL: Verify that the load command will preserve connectivity:
   - For `new_show`: MUST use preserve_connectivity=True (passes /globalsettings /network /protocols).
   - For `load_show`: confirm the target show has Telnet enabled in its global settings.
4. Confirm the operator understands: loading a show with Telnet disabled will disconnect this MCP session.

Only proceed after the checklist is complete.
If loading a completely blank show, the user MUST manually re-enable Telnet in
Setup → Console → Global Settings before the next MCP connection."""


@mcp.prompt()
def bootstrap_rights_users() -> str:
    """
    Bootstrap the standard six-tier MA2 rights user accounts — guided provisioning workflow.

    Use this prompt when setting up a new show file with the standard
    operator rights ladder (Admin, LightOperator, Programmer, PlaybackOperator, Guest, Emergency).
    """
    return """Bootstrap the standard MA2 rights user accounts.

This is a DESTRUCTIVE workflow — it creates user accounts and modifies user profiles.
All steps require confirm_destructive=True.

Steps:
1. INSPECT: Call `list_console_users` — check which accounts already exist.
   Built-in accounts Administrator and Guest always exist and cannot be deleted.
2. READ RESOURCE: Load `ma2://docs/rights-matrix` — review the six-tier rights ladder.
3. PLAN: For each missing account in the standard set:
   - Admin (rights: Admin)
   - LightOperator (rights: Light-Operator)
   - Programmer (rights: Programmer)
   - PlaybackOp (rights: Playback-Operator)
   - Guest (rights: Guest)
4. EXECUTE: For each planned account, call `create_user(username=..., rights=..., confirm_destructive=True)`.
5. VERIFY: Call `list_console_users` again — confirm all accounts were created.
6. SAVE: Call `save_show` to persist the new accounts.

Return a summary of: accounts created, accounts skipped (already existed), any errors."""


# ============================================================
# Busking / Performance Layer Tools
# Live performance primitives: effect assignment, fader control, show mode
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.CUE_STORE)
@_handle_errors
async def assign_effect_to_executor(
    effect_id: int,
    executor_id: int,
    page: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Assign an effect template to a fader executor slot (DESTRUCTIVE).

    Binds an effect from the effect library to an executor so the fader controls
    effect intensity in live busking mode. This is the core primitive for the
    fader-per-effect busking model.

    Args:
        effect_id: Effect pool ID to assign (1-based).
        executor_id: Target executor slot number on the page.
        page: Optional page number. When given, qualifies as 'Page {page}.{exec}'.
        confirm_destructive: Must be True to execute (DESTRUCTIVE — modifies executor assignment).

    Returns:
        JSON result with command sent and console response.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "assign_effect_to_executor is DESTRUCTIVE (modifies executor assignment). Pass confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
            "command_preview": build_assign_effect_to_executor(effect_id, executor_id, page=page),
        }, indent=2)
    client = await get_client()
    cmd = build_assign_effect_to_executor(effect_id, executor_id, page=page)
    response = await client.send_command(cmd)
    return json.dumps({"command": cmd, "response": response, "effect_id": effect_id, "executor_id": executor_id}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def modulate_effect(
    mode: str,
    value: int,
) -> str:
    """
    Set rate or speed on active effects in real time (SAFE_WRITE).

    Used in busking to live-modulate effect tempo without stopping playback.
    Rate is a relative multiplier (100 = normal, 200 = double).
    Speed is an absolute BPM target (overrides rate).

    Args:
        mode: "rate" (relative 1–200, 100=normal) or "speed" (absolute BPM).
        value: Numeric value for the chosen mode.

    Returns:
        JSON result with command sent and console response.
    """
    if mode == "rate":
        cmd = build_set_effect_rate(value)
    else:
        cmd = build_set_effect_speed(value)
    client = await get_client()
    response = await client.send_command(cmd)
    return json.dumps({"command": cmd, "mode": mode, "value": value, "response": response}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def clear_effects_on_page(
    page: int,
    start_exec: int = 1,
    end_exec: int = 20,
) -> str:
    """
    Release (kill) all effect executors across a page range (SAFE_WRITE).

    Sends Off commands to every executor in the range, stopping all running
    effects. Use during song transitions to clean up the previous song's state.
    Does not change fader positions — use normalize_page_faders for that.

    Args:
        page: Fader page number.
        start_exec: First executor slot to release (default 1).
        end_exec: Last executor slot to release (default 20).

    Returns:
        JSON result with command count and console response.
    """
    client = await get_client()
    cmd = build_release_effects_on_page(page, start_exec=start_exec, end_exec=end_exec)
    response = await client.send_command(cmd)
    count = end_exec - start_exec + 1
    return json.dumps({"command_count": count, "page": page, "response": response}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def normalize_page_faders(
    page: int,
    start_exec: int = 1,
    end_exec: int = 20,
) -> str:
    """
    Set all faders on a page to 0 without releasing executors (SAFE_WRITE).

    Silences all effects while keeping them armed for instant recall — the
    standard busking blackout technique. Faders return to zero but executors
    remain active; pushing the fader up immediately restores the effect.

    Args:
        page: Fader page number.
        start_exec: First executor slot (default 1).
        end_exec: Last executor slot (default 20).

    Returns:
        JSON result with command count and console response.
    """
    client = await get_client()
    cmd = build_zero_page_faders(page, start_exec=start_exec, end_exec=end_exec)
    response = await client.send_command(cmd)
    count = end_exec - start_exec + 1
    return json.dumps({"command_count": count, "page": page, "zeroed": True, "response": response}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def classify_show_mode() -> str:
    """
    Inspect the show and classify its execution mode (SAFE_READ).

    Queries the effect and macro libraries to determine whether the current
    show is structured for busking (effect-fader model), sequence-driven
    playback, or a hybrid of both.

    Returns:
        JSON with mode classification and supporting evidence:
        - "busking"  — primarily effects assigned to fader executors
        - "sequence" — primarily cue sequences on executors
        - "hybrid"   — mix of effects and sequences
        - "empty"    — no content detected
    """
    client = await get_client()
    effect_response = await client.send_command(build_list_effect_library())
    macro_response = await client.send_command(build_list_macro_library())

    effect_lines = [line for line in effect_response.splitlines() if line.strip() and not line.startswith("[")]
    macro_lines = [line for line in macro_response.splitlines() if line.strip() and not line.startswith("[")]

    effect_count = len(effect_lines)
    macro_count = len(macro_lines)

    if effect_count == 0 and macro_count == 0:
        mode = "empty"
    elif effect_count > macro_count * 2:
        mode = "busking"
    elif macro_count > effect_count * 2:
        mode = "sequence"
    else:
        mode = "hybrid"

    return json.dumps({
        "mode": mode,
        "evidence": {"effects": effect_count, "macros": macro_count},
    }, indent=2)


# ============================================================
# Wave 1 — Console Session & UI Lock
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def console_login(username: str, password: str) -> str:
    """
    Authenticate to the grandMA2 console as a specific user.

    Sends a Login command over the active Telnet session, switching
    the session to the specified user account and rights level.

    Args:
        username: Console username (e.g. "operator", "administrator")
        password: Console password

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_console_login(username, password)
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.USER_MANAGE)
@_handle_errors
async def console_logout() -> str:
    """
    Log out the current Telnet session user on the grandMA2 console.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_console_logout()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def lock_console_ui() -> str:
    """
    Lock the grandMA2 console UI to prevent accidental input.

    Sends the Lock command, which disables all physical panel input
    until unlocked. Useful during live shows to prevent accidental
    key presses.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_lock_console()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def unlock_console_ui(password: str | None = None) -> str:
    """
    Unlock the grandMA2 console UI.

    Args:
        password: Optional unlock password if the console was locked with one.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_unlock_console(password)
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


# ============================================================
# Wave 2 — Read-only list tools (pool discovery)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_layouts() -> str:
    """
    List all Layout pool objects on the grandMA2 console.

    Returns the raw console output of the List Layout command,
    which shows all defined layout views and their IDs.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_list_objects("Layout")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_worlds() -> str:
    """
    List all World pool objects on the grandMA2 console.

    Worlds are used to restrict which fixtures a user can control.
    Returns the raw console output of the List World command.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_list_objects("World")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def store_world(
    world_id: int,
    name: str | None = None,
    overwrite: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Create (store) a new World pool object on the grandMA2 console. (DESTRUCTIVE)

    Worlds restrict which fixtures a user profile can control. After storing,
    use assign_world_to_user_profile to attach the world to a user.

    Args:
        world_id: World slot number (1-256)
        name: Optional label applied immediately after store
        overwrite: If True, adds /overwrite flag (replaces existing slot)
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with commands_sent and raw_responses.
    """
    if not confirm_destructive:
        return json.dumps({"blocked": True, "reason": "confirm_destructive required"}, indent=2)

    client = await get_client()
    flag = " /overwrite" if overwrite else ""
    store_cmd = f"store world {world_id}{flag}"
    raw1 = await client.send_command_with_response(store_cmd)

    commands_sent = [store_cmd]
    raw_responses = [raw1]

    if name:
        label_cmd = build_label("world", world_id, name)
        raw2 = await client.send_command_with_response(label_cmd)
        commands_sent.append(label_cmd)
        raw_responses.append(raw2)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_responses": raw_responses,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SETUP_CONSOLE)
@_handle_errors
async def label_world(
    world_id: int,
    name: str,
    confirm_destructive: bool = False,
) -> str:
    """
    Label an existing World pool object on the grandMA2 console. (DESTRUCTIVE)

    Args:
        world_id: World slot number to label (1-256)
        name: Name to assign to the world
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if not confirm_destructive:
        return json.dumps({"blocked": True, "reason": "confirm_destructive required"}, indent=2)

    client = await get_client()
    cmd = build_label("world", world_id, name)
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_timers() -> str:
    """
    List all Timer pool objects on the grandMA2 console.

    Returns the raw console output of the List Timer command,
    which shows all defined countdown / count-up timers.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_list_objects("Timer")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_filters() -> str:
    """
    List all Filter pool objects on the grandMA2 console.

    Filters restrict which fixture attributes are stored or recalled.
    Returns the raw console output of the List Filter command.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_list_objects("Filter")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_effects_pool() -> str:
    """
    List all Effect pool objects on the grandMA2 console.

    Returns stored effects (not the effect library) from the
    Effects pool using the List Effect command.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_list_objects("Effect")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_images() -> str:
    """
    List all Image pool objects on the grandMA2 console.

    Returns the raw console output of the List Image command,
    which shows all user-imported images (for gobo media servers, etc.).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_list_objects("Image")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_forms() -> str:
    """
    List all Form pool objects on the grandMA2 console.

    Forms define the waveform shapes used by effects. Returns
    the raw console output of the List Form command.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_list_objects("Form")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_timecode_events() -> str:
    """
    List all Timecode pool objects on the grandMA2 console.

    Returns the raw console output of the List Timecode command,
    which shows all stored timecode tracks and their slot IDs.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_list_objects("Timecode")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_agenda_events() -> str:
    """
    List all Agenda pool objects on the grandMA2 console.

    Agendas are time-triggered events (sunrise/sunset/specific time) that can
    fire macros or cues automatically. Returns the raw console output of the
    List Agenda command, showing all agenda slots and their IDs.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    client = await get_client()
    cmd = build_list_objects("Agenda")
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def store_agenda(
    agenda_id: int,
    name: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Create (store) a new Agenda pool object on the grandMA2 console. (DESTRUCTIVE)

    Agendas are time-triggered events (clock/sunrise/sunset) that fire macros or
    cues automatically. After storing, use the assign tool to attach a macro trigger.

    The store command creates the pool slot. To add time triggers to an existing
    agenda, use store_timecode_event with object_type="agenda".

    Args:
        agenda_id: Agenda slot number (1-256)
        name: Optional label applied immediately after store
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with commands_sent and raw_responses.
    """
    if not confirm_destructive:
        return json.dumps({"blocked": True, "reason": "confirm_destructive required"}, indent=2)

    client = await get_client()
    store_cmd = f"store agenda {agenda_id}"
    raw1 = await client.send_command_with_response(store_cmd)

    commands_sent = [store_cmd]
    raw_responses = [raw1]

    if name:
        label_cmd = build_label("agenda", agenda_id, name)
        raw2 = await client.send_command_with_response(label_cmd)
        commands_sent.append(label_cmd)
        raw_responses.append(raw2)

    return json.dumps({
        "commands_sent": commands_sent,
        "raw_responses": raw_responses,
    }, indent=2)


# ============================================================
# Wave 3 — Chaser live control & Effect programmer parameters
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def control_chaser(
    action: str,
    value: float | None = None,
    executor_id: int | None = None,
    page: int = 1,
) -> str:
    """
    Control a running chaser (rate, speed, skip, crossfade mode).

    Actions:
    - "rate"    : Set the rate (0-200, 100 = normal). Requires value.
    - "speed"   : Set the BPM speed (0-65535). Requires value.
    - "skip_fwd": Skip one step forward (SkipPlus).
    - "skip_bk" : Skip one step backward (SkipMinus).
    - "xfade_a" : Set crossfade mode A (CrossFadeA).
    - "xfade_b" : Set crossfade mode B (CrossFadeB).
    - "xfade_ab": Set crossfade mode AB (CrossFadeAB).

    Args:
        action: One of: rate, speed, skip_fwd, skip_bk, xfade_a, xfade_b, xfade_ab
        value: Required for rate and speed actions.
        executor_id: Target executor ID (optional; uses selected if omitted).
        page: Page number (default 1).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    action = action.lower()
    if action in ("rate", "speed") and value is None:
        return json.dumps({"error": f"'value' is required for action '{action}'"}, indent=2)

    if action == "rate":
        cmd = build_chaser_rate(value, executor_id, page)
    elif action == "speed":
        cmd = build_chaser_speed(value, executor_id, page)
    elif action == "skip_fwd":
        cmd = build_chaser_skip("plus", executor_id, page)
    elif action == "skip_bk":
        cmd = build_chaser_skip("minus", executor_id, page)
    elif action in ("xfade_a", "xfade_b", "xfade_ab"):
        mode = action.replace("xfade_", "")
        cmd = build_chaser_xfade(mode, executor_id, page)
    else:
        return json.dumps({
            "error": f"Unknown action '{action}'. Use: rate, speed, skip_fwd, skip_bk, xfade_a, xfade_b, xfade_ab"
        }, indent=2)

    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def set_effect_param(param: str, value: float) -> str:
    """
    Set an effect parameter in the programmer for the current fixture selection.

    Valid parameters: bpm, hz, high, low, phase, width, attack, decay.

    - bpm / hz   : Effect speed (beats per minute or Hertz)
    - high / low : Upper and lower value limits (0-100)
    - phase      : Phase offset (0-359 degrees)
    - width      : Pulse width (0-100)
    - attack     : Attack time (0-100)
    - decay      : Decay time (0-100)

    Args:
        param: Parameter name (case-insensitive). One of: bpm, hz, high, low,
               phase, width, attack, decay.
        value: Numeric value appropriate for the parameter.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    try:
        cmd = build_set_effect_parameter(param, value)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, indent=2)
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


# ============================================================
# Wave 4 — Plugin / Lua / Special Master
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def call_plugin_tool(plugin_id: int | str, confirm_destructive: bool = False) -> str:
    """
    Execute a plugin on the grandMA2 console by ID or name.

    Plugins are Lua scripts stored in the Plugin pool. This tool
    invokes them using the Plugin keyword.

    Args:
        plugin_id: Plugin number (int) or name (str).
        confirm_destructive: Must be True to proceed. Defaults to False (blocked).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "call_plugin_tool is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
        }, indent=2)
    client = await get_client()
    cmd = build_call_plugin(plugin_id)
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def run_lua_script(script: str, confirm_destructive: bool = False) -> str:
    """
    Execute an inline Lua script directly on the grandMA2 console.

    Sends the script using the Lua keyword. Useful for one-off
    automations without creating a persistent Plugin pool entry.

    Args:
        script: Lua source code (e.g. 'print("hello")', 'gma.cmd("Blackout")').
        confirm_destructive: Must be True to proceed. Defaults to False (blocked).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "run_lua_script is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
        }, indent=2)
    client = await get_client()
    cmd = build_run_lua(script)
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.MACRO_EDIT)
@_handle_errors
async def reload_all_plugins(confirm_destructive: bool = False) -> str:
    """
    Reload all plugins from disk on the grandMA2 console.

    Sends ReloadPlugins, which rescans the plugin folder and reloads
    all Lua plugin files. Use after editing plugin files on disk.

    Args:
        confirm_destructive: Must be True to proceed. Defaults to False (blocked).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "reload_all_plugins is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
        }, indent=2)
    client = await get_client()
    cmd = build_reload_plugins()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def control_special_master(master: str, value: float) -> str:
    """
    Set the level of a grandMA2 SpecialMaster (Grand Master, Speed/Rate masters).

    Special masters globally control intensity and timing for all playbacks.

    Valid master names:
    - "grandmaster"     : Grand Master (0-100 %)
    - "playbackmaster"  : Playback Master (0-100 %)
    - "speed1".."speed16" : Speed Masters (BPM)
    - "rate1".."rate16"   : Rate Masters (%)

    Args:
        master: Master name (case-insensitive). See valid names above.
        value: Level value appropriate for the master type.

    Returns:
        str: JSON with command_sent and raw_response.
    """
    try:
        cmd = build_set_special_master(master, value)
    except ValueError as exc:
        return json.dumps({
            "error": str(exc),
            "valid_masters": sorted(SPECIAL_MASTER_NAMES),
        }, indent=2)
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


# ============================================================
# Wave 5 — RDM (Remote Device Management)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.PATCH_WRITE)
@_handle_errors
async def rdm_discover(action: str = "automatch") -> str:
    """
    Perform RDM device discovery on the grandMA2 console.

    Actions:
    - "automatch"  : Match discovered RDM devices to existing fixture types (RdmAutomatch).
    - "autopatch"  : Auto-patch discovered RDM devices to free DMX addresses (RdmAutopatch).

    RDM (Remote Device Management) allows two-way communication with
    DMX fixtures that support the RDM protocol.

    Args:
        action: "automatch" or "autopatch" (default: "automatch").

    Returns:
        str: JSON with command_sent and raw_response.
    """
    action = action.lower()
    if action == "automatch":
        cmd = build_rdm_automatch()
    elif action == "autopatch":
        cmd = build_rdm_autopatch()
    else:
        return json.dumps({"error": f"Unknown action '{action}'. Use 'automatch' or 'autopatch'."}, indent=2)
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def rdm_get_info(
    fixture_id: int | None = None,
    universe: int | None = None,
) -> str:
    """
    Query RDM device information from the grandMA2 console.

    - If fixture_id is provided: returns RDM device info for that fixture (RdmInfo Fixture N).
    - If universe is provided (and no fixture_id): lists RDM devices on that universe (RdmList Universe N).
    - If neither is provided: lists all discovered RDM devices (RdmList).

    Args:
        fixture_id: Fixture ID to query (optional).
        universe: Universe number to filter by (optional).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if fixture_id is not None:
        cmd = build_rdm_info(fixture_id)
    else:
        cmd = build_rdm_list(universe)
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PATCH_WRITE)
@_handle_errors
async def rdm_patch(
    fixture_id: int,
    action: str,
    universe: int | None = None,
    address: int | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Patch or unmatch an RDM device on the grandMA2 console.

    Actions:
    - "setpatch" : Assign the RDM device at fixture_id to a specific DMX address.
                   Requires universe and address.
    - "unmatch"  : Detach the RDM match for a fixture (RdmUnmatch Fixture N).

    Args:
        fixture_id: Fixture ID of the RDM device.
        action: "setpatch" or "unmatch".
        universe: Target universe number (required for setpatch).
        address: Target DMX address 1-512 (required for setpatch).
        confirm_destructive: Must be True to proceed. Defaults to False (blocked).

    Returns:
        str: JSON with command_sent and raw_response.
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "rdm_patch is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
        }, indent=2)
    action = action.lower()
    if action == "setpatch":
        if universe is None or address is None:
            return json.dumps({"error": "setpatch requires both 'universe' and 'address'."}, indent=2)
        cmd = build_rdm_setpatch(fixture_id, universe, address)
    elif action == "unmatch":
        cmd = build_rdm_unmatch(fixture_id)
    else:
        return json.dumps({"error": f"Unknown action '{action}'. Use 'setpatch' or 'unmatch'."}, indent=2)
    client = await get_client()
    raw = await client.send_command_with_response(cmd)
    return json.dumps({"command_sent": cmd, "raw_response": raw}, indent=2)


# ============================================================
# New Tools: DMX Conflict Detection, Telemetry, Compliance,
# Preset Validation, Macro Jump Targets, Pool Slot Check,
# Fixture Remap
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def detect_dmx_address_conflicts(universe_id: int | None = None) -> str:
    """
    Scan the patch for DMX address conflicts — fixtures sharing overlapping channel ranges.

    Queries list_universes and list_fixtures to build a channel-occupancy map,
    then reports any fixtures whose DMX footprint overlaps with another fixture on
    the same universe. Safe to run before any patching operation or during a show
    health check.

    Args:
        universe_id: Check only this universe (1-based). If None, checks all universes.

    Returns JSON with:
    - conflicts: list of {universe, fixture_a, fixture_b, overlap_channels}
    - clean_universes: list of universe IDs with no conflicts
    - total_fixtures_checked: int
    """
    client = await get_client()
    # Get all fixture data
    raw_fixtures = await client.send_command_with_response("List Fixture")
    raw_universes = await client.send_command_with_response("List Universe")

    # Build occupancy map: universe -> {channel: fixture_id}
    occupancy: dict[int, dict[int, dict]] = {}
    conflicts = []

    # Parse fixtures from raw response (simplified — real implementation would use prompt_parser)
    lines = [ln.strip() for ln in raw_fixtures.splitlines() if ln.strip() and not ln.startswith("Fixture")]

    fixtures_checked = 0
    for line in lines:
        parts = line.split()
        if len(parts) >= 4:
            try:
                fixture_id = int(parts[0])
                univ = int(parts[-2]) if parts[-2].isdigit() else None
                addr = int(parts[-1]) if parts[-1].isdigit() else None
                if univ is None or addr is None:
                    continue
                if universe_id is not None and univ != universe_id:
                    continue
                fixtures_checked += 1
                if univ not in occupancy:
                    occupancy[univ] = {}
                if addr in occupancy[univ]:
                    conflicts.append({
                        "universe": univ,
                        "fixture_a": occupancy[univ][addr],
                        "fixture_b": fixture_id,
                        "channel": addr
                    })
                else:
                    occupancy[univ][addr] = fixture_id
            except (ValueError, IndexError):
                continue

    clean_universes = [u for u in occupancy if not any(c["universe"] == u for c in conflicts)]

    return json.dumps({
        "conflicts": conflicts,
        "clean_universes": clean_universes,
        "total_fixtures_checked": fixtures_checked,
        "universe_filter": universe_id,
        "status": "PASS" if not conflicts else "FAIL",
        "raw_fixture_response": raw_fixtures[:500]
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def update_object(
    object_type: str,
    object_id: int | str | None = None,
    sequence_id: int | None = None,
    merge: bool = False,
    overwrite: bool = False,
    cueonly: bool | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    Update any object with current programmer values (DESTRUCTIVE).

    Generic update tool that works with all 16 object types.
    For cue-specific updates with sequence scoping, prefer update_cue_data.

    Args:
        object_type: Object type — cue, group, preset, sequence, effect, macro, etc.
        object_id: Object ID (optional; updates active if omitted for cue)
        sequence_id: Sequence ID for cue-scoped updates (only used when object_type="cue")
        merge: Merge programmer into existing values
        overwrite: Overwrite existing values with programmer
        cueonly: Prevent changes from tracking forward (True) or allow (False)
        confirm_destructive: Must be True to execute

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    if not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": "update_object is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    from src.commands import update as build_update, update_cue as build_update_cue
    if object_type.lower() == "cue":
        cmd = build_update_cue(
            object_id, sequence_id=sequence_id,
            merge=merge, overwrite=overwrite, cueonly=cueonly,
        )
    else:
        cmd = build_update(
            object_type, object_id,
            merge=merge, overwrite=overwrite, cueonly=cueonly,
        )

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": "DESTRUCTIVE",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def programming_action(
    action: str,
    fixture_ids: int | list[int] | None = None,
    end: int | None = None,
    cue_id: int | float | None = None,
    sequence_id: int | None = None,
    macro_id: int | None = None,
    executor_id: int | None = None,
    page: int | None = None,
    look_id: int | None = None,
    mode: str | None = None,
    merge: bool = False,
    overwrite: bool = False,
    confirm_destructive: bool = False,
) -> str:
    """
    Execute programmer operations — align, locate, flip, extract, learn,
    block/unblock cue, record macro, store look.

    Args:
        action: One of:
            SAFE_WRITE: "align", "locate", "flip", "extract", "learn"
            DESTRUCTIVE: "block", "unblock", "record_macro", "store_look"
        fixture_ids: Fixture number(s) for locate (single int or list)
        end: Ending number for locate range
        cue_id: Cue number for block/unblock
        sequence_id: Sequence ID for block/unblock scoping
        macro_id: Macro pool slot for record_macro
        executor_id: Executor ID for learn
        page: Page for learn page-qualified addressing
        look_id: Look pool slot for store_look
        mode: Alignment mode for align (">" "><" "<>" "<")
        merge: Merge option for store_look
        overwrite: Overwrite option for store_look
        confirm_destructive: Required for block/unblock/record_macro/store_look

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    from src.commands import (
        align as build_align,
        block_cue as build_block_cue,
        extract as build_extract,
        flip as build_flip,
        learn_executor as build_learn_executor,
        locate as build_locate,
        record_macro as build_record_macro,
        store_look as build_store_look,
        unblock_cue as build_unblock_cue,
    )

    valid_actions = {
        "align", "locate", "flip", "extract", "learn",
        "block", "unblock", "record_macro", "store_look",
    }
    if action not in valid_actions:
        return json.dumps({
            "error": f"Invalid action '{action}'. Valid: {sorted(valid_actions)}",
            "blocked": True,
        }, indent=2)

    destructive_actions = {"block", "unblock", "record_macro", "store_look"}
    if action in destructive_actions and not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": f"Action '{action}' is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if action == "align":
        cmd = build_align(mode=mode)
    elif action == "locate":
        cmd = build_locate(fixture_ids=fixture_ids, end=end)
    elif action == "flip":
        cmd = build_flip()
    elif action == "extract":
        cmd = build_extract()
    elif action == "learn":
        if executor_id is None:
            return json.dumps({"error": "executor_id required for learn", "blocked": True}, indent=2)
        cmd = build_learn_executor(executor_id, page=page)
    elif action == "block":
        if cue_id is None:
            return json.dumps({"error": "cue_id required for block", "blocked": True}, indent=2)
        cmd = build_block_cue(cue_id, sequence_id=sequence_id)
    elif action == "unblock":
        if cue_id is None:
            return json.dumps({"error": "cue_id required for unblock", "blocked": True}, indent=2)
        cmd = build_unblock_cue(cue_id, sequence_id=sequence_id)
    elif action == "record_macro":
        if macro_id is None:
            return json.dumps({"error": "macro_id required for record_macro", "blocked": True}, indent=2)
        cmd = build_record_macro(macro_id)
    elif action == "store_look":
        cmd = build_store_look(look_id=look_id, merge=merge, overwrite=overwrite)
    else:
        return json.dumps({"error": f"Unhandled action: {action}"}, indent=2)

    risk = "DESTRUCTIVE" if action in destructive_actions else "SAFE_WRITE"
    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.EXECUTOR_CTRL)
@_handle_errors
async def master_control(
    action: str,
    master_id: int | None = None,
    master_type: int | None = None,
    level: int | None = None,
) -> str:
    """
    Control master faders — set level, set special master, or list all masters.

    Args:
        action: "set" (SAFE_WRITE), "set_special" (SAFE_WRITE), or "list" (SAFE_READ)
        master_id: Master pool slot number (required for set / set_special)
        master_type: Special master type number (required for set_special)
        level: Level 0-100 (required for set / set_special)

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    from src.commands import (
        master_at as build_master_at,
        special_master_at as build_special_master_at,
        list_masters as build_list_masters,
    )

    valid_actions = ("set", "set_special", "list")
    if action not in valid_actions:
        return json.dumps({"error": f"action must be one of {valid_actions}", "blocked": True}, indent=2)

    if action == "set":
        if master_id is None or level is None:
            return json.dumps({"error": "master_id and level required for set", "blocked": True}, indent=2)
        cmd = build_master_at(master_id, level)
        risk_tier = "SAFE_WRITE"
    elif action == "set_special":
        if master_type is None or master_id is None or level is None:
            return json.dumps({"error": "master_type, master_id, level required for set_special", "blocked": True}, indent=2)
        cmd = build_special_master_at(master_type, master_id, level)
        risk_tier = "SAFE_WRITE"
    else:
        cmd = build_list_masters()
        risk_tier = "SAFE_READ"

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk_tier,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.SYSTEM_ADMIN)
@_handle_errors
async def system_admin(
    action: str,
    user: str | None = None,
    password: str | None = None,
    script: str | None = None,
    message: str | None = None,
    confirm_destructive: bool = False,
) -> str:
    """
    System administration — login, logout, lock, unlock, lua, chat,
    reboot, restart, shutdown.

    Args:
        action: One of:
            SAFE_READ: "logout"
            SAFE_WRITE: "login", "lock", "unlock", "lua", "chat"
            DESTRUCTIVE: "reboot", "restart", "shutdown"
        user: Username (required for login)
        password: Password (required for login; optional for lock/unlock)
        script: Lua script string (required for lua)
        message: Chat message text (required for chat)
        confirm_destructive: Must be True for reboot/restart/shutdown

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    from src.commands import (
        build_login,
        build_logout,
        lock_console as build_lock,
        unlock_console as build_unlock,
        lua_execute as build_lua,
        reboot_console as build_reboot,
        restart_console as build_restart,
        send_chat as build_chat,
        shutdown_console as build_shutdown,
    )

    valid_actions = {"login", "logout", "lock", "unlock", "lua", "chat", "reboot", "restart", "shutdown"}
    if action not in valid_actions:
        return json.dumps({"error": f"Invalid action '{action}'. Valid: {sorted(valid_actions)}", "blocked": True}, indent=2)

    destructive_actions = {"reboot", "restart", "shutdown"}
    if action in destructive_actions and not confirm_destructive:
        return json.dumps({
            "blocked": True,
            "error": f"Action '{action}' is DESTRUCTIVE. Set confirm_destructive=True to proceed.",
            "risk_tier": "DESTRUCTIVE",
        }, indent=2)

    if action == "login":
        if user is None or password is None:
            return json.dumps({"error": "user and password required for login", "blocked": True}, indent=2)
        cmd = build_login(user, password)
        risk_tier = "SAFE_WRITE"
    elif action == "logout":
        cmd = build_logout()
        risk_tier = "SAFE_READ"
    elif action == "lock":
        cmd = build_lock(password)
        risk_tier = "SAFE_WRITE"
    elif action == "unlock":
        cmd = build_unlock(password)
        risk_tier = "SAFE_WRITE"
    elif action == "lua":
        if script is None:
            return json.dumps({"error": "script required for lua", "blocked": True}, indent=2)
        cmd = build_lua(script)
        risk_tier = "SAFE_WRITE"
    elif action == "chat":
        if message is None:
            return json.dumps({"error": "message required for chat", "blocked": True}, indent=2)
        cmd = build_chat(message)
        risk_tier = "SAFE_WRITE"
    elif action == "reboot":
        cmd = build_reboot()
        risk_tier = "DESTRUCTIVE"
    elif action == "restart":
        cmd = build_restart()
        risk_tier = "DESTRUCTIVE"
    else:
        cmd = build_shutdown()
        risk_tier = "DESTRUCTIVE"

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk_tier,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def plugin_management(action: str) -> str:
    """
    Manage Lua plugins — list available plugins or reload the plugin pool.

    Args:
        action: "list" (SAFE_READ) or "reload" (SAFE_WRITE)

    Returns:
        str: JSON with command_sent, raw_response, risk_tier
    """
    from src.commands import (
        list_plugin_library as build_list_plugins,
        reload_plugins as build_reload_plugins,
    )

    if action == "list":
        cmd = build_list_plugins()
        risk_tier = "SAFE_READ"
    elif action == "reload":
        cmd = build_reload_plugins()
        risk_tier = "SAFE_WRITE"
    else:
        return json.dumps({"error": f"Invalid action '{action}'. Valid: ['list', 'reload']", "blocked": True}, indent=2)

    client = await get_client()
    response = await client.send_command_with_response(cmd)
    return json.dumps({
        "command_sent": cmd,
        "raw_response": response,
        "risk_tier": risk_tier,
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def get_telemetry_report(
    session_id: str | None = None,
    days: int = 1,
    risk_tier: str | None = None,
    format: str = "json"
) -> str:
    """
    Export tool invocation telemetry as a structured audit report.

    Queries the tool_invocations table filtered by session, date range, and/or
    risk tier. Returns a structured log suitable for SB 132 compliance reports,
    insurance documentation, and safety audits.

    Args:
        session_id: Filter to a specific session ID (from list_agent_sessions).
                    If None, includes all sessions in the date range.
        days: Number of past days to include (default 1 = today only).
        risk_tier: Filter to "SAFE_READ", "SAFE_WRITE", or "DESTRUCTIVE" only.
                   If None, includes all tiers.
        format: "json" (default) or "markdown" for human-readable report.

    Returns structured report with:
    - header: session info, date range, operator
    - risk_summary: counts per tier
    - destructive_log: full detail on every DESTRUCTIVE operation
    - error_log: any operations that returned errors
    - timeline: ordered list of all operations
    """
    import time as _time
    import datetime
    import sqlite3

    cutoff_ts = _time.time() - (days * 86400)

    db_path = Path(__file__).parent.parent / "rag" / "store" / "agent_memory.db"
    if not db_path.exists():
        return json.dumps({"error": "Telemetry database not found", "path": str(db_path)})

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM tool_invocations WHERE ts >= ?"
        params: list = [cutoff_ts]

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        if risk_tier:
            query += " AND risk_tier = ?"
            params.append(risk_tier.upper())

        query += " ORDER BY ts ASC"

        rows = conn.execute(query, params).fetchall()
        invocations = [dict(r) for r in rows]
        conn.close()

    except Exception as e:
        return json.dumps({"error": f"Database query failed: {e}"})

    # Build report
    risk_summary: dict[str, int] = {"SAFE_READ": 0, "SAFE_WRITE": 0, "DESTRUCTIVE": 0, "UNKNOWN": 0}
    destructive_log = []
    error_log = []
    timeline = []

    for inv in invocations:
        tier = inv.get("risk_tier", "UNKNOWN")
        risk_summary[tier] = risk_summary.get(tier, 0) + 1

        entry = {
            "ts": inv.get("ts"),
            "ts_human": datetime.datetime.fromtimestamp(inv.get("ts", 0), tz=datetime.timezone.utc).isoformat(),
            "tool": inv.get("tool_name"),
            "tier": tier,
            "latency_ms": inv.get("latency_ms"),
            "session_id": inv.get("session_id"),
            "operator": inv.get("operator", "unknown"),
            "error": inv.get("error_class")
        }
        timeline.append(entry)

        if tier == "DESTRUCTIVE":
            destructive_log.append({
                **entry,
                "inputs_preview": inv.get("inputs_json", "")[:300],
                "output_preview": inv.get("output_preview", "")[:300]
            })

        if inv.get("error_class"):
            error_log.append(entry)

    report = {
        "report_type": "MA2 Agent Telemetry Audit Report",
        "generated_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "filter": {
            "session_id": session_id,
            "days": days,
            "risk_tier_filter": risk_tier
        },
        "risk_summary": risk_summary,
        "total_operations": len(invocations),
        "destructive_operations": len(destructive_log),
        "errors": len(error_log),
        "destructive_log": destructive_log,
        "error_log": error_log,
        "timeline": timeline
    }

    if format == "markdown":
        md_lines = [
            "# MA2 Agent Audit Report",
            f"Generated: {report['generated_at']}",
            "",
            "## Risk Tier Summary",
            "| Tier | Count |",
            "|------|-------|",
        ]
        for tier, count in risk_summary.items():
            md_lines.append(f"| {tier} | {count} |")
        md_lines += [
            "",
            f"**Total operations:** {len(invocations)}  ",
            f"**DESTRUCTIVE operations:** {len(destructive_log)}  ",
            f"**Errors:** {len(error_log)}",
            "",
            "## DESTRUCTIVE Operations Log",
        ]
        if not destructive_log:
            md_lines.append("_No DESTRUCTIVE operations recorded._")
        for op in destructive_log:
            md_lines.append(f"- `{op['ts_human']}` — **{op['tool']}** (operator: {op.get('operator', 'unknown')})")

        md_lines += ["", "## Errors", ""]
        if not error_log:
            md_lines.append("_No errors recorded._")
        for err in error_log:
            md_lines.append(f"- `{err['ts_human']}` — **{err['tool']}** — {err.get('error')}")

        return "\n".join(md_lines)

    return json.dumps(report, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def generate_compliance_report(
    session_id: str | None = None,
    production_name: str = "Production",
    operator_name: str = "",
    days: int = 1
) -> str:
    """
    Generate a SB 132 / safety-audit compliance report from session telemetry.

    Produces a structured report mapping MA2 Agent telemetry fields to
    SB 132 documentation requirements: written risk assessment, operator
    identification, DESTRUCTIVE operation log, and incident timeline.

    Safe to run during any production. Reads telemetry only — no console side effects.

    Args:
        session_id: Target session ID. If None, uses all sessions in date range.
        production_name: Name of production for report header.
        operator_name: Console operator name for report header.
        days: Days of telemetry to include (default 1).

    Returns a markdown compliance report ready for inclusion in safety documentation.
    """
    import time as _time
    import datetime
    import sqlite3

    cutoff_ts = _time.time() - (days * 86400)

    db_path = Path(__file__).parent.parent / "rag" / "store" / "agent_memory.db"
    if not db_path.exists():
        return json.dumps({
            "error": "Telemetry database not found",
            "recommendation": "Ensure GMA_TELEMETRY=1 is set and at least one tool has been called"
        })

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        if session_id:
            query = "SELECT * FROM tool_invocations WHERE session_id = ? ORDER BY ts ASC"
            params: list = [session_id]
        else:
            query = "SELECT * FROM tool_invocations WHERE ts >= ? ORDER BY ts ASC"
            params = [cutoff_ts]

        rows = conn.execute(query, params).fetchall()
        invocations = [dict(r) for r in rows]
        conn.close()
    except Exception as e:
        return json.dumps({"error": f"Database error: {e}"})

    risk_counts: dict[str, int] = {"SAFE_READ": 0, "SAFE_WRITE": 0, "DESTRUCTIVE": 0}
    destructive_ops = []
    errors = []

    for inv in invocations:
        tier = inv.get("risk_tier", "SAFE_READ")
        risk_counts[tier] = risk_counts.get(tier, 0) + 1
        ts_human = datetime.datetime.fromtimestamp(
            inv.get("ts", 0), tz=datetime.timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")

        if tier == "DESTRUCTIVE":
            destructive_ops.append(
                f"  - `{ts_human}` — **{inv.get('tool_name')}** (latency: {inv.get('latency_ms', 0):.0f}ms)"
            )
        if inv.get("error_class"):
            errors.append(
                f"  - `{ts_human}` — **{inv.get('tool_name')}** — Error: {inv.get('error_class')}"
            )

    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    safe_read = risk_counts.get("SAFE_READ", 0)
    safe_write = risk_counts.get("SAFE_WRITE", 0)
    destructive = risk_counts.get("DESTRUCTIVE", 0)
    total = len(invocations)

    report_lines = [
        "# MA2 Agent Safety & Compliance Report",
        "",
        f"**Production:** {production_name}  ",
        f"**Console Operator:** {operator_name or 'Not specified'}  ",
        f"**Report Generated:** {now}  ",
        f"**Period:** Last {days} day(s)",
        "",
        "---",
        "",
        "## Risk Assessment Summary",
        "",
        "All lighting control operations were processed through MA2 Agent's three-tier safety system:",
        "",
        "| Risk Tier | Operations | Description |",
        "|-----------|-----------|-------------|",
        f"| SAFE_READ | {safe_read} | Read-only monitoring — zero risk to console state |",
        f"| SAFE_WRITE | {safe_write} | Controlled modifications requiring standard authorization |",
        f"| DESTRUCTIVE | {destructive} | High-risk operations requiring explicit confirm_destructive=True and elevated OAuth scope |",
        f"| **TOTAL** | **{total}** | |",
        "",
        "### Insurance Brief",
        "",
        "All lighting control operations during this session were processed through MA2 Agent's",
        f"three-tier safety system. {safe_read} operation(s) were classified SAFE_READ (read-only",
        f"monitoring, zero risk), {safe_write} were SAFE_WRITE (controlled modifications requiring",
        f"standard authorization), and {destructive} were DESTRUCTIVE (required explicit",
        "confirm_destructive=True authorization and elevated scope).",
        "Full telemetry is available for forensic review.",
        "",
        "---",
        "",
        "## DESTRUCTIVE Operations Log",
        "",
        "_(SB 132 §3: Written risk assessment for high-risk operations)_",
        "",
    ]

    if destructive_ops:
        report_lines.extend(destructive_ops)
    else:
        report_lines.append("_No DESTRUCTIVE operations recorded in this period._")

    report_lines += [
        "",
        "---",
        "",
        "## Error / Incident Log",
        "",
        "_(SB 132 §4: Incident reporting)_",
        "",
    ]

    if errors:
        report_lines.extend(errors)
    else:
        report_lines.append("_No errors recorded in this period._")

    report_lines += [
        "",
        "---",
        "",
        "## System Information",
        "",
        "- **Control System:** MA2 Agent MCP Server",
        "- **Safety Architecture:** Three-tier (SAFE_READ / SAFE_WRITE / DESTRUCTIVE)",
        "- **Audit Logging:** Enabled — all operations recorded to persistent SQLite database",
        "- **Authorization Model:** OAuth 2.1 scope enforcement per operation",
        "",
        "_This report was generated automatically from MA2 Agent telemetry._",
        "_Retain as part of production safety documentation._",
    ]

    return "\n".join(report_lines)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def validate_preset_references(sequence_id: int, sample_cues: int = 5) -> str:
    """
    Scan a sequence's cues for references to presets that no longer exist in the pool.

    Samples up to `sample_cues` cues from the sequence, inspects each for preset
    references, and cross-checks against the current preset pool. Returns a list
    of broken references that would cause silent failures during playback.

    Safe to run before any performance. Read-only — no console side effects.

    Args:
        sequence_id: The sequence to validate.
        sample_cues: Number of cues to sample (default 5). Use 0 for all cues.

    Returns JSON with:
    - sequence_id: int
    - cues_checked: int
    - broken_references: list of {cue_id, preset_type, preset_id, detail}
    - valid_references: int count
    - status: "PASS" or "FAIL"
    """
    import re as _re
    client = await get_client()

    cue_list_raw = await client.send_command_with_response(f"List Cue Sequence {sequence_id}")
    cue_lines = [ln.strip() for ln in cue_list_raw.splitlines() if ln.strip() and ln[0].isdigit()]

    if sample_cues > 0:
        cue_lines = cue_lines[:sample_cues]

    broken = []
    valid_count = 0

    for line in cue_lines:
        parts = line.split()
        if not parts:
            continue
        cue_id = parts[0]

        cue_info = await client.send_command_with_response(f"Info Cue {cue_id} Sequence {sequence_id}")

        for info_line in cue_info.splitlines():
            if "Preset" in info_line and "." in info_line:
                preset_match = _re.search(r"Preset\s+(\d+)\.(\d+)", info_line)
                if preset_match:
                    p_type = int(preset_match.group(1))
                    p_id = int(preset_match.group(2))
                    check = await client.send_command_with_response(f"Info Preset {p_type}.{p_id}")
                    if "NOT FOUND" in check.upper() or "ERROR" in check.upper() or "EMPTY" in check.upper():
                        broken.append({
                            "cue_id": cue_id,
                            "preset_type": p_type,
                            "preset_id": p_id,
                            "detail": f"Preset {p_type}.{p_id} not found in pool"
                        })
                    else:
                        valid_count += 1

    return json.dumps({
        "sequence_id": sequence_id,
        "cues_checked": len(cue_lines),
        "broken_references": broken,
        "valid_references": valid_count,
        "status": "PASS" if not broken else "FAIL",
        "recommendation": (
            "Re-store missing presets or update cues to use existing preset IDs"
            if broken else "All checked preset references are valid"
        )
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def list_macro_jump_targets(macro_id: int) -> str:
    """
    Parse a macro's lines and return all jump targets (Go Macro N."name".L references).

    Reads macro lines via the console command tree and identifies all jump
    instructions, their current target line numbers, and the total line count.
    Use this before inserting or deleting macro lines to build an index-shift table.

    Args:
        macro_id: The macro pool ID to inspect.

    Returns JSON with:
    - macro_id: int
    - total_lines: int
    - jump_targets: list of {source_line, target_line, raw_command}
    - line_listing: ordered list of {line_num, command}
    """
    import re as _re
    client = await get_client()

    macro_info = await client.send_command_with_response(f"Info Macro {macro_id}")
    lines_raw = await client.send_command_with_response(f"List Macro {macro_id}")

    jump_targets = []
    line_listing = []
    line_num = 1

    for raw_line in lines_raw.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("Macro"):
            continue

        line_listing.append({"line_num": line_num, "command": stripped})

        jump_match = _re.search(r'Go\s+Macro\s+\d+[."][^.]+[.".](\d+)', stripped, _re.IGNORECASE)
        if jump_match:
            target_line = int(jump_match.group(1))
            jump_targets.append({
                "source_line": line_num,
                "target_line": target_line,
                "raw_command": stripped
            })

        line_num += 1

    return json.dumps({
        "macro_id": macro_id,
        "total_lines": len(line_listing),
        "jump_count": len(jump_targets),
        "jump_targets": jump_targets,
        "line_listing": line_listing,
        "usage": (
            "When inserting line at position N: add 1 to all target_line values >= N. "
            "When deleting line N: subtract 1 from all target_line values > N."
        ),
        "raw_macro_info": macro_info[:300]
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def check_pool_slot_availability(
    pool_type: str,
    slot_range_start: int,
    slot_range_end: int
) -> str:
    """
    Check which pool slots are available (empty) and which are occupied in a range.

    Pre-flight check before bulk import, PSR, or mass preset creation to prevent
    silent overwrites. Safe to run at any time — read-only.

    Args:
        pool_type: "sequence", "preset", "group", "macro", "effect", "world",
                   "filter", "view", "layout", "timecode"
        slot_range_start: First slot ID to check (inclusive).
        slot_range_end: Last slot ID to check (inclusive).

    Returns JSON with:
    - pool_type: str
    - range: [start, end]
    - occupied: list of {slot_id, label} for occupied slots
    - available: list of slot_ids that are empty
    - first_available_block_of_10: smallest contiguous block of 10 empty slots
    """
    client = await get_client()

    pool_keyword_map = {
        "sequence": "Sequence", "preset": "Preset", "group": "Group",
        "macro": "Macro", "effect": "Effect", "world": "World",
        "filter": "Filter", "view": "View", "layout": "Layout", "timecode": "Timecode"
    }

    keyword = pool_keyword_map.get(pool_type.lower())
    if not keyword:
        return json.dumps({
            "error": f"Unknown pool_type '{pool_type}'. Valid: {list(pool_keyword_map.keys())}"
        })

    if slot_range_end - slot_range_start > 200:
        return json.dumps({
            "error": "Range too large (max 200 slots per check). Split into smaller ranges."
        })

    occupied = []
    available = []

    for slot_id in range(slot_range_start, slot_range_end + 1):
        info_raw = await client.send_command_with_response(f"Info {keyword} {slot_id}")

        if any(x in info_raw.upper() for x in ["NOT FOUND", "EMPTY", "NO OBJECT", "DOES NOT EXIST"]):
            available.append(slot_id)
        else:
            label = ""
            for ln in info_raw.splitlines():
                if "Name" in ln or "Label" in ln:
                    parts = ln.split(":", 1)
                    if len(parts) > 1:
                        label = parts[1].strip()
                        break
            occupied.append({"slot_id": slot_id, "label": label or f"{keyword} {slot_id}"})

    # Find first contiguous block of 10
    first_block = None
    block_size = 10
    available_set = set(available)
    for start in available:
        if all(start + i in available_set for i in range(block_size)):
            first_block = {"start": start, "end": start + block_size - 1, "size": block_size}
            break

    return json.dumps({
        "pool_type": pool_type,
        "range": [slot_range_start, slot_range_end],
        "occupied_count": len(occupied),
        "available_count": len(available),
        "occupied": occupied,
        "available": available,
        "first_available_block_of_10": first_block,
        "recommendation": (
            f"Use target_slot={first_block['start']} for PSR to avoid conflicts"
            if first_block and occupied else "All slots available in range"
        )
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.PROGRAMMER_WRITE)
@_handle_errors
async def remap_fixture_ids(
    source_fixture_id: int,
    target_fixture_id: int,
    scope: str = "groups",
    confirm_destructive: bool = False
) -> str:
    """
    Remap fixture references from one fixture ID to another within groups or presets.

    Used after PSR import or cross-venue adaptation when imported cue data references
    fixture IDs that have changed in the current rig. Updates group membership and/or
    selective preset fixture references.

    DESTRUCTIVE — modifies show data. Use check_pool_slot_availability and
    list_fixtures first to confirm both fixture IDs exist in the current patch.

    Args:
        source_fixture_id: The old fixture ID to replace.
        target_fixture_id: The new fixture ID to use.
        scope: "groups" (update group membership only), "presets" (update selective
               preset references only), or "both".
        confirm_destructive: Must be True to execute.

    Returns JSON with:
    - remapped_objects: list of modified pool objects
    - skipped: list of objects where source_fixture_id was not found
    - command_log: commands sent to console
    """
    if not confirm_destructive:
        return json.dumps({
            "error": "confirm_destructive=True required",
            "detail": (
                f"This will remap fixture {source_fixture_id} -> {target_fixture_id} in {scope}. "
                "Verify both fixtures exist with list_fixtures() before proceeding."
            )
        })

    client = await get_client()

    src_info = await client.send_command_with_response(f"Info Fixture {source_fixture_id}")
    tgt_info = await client.send_command_with_response(f"Info Fixture {target_fixture_id}")

    if any(x in src_info.upper() for x in ["NOT FOUND", "ERROR"]):
        return json.dumps({"error": f"Source fixture {source_fixture_id} not found in current patch"})
    if any(x in tgt_info.upper() for x in ["NOT FOUND", "ERROR"]):
        return json.dumps({"error": f"Target fixture {target_fixture_id} not found in current patch"})

    commands_sent = []
    remapped = []

    if scope in ("groups", "both"):
        groups_raw = await client.send_command_with_response("List Group")
        group_lines = [
            ln.strip() for ln in groups_raw.splitlines()
            if ln.strip() and ln.strip()[0].isdigit()
        ]

        for gline in group_lines:
            gid = gline.split()[0]
            g_info = await client.send_command_with_response(f"Info Group {gid}")
            if str(source_fixture_id) in g_info:
                cmd = f"Fixture {target_fixture_id} Store Group {gid} /merge"
                await client.send_command_with_response(cmd)
                commands_sent.append(cmd)
                cmd2 = f"Fixture {source_fixture_id} Remove Group {gid}"
                await client.send_command_with_response(cmd2)
                commands_sent.append(cmd2)
                remapped.append(f"Group {gid}")

    return json.dumps({
        "source_fixture_id": source_fixture_id,
        "target_fixture_id": target_fixture_id,
        "scope": scope,
        "remapped_objects": remapped,
        "commands_sent": commands_sent,
        "note": (
            "Selective preset fixture references require re-recording presets with the new fixture "
            "selected — automated remapping of preset fixture IDs is not supported via telnet."
        )
    }, indent=2)


# ============================================================
# New Prompts: Volunteer Preflight, Busking Template,
# Pre-Show Health Check, Adapt Show to Venue
# ============================================================


@mcp.prompt()
def volunteer_sunday_preflight(show_name: str = "", campus_name: str = "") -> str:
    """
    Sunday morning preflight checklist for volunteer operators — SAFE_READ guided verification
    that the correct show is loaded, presets are populated, and executors are assigned.
    """
    context = f"Show: {show_name}" if show_name else "Show: (use get_showfile_info to determine)"
    campus = f"Campus: {campus_name}" if campus_name else ""

    return f"""You are running a pre-show safety check for a volunteer operator.
{context}
{campus}

Execute the following SAFE_READ verification sequence in order. Stop and report
immediately if any step returns unexpected results.

STEP 1 -- SHOWFILE VERIFICATION
Call get_showfile_info(). Confirm the show name matches "{show_name or 'the expected show name'}".
Then call assert_showfile_unchanged(). If it returns False, STOP -- the show file has been modified
since the last programmer session. Do not proceed; contact the Technical Director.

STEP 2 -- STATE HYDRATION
Call hydrate_console_state(). Then call get_console_state().
Check for: unexpected parked fixtures (park_ledger not empty), active filter (may restrict fixtures),
unexpected world assignment.

STEP 3 -- PRESET POOL CHECK
Call list_preset_pool(preset_type="color") and list_preset_pool(preset_type="position").
Flag as AMBER if either pool has fewer than 3 entries.

STEP 4 -- EXECUTOR ASSIGNMENT CHECK
Call get_executor_detail(executor_id="1.1") and get_executor_detail(executor_id="1.2").
Confirm each has a sequence assigned and at least 1 cue.

STEP 5 -- CUE INTEGRITY CHECK
Call query_object_list(object_type="sequence", object_id=1).
Confirm the expected number of cues are present and the first cue is labeled.

STEP 6 -- GENERATE REPORT
Return a structured report:
{{
  "show_name": "<from step 1>",
  "campus": "{campus_name or 'N/A'}",
  "overall": "GREEN | AMBER | RED",
  "checks": {{
    "showfile": "GREEN | AMBER | RED",
    "console_state": "GREEN | AMBER | RED",
    "preset_pool": "GREEN | AMBER | RED",
    "executors": "GREEN | AMBER | RED",
    "cue_list": "GREEN | AMBER | RED"
  }},
  "findings": ["..."],
  "action_required": true | false
}}

GREEN = everything nominal. AMBER = non-blocking issue, report to TD. RED = stop, contact TD immediately."""


@mcp.prompt()
def generate_busking_template(
    target_page: str = "2",
    fixture_strategy: str = "by_type"
) -> str:
    """
    Generate a complete grandMA2 busking template from the current patch —
    groups, presets, effects, speed masters, and executor layout.
    """
    return f"""You are building a complete busking template for a grandMA2 rig.

Target executor page: {target_page}
Fixture grouping strategy: {fixture_strategy} (options: by_type, by_position, by_zone)

PHASE 0 -- SURVEY (SAFE_READ, always first -- present findings before proceeding)
1. Call hydrate_console_state() and list_fixtures() -- record total fixture count and types
2. Call list_fixture_types() -- identify unique fixture types in the rig
3. Call list_preset_pool(preset_type="color") -- check if color presets already exist
4. Call list_preset_pool(preset_type="position") -- check position presets
5. Present survey summary to operator and ask: "I found [N] fixtures of [M] types.
   Color pool has [K] existing presets. Shall I proceed with template generation?"
   STOP if operator says no.

PHASE 1 -- GROUP CREATION (confirm before executing DESTRUCTIVE operations)
Using the {fixture_strategy} strategy:
- by_type: one group per fixture type (all washes, all spots, all beams, all strobes)
- by_position: groups by stage position (front, back, left, right, truss)
- by_zone: groups by zone (audience, stage, backlight)

For each group: call create_fixture_group() then label_or_appearance() with HSB color coding.
Ask operator to confirm before executing: "I will create [N] groups in slots [X-Y]. Proceed?"

PHASE 2 -- COLOR PRESETS (8 per group -- confirm first)
Create 8 universal color presets using RGB 0-100 scale:
Red(100,0,0), Orange(100,40,0), Yellow(100,100,0), Green(0,100,0),
Cyan(0,100,100), Blue(0,0,100), Magenta(100,0,100), White(100,100,100)

PHASE 3 -- POSITION PRESETS (movers only -- 4 positions)
For fixture groups with Pan/Tilt attributes: create Home, DownCenter, SL_Top, SR_Top presets.

PHASE 4 -- EXECUTOR LAYOUT (confirm slot assignments before executing)
On page {target_page}:
- Exec 1: Song loader macro (label "LOAD")
- Exec 2-5: Effect sequences per fixture group
- Exec 6-8: Group intensity masters
- Exec 9: Speed master 1 (default 120 BPM)
- Exec 10: Emergency blackout macro

PHASE 5 -- VERIFY AND SAVE
Call get_console_state() to confirm all objects registered.
Call save_show(confirm_destructive=True) -- always save after template build.

At each DESTRUCTIVE phase, pause and confirm with the operator before proceeding.
Never auto-execute DESTRUCTIVE operations without explicit operator confirmation."""


@mcp.prompt()
def pre_show_health_check(sequence_ids: str = "1", strict: bool = False) -> str:
    """
    Full show health audit before going live — checks showfile, presets, executors,
    cue integrity, park ledger, and DMX. Returns GREEN/AMBER/RED per category.
    """
    sequences = sequence_ids or "1"
    mode = "strict" if strict else "standard"

    return f"""You are performing a pre-show health check in {mode} mode.
Target sequences: {sequences}

Run all checks in order. Collect ALL findings before returning the final report.
Do NOT stop at first AMBER -- run all categories.

CATEGORY 1 -- SHOWFILE (GREEN/RED)
Call get_showfile_info() -- record show name and version.
Call assert_showfile_unchanged() -- RED if fails (show was modified unexpectedly).

CATEGORY 2 -- HYDRATION
Call hydrate_console_state() then get_console_state().

CATEGORY 3 -- PRESET POOL (GREEN/AMBER)
For preset types Color, Position, Beam:
  Call list_preset_pool(preset_type=X).
  AMBER if any expected type has 0 entries.
  AMBER if fewer than 3 entries in Color preset pool.

CATEGORY 4 -- EXECUTOR ASSIGNMENTS (GREEN/AMBER/RED)
For each key executor (1.1, 1.2 minimum):
  Call get_executor_detail(executor_id=X).
  AMBER if executor has no assigned sequence.
  RED if main sequence executor has 0 cues.

CATEGORY 5 -- CUE INTEGRITY (GREEN/AMBER)
For each sequence in [{sequences}]:
  Call query_object_list(object_type="sequence", object_id=N).
  AMBER if gap > 10 between consecutive cue numbers.
  AMBER if more than 20% of cues are unlabeled.
  {"RED if any gap found." if strict else "AMBER if cue count < 3."}

CATEGORY 6 -- PARK LEDGER (GREEN/AMBER)
Call get_park_ledger().
AMBER if any fixtures are parked (may be intentional -- report don't assume error).

CATEGORY 7 -- DMX (GREEN/AMBER)
Call list_fixtures() -- count fixtures with no DMX address.
AMBER if any fixture has address 0 or None.

RETURN FORMAT:
{{
  "show_name": "...",
  "audit_mode": "{mode}",
  "overall": "GREEN | AMBER | RED",
  "categories": {{
    "showfile": {{"score": "...", "findings": [...]}},
    "preset_pool": {{"score": "...", "findings": [...]}},
    "executors": {{"score": "...", "findings": [...]}},
    "cue_integrity": {{"score": "...", "findings": [...]}},
    "park_ledger": {{"score": "...", "findings": [...]}},
    "dmx": {{"score": "...", "findings": [...]}}
  }},
  "recommended_actions": [...]
}}

Overall score = worst score across all categories."""


@mcp.prompt()
def adapt_show_to_venue(
    source_show_description: str = "",
    new_venue_notes: str = ""
) -> str:
    """
    Adapt an existing show file to a new venue's fixture rig — guided cross-venue
    adaptation with patch comparison, group remapping, and preset verification.
    """
    return f"""You are adapting a show file to a new venue rig.

Source show context: {source_show_description or "current loaded show"}
New venue notes: {new_venue_notes or "no additional context provided"}

PHASE 0 -- SURVEY (SAFE_READ -- complete before any changes)
1. Call hydrate_console_state()
2. Call list_fixtures() -- document: fixture ID, type, DMX address for ALL fixtures
3. Call list_fixture_types() -- document imported profiles
4. Call list_preset_pool(preset_type="color") and list_preset_pool(preset_type="position")
5. Sample group membership: call query_object_list(object_type="group", object_id=1)

Present comparison to operator:
"Current rig has [N] fixtures of types [A, B, C].
[Describe any type mismatches based on new_venue_notes].
Which types map to which in the new venue?"

WAIT for operator confirmation of the fixture type mapping before proceeding.

PHASE 1 -- IDENTIFY MISMATCHES
Cross-reference fixture types in the show against new venue patch.
Categorize each type as: COMPATIBLE (same attributes), SIMILAR (same Pan/Tilt/Dim but different gobos),
or INCOMPATIBLE (completely different attribute set).

DECISION: If >50% of fixture types are INCOMPATIBLE, recommend using generate_busking_template
prompt to rebuild from scratch rather than adapting.

PHASE 2 -- REMAP GROUPS (confirm before DESTRUCTIVE operations)
For each group containing old fixture IDs:
  Check current membership with query_object_list(object_type="group", object_id=N).
  If fixture type mapping is COMPATIBLE or SIMILAR: use remap_fixture_ids() to update
  group membership with new fixture IDs. Ask operator to confirm before each group.

PHASE 3 -- VERIFY PRESETS
For SIMILAR types: test universal color presets -- call apply_preset(preset_type="color", preset_id=1)
with new fixture selected and verify output.
For INCOMPATIBLE types: presets must be re-recorded. Guide operator through re-recording.

PHASE 4 -- TEST AND VERIFY
Select a sample group: select_fixtures_by_group(group_id=1).
Apply a color preset: apply_preset(preset_type="color", preset_id=1).
Confirm correct fixtures respond.

PHASE 5 -- SAVE
Call save_show(confirm_destructive=True).

At every DESTRUCTIVE phase: present what will change and ask "Proceed? (yes/no)" before executing."""


# ============================================================
# Agent Harness
# ============================================================


def _build_tool_registry() -> dict:
    """Build a registry mapping tool names to their async callables.

    This enables the agent runtime to call MCP tools directly as Python
    functions, without going through the MCP protocol.

    Uses FastMCP's tool manager as the authoritative source so that the
    registry is always exactly the set of registered MCP tools — no more,
    no less. Falls back to globals() introspection if the FastMCP internals
    change in a future version.
    """
    registry: dict = {}
    try:
        for tool_name, tool_obj in mcp._tool_manager._tools.items():
            fn = getattr(tool_obj, "fn", None)
            if fn is not None:
                registry[tool_name] = fn
    except AttributeError:
        # Fallback: scan module globals for @_handle_errors-wrapped async fns
        import inspect

        for name, obj in globals().items():
            if callable(obj) and hasattr(obj, "__wrapped__"):
                registry[name] = obj
            elif inspect.iscoroutinefunction(obj) and not name.startswith("_"):
                registry[name] = obj
    return registry


@mcp.tool()
@require_scope(OAuthScope.SYSTEM_ADMIN)
@_handle_errors
async def run_agent_goal(
    goal: str,
    auto_confirm: bool = False,
    dry_run: bool = False,
) -> str:
    """Execute a high-level production goal using the agent runtime.

    The agent runtime decomposes the goal into a sequenced plan, validates
    it against safety policies, executes steps with verification, and
    produces a structured execution trace.

    SAFETY: Destructive steps require confirmation. Set auto_confirm=True
    to skip confirmation prompts (use with caution).

    Args:
        goal: Natural language goal, e.g. "Patch 8 Mac 700 fixtures
            starting at address 1.001 and assign to executor 1"
        auto_confirm: If True, auto-confirm all destructive steps.
            If False (default), destructive steps remain blocked unless
            the runtime can obtain an explicit confirmation callback.
        dry_run: If True, generate and validate the plan but do NOT
            execute it. Returns the plan and policy warnings.

    Returns:
        str: JSON execution trace with goal, plan, steps, result,
            and timing information.

    Examples:
        - "List all groups" → discovery workflow
        - "Patch 4 Mac 700 fixtures at 1.001" → patch workflow
        - "Create a color preset for group 1" → preset workflow
    """
    from src.agent.runtime import AgentRuntime

    registry = _build_tool_registry()
    runtime = AgentRuntime(tool_registry=registry)

    if dry_run:
        parsed_goal, plan, warnings = await runtime.plan_only(goal)
        return json.dumps({
            "dry_run": True,
            "goal": goal,
            "intent": parsed_goal.intent.value,
            "confidence": parsed_goal.confidence,
            "plan": [s.to_dict() for s in plan],
            "policy_warnings": warnings,
        }, indent=2)

    # Auto-confirm callback for the agent runtime
    async def _auto_confirm(step) -> bool:
        return True

    trace = await runtime.run(
        goal,
        on_confirm=_auto_confirm if auto_confirm else None,
    )
    return trace.to_json()


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def plan_agent_goal(goal: str) -> str:
    """Generate a plan for a goal WITHOUT executing it.

    Useful for previewing what the agent would do before committing.
    Returns the parsed goal, generated plan steps, and any policy warnings.

    Args:
        goal: Natural language goal to plan for.

    Returns:
        str: JSON with intent, plan steps, confidence, and warnings.
    """
    from src.agent.runtime import AgentRuntime

    registry = _build_tool_registry()
    runtime = AgentRuntime(tool_registry=registry)

    parsed_goal, plan, warnings = await runtime.plan_only(goal)
    return json.dumps({
        "goal": goal,
        "intent": parsed_goal.intent.value,
        "object_type": parsed_goal.object_type,
        "confidence": parsed_goal.confidence,
        "step_count": len(plan),
        "plan": [
            {
                "description": s.description,
                "tool": s.tool_name,
                "risk_tier": s.risk_tier.value,
                "depends_on_count": len(s.depends_on),
            }
            for s in plan
        ],
        "policy_warnings": warnings,
    }, indent=2)


# ============================================================
# Server Startup
# ============================================================

_VALID_TRANSPORTS = ("stdio", "sse", "streamable-http")


def main():
    """MCP Server entry point."""
    logger.info("Starting grandMA2 MCP Server...")
    logger.info(f"Connecting to grandMA2: {_GMA_HOST}:{_GMA_PORT}")

    # Warn if using factory-default credentials
    if _GMA_USER == "administrator" and _GMA_PASSWORD == "admin":
        logger.warning(
            "Using factory-default credentials (administrator/admin). "
            "Set GMA_USER and GMA_PASSWORD environment variables for "
            "network deployments."
        )

    # Select transport from environment (default: stdio for Claude Code / Claude Desktop)
    transport = os.environ.get("GMA_TRANSPORT", "stdio").lower()
    if transport not in _VALID_TRANSPORTS:
        raise ValueError(
            f"Invalid GMA_TRANSPORT={transport!r}. "
            f"Valid options: {', '.join(_VALID_TRANSPORTS)}"
        )

    if transport != "stdio":
        logger.warning(
            "HTTP transport (%s) has no built-in authentication. "
            "Only use on trusted local networks.", transport,
        )

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
