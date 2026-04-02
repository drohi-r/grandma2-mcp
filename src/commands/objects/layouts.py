"""
Layout/View Object Keywords for grandMA2 Command Builder

Contains Object Keywords related to Layouts and Views:
- layout: Select layouts

Layout is an object type that represents the layout of fixtures and other objects.
"""



def layout(
    layout_id: int | list[int] | None = None,
    end: int | None = None,
) -> str:
    """
    Construct a Layout command to select layouts.

    Layout is an object type that represents the layout of fixtures and other objects.
    The default function for Layout is Select, meaning calling a Layout will select it
    and display it in any Layout View with Link Selected enabled.

    Args:
        layout_id: Layout number or list of layout numbers
        end: End layout number (for range selection)

    Returns:
        str: MA command string

    Examples:
        >>> layout(3)
        'layout 3'
        >>> layout(1, end=5)
        'layout 1 thru 5'
        >>> layout([1, 3, 5])
        'layout 1 + 3 + 5'
    """
    if layout_id is None:
        raise ValueError("Must provide layout_id")

    # Handle list selection (using + separator)
    if isinstance(layout_id, list):
        if len(layout_id) == 1:
            return f"layout {layout_id[0]}"
        layouts_str = " + ".join(str(lid) for lid in layout_id)
        return f"layout {layouts_str}"

    # Handle range selection (using thru)
    if end is not None:
        if layout_id == end:
            return f"layout {layout_id}"
        return f"layout {layout_id} thru {end}"

    # Single selection
    return f"layout {layout_id}"
