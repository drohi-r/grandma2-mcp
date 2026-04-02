"""
OAuth 2.1 Scope Enforcement Tests

Tests for src/auth.py — scope parsing, expansion, checking, and the
@require_scope decorator.
"""

import json

import pytest


class TestOAuthScopeEnum:
    """Verify all 20 OAuth scope strings are correct."""

    def test_tier0_scopes(self):
        from src.commands.constants import OAuthScope
        assert str(OAuthScope.DISCOVER) == "gma2:discover"
        assert str(OAuthScope.STATE_READ) == "gma2:state:read"

    def test_tier1_scopes(self):
        from src.commands.constants import OAuthScope
        assert str(OAuthScope.PLAYBACK_GO) == "gma2:playback:go"
        assert str(OAuthScope.EXECUTOR_CTRL) == "gma2:executor:control"

    def test_tier2_scopes(self):
        from src.commands.constants import OAuthScope
        assert str(OAuthScope.PROGRAMMER_WRITE) == "gma2:programmer:write"
        assert str(OAuthScope.PRESET_UPDATE) == "gma2:preset:update"

    def test_tier3_scopes(self):
        from src.commands.constants import OAuthScope
        assert str(OAuthScope.CUE_STORE) == "gma2:cue:store"
        assert str(OAuthScope.SEQUENCE_EDIT) == "gma2:sequence:edit"
        assert str(OAuthScope.GROUP_STORE) == "gma2:group:store"
        assert str(OAuthScope.MACRO_EDIT) == "gma2:macro:edit"
        assert str(OAuthScope.EFFECT_EDIT) == "gma2:effect:edit"
        assert str(OAuthScope.FILTER_MANAGE) == "gma2:filter:manage"

    def test_tier4_scopes(self):
        from src.commands.constants import OAuthScope
        assert str(OAuthScope.SETUP_CONSOLE) == "gma2:setup:console"
        assert str(OAuthScope.NETWORK_CONFIG) == "gma2:network:config"
        assert str(OAuthScope.PATCH_WRITE) == "gma2:patch:write"
        assert str(OAuthScope.FIXTURE_IMPORT) == "gma2:fixture:import"

    def test_tier5_scopes(self):
        from src.commands.constants import OAuthScope
        assert str(OAuthScope.USER_MANAGE) == "gma2:user:manage"
        assert str(OAuthScope.SESSION_MANAGE) == "gma2:session:manage"
        assert str(OAuthScope.SHOW_LOAD) == "gma2:show:load"
        assert str(OAuthScope.SYSTEM_ADMIN) == "gma2:system:admin"

    def test_total_scope_count(self):
        from src.auth import ALL_SCOPES
        assert len(ALL_SCOPES) == 20


class TestOAuthTierScopes:
    """Verify OAUTH_TIER_SCOPES has correct scope counts per tier."""

    def test_tier_counts(self):
        from src.commands.constants import OAUTH_TIER_SCOPES
        assert len(OAUTH_TIER_SCOPES[0]) == 2
        assert len(OAUTH_TIER_SCOPES[1]) == 2
        assert len(OAUTH_TIER_SCOPES[2]) == 2
        assert len(OAUTH_TIER_SCOPES[3]) == 6
        assert len(OAUTH_TIER_SCOPES[4]) == 4
        assert len(OAUTH_TIER_SCOPES[5]) == 4

    def test_all_tiers_present(self):
        from src.commands.constants import OAUTH_TIER_SCOPES
        assert set(OAUTH_TIER_SCOPES.keys()) == {0, 1, 2, 3, 4, 5}


class TestGetGrantedScopes:
    """Test GMA_SCOPE env var parsing."""

    def test_default_scopes(self, monkeypatch):
        monkeypatch.delenv("GMA_SCOPE", raising=False)
        from src.auth import get_granted_scopes
        scopes = get_granted_scopes()
        assert "gma2:discover" in scopes
        assert "gma2:state:read" in scopes
        # No tier 1+ scopes by default
        assert "gma2:playback:go" not in scopes

    def test_tier0_shorthand(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        from src.auth import get_granted_scopes
        scopes = get_granted_scopes()
        assert "gma2:discover" in scopes
        assert "gma2:state:read" in scopes
        assert "gma2:playback:go" not in scopes

    def test_tier1_shorthand_includes_tier0(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:1")
        from src.auth import get_granted_scopes
        scopes = get_granted_scopes()
        # Tier 1 cumulative includes tier 0
        assert "gma2:discover" in scopes
        assert "gma2:playback:go" in scopes
        # Does not include tier 2+
        assert "gma2:programmer:write" not in scopes

    def test_tier3_shorthand_cumulative(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:3")
        from src.auth import get_granted_scopes
        scopes = get_granted_scopes()
        # All tiers 0-3
        assert "gma2:discover" in scopes
        assert "gma2:playback:go" in scopes
        assert "gma2:programmer:write" in scopes
        assert "gma2:cue:store" in scopes
        # Not tier 4+
        assert "gma2:setup:console" not in scopes
        assert "gma2:user:manage" not in scopes

    def test_tier5_includes_all_20_scopes(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:5")
        from src.auth import ALL_SCOPES, get_granted_scopes
        scopes = get_granted_scopes()
        assert scopes == ALL_SCOPES
        assert len(scopes) == 20

    def test_single_explicit_scope(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "gma2:cue:store")
        from src.auth import get_granted_scopes
        scopes = get_granted_scopes()
        assert "gma2:cue:store" in scopes
        # Explicit scope does NOT auto-expand tiers
        assert "gma2:discover" not in scopes

    def test_multiple_explicit_scopes(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "gma2:playback:go gma2:executor:control")
        from src.auth import get_granted_scopes
        scopes = get_granted_scopes()
        assert "gma2:playback:go" in scopes
        assert "gma2:executor:control" in scopes
        assert "gma2:discover" not in scopes

    def test_mixed_tier_and_explicit(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:0 gma2:cue:store")
        from src.auth import get_granted_scopes
        scopes = get_granted_scopes()
        assert "gma2:discover" in scopes
        assert "gma2:cue:store" in scopes
        # Tier 1 scopes not included
        assert "gma2:playback:go" not in scopes

    def test_invalid_tier_does_not_crash(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:99 gma2:discover")
        from src.auth import get_granted_scopes
        # Should not raise, should return the explicit scope
        scopes = get_granted_scopes()
        assert "gma2:discover" in scopes


class TestHasScope:
    """Test the has_scope() boolean check."""

    def test_has_scope_when_granted(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:1")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.auth import has_scope
        from src.commands.constants import OAuthScope
        assert has_scope(OAuthScope.PLAYBACK_GO) is True

    def test_missing_scope(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:1")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.auth import has_scope
        from src.commands.constants import OAuthScope
        assert has_scope(OAuthScope.CUE_STORE) is False

    def test_bypass_mode_grants_all(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.auth import has_scope
        from src.commands.constants import OAuthScope
        assert has_scope(OAuthScope.USER_MANAGE) is True

    def test_string_scope_argument(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "gma2:cue:store")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.auth import has_scope
        assert has_scope("gma2:cue:store") is True
        assert has_scope("gma2:user:manage") is False


class TestRequireScopeDecorator:
    """Test the @require_scope async decorator."""

    @pytest.mark.asyncio
    async def test_allows_when_scope_granted(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:1")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.auth import require_scope
        from src.commands.constants import OAuthScope

        @require_scope(OAuthScope.PLAYBACK_GO)
        async def my_tool():
            return "success"

        result = await my_tool()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_blocks_when_scope_missing(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.auth import require_scope
        from src.commands.constants import OAuthScope

        @require_scope(OAuthScope.CUE_STORE)
        async def my_tool():
            return "success"

        result = await my_tool()
        assert result != "success"
        data = json.loads(result)
        assert data["blocked"] is True

    @pytest.mark.asyncio
    async def test_blocked_result_is_valid_json(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.auth import require_scope
        from src.commands.constants import OAuthScope

        @require_scope(OAuthScope.USER_MANAGE)
        async def my_tool():
            return "success"

        result = await my_tool()
        data = json.loads(result)
        assert "scope_required" in data
        assert data["scope_required"] == "gma2:user:manage"
        assert "scope_tier" in data
        assert data["scope_tier"] == 5
        assert "granted_scopes" in data

    @pytest.mark.asyncio
    async def test_preserves_function_name(self, monkeypatch):
        """functools.wraps must preserve the original function name."""
        monkeypatch.setenv("GMA_SCOPE", "tier:5")
        from src.auth import require_scope
        from src.commands.constants import OAuthScope

        @require_scope(OAuthScope.CUE_STORE)
        async def store_the_cue():
            return "ok"

        assert store_the_cue.__name__ == "store_the_cue"

    @pytest.mark.asyncio
    async def test_bypass_allows_all(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.auth import require_scope
        from src.commands.constants import OAuthScope

        @require_scope(OAuthScope.USER_MANAGE)
        async def admin_tool():
            return "admin_ok"

        result = await admin_tool()
        assert result == "admin_ok"

    @pytest.mark.asyncio
    async def test_error_message_includes_tool_name(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.auth import require_scope
        from src.commands.constants import OAuthScope

        @require_scope(OAuthScope.CUE_STORE)
        async def my_special_tool():
            return "ok"

        result = await my_special_tool()
        data = json.loads(result)
        assert "my_special_tool" in data["error"]


class TestScopeToTier:
    """Verify the reverse scope→tier lookup."""

    def test_tier0_scope_maps_to_0(self):
        from src.auth import _scope_to_tier
        assert _scope_to_tier("gma2:discover") == 0
        assert _scope_to_tier("gma2:state:read") == 0

    def test_tier3_scope_maps_to_3(self):
        from src.auth import _scope_to_tier
        assert _scope_to_tier("gma2:cue:store") == 3

    def test_tier5_scope_maps_to_5(self):
        from src.auth import _scope_to_tier
        assert _scope_to_tier("gma2:user:manage") == 5

    def test_unknown_scope_returns_minus1(self):
        from src.auth import _scope_to_tier
        assert _scope_to_tier("gma2:nonexistent:scope") == -1
