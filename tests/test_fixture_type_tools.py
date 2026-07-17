"""Tests for the fixture-type intelligence MCP tools (src/server.py) and
plugin manifests (src/plugin_manifests.py)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.fixture_types import build_fixture_type_model


def _patch_summary() -> dict:
    fixtures = (
        [{"id": i, "name": f"Wash {i}", "type": "HY B-EYE K25", "patch": f"1.{i:03d}"} for i in range(1, 5)]
        + [{"id": i, "name": f"Spot {i}", "type": "Mac Viper Profile", "patch": f"2.{i:03d}"} for i in range(101, 104)]
        + [{"id": 50, "name": "Stray", "type": "Mac Viper Profile", "patch": "2.200"}]
        + [{"id": 401, "name": "Blinder", "type": "8-Lite Blinder", "patch": "5.001"}]
    )
    return {
        "showfile": "test_show",
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
        "fixture_types": [
            {"id": 1, "long_name": "HY B-EYE K25", "short_name": "K25", "manufacturer": "Claypaky"},
            {"id": 2, "long_name": "Mac Viper Profile", "short_name": "Viper", "manufacturer": "Martin"},
            {"id": 3, "long_name": "8-Lite Blinder", "short_name": "8Lite", "manufacturer": "Generic"},
        ],
        "groups": [],
        "sequences_count": 0,
        "macros_count": 0,
    }


def _model_and_patch():
    patch_data = _patch_summary()
    return build_fixture_type_model(patch_data), patch_data


# ---------------------------------------------------------------- manifests

class TestPluginManifests:
    def test_builtin_lookup_by_key_and_name(self):
        from src.plugin_manifests import get_manifest
        m1 = get_manifest("auto-layout-color-picker")
        assert m1 and m1["name"] == "Auto Layout Color Picker"
        m2 = get_manifest("auto layout color picker")
        assert m2 and m2["selection"] == "type-ordered"
        assert get_manifest("nope") is None

    def test_merge_overrides_win(self):
        from src.plugin_manifests import get_manifest, merge_manifest
        merged = merge_manifest(
            get_manifest("auto-layout-color-picker"),
            {"pool_ranges": {"macro": [100, 120]}, "required_groups": [1, 2]},
        )
        assert merged["pool_ranges"] == {"macro": [100, 120]}
        assert merged["required_groups"] == [1, 2]
        assert merged["name"] == "Auto Layout Color Picker"

    def test_merge_with_no_base(self):
        from src.plugin_manifests import merge_manifest
        merged = merge_manifest(None, {"name": "Custom", "outputs": ["macro"]})
        assert merged["name"] == "Custom"

    def test_occupied_ids(self):
        from src.plugin_manifests import occupied_ids_in_range
        assert occupied_ids_in_range([1, 5, 900, 950, 1000], 900, 999) == [900, 950]


class TestParsePoolIds:
    def test_extracts_ids(self):
        from src.server import _parse_pool_ids
        raw = (
            "Macro 1 901   ColorPick 1\n"
            "Macro 1 902   ColorPick 2\n"
            "[Macro]> header noise\n"
        )
        assert _parse_pool_ids(raw, "Macro") == [901, 902]


# ---------------------------------------------------------------- tools

class TestAnalyzePatchTypes:
    @pytest.mark.asyncio
    @patch("src.server._hydrate_fixture_type_model")
    async def test_envelope(self, mock_hydrate):
        from src.server import analyze_patch_types
        mock_hydrate.return_value = _model_and_patch()
        data = json.loads(await analyze_patch_types())
        assert data["risk_tier"] == "SAFE_READ"
        assert data["showfile"] == "test_show"
        assert data["fixture_count"] == 9
        assert "Mac Viper Profile" in data["categories"]["mover"]


class TestVerifyFixtureIdBlocks:
    @pytest.mark.asyncio
    @patch("src.server._hydrate_fixture_type_model")
    async def test_out_of_block_reported(self, mock_hydrate):
        from src.server import verify_fixture_id_blocks
        mock_hydrate.return_value = _model_and_patch()
        data = json.loads(await verify_fixture_id_blocks())
        assert data["compliant"] is False
        assert data["out_of_block"][0]["fixture_id"] == 50
        assert data["proposed_commands"] == ["Assign Fixture 50 /fixid=100"]


class TestRenumberFixtures:
    @pytest.mark.asyncio
    @patch("src.server._hydrate_fixture_type_model")
    async def test_dry_run_default(self, mock_hydrate):
        from src.server import renumber_fixtures
        mock_hydrate.return_value = _model_and_patch()
        data = json.loads(await renumber_fixtures())
        assert data["dry_run"] is True
        assert data["executed"] == 0
        assert data["commands"] == ["Assign Fixture 50 /fixid=100"]

    @pytest.mark.asyncio
    @patch("src.server._hydrate_fixture_type_model")
    async def test_blocked_without_confirm(self, mock_hydrate):
        from src.server import renumber_fixtures
        mock_hydrate.return_value = _model_and_patch()
        data = json.loads(await renumber_fixtures(dry_run=False))
        assert data["blocked"] is True
        assert data["executed"] == 0

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    @patch("src.server._hydrate_fixture_type_model")
    async def test_executes_when_confirmed(self, mock_hydrate, mock_get_client):
        from src.server import renumber_fixtures
        mock_hydrate.return_value = _model_and_patch()
        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = client
        data = json.loads(await renumber_fixtures(dry_run=False, confirm_destructive=True))
        assert data["executed"] == 1
        client.send_command_with_response.assert_awaited_with("Assign Fixture 50 /fixid=100")


class TestSelectFixturesByTypeOrder:
    @pytest.mark.asyncio
    @patch("src.server._hydrate_fixture_type_model")
    async def test_commands_only(self, mock_hydrate):
        from src.server import select_fixtures_by_type_order
        mock_hydrate.return_value = _model_and_patch()
        data = json.loads(await select_fixtures_by_type_order())
        assert data["commands"][0] == "ClearAll"
        assert data["commands"][1] == "Fixture 1 Thru 4"                # wash
        assert data["commands"][2] == "Fixture 50 + 101 Thru 103"      # mover
        assert data["commands"][3] == "Fixture 401"                    # blinder
        assert data["selection_order"] == [
            "HY B-EYE K25", "Mac Viper Profile", "8-Lite Blinder",
        ]
        assert data["executed"] == 0

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    @patch("src.server._hydrate_fixture_type_model")
    async def test_execute(self, mock_hydrate, mock_get_client):
        from src.server import select_fixtures_by_type_order
        mock_hydrate.return_value = _model_and_patch()
        client = MagicMock()
        client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = client
        data = json.loads(await select_fixtures_by_type_order(execute=True))
        assert data["executed"] == len(data["commands"])


class TestRunPresetPlugin:
    def _availability(self, available=True):
        return {
            "plugin_name": "Auto Layout Color Picker",
            "available": available,
            "pool_id": 7 if available else None,
            "match": "exact" if available else "miss",
            "last_checked_at": "2026-07-17T00:00:00",
            "source": "live_query",
        }

    @pytest.mark.asyncio
    @patch("src.plugin_inventory._default_inventory")
    async def test_missing_plugin_blocks(self, mock_inv):
        from src.server import run_preset_plugin
        inv = MagicMock()
        inv.lookup = AsyncMock(return_value=self._availability(False))
        mock_inv.return_value = inv
        data = json.loads(await run_preset_plugin("auto-layout-color-picker"))
        assert data["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server._hydrate_fixture_type_model")
    @patch("src.server.get_client")
    @patch("src.plugin_inventory._default_inventory")
    async def test_dry_run_reports_preconditions(
        self, mock_inv, mock_get_client, mock_hydrate
    ):
        from src.server import run_preset_plugin
        inv = MagicMock()
        inv.lookup = AsyncMock(return_value=self._availability())
        mock_inv.return_value = inv
        client = MagicMock()
        # macro/sequence/image pools: one occupied macro inside the range
        client.send_command_with_response = AsyncMock(
            side_effect=lambda cmd, **kw: {
                "list macro": "Macro 1 901   Old Macro\n",
                "list sequence": "",
                "list image": "",
            }.get(cmd, "")
        )
        mock_get_client.return_value = client
        mock_hydrate.return_value = _model_and_patch()

        data = json.loads(await run_preset_plugin("auto-layout-color-picker"))
        assert data["dry_run"] is True
        assert data["preconditions_ok"] is False
        macro_check = next(
            p for p in data["preconditions"] if p["check"].startswith("macro")
        )
        assert macro_check["occupied"] == [901]
        assert data["selection_commands"][0] == "ClearAll"


class TestCreatePresetsForPatch:
    @pytest.mark.asyncio
    @patch("src.server._hydrate_fixture_type_model")
    async def test_dry_run_capability_aware(self, mock_hydrate):
        from src.server import create_presets_for_patch
        mock_hydrate.return_value = _model_and_patch()
        data = json.loads(await create_presets_for_patch(strategy="color-first"))
        assert data["dry_run"] is True
        assert data["executed_presets"] == 0
        assert data["stored_plan"], "cardinal color presets must be storable"
        first = data["stored_plan"][0]
        # Blinder (no color_mix) must not be part of any color preset selection
        assert "8-Lite Blinder" not in first["capable_types"]
        assert any("store preset" in c.lower() for c in first["commands"])
        # Position presets have no concrete values → declared_only
        assert any(e["preset_type"] == 2 for e in data["declared_only"])

    @pytest.mark.asyncio
    @patch("src.server._hydrate_fixture_type_model")
    async def test_unknown_strategy_blocks(self, mock_hydrate):
        from src.server import create_presets_for_patch
        data = json.loads(await create_presets_for_patch(strategy="space-opera"))
        assert data["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server._hydrate_fixture_type_model")
    async def test_blocked_without_confirm(self, mock_hydrate):
        from src.server import create_presets_for_patch
        mock_hydrate.return_value = _model_and_patch()
        data = json.loads(await create_presets_for_patch(dry_run=False))
        assert data["blocked"] is True
        assert data["executed_presets"] == 0
