"""
grandMA2 Telnet Prompt Parser

Parses raw telnet output to detect the grandMA2 command-line prompt and
extract the current navigation destination (object tree location).

The exact prompt format is discovered empirically by sending commands and
inspecting responses.  This module uses a flexible multi-pattern approach
so it can be refined as we learn the real format from live consoles.

Candidate prompt patterns (ordered by specificity):
  1. ``[something]>``  or ``[something]>/`` — bracket-delimited
  2. Lines ending with ``>`` after stripping whitespace
  3. Fallback: no prompt detected
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Strip ANSI/VT100 escape sequences (e.g. \x1b[32m, \x1b[K) from telnet output
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    """Remove ANSI/VT100 escape sequences from *text*."""
    return _ANSI_ESCAPE_RE.sub("", text)


@dataclass(frozen=True)
class ConsolePrompt:
    """Parsed console prompt state extracted from raw telnet output.

    Attributes:
        raw_response: The complete raw telnet output.
        prompt_line: The detected prompt line (e.g. ``[Group 1]>``), or
            ``None`` if no prompt pattern was matched.
        location: Extracted location text from inside the prompt brackets
            (e.g. ``"Group 1"``), or ``None``.
        object_type: Parsed object type if the location contains a
            recognizable ``Type ID`` pattern (e.g. ``"Group"``), or ``None``.
        object_id: Parsed object ID from the location (e.g. ``"1"``),
            or ``None``.
    """

    raw_response: str
    prompt_line: str | None = None
    location: str | None = None
    object_type: str | None = None
    object_id: str | None = None


# ---------------------------------------------------------------------------
# Prompt detection patterns (tried in order)
# ---------------------------------------------------------------------------

# Pattern 1: bracket-delimited prompt  [content]>  or  [content]>/
_BRACKET_PROMPT_RE = re.compile(r"\[(.+?)\]\s*>/?\s*$", re.MULTILINE)

# Pattern 2: line ending with >
_ANGLE_PROMPT_RE = re.compile(r"^(.+)>\s*$", re.MULTILINE)

# ---------------------------------------------------------------------------
# Location splitting: "Group 1" or "Group.1" -> object_type="Group", object_id="1"
# ---------------------------------------------------------------------------

# Space-separated: "Group 1", "Preset 4.1"
_LOCATION_SPLIT_SPACE_RE = re.compile(r"^([A-Za-z]+)\s+(\d+(?:\.\d+)?)$")
# Dot-separated: "Group.1", "Preset.4.1"  (MA2 object reference notation)
_LOCATION_SPLIT_DOT_RE = re.compile(r"^([A-Za-z]+)\.(\d+(?:\.\d+)?)$")
# Single word: "Fixture", "Root", "channel"
_LOCATION_SINGLE_RE = re.compile(r"^[A-Za-z]\w*$")


def _split_location(location: str) -> tuple[str | None, str | None]:
    """Attempt to split a location string into object_type and object_id.

    Recognises both space-separated (``"Group 1"``) and dot-separated
    (``"Group.1"``) forms, single-word locations (``"Fixture"``), and
    returns ``(None, None)`` for anything else.
    """
    if not location:
        return None, None

    # "Group 1", "Preset 4.1"
    m = _LOCATION_SPLIT_SPACE_RE.match(location)
    if m:
        return m.group(1), m.group(2)

    # "Group.1", "Preset.4.1"
    m = _LOCATION_SPLIT_DOT_RE.match(location)
    if m:
        return m.group(1), m.group(2)

    # "Fixture", "Root", "channel"
    if _LOCATION_SINGLE_RE.match(location):
        return location, None

    return None, None


def parse_prompt(raw: str) -> ConsolePrompt:
    """Parse raw telnet output and attempt to detect the MA2 prompt.

    Tries multiple candidate patterns against the raw output.  Returns a
    :class:`ConsolePrompt` with as much information as could be extracted.
    If no prompt pattern matches, ``prompt_line`` and derived fields will
    be ``None`` — the ``raw_response`` is always preserved so callers can
    inspect the output manually.

    Args:
        raw: Raw telnet output string.

    Returns:
        Parsed :class:`ConsolePrompt`.
    """
    if not raw:
        return ConsolePrompt(raw_response=raw)

    raw = _strip_ansi(raw)

    # Try pattern 1: bracket-delimited [content]>
    matches = list(_BRACKET_PROMPT_RE.finditer(raw))
    if matches:
        # Use the last match (prompt is typically at the end of output)
        last = matches[-1]
        prompt_line = last.group(0).strip()
        location = last.group(1).strip()
        obj_type, obj_id = _split_location(location)
        return ConsolePrompt(
            raw_response=raw,
            prompt_line=prompt_line,
            location=location,
            object_type=obj_type,
            object_id=obj_id,
        )

    # Try pattern 2: line ending with >
    matches = list(_ANGLE_PROMPT_RE.finditer(raw))
    if matches:
        last = matches[-1]
        prompt_line = last.group(0).strip()
        content = last.group(1).strip()
        # The content before > might contain location info
        obj_type, obj_id = _split_location(content)
        return ConsolePrompt(
            raw_response=raw,
            prompt_line=prompt_line,
            location=content if content else None,
            object_type=obj_type,
            object_id=obj_id,
        )

    # No prompt detected — return raw only
    return ConsolePrompt(raw_response=raw)


# ---------------------------------------------------------------------------
# List output parsing: extract object entries from MA2 "list" feedback
# ---------------------------------------------------------------------------


@dataclass
class ListEntry:
    """Single object entry parsed from MA2 list output.

    Attributes:
        object_type: Object type (e.g. ``"Group"``, ``"Sequence"``), or ``None``.
        object_id: Object ID (e.g. ``"1"``, ``"4.1"``), or ``None``.
            For tabular entries this is col2 (pool slot).
        name: Element name / label (e.g. ``"Front Wash"``), or ``None``.
        raw_line: The original line from the list output.
        col3: Third column from tabular format (e.g. ``"1"``, ``"3.7.0.5"``).
            May differ from object_id for SubForm entries where both cols
            carry the parent's form number and the real cd index is the
            entry's ordinal position (1, 2, 3…).
        columns: Mapping of column header names to their values for this
            entry, parsed from the tabular output.  For tabular entries
            these are the extra columns after ``name``; for root entries
            these are parsed ``key=value`` properties.
    """

    object_type: str | None = None
    object_id: str | None = None
    name: str | None = None
    raw_line: str | None = None
    col3: str | None = None
    columns: dict[str, str] | None = None


@dataclass(frozen=True)
class ListOutput:
    """Parsed result of an MA2 ``list`` command.

    Attributes:
        raw_response: Complete raw telnet output.
        entries: Extracted list entries.
        prompt: Trailing prompt parsed from the output (if present).
        column_headers: Detected column header names from the header row,
            if one was found before the data lines.
    """

    raw_response: str
    entries: tuple[ListEntry, ...]
    prompt: ConsolePrompt | None = None
    column_headers: tuple[str, ...] = ()


# Patterns for extracting entries from list output lines:
#
# Live-console validated formats (grandMA2 v3.9 telnet):
#
#   1.  Tabular (pool listing):  "Group   1 1    ALL LASERS"
#                                "Sequ   1 1    ALL WHITE   On  ..."
#                                "History  1 3.7.0.5    No    Mar 16 2022  newshow"
#                                "SubForm  2  2    Release  192 192 192   (1)"
#       Columns: TypeAbbr  col2  col3  Name  [extra columns...]
#       NOTE: col2 and col3 may both be the parent's pool_slot (SubForm case).
#       The cd index is determined by the scanner, not assumed here.
#
#   1b. Root/container listing:  "Showfile              1  Date=Feb 25 2026 Info= (37)"
#                                "Settings              3  (6)"
#                                "EditSetup            11"
#                                "Art-Net  1  OutActive=Off InActive=Off ..."
#                                "ETC Net2 2  Active=Off ..."
#                                "Modules             1  (1)"
#       Columns: Name  ID  [key=value properties or (count)]
#       Name may contain hyphens, digits, and spaces.
#
#   2.  Dot notation:  "Group.1  Front Wash"   (legacy / manual testing)
#   3.  Bare ID:       "1  Front Wash"         (when inside a typed pool)
#   4.  Quoted name:   '1  "Front Wash"'

# Pattern 1: tabular pool listing  "Group   1 1    Name  [extra...]"
# Also handles version-style third field: "History  1 3.7.0.5    No ..."
# Captures: (type_abbr, col2, col3, rest_of_line)
_LIST_TABULAR_RE = re.compile(
    r"^\s*([A-Za-z]\w*)\s+(\d+)\s+(\d+(?:\.\d+)*)\s{2,}(.+?)\s*$"
)

# Pattern 1b: root/container listing  "Showfile  1  Date=..." or "Settings  3  (6)"
# The "Name" part can contain hyphens, digits, spaces (e.g. "Art-Net", "ETC Net2").
# Uses lazy (.+?) so the regex engine finds the first \d+ that allows the rest
# (optional 2+ spaces + properties, then end of line) to match.
# Widget lines are filtered out before reaching this regex.
_LIST_ROOT_RE = re.compile(
    r"^\s*(.+?)\s+(\d+)(?:\s{2,}(.+?))?\s*$"
)

# Pattern 2: Type.ID with optional name (e.g. "Group.1  Front Wash")
_LIST_DOT_RE = re.compile(
    r"^\s*([A-Za-z]\w*)\.(\d+(?:\.\d+)?)"
    r"(?:\s+(.+?))?\s*$"
)

# Pattern 3: bare numeric ID with optional name (e.g. "1  Front Wash")
_LIST_ID_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)"
    r"(?:\s+(.+?))?\s*$"
)


_SKIP_PREFIXES = ("Executing :", "Error :", "Error #", "WARNING,", "Widget ")


def _is_skip_line(stripped: str) -> bool:
    """Return True if *stripped* should be skipped entirely."""
    return stripped.startswith(_SKIP_PREFIXES)


def _is_prompt_line(stripped: str) -> bool:
    """Return True if *stripped* looks like a console prompt."""
    if _BRACKET_PROMPT_RE.search(stripped):
        return True
    return bool(_ANGLE_PROMPT_RE.search(stripped) and ">Executing" not in stripped)


def _is_data_line(stripped: str) -> bool:
    """Return True if *stripped* matches any data-line pattern."""
    if _LIST_TABULAR_RE.match(stripped):
        return True
    if _LIST_ROOT_RE.match(stripped):
        return True
    if _LIST_DOT_RE.match(stripped):
        return True
    return bool(_LIST_ID_RE.match(stripped))


def _detect_header(lines: list[str]) -> list[str]:
    """Detect column header line from list output.

    Scans *lines* for the first non-skippable, non-prompt, non-data line
    that appears before any data line.  Splits it on 2+ spaces to extract
    column names.

    Returns:
        List of column name strings, or empty list if no header detected.
    """
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _is_skip_line(stripped):
            continue
        if _is_prompt_line(stripped):
            continue
        if _is_data_line(stripped):
            # Hit a data line before finding a header — no header row
            return []
        # This is a non-data, non-skip, non-prompt line before any data.
        # Treat it as a header if it contains at least 2 space-separated words.
        parts = re.split(r"\s{2,}", stripped)
        if len(parts) >= 2:
            return [p.strip() for p in parts if p.strip()]
        # Single-word non-data line — not a useful header, keep scanning
    return []


def _parse_root_properties(props: str) -> dict[str, str]:
    """Parse ``key=value`` properties and ``(N)`` child count from root entries.

    Handles multi-word values like ``Date=Feb 25 2026`` by consuming
    everything up to the next ``Key=`` boundary or end of string.
    """
    columns: dict[str, str] = {}
    if not props:
        return columns
    # Match key=value where value extends to the next key= or (N) or end
    for kv_match in re.finditer(r"(\w+)=(.*?)(?=\s+\w+=|\s*\(\d+\)\s*$|\s*$)", props):
        val = kv_match.group(2).strip()
        if val:
            columns[kv_match.group(1)] = val
    count_m = re.search(r"\((\d+)\)", props)
    if count_m:
        columns["child_count"] = count_m.group(1)
    return columns


def parse_list_output(raw: str) -> ListOutput:
    """Parse raw telnet output from a ``list`` command.

    Extracts object entries (type, id, name, extra columns) from each line
    of the list output.  Detects the column header row (if present) and maps
    extra column values to their header names.

    The parser is intentionally lenient — unrecognised lines are skipped,
    and the raw output is always preserved.

    Args:
        raw: Raw telnet output string from a ``list`` command.

    Returns:
        :class:`ListOutput` with extracted entries, column headers,
        and optional prompt.
    """
    if not raw or not raw.strip():
        return ListOutput(raw_response=raw, entries=())

    raw = _strip_ansi(raw)
    lines = raw.strip().splitlines()

    # --- Phase 1: detect column header row ---
    header_columns = _detect_header(lines)

    # --- Phase 2: parse data lines ---
    entries: list[ListEntry] = []
    prompt: ConsolePrompt | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip MA2 feedback prefixes, error lines, and widget config lines
        if _is_skip_line(stripped):
            continue

        # Skip lines that look like a prompt (don't treat as data)
        if _BRACKET_PROMPT_RE.search(stripped):
            prompt = parse_prompt(stripped)
            continue

        if _ANGLE_PROMPT_RE.search(stripped) and ">Executing" not in stripped:
            prompt = parse_prompt(stripped)
            continue

        # Try tabular pool listing: "Group   1 1    Name  [extra...]"
        m = _LIST_TABULAR_RE.match(stripped)
        if m:
            rest = m.group(4)
            # Split on 2+ spaces to get [name, extra1, extra2, ...]
            parts = re.split(r"\s{2,}", rest)
            name = parts[0].strip() if parts else None
            extra_values = [p.strip() for p in parts[1:]] if len(parts) > 1 else []

            # Map extra values to column headers
            columns: dict[str, str] | None = None
            if extra_values:
                columns = {}
                # header_columns[0] = col2/col3 header (e.g. "No.", "Version")
                # header_columns[1] = name header (e.g. "Name", "LongName")
                # header_columns[2:] = extra column headers
                extra_headers = header_columns[2:] if len(header_columns) > 2 else []
                for i, val in enumerate(extra_values):
                    if i < len(extra_headers):
                        columns[extra_headers[i]] = val
                    else:
                        columns[f"col{i + 5}"] = val

            entries.append(ListEntry(
                object_type=m.group(1),
                object_id=m.group(2),  # col2 (pool slot)
                name=name,
                raw_line=stripped,
                col3=m.group(3),       # col3 (No. or version)
                columns=columns,
            ))
            continue

        # Try root-level listing: "Showfile  1  Date=..." or "Settings  3  (6)"
        m = _LIST_ROOT_RE.match(stripped)
        if m:
            name = m.group(1)          # the type name IS the display name at root
            obj_id = m.group(2)        # the cd index
            props = m.group(3)
            root_cols = _parse_root_properties(props) if props else None
            entries.append(ListEntry(
                object_type=m.group(1),
                object_id=obj_id,
                name=name,
                raw_line=stripped,
                columns=root_cols if root_cols else None,
            ))
            continue

        # Try dot notation: Group.1  Front Wash
        m = _LIST_DOT_RE.match(stripped)
        if m:
            name_raw = m.group(3)
            name = name_raw.strip('"') if name_raw else None
            entries.append(ListEntry(
                object_type=m.group(1),
                object_id=m.group(2),
                name=name,
                raw_line=stripped,
            ))
            continue

        # Try bare ID: 1  Front Wash
        m = _LIST_ID_RE.match(stripped)
        if m:
            name_raw = m.group(2)
            name = name_raw.strip('"') if name_raw else None
            entries.append(ListEntry(
                object_type=None,
                object_id=m.group(1),
                name=name,
                raw_line=stripped,
            ))
            continue

        # Unrecognised line — skip silently (separator, etc.)

    return ListOutput(
        raw_response=raw,
        entries=tuple(entries),
        prompt=prompt,
        column_headers=tuple(header_columns),
    )


# ---------------------------------------------------------------------------
# Executor-specific parser (KEY=VALUE inline format)
# ---------------------------------------------------------------------------


def parse_executor_list(raw: str) -> dict[str, str]:
    """Parse all KEY=VALUE fields from a ``List Executor page.id`` response.

    MA2 executor list output is uniquely KEY=VALUE inline (not tabular columns).
    Output may span multiple lines due to terminal wrapping. Field keys can
    contain dots (e.g. ``No.``).

    Args:
        raw: Raw telnet output from ``list executor page.id``.

    Returns:
        dict mapping field names to string values.
        Empty dict if no KEY=VALUE pairs are found.

    Example input::

        Exec 1.203  No.=1.203 Name=Washes Color Sequence=Seq 202(9)
        Width=1 SwopProtect=off Priority=Normal ...

    Example output::

        {"No.": "1.203", "Name": "Washes Color", "Sequence": "Seq 202(9)",
         "Width": "1", "SwopProtect": "off", "Priority": "Normal", ...}
    """
    clean = _strip_ansi(raw)
    lines = []
    for line in clean.replace("\r", "\n").split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("Executing"):
            continue
        if _BRACKET_PROMPT_RE.search(s):
            continue
        if _ANGLE_PROMPT_RE.search(s) and ">Executing" not in s:
            continue
        lines.append(s)

    combined = " ".join(lines)

    # Extract KEY=VALUE pairs; key may contain dots (No.)
    # Value extends to the next KEY= boundary or end of string.
    fields: dict[str, str] = {}
    for m in re.finditer(
        r"([\w.]+)=(.*?)(?=\s+[\w.]+=|\s*$)",
        combined,
    ):
        key = m.group(1).strip()
        val = m.group(2).strip()
        if key and val:
            fields[key] = val

    return fields


# ---------------------------------------------------------------------------
# Tabular list convenience wrapper
# ---------------------------------------------------------------------------


def parse_tabular_list(raw: str) -> list[dict[str, str]]:
    """Parse tabular List output into a list of dicts keyed by column headers.

    Convenience wrapper over :func:`parse_list_output` for server tools that
    need a simple ``list[dict]`` rather than the full :class:`ListOutput`.

    Args:
        raw: Raw telnet output from any ``list <type>`` command.

    Returns:
        List of dicts, one per entry. Standard keys are ``No.`` and ``Name``
        (or the detected header names). Extra columns are included when
        column headers are detected. Falls back to positional keys
        (``col1``, ``col2``) when no headers are present.
    """
    out = parse_list_output(raw)
    headers = list(out.column_headers)

    result: list[dict[str, str]] = []
    for entry in out.entries:
        row: dict[str, str] = {}
        if entry.object_type:
            row["_type"] = entry.object_type
        id_key = headers[0] if headers else "No."
        name_key = headers[1] if len(headers) > 1 else "Name"
        if entry.object_id:
            row[id_key] = entry.object_id
        if entry.name:
            row[name_key] = entry.name
        if entry.columns:
            row.update(entry.columns)
        result.append(row)

    return result
