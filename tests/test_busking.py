"""
tests/test_busking.py — Unit tests for src/commands/busking.py

All tests are pure string-assertion tests — no telnet, no server required.
"""

from src.commands.busking import (
    assign_effect_to_executor,
    executor_page_range,
    release_effects_on_page,
    set_effect_rate,
    set_effect_speed,
    zero_page_faders,
)

# ── assign_effect_to_executor ────────────────────────────────────────────────

class TestAssignEffectToExecutor:
    def test_basic(self):
        result = assign_effect_to_executor(3, 5)
        assert result == "Assign Effect 3 Executor 5"

    def test_with_page(self):
        result = assign_effect_to_executor(3, 5, page=2)
        assert result == "Assign Effect 3 Page 2.5"

    def test_no_page_no_qualifier(self):
        result = assign_effect_to_executor(1, 1)
        assert "Page" not in result
        assert result == "Assign Effect 1 Executor 1"

    def test_page_zero(self):
        result = assign_effect_to_executor(10, 8, page=1)
        assert result == "Assign Effect 10 Page 1.8"

    def test_large_ids(self):
        result = assign_effect_to_executor(100, 20)
        assert result == "Assign Effect 100 Executor 20"


# ── set_effect_rate ──────────────────────────────────────────────────────────

class TestSetEffectRate:
    def test_normal_rate(self):
        assert set_effect_rate(100) == "EffectRate 100"

    def test_half_rate(self):
        assert set_effect_rate(50) == "EffectRate 50"

    def test_double_rate(self):
        assert set_effect_rate(200) == "EffectRate 200"

    def test_minimum_rate(self):
        assert set_effect_rate(1) == "EffectRate 1"


# ── set_effect_speed ─────────────────────────────────────────────────────────

class TestSetEffectSpeed:
    def test_bpm_120(self):
        assert set_effect_speed(120) == "EffectSpeed 120"

    def test_bpm_128(self):
        assert set_effect_speed(128) == "EffectSpeed 128"

    def test_slow_speed(self):
        assert set_effect_speed(20) == "EffectSpeed 20"


# ── release_effects_on_page ──────────────────────────────────────────────────

class TestReleaseEffectsOnPage:
    def test_default_range_produces_20_commands(self):
        result = release_effects_on_page(3)
        parts = result.split(" ; ")
        assert len(parts) == 20

    def test_default_range_starts_at_1(self):
        result = release_effects_on_page(3)
        assert result.startswith("Off Page 3.1")

    def test_default_range_ends_at_20(self):
        result = release_effects_on_page(3)
        assert result.endswith("Off Page 3.20")

    def test_custom_range(self):
        result = release_effects_on_page(2, start_exec=3, end_exec=5)
        parts = result.split(" ; ")
        assert len(parts) == 3
        assert parts[0] == "Off Page 2.3"
        assert parts[1] == "Off Page 2.4"
        assert parts[2] == "Off Page 2.5"

    def test_single_exec(self):
        result = release_effects_on_page(1, start_exec=7, end_exec=7)
        assert result == "Off Page 1.7"
        assert " ; " not in result

    def test_page_number_embedded(self):
        result = release_effects_on_page(5)
        assert "Page 5." in result


# ── zero_page_faders ─────────────────────────────────────────────────────────

class TestZeroPageFaders:
    def test_default_range_produces_20_commands(self):
        result = zero_page_faders(1)
        parts = result.split(" ; ")
        assert len(parts) == 20

    def test_command_format(self):
        result = zero_page_faders(1, start_exec=1, end_exec=3)
        parts = result.split(" ; ")
        assert parts[0] == "Executor 1.1 At 0"
        assert parts[1] == "Executor 1.2 At 0"
        assert parts[2] == "Executor 1.3 At 0"

    def test_custom_range(self):
        result = zero_page_faders(4, start_exec=2, end_exec=4)
        parts = result.split(" ; ")
        assert len(parts) == 3
        assert all("At 0" in p for p in parts)

    def test_page_number_embedded(self):
        result = zero_page_faders(7)
        assert "Executor 7." in result

    def test_does_not_contain_off(self):
        # zero_page_faders uses At 0, not Off — faders silenced but executors stay active
        result = zero_page_faders(2)
        assert " Off " not in result


# ── executor_page_range ──────────────────────────────────────────────────────

class TestExecutorPageRange:
    def test_basic(self):
        assert executor_page_range(2, 1, 8) == "Page 2.1 Thru 8"

    def test_single_page(self):
        assert executor_page_range(1, 1, 20) == "Page 1.1 Thru 20"

    def test_partial_range(self):
        assert executor_page_range(3, 5, 10) == "Page 3.5 Thru 10"

    def test_page_number_in_result(self):
        result = executor_page_range(7, 2, 6)
        assert result.startswith("Page 7.")
