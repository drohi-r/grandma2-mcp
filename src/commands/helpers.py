"""
Internal Helper Functions for grandMA2 Command Builder

This module contains internal helper functions used by the command builder.
These functions are not intended for external use.
"""

import logging
from typing import Any

from .constants import STORE_BOOL_OPTIONS, STORE_FLAG_OPTIONS, STORE_VALUE_OPTIONS

logger = logging.getLogger(__name__)

# Characters that have special meaning in the MA2 command line (manual: key_cs_special_characters)
MA2_SPECIAL_CHARS: frozenset[str] = frozenset('*@$./;[]() "')


def quote_name(name: str, match_mode: str = "literal") -> str:
    """
    Quote an object name per the MA2 wildcard specification.

    Implements all three deterministic builder rules from the MA2 special-characters spec:

    - Rule A (literal intent): Quote any name that contains special characters
      so they are treated literally by the console.
    - Rule B (wildcard intent): Pass the name raw (unquoted) so '*' is interpreted
      as a wildcard operator by the console.
    - Rule C (safe default): Default is literal — autonomous agents must explicitly
      opt in to wildcard mode to avoid unexpected multi-object expansion.

    Args:
        name: Object name or wildcard pattern.
        match_mode: "literal" (default) or "wildcard".

    Returns:
        str: Properly quoted or raw name ready to embed in a command string.

    Examples:
        >>> quote_name("AllFixtures")
        'AllFixtures'
        >>> quote_name("Front*Wash")
        '"Front*Wash"'
        >>> quote_name("Go.Live")
        '"Go.Live"'
        >>> quote_name("Intro/Outro")
        '"Intro/Outro"'
        >>> quote_name("Mac*", match_mode="wildcard")
        'Mac*'
        >>> quote_name("*Wash*", match_mode="wildcard")
        '*Wash*'
    """
    if match_mode == "wildcard":
        return name  # Rule B — emit raw; * is wildcard operator
    # Rule A + C — quote if the name contains any MA2 special character
    if any(c in MA2_SPECIAL_CHARS for c in name):
        return f'"{name}"'
    return name  # No special chars — quotes may be safely omitted per manual


def _build_store_options(**kwargs: Any) -> str:
    """
    Build option string for store commands.

    Handles three types of options:
    1. Flag options (no value): /merge, /overwrite, /noconfirm
    2. Boolean options: /cueonly=true, /tracking=false
    3. Value options: /source=output, /screen=1

    Args:
        **kwargs: Option name-value pairs

    Returns:
        str: Formatted option string (e.g., " /merge /cueonly=true")
    """
    options_parts = []

    for key, value in kwargs.items():
        if value is None:
            continue

        # Normalize key (remove underscores, convert to lowercase)
        option_key = key.replace("_", "").lower()

        # Handle flag options (no value needed)
        if option_key in STORE_FLAG_OPTIONS:
            if value:  # Only add if True
                options_parts.append(f"/{option_key}")

        # Handle boolean options (need =true or =false)
        elif option_key in STORE_BOOL_OPTIONS:
            bool_value = "true" if value else "false"
            options_parts.append(f"/{option_key}={bool_value}")

        # Handle value options
        elif option_key in STORE_VALUE_OPTIONS:
            options_parts.append(f"/{option_key}={value}")

        else:
            logger.warning(
                f"Unknown store option '{key}' (normalized: '{option_key}') — "
                "this option will be ignored. Check for typos."
            )

    if options_parts:
        return " " + " ".join(options_parts)
    return ""

