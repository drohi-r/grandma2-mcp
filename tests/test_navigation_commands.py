"""
Tests for grandMA2 ChangeDest (cd) command string generation.

Tests all documented CD forms from the grandMA2 v3.9 manual:
  cd /                          - Go to root
  cd ..                         - Go up one level
  cd [Element-index]            - Navigate by numeric index
  cd "Element name"             - Navigate by element name
  cd [Object-type].[Object-ID] - Navigate by object type and ID (dot notation)
"""

from src.commands import changedest


class TestChangeDestCommands:
    """Tests for changedest() — navigate the console object tree."""

    def test_root(self):
        assert changedest("/") == "cd /"

    def test_up_one_level(self):
        assert changedest("..") == "cd .."

    def test_by_index(self):
        assert changedest("5") == "cd 5"

    def test_by_quoted_name(self):
        assert changedest('"MySequence"') == 'cd "MySequence"'

    def test_object_type_with_int_id_dot_notation(self):
        """cd Group.1 — dot notation for object type + ID."""
        assert changedest("Group", 1) == "cd Group.1"

    def test_object_type_with_string_id_dot_notation(self):
        """cd Preset.4.1 — dot notation with compound ID."""
        assert changedest("Preset", "4.1") == "cd Preset.4.1"

    def test_sequence_dot_notation(self):
        assert changedest("Sequence", 3) == "cd Sequence.3"

    def test_fixture_dot_notation(self):
        assert changedest("Fixture", 42) == "cd Fixture.42"

    def test_object_type_without_id(self):
        """Object type alone (no ID) is valid — navigates to the type pool."""
        assert changedest("Group") == "cd Group"

    def test_keyword_object_id(self):
        assert changedest("Group", object_id=1) == "cd Group.1"

    def test_keyword_object_id_string(self):
        assert changedest("Sequence", object_id="3") == "cd Sequence.3"
