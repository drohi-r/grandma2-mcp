"""
Executor Object Keywords for grandMA2 Command Builder

Contains Object Keywords related to Executors:
- executor: Reference executors

Executor is an object type that can contain sequences, chasers, or other objects.
"""



def executor(
    executor_id: int | list[int] | None = None,
    *,
    end: int | None = None,
    page: int | None = None,
) -> str:
    """
    Construct an Executor command to reference executors.

    Executor is an object type that can contain sequences, chasers, or other objects.

    Args:
        executor_id: Executor number or list of executor numbers
        end: End executor number (for range selection)
        page: Executor page number (for page.id syntax)

    Returns:
        str: MA command string to reference executors

    Raises:
        ValueError: When executor_id is not provided
        ValueError: When page is used with multiple executors

    Examples:
        >>> executor(3)
        'executor 3'
        >>> executor(1, end=5)
        'executor 1 thru 5'
        >>> executor([1, 3, 5])
        'executor 1 + 3 + 5'
        >>> executor(5, page=2)
        'executor 2.5'
    """
    if executor_id is None:
        raise ValueError("Must provide executor_id")

    # Handle page syntax (page.id)
    if page is not None:
        if isinstance(executor_id, list):
            raise ValueError("Cannot use page with multiple executors")
        return f"executor {page}.{executor_id}"

    # Handle list selection (using + separator)
    if isinstance(executor_id, list):
        if len(executor_id) == 1:
            return f"executor {executor_id[0]}"
        execs_str = " + ".join(str(eid) for eid in executor_id)
        return f"executor {execs_str}"

    # Handle range selection (using thru)
    if end is not None:
        if executor_id == end:
            return f"executor {executor_id}"
        return f"executor {executor_id} thru {end}"

    # Single selection
    return f"executor {executor_id}"
