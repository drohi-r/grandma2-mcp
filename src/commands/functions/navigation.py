"""
Navigation Function Keywords for grandMA2 Command Builder

Implements the ChangeDest (cd) command for navigating the grandMA2
command-line object tree.

grandMA2 supports these CD forms:
  cd /                          -> Go to root
  cd ..                         -> Go up one level
  cd [element-index]            -> Navigate by element index
  cd "element name"             -> Navigate by element name
  cd [object-type].[object-id]  -> Navigate by object type and ID
"""



def changedest(
    destination: str,
    object_id: int | str | None = None,
) -> str:
    """
    Build a ChangeDest (cd) command string.

    When ``object_id`` is provided, uses MA2 dot notation:
    ``cd [object-type].[object-id]``.

    Args:
        destination: Navigation target. Can be:
            - ``"/"`` for root
            - ``".."`` to go up one level
            - A numeric string (e.g. ``"5"``) to navigate by index
            - A quoted name (e.g. ``'"MySequence"'``) to navigate by name
            - An object type (e.g. ``"Group"``) when ``object_id`` is given
        object_id: Object ID, used with ``destination`` as object type.
            Produces dot notation: ``cd Group.1``.

    Returns:
        Formatted cd command string.

    Examples:
        >>> changedest("/")
        'cd /'
        >>> changedest("..")
        'cd ..'
        >>> changedest("5")
        'cd 5'
        >>> changedest('"MySequence"')
        'cd "MySequence"'
        >>> changedest("Group", 1)
        'cd Group.1'
        >>> changedest("Sequence", 3)
        'cd Sequence.3'
        >>> changedest("Preset", "4.1")
        'cd Preset.4.1'
    """
    if object_id is not None:
        return f"cd {destination}.{object_id}"

    return f"cd {destination}"
