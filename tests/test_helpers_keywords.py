"""
Helping Keywords Tests

Tests for grandMA2 Plus (+) and Minus (-) helping keyword command generation.
These keywords are used to combine/exclude objects, apply relative values,
and control page navigation.

Plus (+) keyword functions:
- Combine multiple objects in a list (e.g., Delete Cue 1 + 2)
- Indicate a relative positive value (e.g., At + 5)
- Add objects to current selection (e.g., + 5 Thru 7)
- Navigate to next page (e.g., Page +)

Minus (-) keyword functions:
- Remove objects from a list (e.g., Group 5 - Channel 2)
- Indicate a relative negative value (e.g., At - 10)
- Remove objects from current selection (e.g., - 5 Thru 7)
- Navigate to previous page (e.g., Page -)

Test Classes:
- TestAtRelative: Tests for relative value changes with At keyword
- TestAddToSelection: Tests for adding to selection with Plus
- TestRemoveFromSelection: Tests for removing from selection with Minus
- TestPageNavigation: Tests for page navigation with +/-
"""

import pytest


class TestAtRelative:
    """Tests for At keyword with relative values using Plus and Minus."""

    # ---- Plus: Adding relative values ----

    def test_at_plus_relative_value(self):
        """Test adding relative dimmer value: at + 5"""
        from src.commands import at_relative

        result = at_relative(5)
        assert result == "at + 5"

    def test_at_plus_relative_larger_value(self):
        """Test adding larger relative dimmer value: at + 10"""
        from src.commands import at_relative

        result = at_relative(10)
        assert result == "at + 10"

    def test_at_plus_relative_float_value(self):
        """Test adding relative float dimmer value: at + 5.5"""
        from src.commands import at_relative

        result = at_relative(5.5)
        assert result == "at + 5.5"

    # ---- Minus: Subtracting relative values ----

    def test_at_minus_relative_value(self):
        """Test subtracting relative dimmer value: at - 10"""
        from src.commands import at_relative

        result = at_relative(-10)
        assert result == "at - 10"

    def test_at_minus_relative_larger_value(self):
        """Test subtracting larger relative dimmer value: at - 25"""
        from src.commands import at_relative

        result = at_relative(-25)
        assert result == "at - 25"

    def test_at_minus_relative_float_value(self):
        """Test subtracting relative float dimmer value: at - 5.5"""
        from src.commands import at_relative

        result = at_relative(-5.5)
        assert result == "at - 5.5"

    # ---- Edge cases ----

    def test_at_relative_zero_raises_error(self):
        """Test that zero value raises ValueError."""
        from src.commands import at_relative

        with pytest.raises(ValueError):
            at_relative(0)


class TestAddToSelection:
    """Tests for adding objects to selection using Plus (+)."""

    def test_add_to_selection_single(self):
        """Test adding single channel to selection: + 5"""
        from src.commands import add_to_selection

        result = add_to_selection(5)
        assert result == "+ 5"

    def test_add_to_selection_range(self):
        """Test adding channel range to selection: + 5 thru 7"""
        from src.commands import add_to_selection

        result = add_to_selection(5, end=7)
        assert result == "+ 5 thru 7"

    def test_add_to_selection_list(self):
        """Test adding multiple channels to selection: + 1 + 3 + 5"""
        from src.commands import add_to_selection

        result = add_to_selection([1, 3, 5])
        assert result == "+ 1 + 3 + 5"


class TestRemoveFromSelection:
    """Tests for removing objects from selection using Minus (-)."""

    def test_remove_from_selection_single(self):
        """Test removing single channel from selection: - 5"""
        from src.commands import remove_from_selection

        result = remove_from_selection(5)
        assert result == "- 5"

    def test_remove_from_selection_range(self):
        """Test removing channel range from selection: - 5 thru 7"""
        from src.commands import remove_from_selection

        result = remove_from_selection(5, end=7)
        assert result == "- 5 thru 7"

    def test_remove_from_selection_list(self):
        """Test removing multiple channels from selection: - 1 - 3 - 5"""
        from src.commands import remove_from_selection

        result = remove_from_selection([1, 3, 5])
        assert result == "- 1 - 3 - 5"


class TestPageNavigation:
    """Tests for page navigation with Plus and Minus."""

    # ---- Page Plus (Next) ----

    def test_page_next_default(self):
        """Test page next with default step: page +"""
        from src.commands import page_next

        result = page_next()
        assert result == "page +"

    def test_page_next_with_steps(self):
        """Test page next with explicit steps: page + 3"""
        from src.commands import page_next

        result = page_next(3)
        assert result == "page + 3"

    # ---- Page Minus (Previous) ----

    def test_page_previous_default(self):
        """Test page previous with default step: page -"""
        from src.commands import page_previous

        result = page_previous()
        assert result == "page -"

    def test_page_previous_with_steps(self):
        """Test page previous with explicit steps: page - 3"""
        from src.commands import page_previous

        result = page_previous(3)
        assert result == "page - 3"


class TestAndKeyword:
    """
    Tests for And keyword - a helping keyword that adds selection or values.

    And is used to combine conditions, especially with the If keyword.
    Syntax: [Function] [Object] If [Condition] And [Condition]

    Example:
        Delete Cue 1 If Fixture 5 Attribute "Pan" And Fixture 5 Attribute "Tilt"
    """

    # ---- Basic And combination ----

    def test_condition_and_two_conditions(self):
        """Test combining two conditions with And"""
        from src.commands import condition_and

        result = condition_and(
            'fixture 5 attribute "pan"',
            'fixture 5 attribute "tilt"',
        )
        assert result == 'fixture 5 attribute "pan" and fixture 5 attribute "tilt"'

    def test_condition_and_three_conditions(self):
        """Test combining three conditions with And"""
        from src.commands import condition_and

        result = condition_and(
            'fixture 5 attribute "pan"',
            'fixture 5 attribute "tilt"',
            'fixture 5 attribute "dimmer"',
        )
        assert (
            result
            == 'fixture 5 attribute "pan" and fixture 5 attribute "tilt" and fixture 5 attribute "dimmer"'
        )

    def test_condition_and_single_condition(self):
        """Test single condition returns as-is (no And needed)"""
        from src.commands import condition_and

        result = condition_and('fixture 5 attribute "pan"')
        assert result == 'fixture 5 attribute "pan"'

    def test_condition_and_empty_raises_error(self):
        """Test that empty conditions raise ValueError"""
        from src.commands import condition_and

        with pytest.raises(ValueError):
            condition_and()


class TestIfCondition:
    """
    Tests for If condition builder with And support.

    The If keyword is used to filter commands based on conditions.
    And can be used to combine multiple conditions.
    """

    # ---- Basic If condition ----

    def test_if_condition_single(self):
        """Test if condition with single condition"""
        from src.commands import if_condition

        result = if_condition('fixture 5 attribute "pan"')
        assert result == 'if fixture 5 attribute "pan"'

    def test_if_condition_with_and(self):
        """Test if condition with And: if ... and ..."""
        from src.commands import if_condition

        result = if_condition(
            'fixture 5 attribute "pan"',
            'fixture 5 attribute "tilt"',
        )
        assert result == 'if fixture 5 attribute "pan" and fixture 5 attribute "tilt"'

    def test_if_condition_with_multiple_and(self):
        """Test if condition with multiple And conditions"""
        from src.commands import if_condition

        result = if_condition(
            'fixture 5 attribute "pan"',
            'fixture 5 attribute "tilt"',
            'fixture 10 attribute "dimmer"',
        )
        assert (
            result
            == 'if fixture 5 attribute "pan" and fixture 5 attribute "tilt" and fixture 10 attribute "dimmer"'
        )

    def test_if_condition_empty_raises_error(self):
        """Test that empty condition raises ValueError"""
        from src.commands import if_condition

        with pytest.raises(ValueError):
            if_condition()
