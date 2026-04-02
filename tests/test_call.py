"""
Tests for Call Function Keyword

Call is a function used to apply/engage an object or its content.
It loads values into the programmer without selecting fixtures.

Syntax:
    Call [Object-list]
    Call [Object-list] / [option]

Options:
    status (s) - =False or =True, takes tracking values into programmer
    LAYER - sets destination layer
    SCREEN - sets destination screen
    toggle_activation (t) - toggles activation state
"""



class TestCall:
    """
    Tests for Call function keyword - apply/engage objects.

    Syntax:
        Call [Object-list]
        Call [Object-list] / [option]
    """

    # ---- Basic Call ----

    def test_call_preset(self):
        """Test call preset: call preset 3.1"""
        from src.commands import call

        result = call("preset 3.1")
        assert result == "call preset 3.1"

    def test_call_sequence(self):
        """Test call sequence: call sequence 1"""
        from src.commands import call

        result = call("sequence 1")
        assert result == "call sequence 1"

    def test_call_cue(self):
        """Test call cue: call cue 3"""
        from src.commands import call

        result = call("cue 3")
        assert result == "call cue 3"

    def test_call_group(self):
        """Test call group: call group 5"""
        from src.commands import call

        result = call("group 5")
        assert result == "call group 5"

    # ---- Call with status option ----

    def test_call_with_status_true(self):
        """Test call with status option: call cue 3 /status=true"""
        from src.commands import call

        result = call("cue 3", status=True)
        assert result == "call cue 3 /status=true"

    def test_call_with_status_false(self):
        """Test call with status option: call cue 3 /status=false"""
        from src.commands import call

        result = call("cue 3", status=False)
        assert result == "call cue 3 /status=false"

    # ---- Call with layer option ----

    def test_call_with_layer(self):
        """Test call with layer option: call preset 1.1 /layer"""
        from src.commands import call

        result = call("preset 1.1", layer=True)
        assert result == "call preset 1.1 /layer"

    # ---- Call with screen option ----

    def test_call_with_screen(self):
        """Test call with screen option: call layout 1 /screen"""
        from src.commands import call

        result = call("layout 1", screen=True)
        assert result == "call layout 1 /screen"

    # ---- Call with toggle_activation option ----

    def test_call_with_toggle_activation(self):
        """Test call with toggle_activation: call preset 2.1 /toggle_activation"""
        from src.commands import call

        result = call("preset 2.1", toggle_activation=True)
        assert result == "call preset 2.1 /toggle_activation"

    # ---- Call with multiple options ----

    def test_call_with_multiple_options(self):
        """Test call with multiple options: call cue 5 /status=true /layer"""
        from src.commands import call

        result = call("cue 5", status=True, layer=True)
        assert result == "call cue 5 /status=true /layer"

