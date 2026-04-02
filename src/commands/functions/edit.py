"""
Edit Function Keywords for grandMA2 Command Builder

This module contains functions related to edit operations.

Included functions:
- Edit: edit
- Copy: copy, copy_cue
- Move: move
- Delete: delete, delete_cue, delete_group, delete_preset, delete_fixture, delete_messages
- Remove: remove, remove_selection, remove_preset_type, remove_fixture, remove_effect
"""


from ..constants import PRESET_TYPES

# ============================================================================
# EDIT FUNCTION KEYWORD
# ============================================================================


def edit(
    object_type: str | None = None,
    object_id: int | str | list[int] | None = None,
    *,
    end: int | None = None,
    noconfirm: bool = False,
) -> str:
    """
    Construct an Edit command to modify values or open editors.

    Edit is a function keyword used to modify values. When called without
    arguments, it takes the first cue in the sequence of a selected executor.
    If the executor is in a certain cue, then this cue is edited.

    Args:
        object_type: Type of object to edit (e.g., "effect", "cue", "sequence")
        object_id: Object ID (int, string like "2.1", or list of ints)
        end: End ID for range selection
        noconfirm: Suppress confirmation pop-up

    Returns:
        str: MA command to edit object(s)

    Examples:
        >>> edit()
        'edit'
        >>> edit("effect", 2)
        'edit effect 2'
        >>> edit("cue", 5)
        'edit cue 5'
        >>> edit("dmxuniverse", 3)
        'edit dmxuniverse 3'
        >>> edit("cue", 1, end=5)
        'edit cue 1 thru 5'
        >>> edit("group", [1, 3, 5])
        'edit group 1 + 3 + 5'
        >>> edit("effect", 2, noconfirm=True)
        'edit effect 2 /noconfirm'
    """
    # If no object type specified, return simple edit command
    if object_type is None:
        return "edit"

    # Build ID part
    if object_id is None:
        cmd = f"edit {object_type}"
    elif isinstance(object_id, list):
        id_part = " + ".join(str(i) for i in object_id)
        cmd = f"edit {object_type} {id_part}"
    elif end is not None:
        cmd = f"edit {object_type} {object_id} thru {end}"
    else:
        cmd = f"edit {object_type} {object_id}"

    # Add noconfirm option
    if noconfirm:
        cmd = f"{cmd} /noconfirm"

    return cmd


# ============================================================================
# CUT FUNCTION KEYWORD
# ============================================================================


def cut(
    object_type: str,
    object_id: int | str | list[int | str],
    *,
    end: int | str | None = None,
) -> str:
    """
    Construct a Cut command to specify source objects for a two-step move action.

    Cut prepares objects to be moved via the Paste command. The object list is
    temporarily stored for later use. Note: Cut & Paste does not work with cue
    objects. To move cues, use the Move keyword instead.

    Args:
        object_type: Type of object (e.g., "group", "preset", "sequence", "macro")
        object_id: Object ID (int, string like "4.1", or list)
        end: End ID for range selection (thru)

    Returns:
        str: MA command to cut object(s)

    Examples:
        >>> cut("preset", "4.1")
        'cut preset 4.1'
        >>> cut("group", 1)
        'cut group 1'
        >>> cut("group", 1, end=5)
        'cut group 1 thru 5'
        >>> cut("preset", ["4.1", "4.2", "4.3"])
        'cut preset 4.1 + 4.2 + 4.3'
    """
    # Handle list selection
    if isinstance(object_id, list):
        ids_str = " + ".join(str(i) for i in object_id)
        return f"cut {object_type} {ids_str}"

    # Handle range selection (using thru)
    if end is not None:
        return f"cut {object_type} {object_id} thru {end}"

    # Single object
    return f"cut {object_type} {object_id}"


# ============================================================================
# PASTE FUNCTION KEYWORD
# ============================================================================


def paste(
    object_type_or_id: str | int | None = None,
    target_id: int | str | None = None,
) -> str:
    """
    Construct a Paste command to paste copied content or move cut objects.

    Paste will paste previous copied content from clipboard.xml, or move
    previous Cut object-lists. If no object type is given and command line
    destination is root, the default object is Cue.

    Args:
        object_type_or_id: Type of object (str) or target ID (int) if no type given
        target_id: Target ID to paste to (used when object_type_or_id is a string)

    Returns:
        str: MA command to paste object(s)

    Examples:
        >>> paste()
        'paste'
        >>> paste(15)
        'paste 15'
        >>> paste("group", 5)
        'paste group 5'
        >>> paste("preset", "4.5")
        'paste preset 4.5'
    """
    # No arguments - basic paste
    if object_type_or_id is None:
        return "paste"

    # Single argument - could be just target ID (for cues)
    if target_id is None:
        return f"paste {object_type_or_id}"

    # Object type and target ID
    return f"paste {object_type_or_id} {target_id}"


# ============================================================================
# COPY FUNCTION KEYWORD
# ============================================================================


def copy(
    object_type: str,
    object_id: int | list[int],
    target: int | list[int] | None = None,
    *,
    end: int | None = None,
    target_end: int | None = None,
    overwrite: bool = False,
    merge: bool = False,
    status: bool | None = None,
    cueonly: bool | None = None,
    noconfirm: bool = False,
) -> str:
    """
    Construct a Copy command to create copies of objects.

    If no target is given, the object will be exported to clipboard.xml
    for use with the Paste keyword.

    Args:
        object_type: Type of object (e.g., "group", "macro", "cue")
        object_id: Object ID or list of IDs to copy
        target: Target ID or list of target IDs (None = export to clipboard)
        end: End ID for source range (object_id thru end)
        target_end: End ID for target range (target thru target_end)
        overwrite: Replace existing content
        merge: Add to existing content
        status: Add tracking status to existing content
        cueonly: Prevent changes to track forward
        noconfirm: Suppress confirmation pop-up

    Returns:
        str: MA command to copy object(s)

    Examples:
        >>> copy("group", 1, 5)
        'copy group 1 at 5'
        >>> copy("group", 1, end=3, target=11)
        'copy group 1 thru 3 at 11'
        >>> copy("group", 2, target=6, target_end=8)
        'copy group 2 at 6 thru 8'
        >>> copy("macro", 2, 6)
        'copy macro 2 at 6'
        >>> copy("cue", 5)
        'copy cue 5'
    """
    # Build source part
    if isinstance(object_id, list):
        source = " + ".join(str(i) for i in object_id)
        cmd = f"copy {object_type} {source}"
    elif end is not None:
        cmd = f"copy {object_type} {object_id} thru {end}"
    else:
        cmd = f"copy {object_type} {object_id}"

    # Build target part (if provided)
    if target is not None:
        if isinstance(target, list):
            target_str = " + ".join(str(t) for t in target)
            cmd += f" at {target_str}"
        elif target_end is not None:
            cmd += f" at {target} thru {target_end}"
        else:
            cmd += f" at {target}"

    # Build options
    options = []
    if overwrite:
        options.append("/overwrite")
    if merge:
        options.append("/merge")
    if status is not None:
        options.append(f"/status={'true' if status else 'false'}")
    if cueonly is not None:
        options.append(f"/cueonly={'true' if cueonly else 'false'}")
    if noconfirm:
        options.append("/noconfirm")

    if options:
        cmd += " " + " ".join(options)

    return cmd


def copy_cue(
    cue_id: int,
    target: int | None = None,
    *,
    end: int | None = None,
    target_end: int | None = None,
    overwrite: bool = False,
    merge: bool = False,
    status: bool | None = None,
    cueonly: bool | None = None,
    noconfirm: bool = False,
) -> str:
    """
    Construct a Copy command specifically for cues.

    Cue is the default object type for Copy when no object type is specified.

    Args:
        cue_id: Cue ID to copy
        target: Target cue ID (None = export to clipboard)
        end: End ID for source range
        target_end: End ID for target range
        overwrite: Replace existing content
        merge: Add to existing content
        status: Add tracking status
        cueonly: Prevent changes to track forward
        noconfirm: Suppress confirmation pop-up

    Returns:
        str: MA command to copy cue(s)

    Examples:
        >>> copy_cue(2, 6)
        'copy cue 2 at 6'
        >>> copy_cue(5)
        'copy cue 5'
        >>> copy_cue(1, 10, end=5)
        'copy cue 1 thru 5 at 10'
    """
    return copy(
        "cue",
        cue_id,
        target,
        end=end,
        target_end=target_end,
        overwrite=overwrite,
        merge=merge,
        status=status,
        cueonly=cueonly,
        noconfirm=noconfirm,
    )


# ============================================================================
# MOVE FUNCTION KEYWORD
# ============================================================================


def move(
    object_type: str,
    object_id: int | list[int],
    target: int | list[int],
    *,
    end: int | None = None,
    target_end: int | None = None,
) -> str:
    """
    Construct a Move command to move objects and give them a new ID.

    If the destination is already taken, the moved object and the
    destination object will swap positions.

    Note: If the destination is a list, the number of elements in the
    destination list must be the same as in the source list.

    Args:
        object_type: Type of object (e.g., "group", "macro", "cue")
        object_id: Object ID or list of IDs to move
        target: Target ID or list of target IDs
        end: End ID for source range (object_id thru end)
        target_end: End ID for target range (target thru target_end)

    Returns:
        str: MA command to move object(s)

    Examples:
        >>> move("group", 5, 9)
        'move group 5 at 9'
        >>> move("group", 1, 10, end=3)
        'move group 1 thru 3 at 10'
        >>> move("cue", 5, 1)
        'move cue 5 at 1'
        >>> move("preset", [1, 3, 5], [10, 12, 14])
        'move preset 1 + 3 + 5 at 10 + 12 + 14'
    """
    # Build source part
    if isinstance(object_id, list):
        source = " + ".join(str(i) for i in object_id)
        cmd = f"move {object_type} {source}"
    elif end is not None:
        cmd = f"move {object_type} {object_id} thru {end}"
    else:
        cmd = f"move {object_type} {object_id}"

    # Build target part
    if isinstance(target, list):
        target_str = " + ".join(str(t) for t in target)
        cmd += f" at {target_str}"
    elif target_end is not None:
        cmd += f" at {target} thru {target_end}"
    else:
        cmd += f" at {target}"

    return cmd


# ============================================================================
# DELETE FUNCTION KEYWORD
# ============================================================================


def delete(
    object_type: str,
    object_id: int | str | list[int],
    *,
    end: int | None = None,
    selection_filter: str | None = None,
    deletevalues: bool = False,
    cueonly: bool = False,
    noconfirm: bool = False,
    region: bool = False,
    element: bool = False,
) -> str:
    """
    Construct a command to delete objects from the show file.

    Delete is used to remove data from the show file. If an object cannot be
    deleted directly, its associations will be removed (e.g., Fixture will be unpatched).

    Args:
        object_type: Object type (e.g., "cue", "group", "fixture", "world", "preset")
        object_id: Object ID (single, string, or list)
        end: End ID for range (uses thru syntax)
        selection_filter: Selection filter (delete data only for specified fixtures)
        deletevalues: Delete values when deleting cue part
        cueonly: Prevent changes from tracking to subsequent cues
        noconfirm: Suppress confirmation dialog
        region: Delete region in layout view
        element: Delete specific element in layout view

    Returns:
        str: MA command to delete objects

    Examples:
        >>> delete("cue", 7)
        'delete cue 7'
        >>> delete("group", 3)
        'delete group 3'
        >>> delete("fixture", 4)
        'delete fixture 4'
        >>> delete("cue", 1, end=5, noconfirm=True)
        'delete cue 1 thru 5 /noconfirm'
    """
    # Handle object_id (supports single, range, list)
    if isinstance(object_id, list):
        id_part = " + ".join(str(i) for i in object_id)
    elif end is not None:
        id_part = f"{object_id} thru {end}"
    else:
        id_part = str(object_id)

    cmd = f"delete {object_type} {id_part}"

    # Add selection filter
    if selection_filter:
        cmd = f"{cmd} {selection_filter}"

    # Add options
    options = []
    if deletevalues:
        options.append("/deletevalues")
    if cueonly:
        options.append("/cueonly")
    if noconfirm:
        options.append("/noconfirm")
    if region:
        options.append("/region")
    if element:
        options.append("/element")

    if options:
        cmd = f"{cmd} {' '.join(options)}"

    return cmd


def delete_cue(
    cue_id: int | float | str,
    *,
    sequence_id: int | None = None,
    end: int | float | str | None = None,
    deletevalues: bool = False,
    cueonly: bool = False,
    noconfirm: bool = False,
) -> str:
    """
    Construct a command to delete cue(s).

    Args:
        cue_id: Cue ID
        sequence_id: Sequence number (if not specified, uses currently selected executor)
        end: End cue ID for range
        deletevalues: Delete values when deleting cue part
        cueonly: Prevent changes from tracking to subsequent cues
        noconfirm: Suppress confirmation dialog

    Returns:
        str: MA command to delete cue(s)

    Examples:
        >>> delete_cue(7)
        'delete cue 7'
        >>> delete_cue(1, sequence_id=2)
        'delete cue 1 sequence 2'
        >>> delete_cue(1, end=5, noconfirm=True)
        'delete cue 1 thru 5 /noconfirm'
    """
    if end is not None:
        id_part = f"{cue_id} thru {end}"
    else:
        id_part = str(cue_id)

    cmd = f"delete cue {id_part}"

    if sequence_id is not None:
        cmd = f"{cmd} sequence {sequence_id}"

    # Add options
    options = []
    if deletevalues:
        options.append("/deletevalues")
    if cueonly:
        options.append("/cueonly")
    if noconfirm:
        options.append("/noconfirm")

    if options:
        cmd = f"{cmd} {' '.join(options)}"

    return cmd


def delete_group(
    group_id: int, *, end: int | None = None, noconfirm: bool = False
) -> str:
    """
    Construct a command to delete a group.

    Args:
        group_id: Group number
        end: End group ID for range
        noconfirm: Suppress confirmation dialog

    Returns:
        str: MA command to delete a group

    Examples:
        >>> delete_group(3)
        'delete group 3'
        >>> delete_group(1, end=5)
        'delete group 1 thru 5'
    """
    if end is not None:
        cmd = f"delete group {group_id} thru {end}"
    else:
        cmd = f"delete group {group_id}"

    if noconfirm:
        cmd = f"{cmd} /noconfirm"

    return cmd


def delete_preset(
    preset_type: str | int,
    preset_id: int,
    *,
    end: int | None = None,
    noconfirm: bool = False,
) -> str:
    """
    Construct a command to delete a preset.

    Args:
        preset_type: Preset type (e.g., "dimmer", "color", "position") or type number
        preset_id: Preset ID
        end: End preset ID for range
        noconfirm: Suppress confirmation dialog

    Returns:
        str: MA command to delete a preset

    Examples:
        >>> delete_preset("color", 5)
        'delete preset 4.5'
        >>> delete_preset(1, 1, end=10)
        'delete preset 1.1 thru 10'
    """
    if isinstance(preset_type, str):
        type_num = PRESET_TYPES.get(preset_type.lower(), 1)
    else:
        type_num = preset_type

    if end is not None:
        cmd = f"delete preset {type_num}.{preset_id} thru {end}"
    else:
        cmd = f"delete preset {type_num}.{preset_id}"

    if noconfirm:
        cmd = f"{cmd} /noconfirm"

    return cmd


def delete_fixture(
    fixture_id: int | list[int],
    *,
    end: int | None = None,
    noconfirm: bool = False,
) -> str:
    """
    Construct a command to delete (unpatch) fixture(s).

    Note: Delete Fixture will unpatch the fixture (remove DMX assignment), not remove it from the show.

    Args:
        fixture_id: Fixture ID (single or list)
        end: End fixture ID for range
        noconfirm: Suppress confirmation dialog

    Returns:
        str: MA command to unpatch fixture(s)

    Examples:
        >>> delete_fixture(4)
        'delete fixture 4'
        >>> delete_fixture(1, end=10)
        'delete fixture 1 thru 10'
    """
    if isinstance(fixture_id, list):
        id_part = " + ".join(str(i) for i in fixture_id)
    elif end is not None:
        id_part = f"{fixture_id} thru {end}"
    else:
        id_part = str(fixture_id)

    cmd = f"delete fixture {id_part}"

    if noconfirm:
        cmd = f"{cmd} /noconfirm"

    return cmd


def delete_messages() -> str:
    """
    Construct a command to delete all messages in the message center.

    Returns:
        str: MA command to delete messages

    Example:
        >>> delete_messages()
        'delete messages'
    """
    return "delete messages"


# ============================================================================
# CLONE FUNCTION KEYWORD
# ============================================================================
# Clone duplicates all data from source fixture(s) to target fixture(s).
# DESTRUCTIVE — modifies stored show data.
# ============================================================================


def clone(
    object_type: str,
    object_id: int | list[int],
    target: int | list[int],
    *,
    end: int | None = None,
    target_end: int | None = None,
    noconfirm: bool = False,
) -> str:
    """
    Clone data from source object(s) to target object(s).

    Clone copies all stored data (cues, presets, etc.) from the source to the
    target. Typically used with Fixture to duplicate a full fixture patch and
    all its associated data.

    Args:
        object_type: Object type (e.g., "fixture", "group", "sequence")
        object_id: Source object ID or list of IDs
        target: Target object ID or list of IDs
        end: End ID for source range (thru syntax)
        target_end: End ID for target range
        noconfirm: Suppress confirmation dialog

    Returns:
        str: MA command string

    Examples:
        >>> clone("fixture", 1, 2)
        'clone fixture 1 at 2'
        >>> clone("fixture", 1, 10, end=5)
        'clone fixture 1 thru 5 at 10'
        >>> clone("fixture", [1, 3], [2, 4])
        'clone fixture 1 + 3 at 2 + 4'
        >>> clone("fixture", 1, 2, noconfirm=True)
        'clone fixture 1 at 2 /noconfirm'
    """
    if isinstance(object_id, list):
        source = " + ".join(str(i) for i in object_id)
        cmd = f"clone {object_type} {source}"
    elif end is not None:
        cmd = f"clone {object_type} {object_id} thru {end}"
    else:
        cmd = f"clone {object_type} {object_id}"

    if isinstance(target, list):
        target_str = " + ".join(str(t) for t in target)
        cmd += f" at {target_str}"
    elif target_end is not None:
        cmd += f" at {target} thru {target_end}"
    else:
        cmd += f" at {target}"

    if noconfirm:
        cmd += " /noconfirm"

    return cmd


# ============================================================================
# BLOCK / UNBLOCK FUNCTION KEYWORDS
# ============================================================================
# Block makes a cue "blocking" — it stores all active values and stops tracking.
# Unblock removes the blocking flag, allowing values to track again.
# Both are DESTRUCTIVE — they modify cue data in the show file.
# ============================================================================


def block(
    cue_id: int | float,
    *,
    sequence_id: int | None = None,
    end: int | float | None = None,
) -> str:
    """
    Block a cue (make it blocking — stores all active values, stops tracking).

    A blocking cue stores all active values and prevents them from tracking
    from previous cues. Changes made before the block cue do not affect it.

    Args:
        cue_id: Cue number to block
        sequence_id: Sequence ID to scope the block (optional)
        end: End cue ID for range (thru syntax)

    Returns:
        str: MA command string

    Examples:
        >>> block(5)
        'block cue 5'
        >>> block(1, end=5)
        'block cue 1 thru 5'
        >>> block(3, sequence_id=2)
        'block cue 3 sequence 2'
    """
    if end is not None:
        id_part = f"{cue_id} thru {end}"
    else:
        id_part = str(cue_id)

    cmd = f"block cue {id_part}"
    if sequence_id is not None:
        cmd = f"{cmd} sequence {sequence_id}"
    return cmd


def unblock(
    cue_id: int | float,
    *,
    sequence_id: int | None = None,
    end: int | float | None = None,
) -> str:
    """
    Unblock a cue (remove blocking — allows values to track again).

    Removes the blocking flag from a cue so that values from earlier cues
    can track forward through it again.

    Args:
        cue_id: Cue number to unblock
        sequence_id: Sequence ID to scope the unblock (optional)
        end: End cue ID for range (thru syntax)

    Returns:
        str: MA command string

    Examples:
        >>> unblock(5)
        'unblock cue 5'
        >>> unblock(1, end=5)
        'unblock cue 1 thru 5'
        >>> unblock(3, sequence_id=2)
        'unblock cue 3 sequence 2'
    """
    if end is not None:
        id_part = f"{cue_id} thru {end}"
    else:
        id_part = str(cue_id)

    cmd = f"unblock cue {id_part}"
    if sequence_id is not None:
        cmd = f"{cmd} sequence {sequence_id}"
    return cmd


# ============================================================================
# REMOVE FUNCTION KEYWORD
# ============================================================================


def remove(
    object_type: str | None = None,
    object_id: int | str | None = None,
    *,
    end: int | None = None,
    if_filter: str | None = None,
) -> str:
    """
    Construct a command to enter remove values in the programmer.

    Remove is used to enter remove values in the programmer. When used with store merge,
    it can remove previously stored values and allow the previous cue's values to track again.

    Args:
        object_type: Object type (e.g., "selection", "fixture", "presettype")
        object_id: Object ID (optional, depends on object type)
        end: End ID for range
        if_filter: If filter condition (e.g., "PresetType 1")

    Returns:
        str: MA command to enter remove values

    Examples:
        >>> remove("selection")
        'remove selection'
        >>> remove("presettype", '"position"')
        'remove presettype "position"'
        >>> remove("fixture", 1, if_filter="PresetType 1")
        'remove fixture 1 if PresetType 1'
    """
    if object_type is None:
        return "remove"

    if object_id is not None:
        if end is not None:
            cmd = f"remove {object_type} {object_id} thru {end}"
        else:
            cmd = f"remove {object_type} {object_id}"
    else:
        cmd = f"remove {object_type}"

    if if_filter:
        cmd = f"{cmd} if {if_filter}"

    return cmd


def remove_selection() -> str:
    """
    Construct a command to enter remove values for all attributes of current selection.

    This will enter remove values for all attributes of the currently selected fixtures.

    Returns:
        str: MA command to remove selection values

    Example:
        >>> remove_selection()
        'remove selection'
    """
    return "remove selection"


def remove_preset_type(preset_type: str | int, *, if_filter: str | None = None) -> str:
    """
    Construct a command to enter remove values for a specific preset type.

    Args:
        preset_type: Preset type name (e.g., "position", "color") or type number
        if_filter: If filter condition

    Returns:
        str: MA command to remove preset type values

    Examples:
        >>> remove_preset_type("position")
        'remove presettype "position"'
        >>> remove_preset_type(1)
        'remove presettype 1'
    """
    if isinstance(preset_type, str):
        cmd = f'remove presettype "{preset_type}"'
    else:
        cmd = f"remove presettype {preset_type}"

    if if_filter:
        cmd = f"{cmd} if {if_filter}"

    return cmd


def remove_fixture(
    fixture_id: int | list[int],
    *,
    end: int | None = None,
    if_filter: str | None = None,
) -> str:
    """
    Construct a command to enter remove values for specific fixture(s).

    Args:
        fixture_id: Fixture ID (single or list)
        end: End fixture ID for range
        if_filter: If filter condition (e.g., "PresetType 1")

    Returns:
        str: MA command to remove fixture values

    Examples:
        >>> remove_fixture(1, if_filter="PresetType 1")
        'remove fixture 1 if PresetType 1'
        >>> remove_fixture(1, end=10)
        'remove fixture 1 thru 10'
    """
    if isinstance(fixture_id, list):
        id_part = " + ".join(str(i) for i in fixture_id)
    elif end is not None:
        id_part = f"{fixture_id} thru {end}"
    else:
        id_part = str(fixture_id)

    cmd = f"remove fixture {id_part}"

    if if_filter:
        cmd = f"{cmd} if {if_filter}"

    return cmd


def remove_effect(effect_id: int | str, *, end: int | None = None) -> str:
    """
    Construct a command to enter remove values for effect(s).

    Args:
        effect_id: Effect ID
        end: End effect ID for range

    Returns:
        str: MA command to remove effect values

    Examples:
        >>> remove_effect(1)
        'remove effect 1'
        >>> remove_effect(1, end=5)
        'remove effect 1 thru 5'
    """
    if end is not None:
        return f"remove effect {effect_id} thru {end}"
    return f"remove effect {effect_id}"


# ============================================================================
# OOPS FUNCTION KEYWORD
# ============================================================================


def oops(
    object_type: str | None = None,
    object_id: int | str | None = None,
) -> str:
    """
    Construct an Oops command to undo the last action.

    Oops is universal — accepted by all 16 object types (live-verified).
    When called bare (no arguments) it undoes the most recent action.
    When called with an object it undoes the last action on that object.

    Args:
        object_type: Object type (optional — scopes undo to an object)
        object_id: Object ID

    Returns:
        str: MA command string

    Examples:
        >>> oops()
        'oops'
        >>> oops("cue", 5)
        'oops cue 5'
        >>> oops("group", 3)
        'oops group 3'
    """
    if object_type is not None and object_id is not None:
        return f"oops {object_type} {object_id}"
    if object_type is not None:
        return f"oops {object_type}"
    return "oops"


# ============================================================================
# EXTRACT FUNCTION KEYWORD
# ============================================================================


def extract() -> str:
    """
    Construct an Extract command to pull tracked values into the programmer.

    Extract pulls tracked attribute values from the active cue into the
    programmer, making them available for editing without affecting other cues.

    Returns:
        str: MA command string

    Examples:
        >>> extract()
        'Extract'
    """
    return "Extract"

