"""
Assignment Commands Tests

Tests for grandMA2 Assign command generation.
Assign commands are used to assign objects to executors, layouts, or other targets.

Test Classes:
- TestAssignCommands: Tests for assign, assign_function, assign_fade, assign_to_layout
"""



class TestAssignCommands:
    """Tests for Assign keyword commands."""

    # ---- Basic Assign ----

    def test_assign_sequence_to_executor(self):
        """Test assign sequence to executor."""
        from src.commands import assign

        result = assign("sequence", 1, "executor", 6)
        assert result == "assign sequence 1 at executor 6"

    def test_assign_sequence_range_to_executor_range(self):
        """Test assign sequence range to executor range."""
        from src.commands import assign

        result = assign("sequence", 1, "executor", 6, source_end=5, target_end=10)
        assert result == "assign sequence 1 thru 5 at executor 6 thru 10"

    def test_assign_dmx_to_channel(self):
        """Test assign DMX address to channel."""
        from src.commands import assign

        result = assign("dmx", "2.101", "channel", 5)
        assert result == "assign dmx 2.101 at channel 5"

    def test_assign_group_to_layout(self):
        """Test assign group to layout with coordinates."""
        from src.commands import assign

        result = assign("group", 1, "layout", 1, x=5, y=2)
        assert result == "assign group 1 at layout 1 /x=5 /y=2"

    def test_assign_with_password(self):
        """Test assign user with password."""
        from src.commands import assign

        result = assign("user", "JohnDoe", password="qwerty")
        assert result == 'assign user JohnDoe /password="qwerty"'

    def test_assign_with_cue_mode(self):
        """Test assign with cue_mode option - use assign_function for this."""
        from src.commands import assign_function

        result = assign_function("go", "execbutton1", "1.1", cue_mode="xassert")
        assert result == "assign go at execbutton1 1.1 /cue_mode=xassert"

    def test_assign_with_reset(self):
        """Test assign with reset option."""
        from src.commands import assign

        result = assign("dmx", "1.1", "channel", 1, reset=True)
        assert result == "assign dmx 1.1 at channel 1 /reset"

    def test_assign_with_break(self):
        """Test assign with break option."""
        from src.commands import assign

        result = assign("dmx", "1.1", "fixture", 1, break_=2)
        assert result == "assign dmx 1.1 at fixture 1 /break=2"

    # ---- assign_function ----

    def test_assign_function_toggle(self):
        """Test assign toggle function to executor."""
        from src.commands import assign_function

        result = assign_function("Toggle", "executor", 101)
        assert result == "assign toggle at executor 101"

    def test_assign_function_go_with_cue_mode(self):
        """Test assign go function with cue_mode."""
        from src.commands import assign_function

        result = assign_function("Go", "execbutton1", "1.1", cue_mode="xassert")
        assert result == "assign go at execbutton1 1.1 /cue_mode=xassert"

    # ---- assign_fade ----

    def test_assign_fade_basic(self):
        """Test assign fade time to cue."""
        from src.commands import assign_fade

        result = assign_fade(3, 5)
        assert result == "assign fade 3 cue 5"

    def test_assign_fade_with_sequence(self):
        """Test assign fade time with sequence."""
        from src.commands import assign_fade

        result = assign_fade(2.5, 3, sequence_id=1)
        assert result == "assign fade 2.5 cue 3 sequence 1"

    # ---- assign_to_layout ----

    def test_assign_to_layout_basic(self):
        """Test assign object to layout with position."""
        from src.commands import assign_to_layout

        result = assign_to_layout("group", 1, 1, x=5, y=2)
        assert result == "assign group 1 at layout 1 /x=5 /y=2"

    def test_assign_to_layout_range(self):
        """Test assign object range to layout."""
        from src.commands import assign_to_layout

        result = assign_to_layout("macro", 1, 2, x=0, y=0, end=5)
        assert result == "assign macro 1 thru 5 at layout 2 /x=0 /y=0"
