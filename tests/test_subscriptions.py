"""Tests for MCP resource subscriptions module."""

from __future__ import annotations

import pytest

from src.subscriptions import (
    _subscriptions,
    get_subscribed_uris,
    get_subscription_count,
    has_subscribers,
)


@pytest.fixture(autouse=True)
def _clear_subscriptions():
    """Reset subscription state before each test."""
    _subscriptions.clear()
    yield
    _subscriptions.clear()


class TestSubscriptionTracking:
    def test_no_subscriptions_initially(self):
        assert get_subscribed_uris() == []

    def test_has_subscribers_false_when_empty(self):
        assert has_subscribers("gma2://console/status") is False

    def test_get_subscription_count_zero_when_empty(self):
        assert get_subscription_count("gma2://console/status") == 0

    def test_manual_add_subscription(self):
        """Simulate a subscription being tracked."""
        _subscriptions["gma2://console/status"].add(1)
        assert has_subscribers("gma2://console/status") is True
        assert get_subscription_count("gma2://console/status") == 1

    def test_multiple_subscriptions_same_uri(self):
        _subscriptions["gma2://console/status"].add(1)
        _subscriptions["gma2://console/status"].add(2)
        assert get_subscription_count("gma2://console/status") == 2

    def test_subscriptions_multiple_uris(self):
        _subscriptions["gma2://console/status"].add(1)
        _subscriptions["gma2://show/groups"].add(2)
        uris = get_subscribed_uris()
        assert len(uris) == 2
        assert "gma2://console/status" in uris
        assert "gma2://show/groups" in uris

    def test_remove_subscription(self):
        _subscriptions["gma2://console/status"].add(1)
        _subscriptions["gma2://console/status"].discard(1)
        # Empty set still exists in defaultdict
        assert get_subscription_count("gma2://console/status") == 0

    def test_has_subscribers_false_after_all_removed(self):
        _subscriptions["gma2://console/status"].add(1)
        _subscriptions["gma2://console/status"].discard(1)
        assert has_subscribers("gma2://console/status") is False
