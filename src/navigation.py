"""
grandMA2 Console Navigation Module

High-level async API for navigating the MA2 console's object tree via telnet.
Combines three layers:

1. Command builder (src/commands/functions/navigation.py) — generates cd strings
2. Telnet client (src/telnet_client.py) — sends commands, captures raw response
3. Prompt parser (src/prompt_parser.py) — extracts prompt state from raw output

Workflow for discovering console state:
  1. ``cd [object-type].[object-id]``  — navigate into an object
  2. ``list``                           — enumerate children at current destination
  3. Parse the list feedback to identify object-type, object-id, and element names

This module is the I/O boundary for navigation operations.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from src.commands import assign_property as _build_assign_property
from src.commands import changedest, list_objects
from src.prompt_parser import (
    ConsolePrompt,
    ListOutput,
    parse_list_output,
    parse_prompt,
)
from src.telnet_client import GMA2TelnetClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NavigationResult:
    """Result of a navigation operation.

    Attributes:
        command_sent: The MA command string that was sent (e.g. ``"cd Group.1"``).
        raw_response: The complete raw telnet response.
        parsed_prompt: Parsed prompt state from the response.
        success: ``True`` if a prompt was detected, ``None`` if indeterminate.
    """

    command_sent: str
    raw_response: str
    parsed_prompt: ConsolePrompt
    success: bool | None = None


@dataclass(frozen=True)
class ListDestinationResult:
    """Result of listing objects at the current console destination.

    Attributes:
        command_sent: The ``list`` command that was sent.
        raw_response: The complete raw telnet response.
        parsed_list: Parsed list output with extracted entries.
    """

    command_sent: str
    raw_response: str
    parsed_list: ListOutput


async def navigate(
    client: GMA2TelnetClient,
    destination: str,
    object_id: int | str | None = None,
    *,
    timeout: float = 2.0,
    delay: float = 0.3,
) -> NavigationResult:
    """Send a cd command and parse the resulting prompt.

    Args:
        client: Connected GMA2TelnetClient instance.
        destination: Navigation target (see :func:`changedest` for formats).
        object_id: Object ID when destination is an object type.
            Uses dot notation: ``cd Group.1``.
        timeout: Maximum time to wait for telnet response.
        delay: Initial delay after sending command.

    Returns:
        NavigationResult with command sent, raw response, and parsed prompt.
    """
    cmd = changedest(destination, object_id)
    logger.info("Navigating: %s", cmd)

    raw_response = await client.send_command_with_response(
        cmd, timeout=timeout, delay=delay
    )
    logger.debug(
        "Navigation raw response (%d chars): %r", len(raw_response), raw_response
    )

    parsed = parse_prompt(raw_response)

    success: bool | None = None
    if parsed.prompt_line is not None:
        success = True

    result = NavigationResult(
        command_sent=cmd,
        raw_response=raw_response,
        parsed_prompt=parsed,
        success=success,
    )
    logger.info(
        "Navigation result: success=%s, location=%s", result.success, parsed.location
    )
    return result


async def get_current_location(
    client: GMA2TelnetClient,
    *,
    timeout: float = 2.0,
    delay: float = 0.3,
) -> NavigationResult:
    """Query the current console location without navigating.

    Sends an empty line to prompt the console to re-display its prompt.

    Args:
        client: Connected GMA2TelnetClient instance.
        timeout: Maximum time to wait for telnet response.
        delay: Initial delay after sending command.

    Returns:
        NavigationResult with the current parsed prompt state.
    """
    cmd = ""
    logger.info("Querying current console location (empty command)")

    raw_response = await client.send_command_with_response(
        cmd, timeout=timeout, delay=delay
    )
    logger.debug(
        "Location query raw response (%d chars): %r", len(raw_response), raw_response
    )

    parsed = parse_prompt(raw_response)

    success: bool | None = True if parsed.prompt_line is not None else None

    return NavigationResult(
        command_sent=cmd,
        raw_response=raw_response,
        parsed_prompt=parsed,
        success=success,
    )


async def list_destination(
    client: GMA2TelnetClient,
    object_type: str | None = None,
    *,
    timeout: float = 2.0,
    delay: float = 0.3,
) -> ListDestinationResult:
    """Run ``list`` at the current destination and parse the feedback.

    After ``cd``-ing into a location, this function sends ``list`` (or
    ``list [object-type]``) and parses the tabular feedback to extract
    object-type, object-id, and element name for each entry.

    Args:
        client: Connected GMA2TelnetClient instance.
        object_type: Optional object type filter (e.g. ``"cue"``, ``"group"``).
            If ``None``, lists everything at the current destination.
        timeout: Maximum time to wait for telnet response.
        delay: Initial delay after sending command.

    Returns:
        ListDestinationResult with command sent, raw response, and parsed entries.
    """
    cmd = list_objects(object_type)
    logger.info("Listing destination: %s", cmd)

    raw_response = await client.send_command_with_response(
        cmd, timeout=timeout, delay=delay
    )
    logger.debug(
        "List destination raw response (%d chars): %r",
        len(raw_response),
        raw_response,
    )

    parsed = parse_list_output(raw_response)

    logger.info(
        "List destination result: %d entries parsed", len(parsed.entries)
    )
    return ListDestinationResult(
        command_sent=cmd,
        raw_response=raw_response,
        parsed_list=parsed,
    )


@dataclass(frozen=True)
class SetPropertyResult:
    """Result of setting a property on a node in the object tree.

    Attributes:
        path: The dot-separated index path that was targeted.
        commands_sent: All MA commands that were sent (cd, assign, list, cd /).
        raw_responses: Raw telnet responses for each command.
        success: ``True`` if the assign command was sent and root was restored.
        verified_value: The property value read back after setting (if verify was True).
        error: Error message if something went wrong, ``None`` otherwise.
    """

    path: str
    commands_sent: list
    raw_responses: list
    success: bool
    verified_value: str | None = None
    error: str | None = None


async def set_property(
    client: GMA2TelnetClient,
    path: str,
    property_name: str,
    value: str,
    *,
    verify: bool = True,
    timeout: float = 2.0,
    delay: float = 0.3,
) -> SetPropertyResult:
    """Navigate to a node by path, set a property, and return to root.

    Uses the MA2 inline property assignment syntax::

        cd [parent]
        assign [child_index]/property=value
        cd /

    The *path* is a dot-separated string of numeric indexes matching the
    scan tree output (e.g. ``"3.1"`` for Settings/Global).  The last
    segment is the target child index; all preceding segments are
    navigated via ``cd``.

    Args:
        client: Connected GMA2TelnetClient instance.
        path: Dot-separated index path (e.g. ``"3.1"``, ``"4.1"``).
        property_name: Property to set (e.g. ``"Telnet"``, ``"OutActive"``).
        value: New value for the property.
        verify: If ``True``, re-lists after setting and checks the value.
        timeout: Per-command telnet timeout.
        delay: Per-command delay after sending.

    Returns:
        SetPropertyResult with commands sent, verification, and status.
    """
    commands_sent: list[str] = []
    raw_responses: list[str] = []

    segments = path.split(".")
    if not all(s.strip() for s in segments):
        return SetPropertyResult(
            path=path,
            commands_sent=[],
            raw_responses=[],
            success=False,
            error=f"Invalid path: {path!r} — segments must be non-empty numeric indexes",
        )

    parent_segments = segments[:-1]
    target_index = segments[-1]

    # 1. Navigate to root for clean state
    nav = await navigate(client, "/", timeout=timeout, delay=delay)
    commands_sent.append(nav.command_sent)
    raw_responses.append(nav.raw_response)

    # 2. Navigate through parent segments
    for seg in parent_segments:
        nav = await navigate(client, seg, timeout=timeout, delay=delay)
        commands_sent.append(nav.command_sent)
        raw_responses.append(nav.raw_response)

    # 3. Send the assign command
    assign_cmd = _build_assign_property(target_index, property_name, value)
    logger.info("Setting property: %s", assign_cmd)
    assign_response = await client.send_command_with_response(
        assign_cmd, timeout=timeout, delay=delay
    )
    commands_sent.append(assign_cmd)
    raw_responses.append(assign_response)

    # 4. Optionally verify by re-listing
    verified_value: str | None = None
    if verify:
        lst = await list_destination(client, timeout=timeout, delay=delay)
        commands_sent.append(lst.command_sent)
        raw_responses.append(lst.raw_response)

        # Find the target entry and check its columns
        for entry in lst.parsed_list.entries:
            if entry.object_id == target_index:
                if entry.columns and property_name in entry.columns:
                    verified_value = entry.columns[property_name]
                break

    # 5. Return to root
    nav = await navigate(client, "/", timeout=timeout, delay=delay)
    commands_sent.append(nav.command_sent)
    raw_responses.append(nav.raw_response)

    return SetPropertyResult(
        path=path,
        commands_sent=commands_sent,
        raw_responses=raw_responses,
        success=True,
        verified_value=verified_value,
    )


@dataclass(frozen=True)
class IndexScanEntry:
    """One result from a sequential index scan.

    Attributes:
        index: The numeric index that was cd'd into.
        location: Parsed location string from the prompt (e.g. ``"Groups/Global"``).
        object_type: Parsed object type, or ``None``.
        entries: Parsed list entries at this index.
    """

    index: int
    location: str | None
    object_type: str | None
    entries: tuple


async def scan_indexes(
    client: GMA2TelnetClient,
    *,
    reset_to: str = "/",
    max_index: int = 50,
    stop_after_failures: int = 3,
    timeout: float = 2.0,
    delay: float = 0.3,
) -> list[IndexScanEntry]:
    """Scan numeric indexes via cd N → list → cd <reset_to>.

    For each index N from 1 to *max_index*:
      1. ``cd N``           — navigate into that index
      2. ``list``           — enumerate children there
      3. ``cd <reset_to>``  — return to the base location for a clean slate

    The *reset_to* destination controls where each ``cd N`` starts from:

    * ``"/"`` (default) — all scans start from root.  Use this to scan the
      top-level object tree (Showfile, TimeConfig, Settings, …).
    * ``"Sequence"`` — reset to the Sequence pool after each iteration so
      that ``cd N`` enters Sequence N each time (lists its cues).
    * ``"Group"`` — reset to the Group pool (groups have no sub-objects so
      ``list`` will be empty, but the navigation result is still captured).

    Stops early after *stop_after_failures* consecutive indexes that produce
    no parsed entries (indicating the index is empty or invalid).

    Args:
        client: Connected GMA2TelnetClient instance.
        reset_to: Destination to navigate to after each ``list`` before the
            next ``cd N``.  Defaults to ``"/"`` (root).
        max_index: Highest index to try (inclusive).
        stop_after_failures: Stop scanning after this many consecutive
            indexes with no list entries.
        timeout: Per-command telnet timeout.
        delay: Per-command delay after sending.

    Returns:
        List of :class:`IndexScanEntry`, one per index that returned entries.
    """
    results: list[IndexScanEntry] = []
    consecutive_empty = 0

    # Navigate to reset destination and record its location as the base
    base_nav = await navigate(client, reset_to, timeout=timeout, delay=delay)
    base_location = base_nav.parsed_prompt.location
    logger.info("scan_indexes: base location = %r", base_location)

    for idx in range(1, max_index + 1):
        # cd N
        nav = await navigate(client, str(idx), timeout=timeout, delay=delay)
        after_location = nav.parsed_prompt.location
        logger.info("scan_indexes: cd %d → location=%s", idx, after_location)

        # If location didn't change, navigation failed (index doesn't exist)
        if after_location == base_location:
            logger.info(
                "scan_indexes: index %d navigation failed (stayed at base), skipping list",
                idx,
            )
            # Reset and count as empty
            await navigate(client, reset_to, timeout=timeout, delay=delay)
            consecutive_empty += 1
            if consecutive_empty >= stop_after_failures:
                logger.info(
                    "scan_indexes: stopping after %d consecutive failures",
                    stop_after_failures,
                )
                break
            continue

        # list
        lst = await list_destination(client, timeout=timeout, delay=delay)
        entries = lst.parsed_list.entries if lst.parsed_list else ()

        # Supplement: detect rows the tabular parser misses (PresetType/Feature/
        # Attribute/SubAttribute listings that have only one numeric ID column).
        if not entries and lst.raw_response:
            _TREE_ROW = re.compile(
                r"^\s*(PresetType|Feature|Attribute|SubAttribute)\s+\d+",
                re.IGNORECASE | re.MULTILINE,
            )
            if _TREE_ROW.search(lst.raw_response):
                # Node has children — count them as a synthetic non-empty result
                matches = _TREE_ROW.findall(lst.raw_response)
                logger.info(
                    "scan_indexes: index %d has %d tree-row children (preset-tree format)",
                    idx, len(matches),
                )
                entries = (None,) * len(matches)  # type: ignore[assignment]

        # Reset to base location
        await navigate(client, reset_to, timeout=timeout, delay=delay)

        if entries:
            consecutive_empty = 0
            results.append(IndexScanEntry(
                index=idx,
                location=after_location,
                object_type=nav.parsed_prompt.object_type,
                entries=entries,
            ))
        else:
            consecutive_empty += 1
            logger.info(
                "scan_indexes: index %d produced no entries (%d consecutive)",
                idx, consecutive_empty,
            )
            if consecutive_empty >= stop_after_failures:
                logger.info(
                    "scan_indexes: stopping after %d consecutive empty indexes",
                    stop_after_failures,
                )
                break

    logger.info("scan_indexes: done — %d indexes with entries", len(results))
    return results
