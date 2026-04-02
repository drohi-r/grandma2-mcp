"""Tests for src/credentials.py — OAuth tier → console credential resolver."""

import os
from unittest.mock import patch


class TestResolveConsoleCredentials:
    """Tests for resolve_console_credentials()."""

    def test_gma_user_override_returns_explicit_creds(self):
        """GMA_USER env var bypasses tier logic entirely."""
        from src.credentials import resolve_console_credentials

        with patch.dict(os.environ, {"GMA_USER": "myuser", "GMA_PASSWORD": "mypass"}):
            user, pw = resolve_console_credentials()

        assert user == "myuser"
        assert pw == "mypass"

    def test_gma_user_override_empty_password(self):
        """GMA_USER with no GMA_PASSWORD returns empty string for password."""
        from src.credentials import resolve_console_credentials

        env = {"GMA_USER": "admin"}
        env.pop("GMA_PASSWORD", None)
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("GMA_PASSWORD", None)
            user, pw = resolve_console_credentials()

        assert user == "admin"
        assert pw == ""

    def test_tier_0_returns_guest(self):
        """Tier 0 (empty scopes) returns guest/empty password."""
        from src.credentials import resolve_console_credentials

        env = {}
        for key in ("GMA_USER", "GMA_GUEST_USER", "GMA_GUEST_PASSWORD"):
            env[key] = ""  # ensure not set
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GMA_USER", None)
            user, pw = resolve_console_credentials(scopes=frozenset())

        assert user == "guest"
        assert pw == ""

    def test_tier_5_returns_administrator(self):
        """Tier 5 scopes → administrator credentials by default."""
        from src.commands.constants import OAUTH_TIER_SCOPES
        from src.credentials import resolve_console_credentials

        tier5_scopes = {str(s) for s in OAUTH_TIER_SCOPES[5]}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GMA_USER", None)
            os.environ.pop("GMA_ADMIN_USER", None)
            os.environ.pop("GMA_ADMIN_PASSWORD", None)
            user, pw = resolve_console_credentials(scopes=tier5_scopes)

        assert user == "administrator"
        assert pw == "admin"

    def test_tier_3_returns_programmer(self):
        """Tier 3 scopes → programmer credentials."""
        from src.commands.constants import OAUTH_TIER_SCOPES
        from src.credentials import resolve_console_credentials

        tier3_scopes = {str(s) for s in OAUTH_TIER_SCOPES[3]}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GMA_USER", None)
            os.environ.pop("GMA_PROGRAMMER_USER", None)
            os.environ.pop("GMA_PROGRAMMER_PASSWORD", None)
            user, pw = resolve_console_credentials(scopes=tier3_scopes)

        assert user == "programmer"
        assert pw == "programmer"

    def test_env_var_overrides_default_username(self):
        """GMA_PROGRAMMER_USER overrides the default programmer username."""
        from src.commands.constants import OAUTH_TIER_SCOPES
        from src.credentials import resolve_console_credentials

        tier3_scopes = {str(s) for s in OAUTH_TIER_SCOPES[3]}
        with patch.dict(os.environ, {"GMA_PROGRAMMER_USER": "custom_prog"}, clear=False):
            os.environ.pop("GMA_USER", None)
            user, _ = resolve_console_credentials(scopes=tier3_scopes)

        assert user == "custom_prog"

    def test_accepts_set_type_scopes(self):
        """resolve_console_credentials accepts plain set[str] in addition to frozenset."""
        from src.credentials import resolve_console_credentials

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GMA_USER", None)
            # Should not raise TypeError
            user, _ = resolve_console_credentials(scopes=set())

        assert user == "guest"


class TestGetOperatorIdentity:
    """Tests for get_operator_identity()."""

    def test_gma_user_returns_that_username(self):
        """When GMA_USER is set, identity equals that username."""
        from src.credentials import get_operator_identity

        with patch.dict(os.environ, {"GMA_USER": "operator"}):
            identity = get_operator_identity()

        assert identity == "operator"

    def test_no_gma_user_returns_tier_string(self):
        """Without GMA_USER, identity is 'tier:N'."""
        from src.credentials import get_operator_identity

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GMA_USER", None)
            identity = get_operator_identity(scopes=frozenset())

        assert identity == "tier:0"

    def test_tier5_identity(self):
        """Tier 5 scopes produce 'tier:5' identity."""
        from src.commands.constants import OAUTH_TIER_SCOPES
        from src.credentials import get_operator_identity

        tier5_scopes = {str(s) for s in OAUTH_TIER_SCOPES[5]}
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GMA_USER", None)
            identity = get_operator_identity(scopes=tier5_scopes)

        assert identity == "tier:5"

    def test_accepts_set_type(self):
        """get_operator_identity accepts plain set[str]."""
        from src.credentials import get_operator_identity

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GMA_USER", None)
            identity = get_operator_identity(scopes=set())

        assert identity.startswith("tier:")


class TestMaxTier:
    """Tests for _max_tier()."""

    def test_empty_scopes_returns_0(self):
        from src.credentials import _max_tier

        assert _max_tier(frozenset()) == 0

    def test_tier5_scope_returns_5(self):
        from src.commands.constants import OAUTH_TIER_SCOPES
        from src.credentials import _max_tier

        tier5_scopes = frozenset(str(s) for s in OAUTH_TIER_SCOPES[5])
        assert _max_tier(tier5_scopes) == 5

    def test_mixed_scopes_returns_highest(self):
        """When scopes from multiple tiers are present, returns the highest tier."""
        from src.commands.constants import OAUTH_TIER_SCOPES
        from src.credentials import _max_tier

        mixed = frozenset(
            str(s) for tier in (1, 3) for s in OAUTH_TIER_SCOPES[tier]
        )
        assert _max_tier(mixed) == 3

    def test_accepts_plain_set(self):
        from src.credentials import _max_tier

        # Should not raise TypeError with a plain set
        result = _max_tier(set())
        assert result == 0
