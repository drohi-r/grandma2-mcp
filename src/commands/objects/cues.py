"""
Cue/Sequence Object Keywords for grandMA2 Command Builder

Contains Object Keywords related to Cues and Sequences:
- cue: Reference cues
- cue_part: Convenience function to reference cue parts
- sequence: Reference sequences

Cue is the only object type that accepts decimal IDs (range 0.001 to 9999.999).
"""



def cue(
    cue_id: int | float | list[int | float] | None = None,
    *,
    end: int | float | None = None,
    part: int | None = None,
    executor: int | None = None,
    sequence: int | None = None,
) -> str:
    """
    Construct a Cue command to reference cues.

    Cue is the only object type that accepts decimal IDs.
    Allowed ID range is from 0.001 to 9999.999.
    The default function for cue objects is SelFix.

    Args:
        cue_id: Cue number (int or float) or list of cue numbers
        end: End cue number (for range selection)
        part: Part number within the Cue
        executor: Executor number to specify which executor
        sequence: Sequence number to specify which sequence

    Returns:
        str: MA command string to reference cues

    Raises:
        ValueError: When cue_id is not provided

    Examples:
        >>> cue(5)
        'cue 5'
        >>> cue(3.5)
        'cue 3.5'
        >>> cue(1, end=10)
        'cue 1 thru 10'
        >>> cue([1, 3, 5])
        'cue 1 + 3 + 5'
        >>> cue(3, part=2)
        'cue 3 part 2'
        >>> cue(3, executor=1)
        'cue 3 executor 1'
        >>> cue(5, sequence=3)
        'cue 5 sequence 3'
    """
    if cue_id is None:
        raise ValueError("Must provide cue_id")

    # Helper function: format cue ID (preserve decimal precision)
    def format_cue_id(cid: int | float) -> str:
        if isinstance(cid, float):
            formatted = f"{cid:.3f}".rstrip("0").rstrip(".")
            return formatted
        return str(cid)

    # Handle list selection (using + separator)
    if isinstance(cue_id, list):
        if len(cue_id) == 1:
            return f"cue {format_cue_id(cue_id[0])}"
        cues_str = " + ".join(format_cue_id(cid) for cid in cue_id)
        return f"cue {cues_str}"

    # Build base command
    base = f"cue {format_cue_id(cue_id)}"

    # Handle range selection (using thru)
    if end is not None:
        if cue_id == end:
            pass  # Same start and end, use single cue only
        else:
            base = f"cue {format_cue_id(cue_id)} thru {format_cue_id(end)}"

    # Add part if specified
    if part is not None:
        base = f"{base} part {part}"

    # Add executor if specified
    if executor is not None:
        base = f"{base} executor {executor}"

    # Add sequence if specified
    if sequence is not None:
        base = f"{base} sequence {sequence}"

    return base


def cue_part(
    cue_id: int | float,
    part_id: int,
    *,
    executor: int | None = None,
    sequence: int | None = None,
) -> str:
    """
    Convenience function to reference cue parts.

    Parts divide cues into segments, allowing different timing for different fixture parameter groups.

    Args:
        cue_id: Cue number (int or float)
        part_id: Part number within the Cue
        executor: Executor number to specify which executor
        sequence: Sequence number to specify which sequence

    Returns:
        str: MA command string to reference cue parts

    Examples:
        >>> cue_part(3, 2)
        'cue 3 part 2'
        >>> cue_part(2.5, 1)
        'cue 2.5 part 1'
        >>> cue_part(3, 2, executor=1)
        'cue 3 part 2 executor 1'
        >>> cue_part(3, 2, sequence=5)
        'cue 3 part 2 sequence 5'
    """
    return cue(cue_id, part=part_id, executor=executor, sequence=sequence)


def sequence(
    sequence_id: int | list[int] | None = None,
    *,
    end: int | None = None,
    pool: int | None = None,
) -> str:
    """
    Construct a Sequence command to reference sequences.

    The default function for the sequence keyword is SelFix.
    If the Sequence keyword is used with an ID, all fixtures in the sequence will be selected.

    Args:
        sequence_id: Sequence number or list of sequence numbers
        end: End sequence number (for range selection)
        pool: Sequence pool number (for pool.id syntax)

    Returns:
        str: MA command string to reference sequences

    Raises:
        ValueError: When sequence_id is not provided
        ValueError: When pool is used with multiple sequences

    Examples:
        >>> sequence(3)
        'sequence 3'
        >>> sequence(1, end=5)
        'sequence 1 thru 5'
        >>> sequence([1, 3, 5])
        'sequence 1 + 3 + 5'
        >>> sequence(5, pool=2)
        'sequence 2.5'
    """
    if sequence_id is None:
        raise ValueError("Must provide sequence_id")

    # Handle pool syntax (pool.id)
    if pool is not None:
        if isinstance(sequence_id, list):
            raise ValueError("Cannot use pool with multiple sequences")
        return f"sequence {pool}.{sequence_id}"

    # Handle list selection (using + separator)
    if isinstance(sequence_id, list):
        if len(sequence_id) == 1:
            return f"sequence {sequence_id[0]}"
        seqs_str = " + ".join(str(sid) for sid in sequence_id)
        return f"sequence {seqs_str}"

    # Handle range selection (using thru)
    if end is not None:
        if sequence_id == end:
            return f"sequence {sequence_id}"
        return f"sequence {sequence_id} thru {end}"

    # Single selection
    return f"sequence {sequence_id}"
