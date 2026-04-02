"""
Tests for TempFader Function Keyword

TempFader is a function that crossfades the cue on when pulled up,
and crossfades the cue off when pulled down.

Syntax:
    Assign TempFader [Executor-list]
    TempFader [Value] [Executor-list]

Note: TempFader can be used in two ways:
1. With Assign to assign the function to an executor
2. Standalone to set the temp fader value
"""



class TestTempFader:
    """
    Tests for TempFader function keyword - temporary fader control.

    Syntax:
        Assign TempFader [Executor-list]
        TempFader [Value] [Executor-list]
    """

    # ---- Basic TempFader (returns keyword) ----

    def test_tempfader_basic(self):
        """Test tempfader keyword: tempfader"""
        from src.commands import temp_fader

        result = temp_fader()
        assert result == "tempfader"

    # ---- TempFader with value (set fader level) ----

    def test_tempfader_with_value(self):
        """Test tempfader with value: tempfader 50"""
        from src.commands import temp_fader

        result = temp_fader(50)
        assert result == "tempfader 50"

    def test_tempfader_with_value_0(self):
        """Test tempfader at 0%: tempfader 0"""
        from src.commands import temp_fader

        result = temp_fader(0)
        assert result == "tempfader 0"

    def test_tempfader_with_value_100(self):
        """Test tempfader at 100%: tempfader 100"""
        from src.commands import temp_fader

        result = temp_fader(100)
        assert result == "tempfader 100"

    def test_tempfader_with_value_75(self):
        """Test tempfader at 75%: tempfader 75"""
        from src.commands import temp_fader

        result = temp_fader(75)
        assert result == "tempfader 75"

    # ---- TempFader with Assign (assign function to executor) ----

    def test_assign_tempfader_single_executor(self):
        """Test assign tempfader to executor: assign tempfader at executor 28"""
        from src.commands import assign_function

        result = assign_function("tempfader", "executor", 28)
        assert result == "assign tempfader at executor 28"

    def test_assign_tempfader_exec_shortcut(self):
        """Test assign tempfader with exec shortcut: assign tempfader at exec 28"""
        from src.commands import assign_function

        result = assign_function("tempfader", "exec", 28)
        assert result == "assign tempfader at exec 28"

    def test_assign_tempfader_different_executor(self):
        """Test assign tempfader to different executor: assign tempfader at executor 1"""
        from src.commands import assign_function

        result = assign_function("tempfader", "executor", 1)
        assert result == "assign tempfader at executor 1"

    # ---- TempFader with value and executor (combined) ----

    def test_tempfader_value_with_executor(self):
        """Test tempfader with value and executor: tempfader 50 executor 28"""
        from src.commands import executor, temp_fader

        result = f"{temp_fader(50)} {executor(28)}"
        assert result == "tempfader 50 executor 28"

    def test_tempfader_value_with_exec(self):
        """Test tempfader with value and exec: tempfader 75 exec 1"""
        from src.commands import executor, temp_fader

        result = f"{temp_fader(75)} {executor(1)}"
        assert result == "tempfader 75 executor 1"

