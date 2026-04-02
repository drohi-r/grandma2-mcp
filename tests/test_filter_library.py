"""
Filter Library Tests

Tests for filter attribute constants, XML generation from the script,
and the create_filter_library MCP tool.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.commands.constants import FILTER_ATTRIBUTES, FILTER_COLORS, FILTER_VTE_COMBOS


@pytest.fixture(autouse=True)
def _gma2_data_root_tmpdir(tmp_path, monkeypatch):
    """Redirect GMA2_DATA_ROOT to a temp dir so filesystem writes work on any OS."""
    (tmp_path / "importexport" / "filters").mkdir(parents=True, exist_ok=True)
    (tmp_path / "matricks").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GMA2_DATA_ROOT", str(tmp_path))
    # Also patch the module-level variable that was already read at import time
    monkeypatch.setattr("src.server._GMA2_DATA_ROOT", str(tmp_path))

# ============================================================
# Filter Attribute Constants Tests
# ============================================================


class TestFilterAttributes:
    """Tests for FILTER_ATTRIBUTES constant completeness."""

    def test_has_all_seven_preset_types(self):
        expected = {"dimmer", "position", "gobo", "color", "beam", "focus", "control"}
        assert set(FILTER_ATTRIBUTES.keys()) == expected

    def test_dimmer_attributes(self):
        assert FILTER_ATTRIBUTES["dimmer"] == ["DIM"]

    def test_position_attribute_count(self):
        assert len(FILTER_ATTRIBUTES["position"]) == 5

    def test_position_contains_pan_tilt(self):
        pos = FILTER_ATTRIBUTES["position"]
        assert "PAN" in pos
        assert "TILT" in pos

    def test_gobo_attribute_count(self):
        assert len(FILTER_ATTRIBUTES["gobo"]) == 7

    def test_color_attribute_count(self):
        assert len(FILTER_ATTRIBUTES["color"]) == 10

    def test_color_contains_rgb(self):
        col = FILTER_ATTRIBUTES["color"]
        assert "COLORRGB1" in col
        assert "COLORRGB2" in col
        assert "COLORRGB3" in col

    def test_beam_attribute_count(self):
        assert len(FILTER_ATTRIBUTES["beam"]) == 5

    def test_focus_attribute_count(self):
        assert len(FILTER_ATTRIBUTES["focus"]) == 2
        assert "FOCUS" in FILTER_ATTRIBUTES["focus"]
        assert "ZOOM" in FILTER_ATTRIBUTES["focus"]

    def test_control_attribute_count(self):
        assert len(FILTER_ATTRIBUTES["control"]) == 6

    def test_total_attributes(self):
        total = sum(len(v) for v in FILTER_ATTRIBUTES.values())
        assert total == 36

    def test_no_duplicate_attributes_across_types(self):
        all_attrs = []
        for attrs in FILTER_ATTRIBUTES.values():
            all_attrs.extend(attrs)
        assert len(all_attrs) == len(set(all_attrs)), "Duplicate attributes found"


# ============================================================
# Filter Color Constants Tests
# ============================================================


class TestFilterColors:
    """Tests for FILTER_COLORS constant."""

    def test_has_all_nine_categories(self):
        expected = {
            "dimmer", "position", "gobo", "color", "beam",
            "focus", "control", "combo", "exclude",
        }
        assert set(FILTER_COLORS.keys()) == expected

    def test_all_colors_are_6_char_hex(self):
        for cat, hex_val in FILTER_COLORS.items():
            assert len(hex_val) == 6, f"{cat} color '{hex_val}' is not 6 chars"
            int(hex_val, 16)  # should not raise

    def test_specific_colors(self):
        assert FILTER_COLORS["dimmer"] == "FFCC00"
        assert FILTER_COLORS["exclude"] == "FF3333"
        assert FILTER_COLORS["combo"] == "CC44FF"


# ============================================================
# Script XML Generation Tests
# ============================================================


class TestFilterXMLGeneration:
    """Tests for the XML generation in the filter library script."""

    def test_generate_filter_xml(self):
        from scripts.create_filter_library import generate_filter_xml

        xml = generate_filter_xml(3, ["DIM"], "FFCC00")
        assert 'index="2"' in xml  # slot 3 → index 2
        assert 'Color="FFCC00"' in xml
        assert '<AttributeLink name="DIM" />' in xml
        assert 'keep_filter="false"' in xml

    def test_generate_filter_xml_multiple_attrs(self):
        from scripts.create_filter_library import generate_filter_xml

        xml = generate_filter_xml(4, ["PAN", "TILT", "POSITIONMSPEED"], "0088FF")
        assert 'index="3"' in xml
        assert 'Color="0088FF"' in xml
        assert '<AttributeLink name="PAN" />' in xml
        assert '<AttributeLink name="TILT" />' in xml
        assert '<AttributeLink name="POSITIONMSPEED" />' in xml

    def test_generate_library_xml_structure(self):
        from scripts.create_filter_library import generate_library_xml

        xml = generate_library_xml()
        assert '<?xml version="1.0"' in xml
        assert "schemas.malighting.de" in xml
        assert "</MA>" in xml
        # Should have all 21 filters
        assert xml.count("<Filter ") == 21

    def test_generate_library_xml_has_all_categories(self):
        from scripts.create_filter_library import generate_library_xml

        xml = generate_library_xml()
        # Check all color categories appear
        for color_hex in FILTER_COLORS.values():
            assert f'Color="{color_hex}"' in xml


# ============================================================
# create_filter_library MCP Tool Tests
# ============================================================


class TestCreateFilterLibraryTool:
    """Tests for the create_filter_library MCP tool."""

    @pytest.mark.asyncio
    async def test_blocked_without_confirm(self):
        from src.server import create_filter_library

        result = await create_filter_library()
        data = json.loads(result)
        assert data["blocked"] is True
        assert "DESTRUCTIVE" in data["risk_tier"]
        assert "confirm_destructive" in data["error"]

    @pytest.mark.asyncio
    async def test_blocked_with_custom_params(self):
        from src.server import create_filter_library

        result = await create_filter_library(
            start_slot=5, include_combos=False, include_exclusions=False,
        )
        data = json.loads(result)
        assert data["blocked"] is True

    @pytest.mark.asyncio
    @patch("src.server._check_pool_slots", new_callable=AsyncMock)
    @patch("src.server.get_client")
    async def test_creates_all_filters(self, mock_get_client, mock_check):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        mock_check.return_value = {"occupied_slots": [], "free_ranges": [], "next_free_slots": [],
                                   "total_occupied": 0, "total_free_in_range": 0,
                                   "largest_contiguous": 0, "can_fit": None, "suggested_start": None}

        result = await create_filter_library(confirm_destructive=True)

        data = json.loads(result)
        assert data["filters_created"] == 21  # 7 + 7 + 7
        assert data["first_slot"] == 3
        assert data["last_slot"] == 23
        assert data["risk_tier"] == "DESTRUCTIVE"

        # Each filter: import + label + appearance = 3 commands
        assert mock_client.send_command_with_response.call_count == 21 * 3

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_no_combos_no_exclusions(self, mock_get_client, tmp_path):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await create_filter_library(
            include_combos=False,
            include_exclusions=False,
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert data["filters_created"] == 7  # only single PresetType filters
        assert data["first_slot"] == 3
        assert data["last_slot"] == 9

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_custom_start_slot(self, mock_get_client):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await create_filter_library(
            start_slot=10,
            include_combos=False,
            include_exclusions=False,
            confirm_destructive=True,
        )
        data = json.loads(result)
        assert data["first_slot"] == 10
        assert data["last_slot"] == 16  # 7 single filters starting at 10

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_commands_sent(self, mock_get_client):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        await create_filter_library(
            include_combos=False,
            include_exclusions=False,
            confirm_destructive=True,
        )

        calls = [
            str(c) for c in mock_client.send_command_with_response.call_args_list
        ]
        # Check import commands use correct syntax
        import_calls = [c for c in calls if "Import" in c or "import" in c]
        assert len(import_calls) == 7
        # Check label commands
        label_calls = [c for c in calls if "Label" in c]
        assert len(label_calls) == 7
        # Check appearance commands
        appearance_calls = [c for c in calls if "Appearance" in c]
        assert len(appearance_calls) == 7

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_color_scheme_in_result(self, mock_get_client):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await create_filter_library(confirm_destructive=True)
        data = json.loads(result)
        assert "color_scheme" in data
        assert "dimmer" in data["color_scheme"]
        assert "FFCC00" in data["color_scheme"]["dimmer"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_filter_categories_in_results(self, mock_get_client):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await create_filter_library(confirm_destructive=True)
        data = json.loads(result)

        categories = {f["category"] for f in data["filters"]}
        assert categories == {"dimmer", "position", "gobo", "color", "beam",
                              "focus", "control", "combo", "exclude"}

        # Check filter names
        names = {f["name"] for f in data["filters"]}
        assert "Dimmer" in names
        assert "Dim+Pos" in names
        assert "No Dimmer" in names


# ============================================================
# FILTER_VTE_COMBOS Constants Tests
# ============================================================


class TestFilterVTECombos:
    """Tests for FILTER_VTE_COMBOS constant."""

    def test_has_seven_combos(self):
        assert len(FILTER_VTE_COMBOS) == 7

    def test_no_all_off_combo(self):
        for suffix, v, vt, e in FILTER_VTE_COMBOS:
            assert v or vt or e, f"All-off combo found: {suffix}"

    def test_all_suffixes_unique(self):
        suffixes = [s for s, _, _, _ in FILTER_VTE_COMBOS]
        assert len(suffixes) == len(set(suffixes))

    def test_includes_single_flags(self):
        suffixes = {s for s, _, _, _ in FILTER_VTE_COMBOS}
        assert "V" in suffixes
        assert "VT" in suffixes
        assert "E" in suffixes

    def test_includes_all_on(self):
        suffixes = {s for s, _, _, _ in FILTER_VTE_COMBOS}
        assert "V+VT+E" in suffixes

    def test_correct_bool_values(self):
        combo_map = {s: (v, vt, e) for s, v, vt, e in FILTER_VTE_COMBOS}
        assert combo_map["V"] == (True, False, False)
        assert combo_map["VT"] == (False, True, False)
        assert combo_map["E"] == (False, False, True)
        assert combo_map["V+VT"] == (True, True, False)
        assert combo_map["V+E"] == (True, False, True)
        assert combo_map["VT+E"] == (False, True, True)
        assert combo_map["V+VT+E"] == (True, True, True)


# ============================================================
# V/VT/E XML Generation Tests
# ============================================================


class TestFilterVTEXMLGeneration:
    """Tests for V/VT/E XML attribute generation."""

    def test_all_true_no_vte_attrs(self):
        from scripts.create_filter_library import generate_filter_xml

        xml = generate_filter_xml(3, ["DIM"], "FFCC00")
        assert 'value=' not in xml
        assert 'value_timing=' not in xml
        assert 'effect=' not in xml

    def test_value_false(self):
        from scripts.create_filter_library import generate_filter_xml

        xml = generate_filter_xml(3, ["DIM"], "FFCC00", value=False)
        assert 'value="false"' in xml
        assert 'value_timing=' not in xml
        assert 'effect=' not in xml

    def test_value_timing_false(self):
        from scripts.create_filter_library import generate_filter_xml

        xml = generate_filter_xml(3, ["DIM"], "FFCC00", value_timing=False)
        assert 'value=' not in xml or 'value_timing="false"' in xml
        assert 'value_timing="false"' in xml

    def test_effect_false(self):
        from scripts.create_filter_library import generate_filter_xml

        xml = generate_filter_xml(3, ["DIM"], "FFCC00", effect=False)
        assert 'effect="false"' in xml

    def test_all_false(self):
        from scripts.create_filter_library import generate_filter_xml

        xml = generate_filter_xml(
            3, ["DIM"], "FFCC00",
            value=False, value_timing=False, effect=False,
        )
        assert 'value="false"' in xml
        assert 'value_timing="false"' in xml
        assert 'effect="false"' in xml

    def test_v_only(self):
        from scripts.create_filter_library import generate_filter_xml

        xml = generate_filter_xml(
            3, ["DIM"], "FFCC00",
            value=True, value_timing=False, effect=False,
        )
        assert 'value="false"' not in xml
        assert 'value_timing="false"' in xml
        assert 'effect="false"' in xml

    def test_vte_attrs_before_keep_filter(self):
        from scripts.create_filter_library import generate_filter_xml

        xml = generate_filter_xml(
            3, ["DIM"], "FFCC00", value=False,
        )
        # V/VT/E attrs should come before keep_filter
        vf_pos = xml.index('value="false"')
        kf_pos = xml.index('keep_filter="false"')
        assert vf_pos < kf_pos


# ============================================================
# V/VT/E Script Helper Tests
# ============================================================


class TestBuildVTEFilters:
    """Tests for the build_vte_filters helper in the script."""

    def test_builds_correct_count(self):
        from scripts.create_filter_library import build_vte_filters

        base = [
            (3, "Dimmer", ["DIM"], "dimmer"),
            (4, "Position", ["PAN", "TILT"], "position"),
        ]
        vte = build_vte_filters(base, start_slot=24)
        assert len(vte) == 2 * 7  # 2 base × 7 VTE combos

    def test_naming_scheme(self):
        from scripts.create_filter_library import build_vte_filters

        base = [(3, "Dimmer", ["DIM"], "dimmer")]
        vte = build_vte_filters(base, start_slot=24)
        names = [name for _, name, _, _, _, _, _ in vte]
        assert "Dimmer V" in names
        assert "Dimmer VT" in names
        assert "Dimmer E" in names
        assert "Dimmer V+VT+E" in names

    def test_slot_continuity(self):
        from scripts.create_filter_library import build_vte_filters

        base = [(3, "Dim", ["DIM"], "dimmer"), (4, "Pos", ["PAN"], "position")]
        vte = build_vte_filters(base, start_slot=24)
        slots = [s for s, _, _, _, _, _, _ in vte]
        assert slots == list(range(24, 24 + 14))

    def test_preserves_attrs(self):
        from scripts.create_filter_library import build_vte_filters

        base = [(3, "Dimmer", ["DIM"], "dimmer")]
        vte = build_vte_filters(base, start_slot=24)
        for _, _, attrs, _, _, _, _ in vte:
            assert attrs == ["DIM"]


# ============================================================
# MCP Tool V/VT/E Tests
# ============================================================


class TestCreateFilterLibraryVTE:
    """Tests for create_filter_library with include_vte=True."""

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_vte_creates_all_variants(self, mock_get_client):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await create_filter_library(
            include_vte=True, confirm_destructive=True,
        )
        data = json.loads(result)
        # 21 base + 21 × 7 VTE = 21 + 147 = 168
        assert data["filters_created"] == 168
        assert data["base_filters"] == 21
        assert data["vte_variants"] == 147

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_vte_single_type_only(self, mock_get_client):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await create_filter_library(
            include_combos=False,
            include_exclusions=False,
            include_vte=True,
            confirm_destructive=True,
        )
        data = json.loads(result)
        # 7 base + 7 × 7 VTE = 7 + 49 = 56
        assert data["filters_created"] == 56
        assert data["base_filters"] == 7
        assert data["vte_variants"] == 49

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_vte_false_no_variants(self, mock_get_client):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await create_filter_library(
            include_vte=False, confirm_destructive=True,
        )
        data = json.loads(result)
        assert data["filters_created"] == 21
        assert data["vte_variants"] == 0

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_vte_filter_names(self, mock_get_client):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await create_filter_library(
            include_combos=False,
            include_exclusions=False,
            include_vte=True,
            confirm_destructive=True,
        )
        data = json.loads(result)
        names = {f["name"] for f in data["filters"]}
        assert "Dimmer V" in names
        assert "Position VT" in names
        assert "Control V+VT+E" in names

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_vte_has_vte_field(self, mock_get_client):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await create_filter_library(
            include_combos=False,
            include_exclusions=False,
            include_vte=True,
            confirm_destructive=True,
        )
        data = json.loads(result)
        # Base filters should have V=on VT=on E=on
        base = [f for f in data["filters"] if f["name"] == "Dimmer"][0]
        assert base["vte"] == "V=on VT=on E=on"
        # VTE variant should reflect its flags
        dimv = [f for f in data["filters"] if f["name"] == "Dimmer V"][0]
        assert dimv["vte"] == "V=on VT=off E=off"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_vte_slot_continuity(self, mock_get_client):
        from src.server import create_filter_library

        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client

        result = await create_filter_library(
            include_combos=False,
            include_exclusions=False,
            include_vte=True,
            confirm_destructive=True,
        )
        data = json.loads(result)
        slots = [f["slot"] for f in data["filters"]]
        # Base: 3-9, VTE: 10-58 (7 base × 7 VTE = 49, starting at 10)
        assert slots == list(range(3, 10)) + list(range(10, 10 + 49))
