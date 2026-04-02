"""
OAuth 2.1 scope enforcement layer (stub implementation).

This module provides scope-based authorization for MCP tools.
Real OAuth token validation (Keycloak/Auth0) is future work.
For now: GMA_SCOPE env var holds a space-separated list of granted scopes
or tier shorthand tokens.

Scope expansion is cumulative: tier N includes all scopes from tiers 0..N-1.
Set GMA_SCOPE="tier:5" to grant all scopes (full admin access).

Environment variables:
    GMA_SCOPE: Space-separated granted scopes or tier shorthands
               Default: "gma2:discover gma2:state:read"   (Tier 0 — view only)
               Examples:
                 GMA_SCOPE="tier:1"                     (Playback operator)
                 GMA_SCOPE="tier:3"                     (Show programmer)
                 GMA_SCOPE="tier:5"                     (Full admin)
                 GMA_SCOPE="gma2:playback:go gma2:executor:control"  (explicit)
    GMA_AUTH_BYPASS: Set to "1" to disable scope checking entirely (dev/test mode)
                     WARNING: never set in production.

Decorator stacking order in src/server.py (critical):
    @mcp.tool()           ← FastMCP registration (outermost)
    @require_scope(...)   ← scope check (second)
    @_handle_errors       ← error formatting (innermost before function)
    async def tool_fn():  ← actual implementation

When scope is denied, returns the same JSON shape as _handle_errors blocks:
    {"blocked": True, "error": "...", "scope_required": "...", "scope_tier": N}
"""

from __future__ import annotations

import functools
import json
import logging
import os

from src.commands.constants import MA2RIGHT_TO_OAUTH_SCOPE, OAUTH_TIER_SCOPES, MA2Right, OAuthScope

logger = logging.getLogger(__name__)


# ============================================================================
# Cumulative scope expansion
# ============================================================================

def _build_cumulative_scope_set(tier: int) -> frozenset[str]:
    """Return all scope strings for tiers 0..tier (inclusive, cumulative)."""
    scopes: list[str] = []
    for t in range(tier + 1):
        for s in OAUTH_TIER_SCOPES.get(t, []):
            scopes.append(str(s))
    return frozenset(scopes)


# Precomputed cumulative scope sets for tiers 0-5.
_TIER_SCOPE_SETS: dict[int, frozenset[str]] = {
    t: _build_cumulative_scope_set(t) for t in range(6)
}

# Full set of all scopes (tier 5 cumulative).
ALL_SCOPES: frozenset[str] = _TIER_SCOPE_SETS[5]


# ============================================================================
# Scope resolution from environment
# ============================================================================

def get_granted_scopes() -> frozenset[str]:
    """
    Parse GMA_SCOPE env var into a frozenset of granted OAuth scope strings.

    Expansion rules (tokens are space-separated):
    - "tier:N"               → expands to all scopes for tiers 0..N (cumulative)
    - "gma2:cue:store"       → grants exactly that scope string
    - Multiple tokens        → union of all resolved scopes

    Examples:
        GMA_SCOPE="tier:1"                       → {gma2:discover, gma2:state:read,
                                                    gma2:playback:go, gma2:executor:control}
        GMA_SCOPE="gma2:playback:go"             → {gma2:playback:go}
        GMA_SCOPE="tier:0 gma2:cue:store"        → tier 0 + gma2:cue:store
    """
    raw = os.getenv("GMA_SCOPE", "gma2:discover gma2:state:read")
    granted: set[str] = set()

    for token in raw.split():
        token = token.strip()
        if not token:
            continue
        if token.startswith("tier:"):
            try:
                tier_num = int(token[5:])
                granted |= _TIER_SCOPE_SETS.get(min(tier_num, 5), frozenset())
            except ValueError:
                logger.warning("Invalid tier token in GMA_SCOPE: %r (expected tier:0..5)", token)
        else:
            granted.add(token)

    return frozenset(granted)


def _scope_to_tier(scope_str: str) -> int:
    """Reverse lookup: return the tier number that defines this scope (-1 if unknown)."""
    for t, scopes in OAUTH_TIER_SCOPES.items():
        if scope_str in [str(s) for s in scopes]:
            return t
    return -1


# ============================================================================
# Authorization check
# ============================================================================

def has_scope(required: OAuthScope | str) -> bool:
    """Return True if the current session has the required scope granted."""
    if os.getenv("GMA_AUTH_BYPASS", "0") == "1":
        return True
    return str(required) in get_granted_scopes()


# ============================================================================
# require_scope decorator
# ============================================================================

def require_ma2_right(right: MA2Right):
    """
    Decorator factory: enforce a grandMA2 native rights level on an MCP tool.

    Translates the MA2Right value to its corresponding OAuthScope via
    MA2RIGHT_TO_OAUTH_SCOPE and delegates to require_scope.  Use this instead
    of @require_scope when you want to express authorization in terms of the
    MA2 native rights ladder rather than raw OAuth scope strings.

    Usage in src/server.py:
        @mcp.tool()
        @require_ma2_right(MA2Right.PROGRAM)
        @_handle_errors
        async def store_current_cue(...):
            ...

    Equivalent to: @require_scope(MA2RIGHT_TO_OAUTH_SCOPE[MA2Right.PROGRAM])
    """
    return require_scope(MA2RIGHT_TO_OAUTH_SCOPE[right])


def require_scope(scope: OAuthScope | str):
    """
    Decorator factory: blocks the MCP tool if the required OAuth scope is absent.

    Returns a JSON-serialized {"blocked": True, ...} string when access is denied,
    consistent with the existing _handle_errors response format.

    Usage in src/server.py:
        @mcp.tool()
        @require_scope(OAuthScope.CUE_STORE)
        @_handle_errors
        async def store_current_cue(...):
            ...

    The decorator preserves the original function signature via functools.wraps
    so FastMCP's introspection continues to work correctly.
    """
    scope_str = str(scope)
    scope_tier = _scope_to_tier(scope_str)

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not has_scope(scope_str):
                granted = sorted(get_granted_scopes())
                logger.warning(
                    "SCOPE DENIED: tool=%r requires_scope=%r granted=%r",
                    func.__name__, scope_str, granted,
                )
                return json.dumps({
                    "blocked": True,
                    "error": (
                        f"Tool '{func.__name__}' requires OAuth scope '{scope_str}'. "
                        f"Set GMA_SCOPE to include '{scope_str}' "
                        f"or use 'tier:{scope_tier}' shorthand."
                    ),
                    "scope_required": scope_str,
                    "scope_tier": scope_tier,
                    "granted_scopes": granted,
                }, indent=2)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
