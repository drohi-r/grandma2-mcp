"""
Variable Function Keywords for grandMA2 Command Builder

Variable keywords are used to set and modify show/user variables.

SetUserVar (SetUs) - Set user profile specific variables
SetVar (SetV) - Set global show variables
AddUserVar (AddU) - Change/extend user variable content
AddVar (Ad) - Change/extend show variable content

Key behaviors:
- SetUserVar/SetVar: Set variable value (overwrite)
- AddUserVar/AddVar: Modify/extend variable content
  * Numeric: Add values (5 + 6 = 11)
  * Text: Concatenate strings ("John" + " Doe" = "John Doe")

Included functions:
- set_user_var: Set user profile specific variable
- set_var: Set global show variable
- add_user_var: Change/extend user variable content
- add_var: Change/extend show variable content
"""



def get_user_var(var_name: str) -> str:
    """
    Construct a GetUserVar command to read a user variable value.

    Args:
        var_name: Variable name (should start with $, e.g., "$mycounter")

    Returns:
        str: MA command to get user variable

    Examples:
        >>> get_user_var("$mycounter")
        'getuservar $mycounter'
    """
    return f"getuservar {var_name}"


def list_var() -> str:
    """
    Construct a ListVar command to list all global show variables.

    Returns:
        str: MA command to list show variables

    Examples:
        >>> list_var()
        'listvar'
    """
    return "listvar"


def list_user_var() -> str:
    """
    Construct a ListUserVar command to list all user profile variables.

    Returns:
        str: MA command to list user variables

    Examples:
        >>> list_user_var()
        'listuservar'
    """
    return "listuservar"


def set_user_var(
    var_name: str,
    value: int | float | str | None,
    *,
    input_dialog: bool = False,
) -> str:
    """
    Construct a SetUserVar command to set user profile specific variables.

    SetUserVar sets variables that are specific to the current user profile.
    These variables are not shared across different user profiles.

    Args:
        var_name: Variable name (should start with $, e.g., "$mycounter")
        value: Variable value (numeric, text, or None to delete).
               If None, deletes the variable.
        input_dialog: If True, wraps value in parentheses to show input dialog.
                      Only applicable when value is a string.

    Returns:
        str: MA command to set user variable

    Examples:
        >>> set_user_var("$mycounter", 5)
        'setuservar $mycounter = 5'
        >>> set_user_var("$myname", "John")
        'setuservar $myname = "John"'
        >>> set_user_var("$CueNumber", "Cue number to store?", input_dialog=True)
        'setuservar $CueNumber = ("Cue number to store?")'
        >>> set_user_var("$CueNumber", None)
        'setuservar $CueNumber ='
    """
    # Delete variable if value is None
    if value is None:
        return f"setuservar {var_name} ="

    # Input dialog mode (only for strings)
    if input_dialog and isinstance(value, str):
        return f'setuservar {var_name} = ("{value}")'

    # Numeric value
    if isinstance(value, (int, float)):
        return f"setuservar {var_name} = {value}"

    # Text value (add quotes)
    return f'setuservar {var_name} = "{value}"'


def set_var(
    var_name: str,
    value: int | float | str | None,
    *,
    input_dialog: bool = False,
) -> str:
    """
    Construct a SetVar command to set global show variables.

    SetVar sets variables that are global to the show.
    Every user profile can use these variables.

    Args:
        var_name: Variable name (should start with $, e.g., "$mycounter")
        value: Variable value (numeric, text, or None to delete).
               If None, deletes the variable.
        input_dialog: If True, wraps value in parentheses to show input dialog.
                      Only applicable when value is a string.

    Returns:
        str: MA command to set show variable

    Examples:
        >>> set_var("$mycounter", 5)
        'setvar $mycounter = 5'
        >>> set_var("$myname", "John")
        'setvar $myname = "John"'
        >>> set_var("$Songname", "Which song?", input_dialog=True)
        'setvar $Songname = ("Which song?")'
        >>> set_var("$CueNumber", None)
        'setvar $CueNumber ='
    """
    # Delete variable if value is None
    if value is None:
        return f"setvar {var_name} ="

    # Input dialog mode (only for strings)
    if input_dialog and isinstance(value, str):
        return f'setvar {var_name} = ("{value}")'

    # Numeric value
    if isinstance(value, (int, float)):
        return f"setvar {var_name} = {value}"

    # Text value (add quotes)
    return f'setvar {var_name} = "{value}"'


def add_user_var(
    var_name: str,
    value: int | float | str,
) -> str:
    """
    Construct an AddUserVar command to change/extend user variable content.

    AddUserVar modifies existing user variable content:
    - Numeric: Adds to existing value (5 + 6 = 11)
    - Text: Concatenates to existing text ("John" + " Doe" = "John Doe")

    Args:
        var_name: Variable name (should start with $, e.g., "$mycounter")
        value: Value to add (numeric or text)

    Returns:
        str: MA command to add to user variable

    Examples:
        >>> add_user_var("$mycounter", 6)
        'adduservar $mycounter = 6'
        >>> add_user_var("$myname", " Doe")
        'adduservar $myname = " Doe"'
    """
    # Numeric value
    if isinstance(value, (int, float)):
        return f"adduservar {var_name} = {value}"

    # Text value (add quotes)
    return f'adduservar {var_name} = "{value}"'


def add_var(
    var_name: str,
    value: int | float | str,
) -> str:
    """
    Construct an AddVar command to change/extend show variable content.

    AddVar modifies existing show variable content:
    - Numeric: Adds to existing value (5 + 6 = 11)
    - Text: Concatenates to existing text ("John" + " Doe" = "John Doe")

    Args:
        var_name: Variable name (should start with $, e.g., "$mycounter")
        value: Value to add (numeric or text)

    Returns:
        str: MA command to add to show variable

    Examples:
        >>> add_var("$mycounter", 6)
        'addvar $mycounter = 6'
        >>> add_var("$myname", " Doe")
        'addvar $myname = " Doe"'
    """
    # Numeric value
    if isinstance(value, (int, float)):
        return f"addvar {var_name} = {value}"

    # Text value (add quotes)
    return f'addvar {var_name} = "{value}"'

