"""Tests for src/fixture_types.py — fixture-type intelligence core."""

from __future__ import annotations

from src.fixture_types import (
    CATEGORY_ORDER,
    build_fixture_type_model,
    build_type_ordered_selection,
    capabilities_from_attributes,
    classify_category,
    fallback_capabilities,
    parse_channel_type_rows,
    renumber_commands,
    verify_id_blocks,
)


def _patch_summary() -> dict:
    """Nemesis-style patch: washes, movers, bars, strobes, blinders."""
    fixtures = []
    # 8 washes, correctly in 1-99
    for i in range(1, 9):
        fixtures.append({"id": i, "name": f"Wash {i}", "type": "HY B-EYE K25", "patch": f"1.{i:03d}"})
    # 6 movers in 101-106, one stray at 50 (wrong block)
    for i in range(101, 107):
        fixtures.append({"id": i, "name": f"Spot {i}", "type": "Mac Viper Profile", "patch": f"2.{i:03d}"})
    fixtures.append({"id": 50, "name": "Spot stray", "type": "Mac Viper Profile", "patch": "2.200"})
    # 4 bars at 201-204
    for i in range(201, 205):
        fixtures.append({"id": i, "name": f"Bar {i}", "type": "LED Bar 18", "patch": f"3.{i:03d}"})
    # 2 strobes at 301-302
    for i in range(301, 303):
        fixtures.append({"id": i, "name": f"Strobe {i}", "type": "Atomic 3000", "patch": f"4.{i:03d}"})
    # 2 blinders at 401-402
    for i in range(401, 403):
        fixtures.append({"id": i, "name": f"Blinder {i}", "type": "8-Lite Blinder", "patch": f"5.{i:03d}"})

    fixture_types = [
        {"id": 1, "long_name": "HY B-EYE K25", "short_name": "K25", "manufacturer": "Claypaky"},
        {"id": 2, "long_name": "Mac Viper Profile", "short_name": "Viper", "manufacturer": "Martin"},
        {"id": 3, "long_name": "LED Bar 18", "short_name": "Bar18", "manufacturer": "Generic"},
        {"id": 4, "long_name": "Atomic 3000", "short_name": "Atomic", "manufacturer": "Martin"},
        {"id": 5, "long_name": "8-Lite Blinder", "short_name": "8Lite", "manufacturer": "Generic"},
    ]
    return {
        "showfile": "nemesis_25",
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
        "fixture_types": fixture_types,
        "groups": [],
        "sequences_count": 0,
        "macros_count": 0,
    }


# ---------------------------------------------------------------- capabilities

class TestCapabilities:
    def test_attributes_map_to_flags(self):
        caps = capabilities_from_attributes({"PAN", "TILT", "DIM", "COLORRGB1", "GOBO1", "ZOOM", "FOCUS"})
        assert caps["position"] and caps["dimmer"] and caps["color_mix"]
        assert caps["gobo"] and caps["beam"] and caps["focus"]
        assert not caps["control"]

    def test_control_and_shutter(self):
        caps = capabilities_from_attributes({"CTRL1", "SHUTTER1"})
        assert caps["control"] and caps["beam"]
        assert not caps["position"]

    def test_parse_channel_type_rows(self):
        raw = (
            "[EditSetup]> list\n"
            'ChannelType 1  PAN     "coarse"\n'
            'ChannelType 2  TILT    "coarse"\n'
            'ChannelType 3  DIM\n'
            "ChannelType 4  COLORRGB1\n"
            "some other line\n"
        )
        names = parse_channel_type_rows(raw)
        assert {"PAN", "TILT", "DIM", "COLORRGB1"} <= names

    def test_parse_channel_type_rows_real_console_output(self):
        # Trimmed from a live 3.9.60.50 capture of the VL3500 Spot
        # (verify_captures/discover_type_4.json): ANSI escapes in the header,
        # \n\r line endings, NAME (Shortname) attribute column.
        raw = (
            "Executing : \x1b[32mList\x1b[37m\n\r"
            "\x1b[32m               \x1b[31mNo.  \x1b[32m\x1b[33mAttrib"
            "                                     \x1b[32mBreak  Coarse  Fine\x1b[37m\n\r"
            "ChannelType  1 1    DIM (Dim)                                  1      1       None  None   0.00     100.00            Off   Off     On             Off         Default                              0 0 0    0               Off       (1)\n\r"
            "ChannelType  2 2    PAN (Pan)                                  1      2       3     None   0.00                       Off   Off     Off            Off         Default                              0 0 0    0               Off       (1)\n\r"
            "ChannelType  3 3    TILT (Tilt)                                1      4       5     None   0.00                       Off   Off     Off            Off         Default                              0 0 0    0               Off       (1)\n\r"
            "ChannelType  7 7    COLORRGB1 (R)                              1      9       None  None   100.00   100.00            Off   Off     Off            Off         Default                              255 0 0  0               Off       (1)\n\r"
            "ChannelType 11 11   GOBO1 (G1)                                 1      13      None  None   0.00     0.00              On    Off     Off            Off         Default           Mode!              0 0 0    0               Off       (3)\n\r"
            "ChannelType 12 12   GOBO1_POS (G1<>)                           1      14      15    None   0.00                       Off   Off     Off            Off         Default           GOBO1              0 0 0    0               Off       (3)\n\r"
            "ChannelType 27 27   GOBO1WHEELSELECTMSPEED (Gobo1WheelSelect)  1      30      None  None   100.00                     Off   Off     Off            Off         Default                              0 0 0    0               Off       (1)\n\r"
            "ChannelType 28 28   LAMPCONTROL (LampControl)                  1      31      None  None   0.00                       Off   Off     Off            Off         Default                              0 0 0    0               Off       (18)\n\r"
            "\rEditSetup/FixtureTypes 3/4 VL3500 Spot 00/Modules 1/Main Module 1 >\x1b[K"
        )
        names = parse_channel_type_rows(raw)
        assert {
            "DIM", "PAN", "TILT", "COLORRGB1", "GOBO1",
            "GOBO1_POS", "GOBO1WHEELSELECTMSPEED", "LAMPCONTROL",
        } <= names
        caps = capabilities_from_attributes(names)
        assert caps["dimmer"] and caps["position"] and caps["gobo"] and caps["color_mix"]

    def test_console_attributes_match_composite_type_names(self):
        # Live patch rows carry composite type strings ("4 VL3500 Spot 00" =
        # "{type_id} {long_name} {mode}") while attribute discovery keys by
        # declared long_name — the model must still bind them.
        patch = {
            "showfile": "mcp_verify_demo",
            "fixture_count": 1,
            "fixtures": [
                {"id": 1, "name": "Spot 1", "type": "4 VL3500 Spot 00", "patch": "1.001"},
            ],
            "fixture_types": [
                {"id": 4, "long_name": "VL3500 Spot", "short_name": "VL3500S", "manufacturer": "VariLite"},
            ],
        }
        attrs = {"VL3500 Spot": {"DIM", "PAN", "TILT", "COLORRGB1", "GOBO1", "ZOOM", "FOCUS"}}
        model = build_fixture_type_model(patch, attributes_by_type=attrs)
        rec = model.types["4 VL3500 Spot 00"]
        assert rec.capability_source == "console"
        assert rec.type_id == 4
        assert rec.capabilities["color_mix"] and rec.capabilities["position"]

    def test_fallback_led_rgb(self):
        caps = fallback_capabilities("5 LED - RGB 8 bit")
        assert caps is not None
        assert caps["dimmer"] and caps["color_mix"]
        assert not caps["position"]

    def test_fallback_known_and_unknown(self):
        caps = fallback_capabilities("Mac Viper Profile")
        assert caps and caps["gobo"] and caps["position"]
        assert fallback_capabilities("Mystery Device 9000") is None


# ---------------------------------------------------------------- classification

class TestClassification:
    def test_name_keywords_win(self):
        assert classify_category("HY B-EYE K25", {}) == "wash"
        assert classify_category("Atomic 3000", {}) == "strobe"
        assert classify_category("8-Lite Blinder", {}) == "blinder"
        assert classify_category("LED Bar 18", {}) == "bar"
        assert classify_category("Mac Viper Profile", {}) == "mover"

    def test_capability_heuristics(self):
        mover_caps = {"position": True, "gobo": True}
        assert classify_category("XYZ 500", mover_caps) == "mover"
        wash_caps = {"position": True, "gobo": False}
        assert classify_category("XYZ 500", wash_caps) == "wash"
        dim_caps = {"dimmer": True}
        assert classify_category("XYZ 500", dim_caps) == "conventional"
        assert classify_category("XYZ 500", {}) == "other"


# ---------------------------------------------------------------- model build

class TestModelBuild:
    def test_members_and_categories(self):
        model = build_fixture_type_model(_patch_summary())
        assert set(model.types) == {
            "HY B-EYE K25", "Mac Viper Profile", "LED Bar 18",
            "Atomic 3000", "8-Lite Blinder",
        }
        viper = model.types["Mac Viper Profile"]
        assert viper.category == "mover"
        assert viper.member_ids == [50, 101, 102, 103, 104, 105, 106]
        assert viper.type_id == 2
        assert viper.short_name == "Viper"

    def test_console_attributes_override_fallback(self):
        attrs = {"Mac Viper Profile": {"PAN", "TILT", "DIM"}}
        model = build_fixture_type_model(_patch_summary(), attributes_by_type=attrs)
        viper = model.types["Mac Viper Profile"]
        assert viper.capability_source == "console"
        assert not viper.capabilities["gobo"]     # console said no gobo
        k25 = model.types["HY B-EYE K25"]
        assert k25.capability_source == "fallback"

    def test_capability_query(self):
        model = build_fixture_type_model(_patch_summary())
        color_types = {r.name for r in model.types_with_capability("color_mix")}
        assert "8-Lite Blinder" not in color_types
        assert "HY B-EYE K25" in color_types


# ---------------------------------------------------------------- block verify

class TestVerifyIdBlocks:
    def test_detects_out_of_block_and_plans_renumber(self):
        model = build_fixture_type_model(_patch_summary())
        report = verify_id_blocks(model)
        assert not report["compliant"]
        assert [e["fixture_id"] for e in report["out_of_block"]] == [50]
        plan = report["renumber_plan"]
        assert len(plan) == 1
        # 100 is the lowest free mover slot (101-106 taken)
        assert plan[0]["old_id"] == 50 and plan[0]["new_id"] == 100

    def test_compliant_patch(self):
        patch = _patch_summary()
        patch["fixtures"] = [f for f in patch["fixtures"] if f["id"] != 50]
        report = verify_id_blocks(build_fixture_type_model(patch))
        assert report["compliant"]
        assert report["renumber_plan"] == []

    def test_collision_detection(self):
        patch = _patch_summary()
        patch["fixtures"].append(
            {"id": 1, "name": "Dup", "type": "Atomic 3000", "patch": "9.001"}
        )
        report = verify_id_blocks(build_fixture_type_model(patch))
        assert 1 in report["collisions"]
        assert not report["compliant"]

    def test_full_block_yields_unplannable_entry(self):
        patch = _patch_summary()
        # Fill the entire strobe block 300-399 and add one stray strobe
        patch["fixtures"] = [
            {"id": i, "name": f"S{i}", "type": "Atomic 3000", "patch": f"4.{i - 300 + 1:03d}"}
            for i in range(300, 400)
        ] + [{"id": 999, "name": "Stray", "type": "Atomic 3000", "patch": "4.150"}]
        report = verify_id_blocks(build_fixture_type_model(patch))
        entry = report["renumber_plan"][0]
        assert entry["old_id"] == 999 and entry["new_id"] is None
        assert "no free slot" in entry["error"]

    def test_renumber_commands(self):
        cmds = renumber_commands([
            {"old_id": 50, "new_id": 100, "name": "Spot stray"},
            {"old_id": 999, "new_id": None, "error": "full"},
        ])
        assert cmds == [
            "Setup → Patch & Fixture Schedule → set FixId of "
            "fixture 50 (Spot stray) to 100"
        ]


# ---------------------------------------------------------------- selection

class TestTypeOrderedSelection:
    def test_canonical_order_and_ranges(self):
        model = build_fixture_type_model(_patch_summary())
        cmds = build_type_ordered_selection(model)
        assert cmds[0] == "ClearAll"
        # wash first, then mover (incl. stray 50), bar, strobe, blinder
        assert cmds[1] == "Fixture 1 Thru 8"
        assert cmds[2] == "Fixture 50 + 101 Thru 106"
        assert cmds[3] == "Fixture 201 Thru 204"
        assert cmds[4] == "Fixture 301 Thru 302"
        assert cmds[5] == "Fixture 401 Thru 402"

    def test_custom_order_no_clear(self):
        model = build_fixture_type_model(_patch_summary())
        cmds = build_type_ordered_selection(
            model, order=["strobe", "wash"], clear_first=False
        )
        assert cmds == ["Fixture 301 Thru 302", "Fixture 1 Thru 8"]

    def test_order_constant_covers_all(self):
        model = build_fixture_type_model(_patch_summary())
        cats = {r.category for r in model.types.values()}
        assert cats <= set(CATEGORY_ORDER)
