"""
Master Function Keywords for grandMA2 Command Builder

This module contains functions related to master and special master control.

Included functions:
- master_at: Set a master fader level
- special_master_at: Set a special master level (grand, speed, rate, playback)
- list_masters: List all masters in the master pool
"""


# ============================================================================
# MASTER FUNCTION KEYWORD
# ============================================================================


def master_at(master_id: int, level: int) -> str:
    """
    Construct a Master At command to set a master fader level.

    Args:
        master_id: Master pool slot number
        level: Level value (0-100 percentage)

    Returns:
        str: MA command string

    Examples:
        >>> master_at(1, 80)
        'Master 1 At 80'
        >>> master_at(3, 0)
        'Master 3 At 0'
    """
    return f"Master {master_id} At {level}"


# ============================================================================
# SPECIALMASTER FUNCTION KEYWORD
# ============================================================================


def special_master_at(master_type: int, master_id: int, level: int) -> str:
    """
    Construct a SpecialMaster At command to set a special master level.

    Special masters include Grand Master, Speed Master, Rate Master,
    and Playback Master. They use dotted notation: type.id.

    Args:
        master_type: Special master type number
        master_id: Master ID within the type
        level: Level value (0-100 percentage)

    Returns:
        str: MA command string

    Examples:
        >>> special_master_at(3, 1, 50)
        'SpecialMaster 3.1 At 50'
        >>> special_master_at(1, 1, 100)
        'SpecialMaster 1.1 At 100'
    """
    return f"SpecialMaster {master_type}.{master_id} At {level}"


def list_masters() -> str:
    """
    Construct a List Master command to enumerate all masters.

    Returns:
        str: MA command string

    Examples:
        >>> list_masters()
        'List Master'
    """
    return "List Master"
