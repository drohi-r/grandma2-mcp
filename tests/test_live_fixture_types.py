"""
Live tests — fixture-type intelligence tools against a real grandMA2 console.

Verifies the two live-verified behaviors of the fixture-type build:
  1. ChannelType attribute-discovery parsing against real EditSetup output
  2. Fixture ID renumbering is NOT possible over telnet (Error #66) — the
     renumber_fixtures tool must stay plan-only
plus end-to-end sanity of the read-only tools and plugin preflight.

Usage (on the console PC / office machine):
    # Read-only layers:
    uv run pytest tests/test_live_fixture_types.py --live -v -s

    # Including the renumber probes (sends one refused command, no changes):
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
    """LIVE-VERIFY 2: fixture IDs cannot be renumbered over telnet.

    Live-verified 2026-07-17 (v3.9.60.50): every FixId assign variant
    (``Assign Fixture <old> /fixid=<new>`` at root, /FixId= in the EditSetup
    and LiveSetup layer contexts, ``Move``) returns Error #66 CANNOT ASSIGN
    while sibling properties like /name= apply fine — FixId is console-side
    read-only. These tests pin that behavior: the console must refuse the
    command and leave the patch untouched, and renumber_fixtures must stay
    plan-only.
    """

    SCRATCH_ID = 9500

    async def test_fixid_refused_and_patch_untouched(self, live_client):
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
        if scratch in after_ids:
            # A future MA2 version accepted /fixid — restore and flag so the
            # plan-only downgrade can be revisited.
            await live_client.send_command_with_response(
                f"Assign Fixture {scratch} /fixid={victim}"
            )
            restored = await summarize_patch(live_client)
            assert victim in {f["id"] for f in restored["fixtures"]}
            pytest.fail(
                "/fixid was ACCEPTED on this console version — "
                "renumber_fixtures can be upgraded from plan-only."
            )
        assert "CANNOT ASSIGN" in resp, (
            f"Expected Error #66 CANNOT ASSIGN, got: {resp!r}"
        )
        assert after_ids == ids, "patch changed despite the refused command"

    async def test_renumber_fixtures_is_plan_only(self, live_client):
        data = json.loads(
            await renumber_fixtures(dry_run=False, confirm_destructive=True)
        )
        assert data["plan_only"] is True
        assert data["executed"] == 0
        assert data["blocked"] is True
        assert "CANNOT ASSIGN" in data["plan_only_reason"]
        # Manual dialog steps, not telnet commands
        assert all("/fixid=" not in c for c in data["commands"])
