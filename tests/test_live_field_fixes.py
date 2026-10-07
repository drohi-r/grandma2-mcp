"""
Live checks for the 2026-10 reliability work against a real grandMA2 console.

Read-only part (safe on any show):
    uv run pytest tests/test_live_field_fixes.py --live -v -s

Destructive part — use a throwaway show; touches group 9999 and sequence 9999:
    uv run pytest tests/test_live_field_fixes.py --live --destructive -v -s
"""

from __future__ import annotations

import asyncio
import json

import pytest
import pytest_asyncio

from src.server import (
    delete_object,
    disconnect_console,
    get_client,
    list_agenda_events,
    list_console_users,
    list_filters,
    list_system_variables,
    list_timecode_events,
    list_timers,
    list_universes,
    list_worlds,
    query_object_list,
    run_command_batch,
    send_raw_command,
    set_sequence_property,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")

SCRATCH_GROUP = 9999
SCRATCH_SEQUENCE = 9999


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def live_client():
    client = await get_client()
    assert client is not None, "Failed to connect to grandMA2 console"
    yield client


def _show(data: dict) -> dict:
    print(json.dumps(data, indent=2)[:1500])
    return data


@pytest.mark.live
class TestRepliesTellTheTruth:
    async def test_unknown_command_is_reported_as_console_error(self, live_client):
        """Confirms the error detector matches the console's real wording."""
        data = _show(json.loads(await send_raw_command(command="zzqqxx")))
        assert data["ok"] is False
        assert data["console_errors"], "real console error text not recognised"

    async def test_clean_read_ends_in_a_prompt(self, live_client):
        """Confirms the prompt detector matches the real prompt (no cut-off warnings)."""
        data = _show(json.loads(await send_raw_command(command="List Sequence")))
        assert data["ok"] is True
        assert "transport_warnings" not in data

    async def test_concurrent_calls_each_get_their_own_reply(self, live_client):
        kinds = ["group", "sequence", "macro", "effect", "preset"]
        replies = await asyncio.gather(*[query_object_list(object_type=k) for k in kinds])
        for kind, reply in zip(kinds, replies, strict=True):
            data = json.loads(reply)
            assert data["ok"] is True, data
            assert kind in data["command_sent"].lower()
            assert data["raw_response"].lower().startswith(data["command_sent"].lower()[:8]), (
                f"{kind}: reply does not start at its own command echo"
            )

    async def test_read_only_batch(self, live_client):
        data = _show(json.loads(await run_command_batch(commands=["List Group", "List Sequence", "ListVar"])))
        assert data["ok"] is True
        assert data["executed"] == 3

    async def test_disconnect_then_reconnect(self, live_client):
        data = _show(json.loads(await disconnect_console()))
        assert data["sessions_closed"] >= 1
        again = json.loads(await list_system_variables(filter_prefix="VERSION"))
        assert again["ok"] is True


@pytest.mark.live
class TestPreviouslyUnverifiedReads:
    """Areas with no live evidence before 2026-10 — reads only."""

    @pytest.mark.parametrize("tool", [
        list_timecode_events, list_agenda_events, list_worlds, list_filters,
        list_console_users, list_timers, list_universes,
    ], ids=lambda t: t.__name__)
    async def test_read_tool_is_accepted(self, live_client, tool):
        data = _show(json.loads(await tool()))
        assert data.get("ok") is True, data.get("error")


@pytest.mark.live
@pytest.mark.destructive
class TestDestructiveRoundTrips:
    async def test_batch_store_and_delete_group(self, live_client):
        stored = _show(json.loads(await run_command_batch(
            commands=["ClearAll", "Fixture 1", f"Store Group {SCRATCH_GROUP} /o", "ClearAll"],
            confirm_destructive=True,
        )))
        assert stored["ok"] is True
        present = json.loads(await query_object_list(object_type="group", object_id=SCRATCH_GROUP))
        assert "NO OBJECTS FOUND" not in (present.get("console_warnings") or [])

        deleted = json.loads(await delete_object(
            object_type="group", object_id=SCRATCH_GROUP, confirm_destructive=True,
        ))
        assert deleted["ok"] is True
        gone = json.loads(await query_object_list(object_type="group", object_id=SCRATCH_GROUP))
        assert "NO OBJECTS FOUND" in (gone.get("console_warnings") or [])

    async def test_sequence_track_property_round_trip(self, live_client):
        await run_command_batch(
            commands=["ClearAll", "Fixture 1", f"Store Sequence {SCRATCH_SEQUENCE} Cue 1 /o", "ClearAll"],
            confirm_destructive=True,
        )
        try:
            data = _show(json.loads(await set_sequence_property(
                sequence_id=SCRATCH_SEQUENCE, property_name="tracking", value="Off",
                confirm_destructive=True,
            )))
            assert data["success"] is True
            assert data["verified"] is True, "Track did not read back as Off"
        finally:
            await delete_object(object_type="sequence", object_id=SCRATCH_SEQUENCE, confirm_destructive=True)
