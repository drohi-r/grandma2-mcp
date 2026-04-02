"""Tests for MCP sampling module."""

from __future__ import annotations

import pytest

from src.sampling import (
    _DEFAULT_PREFS,
    _extract_text,
    check_sampling_support,
    generate_cue_suggestions,
    generate_lua_script,
    generate_troubleshooting_advice,
)


class _FakeContent:
    def __init__(self, text: str):
        self.text = text


class _FakeResult:
    def __init__(self, text: str):
        self.content = _FakeContent(text)
        self.model = "test-model"
        self.stopReason = "endTurn"


class TestCheckSamplingSupport:
    @pytest.mark.asyncio
    async def test_returns_false_without_capability(self):
        class FakeSession:
            def check_client_capability(self, cap):
                raise AttributeError("No capabilities")

        result = await check_sampling_support(FakeSession())
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_with_capability(self):
        class FakeSession:
            def check_client_capability(self, cap):
                pass  # no exception = supported

        result = await check_sampling_support(FakeSession())
        assert result is True


class TestExtractText:
    def test_extracts_text_content(self):
        result = _FakeResult("Hello from LLM")
        assert _extract_text(result) == "Hello from LLM"

    def test_handles_non_text_content(self):
        class NoTextContent:
            pass

        class FakeResult:
            content = NoTextContent()

        result = _extract_text(FakeResult())
        assert result is not None  # falls back to str()

    def test_handles_none_content(self):
        class FakeResult:
            content = None

        result = _extract_text(FakeResult())
        assert result is None


class TestGenerateCueSuggestions:
    @pytest.mark.asyncio
    async def test_returns_none_when_unsupported(self):
        class FakeSession:
            def check_client_capability(self, cap):
                raise AttributeError("nope")

        result = await generate_cue_suggestions(
            session=FakeSession(),
            console_state={"$SHOWFILE": "test_show"},
            sequence_info="Sequence 1: 3 cues",
        )
        assert result is None


class TestGenerateTroubleshootingAdvice:
    @pytest.mark.asyncio
    async def test_returns_none_when_unsupported(self):
        class FakeSession:
            def check_client_capability(self, cap):
                raise AttributeError("nope")

        result = await generate_troubleshooting_advice(
            session=FakeSession(),
            error_message="Connection refused",
            recent_commands=["ListVar", "cd Group"],
        )
        assert result is None


class TestGenerateLuaScript:
    @pytest.mark.asyncio
    async def test_returns_none_when_unsupported(self):
        class FakeSession:
            def check_client_capability(self, cap):
                raise AttributeError("nope")

        result = await generate_lua_script(
            session=FakeSession(),
            description="cycle through all groups",
        )
        assert result is None


class TestDefaultPreferences:
    def test_intelligence_prioritized(self):
        assert _DEFAULT_PREFS.intelligencePriority > _DEFAULT_PREFS.speedPriority
        assert _DEFAULT_PREFS.intelligencePriority > _DEFAULT_PREFS.costPriority

    def test_has_model_hint(self):
        assert len(_DEFAULT_PREFS.hints) == 1
        assert "claude" in _DEFAULT_PREFS.hints[0].name.lower()
