"""Tests for MCP completions module."""

from __future__ import annotations

import pytest

from src.completions import _complete_prompt, _complete_resource


class _FakeRef:
    """Minimal stand-in for PromptReference / ResourceTemplateReference."""

    def __init__(self, name: str = "", uri: str = ""):
        self.name = name
        self.uri = uri


class _FakeArg:
    """Minimal stand-in for CompletionArgument."""

    def __init__(self, name: str, value: str = ""):
        self.name = name
        self.value = value


# ── Resource template completions ──


class TestResourceCompletions:
    def test_sequence_id_completion_no_prefix(self):
        ref = _FakeRef(uri="gma2://show/sequences/{seq_id}/cues")
        arg = _FakeArg(name="seq_id", value="")
        result = _complete_resource(ref, arg)
        assert result is not None
        assert "1" in result.values
        assert "50" in result.values
        assert len(result.values) == 50

    def test_sequence_id_completion_with_prefix(self):
        ref = _FakeRef(uri="gma2://show/sequences/{seq_id}/cues")
        arg = _FakeArg(name="seq_id", value="1")
        result = _complete_resource(ref, arg)
        assert result is not None
        # "1", "10"-"19" = 11 matches
        assert "1" in result.values
        assert "10" in result.values
        assert "2" not in result.values

    def test_unknown_resource_returns_none(self):
        ref = _FakeRef(uri="gma2://unknown/thing")
        arg = _FakeArg(name="id", value="")
        result = _complete_resource(ref, arg)
        assert result is None

    def test_unknown_argument_returns_none(self):
        ref = _FakeRef(uri="gma2://show/sequences/{seq_id}/cues")
        arg = _FakeArg(name="unknown_param", value="")
        result = _complete_resource(ref, arg)
        assert result is None


# ── Prompt completions ──


class TestPromptCompletions:
    def test_color_chase_fixture_group(self):
        ref = _FakeRef(name="program-color-chase")
        arg = _FakeArg(name="fixture_group", value="")
        result = _complete_prompt(ref, arg)
        assert result is not None
        assert "1" in result.values
        assert "20" in result.values

    def test_color_chase_color_count(self):
        ref = _FakeRef(name="program-color-chase")
        arg = _FakeArg(name="color_count", value="")
        result = _complete_prompt(ref, arg)
        assert result is not None
        assert "4" in result.values
        assert "8" in result.values

    def test_color_chase_color_count_filter(self):
        ref = _FakeRef(name="program-color-chase")
        arg = _FakeArg(name="color_count", value="1")
        result = _complete_prompt(ref, arg)
        assert result is not None
        assert "10" in result.values
        assert "12" in result.values
        assert "4" not in result.values

    def test_setup_moving_lights_fixture_type(self):
        ref = _FakeRef(name="setup-moving-lights")
        arg = _FakeArg(name="fixture_type", value="mac")
        result = _complete_prompt(ref, arg)
        assert result is not None
        assert any("Mac" in v for v in result.values)
        assert not any("Generic" in v for v in result.values)

    def test_setup_moving_lights_start_address(self):
        ref = _FakeRef(name="setup-moving-lights")
        arg = _FakeArg(name="start_address", value="")
        result = _complete_prompt(ref, arg)
        assert result is not None
        assert "1" in result.values

    def test_setup_moving_lights_count(self):
        ref = _FakeRef(name="setup-moving-lights")
        arg = _FakeArg(name="count", value="")
        result = _complete_prompt(ref, arg)
        assert result is not None
        assert "8" in result.values

    def test_create_cue_sequence_id(self):
        ref = _FakeRef(name="create-cue-sequence")
        arg = _FakeArg(name="sequence_id", value="")
        result = _complete_prompt(ref, arg)
        assert result is not None
        assert "1" in result.values
        assert "50" in result.values

    def test_create_cue_sequence_cue_count(self):
        ref = _FakeRef(name="create-cue-sequence")
        arg = _FakeArg(name="cue_count", value="")
        result = _complete_prompt(ref, arg)
        assert result is not None
        assert "5" in result.values

    def test_unknown_prompt_returns_none(self):
        ref = _FakeRef(name="nonexistent-prompt")
        arg = _FakeArg(name="whatever", value="")
        result = _complete_prompt(ref, arg)
        assert result is None

    def test_unknown_argument_returns_none(self):
        ref = _FakeRef(name="program-color-chase")
        arg = _FakeArg(name="nonexistent_param", value="")
        result = _complete_prompt(ref, arg)
        assert result is None

    def test_has_more_is_false(self):
        """All our completions are finite — hasMore should always be False."""
        ref = _FakeRef(name="program-color-chase")
        arg = _FakeArg(name="fixture_group", value="")
        result = _complete_prompt(ref, arg)
        assert result is not None
        assert result.hasMore is False

    def test_total_matches_values_length(self):
        ref = _FakeRef(name="create-cue-sequence")
        arg = _FakeArg(name="cue_count", value="")
        result = _complete_prompt(ref, arg)
        assert result is not None
        assert result.total == len(result.values)
