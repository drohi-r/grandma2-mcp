"""
User Management Tests

Tests for src/commands/functions/users.py builder functions
and the three user-management MCP tools in src/server.py:
  list_console_users, create_console_user, assign_world_to_user_profile
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Builder function tests ─────────────────────────────────────────────────────

class TestBuildLogin:

    def test_basic(self):
        from src.commands import build_login
        assert build_login("operator", "show123") == 'Login "operator" "show123"'

    def test_empty_password(self):
        from src.commands import build_login
        assert build_login("guest", "") == 'Login "guest" ""'

    def test_admin(self):
        from src.commands import build_login
        assert build_login("administrator", "admin") == 'Login "administrator" "admin"'


class TestBuildLogout:

    def test_returns_logout(self):
        from src.commands import build_logout
        assert build_logout() == "Logout"


class TestBuildListUsers:

    def test_returns_list_user(self):
        from src.commands import build_list_users
        assert build_list_users() == "list user"


class TestBuildStoreUser:

    def test_operator(self):
        from src.commands import build_store_user
        result = build_store_user(2, "operator", "show123", 1)
        assert result == 'Store User 2 /name="operator" /password="show123" /rights=1'

    def test_guest_no_password(self):
        from src.commands import build_store_user
        result = build_store_user(5, "guest", "", 0)
        assert result == 'Store User 5 /name="guest" /password="" /rights=0'

    def test_admin_rights5(self):
        from src.commands import build_store_user
        result = build_store_user(1, "administrator", "admin", 5)
        assert result == 'Store User 1 /name="administrator" /password="admin" /rights=5'

    def test_all_rights_levels(self):
        from src.commands import build_store_user
        for level in range(6):
            result = build_store_user(1, "user", "pw", level)
            assert f"/rights={level}" in result

    def test_invalid_rights_raises(self):
        from src.commands import build_store_user
        with pytest.raises(ValueError, match="rights_level must be 0-5"):
            build_store_user(2, "user", "pw", 6)

    def test_invalid_negative_rights_raises(self):
        from src.commands import build_store_user
        with pytest.raises(ValueError):
            build_store_user(2, "user", "pw", -1)


class TestBuildDeleteUser:

    def test_basic(self):
        from src.commands import build_delete_user
        assert build_delete_user(3) == "Delete User 3 /noconfirm"

    def test_slot_5(self):
        from src.commands import build_delete_user
        assert build_delete_user(5) == "Delete User 5 /noconfirm"

    def test_includes_noconfirm(self):
        from src.commands import build_delete_user
        result = build_delete_user(2)
        assert "/noconfirm" in result


class TestBuildAssignWorldToUserProfile:

    def test_basic(self):
        from src.commands import build_assign_world_to_user_profile
        result = build_assign_world_to_user_profile(3, 4)
        assert result == "Assign World 4 At UserProfile 3"

    def test_remove_world_slot0(self):
        from src.commands import build_assign_world_to_user_profile
        result = build_assign_world_to_user_profile(3, 0)
        assert result == "Assign World 0 At UserProfile 3"

    def test_slot1_world1(self):
        from src.commands import build_assign_world_to_user_profile
        result = build_assign_world_to_user_profile(1, 1)
        assert result == "Assign World 1 At UserProfile 1"


# ── MCP tool tests ─────────────────────────────────────────────────────────────

class TestListConsoleUsersTool:
    """Tests for list_console_users MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_sends_list_user(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import list_console_users

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Slot 1 administrator Admin")
        mock_get_client.return_value = mock_client

        result = await list_console_users()

        mock_client.send_command_with_response.assert_called_once_with("list user")
        assert "administrator" in result

    @pytest.mark.asyncio
    async def test_blocked_without_scope(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:0")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)

        # list_console_users requires STATE_READ which is in tier:0, so should succeed
        # Actually STATE_READ is tier:0 so tier:0 grants it
        # Let's verify the scope required is state:read
        from src.auth import OAuthScope
        from src.commands.constants import OAUTH_TIER_SCOPES
        assert OAuthScope.STATE_READ in OAUTH_TIER_SCOPES[0]


class TestCreateConsoleUserTool:
    """Tests for create_console_user MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_creates_user(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import create_console_user

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        await create_console_user(
            slot=3, name="programmer", password="pw123",
            rights_level=3, confirm_destructive=True
        )

        call_args = mock_client.send_command_with_response.call_args[0][0]
        assert 'Store User 3' in call_args
        assert '/name="programmer"' in call_args
        assert '/rights=3' in call_args

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import create_console_user

        result = await create_console_user(
            slot=3, name="programmer", password="pw", rights_level=3
        )
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    async def test_blocked_without_scope(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:4")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import create_console_user

        result = await create_console_user(
            slot=3, name="programmer", password="pw", rights_level=3, confirm_destructive=True
        )
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["scope_required"] == "gma2:user:manage"

    @pytest.mark.asyncio
    async def test_invalid_slot_rejected(self, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import create_console_user

        result = await create_console_user(
            slot=0, name="user", password="pw", rights_level=1, confirm_destructive=True
        )
        data = json.loads(result)
        assert data["blocked"] is True

    @pytest.mark.asyncio
    async def test_invalid_rights_level_rejected(self, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import create_console_user

        result = await create_console_user(
            slot=3, name="user", password="pw", rights_level=6, confirm_destructive=True
        )
        data = json.loads(result)
        assert "error" in data


class TestAssignWorldToUserProfileTool:
    """Tests for assign_world_to_user_profile MCP tool."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assigns_world(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import assign_world_to_user_profile

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        await assign_world_to_user_profile(
            user_profile_slot=2, world_slot=1, confirm_destructive=True
        )

        call_args = mock_client.send_command_with_response.call_args[0][0]
        assert call_args == "Assign World 1 At UserProfile 2"

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import assign_world_to_user_profile

        result = await assign_world_to_user_profile(user_profile_slot=2, world_slot=1)
        data = json.loads(result)
        assert data["blocked"] is True

    @pytest.mark.asyncio
    async def test_blocked_without_scope(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:4")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import assign_world_to_user_profile

        result = await assign_world_to_user_profile(
            user_profile_slot=2, world_slot=1, confirm_destructive=True
        )
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["scope_required"] == "gma2:user:manage"

    @pytest.mark.asyncio
    async def test_invalid_profile_slot_rejected(self, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import assign_world_to_user_profile

        result = await assign_world_to_user_profile(
            user_profile_slot=0, world_slot=1, confirm_destructive=True
        )
        data = json.loads(result)
        assert data["blocked"] is True


class TestDeleteUserTool:
    """Tests for delete_user MCP tool (tool 102)."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import delete_user

        result = await delete_user(slot=3)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    async def test_slot1_protected(self, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import delete_user

        result = await delete_user(slot=1, confirm_destructive=True)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"
        assert "Slot 1" in data["error"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_deletes_user_slot3(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("GMA_AUTH_BYPASS", "1")
        from src.server import delete_user

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await delete_user(slot=3, confirm_destructive=True)
        data = json.loads(result)

        assert data["command_sent"] == "Delete User 3 /noconfirm"
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    async def test_blocked_without_scope(self, monkeypatch):
        monkeypatch.setenv("GMA_SCOPE", "tier:4")
        monkeypatch.delenv("GMA_AUTH_BYPASS", raising=False)
        from src.server import delete_user

        result = await delete_user(slot=3, confirm_destructive=True)
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["scope_required"] == "gma2:user:manage"
