"""
Macro Commands Tests

Tests for grandMA2 macro placeholder command generation.
The @ character is used as a placeholder for user input in macros.

Test Classes:
- TestMacroPlaceholder: Tests for macro_with_input_after, macro_with_input_before
"""



class TestMacroPlaceholder:
    """Tests for @ character macro placeholder."""

    def test_macro_with_input_after(self):
        """Test macro with @ at the end: Load @"""
        from src.commands import macro_with_input_after

        result = macro_with_input_after("Load")
        assert result == "Load @"

    def test_macro_with_input_after_complex(self):
        """Test macro with @ at the end for attribute: Attribute Pan At @"""
        from src.commands import macro_with_input_after

        result = macro_with_input_after("Attribute Pan At")
        assert result == "Attribute Pan At @"

    def test_macro_with_input_before(self):
        """Test macro with @ at the beginning: @ Fade 20"""
        from src.commands import macro_with_input_before

        result = macro_with_input_before("Fade 20")
        assert result == "@ Fade 20"
