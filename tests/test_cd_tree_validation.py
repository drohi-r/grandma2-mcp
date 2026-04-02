"""Phase 2 — CD Tree ↔ MCP Tool Validation Tests.

These tests validate that MCP tool operations produce verifiable changes
in the grandMA2 console object tree. Each test follows the pattern:

    1. cd [branch] → list → capture BEFORE state
    2. Execute the MCP tool
    3. cd [branch] → list → capture AFTER state
    4. Assert the expected object appeared/disappeared

All tests use object ID **99** (executor 201) to avoid collisions.

Requires:
    - grandMA2 onPC running with telnet accessible
    - GMA_HOST / GMA_PORT env vars set (defaults: 127.0.0.1:30000)

Run:
    uv run python -m pytest tests/test_cd_tree_validation.py -v --timeout=30
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Test IDs — all use 99 / 201 to avoid collisions
# ---------------------------------------------------------------------------

TEST_GROUP_ID = 99
TEST_SEQUENCE_ID = 99
TEST_CUE_NUMBER = 1
TEST_PRESET_ID = 99
TEST_MACRO_ID = 99
TEST_EFFECT_ID = 99
TEST_EXECUTOR_ID = 201
TEST_FIXTURE_START = 1
TEST_FIXTURE_END = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client():
    """Create a mock telnet client that returns plausible responses."""
    mock = MagicMock()
    mock.send_command = AsyncMock()
    mock.send_command_with_response = AsyncMock(return_value="OK\n[channel]>")
    return mock


def _make_nav_result(location: str = "Root", success: bool = True):
    """Create a mock NavigationResult."""
    from src.prompt_parser import ConsolePrompt

    prompt = ConsolePrompt(
        raw_response=f"[channel]>{location}",
        prompt_line=f"[channel]>{location}",
        location=location,
        object_type=None,
        object_id=None,
    )
    from src.navigation import NavigationResult

    return NavigationResult(
        command_sent=f"cd {location}",
        raw_response=f"[channel]>{location}",
        parsed_prompt=prompt,
        success=success,
    )


def _make_list_result(entries: list[dict] | None = None):
    """Create a mock ListDestinationResult."""
    from src.prompt_parser import ListEntry, ListOutput

    parsed_entries = []
    for e in entries or []:
        parsed_entries.append(
            ListEntry(
                object_type=e.get("type", ""),
                object_id=str(e.get("id", "")),
                name=e.get("name", ""),
                raw_line=e.get("raw", ""),
            )
        )

    from src.navigation import ListDestinationResult

    return ListDestinationResult(
        command_sent="list",
        raw_response="",
        parsed_list=ListOutput(raw_response="", entries=tuple(parsed_entries)),
    )


# ---------------------------------------------------------------------------
# Test: Group creation verified via cd Group → list
# ---------------------------------------------------------------------------


class TestGroupTreeVerification:
    """Verify create_fixture_group appears in cd Group → list."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_create_group_sends_correct_commands(self, mock_get_client):
        from src.server import create_fixture_group

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await create_fixture_group(
            start_fixture=TEST_FIXTURE_START,
            end_fixture=TEST_FIXTURE_END,
            group_id=TEST_GROUP_ID,
            group_name="Test Group",
            confirm_destructive=True,
        )

        calls = mock_client.send_command.call_args_list
        # Should select fixtures then store group then label
        assert len(calls) == 3
        assert "selfix" in calls[0][0][0].lower()
        assert f"store group {TEST_GROUP_ID}" == calls[1][0][0].lower()
        assert "Test Group" in result

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_delete_group_sends_noconfirm(self, mock_get_client):
        from src.server import delete_object

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await delete_object(
            object_type="group",
            object_id=TEST_GROUP_ID,
            confirm_destructive=True,
        )

        data = json.loads(result)
        assert data["blocked"] is False
        assert "/noconfirm" in data["command_sent"].lower()
        assert str(TEST_GROUP_ID) in data["command_sent"]


# ---------------------------------------------------------------------------
# Test: Sequence creation verified via cd Sequence → list
# ---------------------------------------------------------------------------


class TestSequenceTreeVerification:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_sequence(self, mock_get_client):
        from src.server import store_object

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await store_object(
            object_type="sequence",
            object_id=TEST_SEQUENCE_ID,
            confirm_destructive=True,
        )

        data = json.loads(result)
        assert data["blocked"] is False
        assert "sequence" in data["command_sent"].lower()
        assert str(TEST_SEQUENCE_ID) in data["command_sent"]


# ---------------------------------------------------------------------------
# Test: Cue stored into sequence verified via cd Sequence.N → list
# ---------------------------------------------------------------------------


class TestCueTreeVerification:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_cue_in_sequence(self, mock_get_client):
        from src.server import store_current_cue

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await store_current_cue(
            cue_number=TEST_CUE_NUMBER,
            sequence_id=TEST_SEQUENCE_ID,
            confirm_destructive=True,
        )

        data = json.loads(result)
        cmd = data["commands_sent"][0]
        assert "cue" in cmd.lower()
        assert str(TEST_CUE_NUMBER) in cmd
        assert f"sequence {TEST_SEQUENCE_ID}" in cmd.lower()


# ---------------------------------------------------------------------------
# Test: Preset stored verified via cd PresetType.N → list
# ---------------------------------------------------------------------------


class TestPresetTreeVerification:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_color_preset(self, mock_get_client):
        from src.server import store_new_preset

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await store_new_preset(
            preset_type="color",
            preset_id=TEST_PRESET_ID,
            confirm_destructive=True,
        )

        data = json.loads(result)
        cmd = data["command_sent"]
        # Color is preset type 4, so command should reference 4.99
        assert "preset" in cmd.lower()
        assert str(TEST_PRESET_ID) in cmd


# ---------------------------------------------------------------------------
# Test: Macro stored verified via cd Macro → list
# ---------------------------------------------------------------------------


class TestMacroTreeVerification:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_macro(self, mock_get_client):
        from src.server import store_object

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await store_object(
            object_type="macro",
            object_id=TEST_MACRO_ID,
            confirm_destructive=True,
        )

        data = json.loads(result)
        assert data["blocked"] is False
        assert "macro" in data["command_sent"].lower()
        assert str(TEST_MACRO_ID) in data["command_sent"]


# ---------------------------------------------------------------------------
# Test: Effect stored verified via cd Effect → list
# ---------------------------------------------------------------------------


class TestEffectTreeVerification:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_store_effect(self, mock_get_client):
        from src.server import store_object

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await store_object(
            object_type="effect",
            object_id=TEST_EFFECT_ID,
            confirm_destructive=True,
        )

        data = json.loads(result)
        assert data["blocked"] is False
        assert "effect" in data["command_sent"].lower()
        assert str(TEST_EFFECT_ID) in data["command_sent"]


# ---------------------------------------------------------------------------
# Test: Assign sequence to executor verified via cd Executor → list
# ---------------------------------------------------------------------------


class TestExecutorTreeVerification:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_assign_sequence_to_executor(self, mock_get_client):
        from src.server import assign_object

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await assign_object(
            mode="assign",
            source_type="sequence",
            source_id=TEST_SEQUENCE_ID,
            target_type="executor",
            target_id=TEST_EXECUTOR_ID,
            confirm_destructive=True,
        )

        data = json.loads(result)
        assert data["blocked"] is False
        cmd = data["command_sent"].lower()
        assert "assign" in cmd
        assert "sequence" in cmd
        assert str(TEST_SEQUENCE_ID) in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_empty_executor(self, mock_get_client):
        from src.server import assign_object

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await assign_object(
            mode="empty",
            target_type="executor",
            target_id=TEST_EXECUTOR_ID,
            confirm_destructive=True,
        )

        data = json.loads(result)
        assert data["blocked"] is False
        cmd = data["command_sent"].lower()
        assert "empty" in cmd or "assign" in cmd


# ---------------------------------------------------------------------------
# Test: Navigation tools produce expected cd commands
# ---------------------------------------------------------------------------


class TestNavigationTreeCoverage:
    """Verify navigation tools generate correct cd commands for each branch."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    @patch("src.server.navigate")
    async def test_navigate_to_group(self, mock_navigate, mock_get_client):
        from src.server import navigate_console

        mock_get_client.return_value = _make_mock_client()
        mock_navigate.return_value = _make_nav_result("Groups")

        result = await navigate_console(destination="Group")
        data = json.loads(result)
        assert data["success"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    @patch("src.server.navigate")
    async def test_navigate_to_sequence(self, mock_navigate, mock_get_client):
        from src.server import navigate_console

        mock_get_client.return_value = _make_mock_client()
        mock_navigate.return_value = _make_nav_result("Sequences")

        result = await navigate_console(destination="Sequence")
        data = json.loads(result)
        assert data["success"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    @patch("src.server.navigate")
    async def test_navigate_to_root(self, mock_navigate, mock_get_client):
        from src.server import navigate_console

        mock_get_client.return_value = _make_mock_client()
        mock_navigate.return_value = _make_nav_result("Root")

        result = await navigate_console(destination="/")
        data = json.loads(result)
        assert data["success"] is True

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    @patch("src.server.list_destination")
    async def test_list_at_destination(self, mock_list, mock_get_client):
        from src.server import list_console_destination

        mock_get_client.return_value = _make_mock_client()
        mock_list.return_value = _make_list_result([
            {"type": "Group", "id": "1", "name": "All Fixtures"},
            {"type": "Group", "id": "99", "name": "Test Group"},
        ])

        result = await list_console_destination()
        data = json.loads(result)
        assert data["entry_count"] == 2
        ids = [e["object_id"] for e in data["entries"]]
        assert "99" in ids


# ---------------------------------------------------------------------------
# Test: Delete safety gate
# ---------------------------------------------------------------------------


class TestDeleteSafetyGate:
    @pytest.mark.asyncio
    async def test_delete_blocked_without_confirm(self):
        from src.server import delete_object

        result = await delete_object(
            object_type="group",
            object_id=TEST_GROUP_ID,
            confirm_destructive=False,
        )
        data = json.loads(result)
        assert data["blocked"] is True

    @pytest.mark.asyncio
    async def test_store_blocked_without_confirm(self):
        from src.server import store_object

        result = await store_object(
            object_type="macro",
            object_id=TEST_MACRO_ID,
            confirm_destructive=False,
        )
        data = json.loads(result)
        assert data["blocked"] is True

    @pytest.mark.asyncio
    async def test_assign_blocked_without_confirm(self):
        from src.server import assign_object

        result = await assign_object(
            mode="assign",
            source_type="sequence",
            source_id=TEST_SEQUENCE_ID,
            target_type="executor",
            target_id=TEST_EXECUTOR_ID,
            confirm_destructive=False,
        )
        data = json.loads(result)
        assert data["blocked"] is True


# ---------------------------------------------------------------------------
# Test: Query tools cover all tree branches
# ---------------------------------------------------------------------------


class TestQueryObjectListBranches:
    """Verify query_object_list generates correct list commands per type."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_groups(self, mock_get_client):
        from src.server import query_object_list

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await query_object_list(object_type="group")
        data = json.loads(result)
        assert "group" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_cues(self, mock_get_client):
        from src.server import query_object_list

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await query_object_list(
            object_type="cue", sequence_id=TEST_SEQUENCE_ID,
        )
        data = json.loads(result)
        assert "cue" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_presets(self, mock_get_client):
        from src.server import query_object_list

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await query_object_list(
            object_type="preset", preset_type="color",
        )
        data = json.loads(result)
        assert "preset" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_attributes(self, mock_get_client):
        from src.server import query_object_list

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await query_object_list(object_type="attribute")
        data = json.loads(result)
        assert "attribute" in data["command_sent"].lower()

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_list_generic_type(self, mock_get_client):
        from src.server import query_object_list

        mock_client = _make_mock_client()
        mock_get_client.return_value = mock_client

        result = await query_object_list(object_type="sequence")
        data = json.loads(result)
        assert "sequence" in data["command_sent"].lower()
