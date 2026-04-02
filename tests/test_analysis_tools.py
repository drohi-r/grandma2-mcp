"""
Tests for analysis & intelligence tools:
find_preset_usages, diff_cues, get_page_map, lint_macro,
detect_programmer_contamination, preview_preset_update_impact,
detect_tracking_leaks, audit_page_consistency, plan_fixture_swap,
incident_snapshot, trace_attribute_lineage, find_executor_dependencies,
find_unused_objects, validate_universal_preset_coverage,
compare_patch_to_show_expectation, snapshot_programmer_state,
restore_programmer_state, generate_song_macro_pack
"""

import json
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest


class TestFindPresetUsages:
    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_finds_references(self, mock_get_client, mock_orch):
        from src.server import find_preset_usages

        mock_orch.last_snapshot = None
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "1  Seq1\n2  Seq2\n",  # list sequence
            "1  Cue1 Preset 4.1 data\n2  Cue2\n",  # seq 1 cues
            "1  Cue1\n2  Cue2\n",  # seq 2 cues (no ref)
        ])
        mock_get_client.return_value = mock_client

        result = await find_preset_usages(preset_type="color", preset_id=1)
        data = json.loads(result)

        assert data["total_references"] >= 1
        assert data["risk_if_deleted"] in ("low", "medium", "high")
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    async def test_invalid_preset_type(self):
        from src.server import find_preset_usages
        result = await find_preset_usages(preset_type="bogus", preset_id=1)
        data = json.loads(result)
        assert "error" in data


class TestDiffCues:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_detects_differences(self, mock_get_client):
        from src.server import diff_cues

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "Dimmer=100 Color=Red Fade=2\n",
            "Dimmer=50 Color=Blue Fade=3\n",
        ])
        mock_get_client.return_value = mock_client

        result = await diff_cues(sequence_id=1, cue_a=1, cue_b=2)
        data = json.loads(result)

        assert data["identical"] is False
        assert data["total_changes"] > 0
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_identical_cues(self, mock_get_client):
        from src.server import diff_cues

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Dimmer=100\n")
        mock_get_client.return_value = mock_client

        result = await diff_cues(sequence_id=1, cue_a=1, cue_b=2)
        data = json.loads(result)
        assert data["identical"] is True


class TestGetPageMap:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_returns_executor_list(self, mock_get_client):
        from src.server import get_page_map

        mock_client = MagicMock()
        responses = ["Name=FrontWash Sequence=1 Width=1\n"] + ["NO OBJECTS FOUND\n"] * 39
        mock_client.send_command_with_response = AsyncMock(side_effect=responses)
        mock_get_client.return_value = mock_client

        result = await get_page_map(page=1)
        data = json.loads(result)

        assert data["occupied"] == 1
        assert len(data["free_slots"]) == 39
        assert data["risk_tier"] == "SAFE_READ"


class TestLintMacro:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_detects_destructive_command(self, mock_get_client):
        from src.server import lint_macro

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "  1  Delete Cue 5 Sequence 1\n  2  Label Group 1\n",  # list macro
            "Name=TestMacro\n",  # info macro
        ])
        mock_get_client.return_value = mock_client

        result = await lint_macro(macro_id=1)
        data = json.loads(result)

        assert data["overall"] == "error"
        assert any(i["rule"] == "destructive_no_gate" for i in data["issues"])
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_clean_macro(self, mock_get_client):
        from src.server import lint_macro

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "1 Label Group 1\n2 Appearance Group 1 /r=100\n",
            "Name=SafeMacro\n",
        ])
        mock_get_client.return_value = mock_client

        result = await lint_macro(macro_id=1)
        data = json.loads(result)
        assert data["overall"] == "clean"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_macro_not_found(self, mock_get_client):
        from src.server import lint_macro

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="NO OBJECTS FOUND")
        mock_get_client.return_value = mock_client

        result = await lint_macro(macro_id=999)
        data = json.loads(result)
        assert "error" in data


class TestDetectProgrammerContamination:
    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    async def test_clean_programmer(self, mock_orch):
        from src.server import detect_programmer_contamination

        snap = MagicMock()
        snap.selected_fixture_count = 0
        snap.active_filter = None
        snap.active_world = None
        snap.console_modes = {"highlight": False, "freeze": False, "solo": False, "blind": False}
        snap.parked_fixtures = set()
        snap.matricks = MagicMock(active=False)
        snap.age_seconds.return_value = 5.0
        mock_orch.last_snapshot = snap

        result = await detect_programmer_contamination()
        data = json.loads(result)

        assert data["contaminated"] is False
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    async def test_contaminated_programmer(self, mock_orch):
        from src.server import detect_programmer_contamination

        snap = MagicMock()
        snap.selected_fixture_count = 5
        snap.active_filter = 3
        snap.active_world = None
        snap.console_modes = {"highlight": True, "freeze": False, "solo": False, "blind": False}
        snap.parked_fixtures = {101, 102}
        snap.matricks = MagicMock(active=False)
        snap.age_seconds.return_value = 2.0
        mock_orch.last_snapshot = snap

        result = await detect_programmer_contamination()
        data = json.loads(result)

        assert data["contaminated"] is True
        assert any(c["check"] == "selected_fixtures" and c["status"] == "fail" for c in data["checks"])


class TestPreviewPresetUpdateImpact:
    @pytest.mark.asyncio
    @patch("src.server.find_preset_usages")
    async def test_safe_impact(self, mock_find):
        from src.server import preview_preset_update_impact

        mock_find.return_value = json.dumps({
            "usages": [], "executor_references": [],
            "total_references": 0, "sequences_scanned": 10,
            "preset_type": "color", "preset_type_id": 4, "preset_id": 99,
            "risk_if_deleted": "none", "risk_tier": "SAFE_READ",
        })

        result = await preview_preset_update_impact(preset_type="color", preset_id=99)
        data = json.loads(result)
        assert data["impact_level"] == "safe"

    @pytest.mark.asyncio
    @patch("src.server.find_preset_usages")
    async def test_catastrophic_impact(self, mock_find):
        from src.server import preview_preset_update_impact

        mock_find.return_value = json.dumps({
            "usages": [{"sequence_id": i, "cue_id": "1", "context": "ref"} for i in range(10)],
            "executor_references": [],
            "total_references": 10, "sequences_scanned": 50,
            "preset_type": "color", "preset_type_id": 4, "preset_id": 1,
            "risk_if_deleted": "high", "risk_tier": "SAFE_READ",
        })

        result = await preview_preset_update_impact(preset_type="color", preset_id=1)
        data = json.loads(result)
        assert data["impact_level"] == "catastrophic"


class TestDetectTrackingLeaks:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_finds_leaks(self, mock_get_client):
        from src.server import detect_tracking_leaks

        shared_line = "Dimmer 100 attr data"
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "1  Cue1\n2  Cue2\n",  # cue list
            f"{shared_line}\nColor Red\n",  # cue 1
            f"{shared_line}\nColor Blue\n",  # cue 2
        ])
        mock_get_client.return_value = mock_client

        result = await detect_tracking_leaks(sequence_id=1)
        data = json.loads(result)

        assert data["cues_checked"] == 2
        assert data["risk_tier"] == "SAFE_READ"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_empty_sequence(self, mock_get_client):
        from src.server import detect_tracking_leaks

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="NO OBJECTS FOUND")
        mock_get_client.return_value = mock_client

        result = await detect_tracking_leaks(sequence_id=99)
        data = json.loads(result)
        assert "error" in data


class TestAuditPageConsistency:
    @pytest.mark.asyncio
    @patch("src.server.get_page_map")
    async def test_clean_page(self, mock_map):
        from src.server import audit_page_consistency

        mock_map.return_value = json.dumps({
            "page": 1,
            "executors": [
                {"id": 201, "label": "Main Wash", "type": "sequence", "fader_function": "Master", "priority": "Normal"},
                {"id": 202, "label": "Effects", "type": "effect", "fader_function": "speed", "priority": "Normal"},
            ],
            "occupied": 2, "free_slots": list(range(203, 241)), "total_slots": 40,
        })

        result = await audit_page_consistency(page=1)
        data = json.loads(result)
        assert data["overall_status"] in ("ok", "warning")
        assert data["risk_tier"] == "SAFE_READ"


class TestPlanFixtureSwap:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_compatible_swap(self, mock_get_client):
        from src.server import plan_fixture_swap

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "cd /\n",  # cd /
            "1  Fix1 Mac700\n",  # list fixture (old type search)
            "Attribute=Dimmer Attribute=Pan Attribute=Tilt\n",  # info fixture
            "cd /\n",  # cd /
            "cd /\n",  # cd / (second type)
            "2  Fix2 MacViper\n",  # list fixture (new type search)
            "Attribute=Dimmer Attribute=Pan Attribute=Tilt Attribute=Zoom\n",  # info
            "cd /\n",  # cd /
        ])
        mock_get_client.return_value = mock_client

        result = await plan_fixture_swap(
            old_fixture_type="Mac700", new_fixture_type="MacViper"
        )
        data = json.loads(result)

        assert "migration_steps" in data
        assert data["risk_tier"] == "SAFE_READ"


class TestIncidentSnapshot:
    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_captures_state(self, mock_get_client, mock_orch):
        from src.server import incident_snapshot

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="$VERSION=3.9.60\n$SHOWFILE=TestShow\n$USER=admin\n$USERRIGHTS=Admin\n$FADERPAGE=1\n$SELECTEDFIXTURESCOUNT=0\n$SELECTEDEXEC=1.1\n"
        )
        mock_get_client.return_value = mock_client
        mock_orch.last_snapshot = None

        result = await incident_snapshot()
        data = json.loads(result)

        assert "timestamp" in data
        assert "showfile" in data
        assert "summary" in data
        assert data["risk_tier"] == "SAFE_READ"


class TestTraceAttributeLineage:
    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_finds_candidate_sources(self, mock_get_client, mock_orch):
        from src.server import trace_attribute_lineage

        snap = MagicMock()
        snap.executor_state = {201: MagicMock(sequence_id=1)}
        snap.selected_fixture_count = 0
        snap.active_filter = None
        snap.active_world = None
        snap.console_modes = {}
        snap.selected_exec = "1.201"
        snap.selected_exec_cue = "1"
        mock_orch.last_snapshot = snap

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(side_effect=[
            "1 Cue1\n2 Cue2\n",
            "Fixture 101 Dimmer 100\n",
            "Fixture 101 Color Red\n",
        ])
        mock_get_client.return_value = mock_client

        result = await trace_attribute_lineage(attribute="Dimmer", fixture_id=101)
        data = json.loads(result)

        assert data["candidate_sources"][0]["sequence_id"] == 1
        assert data["risk_tier"] == "SAFE_READ"


class TestFindExecutorDependencies:
    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_extracts_dependencies(self, mock_get_client, mock_orch):
        from src.server import find_executor_dependencies

        snap = MagicMock()
        snap.executor_state = {
            1: MagicMock(page=3, id=205, sequence_id=12, label="Wash", priority="High",
                         button_function="Go", fader_function="Master", ooo=False,
                         kill_protect=True, auto_start=False)
        }
        mock_orch.last_snapshot = snap

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value='Name="Wash" Sequence=12 Trigger=Go Priority=High Fader=Master Speed=3.1'
        )
        mock_get_client.return_value = mock_client

        result = await find_executor_dependencies(page=3, executor_id=205)
        data = json.loads(result)

        assert data["dependencies"]["sequence_id"] == "12"
        assert data["dependencies"]["speed_master"] == "3.1"


class TestFindUnusedObjects:
    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    @patch("src.server.get_client")
    async def test_sequence_candidates(self, mock_get_client, mock_orch):
        from src.server import find_unused_objects

        snap = MagicMock()
        snap.executor_state = {1: MagicMock(sequence_id=1)}
        mock_orch.last_snapshot = snap

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="1 Seq1\n2 Seq2\n")
        mock_get_client.return_value = mock_client

        result = await find_unused_objects(object_type="sequence")
        data = json.loads(result)

        assert any(item["id"] == 2 for item in data["candidate_unused"])
        assert data["heuristic_only"] is True


class TestValidateUniversalPresetCoverage:
    @pytest.mark.asyncio
    @patch("src.server.list_preset_pool")
    async def test_reports_missing_slots(self, mock_pool):
        from src.server import validate_universal_preset_coverage

        mock_pool.return_value = json.dumps({
            "entries": [
                {"id": 1, "name": "Open White"},
                {"id": 3, "name": "Blue"},
            ],
            "risk_tier": "SAFE_READ",
        })

        result = await validate_universal_preset_coverage("color", 1, 3)
        data = json.loads(result)

        assert data["missing_ids"] == [2]
        assert data["coverage_percent"] == pytest.approx(66.7, rel=1e-2)


class TestComparePatchToShowExpectation:
    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_detects_missing_fixture_counts(self, mock_get_client):
        from src.server import compare_patch_to_show_expectation

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(
            return_value="101 Mac Aura XB\n102 Mac Aura XB\n201 Viper Profile\n"
        )
        mock_get_client.return_value = mock_client

        result = await compare_patch_to_show_expectation("Mac Aura XB=3, Viper Profile=1")
        data = json.loads(result)

        assert data["fit_status"] == "mismatch"
        assert data["missing"][0]["fixture_type"] == "Mac Aura XB"


class TestSnapshotProgrammerState:
    @pytest.mark.asyncio
    @patch("src.server._orchestrator")
    async def test_snapshot_from_hydrated_state(self, mock_orch):
        from src.server import snapshot_programmer_state

        snap = MagicMock()
        snap.selected_fixture_count = 4
        snap.active_preset_type = "COLOR"
        snap.active_feature = "Color"
        snap.active_attribute = "Dimmer"
        snap.selected_exec = "1.201"
        snap.selected_exec_cue = "1"
        snap.active_world = 2
        snap.active_filter = 3
        snap.console_modes = {"blind": True}
        snap.parked_fixtures = {"101"}
        snap.matricks = MagicMock(active=True)
        snap.matricks.summary.return_value = "blocks=2 wings=1"
        snap.age_seconds.return_value = 2.5
        mock_orch.last_snapshot = snap

        result = await snapshot_programmer_state()
        data = json.loads(result)

        assert data["snapshot"]["active_world"] == 2
        assert "selected_fixture_count" in data["non_restorable_fields"]


class TestRestoreProgrammerState:
    @pytest.mark.asyncio
    async def test_preview_only(self):
        from src.server import restore_programmer_state

        result = await restore_programmer_state(json.dumps({
            "snapshot": {
                "active_world": 2,
                "active_filter": 3,
                "selected_exec": "1.201",
                "console_modes": {"blind": True},
            }
        }))
        data = json.loads(result)

        assert data["apply"] is False
        assert "World 2" in data["planned_commands"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_apply_executes_commands(self, mock_get_client):
        from src.server import restore_programmer_state

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="OK")
        mock_get_client.return_value = mock_client

        result = await restore_programmer_state(
            json.dumps({"snapshot": {"active_world": 2, "selected_exec": "1.201", "console_modes": {}}}),
            apply=True,
        )
        data = json.loads(result)

        assert data["apply"] is True
        assert len(data["executed"]) >= 2


class TestGenerateSongMacroPack:
    @pytest.mark.asyncio
    async def test_builds_macro_draft(self):
        from src.server import generate_song_macro_pack

        result = await generate_song_macro_pack("Opening Song", sequence_id=12, start_macro_id=100, target_page=3)
        data = json.loads(result)

        assert data["macro_count"] == 7
        assert data["macros"][0]["macro_id"] == 100
        assert data["macros"][0]["label"] == "Opening Song - Load Song"
