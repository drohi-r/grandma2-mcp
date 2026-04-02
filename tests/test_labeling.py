"""
Labeling Commands Tests

Tests for grandMA2 label and appearance command generation.
Includes Label and Appearance commands.

Test Classes:
- TestLabelCommands: Tests for label, label_group, label_preset
- TestAppearanceCommands: Tests for appearance
"""



class TestLabelCommands:
    """Tests for Label keyword commands."""

    def test_label_group(self):
        """Test label group."""
        from src.commands import label

        result = label("group", 3, "All Studiocolors")
        assert result == 'label group 3 "All Studiocolors"'

    def test_label_fixture_range(self):
        """Test label fixture range with auto-enumerate."""
        from src.commands import label

        result = label("fixture", 1, "Mac700 1", end=10)
        assert result == 'label fixture 1 thru 10 "Mac700 1"'

    def test_label_preset_compound_id(self):
        """Test label preset with compound ID."""
        from src.commands import label

        result = label("preset", '"color"."Red"', "Dark Red")
        assert result == 'label preset "color"."Red" "Dark Red"'

    def test_label_with_plain_name(self):
        """Plain names (no special chars) are emitted without quotes per MA2 spec."""
        from src.commands import label

        result = label("macro", 1, "MyMacro")
        assert result == "label macro 1 MyMacro"

    def test_label_multiple_objects(self):
        """Test label multiple objects — plain name, no quotes needed."""
        from src.commands import label

        result = label("group", [1, 2, 3], "Selected")
        assert result == "label group 1 + 2 + 3 Selected"


class TestAppearanceCommands:
    """Tests for Appearance keyword commands."""

    # ---- RGB Colors ----

    def test_appearance_rgb(self):
        """Test appearance with RGB values."""
        from src.commands import appearance

        result = appearance("preset", "0.1", red=100, green=0, blue=0)
        assert result == "appearance preset 0.1 /r=100 /g=0 /b=0"

    def test_appearance_rgb_full(self):
        """Test appearance with full RGB."""
        from src.commands import appearance

        result = appearance("group", 1, red=50, green=75, blue=100)
        assert result == "appearance group 1 /r=50 /g=75 /b=100"

    # ---- HSB Colors ----

    def test_appearance_hsb(self):
        """Test appearance with HSB values."""
        from src.commands import appearance

        result = appearance("preset", "0.1", hue=0, saturation=100, brightness=50)
        assert result == "appearance preset 0.1 /h=0 /s=100 /br=50"

    def test_appearance_hue_only(self):
        """Test appearance with hue only."""
        from src.commands import appearance

        result = appearance("cue", 1, hue=180)
        assert result == "appearance cue 1 /h=180"

    # ---- Hex Color ----

    def test_appearance_hex_color(self):
        """Test appearance with hex color."""
        from src.commands import appearance

        result = appearance("group", 1, end=5, color="FF0000")
        assert result == "appearance group 1 thru 5 /color=FF0000"

    # ---- Copy from Source ----

    def test_appearance_from_source(self):
        """Test appearance copied from source object."""
        from src.commands import appearance

        result = appearance("macro", 2, source_type="macro", source_id=13)
        assert result == "appearance macro 2 at macro 13"

    def test_appearance_cue_from_group(self):
        """Test appearance cue same as group."""
        from src.commands import appearance

        result = appearance("cue", 1, source_type="group", source_id=2)
        assert result == "appearance cue 1 at group 2"

    # ---- Reset ----

    def test_appearance_reset(self):
        """Test appearance reset."""
        from src.commands import appearance

        result = appearance("preset", 1, reset=True)
        assert result == "appearance preset 1 /reset"

    # ---- Range ----

    def test_appearance_range(self):
        """Test appearance with range."""
        from src.commands import appearance

        result = appearance("group", 1, end=5, hue=240, saturation=100, brightness=75)
        assert result == "appearance group 1 thru 5 /h=240 /s=100 /br=75"

    # ---- Multiple Objects ----

    def test_appearance_multiple_objects(self):
        """Test appearance with multiple objects."""
        from src.commands import appearance

        result = appearance("macro", [1, 3, 5], color="00FF00")
        assert result == "appearance macro 1 + 3 + 5 /color=00FF00"
