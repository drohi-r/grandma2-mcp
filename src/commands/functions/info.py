"""
List and Info Function Keywords for grandMA2 Command Builder

This module contains functions related to list and info operations.

List is used to display show data in the command line feedback window.
Info is used to add or display user information for objects.

Included functions:
- list_objects: Generic list command
- list_cue: List cues
- list_group: List groups
- list_preset: List presets
- list_attribute: List attributes
- list_messages: List messages
- info: Generic info command
- info_group: Group info
- info_cue: Cue info
- info_preset: Preset info
"""

from ..constants import PRESET_TYPES
from ..helpers import quote_name

# ============================================================================
# LIST FUNCTION KEYWORD
# ============================================================================


def list_objects(
    object_type: str | None = None,
    object_id: int | str | None = None,
    *,
    name: str | None = None,
    match_mode: str = "literal",
    end: int | None = None,
    filename: str | None = None,
    condition: str | None = None,
) -> str:
    """
    Construct a List command to display show data in the command line feedback window.

    List is used to display show data in the command line feedback window, such as Cues, Groups,
    Presets, Messages, etc. If no object type is specified, it displays data for the current destination.

    Supports name-based filtering with optional wildcard matching (MA2 wildcard spec):
    - match_mode="literal"  (default): special chars in name are quoted (treated literally)
    - match_mode="wildcard": name is emitted raw so '*' is a wildcard operator

    Args:
        object_type: Object type (e.g., "cue", "group", "preset", "attribute", "messages")
        object_id: Object ID or identifier (optional)
        name: Name or wildcard pattern to filter by (optional)
        match_mode: "literal" (default) or "wildcard" — controls quoting of name
        end: End ID for range (uses Thru)
        filename: Output CSV filename (saved to reports folder)
        condition: Condition filter (only for Messages)

    Returns:
        str: MA List command

    Examples:
        >>> list_objects("cue")
        'list cue'
        >>> list_objects("group", end=10)
        'list group thru 10'
        >>> list_objects("attribute")
        'list attribute'
        >>> list_objects("preset", '"color"."m*"')
        'list preset "color"."m*"'
        >>> list_objects("group", filename="my_groups")
        'list group /filename=my_groups'
        >>> list_objects("group", name="Mac700*", match_mode="wildcard")
        'list group Mac700*'
        >>> list_objects("group", name="Front*Wash")
        'list group "Front*Wash"'
    """
    # Base command
    if object_type is None:
        cmd = "list"
    else:
        cmd = f"list {object_type}"

    # Handle object ID or range
    if object_id is not None:
        if end is not None:
            cmd = f"{cmd} {object_id} thru {end}"
        else:
            cmd = f"{cmd} {object_id}"
    elif end is not None:
        # Only end, means "thru N"
        cmd = f"{cmd} thru {end}"

    # Name-based filtering (with wildcard support)
    if name is not None:
        cmd = f"{cmd} {quote_name(name, match_mode)}"

    # Option handling
    if filename:
        cmd = f"{cmd} /filename={filename}"

    if condition:
        cmd = f"{cmd} /condition={condition}"

    return cmd


def list_cue(
    cue_id: int | str | None = None,
    *,
    end: int | None = None,
    sequence_id: int | None = None,
    filename: str | None = None,
) -> str:
    """
    Construct a List command for cues.

    List cues from the selected Executor or specified Sequence.

    Args:
        cue_id: Cue ID (optional)
        end: End cue ID for range
        sequence_id: Sequence ID (optional, specifies specific sequence)
        filename: Output CSV filename

    Returns:
        str: MA List command for cues

    Examples:
        >>> list_cue()
        'list cue'
        >>> list_cue(1, end=10)
        'list cue 1 thru 10'
        >>> list_cue(sequence_id=5)
        'list cue sequence 5'
    """
    cmd = "list cue"

    if cue_id is not None:
        if end is not None:
            cmd = f"{cmd} {cue_id} thru {end}"
        else:
            cmd = f"{cmd} {cue_id}"
    elif end is not None:
        cmd = f"{cmd} thru {end}"

    if sequence_id is not None:
        cmd = f"{cmd} sequence {sequence_id}"

    if filename:
        cmd = f"{cmd} /filename={filename}"

    return cmd


def list_group(
    group_id: int | None = None,
    *,
    end: int | None = None,
    filename: str | None = None,
) -> str:
    """
    Construct a List command for groups.

    List groups in the Group Pool.

    Args:
        group_id: Group ID (optional, specifies starting point)
        end: End group ID for range
        filename: Output CSV filename

    Returns:
        str: MA List command for groups

    Examples:
        >>> list_group()
        'list group'
        >>> list_group(end=10)
        'list group thru 10'
        >>> list_group(1, end=5)
        'list group 1 thru 5'
    """
    cmd = "list group"

    if group_id is not None:
        if end is not None:
            cmd = f"{cmd} {group_id} thru {end}"
        else:
            cmd = f"{cmd} {group_id}"
    elif end is not None:
        cmd = f"{cmd} thru {end}"

    if filename:
        cmd = f"{cmd} /filename={filename}"

    return cmd


def list_preset(
    preset_type: int | str | None = None,
    preset_id: int | str | None = None,
    *,
    end: int | None = None,
    filename: str | None = None,
) -> str:
    """
    Construct a List command for presets.

    List all presets in the Preset Pool.

    Args:
        preset_type: Preset type (e.g., "color", "position", 4, etc.)
        preset_id: Preset ID or name pattern (e.g., '"m*"')
        end: End Preset ID for range
        filename: Output CSV filename

    Returns:
        str: MA List command for presets

    Examples:
        >>> list_preset()
        'list preset'
        >>> list_preset("color")
        'list preset "color"'
        >>> list_preset("color", '"m*"')
        'list preset "color"."m*"'
        >>> list_preset(4, '"m*"')
        'list preset 4."m*"'
    """
    cmd = "list preset"

    if preset_type is not None:
        # Handle string type names (add quotes) or numeric types
        if isinstance(preset_type, str) and not preset_type.startswith('"'):
            type_part = f'"{preset_type}"'
        else:
            type_part = str(preset_type)

        if preset_id is not None:
            cmd = f"{cmd} {type_part}.{preset_id}"
        else:
            cmd = f"{cmd} {type_part}"
    elif preset_id is not None:
        if end is not None:
            cmd = f"{cmd} {preset_id} thru {end}"
        else:
            cmd = f"{cmd} {preset_id}"

    if filename:
        cmd = f"{cmd} /filename={filename}"

    return cmd


def list_attribute(*, filename: str | None = None) -> str:
    """
    Construct a List command for attributes.

    List all attribute names that exist in the show file.

    Args:
        filename: Output CSV filename

    Returns:
        str: MA List command for attributes

    Example:
        >>> list_attribute()
        'list attribute'
    """
    cmd = "list attribute"

    if filename:
        cmd = f"{cmd} /filename={filename}"

    return cmd


def list_messages(*, condition: str | None = None, filename: str | None = None) -> str:
    """
    Construct a List command for messages.

    List messages from the message center.

    Args:
        condition: Condition filter
        filename: Output CSV filename

    Returns:
        str: MA List command for messages

    Examples:
        >>> list_messages()
        'list messages'
        >>> list_messages(condition="error")
        'list messages /condition=error'
    """
    cmd = "list messages"

    if condition:
        cmd = f"{cmd} /condition={condition}"

    if filename:
        cmd = f"{cmd} /filename={filename}"

    return cmd


# ============================================================================
# LIST* FUNCTION KEYWORDS (specialized list commands)
# ============================================================================


def list_shows() -> str:
    """
    Construct a ListShows command to list available show files.

    Returns:
        str: MA command to list shows

    Examples:
        >>> list_shows()
        'listshows'
    """
    return "listshows"


def list_oops() -> str:
    """
    Construct a ListOops command to display undo history.

    Returns:
        str: MA command to list undo history

    Examples:
        >>> list_oops()
        'listoops'
    """
    return "listoops"


def list_library() -> str:
    """
    Construct a ListLibrary command to browse the fixture library.

    Returns:
        str: MA command to list library

    Examples:
        >>> list_library()
        'listlibrary'
    """
    return "listlibrary"


def list_effect_library() -> str:
    """
    Construct a ListEffectLibrary command to browse effect templates.

    Returns:
        str: MA command to list effect library

    Examples:
        >>> list_effect_library()
        'listeffectlibrary'
    """
    return "listeffectlibrary"


def list_macro_library() -> str:
    """
    Construct a ListMacroLibrary command to browse macro templates.

    Returns:
        str: MA command to list macro library

    Examples:
        >>> list_macro_library()
        'listmacrolibrary'
    """
    return "listmacrolibrary"


def list_plugin_library() -> str:
    """
    Construct a ListPluginLibrary command to browse the grandMA2 plugin library.

    Returns:
        str: MA command to list plugin library

    Examples:
        >>> list_plugin_library()
        'listpluginlibrary'
    """
    return "listpluginlibrary"


def list_fader_modules() -> str:
    """
    Construct a ListFaderModules command to list connected fader modules.

    Returns:
        str: MA command to list fader modules

    Examples:
        >>> list_fader_modules()
        'listfadermodules'
    """
    return "listfadermodules"


def list_update() -> str:
    """
    Construct a ListUpdate command to list programming update history.

    Returns:
        str: MA command to list update history

    Examples:
        >>> list_update()
        'listupdate'
    """
    return "listupdate"


# ============================================================================
# INFO FUNCTION KEYWORD
# ============================================================================


def info(
    object_type: str,
    object_id: int | str | None = None,
    *,
    name: str | None = None,
    match_mode: str = "literal",
    end: int | None = None,
    text: str | None = None,
) -> str:
    """
    Construct an Info command to add or display user info to an object.

    Info is used to add or display user information for an object.
    If text is provided, it sets the information; otherwise, it displays existing information.

    Supports name-based selection with optional wildcard matching:
    - match_mode="literal"  (default): special chars in name are quoted (treated literally)
    - match_mode="wildcard": name is emitted raw so '*' is a wildcard operator

    Args:
        object_type: Object type (e.g., "group", "cue", "preset")
        object_id: Object ID (optional if name is given)
        name: Name or wildcard pattern to select by (optional)
        match_mode: "literal" (default) or "wildcard" — controls quoting of name
        end: End ID for range (uses Thru)
        text: Information text to add (optional; if not provided, displays existing information)

    Returns:
        str: MA Info command

    Examples:
        >>> info("group", 3)
        'info group 3'
        >>> info("group", 3, text="these fixtures are in the backtruss")
        'info group 3 "these fixtures are in the backtruss"'
        >>> info("cue", 1, end=5)
        'info cue 1 thru 5'
        >>> info("group", name="Mac*", match_mode="wildcard")
        'info group Mac*'
        >>> info("group", name="Front*Wash")
        'info group "Front*Wash"'
    """
    cmd = f"info {object_type}"

    # Build object reference — ID takes priority, then name
    if object_id is not None:
        if end is not None:
            cmd = f"{cmd} {object_id} thru {end}"
        else:
            cmd = f"{cmd} {object_id}"
    elif name is not None:
        cmd = f"{cmd} {quote_name(name, match_mode)}"

    # If text is provided, add the information
    if text is not None:
        cmd = f'{cmd} "{text}"'

    return cmd


def info_group(
    group_id: int, *, end: int | None = None, text: str | None = None
) -> str:
    """
    Construct an Info command for groups.

    Add or display information for a Group.

    Args:
        group_id: Group ID
        end: End Group ID for range
        text: Information text to add

    Returns:
        str: MA Info command for group

    Examples:
        >>> info_group(3)
        'info group 3'
        >>> info_group(3, text="backtruss fixtures")
        'info group 3 "backtruss fixtures"'
    """
    return info("group", group_id, end=end, text=text)


def info_cue(
    cue_id: int | str,
    *,
    sequence_id: int | None = None,
    end: int | str | None = None,
    text: str | None = None,
) -> str:
    """
    Construct an Info command for cues.

    Add or display information for a Cue.

    Args:
        cue_id: Cue ID
        sequence_id: Sequence ID (optional)
        end: End Cue ID for range
        text: Information text to add

    Returns:
        str: MA Info command for cue

    Examples:
        >>> info_cue(5)
        'info cue 5'
        >>> info_cue(5, sequence_id=2)
        'info cue 5 sequence 2'
        >>> info_cue(1, text="opening look")
        'info cue 1 "opening look"'
    """
    # Build object part
    if end is not None:
        object_part = f"cue {cue_id} thru {end}"
    else:
        object_part = f"cue {cue_id}"

    if sequence_id is not None:
        object_part = f"{object_part} sequence {sequence_id}"

    cmd = f"info {object_part}"

    if text is not None:
        cmd = f'{cmd} "{text}"'

    return cmd


def info_preset(
    preset_type: int | str,
    preset_id: int | str,
    *,
    text: str | None = None,
) -> str:
    """
    Construct an Info command for presets.

    Add or display information for a Preset.

    Args:
        preset_type: Preset type (e.g., "color", 4)
        preset_id: Preset ID
        text: Information text to add

    Returns:
        str: MA Info command for preset

    Examples:
        >>> info_preset("color", 1)
        'info preset 2.1'
        >>> info_preset(4, 5, text="deep blue")
        'info preset 4.5 "deep blue"'
    """
    # Convert preset type
    if isinstance(preset_type, str):
        type_num = PRESET_TYPES.get(preset_type.lower(), preset_type)
    else:
        type_num = preset_type

    cmd = f"info preset {type_num}.{preset_id}"

    if text is not None:
        cmd = f'{cmd} "{text}"'

    return cmd
