"""
MCP Server Module

This module is responsible for creating and running the MCP server,
integrating all tools together. It uses FastMCP to simplify the MCP server setup.

Usage:
    uv run python -m src.server

Most tools live in ``src/mcp_tools/`` and are imported (and re-exported) at
the end of this module so they register on the same ``mcp`` instance.
"""

if __name__ == "__main__":  # pragma: no cover
    # `python -m src.server` runs this file as __main__; the tool modules import
    # `src.server`, so hand over to that canonical module before doing anything
    # else — otherwise tools would register on a second FastMCP instance.
    import importlib
    import sys

    sys.exit(importlib.import_module("src.server").main())

import asyncio
import contextlib
import functools
import inspect
import json
import logging
import os
import re
import sys
import time

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.agent_memory import LongTermMemory
from src.auth import OAuthScope, require_scope
from src.commands import (
    delete_show as build_delete_show,  # noqa: F401 — used via src.server
    list_fader_modules as build_list_fader_modules,  # noqa: F401 — used via src.server
    list_library as build_list_library,  # noqa: F401 — used via src.server
    list_shows as build_list_shows,  # noqa: F401 — used via src.server
    load_show as build_load_show,  # noqa: F401 — used via src.server
    new_show as build_new_show,  # noqa: F401 — used via src.server
    release_executor as build_release_executor,  # noqa: F401 — used via src.server
)
from src.console_feedback import annotate_tool_result
from src.context import _current_session_id
from src.credentials import get_operator_identity, resolve_console_credentials
from src.mcp_features import (
    ACTIVITY_RESOURCE_URI,
    active_context,
    ask_destructive_confirmation,
    needs_destructive_confirmation,
    notify_resource_updated,
)
from src.navigation import (  # noqa: F401 — used via src.server
    get_current_location,
    list_destination,
    navigate,
    scan_indexes,
    set_property,
)
from src.orchestrator import Orchestrator
from src.server_orchestration_tools import register_orchestration_tools
from src.session_manager import SessionManager
from src.telemetry import ToolTelemetry, infer_risk_tier
from src.telnet_client import GMA2TelnetClient, collect_transport_warnings
from src.tools import set_gma2_client
from src.vocab import build_v39_spec

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

# grandMA2 truncates a Telnet command line at 1023 characters (then Error #72).
_MAX_COMMAND_CHARS = 1023

# Friendly sequence property names → MA2 column names (live: "tracking" is ignored).
_SEQUENCE_PROPERTY_ALIASES = {"tracking": "Track", "track": "Track"}

# Path to the repo-root .env file (used by reconfigure_connection persist).
from pathlib import Path as _Path  # noqa: E402

_ENV_PATH = _Path(__file__).parent.parent / ".env"


def _osc_allowed_hosts() -> set[str]:
    raw = os.getenv("GMA_OSC_ALLOWED_HOSTS", "localhost,127.0.0.1,::1")
    return {host.strip().lower() for host in raw.split(",") if host.strip()}

# Build vocab spec once for token classification / safety gating
_vocab_spec = build_v39_spec()

# Create MCP server
mcp = FastMCP(
    name="MA2 Agent",
    instructions="""grandMA2 MCP server — tools, resources, and prompts for console control via Telnet.

Use suggest_tool_for_task(task_description) to find the right tool for any task.
Use ma2://docs/tool-taxonomy resource to browse all tools by category.

Core workflows:
  Inspect  → navigate_console, list_console_destination, query_object_list, get_object_info
  Plan     → plan_agent_goal (preferred) or inspect + list_system_variables + suggest_tool_for_task
  Execute  → run_agent_goal (preferred agent harness) or run_task (lower-level rule-based orchestration)

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




async def _get_session_manager():
    """Return the active session manager. Honours ``GMA_MOCK`` env var.

    Return type is intentionally untyped here: the real path returns
    :class:`SessionManager`; the mock path returns :class:`MockSessionManager`,
    which implements the same public surface.
    """
    global _session_manager
    async with _session_manager_lock:
        if _session_manager is None:
            mock_tier = os.environ.get("GMA_MOCK")
            if mock_tier:
                from src.mock.session_manager import MockSessionManager
                _session_manager = MockSessionManager(tier=mock_tier)
            else:
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
    _accepts_confirm = "confirm_destructive" in inspect.signature(func).parameters

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> str:
        t0 = time.monotonic()

        async def _invoke(call_kwargs: dict) -> tuple[str, str | None, list[str]]:
            warnings: list[str] = []
            try:
                with collect_transport_warnings() as warnings:
                    return await func(*args, **call_kwargs), None, warnings
            except ConnectionError as e:
                logger.error("Connection error in %s: %s", func.__name__, e)
                error = {"error": f"Connection failed: {e}", "blocked": True}
                return json.dumps(error, indent=2), "ConnectionError", warnings
            except RuntimeError as e:
                logger.error("Runtime error in %s: %s", func.__name__, e)
                error = {"error": f"Runtime error: {e}", "blocked": True}
                return json.dumps(error, indent=2), "RuntimeError", warnings
            except Exception as e:
                logger.error("Unexpected error in %s: %s", func.__name__, e, exc_info=True)
                error = {"error": f"Unexpected error: {e}", "blocked": True}
                return json.dumps(error, indent=2), type(e).__name__, warnings

        result, error_class, transport_warnings = await _invoke(kwargs)
        ctx = active_context(mcp)

        # A destructive tool blocked only for want of confirm_destructive: ask the
        # human in the MCP client (elicitation). Only an explicit accept re-runs it.
        if (
            _accepts_confirm
            and kwargs.get("confirm_destructive") is not True
            and needs_destructive_confirmation(result)
        ):
            reason = str(json.loads(result).get("error", ""))
            answer = await ask_destructive_confirmation(ctx, func.__name__, kwargs, reason)
            if answer is True:
                result, error_class, transport_warnings = await _invoke({**kwargs, "confirm_destructive": True})
                result = _with_fields(result, confirmed_by="elicitation")
            elif answer is False:
                result = _with_fields(result, elicitation="declined")

        # Uniform reply contract: every JSON object reply gets ``ok``; console
        # rejections hidden in raw_response become structured console_errors.
        try:
            result, console_errors = annotate_tool_result(result, transport_warnings)
            if console_errors and error_class is None:
                error_class = "ConsoleError"
        except Exception:  # noqa: BLE001 — annotation must never break a tool call
            logger.debug("Reply annotation failed for %s", func.__name__, exc_info=True)
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

        # Console changed → tell subscribers of the activity resource (after the
        # telemetry row exists, so a re-read sees this call).
        if _risk_tier != "SAFE_READ" and error_class is None and '"ok": true' in result:
            await notify_resource_updated(ctx, ACTIVITY_RESOURCE_URI)
        return result

    return wrapper


def _with_fields(result: str, **fields) -> str:
    """Add fields to a JSON object reply (non-object replies are returned unchanged)."""
    try:
        data = json.loads(result)
    except (TypeError, ValueError):
        return result
    if not isinstance(data, dict):
        return result
    data.update(fields)
    return json.dumps(data, indent=2, default=str)


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
@require_scope(OAuthScope.SYSTEM_ADMIN)
@_handle_errors
async def reconfigure_connection(
    host: str,
    port: int = 30000,
    user: str = "administrator",
    password: str = "admin",
    persist: bool = False,
    verify: bool = True,
) -> str:
    """Swap the active console connection and (optionally) persist to .env.

    Atomic swap: rebuilds the SessionManager under the manager lock so in-flight
    tool calls either complete on the old manager or fail with ConnectionError
    (operator-recoverable). With ``verify=True`` (default), a fresh client is
    opened against the candidate host and ``ListVar`` is executed before any
    swap; failure aborts the call and leaves the previous connection intact.

    Args:
        host: New console host (IPv4 or hostname).
        port: Telnet port (default 30000).
        user: Console user.
        password: Console password.
        persist: When True, also write GMA_HOST/GMA_PORT/GMA_USER/GMA_PASSWORD to
            .env so the next server start uses them (default False: this run only).
        verify: When True, run a SAFE_READ probe before committing the swap.
            With False the reply says ``verified: false``. To just free the
            console, use disconnect_console instead of pointing at a dummy host.

    Returns:
        JSON envelope: ``{success, previous_host, new_host, verified, persisted_to,
        note, warning, error}``.
    """
    global _GMA_HOST, _GMA_PORT, _GMA_USER, _GMA_PASSWORD, _session_manager

    previous_host = _GMA_HOST
    same = (host == _GMA_HOST and port == _GMA_PORT and user == _GMA_USER)
    if same:
        return json.dumps({
            "success": True, "previous_host": previous_host, "new_host": host,
            "verified": True, "persisted_to": None, "note": "no change",
            "warning": None, "error": None,
        }, indent=2)

    verified = False  # only a successful round-trip may claim verified
    if verify:
        verified = await _verify_round_trip(host, port, user, password)
    if verify and not verified:
        return json.dumps({
            "success": False, "previous_host": previous_host, "new_host": host,
            "verified": False, "persisted_to": None, "note": None,
            "warning": None,
            "error": f"verify round-trip to {host}:{port} failed",
        }, indent=2)

    async with _session_manager_lock:
        old_mgr = _session_manager
        _GMA_HOST = host
        _GMA_PORT = port
        _GMA_USER = user
        _GMA_PASSWORD = password
        _session_manager = None  # next get_client() will rebuild

    if old_mgr is not None:
        # close best-effort; new manager already in place
        with contextlib.suppress(Exception):
            await old_mgr.close_all()

    persisted_to: str | None = None
    if persist:
        _persist_env(
            _ENV_PATH,
            GMA_HOST=host,
            GMA_PORT=str(port),
            GMA_USER=user,
            GMA_PASSWORD=password,
        )
        persisted_to = str(_ENV_PATH)

    return json.dumps({
        "success": True, "previous_host": previous_host, "new_host": host,
        "verified": verified, "persisted_to": persisted_to, "note": None,
        "warning": None, "error": None,
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


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def snapshot_console_baseline() -> str:
    """
    Snapshot a console-state baseline for divergence detection (SAFE_READ).

    Records a cheap fingerprint of the console — showfile, user, page
    counters, selected executor, and the ID sets of the group/sequence/
    macro/world/filter pools. Call this at the start of a working session
    (or before handing the desk to another operator); later, call
    detect_console_divergence to see what changed outside this MCP session.

    Returns:
        str: JSON with the recorded baseline and captured_at timestamp.
    """
    global _console_baseline
    state = await _read_divergence_state()
    state["captured_at"] = time.time()
    _console_baseline = state
    return json.dumps({
        "baseline": state,
        "risk_tier": "SAFE_READ",
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

    apply_tool_profile(os.environ.get("GMA_TOOL_PROFILE"))
    mcp.run(transport=transport)




# ============================================================
# Tool modules (split out of this file) — importing them registers their tools;
# the `X as X` re-exports keep `from src.server import X` and
# patch('src.server.X') working (tool modules look names up as _srv.X).
# ============================================================
from src.mcp_tools.agent import (
    _build_tool_registry as _build_tool_registry,
    plan_agent_goal as plan_agent_goal,
    run_agent_goal as run_agent_goal,
)
from src.mcp_tools.analysis import (
    audit_page_consistency as audit_page_consistency,
    compare_patch_to_show_expectation as compare_patch_to_show_expectation,
    detect_programmer_contamination as detect_programmer_contamination,
    detect_tracking_leaks as detect_tracking_leaks,
    diff_cues as diff_cues,
    find_executor_dependencies as find_executor_dependencies,
    find_preset_usages as find_preset_usages,
    find_unused_objects as find_unused_objects,
    generate_song_macro_pack as generate_song_macro_pack,
    get_page_map as get_page_map,
    incident_snapshot as incident_snapshot,
    lint_macro as lint_macro,
    plan_fixture_swap as plan_fixture_swap,
    preview_preset_update_impact as preview_preset_update_impact,
    restore_programmer_state as restore_programmer_state,
    snapshot_programmer_state as snapshot_programmer_state,
    trace_attribute_lineage as trace_attribute_lineage,
    validate_universal_preset_coverage as validate_universal_preset_coverage,
)
from src.mcp_tools.busking import (
    assign_effect_to_executor as assign_effect_to_executor,
    classify_show_mode as classify_show_mode,
    clear_effects_on_page as clear_effects_on_page,
    modulate_effect as modulate_effect,
    normalize_page_faders as normalize_page_faders,
)
from src.mcp_tools.categorization import (
    _taxonomy_cache as _taxonomy_cache,
    get_similar_tools as get_similar_tools,
    list_tool_categories as list_tool_categories,
    recluster_tools as recluster_tools,
    suggest_tool_for_task as suggest_tool_for_task,
)
from src.mcp_tools.composite import (
    _parse_listvar as _parse_listvar,
    _read_selected_exec as _read_selected_exec,
    assign_object as assign_object,
    edit_object as edit_object,
    label_or_appearance as label_or_appearance,
    list_system_variables as list_system_variables,
    manage_variable as manage_variable,
    playback_action as playback_action,
    query_object_list as query_object_list,
    remove_content as remove_content,
    store_object as store_object,
)
from src.mcp_tools.console import (
    _BATCH_FILE_SUFFIXES as _BATCH_FILE_SUFFIXES,
    _BATCH_MAX_FAILURES_REPORTED as _BATCH_MAX_FAILURES_REPORTED,
    _load_batch_lines as _load_batch_lines,
    answer_console_popup as answer_console_popup,
    apply_preset as apply_preset,
    clear_programmer as clear_programmer,
    copy_or_move_object as copy_or_move_object,
    create_fixture_group as create_fixture_group,
    delete_object as delete_object,
    disconnect_console as disconnect_console,
    execute_sequence as execute_sequence,
    get_console_location as get_console_location,
    get_object_info as get_object_info,
    list_console_destination as list_console_destination,
    navigate_console as navigate_console,
    park_fixture as park_fixture,
    run_command_batch as run_command_batch,
    run_macro as run_macro,
    scan_console_indexes as scan_console_indexes,
    send_raw_command as send_raw_command,
    set_attribute as set_attribute,
    set_intensity as set_intensity,
    set_node_property as set_node_property,
    store_current_cue as store_current_cue,
    store_new_preset as store_new_preset,
    unpark_fixture as unpark_fixture,
)
from src.mcp_tools.console_extras import (
    call_plugin_tool as call_plugin_tool,
    console_login as console_login,
    console_logout as console_logout,
    control_chaser as control_chaser,
    control_special_master as control_special_master,
    label_world as label_world,
    list_agenda_events as list_agenda_events,
    list_effects_pool as list_effects_pool,
    list_filters as list_filters,
    list_forms as list_forms,
    list_images as list_images,
    list_layouts as list_layouts,
    list_timecode_events as list_timecode_events,
    list_timers as list_timers,
    list_worlds as list_worlds,
    lock_console_ui as lock_console_ui,
    rdm_discover as rdm_discover,
    rdm_get_info as rdm_get_info,
    rdm_patch as rdm_patch,
    reload_all_plugins as reload_all_plugins,
    run_lua_script as run_lua_script,
    set_effect_param as set_effect_param,
    store_agenda as store_agenda,
    store_world as store_world,
    unlock_console_ui as unlock_console_ui,
)
from src.mcp_tools.diagnostics import (
    auto_number_cues as auto_number_cues,
    batch_label as batch_label,
    bulk_executor_assign as bulk_executor_assign,
    compare_cue_values as compare_cue_values,
    diagnose_no_output as diagnose_no_output,
)
from src.mcp_tools.discovery import (
    _OBJECT_POOL_DESTINATIONS as _OBJECT_POOL_DESTINATIONS,
    _check_pool_slots as _check_pool_slots,
    check_pool_availability as check_pool_availability,
    discover_object_names as discover_object_names,
    list_fixtures as list_fixtures,
    list_sequence_cues as list_sequence_cues,
)
from src.mcp_tools.divergence import (
    _DIVERGENCE_POOLS as _DIVERGENCE_POOLS,
    _DIVERGENCE_VARS as _DIVERGENCE_VARS,
    _console_baseline as _console_baseline,
    _read_divergence_state as _read_divergence_state,
    detect_console_divergence as detect_console_divergence,
)
from src.mcp_tools.expert import (
    _persist_env as _persist_env,
    _verify_round_trip as _verify_round_trip,
    architect_preset_library as architect_preset_library,
    build_layout_for_screen as build_layout_for_screen,
    build_show_from_patch as build_show_from_patch,
    check_plugin_available as check_plugin_available,
    discover_consoles as discover_consoles,
    generate_ma2_macro as generate_ma2_macro,
    suggest_skills_for_task as suggest_skills_for_task,
)
from src.mcp_tools.fixture_import import (
    generate_fixture_layer_xml as generate_fixture_layer_xml,
    import_fixture_layer as import_fixture_layer,
    import_fixture_type as import_fixture_type,
)
from src.mcp_tools.fixture_types import (
    _POOL_ID_RE_TMPL as _POOL_ID_RE_TMPL,
    _hydrate_fixture_type_model as _hydrate_fixture_type_model,
    _parse_pool_ids as _parse_pool_ids,
    analyze_patch_types as analyze_patch_types,
    create_presets_for_patch as create_presets_for_patch,
    renumber_fixtures as renumber_fixtures,
    run_preset_plugin as run_preset_plugin,
    select_fixtures_by_type_order as select_fixtures_by_type_order,
    verify_fixture_id_blocks as verify_fixture_id_blocks,
)
from src.mcp_tools.import_export import (
    _EXPORT_TYPES as _EXPORT_TYPES,
    _GMA2_DATA_ROOT as _GMA2_DATA_ROOT,
    _IMPORT_EXPORT_DATA_ROOT as _IMPORT_EXPORT_DATA_ROOT,
    _IMPORT_TYPES as _IMPORT_TYPES,
    export_objects as export_objects,
    import_objects as import_objects,
)
from src.mcp_tools.integrations import (
    companion_button_press as companion_button_press,
    generate_companion_config as generate_companion_config,
    send_osc as send_osc,
    set_bpm as set_bpm,
)
from src.mcp_tools.operations import (
    check_pool_slot_availability as check_pool_slot_availability,
    detect_dmx_address_conflicts as detect_dmx_address_conflicts,
    generate_compliance_report as generate_compliance_report,
    get_telemetry_report as get_telemetry_report,
    list_macro_jump_targets as list_macro_jump_targets,
    master_control as master_control,
    plugin_management as plugin_management,
    programming_action as programming_action,
    remap_fixture_ids as remap_fixture_ids,
    system_admin as system_admin,
    update_object as update_object,
    validate_preset_references as validate_preset_references,
)
from src.mcp_tools.patching import (
    browse_patch_schedule as browse_patch_schedule,
    patch_fixture as patch_fixture,
    set_fixture_type_property as set_fixture_type_property,
    unpatch_fixture as unpatch_fixture,
)
from src.mcp_tools.playback import (
    blackout_toggle as blackout_toggle,
    get_variable as get_variable,
    highlight_fixtures as highlight_fixtures,
    list_preset_pool as list_preset_pool,
    list_shows as list_shows,
    list_undo_history as list_undo_history,
    load_show as load_show,
    new_show as new_show,
    release_executor as release_executor,
)
from src.mcp_tools.programming import (
    _parse_preset_tree_list as _parse_preset_tree_list,
    adjust_value_relative as adjust_value_relative,
    block_unblock_cue as block_unblock_cue,
    browse_preset_type as browse_preset_type,
    clone_object as clone_object,
    control_executor as control_executor,
    control_timecode as control_timecode,
    control_timer as control_timer,
    cut_paste_object as cut_paste_object,
    fix_locate_fixture as fix_locate_fixture,
    get_executor_status as get_executor_status,
    load_cue as load_cue,
    manipulate_selection as manipulate_selection,
    modify_selection as modify_selection,
    navigate_page as navigate_page,
    select_feature as select_feature,
    select_fixtures_by_group as select_fixtures_by_group,
    select_preset_type as select_preset_type,
    set_cue_timing as set_cue_timing,
    set_executor_level as set_executor_level,
    set_sequence_property as set_sequence_property,
    store_timecode_event as store_timecode_event,
    toggle_console_mode as toggle_console_mode,
    undo_last_action as undo_last_action,
    update_cue_data as update_cue_data,
)
from src.mcp_tools.prompts import (
    adapt_show_to_venue as adapt_show_to_venue,
    bootstrap_rights_users as bootstrap_rights_users,
    diagnose_playback_failure as diagnose_playback_failure,
    generate_busking_template as generate_busking_template,
    inspect_console as inspect_console,
    load_show_safely as load_show_safely,
    plan_cue_store as plan_cue_store,
    pre_show_health_check as pre_show_health_check,
    preflight_destructive_change as preflight_destructive_change,
    volunteer_sunday_preflight as volunteer_sunday_preflight,
)
from src.mcp_tools.quick_wins import (
    assign_temp_fader as assign_temp_fader,
    browse_effect_library as browse_effect_library,
    browse_macro_library as browse_macro_library,
    browse_plugin_library as browse_plugin_library,
    delete_show as delete_show,
    delete_user as delete_user,
    list_fader_modules as list_fader_modules,
    list_update_history as list_update_history,
)
from src.mcp_tools.resources import (
    resource_busking_patterns as resource_busking_patterns,
    resource_color_design as resource_color_design,
    resource_console_activity as resource_console_activity,
    resource_effect_design as resource_effect_design,
    resource_lua_scripting as resource_lua_scripting,
    resource_rdm_workflow as resource_rdm_workflow,
    resource_responsibility_map as resource_responsibility_map,
    resource_rights_matrix as resource_rights_matrix,
    resource_sb132_compliance as resource_sb132_compliance,
    resource_skill_body as resource_skill_body,
    resource_tool_surface_tiers as resource_tool_surface_tiers,
    resource_tool_taxonomy as resource_tool_taxonomy,
    resource_vocab_summary as resource_vocab_summary,
    resource_volunteer_guide as resource_volunteer_guide,
)
from src.mcp_tools.search import (
    search_codebase as search_codebase,
)
from src.mcp_tools.setup_library import (
    _discover_filter_attributes as _discover_filter_attributes,
    create_filter_library as create_filter_library,
    create_matricks_library as create_matricks_library,
    discover_filter_attributes as discover_filter_attributes,
    list_fixture_types as list_fixture_types,
    list_layers as list_layers,
    list_library as list_library,
    list_universes as list_universes,
    manage_matricks as manage_matricks,
    store_matricks_preset as store_matricks_preset,
)
from src.mcp_tools.show_files import (
    assign_cue_trigger as assign_cue_trigger,
    assign_executor_property as assign_executor_property,
    discover_fixture_type_attributes as discover_fixture_type_attributes,
    get_executor_state as get_executor_state,
    if_filter as if_filter,
    remove_from_programmer as remove_from_programmer,
    save_recall_view as save_recall_view,
    save_show as save_show,
    scan_page_executor_layout as scan_page_executor_layout,
    select_executor as select_executor,
    set_executor_priority as set_executor_priority,
    store_cue_with_timing as store_cue_with_timing,
)
from src.mcp_tools.users import (
    assign_world_to_user_profile as assign_world_to_user_profile,
    create_console_user as create_console_user,
    inspect_sessions as inspect_sessions,
    list_console_users as list_console_users,
)

# Every registered tool, kept even when a profile hides some from MCP clients:
# the agent harness (_build_tool_registry) still needs them.
_ALL_TOOLS: dict = dict(mcp._tool_manager._tools)


def apply_tool_profile(value: str | None) -> str:
    """Hide tools outside the GMA_TOOL_PROFILE subset from MCP clients."""
    from src.tool_profiles import resolve_profile, visible_tools

    profile, warning = resolve_profile(value)
    if warning:
        logger.warning(warning)
    keep = visible_tools(profile, set(_ALL_TOOLS))
    mcp._tool_manager._tools = {name: tool for name, tool in _ALL_TOOLS.items() if name in keep}
    logger.info("Tool profile %r: %d of %d tools visible", profile, len(keep), len(_ALL_TOOLS))
    return profile


if __name__ == "__main__":
    main()
