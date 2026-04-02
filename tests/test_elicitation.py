"""Tests for MCP elicitation module."""

from __future__ import annotations

import pytest

from src.elicitation import (
    DestructiveConfirmation,
    ElicitationAction,
    TargetSelection,
    check_elicitation_support,
    elicit_destructive_confirmation,
    elicit_target_selection,
)


class TestElicitationModels:
    def test_destructive_confirmation_true(self):
        model = DestructiveConfirmation(confirmed=True)
        assert model.confirmed is True

    def test_destructive_confirmation_false(self):
        model = DestructiveConfirmation(confirmed=False)
        assert model.confirmed is False

    def test_target_selection(self):
        model = TargetSelection(object_id="5", object_name="Front Wash")
        assert model.object_id == "5"
        assert model.object_name == "Front Wash"

    def test_elicitation_action_values(self):
        assert ElicitationAction.ACCEPT == "accept"
        assert ElicitationAction.DECLINE == "decline"
        assert ElicitationAction.CANCEL == "cancel"


class TestElicitDestructiveConfirmation:
    @pytest.mark.asyncio
    async def test_returns_false_when_unsupported(self):
        """If elicitation module isn't available, returns False gracefully."""

        class FakeSession:
            pass

        result = await elicit_destructive_confirmation(
            session=FakeSession(),
            command="Delete Sequence 1",
            object_description="Sequence 1 (Main Show)",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        """Any exception in elicitation should return False, not crash."""

        class ErrorSession:
            async def elicit(self, **kwargs):
                raise RuntimeError("Not supported")

        result = await elicit_destructive_confirmation(
            session=ErrorSession(),
            command="Delete Group 3",
            object_description="Group 3",
        )
        assert result is False


class TestElicitTargetSelection:
    @pytest.mark.asyncio
    async def test_returns_none_when_unsupported(self):
        class FakeSession:
            pass

        result = await elicit_target_selection(
            session=FakeSession(),
            message="Select target fixture group",
        )
        assert result is None


class TestCheckElicitationSupport:
    @pytest.mark.asyncio
    async def test_returns_false_without_capability(self):
        class FakeSession:
            def check_client_capability(self, cap):
                raise AttributeError("No capabilities")

        result = await check_elicitation_support(FakeSession())
        assert result is False
