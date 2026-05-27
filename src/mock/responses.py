"""Tier-1 canned responses keyed by command regex."""

from __future__ import annotations

import re
from typing import Callable

# Regex -> response (string OR callable that takes the raw command).
_RESPONSES: list[tuple[re.Pattern, str | Callable[[str], str]]] = [
    (
        re.compile(r"^\s*ListVar\b", re.IGNORECASE),
        "Executing : ListVar\n"
        "Global : $VERSION = 3.9.60 (mock)\n"
        "Global : $SHOWFILE = mock_show\n"
        "Global : $USER = administrator\n"
        "Global : $USERRIGHTS = Admin\n",
    ),
    (
        re.compile(r"^\s*list\s+group\b", re.IGNORECASE),
        "Group\n"
        "    1 : Wash\n"
        "    2 : Mover\n"
        "    3 : Bar\n"
        "    4 : Blinder\n",
    ),
    (
        re.compile(r"^\s*list\s+executor\b", re.IGNORECASE),
        "Executor\n"
        "  1.1.1 : Wash Intensity (Normal)\n"
        "  1.1.2 : Mover Intensity (Normal)\n",
    ),
    (
        re.compile(r"^\s*list\s+preset\b", re.IGNORECASE),
        "Preset\n"
        "    4.1 : Red\n"
        "    4.2 : Green\n"
        "    4.3 : Blue\n"
        "    4.4 : White\n",
    ),
    (
        re.compile(r"^\s*list\s+sequence\b", re.IGNORECASE),
        "Sequence\n"
        "    1 : Main\n",
    ),
    (
        re.compile(r"^\s*info\b", re.IGNORECASE),
        "Info: mock console; tier=1\n",
    ),
    (re.compile(r"^\s*cd\b", re.IGNORECASE), ""),  # cd is silent
    (re.compile(r"^\s*Echo\b", re.IGNORECASE), ""),
]


def respond(command: str) -> str:
    """Return the canned response for ``command``, or a not-stubbed marker."""
    for pat, body in _RESPONSES:
        if pat.match(command):
            return body if isinstance(body, str) else body(command)
    return f"MOCK: command not stubbed; got {command!r}\n"


__all__ = ["respond"]
