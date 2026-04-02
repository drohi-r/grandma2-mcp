"""
Playback Commands Tests

Tests for grandMA2 playback control command generation.
Includes Go, GoBack, Goto, GoFast, and DefGo command series.

Test Classes:
- TestGoCommands: Tests for go, go_executor, go_macro
- TestGoBackCommands: Tests for go_back, go_back_executor
- TestGotoCommands: Tests for goto
- TestSequenceCommands: Tests for go_sequence, pause_sequence, goto_cue (legacy)
- TestGoFastCommands: Tests for go_fast_back, go_fast_forward
- TestDefGoCommands: Tests for def_go_back, def_go_forward, def_go_pause
"""



class TestGoCommands:
    """Tests for Go keyword - activates next step of an executing object."""

    def test_go_executor_basic(self):
        """Test Go Executor 3 - executes next cue on executor 3."""
        from src.commands import go

        result = go("executor", 3)
        assert result == "go executor 3"

    def test_go_macro(self):
        """Test Go Macro 2 - starts macro 2."""
        from src.commands import go

        result = go("macro", 2)
        assert result == "go macro 2"

    def test_go_executor_range(self):
        """Test Go Executor 1 Thru 5."""
        from src.commands import go

        result = go("executor", 1, end=5)
        assert result == "go executor 1 thru 5"

    def test_go_executor_list(self):
        """Test Go with multiple executors."""
        from src.commands import go

        result = go("executor", [1, 2, 3])
        assert result == "go executor 1 + 2 + 3"

    def test_go_with_cue_mode_normal(self):
        """Test Go with cue_mode=normal."""
        from src.commands import go

        result = go("executor", 3, cue_mode="normal")
        assert result == "go executor 3 /cue_mode=normal"

    def test_go_with_cue_mode_assert(self):
        """Test Go with cue_mode=assert - Go with assert in original timing."""
        from src.commands import go

        result = go("executor", 3, cue_mode="assert")
        assert result == "go executor 3 /cue_mode=assert"

    def test_go_with_cue_mode_xassert(self):
        """Test Go with cue_mode=xassert - Go with assert in current cue timing."""
        from src.commands import go

        result = go("executor", 3, cue_mode="xassert")
        assert result == "go executor 3 /cue_mode=xassert"

    def test_go_with_cue_mode_release(self):
        """Test Go with cue_mode=release - finishes fade and switches off."""
        from src.commands import go

        result = go("executor", 3, cue_mode="release")
        assert result == "go executor 3 /cue_mode=release"

    def test_go_with_userprofile(self):
        """Test Go with userprofile option."""
        from src.commands import go

        result = go("executor", 3, userprofile="Klaus")
        assert result == 'go executor 3 /userprofile="Klaus"'

    def test_go_with_multiple_options(self):
        """Test Go with both cue_mode and userprofile."""
        from src.commands import go

        result = go("executor", 3, cue_mode="assert", userprofile="Klaus")
        assert result == 'go executor 3 /cue_mode=assert /userprofile="Klaus"'

    def test_go_executor_convenience(self):
        """Test go_executor convenience function."""
        from src.commands import go_executor

        result = go_executor(3)
        assert result == "go executor 3"

    def test_go_executor_with_options(self):
        """Test go_executor with cue_mode option."""
        from src.commands import go_executor

        result = go_executor(3, cue_mode="assert")
        assert result == "go executor 3 /cue_mode=assert"

    def test_go_executor_list_convenience(self):
        """Test go_executor with list of executors."""
        from src.commands import go_executor

        result = go_executor([1, 2, 3])
        assert result == "go executor 1 + 2 + 3"

    def test_go_macro_convenience(self):
        """Test go_macro convenience function."""
        from src.commands import go_macro

        result = go_macro(2)
        assert result == "go macro 2"


class TestGoBackCommands:
    """Tests for GoBack keyword - activates previous step of an object."""

    def test_go_back_executor_basic(self):
        """Test GoBack Executor 3 - executes previous cue on executor 3."""
        from src.commands import go_back

        result = go_back("executor", 3)
        assert result == "goback executor 3"

    def test_go_back_executor_range(self):
        """Test GoBack Executor 1 Thru 5."""
        from src.commands import go_back

        result = go_back("executor", 1, end=5)
        assert result == "goback executor 1 thru 5"

    def test_go_back_executor_list(self):
        """Test GoBack with multiple executors."""
        from src.commands import go_back

        result = go_back("executor", [1, 2, 3])
        assert result == "goback executor 1 + 2 + 3"

    def test_go_back_with_cue_mode_assert(self):
        """Test GoBack with cue_mode=assert."""
        from src.commands import go_back

        result = go_back("executor", 3, cue_mode="assert")
        assert result == "goback executor 3 /cue_mode=assert"

    def test_go_back_with_cue_mode_release(self):
        """Test GoBack with cue_mode=release."""
        from src.commands import go_back

        result = go_back("executor", 3, cue_mode="release")
        assert result == "goback executor 3 /cue_mode=release"

    def test_go_back_with_userprofile(self):
        """Test GoBack with userprofile option."""
        from src.commands import go_back

        result = go_back("executor", 3, userprofile="Klaus")
        assert result == 'goback executor 3 /userprofile="Klaus"'

    def test_go_back_executor_convenience(self):
        """Test go_back_executor convenience function."""
        from src.commands import go_back_executor

        result = go_back_executor(3)
        assert result == "goback executor 3"

    def test_go_back_executor_with_options(self):
        """Test go_back_executor with cue_mode option."""
        from src.commands import go_back_executor

        result = go_back_executor(3, cue_mode="assert")
        assert result == "goback executor 3 /cue_mode=assert"


class TestGotoCommands:
    """Tests for Goto keyword - jumps to a specific cue."""

    def test_goto_cue_basic(self):
        """Test Goto Cue 3 - jumps to cue 3 on selected executor."""
        from src.commands import goto

        result = goto(3)
        assert result == "goto cue 3"

    def test_goto_cue_with_executor(self):
        """Test Goto Cue 5 Executor 4."""
        from src.commands import goto

        result = goto(5, executor=4)
        assert result == "goto cue 5 executor 4"

    def test_goto_cue_with_sequence(self):
        """Test Goto Cue 3 Sequence 1."""
        from src.commands import goto

        result = goto(3, sequence=1)
        assert result == "goto cue 3 sequence 1"

    def test_goto_cue_float(self):
        """Test Goto with decimal cue number."""
        from src.commands import goto

        result = goto(3.5)
        assert result == "goto cue 3.5"

    def test_goto_with_cue_mode_assert(self):
        """Test Goto with cue_mode=assert."""
        from src.commands import goto

        result = goto(3, cue_mode="assert")
        assert result == "goto cue 3 /cue_mode=assert"

    def test_goto_with_cue_mode_release(self):
        """Test Goto with cue_mode=release."""
        from src.commands import goto

        result = goto(3, cue_mode="release")
        assert result == "goto cue 3 /cue_mode=release"

    def test_goto_with_userprofile(self):
        """Test Goto with userprofile option."""
        from src.commands import goto

        result = goto(3, userprofile="Klaus")
        assert result == 'goto cue 3 /userprofile="Klaus"'

    def test_goto_with_executor_and_options(self):
        """Test Goto with executor and cue_mode."""
        from src.commands import goto

        result = goto(5, executor=4, cue_mode="assert")
        assert result == "goto cue 5 executor 4 /cue_mode=assert"


class TestSequenceCommands:
    """Tests for legacy sequence-related commands."""

    def test_go_sequence(self):
        """Test executing a sequence (legacy function)."""
        from src.commands import go_sequence

        result = go_sequence(1)
        assert result == "go+ sequence 1"

    def test_pause_sequence(self):
        """Test pausing a sequence."""
        from src.commands import pause_sequence

        result = pause_sequence(1)
        assert result == "pause sequence 1"

    def test_goto_cue(self):
        """Test jumping to a specific cue (legacy function)."""
        from src.commands import goto_cue

        result = goto_cue(1, 5)
        assert result == "goto cue 5 sequence 1"


class TestGoFastCommands:
    """Tests for <<< (GoFastBack) and >>> (GoFastForward) keywords."""

    # ---- GoFastBack (<<<) Tests ----

    def test_go_fast_back_executor(self):
        """Test <<< Executor 3 - jumps to previous cue on executor 3."""
        from src.commands import go_fast_back

        result = go_fast_back(executor=3)
        assert result == "<<< executor 3"

    def test_go_fast_back_executor_list(self):
        """Test <<< with multiple executors."""
        from src.commands import go_fast_back

        result = go_fast_back(executor=[1, 2, 3])
        assert result == "<<< executor 1 + 2 + 3"

    def test_go_fast_back_sequence(self):
        """Test <<< Sequence 5 - jumps to previous cue on sequence 5."""
        from src.commands import go_fast_back

        result = go_fast_back(sequence=5)
        assert result == "<<< sequence 5"

    def test_go_fast_back_no_target(self):
        """Test <<< without target - applies to current executor/sequence."""
        from src.commands import go_fast_back

        result = go_fast_back()
        assert result == "<<<"

    # ---- GoFastForward (>>>) Tests ----

    def test_go_fast_forward_executor(self):
        """Test >>> Executor 3 - jumps to next cue on executor 3."""
        from src.commands import go_fast_forward

        result = go_fast_forward(executor=3)
        assert result == ">>> executor 3"

    def test_go_fast_forward_executor_list(self):
        """Test >>> with multiple executors."""
        from src.commands import go_fast_forward

        result = go_fast_forward(executor=[1, 2, 3])
        assert result == ">>> executor 1 + 2 + 3"

    def test_go_fast_forward_sequence(self):
        """Test >>> Sequence 5 - jumps to next cue on sequence 5."""
        from src.commands import go_fast_forward

        result = go_fast_forward(sequence=5)
        assert result == ">>> sequence 5"

    def test_go_fast_forward_no_target(self):
        """Test >>> without target - applies to current executor/sequence."""
        from src.commands import go_fast_forward

        result = go_fast_forward()
        assert result == ">>>"


class TestDefGoCommands:
    """Tests for DefGoBack, DefGoForward, DefGoPause keywords.

    These commands operate on the selected Executor (default Executor),
    equivalent to pressing the physical Go-, Go+, Pause buttons on the console.
    """

    def test_def_go_back(self):
        """Test DefGoBack - calls previous cue in selected executor."""
        from src.commands import def_go_back

        result = def_go_back()
        assert result == "defgoback"

    def test_def_go_forward(self):
        """Test DefGoForward - calls next cue in selected executor."""
        from src.commands import def_go_forward

        result = def_go_forward()
        assert result == "defgoforward"

    def test_def_go_pause(self):
        """Test DefGoPause - pauses current fade in selected executor."""
        from src.commands import def_go_pause

        result = def_go_pause()
        assert result == "defgopause"


class TestSwopTopStomp:
    """Tests for Swop, Top, and Stomp executor keywords."""

    def test_swop_executor_basic(self):
        from src.commands import swop_executor
        assert swop_executor(3) == "swop executor 3"

    def test_swop_executor_with_page(self):
        from src.commands import swop_executor
        assert swop_executor(5, page=2) == "swop executor 2.5"

    def test_top_executor_basic(self):
        from src.commands import top_executor
        assert top_executor(3) == "top executor 3"

    def test_top_executor_with_page(self):
        from src.commands import top_executor
        assert top_executor(5, page=2) == "top executor 2.5"

    def test_stomp_executor_basic(self):
        from src.commands import stomp_executor
        assert stomp_executor(3) == "stomp executor 3"

    def test_stomp_executor_with_page(self):
        from src.commands import stomp_executor
        assert stomp_executor(5, page=2) == "stomp executor 2.5"


class TestLoadNextPrev:
    """Tests for LoadNext and LoadPrev keywords."""

    def test_load_next_bare(self):
        from src.commands import load_next
        assert load_next() == "loadnext"

    def test_load_next_executor(self):
        from src.commands import load_next
        assert load_next(executor=3) == "loadnext executor 3"

    def test_load_next_sequence(self):
        from src.commands import load_next
        assert load_next(sequence=5) == "loadnext sequence 5"

    def test_load_prev_bare(self):
        from src.commands import load_prev
        assert load_prev() == "loadprev"

    def test_load_prev_executor(self):
        from src.commands import load_prev
        assert load_prev(executor=3) == "loadprev executor 3"

    def test_load_prev_sequence(self):
        from src.commands import load_prev
        assert load_prev(sequence=5) == "loadprev sequence 5"


class TestGoFastMultiExecutor:
    """Tests for go_fast_forward / go_fast_back with list[int] executor."""

    def test_go_fast_forward_executor_list(self):
        from src.commands import go_fast_forward
        assert go_fast_forward(executor=[1, 2, 3]) == ">>> executor 1 + 2 + 3"

    def test_go_fast_forward_executor_two(self):
        from src.commands import go_fast_forward
        assert go_fast_forward(executor=[2, 4]) == ">>> executor 2 + 4"

    def test_go_fast_back_executor_list(self):
        from src.commands import go_fast_back
        assert go_fast_back(executor=[1, 2, 3]) == "<<< executor 1 + 2 + 3"

    def test_go_fast_back_executor_two(self):
        from src.commands import go_fast_back
        assert go_fast_back(executor=[2, 4]) == "<<< executor 2 + 4"


class TestGoMultiObjectId:
    """Tests for go / go_back with list[int] object_id."""

    def test_go_executor_list(self):
        from src.commands import go
        assert go("executor", [1, 2, 3]) == "go executor 1 + 2 + 3"

    def test_go_back_executor_list(self):
        from src.commands import go_back
        assert go_back("executor", [5, 6]) == "goback executor 5 + 6"
