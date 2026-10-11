"""MCP tools — divergence. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json
import time

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.server import (
    _handle_errors,
    mcp,
)

# ============================================================
# Console divergence detection — baseline snapshot + diff
# ============================================================

_DIVERGENCE_VARS = (
    "$SHOWFILE", "$USER", "$USERPROFILE",
    "$FADERPAGE", "$BUTTONPAGE", "$CHANNELPAGE",
    "$SELECTEDEXEC",
)
_DIVERGENCE_POOLS = ("group", "sequence", "macro", "world", "filter")

_console_baseline: dict | None = None


async def _read_divergence_state() -> dict:
    """Cheap console fingerprint: key system vars + pool ID sets."""
    client = await _srv.get_client()
    raw = await client.send_command_with_response("ListVar")
    variables = _srv._parse_listvar(raw)
    state: dict = {
        "vars": {k: variables.get(k, "") for k in _srv._DIVERGENCE_VARS},
        "pools": {},
    }
    for pool in _srv._DIVERGENCE_POOLS:
        raw = await client.send_command_with_response(f"list {pool}", timeout=3.0)
        state["pools"][pool] = _srv._parse_pool_ids(raw, pool)
    return state


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def detect_console_divergence() -> str:
    """
    Diff current console state against the recorded baseline (SAFE_READ).

    Detects changes made outside this MCP session — a different show loaded,
    user/page changes on the physical desk, pool objects added or deleted
    (groups, sequences, macros, worlds, filters). Complements the tracked
    snapshot for the write-only dimensions (MAtricks, park, filter VTE) that
    have no telnet readback: when the pools or vars moved, assume those
    write-trackers are stale too.

    Call snapshot_console_baseline first; this tool errors without one.

    Returns:
        str: JSON with diverged (bool), changed_vars, pool_changes
        (added/removed IDs per pool), baseline_age_seconds, risk_tier.
    """
    if _srv._console_baseline is None:
        return json.dumps({
            "error": "No baseline recorded — call snapshot_console_baseline first.",
            "diverged": None,
            "risk_tier": "SAFE_READ",
        }, indent=2)

    current = await _srv._read_divergence_state()
    changed_vars = {
        k: {"baseline": _srv._console_baseline["vars"].get(k, ""), "current": v}
        for k, v in current["vars"].items()
        if v != _srv._console_baseline["vars"].get(k, "")
    }
    pool_changes: dict[str, dict] = {}
    for pool in _srv._DIVERGENCE_POOLS:
        base = set(_srv._console_baseline["pools"].get(pool, []))
        cur = set(current["pools"].get(pool, []))
        if base != cur:
            pool_changes[pool] = {
                "added": sorted(cur - base),
                "removed": sorted(base - cur),
            }

    diverged = bool(changed_vars or pool_changes)
    result: dict = {
        "diverged": diverged,
        "changed_vars": changed_vars,
        "pool_changes": pool_changes,
        "baseline_age_seconds": round(
            time.time() - _srv._console_baseline["captured_at"], 1
        ),
        "risk_tier": "SAFE_READ",
    }
    if diverged:
        result["warning"] = (
            "Console state changed outside this session — write-tracked "
            "dimensions (MAtricks, park, filter VTE, console modes) may be "
            "stale. Re-hydrate before DESTRUCTIVE operations."
        )
    return json.dumps(result, indent=2)
