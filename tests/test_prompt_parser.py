"""
Tests for grandMA2 telnet prompt and list output parser.

Since the exact MA2 telnet formats are not yet validated against a live
console, these tests cover hypothesized patterns and edge cases.  The
parsers are designed to be refined as real output is captured.
"""

import pytest

from src.prompt_parser import (
    ConsolePrompt,
    ListEntry,
    _split_location,
    parse_list_output,
    parse_prompt,
)

# =========================================================================
# ConsolePrompt dataclass
# =========================================================================


class TestConsolePromptDataclass:
    def test_minimal(self):
        p = ConsolePrompt(raw_response="output")
        assert p.raw_response == "output"
        assert p.prompt_line is None
        assert p.location is None
        assert p.object_type is None
        assert p.object_id is None

    def test_full(self):
        p = ConsolePrompt(
            raw_response="raw",
            prompt_line="[Group 1]>",
            location="Group 1",
            object_type="Group",
            object_id="1",
        )
        assert p.location == "Group 1"
        assert p.object_type == "Group"
        assert p.object_id == "1"

    def test_frozen(self):
        p = ConsolePrompt(raw_response="test")
        with pytest.raises(AttributeError):
            p.raw_response = "changed"


# =========================================================================
# Bracket pattern: [Location]> or [Location]>/
# =========================================================================


class TestBracketPromptPattern:
    def test_object_with_id(self):
        result = parse_prompt("some output\n[Group 1]>")
        assert result.prompt_line == "[Group 1]>"
        assert result.location == "Group 1"
        assert result.object_type == "Group"
        assert result.object_id == "1"

    def test_object_without_id(self):
        result = parse_prompt("[Fixture]>")
        assert result.location == "Fixture"
        assert result.object_type == "Fixture"
        assert result.object_id is None

    def test_root(self):
        result = parse_prompt("[Root]>")
        assert result.location == "Root"
        assert result.object_type == "Root"
        assert result.object_id is None

    def test_channel_default_prompt(self):
        result = parse_prompt("[channel]>")
        assert result.location == "channel"
        assert result.object_type == "channel"
        assert result.object_id is None

    def test_with_trailing_slash(self):
        result = parse_prompt("[Sequence 3]>/")
        assert result.location == "Sequence 3"
        assert result.object_type == "Sequence"
        assert result.object_id == "3"

    def test_with_preceding_output(self):
        raw = "OK\nSome output line\n[Sequence 3]>"
        result = parse_prompt(raw)
        assert result.location == "Sequence 3"
        assert result.object_type == "Sequence"
        assert result.object_id == "3"

    def test_multiline_with_prompt_at_end(self):
        raw = "Entering Group...\nStatus: OK\n[Group 1]>"
        result = parse_prompt(raw)
        assert result.location == "Group 1"

    def test_uses_last_match(self):
        """If multiple bracket prompts exist, use the last one."""
        raw = "[Root]>\ncd Group 1\n[Group 1]>"
        result = parse_prompt(raw)
        assert result.location == "Group 1"

    def test_dot_notation_in_prompt(self):
        """Prompt may show dot notation: [Group.1]>"""
        result = parse_prompt("[Group.1]>")
        assert result.location == "Group.1"
        assert result.object_type == "Group"
        assert result.object_id == "1"

    def test_dot_notation_preset_in_prompt(self):
        """Dot notation with compound ID: [Preset.4.1]>"""
        result = parse_prompt("[Preset.4.1]>")
        assert result.location == "Preset.4.1"
        assert result.object_type == "Preset"
        assert result.object_id == "4.1"


# =========================================================================
# Generic angle-bracket pattern: something>
# =========================================================================


class TestAngleBracketPattern:
    def test_simple_prompt(self):
        result = parse_prompt("Root>")
        assert result.prompt_line == "Root>"
        assert result.location == "Root"
        assert result.object_type == "Root"

    def test_prompt_with_space(self):
        result = parse_prompt("Group 1>")
        assert result.location == "Group 1"
        assert result.object_type == "Group"
        assert result.object_id == "1"


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases:
    def test_empty_string(self):
        result = parse_prompt("")
        assert result.raw_response == ""
        assert result.prompt_line is None
        assert result.location is None

    def test_whitespace_only(self):
        result = parse_prompt("   \n  \n  ")
        assert result.prompt_line is None

    def test_no_recognizable_prompt(self):
        result = parse_prompt("Error: invalid command")
        assert result.raw_response == "Error: invalid command"

    def test_raw_always_preserved(self):
        raw = "line1\nline2\n[Group 1]>"
        result = parse_prompt(raw)
        assert result.raw_response == raw


# =========================================================================
# _split_location helper
# =========================================================================


class TestSplitLocation:
    def test_type_and_id_space(self):
        assert _split_location("Group 1") == ("Group", "1")

    def test_type_and_id_dot(self):
        """Dot notation: Group.1"""
        assert _split_location("Group.1") == ("Group", "1")

    def test_preset_dot_notation(self):
        """Dot notation with compound ID: Preset.4.1"""
        assert _split_location("Preset.4.1") == ("Preset", "4.1")

    def test_type_only(self):
        assert _split_location("Fixture") == ("Fixture", None)

    def test_empty_string(self):
        assert _split_location("") == (None, None)

    def test_non_alpha_start(self):
        assert _split_location("123") == (None, None)

    def test_multi_word_type(self):
        """Multi-word strings that don't match any pattern."""
        assert _split_location("some thing else") == (None, None)


# =========================================================================
# parse_list_output — list feedback parsing
# =========================================================================


class TestParseListOutput:
    def test_empty_string(self):
        result = parse_list_output("")
        assert result.raw_response == ""
        assert result.entries == ()

    def test_whitespace_only(self):
        result = parse_list_output("   \n  ")
        assert result.entries == ()

    def test_dot_notation_entries(self):
        """Parse dot-notation entries: Group.1  Front Wash"""
        raw = "Group.1  Front Wash\nGroup.2  Back Wash\nGroup.3  Sides"
        result = parse_list_output(raw)
        assert len(result.entries) == 3
        assert result.entries[0].object_type == "Group"
        assert result.entries[0].object_id == "1"
        assert result.entries[0].name == "Front Wash"
        assert result.entries[1].object_id == "2"
        assert result.entries[1].name == "Back Wash"
        assert result.entries[2].object_id == "3"
        assert result.entries[2].name == "Sides"

    def test_dot_notation_no_name(self):
        """Entry with type.id but no name."""
        result = parse_list_output("Group.5")
        assert len(result.entries) == 1
        assert result.entries[0].object_type == "Group"
        assert result.entries[0].object_id == "5"
        assert result.entries[0].name is None

    def test_bare_id_entries(self):
        """Parse bare numeric IDs (inside a typed pool after cd)."""
        raw = "1  Front Wash\n2  Back Wash\n3  Sides"
        result = parse_list_output(raw)
        assert len(result.entries) == 3
        assert result.entries[0].object_type is None
        assert result.entries[0].object_id == "1"
        assert result.entries[0].name == "Front Wash"

    def test_bare_id_no_name(self):
        result = parse_list_output("42")
        assert len(result.entries) == 1
        assert result.entries[0].object_id == "42"
        assert result.entries[0].name is None

    def test_quoted_name(self):
        """Names in quotes should have quotes stripped."""
        result = parse_list_output('Group.1  "Front Wash"')
        assert result.entries[0].name == "Front Wash"

    def test_skips_prompt_lines(self):
        """Prompt lines should not be treated as data entries."""
        raw = "Group.1  Front Wash\n[Group]>"
        result = parse_list_output(raw)
        assert len(result.entries) == 1
        assert result.entries[0].object_id == "1"
        assert result.prompt is not None
        assert result.prompt.location == "Group"

    def test_skips_unrecognised_lines(self):
        """Headers, separators, etc. should be skipped."""
        raw = "=== Groups ===\nGroup.1  Front Wash\n---\nGroup.2  Back"
        result = parse_list_output(raw)
        assert len(result.entries) == 2

    def test_raw_always_preserved(self):
        raw = "Group.1  Front Wash\nGroup.2  Back"
        result = parse_list_output(raw)
        assert result.raw_response == raw

    def test_preset_dot_notation(self):
        """Preset entries with compound type.id."""
        raw = "Preset.4.1  Deep Blue\nPreset.4.2  Red"
        result = parse_list_output(raw)
        assert len(result.entries) == 2
        assert result.entries[0].object_type == "Preset"
        assert result.entries[0].object_id == "4.1"
        assert result.entries[0].name == "Deep Blue"

    def test_entries_tuple_is_frozen(self):
        result = parse_list_output("Group.1  Test")
        assert isinstance(result.entries, tuple)


class TestListEntry:
    def test_mutable_with_columns(self):
        """ListEntry is mutable (not frozen) to support the columns dict field."""
        e = ListEntry(object_type="Group", object_id="1", name="Test")
        e.columns = {"key": "value"}
        assert e.columns == {"key": "value"}

    def test_defaults_none(self):
        e = ListEntry()
        assert e.object_type is None
        assert e.object_id is None
        assert e.name is None
        assert e.raw_line is None
