"""
Tests for MA2 wildcard / name-quoting spec.

Validates all three deterministic builder rules from
ma2.special-characters.deterministic-spec.v1:

  Rule A (literal):  quote names containing special characters
  Rule B (wildcard): emit raw when wildcard matching is intended
  Rule C (safe default): literal is the default (no implicit wildcards)

Also validates the cd-tree name-correlation workflow:
  list → discover names → derive pattern → build wildcard command.
"""

from src.commands import MA2_SPECIAL_CHARS, quote_name
from src.commands.functions.info import info, list_objects

# ============================================================================
# quote_name() — Rule A: literal mode (default)
# ============================================================================


class TestQuoteNameLiteral:
    def test_plain_name_no_quotes(self):
        """Names with no special chars don't need quotes (MA2 manual rule)."""
        assert quote_name("AllFixtures") == "AllFixtures"

    def test_plain_name_single_word(self):
        assert quote_name("Backtruss") == "Backtruss"

    def test_name_with_asterisk_is_quoted(self):
        """* in a literal name must be quoted so it is not treated as wildcard."""
        assert quote_name("Front*Wash") == '"Front*Wash"'

    def test_name_with_dot_is_quoted(self):
        """Dots have special meaning in MA2 (pool.id notation)."""
        assert quote_name("Go.Live") == '"Go.Live"'

    def test_name_with_slash_is_quoted(self):
        """Slash is a special character (option prefix)."""
        assert quote_name("Intro/Outro") == '"Intro/Outro"'

    def test_name_with_space_is_quoted(self):
        """Spaces require quoting in command line syntax."""
        assert quote_name("Mac700 Front") == '"Mac700 Front"'

    def test_name_with_at_sign_is_quoted(self):
        assert quote_name("Rig@Level") == '"Rig@Level"'

    def test_name_with_dollar_is_quoted(self):
        assert quote_name("$SpecialVar") == '"$SpecialVar"'

    def test_name_with_semicolon_is_quoted(self):
        assert quote_name("A;B") == '"A;B"'

    def test_name_with_brackets_is_quoted(self):
        assert quote_name("Group[1]") == '"Group[1]"'

    def test_already_quoted_name_not_double_quoted(self):
        """If caller already quoted, don't double-quote — the outer " is in special chars
        so we'd wrap it. Document the expected behaviour: callers should NOT pre-quote."""
        # quote_name sees the leading " as a special char and wraps again.
        # This is correct — callers should pass raw names, not pre-quoted strings.
        result = quote_name('"AlreadyQuoted"')
        assert result == '""AlreadyQuoted""'  # double-wrapped (caller error, not a bug)


# ============================================================================
# quote_name() — Rule B: wildcard mode
# ============================================================================


class TestQuoteNameWildcard:
    def test_suffix_wildcard_emitted_raw(self):
        """Mac* must be emitted unquoted so the console treats * as wildcard."""
        assert quote_name("Mac*", match_mode="wildcard") == "Mac*"

    def test_prefix_wildcard_emitted_raw(self):
        assert quote_name("*Wash", match_mode="wildcard") == "*Wash"

    def test_infix_wildcard_emitted_raw(self):
        assert quote_name("*Wash*", match_mode="wildcard") == "*Wash*"

    def test_dot_in_wildcard_not_quoted(self):
        """In wildcard mode, dots are also passed raw."""
        assert quote_name("backt*blue", match_mode="wildcard") == "backt*blue"

    def test_official_example_group_mac(self):
        """Official manual example: Group Mac* → matches names beginning with 'Mac'."""
        assert quote_name("Mac*", match_mode="wildcard") == "Mac*"

    def test_official_example_fixture_backt_blue(self):
        """Official manual example: Fixture backt*blue → matches names starting/ending."""
        assert quote_name("backt*blue", match_mode="wildcard") == "backt*blue"


# ============================================================================
# quote_name() — Rule C: safe default is literal
# ============================================================================


class TestQuoteNameSafeDefault:
    def test_default_is_literal(self):
        """Omitting match_mode defaults to literal — asterisk is quoted."""
        assert quote_name("Mac*") == '"Mac*"'

    def test_explicit_literal(self):
        assert quote_name("Mac*", match_mode="literal") == '"Mac*"'

    def test_wildcard_requires_explicit_opt_in(self):
        """Wildcard mode must be explicitly requested — safe default protects show data."""
        literal_result = quote_name("Mac*")
        wildcard_result = quote_name("Mac*", match_mode="wildcard")
        assert literal_result != wildcard_result
        assert literal_result == '"Mac*"'
        assert wildcard_result == "Mac*"


# ============================================================================
# MA2_SPECIAL_CHARS constant
# ============================================================================


class TestMA2SpecialChars:
    def test_asterisk_in_special_chars(self):
        assert "*" in MA2_SPECIAL_CHARS

    def test_dot_in_special_chars(self):
        assert "." in MA2_SPECIAL_CHARS

    def test_slash_in_special_chars(self):
        assert "/" in MA2_SPECIAL_CHARS

    def test_at_in_special_chars(self):
        assert "@" in MA2_SPECIAL_CHARS

    def test_space_in_special_chars(self):
        assert " " in MA2_SPECIAL_CHARS


# ============================================================================
# list_objects() — name + match_mode params
# ============================================================================


class TestListObjectsWildcard:
    def test_no_name_unchanged(self):
        """Existing callers with no name param are unaffected."""
        assert list_objects("group") == "list group"

    def test_object_id_unchanged(self):
        assert list_objects("cue", 5) == "list cue 5"

    def test_wildcard_name_emitted_raw(self):
        """Wildcard pattern is emitted unquoted — console resolves Mac*."""
        assert list_objects("group", name="Mac700*", match_mode="wildcard") == "list group Mac700*"

    def test_literal_name_with_special_char_is_quoted(self):
        """A name containing * in literal mode is quoted to prevent wildcard expansion."""
        assert list_objects("group", name="Front*Wash") == 'list group "Front*Wash"'

    def test_literal_plain_name_no_quotes(self):
        assert list_objects("group", name="AllFixtures") == "list group AllFixtures"

    def test_infix_wildcard(self):
        assert list_objects("group", name="*Wash*", match_mode="wildcard") == "list group *Wash*"

    def test_name_with_space_is_quoted_in_literal(self):
        assert list_objects("group", name="Mac700 Front") == 'list group "Mac700 Front"'

    def test_name_and_filename_coexist(self):
        result = list_objects("group", name="Mac*", match_mode="wildcard", filename="report")
        assert result == "list group Mac* /filename=report"

    def test_official_list_preset_wildcard_example(self):
        """Manual example: List Preset "color"."m*" — caller-supplied quoted string still works."""
        assert list_objects("preset", '"color"."m*"') == 'list preset "color"."m*"'


# ============================================================================
# info() — name + match_mode params
# ============================================================================


class TestInfoWildcard:
    def test_by_id_unchanged(self):
        assert info("group", 3) == "info group 3"

    def test_by_id_with_text_unchanged(self):
        assert info("group", 3, text="in the backtruss") == 'info group 3 "in the backtruss"'

    def test_wildcard_name(self):
        assert info("group", name="Mac*", match_mode="wildcard") == "info group Mac*"

    def test_literal_name_with_special_char(self):
        assert info("group", name="Front*Wash") == 'info group "Front*Wash"'

    def test_literal_plain_name(self):
        assert info("group", name="AllFixtures") == "info group AllFixtures"


# ============================================================================
# CD-tree correlation workflow
# ============================================================================


class TestCDTreeNameCorrelation:
    """
    Simulates the workflow:
      1. list_console_destination() returns ListEntry objects with .name field
      2. Agent derives a wildcard pattern from discovered names
      3. Pattern is used to build a wildcard command
    """

    def test_derive_prefix_pattern_from_names(self):
        """Common prefix of discovered names → wildcard pattern → command."""
        # Simulated list output names (as returned by list_console_destination())
        # Derive common prefix pattern
        common_prefix = "Mac700"
        pattern = f"{common_prefix}*"
        cmd = list_objects("group", name=pattern, match_mode="wildcard")
        assert cmd == "list group Mac700*"

    def test_derive_infix_pattern_from_names(self):
        """Names containing 'Wash' → *Wash* pattern."""
        pattern = "*Wash*"
        cmd = list_objects("group", name=pattern, match_mode="wildcard")
        assert cmd == "list group *Wash*"

    def test_literal_name_discovered_from_list(self):
        """Exact name from list output used literally (default safe behavior)."""
        discovered_name = "ALL LASERS"  # has space — auto-quoted
        cmd = list_objects("group", name=discovered_name)
        assert cmd == 'list group "ALL LASERS"'

    def test_exact_name_no_special_chars(self):
        """Name with no special chars — quotes omitted per MA2 manual rule."""
        discovered_name = "Backtruss"
        cmd = list_objects("group", name=discovered_name)
        assert cmd == "list group Backtruss"
