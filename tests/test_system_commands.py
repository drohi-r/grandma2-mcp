"""
Tests for src/commands/functions/system.py

Covers:
- lock_console / unlock_console
- call_plugin / run_lua / reload_plugins
- set_special_master (with SPECIAL_MASTER_NAMES validation)
- rdm_* (automatch, autopatch, list, info, setpatch, unmatch)
- chaser_rate / chaser_speed / chaser_skip / chaser_xfade
- set_effect_parameter
"""

import pytest

from src.commands.functions.system import (
    SPECIAL_MASTER_NAMES,
    call_plugin,
    chaser_rate,
    chaser_skip,
    chaser_speed,
    chaser_xfade,
    lock_console,
    rdm_automatch,
    rdm_autopatch,
    rdm_info,
    rdm_list,
    rdm_setpatch,
    rdm_unmatch,
    reload_plugins,
    run_lua,
    set_effect_parameter,
    set_special_master,
    unlock_console,
)


# ============================================================
# Console lock / unlock
# ============================================================


class TestLockConsole:
    def test_lock(self):
        assert lock_console() == "Lock"

    def test_unlock_no_password(self):
        assert unlock_console() == "Unlock"

    def test_unlock_with_password(self):
        assert unlock_console("1234") == 'Unlock "1234"'

    def test_unlock_empty_string_is_falsy(self):
        # Empty string is falsy → treated as no password
        assert unlock_console("") == "Unlock"


# ============================================================
# Plugin / Lua
# ============================================================


class TestPlugin:
    def test_call_plugin_int(self):
        assert call_plugin(1) == "Plugin 1"

    def test_call_plugin_str(self):
        assert call_plugin("LUA") == 'Plugin "LUA"'

    def test_call_plugin_large_id(self):
        assert call_plugin(99) == "Plugin 99"


class TestRunLua:
    def test_simple_script(self):
        assert run_lua("print('hi')") == "Lua \"print('hi')\""

    def test_script_with_inner_quotes(self):
        result = run_lua('gma.cmd("Blackout")')
        assert result == 'Lua "gma.cmd(\\"Blackout\\")"'

    def test_reload_plugins(self):
        assert reload_plugins() == "ReloadPlugins"


# ============================================================
# Special Master
# ============================================================


class TestSpecialMaster:
    def test_grandmaster(self):
        assert set_special_master("grandmaster", 80) == "SpecialMaster GrandMaster At 80"

    def test_playbackmaster(self):
        assert set_special_master("playbackmaster", 100) == "SpecialMaster PlaybackMaster At 100"

    def test_speed_master(self):
        assert set_special_master("speed1", 120) == "SpecialMaster Speed1Master At 120"

    def test_speed_master_16(self):
        assert set_special_master("speed16", 90) == "SpecialMaster Speed16Master At 90"

    def test_rate_master(self):
        assert set_special_master("rate1", 100) == "SpecialMaster Rate1Master At 100"

    def test_case_insensitive(self):
        assert set_special_master("GrandMaster", 50) == "SpecialMaster GrandMaster At 50"

    def test_unknown_master_raises(self):
        with pytest.raises(ValueError, match="Unknown master"):
            set_special_master("invalid", 50)

    def test_special_master_names_frozenset(self):
        assert "grandmaster" in SPECIAL_MASTER_NAMES
        assert "speed1" in SPECIAL_MASTER_NAMES
        assert "rate16" in SPECIAL_MASTER_NAMES
        assert len(SPECIAL_MASTER_NAMES) == 34  # grandmaster + playbackmaster + 16 speed + 16 rate


# ============================================================
# RDM
# ============================================================


class TestRDM:
    def test_automatch(self):
        assert rdm_automatch() == "RdmAutomatch"

    def test_autopatch(self):
        assert rdm_autopatch() == "RdmAutopatch"

    def test_list_all(self):
        assert rdm_list() == "RdmList"

    def test_list_universe(self):
        assert rdm_list(1) == "RdmList Universe 1"

    def test_info(self):
        assert rdm_info(101) == "RdmInfo Fixture 101"

    def test_setpatch(self):
        assert rdm_setpatch(101, 1, 1) == "RdmSetpatch Fixture 101 Universe 1 Address 1"

    def test_setpatch_arbitrary(self):
        assert rdm_setpatch(5, 3, 200) == "RdmSetpatch Fixture 5 Universe 3 Address 200"

    def test_unmatch(self):
        assert rdm_unmatch(101) == "RdmUnmatch Fixture 101"


# ============================================================
# Chaser live control
# ============================================================


class TestChaserRate:
    def test_rate_no_executor(self):
        assert chaser_rate(100) == "Rate 100"

    def test_rate_with_executor(self):
        assert chaser_rate(50, 201) == "Rate 50 Executor 1.201"

    def test_rate_with_page(self):
        assert chaser_rate(50, 201, page=2) == "Rate 50 Executor 2.201"


class TestChaserSpeed:
    def test_speed_no_executor(self):
        assert chaser_speed(120) == "Speed 120"

    def test_speed_with_executor(self):
        assert chaser_speed(60, 201) == "Speed 60 Executor 1.201"


class TestChaserSkip:
    def test_skip_plus(self):
        assert chaser_skip("plus") == "SkipPlus"

    def test_skip_minus(self):
        assert chaser_skip("minus") == "SkipMinus"

    def test_skip_plus_executor(self):
        assert chaser_skip("plus", 201) == "SkipPlus Executor 1.201"

    def test_skip_minus_executor_page(self):
        assert chaser_skip("minus", 201, page=2) == "SkipMinus Executor 2.201"

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError, match="direction must be"):
            chaser_skip("forward")


class TestChaserXfade:
    def test_xfade_a(self):
        assert chaser_xfade("a") == "CrossFadeA"

    def test_xfade_b(self):
        assert chaser_xfade("b") == "CrossFadeB"

    def test_xfade_ab(self):
        assert chaser_xfade("ab") == "CrossFadeAB"

    def test_xfade_with_executor(self):
        assert chaser_xfade("ab", 201) == "CrossFadeAB Executor 1.201"

    def test_case_insensitive(self):
        assert chaser_xfade("A") == "CrossFadeA"

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="mode must be"):
            chaser_xfade("c")


# ============================================================
# Effect programmer parameters
# ============================================================


class TestSetEffectParameter:
    def test_bpm(self):
        assert set_effect_parameter("bpm", 120) == "EffectBPM 120"

    def test_hz(self):
        assert set_effect_parameter("hz", 2) == "EffectHZ 2"

    def test_high(self):
        assert set_effect_parameter("high", 80) == "EffectHigh 80"

    def test_low(self):
        assert set_effect_parameter("low", 20) == "EffectLow 20"

    def test_phase(self):
        assert set_effect_parameter("phase", 45) == "EffectPhase 45"

    def test_width(self):
        assert set_effect_parameter("width", 50) == "EffectWidth 50"

    def test_attack(self):
        assert set_effect_parameter("attack", 10) == "EffectAttack 10"

    def test_decay(self):
        assert set_effect_parameter("decay", 10) == "EffectDecay 10"

    def test_case_insensitive(self):
        assert set_effect_parameter("BPM", 120) == "EffectBPM 120"

    def test_unknown_param_raises(self):
        with pytest.raises(ValueError, match="Unknown effect parameter"):
            set_effect_parameter("gain", 50)
