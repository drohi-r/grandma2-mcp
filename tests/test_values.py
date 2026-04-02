"""
Values Commands Tests

Tests for grandMA2 value setting command generation.
Includes At command series for setting fixture attribute values.

Test Classes:
- TestAtCommands: Tests for at, at_full, at_zero, fixture_at, channel_at, group_at,
                  executor_at, preset_type_at, attribute_at
"""



class TestAtCommands:
    """Tests for At keyword commands."""

    # ---- Basic At value ----

    def test_at_value(self):
        """Test setting dimmer to value: at 75"""
        from src.commands import at

        result = at(75)
        assert result == "at 75"

    def test_at_value_float(self):
        """Test setting dimmer to float value: at 50.5"""
        from src.commands import at

        result = at(50.5)
        assert result == "at 50.5"

    def test_at_full(self):
        """Test at full: at full"""
        from src.commands import at_full

        result = at_full()
        assert result == "at full"

    def test_at_zero(self):
        """Test at zero: at 0"""
        from src.commands import at_zero

        result = at_zero()
        assert result == "at 0"

    # ---- At with Cue ----

    def test_at_cue(self):
        """Test applying cue values: at cue 3"""
        from src.commands import at

        result = at(cue=3)
        assert result == "at cue 3"

    def test_at_cue_with_sequence(self):
        """Test applying cue values with sequence: at cue 3 sequence 1"""
        from src.commands import at

        result = at(cue=3, sequence=1)
        assert result == "at cue 3 sequence 1"

    # ---- At with Fade/Delay ----

    def test_at_fade(self):
        """Test at fade time: at fade 2"""
        from src.commands import at

        result = at(fade=2)
        assert result == "at fade 2"

    def test_at_delay(self):
        """Test at delay time: at delay 2"""
        from src.commands import at

        result = at(delay=2)
        assert result == "at delay 2"

    # ---- At with Options ----

    def test_at_with_layer(self):
        """Test at with layer option."""
        from src.commands import at

        result = at(75, layer="Value")
        assert result == "at 75 /layer=Value"

    def test_at_with_ignoreselection(self):
        """Test at with ignoreselection option."""
        from src.commands import at

        result = at(50, ignoreselection=True)
        assert result == "at 50 /ignoreselection"

    def test_at_with_status(self):
        """Test at with status (tracking values)."""
        from src.commands import at

        result = at(cue=5, status=True)
        assert result == "at cue 5 /status=true"

    # ---- Attribute At ----

    def test_attribute_at_pan(self):
        """Test setting pan attribute: attribute "Pan" at 20"""
        from src.commands import attribute_at

        result = attribute_at("Pan", 20)
        assert result == 'attribute "Pan" at 20'

    def test_attribute_at_tilt(self):
        """Test setting tilt attribute: attribute "Tilt" at 50"""
        from src.commands import attribute_at

        result = attribute_at("Tilt", 50)
        assert result == 'attribute "Tilt" at 50'

    # ---- Fixture At ----

    def test_fixture_at_value(self):
        """Test fixture at value: fixture 2 at 50"""
        from src.commands import fixture_at

        result = fixture_at(2, 50)
        assert result == "fixture 2 at 50"

    def test_fixture_at_fixture(self):
        """Test fixture at fixture: fixture 2 at fixture 3"""
        from src.commands import fixture_at

        result = fixture_at(2, source_fixture=3)
        assert result == "fixture 2 at fixture 3"

    def test_fixture_at_range(self):
        """Test fixture range at value: fixture 1 thru 10 at 100"""
        from src.commands import fixture_at

        result = fixture_at(1, 100, end=10)
        assert result == "fixture 1 thru 10 at 100"

    # ---- Channel At ----

    def test_channel_at_value(self):
        """Test channel at value: channel 1 at 75"""
        from src.commands import channel_at

        result = channel_at(1, 75)
        assert result == "channel 1 at 75"

    def test_channel_at_channel(self):
        """Test channel at channel: channel 1 at channel 10"""
        from src.commands import channel_at

        result = channel_at(1, source_channel=10)
        assert result == "channel 1 at channel 10"

    def test_channel_at_range(self):
        """Test channel range at value: channel 1 thru 10 at 100"""
        from src.commands import channel_at

        result = channel_at(1, 100, end=10)
        assert result == "channel 1 thru 10 at 100"

    # ---- Group At ----

    def test_group_at(self):
        """Test group at value: group 3 at 50"""
        from src.commands import group_at

        result = group_at(3, 50)
        assert result == "group 3 at 50"

    # ---- Executor At ----

    def test_executor_at(self):
        """Test executor at value: executor 3 at 50"""
        from src.commands import executor_at

        result = executor_at(3, 50)
        assert result == "executor 3 at 50"

    # ---- PresetType At ----

    def test_preset_type_at_value(self):
        """Test preset type at value: presettype 2 at 50"""
        from src.commands import preset_type_at

        result = preset_type_at(2, 50)
        assert result == "presettype 2 at 50"

    def test_preset_type_at_range(self):
        """Test preset type range at value: presettype 2 thru 9 at 50"""
        from src.commands import preset_type_at

        result = preset_type_at(2, 50, end_type=9)
        assert result == "presettype 2 thru 9 at 50"

    def test_preset_type_at_delay(self):
        """Test preset type at delay: presettype 2 thru 9 at delay 2"""
        from src.commands import preset_type_at

        result = preset_type_at(2, 2, end_type=9, delay=2)
        assert result == "presettype 2 thru 9 at delay 2"

    def test_preset_type_at_fade(self):
        """Test preset type at fade: presettype 2 at fade 3"""
        from src.commands import preset_type_at

        result = preset_type_at(2, 3, fade=3)
        assert result == "presettype 2 at fade 3"
