"""
Tests for new command builders added in Phase 1.
"""
import pytest
from src.commands import (
    master_at, special_master_at, list_masters,
    block_cue, unblock_cue, learn_executor, kill_executor,
    toggle_executor, freeze_executor,
    double_rate, half_rate, double_speed, half_speed,
    align, locate, flip,
    store_look, extract,
    macro_condition_line, record_macro, VALID_CONDITION_OPERATORS,
    lua_execute, reboot_console, restart_console, shutdown_console,
    send_chat, lock_console,
)


class TestMasterAt:
    def test_basic(self): assert master_at(1, 80) == "Master 1 At 80"
    def test_zero(self): assert master_at(3, 0) == "Master 3 At 0"
    def test_full(self): assert master_at(1, 100) == "Master 1 At 100"

class TestSpecialMasterAt:
    def test_basic(self): assert special_master_at(3, 1, 50) == "SpecialMaster 3.1 At 50"
    def test_full(self): assert special_master_at(1, 1, 100) == "SpecialMaster 1.1 At 100"
    def test_zero(self): assert special_master_at(2, 3, 0) == "SpecialMaster 2.3 At 0"

class TestListMasters:
    def test_returns_command(self): assert list_masters() == "List Master"

class TestBlockCue:
    def test_bare(self): assert block_cue(5) == "Block Cue 5"
    def test_with_sequence(self): assert block_cue(3, sequence_id=1) == "Block Cue 3 Sequence 1"
    def test_float_cue(self): assert block_cue(1.5, sequence_id=2) == "Block Cue 1.5 Sequence 2"
    def test_no_sequence_keyword(self): assert "Sequence" not in block_cue(10)

class TestUnblockCue:
    def test_bare(self): assert unblock_cue(5) == "Unblock Cue 5"
    def test_with_sequence(self): assert unblock_cue(3, sequence_id=1) == "Unblock Cue 3 Sequence 1"
    def test_float_cue(self): assert unblock_cue(2.5) == "Unblock Cue 2.5"

class TestLearnExecutor:
    def test_bare(self): assert learn_executor(1) == "Learn Executor 1"
    def test_page_qualified(self): assert learn_executor(5, page=2) == "Learn Executor 2.5"
    def test_no_dot_without_page(self): assert "." not in learn_executor(3)

class TestKillExecutor:
    def test_bare(self): assert kill_executor(3) == "Kill Executor 3"
    def test_page_qualified(self): assert kill_executor(5, page=2) == "Kill Executor 2.5"

class TestToggleExecutor:
    def test_bare(self): assert toggle_executor(3) == "Toggle Executor 3"
    def test_page_qualified(self): assert toggle_executor(5, page=2) == "Toggle Executor 2.5"

class TestFreezeExecutor:
    def test_bare(self): assert freeze_executor(3) == "Freeze Executor 3"
    def test_page_qualified(self): assert freeze_executor(5, page=2) == "Freeze Executor 2.5"
    def test_different_from_generic_freeze(self):
        from src.commands import freeze
        assert freeze_executor(1) != freeze()

class TestDoubleRate:
    def test_global(self): assert double_rate() == "DoubleRate"
    def test_executor(self): assert double_rate(executor=3) == "DoubleRate Executor 3"

class TestHalfRate:
    def test_global(self): assert half_rate() == "HalfRate"
    def test_executor(self): assert half_rate(executor=3) == "HalfRate Executor 3"

class TestDoubleSpeed:
    def test_global(self): assert double_speed() == "DoubleSpeed"
    def test_executor(self): assert double_speed(executor=3) == "DoubleSpeed Executor 3"

class TestHalfSpeed:
    def test_global(self): assert half_speed() == "HalfSpeed"
    def test_executor(self): assert half_speed(executor=3) == "HalfSpeed Executor 3"

class TestAlignExtended:
    def test_bare_preserves_original(self): assert align() == "align"
    def test_left_to_right(self): assert align(">") == "align >"
    def test_right_to_left(self): assert align("<") == "align <"
    def test_center_out(self): assert align("><") == "align ><"
    def test_edges_in(self): assert align("<>") == "align <>"

class TestLocateExtended:
    def test_bare_preserves_original(self): assert locate() == "locate"
    def test_single_fixture(self): assert locate(1) == "locate fixture 1"
    def test_range(self): assert locate(1, 10) == "locate fixture 1 thru 10"
    def test_list(self): assert locate([1, 3, 5]) == "locate fixture 1 + 3 + 5"
    def test_no_thru_without_end(self): assert "thru" not in locate(5)

class TestFlip:
    def test_returns_flip(self): assert flip() == "Flip"

class TestStoreLook:
    def test_bare(self): assert store_look() == "StoreLook"
    def test_with_id(self): assert store_look(5) == "StoreLook 5"
    def test_merge(self): assert store_look(3, merge=True) == "StoreLook 3 /merge"
    def test_overwrite(self): assert store_look(3, overwrite=True) == "StoreLook 3 /overwrite"
    def test_no_id_merge(self): assert store_look(merge=True) == "StoreLook /merge"
    def test_merge_and_overwrite(self):
        result = store_look(1, merge=True, overwrite=True)
        assert "/merge" in result and "/overwrite" in result

class TestExtract:
    def test_returns_extract(self): assert extract() == "Extract"

class TestValidConditionOperators:
    def test_contains_equality(self): assert "==" in VALID_CONDITION_OPERATORS
    def test_contains_inequality(self): assert "!=" in VALID_CONDITION_OPERATORS
    def test_contains_less(self): assert "<" in VALID_CONDITION_OPERATORS
    def test_contains_greater(self): assert ">" in VALID_CONDITION_OPERATORS
    def test_no_single_equals(self): assert "=" not in VALID_CONDITION_OPERATORS

class TestMacroConditionLine:
    def test_equality(self):
        assert macro_condition_line("$mymode", "==", 1, "Go Executor 1") == "[$mymode == 1] Go Executor 1"
    def test_less_than(self):
        assert macro_condition_line("$counter", "<", 10, "AddVar $counter + 1") == "[$counter < 10] AddVar $counter + 1"
    def test_greater_than(self):
        assert macro_condition_line("$val", ">", 5, "Go Executor 2") == "[$val > 5] Go Executor 2"
    def test_inequality(self):
        assert macro_condition_line("$mode", "!=", 0, "Kill Executor 1") == "[$mode != 0] Kill Executor 1"
    def test_raises_on_missing_dollar(self):
        with pytest.raises(ValueError): macro_condition_line("mymode", "==", 1, "Go Executor 1")
    def test_raises_on_single_equals(self):
        with pytest.raises(ValueError): macro_condition_line("$mymode", "=", 1, "Go Executor 1")
    def test_raises_on_invalid_operator(self):
        with pytest.raises(ValueError): macro_condition_line("$mymode", ">=", 1, "Go Executor 1")
    def test_raises_on_empty_command(self):
        with pytest.raises(ValueError): macro_condition_line("$mymode", "==", 1, "")
    def test_raises_on_whitespace_command(self):
        with pytest.raises(ValueError): macro_condition_line("$mymode", "==", 1, "   ")

class TestRecordMacro:
    def test_basic(self): assert record_macro(1) == "Record Macro 1"
    def test_high_slot(self): assert record_macro(99) == "Record Macro 99"
    def test_starts_with_record(self): assert record_macro(5).startswith("Record Macro ")

class TestLuaExecute:
    def test_basic(self):
        result = lua_execute("gma.echo('hello')")
        assert result.startswith('Lua "') and "gma.echo" in result
    def test_matches_run_lua(self):
        from src.commands import run_lua
        assert lua_execute("test") == run_lua("test")

class TestRebootConsole:
    def test_returns_reboot(self): assert reboot_console() == "Reboot"

class TestRestartConsole:
    def test_returns_restart(self): assert restart_console() == "Restart"

class TestShutdownConsole:
    def test_returns_shutdown(self): assert shutdown_console() == "Shutdown"

class TestSendChat:
    def test_basic(self): assert send_chat("Hello from onPC") == 'Chat "Hello from onPC"'
    def test_empty(self): assert send_chat("") == 'Chat ""'

class TestLockConsoleExtended:
    def test_no_password(self): assert lock_console() == "Lock"
    def test_with_password(self): assert lock_console("secret") == 'Lock "secret"'
    def test_password_quoted(self): assert '"1234"' in lock_console("1234")
