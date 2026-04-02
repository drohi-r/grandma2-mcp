"""
Tests for the grandMA2 console navigation module.

Uses mocked telnet client to avoid real network connections.
Tests navigate(), get_current_location(), and list_destination().
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.navigation import (
    NavigationResult,
    get_current_location,
    list_destination,
    navigate,
)
from src.prompt_parser import ConsolePrompt

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def mock_client():
    """Create a mock GMA2TelnetClient with async send_command_with_response."""
    client = MagicMock()
    client.send_command_with_response = AsyncMock()
    return client


# =========================================================================
# NavigationResult dataclass
# =========================================================================


class TestNavigationResult:
    def test_construction(self):
        result = NavigationResult(
            command_sent="cd /",
            raw_response="[Root]>",
            parsed_prompt=ConsolePrompt(raw_response="[Root]>"),
            success=True,
        )
        assert result.command_sent == "cd /"
        assert result.success is True

    def test_default_success_is_none(self):
        result = NavigationResult(
            command_sent="cd /",
            raw_response="",
            parsed_prompt=ConsolePrompt(raw_response=""),
        )
        assert result.success is None


# =========================================================================
# navigate()
# =========================================================================


class TestNavigate:
    @pytest.mark.asyncio
    async def test_navigate_to_root(self, mock_client):
        mock_client.send_command_with_response.return_value = "[Root]>"

        result = await navigate(mock_client, "/")

        mock_client.send_command_with_response.assert_called_once_with(
            "cd /", timeout=2.0, delay=0.3
        )
        assert result.command_sent == "cd /"
        assert result.parsed_prompt.location == "Root"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_navigate_up(self, mock_client):
        mock_client.send_command_with_response.return_value = "[Root]>"

        result = await navigate(mock_client, "..")

        mock_client.send_command_with_response.assert_called_once_with(
            "cd ..", timeout=2.0, delay=0.3
        )
        assert result.command_sent == "cd .."

    @pytest.mark.asyncio
    async def test_navigate_to_object_dot_notation(self, mock_client):
        """cd Group.1 — dot notation for object type + ID."""
        mock_client.send_command_with_response.return_value = "[Group.1]>"

        result = await navigate(mock_client, "Group", 1)

        mock_client.send_command_with_response.assert_called_once_with(
            "cd Group.1", timeout=2.0, delay=0.3
        )
        assert result.command_sent == "cd Group.1"
        assert result.parsed_prompt.object_type == "Group"
        assert result.parsed_prompt.object_id == "1"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_navigate_by_index(self, mock_client):
        mock_client.send_command_with_response.return_value = "[Sequence 5]>"

        result = await navigate(mock_client, "5")

        mock_client.send_command_with_response.assert_called_once_with(
            "cd 5", timeout=2.0, delay=0.3
        )
        assert result.command_sent == "cd 5"

    @pytest.mark.asyncio
    async def test_navigate_empty_response(self, mock_client):
        mock_client.send_command_with_response.return_value = ""

        result = await navigate(mock_client, "/")

        assert result.success is None
        assert result.raw_response == ""

    @pytest.mark.asyncio
    async def test_navigate_unparseable_response(self, mock_client):
        mock_client.send_command_with_response.return_value = "Error: unknown command"

        result = await navigate(mock_client, "BadTarget")

        assert result.raw_response == "Error: unknown command"
        assert result.success is None

    @pytest.mark.asyncio
    async def test_navigate_custom_timeout(self, mock_client):
        mock_client.send_command_with_response.return_value = "[Root]>"

        await navigate(mock_client, "/", timeout=5.0, delay=1.0)

        mock_client.send_command_with_response.assert_called_once_with(
            "cd /", timeout=5.0, delay=1.0
        )

    @pytest.mark.asyncio
    async def test_navigate_preserves_raw(self, mock_client):
        raw = "OK\nSome info\n[Group.1]>"
        mock_client.send_command_with_response.return_value = raw

        result = await navigate(mock_client, "Group", 1)

        assert result.raw_response == raw
        assert result.parsed_prompt.raw_response == raw


# =========================================================================
# get_current_location()
# =========================================================================


class TestGetCurrentLocation:
    @pytest.mark.asyncio
    async def test_with_prompt(self, mock_client):
        mock_client.send_command_with_response.return_value = "[Group 1]>"

        result = await get_current_location(mock_client)

        mock_client.send_command_with_response.assert_called_once_with(
            "", timeout=2.0, delay=0.3
        )
        assert result.command_sent == ""
        assert result.parsed_prompt.location == "Group 1"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_client):
        mock_client.send_command_with_response.return_value = ""

        result = await get_current_location(mock_client)

        assert result.success is None

    @pytest.mark.asyncio
    async def test_custom_timeout(self, mock_client):
        mock_client.send_command_with_response.return_value = "[Root]>"

        await get_current_location(mock_client, timeout=5.0, delay=1.0)

        mock_client.send_command_with_response.assert_called_once_with(
            "", timeout=5.0, delay=1.0
        )

    @pytest.mark.asyncio
    async def test_root_prompt(self, mock_client):
        mock_client.send_command_with_response.return_value = "[channel]>"

        result = await get_current_location(mock_client)

        assert result.parsed_prompt.location == "channel"
        assert result.success is True


# =========================================================================
# list_destination()
# =========================================================================


class TestListDestination:
    @pytest.mark.asyncio
    async def test_list_all(self, mock_client):
        """list (no args) at current destination."""
        mock_client.send_command_with_response.return_value = (
            "Group.1  Front Wash\nGroup.2  Back Wash\n[Group]>"
        )

        result = await list_destination(mock_client)

        mock_client.send_command_with_response.assert_called_once_with(
            "list", timeout=2.0, delay=0.3
        )
        assert result.command_sent == "list"
        assert len(result.parsed_list.entries) == 2
        assert result.parsed_list.entries[0].object_type == "Group"
        assert result.parsed_list.entries[0].object_id == "1"
        assert result.parsed_list.entries[0].name == "Front Wash"

    @pytest.mark.asyncio
    async def test_list_with_object_type(self, mock_client):
        """list group — filtered by object type."""
        mock_client.send_command_with_response.return_value = (
            "Group.1  Front Wash\nGroup.2  Back Wash"
        )

        result = await list_destination(mock_client, "group")

        mock_client.send_command_with_response.assert_called_once_with(
            "list group", timeout=2.0, delay=0.3
        )
        assert result.command_sent == "list group"
        assert len(result.parsed_list.entries) == 2

    @pytest.mark.asyncio
    async def test_list_empty_response(self, mock_client):
        """No objects at destination."""
        mock_client.send_command_with_response.return_value = ""

        result = await list_destination(mock_client)

        assert len(result.parsed_list.entries) == 0

    @pytest.mark.asyncio
    async def test_list_bare_ids(self, mock_client):
        """List output with bare IDs (inside a typed pool)."""
        mock_client.send_command_with_response.return_value = (
            "1  Front Wash\n2  Back Wash\n3  Sides"
        )

        result = await list_destination(mock_client)

        assert len(result.parsed_list.entries) == 3
        assert result.parsed_list.entries[0].object_type is None
        assert result.parsed_list.entries[0].object_id == "1"
        assert result.parsed_list.entries[0].name == "Front Wash"

    @pytest.mark.asyncio
    async def test_list_custom_timeout(self, mock_client):
        mock_client.send_command_with_response.return_value = ""

        await list_destination(mock_client, timeout=5.0, delay=1.0)

        mock_client.send_command_with_response.assert_called_once_with(
            "list", timeout=5.0, delay=1.0
        )

    @pytest.mark.asyncio
    async def test_list_preserves_raw(self, mock_client):
        raw = "Group.1  Front Wash\nGroup.2  Back"
        mock_client.send_command_with_response.return_value = raw

        result = await list_destination(mock_client)

        assert result.raw_response == raw
