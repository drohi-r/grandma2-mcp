"""
Credential Resolver — OAuth scope tier → console user credentials

Maps the effective OAuth scope tier to a console user whose rights level
matches or is more restrictive, implementing the monotonic restriction
principle:

    Console Rights ≤ OAuth Scope Tier (in terms of privilege level)

This ensures the grandMA2 console itself enforces permissions as an
irrevocable floor — even if the MCP layer has a bug, the console will
reject commands that exceed the Telnet user's native rights level.

Bootstrap user mapping (created by scripts/bootstrap_console_users.py):
    Tier 0 → guest          rights=0  (view only, no programmer)
    Tier 1 → operator       rights=1  (playback, no store)
    Tier 2 → presets_editor rights=2  (update existing presets only)
    Tier 3 → programmer     rights=3  (full show programming)
    Tier 4 → tech_director  rights=4  (setup, patch, fixture import)
    Tier 5 → administrator  rights=5  (full admin, show load, users)

Each username and password can be overridden via environment variables
(same vars used by bootstrap_console_users.py).

Single-user override
--------------------
When ``GMA_USER`` is set in the environment, it is used directly for ALL
operators, bypassing the tier-based mapping.  This preserves full backwards
compatibility with existing single-user deployments.
"""

from __future__ import annotations

import os

# ── Tier → credential table ───────────────────────────────────────────────────
#
# Each entry: (user_env_var, password_env_var, default_username, default_password)
# Env vars let operators override individual credentials without touching code.

_TIER_CREDENTIALS: dict[int, tuple[str, str, str, str]] = {
    0: ("GMA_GUEST_USER",      "GMA_GUEST_PASSWORD",      "guest",          ""),
    1: ("GMA_OPERATOR_USER",   "GMA_OPERATOR_PASSWORD",   "operator",       "operator"),
    2: ("GMA_PRESETS_USER",    "GMA_PRESETS_PASSWORD",    "presets_editor", "presets"),
    3: ("GMA_PROGRAMMER_USER", "GMA_PROGRAMMER_PASSWORD", "programmer",     "programmer"),
    4: ("GMA_TECH_DIR_USER",   "GMA_TECH_DIR_PASSWORD",   "tech_director",  "techdir"),
    5: ("GMA_ADMIN_USER",      "GMA_ADMIN_PASSWORD",      "administrator",  "admin"),
}


def resolve_console_credentials(scopes: frozenset[str] | set[str] | None = None) -> tuple[str, str]:
    """
    Return ``(username, password)`` for the console user that corresponds to
    the effective OAuth scope tier.

    Parameters
    ----------
    scopes:
        Granted OAuth scope strings.  When ``None``, calls
        ``get_granted_scopes()`` from ``src.auth``.

    Returns
    -------
    tuple[str, str]
        ``(username, password)`` ready to pass to ``GMA2TelnetClient``.
    """
    # Single-user override — backwards-compatible with existing .env files
    # that set GMA_USER=administrator.
    explicit_user = os.getenv("GMA_USER")
    if explicit_user:
        return explicit_user, os.getenv("GMA_PASSWORD", "")

    if scopes is None:
        from .auth import get_granted_scopes
        scopes = get_granted_scopes()

    tier = _max_tier(scopes)
    user_env, pw_env, default_user, default_pw = _TIER_CREDENTIALS[tier]
    return os.getenv(user_env, default_user), os.getenv(pw_env, default_pw)


def get_operator_identity(scopes: frozenset[str] | set[str] | None = None) -> str:
    """
    Return the operator identity string used as the session pool key.

    Stub mode (no IdP)
    ------------------
    * ``GMA_USER`` set → that username is the identity (single-operator mode,
      full backwards compatibility).
    * ``GMA_USER`` unset → ``"tier:<N>"`` derived from the effective scope tier
      (tier-matched multi-session mode).

    OAuth mode (future)
    -------------------
    Replace this function's body with JWT ``sub`` claim extraction.
    """
    explicit_user = os.getenv("GMA_USER")
    if explicit_user:
        return explicit_user

    if scopes is None:
        from .auth import get_granted_scopes
        scopes = get_granted_scopes()

    return f"tier:{_max_tier(scopes)}"


# ── Internal helpers ──────────────────────────────────────────────────────────


def _max_tier(scopes: frozenset[str] | set[str]) -> int:
    """Return the highest scope tier represented in *scopes* (0–5)."""
    from .commands.constants import OAUTH_TIER_SCOPES

    for tier in range(5, -1, -1):
        for scope in OAUTH_TIER_SCOPES[tier]:
            if str(scope) in scopes:
                return tier
    return 0
