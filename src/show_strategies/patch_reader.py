"""Live patch summarizer — issues SAFE_READ commands and returns a typed dict.

This is the ONLY module in ``src/show_strategies/`` that touches the Telnet
client. ``plan_builder.py`` is pure and operates on the summary returned here.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from src.show_strategies.types import PatchSummary

if TYPE_CHECKING:
    from src.telnet_client import GMA2TelnetClient


# MA2 telnet emits ANSI colour codes and `\n\r` line endings (note the
# reverse order — MA2 emits LF then CR). Strip ANSI and normalise line
# endings before regex parsing so MULTILINE `^` anchors fire correctly.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    text = _ANSI_RE.sub("", text)
    text = text.replace("\n\r", "\n").replace("\r\n", "\n").replace("\r", "\n")
    return text


# MA2 `list fixture` rows look like:
#   Fixture   1 HY B-EYE K25 1   1      1      32 Zoom Wash 1240 18 Channel   1.001  No  ...
# Columns: Fixture <page> <name with spaces>  <fixid>  <chaid>  <type with spaces>  <patch>
# Boundaries between columns are 3+ whitespace (the alignment padding); the
# name and type columns themselves may contain single spaces.
_FIXTURE_ROW_RE = re.compile(
    r"^Fixture\s+\d+\s+(?P<name>\S.+?)\s{2,}"
    r"(?P<id>\d+)\s+\d+\s+(?P<type>\S.+?)\s{2,}"
    r"(?P<patch>\d+\.\d{3})",
    re.MULTILINE,
)

# `list fixturetype` rows:
#   FixtureType  1 1    Universal Attributes  Universal Attributes  AutoMA  AutoMA  ...
_FT_ROW_RE = re.compile(
    r"^FixtureType\s+\d+\s+(?P<id>\d+)\s+(?P<long_name>\S.+?)\s{2,}"
    r"(?P<short_name>\S.+?)\s{2,}(?P<manuf>\S+)",
    re.MULTILINE,
)

# `list group` rows:
#   Group 1 1    Blinder
#   Group 1 2    Wash
_GROUP_ROW_RE = re.compile(
    r"^Group\s+\d+\s+(?P<id>\d+)\s+(?P<name>\S.*?)\s*$",
    re.MULTILINE,
)

_SHOWFILE_RE = re.compile(r"\$SHOWFILE\s*=\s*(?P<sf>\S.+?)\s*$", re.MULTILINE)


async def summarize_patch(client: "GMA2TelnetClient") -> PatchSummary:
    """Read the current patch state via SAFE_READ commands.

    Returns a typed :class:`PatchSummary`. All counts are derived from the
    raw `list ...` responses; the returned shape is deterministic for a
    given live state, which makes it suitable to commit as a test fixture.
    """
    showfile_resp = _strip_ansi(
        await client.send_command_with_response("ListVar", timeout=2.0)
    )
    sf_match = _SHOWFILE_RE.search(showfile_resp)
    showfile = sf_match.group("sf") if sf_match else "unknown"

    fix_resp = _strip_ansi(
        await client.send_command_with_response("list fixture", timeout=3.0)
    )
    fixtures = [
        {
            "id": int(m.group("id")),
            "name": m.group("name").strip(),
            "type": m.group("type").strip(),
            "patch": m.group("patch"),
        }
        for m in _FIXTURE_ROW_RE.finditer(fix_resp)
    ]

    ft_resp = _strip_ansi(
        await client.send_command_with_response("list fixturetype", timeout=2.0)
    )
    fixture_types = [
        {
            "id": int(m.group("id")),
            "long_name": m.group("long_name").strip(),
            "short_name": m.group("short_name").strip(),
            "manufacturer": m.group("manuf"),
        }
        for m in _FT_ROW_RE.finditer(ft_resp)
    ]

    grp_resp = _strip_ansi(
        await client.send_command_with_response("list group", timeout=2.0)
    )
    groups = [
        {"id": int(m.group("id")), "name": m.group("name").strip()}
        for m in _GROUP_ROW_RE.finditer(grp_resp)
    ]

    seq_resp = await client.send_command_with_response("list sequence", timeout=2.0)
    sequences_count = max(0, len([
        ln for ln in seq_resp.splitlines() if ln.strip()
    ]) - 2)

    mac_resp = await client.send_command_with_response("list macro", timeout=2.0)
    macros_count = max(0, len([
        ln for ln in mac_resp.splitlines() if ln.strip()
    ]) - 2)

    return PatchSummary(
        showfile=showfile,
        fixture_count=len(fixtures),
        fixtures=fixtures,
        fixture_types=fixture_types,
        groups=groups,
        sequences_count=sequences_count,
        macros_count=macros_count,
    )


__all__ = ["summarize_patch"]
