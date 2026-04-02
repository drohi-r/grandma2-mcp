"""
Call Function Keyword for grandMA2 Command Builder

Call is a function used to apply/engage an object or its content.
It loads values into the programmer without selecting fixtures.

Key behaviors:
- If used on objects with parameters (fixture values), values are loaded
  into programmer WITHOUT selecting fixtures
- At universal presets, all fixtures supporting the attributes are affected
- Shortcut: Ca

Included functions:
- call: Apply/engage an object or its content
"""



def call(
    target: str,
    *,
    status: bool | None = None,
    layer: bool = False,
    screen: bool = False,
    toggle_activation: bool = False,
) -> str:
    """
    Construct a Call command to apply/engage an object or its content.

    Call loads values into the programmer without selecting fixtures.
    This is useful for loading preset values, cue content, or sequence
    status without modifying the current fixture selection.

    Args:
        target: The object to call (e.g., "preset 3.1", "sequence 1", "cue 3")
        status: If True/False, adds /status=true or /status=false option.
                Takes all values along with tracking values actively into programmer.
        layer: If True, adds /layer option. Sets destination layer.
        screen: If True, adds /screen option. Sets destination screen.
        toggle_activation: If True, adds /toggle_activation option.

    Returns:
        str: MA command to call the object

    Examples:
        >>> call("preset 3.1")
        'call preset 3.1'
        >>> call("sequence 1")
        'call sequence 1'
        >>> call("cue 3")
        'call cue 3'
        >>> call("cue 3", status=True)
        'call cue 3 /status=true'
        >>> call("preset 1.1", layer=True)
        'call preset 1.1 /layer'
        >>> call("cue 5", status=True, layer=True)
        'call cue 5 /status=true /layer'
    """
    # Build the base command
    command = f"call {target}"

    # Collect options in a list
    options = []

    # status option: /status=true or /status=false
    if status is not None:
        options.append(f"/status={'true' if status else 'false'}")

    # layer option: /layer
    if layer:
        options.append("/layer")

    # screen option: /screen
    if screen:
        options.append("/screen")

    # toggle_activation option: /toggle_activation
    if toggle_activation:
        options.append("/toggle_activation")

    # Append options to command
    if options:
        command = f"{command} {' '.join(options)}"

    return command

