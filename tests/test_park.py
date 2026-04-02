"""
Park and Unpark Keywords Tests

Tests for grandMA2 Park and Unpark function keyword command generation.

Park keyword:
- Locks DMX output values of attributes
- Can lock fixture selection, attributes, or DMX channels
- Optional value parameter with At keyword

Unpark keyword:
- Unlocks previously parked DMX channels
- Can unpark fixture selection, attributes, or DMX channels

Test Classes:
- TestPark: Tests for Park command generation
- TestUnpark: Tests for Unpark command generation
"""



class TestPark:
    """
    Tests for Park keyword - locks DMX output values.

    Syntax:
        Park [Selection-list] (At [Value])
        Park [Attribute-list] (At [Value])
        Park [DMX-list] (At [Value])
    """

    # ---- Basic Park with object ----

    def test_park_fixture(self):
        """Test park fixture: park fixture 5"""
        from src.commands import park

        result = park("fixture 5")
        assert result == "park fixture 5"

    def test_park_attribute(self):
        """Test park attribute: park attribute "pan" """
        from src.commands import park

        result = park('attribute "pan"')
        assert result == 'park attribute "pan"'

    def test_park_channel_range(self):
        """Test park channel range: park channel 1 thru 5"""
        from src.commands import park

        result = park("channel 1 thru 5")
        assert result == "park channel 1 thru 5"

    def test_park_dmx(self):
        """Test park DMX channel: park dmx 1.2"""
        from src.commands import park

        result = park("dmx 1.2")
        assert result == "park dmx 1.2"

    # ---- Park with At value ----

    def test_park_channel_at_value(self):
        """Test park channel at value: park channel 1 thru 5 at 100"""
        from src.commands import park

        result = park("channel 1 thru 5", at=100)
        assert result == "park channel 1 thru 5 at 100"

    def test_park_fixture_at_value(self):
        """Test park fixture at value: park fixture 1 at 50"""
        from src.commands import park

        result = park("fixture 1", at=50)
        assert result == "park fixture 1 at 50"

    def test_park_dmx_at_value(self):
        """Test park DMX at value: park dmx 1.1 at 255"""
        from src.commands import park

        result = park("dmx 1.1", at=255)
        assert result == "park dmx 1.1 at 255"

    # ---- Park without object (current selection) ----

    def test_park_current_selection(self):
        """Test park current selection: park"""
        from src.commands import park

        result = park()
        assert result == "park"

    def test_park_current_selection_at_value(self):
        """Test park current selection at value: park at 100"""
        from src.commands import park

        result = park(at=100)
        assert result == "park at 100"


class TestUnpark:
    """
    Tests for Unpark keyword - unlocks previously parked DMX channels.

    Syntax:
        Unpark [Selection-list]
        Unpark [Attributes-list]
    """

    # ---- Basic Unpark ----

    def test_unpark_fixture(self):
        """Test unpark fixture: unpark fixture 2"""
        from src.commands import unpark

        result = unpark("fixture 2")
        assert result == "unpark fixture 2"

    def test_unpark_dmx_range(self):
        """Test unpark DMX range: unpark dmx 1.1 thru 1.10"""
        from src.commands import unpark

        result = unpark("dmx 1.1 thru 1.10")
        assert result == "unpark dmx 1.1 thru 1.10"

    def test_unpark_dmx_universe(self):
        """Test unpark all DMX universes: unpark dmxuniverse thru"""
        from src.commands import unpark

        result = unpark("dmxuniverse thru")
        assert result == "unpark dmxuniverse thru"

    def test_unpark_preset_type(self):
        """Test unpark preset type: unpark presettype dimmer"""
        from src.commands import unpark

        result = unpark("presettype dimmer")
        assert result == "unpark presettype dimmer"

    # ---- Unpark current selection ----

    def test_unpark_current_selection(self):
        """Test unpark current selection: unpark"""
        from src.commands import unpark

        result = unpark()
        assert result == "unpark"

