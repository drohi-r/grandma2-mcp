"""
Attribute and Feature Object Keywords for grandMA2 Command Builder

This module contains Attribute and Feature object keywords.

Attribute:
- Object type used as reference to fixture attributes
- Can be called by name (string) or number
- Organized by Features, which are organized by PresetType
- Shortcut: Att

Feature:
- Container for related attributes
- Can use dot notation to access specific attribute
- Organized under PresetType

Included functions:
- attribute: Reference fixture attributes by name or number
- feature: Reference feature groups with optional attribute
"""



def attribute(attr_id: int | str) -> str:
    """
    Construct an Attribute command to reference fixture attributes.

    Attribute is an object type used as reference to fixture attributes.
    The default function is Call - calling attributes will bring them to
    the encoder and select them in the fixture sheet (blue column header).

    Note: Press Preset twice on the console to enter Attribute keyword.
    Note: Attribute numbers may change when fixtures are added.
          Use unique attribute library names in macros for stability.
    Tip: Type "List Attribute" to see all attributes with names and numbers.

    Args:
        attr_id: Attribute name (string) or number (integer).
                 String names are automatically quoted.

    Returns:
        str: MA command to reference the attribute

    Examples:
        >>> attribute("pan")
        'attribute "pan"'
        >>> attribute("tilt")
        'attribute "tilt"'
        >>> attribute(1)
        'attribute 1'
        >>> attribute(5)
        'attribute 5'
    """
    if isinstance(attr_id, str):
        return f'attribute "{attr_id}"'
    return f"attribute {attr_id}"


def feature(
    feature_id: int | str,
    attr_num: int | None = None,
) -> str:
    """
    Construct a Feature command to reference feature groups.

    Feature is a container for related attributes. Attributes are
    organized by Features, which in turn are organized by PresetType.
    You can use dot notation to access specific attributes within a feature.

    Note: Feature numbers may change when fixtures are added.
          Use unique feature names in macros for stability.
    Tip: Type "List Feature" to see all features with names and numbers.

    Args:
        feature_id: Feature number (int), name (str), or variable (str starting with $).
                    String names are automatically quoted unless they start with $.
        attr_num: Optional attribute number within the feature.
                  If provided, uses dot notation (e.g., "feature 3.1")

    Returns:
        str: MA command to reference the feature (with optional attribute)

    Examples:
        >>> feature(3)
        'feature 3'
        >>> feature("Gobo1")
        'feature "Gobo1"'
        >>> feature(3, 1)
        'feature 3.1'
        >>> feature("Position", 2)
        'feature "Position".2'
        >>> feature("$feature", 1)
        'feature $feature.1'
    """
    # Determine if feature_id needs quoting
    # - Integers: no quotes
    # - Variables (starting with $): no quotes
    # - Names (other strings): add quotes
    if isinstance(feature_id, int):
        feature_ref = str(feature_id)
    elif isinstance(feature_id, str) and feature_id.startswith("$"):
        # Variable reference - no quotes
        feature_ref = feature_id
    else:
        # Name reference - add quotes
        feature_ref = f'"{feature_id}"'

    if attr_num is not None:
        return f"feature {feature_ref}.{attr_num}"
    return f"feature {feature_ref}"
