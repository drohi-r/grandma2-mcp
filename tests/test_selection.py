"""
Selection Commands Tests

Tests for grandMA2 selection and clear command generation.
Includes SelFix (select fixtures) and Clear command series.

Test Classes:
- TestFixtureCommands: Tests for select_fixture, clear series
"""



class TestFixtureCommands:
    """Tests for fixture-related commands."""

    # ---- Single fixture selection ----

    def test_select_fixture_single(self):
        """Test selecting a single fixture: selfix fixture 1"""
        from src.commands import select_fixture

        result = select_fixture(1)
        assert result == "selfix fixture 1"

    def test_select_fixture_single_large_id(self):
        """Test selecting a single fixture with large ID: selfix fixture 101"""
        from src.commands import select_fixture

        result = select_fixture(101)
        assert result == "selfix fixture 101"

    # ---- Multiple fixture (list) selection ----

    def test_select_fixture_multiple_ids(self):
        """Test selecting multiple non-contiguous fixtures: selfix fixture 1 + 3 + 5"""
        from src.commands import select_fixture

        result = select_fixture([1, 3, 5])
        assert result == "selfix fixture 1 + 3 + 5"

    def test_select_fixture_list_with_single_id(self):
        """Test that a list with single element equals selecting a single fixture"""
        from src.commands import select_fixture

        result = select_fixture([7])
        assert result == "selfix fixture 7"

    # ---- Range selection (using thru) ----

    def test_select_fixture_range(self):
        """Test selecting a range: selfix fixture 1 thru 10"""
        from src.commands import select_fixture

        result = select_fixture(1, 10)
        assert result == "selfix fixture 1 thru 10"

    def test_select_fixture_with_same_start_end(self):
        """Test that same start and end selects a single fixture"""
        from src.commands import select_fixture

        result = select_fixture(5, 5)
        assert result == "selfix fixture 5"

    # ---- Select from beginning to specified number (Fixture Thru X) ----

    def test_select_fixture_from_beginning(self):
        """Test selecting from beginning to specified number: selfix fixture thru 10"""
        from src.commands import select_fixture

        result = select_fixture(end=10)
        assert result == "selfix fixture thru 10"

    # ---- Select from specified number to end (Fixture X Thru) ----

    def test_select_fixture_to_end(self):
        """Test selecting from specified number to end: selfix fixture 5 thru"""
        from src.commands import select_fixture

        result = select_fixture(start=5, thru_all=True)
        assert result == "selfix fixture 5 thru"

    # ---- Select all (Fixture Thru) ----

    def test_select_fixture_all(self):
        """Test selecting all fixtures: selfix fixture thru"""
        from src.commands import select_fixture

        result = select_fixture(select_all=True)
        assert result == "selfix fixture thru"

    # ---- Clear commands ----

    def test_clear(self):
        """Test clear command - sequentially clears selection, active values, or programmer."""
        from src.commands import clear

        result = clear()
        assert result == "clear"

    def test_clear_selection(self):
        """Test clearing selection - deselects all fixtures."""
        from src.commands import clear_selection

        result = clear_selection()
        assert result == "clearselection"

    def test_clear_active(self):
        """Test clearing active values - inactivates all values in programmer."""
        from src.commands import clear_active

        result = clear_active()
        assert result == "clearactive"

    def test_clear_all(self):
        """Test clearing all - empties the entire programmer."""
        from src.commands import clear_all

        result = clear_all()
        assert result == "clearall"


class TestFixLocateInvertAlign:
    """Tests for Fix, Locate, Invert, Align keywords."""

    def test_fix_bare(self):
        from src.commands import fix_fixture
        assert fix_fixture() == "fix"

    def test_fix_single(self):
        from src.commands import fix_fixture
        assert fix_fixture(1) == "fix fixture 1"

    def test_fix_range(self):
        from src.commands import fix_fixture
        assert fix_fixture(1, end=10) == "fix fixture 1 thru 10"

    def test_fix_list(self):
        from src.commands import fix_fixture
        assert fix_fixture([1, 3, 5]) == "fix fixture 1 + 3 + 5"

    def test_locate(self):
        from src.commands import locate
        assert locate() == "locate"

    def test_invert(self):
        from src.commands import invert
        assert invert() == "invert"

    def test_align(self):
        from src.commands import align
        assert align() == "align"
