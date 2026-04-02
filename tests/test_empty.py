"""
Tests for Empty Function Keyword

Empty is a function used to deactivate executors.
It assigns the "empty" function to executors, making them inactive.

Syntax:
    Assign Empty [Executor list]

Note: Empty must be used with the Assign keyword.
"""



class TestEmpty:
    """
    Tests for Empty function keyword - deactivate executors.

    Syntax:
        Assign Empty [Executor list]
    """

    # ---- Basic Empty ----

    def test_empty_basic(self):
        """Test empty keyword: empty"""
        from src.commands import empty

        result = empty()
        assert result == "empty"

    # ---- Empty with Assign (typical usage) ----

    def test_assign_empty_single_executor(self):
        """Test assign empty to single executor: assign empty at executor 101"""
        from src.commands import assign_function

        result = assign_function("empty", "executor", 101)
        assert result == "assign empty at executor 101"

    def test_assign_empty_executor_range(self):
        """Test assign empty to executor range: assign empty at executor 1"""
        from src.commands import assign_function

        result = assign_function("empty", "executor", 1)
        assert result == "assign empty at executor 1"

    def test_assign_empty_multiple_executors(self):
        """Test assign empty to executor: assign empty at executor 5"""
        from src.commands import assign_function

        result = assign_function("empty", "executor", 5)
        assert result == "assign empty at executor 5"

    # ---- Integration test with full command ----

    def test_full_command_assign_empty_executor(self):
        """Test full command: assign empty executor 101"""
        from src.commands import assign_function

        # Using assign_function helper that combines assign + function
        result = assign_function("empty", "executor", 101)
        assert result == "assign empty at executor 101"
