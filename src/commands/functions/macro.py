"""
Macro Placeholder and Condition Function Keywords for grandMA2 Command Builder

The "@" character is used in macros as a placeholder for user input.
This is completely different from the "At" keyword.

- @ at the end: User input will come after the command
- @ at the beginning: User input will come before the command (CLI must be disabled)

Conditional execution uses [$variable operator value] prefix syntax.
IMPORTANT: Equality uses == (double equals), NOT = (single equals).
Single = is only for variable assignment (SetVar/AddVar).

Included functions:
- macro_with_input_after: Add user input placeholder at the end of command
- macro_with_input_before: Add user input placeholder at the beginning of command
- macro_condition_line: Build a conditional macro line with operator validation
- record_macro: Start recording a macro via key capture
"""

VALID_CONDITION_OPERATORS = ("==", "!=", "<", ">")


def macro_with_input_after(command: str) -> str:
    """
    Create a macro line with user input placeholder at the end.

    The @ at the end means the user will provide input after
    executing the macro.

    Args:
        command: The command prefix before user input

    Returns:
        str: Macro line with @ placeholder at the end

    Examples:
        >>> macro_with_input_after("Load")
        'Load @'
        >>> macro_with_input_after("Attribute Pan At")
        'Attribute Pan At @'
    """
    return f"{command} @"


def macro_with_input_before(command: str) -> str:
    """
    Create a macro line with user input placeholder at the beginning.

    The @ at the beginning means the user's previous command line
    input will be prepended. Note: CLI must be disabled for this to work.

    Args:
        command: The command suffix after user input

    Returns:
        str: Macro line with @ placeholder at the beginning

    Examples:
        >>> macro_with_input_before("Fade 20")
        '@ Fade 20'
    """
    return f"@ {command}"


# ============================================================================
# CONDITIONAL MACRO LINE
# ============================================================================


def macro_condition_line(
    var_name: str,
    operator: str,
    value: int | float | str,
    command: str,
) -> str:
    """
    Build a conditional macro line: [$var op value] command.

    grandMA2 macro conditions use == for equality (NOT single =).
    Single = is only for variable assignment (SetVar).

    Args:
        var_name: Variable name (must start with $, e.g. "$mymode")
        operator: Comparison operator — one of ==, !=, <, >
        value: Value to compare against
        command: The grandMA2 command to execute if condition is true

    Raises:
        ValueError: If operator is invalid (including single =),
                    if var_name does not start with $,
                    or if command is empty.

    Returns:
        str: Conditional macro line, e.g. "[$mymode == 1] Go Executor 1"

    Examples:
        >>> macro_condition_line("$mymode", "==", 1, "Go Executor 1")
        '[$mymode == 1] Go Executor 1'
        >>> macro_condition_line("$counter", "<", 10, "AddVar $counter + 1")
        '[$counter < 10] AddVar $counter + 1'
    """
    if not var_name.startswith("$"):
        raise ValueError(
            f"Variable name must start with '$', got: '{var_name}'"
        )
    if not command or not command.strip():
        raise ValueError("Command must not be empty")
    if operator == "=":
        raise ValueError(
            "Use '==' for equality in macro conditions, not '='. "
            "Single '=' is for variable assignment (SetVar)."
        )
    if operator not in VALID_CONDITION_OPERATORS:
        raise ValueError(
            f"Invalid condition operator '{operator}'. "
            f"Valid operators: {', '.join(VALID_CONDITION_OPERATORS)}"
        )
    return f"[{var_name} {operator} {value}] {command}"


# ============================================================================
# RECORD FUNCTION KEYWORD
# ============================================================================


def record_macro(macro_id: int) -> str:
    """
    Construct a Record command to start recording a macro via key capture.

    Args:
        macro_id: Macro pool slot number to record into

    Returns:
        str: MA command string

    Examples:
        >>> record_macro(1)
        'Record Macro 1'
        >>> record_macro(99)
        'Record Macro 99'
    """
    return f"Record Macro {macro_id}"
