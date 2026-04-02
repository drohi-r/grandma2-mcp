"""
Tests for grandMA2 Vocabulary & Safety-Tier Classification Module
"""

import pytest

from src.vocab import (
    KeywordCategory,
    KeywordKind,
    RiskTier,
    _load_keywords_from_json,
    _norm_token,
    build_v39_spec,
    classify_token,
    parse_changedest,
    parse_list,
)


@pytest.fixture
def spec():
    """Build the v3.9 vocabulary spec for testing."""
    return build_v39_spec()


# =============================================================================
# Normalization
# =============================================================================


class TestNormToken:
    def test_lowercase(self):
        assert _norm_token("GoBack") == "goback"

    def test_strip_whitespace(self):
        assert _norm_token("  Store  ") == "store"

    def test_collapse_internal_spaces(self):
        assert _norm_token("Plus  +") == "plus +"

    def test_empty_string(self):
        assert _norm_token("") == ""


# =============================================================================
# JSON loading
# =============================================================================


class TestLoadKeywords:
    def test_missing_file_gives_helpful_error(self):
        with pytest.raises(FileNotFoundError, match="keyword vocabulary file not found"):
            _load_keywords_from_json("/nonexistent/path/keywords.json")

    def test_loads_object_keywords(self, spec):
        """Object keywords should be populated from schema v2.0."""
        assert len(spec.object_keywords) >= 48
        assert "Channel" in spec.object_keywords
        assert "Fixture" in spec.object_keywords
        assert "FixtureType" in spec.object_keywords

    def test_cuepart_not_in_vocabulary(self, spec):
        """CuePart was removed -- it errors on console. Use Part."""
        assert "CuePart" not in spec.object_keywords
        result = classify_token("CuePart", spec)
        assert result.kind == KeywordKind.UNKNOWN


# =============================================================================
# classify_token
# =============================================================================


class TestClassifyToken:
    def test_known_keyword(self, spec):
        result = classify_token("Store", spec)
        assert result.kind == KeywordKind.KEYWORD
        assert result.canonical == "Store"
        assert result.risk == RiskTier.DESTRUCTIVE

    def test_case_insensitive(self, spec):
        result = classify_token("store", spec)
        assert result.kind == KeywordKind.KEYWORD
        assert result.canonical == "Store"
        assert result.risk == RiskTier.DESTRUCTIVE

    def test_safe_read_keyword(self, spec):
        result = classify_token("Info", spec)
        assert result.risk == RiskTier.SAFE_READ

    def test_safe_write_keyword(self, spec):
        result = classify_token("Go", spec)
        assert result.risk == RiskTier.SAFE_WRITE

    def test_destructive_keyword(self, spec):
        result = classify_token("Delete", spec)
        assert result.risk == RiskTier.DESTRUCTIVE

    def test_unknown_keyword(self, spec):
        result = classify_token("NotAKeyword", spec)
        assert result.kind == KeywordKind.UNKNOWN
        assert result.canonical is None
        assert result.risk == RiskTier.UNKNOWN
        assert result.category is None

    def test_alias_shortcut(self, spec):
        result = classify_token("li", spec)
        assert result.kind == KeywordKind.KEYWORD
        assert result.canonical == "List"
        assert result.risk == RiskTier.SAFE_READ

    def test_changedest_alias(self, spec):
        result = classify_token("cd", spec)
        assert result.kind == KeywordKind.KEYWORD
        assert result.canonical == "ChangeDest"

    def test_cd_special_dotdot(self, spec):
        result = classify_token("..", spec)
        assert result.kind == KeywordKind.PUNCT_TOKEN
        assert result.risk == RiskTier.SAFE_READ

    def test_cd_special_slash(self, spec):
        result = classify_token("/", spec)
        assert result.kind == KeywordKind.PUNCT_TOKEN

    def test_special_char_entry(self, spec):
        result = classify_token("Plus +", spec)
        assert result.kind == KeywordKind.SPECIAL_CHAR_ENTRY

    def test_special_char_dot(self, spec):
        result = classify_token("Dot .", spec)
        assert result.kind == KeywordKind.SPECIAL_CHAR_ENTRY


# =============================================================================
# Object Keyword classification
# =============================================================================


class TestObjectKeywordClassification:
    """Verify all 48 official Object Keywords + extras are properly classified."""

    OFFICIAL_48 = [
        "Agenda", "Attribute", "ButtonPage", "Camera", "Channel",
        "ChannelFader", "Cue", "Default", "Dmx", "DmxUniverse",
        "Effect", "ExecButton1", "ExecButton2", "ExecButton3",
        "Executor", "Fader", "FaderPage", "Feature", "Filter",
        "Fixture", "FixtureType", "Form", "Full", "Group",
        "Layout", "Macro", "Mask", "MAtricks", "Normal", "Page",
        "Part", "Preset", "PresetType", "PreviewExecutor", "Remote",
        "Root", "Screen", "Selection", "Sequence", "SpecialMaster",
        "Timecode", "TimecodeSlot", "Timer", "User", "UserProfile",
        "View", "ViewButton", "ViewPage", "World", "Zero",
    ]

    EXTRA_VERIFIED = [
        "Gel", "Image", "Messages", "Programmer",
        "SoundChannel", "RdmFixtureType",
    ]

    def test_all_official_object_keywords_present(self, spec):
        missing = [kw for kw in self.OFFICIAL_48 if kw not in spec.object_keywords]
        assert missing == [], f"Missing Object Keywords: {missing}"

    def test_extra_verified_keywords_present(self, spec):
        missing = [kw for kw in self.EXTRA_VERIFIED if kw not in spec.object_keywords]
        assert missing == [], f"Missing extra Object Keywords: {missing}"

    def test_object_keywords_are_safe_write(self, spec):
        wrong_tier = []
        for kw in self.OFFICIAL_48:
            result = classify_token(kw, spec)
            if result.risk != RiskTier.SAFE_WRITE:
                wrong_tier.append((kw, result.risk))
        assert wrong_tier == [], f"Object Keywords not SAFE_WRITE: {wrong_tier}"

    def test_object_keywords_have_object_category(self, spec):
        wrong_cat = []
        for kw in self.OFFICIAL_48:
            result = classify_token(kw, spec)
            if result.category != KeywordCategory.OBJECT:
                wrong_cat.append((kw, result.category))
        assert wrong_cat == [], f"Object Keywords wrong category: {wrong_cat}"

    def test_channel_resets_context(self, spec):
        """Channel changes prompt to [Channel]> -- verified via live telnet."""
        entry = spec.object_keyword_entries.get("Channel")
        assert entry is not None
        assert entry.context_change is True

    def test_default_resets_context(self, spec):
        """Default resets prompt to [Channel]> -- verified via live telnet."""
        entry = spec.object_keyword_entries.get("Default")
        assert entry is not None
        assert entry.context_change is True

    def test_full_normal_zero_no_context_change(self, spec):
        """Full, Normal, Zero set dimmer values but don't change context."""
        for kw in ("Full", "Normal", "Zero"):
            entry = spec.object_keyword_entries.get(kw)
            assert entry is not None, f"{kw} missing from entries"
            assert entry.context_change is False, (
                f"{kw} should have context_change=False"
            )

    def test_appearance_is_not_object_keyword(self, spec):
        """Appearance is a Function Keyword (destructive), not Object."""
        assert "Appearance" not in spec.object_keywords
        result = classify_token("Appearance", spec)
        assert result.category == KeywordCategory.FUNCTION
        assert result.risk == RiskTier.DESTRUCTIVE

    def test_part_replaces_cuepart(self, spec):
        """Part is the correct keyword; CuePart errors on console."""
        assert "Part" in spec.object_keywords
        result_part = classify_token("Part", spec)
        assert result_part.category == KeywordCategory.OBJECT
        assert result_part.risk == RiskTier.SAFE_WRITE

        result_cuepart = classify_token("CuePart", spec)
        assert result_cuepart.kind == KeywordKind.UNKNOWN


# =============================================================================
# Alias resolution
# =============================================================================


class TestAliases:
    """Verify console alias keywords resolve correctly."""

    def test_dmx_alias(self, spec):
        result = classify_token("DMX", spec)
        assert result.canonical == "Dmx"
        assert result.risk == RiskTier.SAFE_WRITE
        assert result.category == KeywordCategory.OBJECT

    def test_dmxuniverse_alias(self, spec):
        result = classify_token("DMXUniverse", spec)
        assert result.canonical == "DmxUniverse"
        assert result.risk == RiskTier.SAFE_WRITE
        assert result.category == KeywordCategory.OBJECT

    def test_sound_alias(self, spec):
        result = classify_token("Sound", spec)
        assert result.canonical == "SoundChannel"
        assert result.category == KeywordCategory.OBJECT

    def test_rdm_alias(self, spec):
        result = classify_token("RDM", spec)
        assert result.canonical == "RdmFixtureType"
        assert result.category == KeywordCategory.OBJECT

    def test_existing_aliases_still_work(self, spec):
        """Pre-existing aliases (li, listef, etc.) still resolve."""
        result = classify_token("li", spec)
        assert result.canonical == "List"
        assert result.risk == RiskTier.SAFE_READ


# =============================================================================
# Risk tier coverage: all implemented command builder keywords should have a tier
# =============================================================================


class TestRiskTierCoverage:
    """Verify that all keywords used in src/commands/ have a defined risk tier."""

    IMPLEMENTED_KEYWORDS = [
        # Function keywords from src/commands/
        "Store", "Delete", "Copy", "Move", "Edit", "Cut", "Paste",
        "Label", "Appearance", "Assign", "Remove", "Empty",
        # Playback
        "Go", "GoBack", "Goto", "GoFastBack", "GoFastForward",
        "DefGoBack", "DefGoForward", "DefGoPause", "Pause",
        # Selection & Clear
        "SelFix", "Clear", "ClearAll", "ClearSelection", "ClearActive",
        # Values
        "At", "Call", "Park", "Unpark",
        # Info
        "List", "Info",
        # Variables
        "SetVar", "SetUserVar", "AddVar", "AddUserVar",
        # TempFader
        "TempFader",
    ]

    def test_all_implemented_keywords_have_risk_tier(self, spec):
        missing = []
        for kw in self.IMPLEMENTED_KEYWORDS:
            result = classify_token(kw, spec)
            if result.risk == RiskTier.UNKNOWN:
                missing.append(kw)
        assert missing == [], f"Keywords missing risk tier: {missing}"


# =============================================================================
# Keyword category coverage
# =============================================================================


class TestKeywordCategories:
    """Verify keyword category assignments."""

    def test_function_keywords_have_function_category(self, spec):
        function_kws = ["Store", "Delete", "Go", "Info", "List", "Assign"]
        for kw in function_kws:
            result = classify_token(kw, spec)
            assert result.category == KeywordCategory.FUNCTION, (
                f"{kw} should be FUNCTION, got {result.category}"
            )

    def test_helping_keywords_have_helping_category(self, spec):
        # "And", "Delay", "Fade", "If", "Thru" are pure helping keywords
        helping_kws = ["And", "Delay", "Fade", "If", "Thru"]
        for kw in helping_kws:
            result = classify_token(kw, spec)
            assert result.category == KeywordCategory.HELPING, (
                f"{kw} should be HELPING, got {result.category}"
            )

    def test_special_chars_have_special_char_category(self, spec):
        result = classify_token("Plus +", spec)
        assert result.category == KeywordCategory.SPECIAL_CHAR

    def test_at_is_function_category(self, spec):
        """At appears in both function and helping; function takes precedence."""
        result = classify_token("At", spec)
        assert result.category == KeywordCategory.FUNCTION

    def test_part_is_object_category(self, spec):
        """Part appears in both object and helping; object takes precedence."""
        result = classify_token("Part", spec)
        assert result.category == KeywordCategory.OBJECT


# =============================================================================
# Canonical spelling round-trip
# =============================================================================


class TestCanonicalSpelling:
    """Verify that canonical spellings are preserved correctly."""

    def test_compound_keywords(self, spec):
        compound = [
            ("selfix", "SelFix"),
            ("goback", "GoBack"),
            ("gofastback", "GoFastBack"),
            ("clearall", "ClearAll"),
            ("defgoback", "DefGoBack"),
            ("listuservar", "ListUserVar"),
            ("changedest", "ChangeDest"),
        ]
        for normalized, expected in compound:
            result = classify_token(normalized, spec)
            assert result.canonical == expected, (
                f"Expected canonical '{expected}' for '{normalized}', "
                f"got '{result.canonical}'"
            )

    def test_object_keyword_canonical_spellings(self, spec):
        """Object Keywords preserve their canonical casing."""
        cases = [
            ("channel", "Channel"),
            ("fixturetype", "FixtureType"),
            ("matricks", "MAtricks"),
            ("presettype", "PresetType"),
            ("specialmaster", "SpecialMaster"),
            ("execbutton1", "ExecButton1"),
        ]
        for normalized, expected in cases:
            result = classify_token(normalized, spec)
            assert result.canonical == expected, (
                f"Expected canonical '{expected}' for '{normalized}', "
                f"got '{result.canonical}'"
            )


# =============================================================================
# parse_changedest
# =============================================================================


class TestParseChangeDest:
    def test_no_args(self, spec):
        result = parse_changedest([], spec)
        assert result.mode == "UNKNOWN"

    def test_dotdot(self, spec):
        result = parse_changedest([".."], spec)
        assert result.mode == "UP_ONE_LEVEL"

    def test_slash(self, spec):
        result = parse_changedest(["/"], spec)
        assert result.mode == "ROOT"

    def test_element_index(self, spec):
        result = parse_changedest(["5"], spec)
        assert result.mode == "INDEX"
        assert result.arg1 == "5"

    def test_element_name(self, spec):
        result = parse_changedest(['"MySequence"'], spec)
        assert result.mode == "NAME"
        assert result.arg1 == "MySequence"

    def test_object_type_and_id(self, spec):
        result = parse_changedest(["Sequence", "3"], spec)
        assert result.mode == "OBJECT"
        assert result.arg1 == "Sequence"
        assert result.arg2 == "3"


# =============================================================================
# parse_list
# =============================================================================


class TestParseList:
    def test_empty(self, spec):
        result = parse_list([], spec)
        assert result.object_list is None
        assert result.options == {}
        assert result.discovery is False

    def test_discovery(self, spec):
        result = parse_list(["/?"], spec)
        assert result.discovery is True

    def test_object_list(self, spec):
        result = parse_list(["Preset", "4"], spec)
        assert result.object_list == "Preset 4"

    def test_option_flag(self, spec):
        result = parse_list(["/noconfirm"], spec)
        assert result.options == {"noconfirm": "true"}

    def test_option_with_value(self, spec):
        result = parse_list(["/source=output"], spec)
        assert result.options == {"source": "output"}

    def test_mixed_object_and_options(self, spec):
        result = parse_list(["Preset", "4", "/source=output"], spec)
        assert result.object_list == "Preset 4"
        assert result.options == {"source": "output"}


# =============================================================================
# VocabSpec construction
# =============================================================================


class TestVocabSpec:
    def test_spec_has_canonical_keywords(self, spec):
        assert len(spec.canonical_keywords) > 50

    def test_spec_has_normalized_map(self, spec):
        assert "store" in spec.normalized_to_canonical
        assert spec.normalized_to_canonical["store"] == "Store"

    def test_changedest_aliases(self, spec):
        assert "cd" in spec.changedest_aliases
        assert spec.changedest_aliases["cd"] == "ChangeDest"

    def test_list_discovery_token(self, spec):
        assert spec.list_option_discovery == "/?"

    def test_spec_has_object_keywords(self, spec):
        assert len(spec.object_keywords) >= 48
        assert isinstance(spec.object_keywords, frozenset)

    def test_spec_has_keyword_categories(self, spec):
        assert "Channel" in spec.keyword_categories
        assert spec.keyword_categories["Channel"] == KeywordCategory.OBJECT

    def test_spec_has_object_keyword_entries(self, spec):
        assert "Channel" in spec.object_keyword_entries
        entry = spec.object_keyword_entries["Channel"]
        assert entry.canonical == "Channel"
        assert entry.context_change is True


class TestPlaybackControlKeywords:
    """Regression tests for playback_control keywords verified live but absent
    from the JSON vocabulary. Kill was missing from _extra_keywords; Off/On/
    Release/Toggle work via JSON normalization. Fixed 2026-03-30."""

    PLAYBACK_KEYWORDS = ["Off", "On", "Kill", "Release", "Toggle"]

    def test_kill_resolves(self, spec):
        result = classify_token("Kill", spec)
        assert result.kind == KeywordKind.KEYWORD
        assert result.canonical == "Kill"

    def test_kill_is_safe_write(self, spec):
        result = classify_token("Kill", spec)
        assert result.risk == RiskTier.SAFE_WRITE

    def test_kill_is_function_category(self, spec):
        result = classify_token("Kill", spec)
        assert result.category == KeywordCategory.FUNCTION

    def test_kill_case_insensitive(self, spec):
        result = classify_token("kill", spec)
        assert result.canonical == "Kill"
        assert result.risk == RiskTier.SAFE_WRITE

    def test_all_playback_keywords_resolve(self, spec):
        for kw in self.PLAYBACK_KEYWORDS:
            result = classify_token(kw, spec)
            assert result.kind != KeywordKind.UNKNOWN, f"{kw} returned UNKNOWN"
            assert result.risk == RiskTier.SAFE_WRITE, f"{kw} risk={result.risk}"

    def test_all_playback_keywords_are_function_category(self, spec):
        for kw in self.PLAYBACK_KEYWORDS:
            result = classify_token(kw, spec)
            assert result.category == KeywordCategory.FUNCTION, (
                f"{kw} category={result.category}"
            )

    def test_off_lowercase_resolves_to_canonical(self, spec):
        """'off' (normalized form) must resolve to canonical 'Off', not be stray."""
        result = classify_token("off", spec)
        assert result.canonical == "Off"
        assert result.category == KeywordCategory.FUNCTION
        assert result.risk == RiskTier.SAFE_WRITE
