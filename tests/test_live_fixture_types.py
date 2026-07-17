"""
Live tests — fixture-type intelligence tools against a real grandMA2 console.

Verifies the two live-UNVERIFIED assumptions of the fixture-type build:
  1. ChannelType attribute-discovery parsing against real EditSetup output
  2. The ``Assign Fixture <old> /fixid=<new>`` renumbering command
plus end-to-end sanity of the read-only tools and plugin preflight.

Usage (on the console PC / office machine):
    # Read-only layers:
    uv run pytest tests/test_live_fixture_types.py --live -v -s

    # Including the renumber round-trip (modifies + restores the patch):
    uv run pytest tests/test_live_fixture_types.py --live --destructive -v -s
"""

from __future__ import annotations

import json

import pytest
import pytest_asyncio

from src.server import (
    analyze_patch_types,
    renumber_fixtures,
    run_preset_plugin,
    select_fixtures_by_type_order,
    verify_fixture_id_blocks,
)
from src.server import get_client

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def live_client():
    client = await get_client()
    assert client is not None, "Failed to connect to grandMA2 console"
    yield client


@pytest.mark.live
class TestFixtureTypeReadOnly:
    """SAFE_READ layer — no side effects."""

    async def test_analyze_patch_types_fallback(self, live_client):
        data = json.loads(await analyze_patch_types())
        print(json.dumps(data, indent=2))
        assert data["fixture_count"] > 0, "no fixtures parsed from live patch"
        assert data["types"], "no fixture types built"
        for rec in data["types"].values():
            assert rec["category"] in {
                "wash", "mover", "bar", "strobe", "blinder", "conventional", "other",
            }

    async def test_analyze_patch_types_live_attributes(self, live_client):
        """LIVE-VERIFY 1: ChannelType parsing against real EditSetup output."""
        data = json.loads(await analyze_patch_types(discover_attributes=True))
        print(json.dumps({k: v["capabilities"] for k, v in data["types"].items()}, indent=2))
        sources = {v["capability_source"] for v in data["types"].values()}
        assert "console" in sources, (
            "No type got capabilities from the console — ChannelType parsing "
            "failed against real EditSetup output. Capture the raw list output "
            "via discover_fixture_type_attributes and fix parse_channel_type_rows."
        )

    async def test_verify_fixture_id_blocks(self, live_client):
        data = json.loads(await verify_fixture_id_blocks())
        print(json.dumps(data, indent=2))
        assert "categories" in data and "renumber_plan" in data

    async def test_type_ordered_selection_commands(self, live_client):
        data = json.loads(await select_fixtures_by_type_order())
        print(json.dumps(data, indent=2))
        assert data["commands"][0] == "ClearAll"
        assert len(data["commands"]) >= 2

    async def test_plugin_preflight_dry_run(self, live_client):
        data = json.loads(await run_preset_plugin("auto-layout-color-picker"))
        print(json.dumps(data, indent=2))
        # Either the plugin is absent (blocked) or we get a full preflight
        assert data.get("blocked") or "preconditions" in data


@pytest.mark.live
class TestTypeOrderedSelectionExecute:
    """SAFE_WRITE — executes selection, then clears it."""

    async def test_execute_and_clear(self, live_client):
        data = json.loads(await select_fixtures_by_type_order(execute=True))
        assert data["executed"] == len(data["commands"])
        await live_client.send_command_with_response("ClearAll")


@pytest.mark.live
@pytest.mark.destructive
class TestRenumberRoundTrip:
    """LIVE-VERIFY 2: the /fixid renumber command — round-trips one fixture.

    Picks the highest fixture ID in the patch, renumbers it to a free scratch
    ID (9500+), verifies via re-read, then renumbers it back. If the /fixid
    syntax is wrong on this MA2 version, the first assert fails and nothing
    was changed.
    """

    SCRATCH_ID = 9500

    async def test_fixid_round_trip(self, live_client):
        from src.show_strategies.patch_reader import summarize_patch

        patch = await summarize_patch(live_client)
        assert patch["fixtures"], "empty patch"
        ids = {f["id"] for f in patch["fixtures"]}
        victim = max(ids)
        scratch = self.SCRATCH_ID
        while scratch in ids:
            scratch += 1

        resp = await live_client.send_command_with_response(
            f"Assign Fixture {victim} /fixid={scratch}"
        )
        print(f"renumber response: {resp!r}")

        after = await summarize_patch(live_client)
        after_ids = {f["id"] for f in after["fixtures"]}
        try:
            assert scratch in after_ids and victim not in after_ids, (
                f"'Assign Fixture {victim} /fixid={scratch}' did not take effect — "
                f"the /fixid syntax is NOT valid on this console version. "
                f"Response was: {resp!r}. renumber_fixtures must be reworked "
                "(e.g. via EditSetup patch edit)."
            )
        finally:
            # Restore regardless — if the first command worked, undo it.
            if scratch in after_ids:
                await live_client.send_command_with_response(
                    f"Assign Fixture {scratch} /fixid={victim}"
                )
                restored = await summarize_patch(live_client)
                assert victim in {f["id"] for f in restored["fixtures"]}
