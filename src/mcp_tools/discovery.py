"""MCP tools — discovery. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501

import json

import src.server as _srv
from src.auth import OAuthScope, require_scope
from src.server import (
    _get_sequence_for_executor,
    _handle_errors,
    mcp,
)
from src.telnet_client import GMA2TelnetClient

# ============================================================
# Tools 55–56 — Fixture & Sequence/Cue Discovery (SAFE_READ)
# ============================================================


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_fixtures(
    fixture_id: int | None = None,
) -> str:
    """
    List fixtures defined on the console, or check a specific fixture exists.

    This is the correct way to discover fixture IDs before using park_fixture,
    unpark_fixture, set_intensity, or set_attribute. Note: 'cd Fixture' is NOT
    a valid MA2 navigation destination — this tool uses 'list fixture' instead.

    Args:
        fixture_id: Optional fixture ID to inspect. If None, lists all fixtures.

    Returns:
        str: JSON with command_sent, raw_response, exists (bool), fixture_id.
             exists is always True when fixture_id is None (listing all).

    Examples:
        - List all fixtures: list_fixtures()
        - Check fixture 20: list_fixtures(fixture_id=20)
        - Check fixture 1 (likely missing): list_fixtures(fixture_id=1)
    """
    client = await _srv.get_client()

    if fixture_id is not None:
        cmd = f"list fixture {fixture_id}"
        raw = await client.send_command_with_response(cmd)
        exists = "NO OBJECTS FOUND" not in raw.upper()
    else:
        cmd = "list fixture"
        raw = await client.send_command_with_response(cmd)
        exists = True

    return json.dumps({
        "command_sent": cmd,
        "raw_response": raw,
        "exists": exists,
        "fixture_id": fixture_id,
        "risk_tier": "SAFE_READ",
    }, indent=2)


@mcp.tool()
@require_scope(OAuthScope.STATE_READ)
@_handle_errors
async def list_sequence_cues(
    sequence_id: int | None = None,
    executor_id: int | None = None,
    executor_page: int = 1,
    cue_id: int | float | None = None,
) -> str:
    """
    List cues in a sequence, or check whether a specific cue exists.

    Supports two ways to identify the sequence:
      - sequence_id: Direct sequence number (e.g. 278)
      - executor_id: Executor number — sequence is resolved via
        'list executor PAGE.ID' before listing cues

    If both are supplied, sequence_id takes precedence.

    Validated MA2 probes used:
      'list cue sequence N'     → all cues in sequence N
      'list cue M sequence N'   → specific cue M in sequence N
      'list executor P.E'       → resolve sequence from executor

    Args:
        sequence_id: Sequence number to inspect.
        executor_id: Executor number — resolved to its linked sequence.
        executor_page: Executor page for resolution (default 1).
        cue_id: Optional specific cue to check for existence.

    Returns:
        str: JSON with command_sent, raw_response, exists, resolved_sequence_id,
             and executor_probe_response (when executor_id was used).

    Examples:
        - All cues in seq 278: list_sequence_cues(sequence_id=278)
        - Cue 5 in seq 278: list_sequence_cues(sequence_id=278, cue_id=5)
        - Cues for executor 1: list_sequence_cues(executor_id=1)
        - Check cue 99 on executor 1: list_sequence_cues(executor_id=1, cue_id=99)
    """
    client = await _srv.get_client()
    executor_probe_response: str | None = None

    resolved_sequence = sequence_id
    if resolved_sequence is None and executor_id is not None:
        resolved_sequence, executor_probe_response = await _get_sequence_for_executor(
            client, executor_id, page=executor_page
        )
        if resolved_sequence is None:
            return json.dumps({
                "command_sent": f"list executor {executor_page}.{executor_id}",
                "raw_response": executor_probe_response,
                "error": (
                    f"Could not resolve a sequence for executor "
                    f"{executor_page}.{executor_id}. "
                    "The executor may not have a sequence assigned."
                ),
                "exists": False,
                "resolved_sequence_id": None,
                "risk_tier": "SAFE_READ",
                "blocked": True,
            }, indent=2)

    if resolved_sequence is None:
        return json.dumps({
            "error": "Must supply either sequence_id or executor_id.",
            "command_sent": None,
            "risk_tier": "SAFE_READ",
            "blocked": True,
        }, indent=2)

    if cue_id is not None:
        cmd = f"list cue {cue_id} sequence {resolved_sequence}"
    else:
        cmd = f"list cue sequence {resolved_sequence}"

    raw = await client.send_command_with_response(cmd)
    exists = "NO OBJECTS FOUND" not in raw.upper() if cue_id is not None else True

    result: dict = {
        "command_sent": cmd,
        "raw_response": raw,
        "exists": exists,
        "resolved_sequence_id": resolved_sequence,
        "risk_tier": "SAFE_READ",
    }
    if executor_probe_response is not None:
        result["executor_probe_response"] = executor_probe_response

    return json.dumps(result, indent=2)


# ============================================================
# Wildcard Name Discovery
# ============================================================

# Object pool destinations that hold user-nameable objects.
# Keyword form (e.g. "Group") and numeric cd-index form (e.g. "22") are both accepted.
# Reference: CD_NUMERIC_INDEX in src/vocab.py — live-verified on MA2 3.9.60.65.
# NOTE: System-config branches (cd 1=Showfile, cd 2=TimeConfig, cd 3=Settings …)
#       are NOT object pools — they have property nodes, not named user objects.
_OBJECT_POOL_DESTINATIONS: dict[str, str] = {
    # keyword        numeric cd index
    "Group":         "22",
    "Sequence":      "25",
    "Preset":        "17",
    "Macro":         "13",
    "Effect":        "24",
    "Gel":           "16",
    "World":         "18",
    "Filter":        "19",
    "Form":          "23",
    "Timer":         "26",
    "Layout":        "38",
    "Timecode":      "35",
    "Agenda":        "34",
    "UserProfile":   "39",
    "Camera":        "Camera",   # no separate numeric index — cd Camera
    "MAtricks":      "MAtricks",
    "View":          "View",
    "Remote":        "36",
}


# ============================================================
# Pool Availability Checker
# ============================================================


async def _check_pool_slots(
    client: "GMA2TelnetClient",
    pool_type: str,
    start_from: int = 1,
    scan_up_to: int = 200,
    needed_slots: int | None = None,
) -> dict:
    """Check which slots are occupied/free in a pool.

    Navigates to the pool via cd, lists contents, computes availability,
    then returns to root.  Pure SAFE_READ — no modifications.

    Args:
        client: Connected telnet client.
        pool_type: Pool keyword (e.g. "Macro", "Filter", "Group") or
            numeric cd index (e.g. "13").  Case-insensitive lookup
            against ``_OBJECT_POOL_DESTINATIONS``.
        start_from: First slot to consider (default 1).
        scan_up_to: Last slot to consider (default 200).
        needed_slots: If set, checks whether this many contiguous free
            slots exist and suggests a start position.

    Returns:
        dict with keys: pool_type, occupied_slots, free_ranges,
        next_free_slots, total_occupied, total_free_in_range,
        largest_contiguous, can_fit, suggested_start.
    """
    # Resolve pool destination
    destination: str | None = None
    pool_key = pool_type.strip()

    # Try keyword lookup (case-insensitive)
    for key, val in _srv._OBJECT_POOL_DESTINATIONS.items():
        if key.lower() == pool_key.lower():
            destination = val
            pool_key = key  # normalise casing
            break

    # Accept raw numeric / keyword destinations as-is
    if destination is None:
        destination = pool_key

    # Navigate to pool
    await _srv.navigate(client, destination)

    # List contents
    lst = await _srv.list_destination(client)
    entries = lst.parsed_list.entries

    # Detect sub-pool level (e.g. Macros cd 13 → "MacroPool 1 Global")
    # If entries look like container objects rather than actual pool items,
    # navigate one level deeper.
    if (
        entries
        and len(entries) == 1
        and entries[0].object_type
        and "Pool" in (entries[0].object_type or "")
    ):
        await _srv.navigate(client, "1")
        lst = await _srv.list_destination(client)
        entries = lst.parsed_list.entries

    # Parse occupied slot numbers
    occupied: list[dict] = []
    occupied_ids: set[int] = set()
    for e in entries:
        if e.object_id is None:
            continue
        try:
            slot = int(e.object_id)
        except (ValueError, TypeError):
            continue
        if start_from <= slot <= scan_up_to:
            occupied.append({"slot": slot, "name": e.name or ""})
            occupied_ids.add(slot)

    # Sort occupied by slot number
    occupied.sort(key=lambda x: x["slot"])

    # Compute free ranges and next free slots
    free_ranges: list[dict] = []
    next_free: list[int] = []
    run_start: int | None = None
    largest_contiguous = 0

    for slot in range(start_from, scan_up_to + 1):
        if slot not in occupied_ids:
            if run_start is None:
                run_start = slot
            if len(next_free) < 10:
                next_free.append(slot)
        else:
            if run_start is not None:
                run_len = slot - run_start
                free_ranges.append({"start": run_start, "end": slot - 1})
                if run_len > largest_contiguous:
                    largest_contiguous = run_len
                run_start = None

    # Close trailing free range
    if run_start is not None:
        run_len = scan_up_to - run_start + 1
        free_ranges.append({"start": run_start, "end": scan_up_to})
        if run_len > largest_contiguous:
            largest_contiguous = run_len

    total_in_range = scan_up_to - start_from + 1
    total_free = total_in_range - len(occupied)

    # Check if needed_slots can fit contiguously
    can_fit: bool | None = None
    suggested_start: int | None = None
    if needed_slots is not None:
        can_fit = False
        for fr in free_ranges:
            block_size = fr["end"] - fr["start"] + 1
            if block_size >= needed_slots:
                can_fit = True
                suggested_start = fr["start"]
                break

    # Return to root
    await _srv.navigate(client, "/")

    return {
        "pool_type": pool_key,
        "occupied_slots": occupied,
        "free_ranges": free_ranges,
        "next_free_slots": next_free,
        "total_occupied": len(occupied),
        "total_free_in_range": total_free,
        "largest_contiguous": largest_contiguous,
        "can_fit": can_fit,
        "suggested_start": suggested_start,
    }


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def check_pool_availability(
    pool_type: str,
    start_from: int = 1,
    scan_up_to: int = 200,
    needed_slots: int | None = None,
) -> str:
    """
    Check which slots are occupied and free in an object pool (SAFE_READ).

    Navigates to the pool, lists all entries, and computes a full
    availability map: occupied slots (with names), free ranges,
    next 10 free slots, and contiguous-block analysis.

    Use this **before importing XML** to verify target slots are free,
    or to find the best slot range for bulk imports (filters, MAtricks).

    Valid pool types (case-insensitive):
      Group, Sequence, Preset, Macro, Effect, Gel, World, Filter,
      Form, Timer, Layout, Timecode, Agenda, UserProfile, Camera,
      MAtricks, View, Remote

    Numeric cd indexes also accepted (e.g. "13" for Macros, "19" for Filters).

    Args:
        pool_type: Pool keyword or numeric cd index.
        start_from: First slot number to check (default 1).
        scan_up_to: Last slot number to check (default 200).
        needed_slots: If set, checks whether N contiguous free slots
            exist and returns can_fit + suggested_start.

    Returns:
        str: JSON with occupied_slots, free_ranges, next_free_slots,
             total_occupied, total_free_in_range, largest_contiguous,
             can_fit, suggested_start, risk_tier.
    """
    client = await _srv.get_client()
    result = await _srv._check_pool_slots(
        client,
        pool_type,
        start_from=start_from,
        scan_up_to=scan_up_to,
        needed_slots=needed_slots,
    )
    result["risk_tier"] = "SAFE_READ"
    return json.dumps(result, indent=2)


@mcp.tool()
@require_scope(OAuthScope.DISCOVER)
@_handle_errors
async def discover_object_names(destination: str) -> str:
    """
    Navigate to an object pool and return all object names for wildcard pattern building.

    This is the first step in the discover-names → derive-pattern → wildcard-command
    workflow.  The returned names can be used directly with list_objects(),
    info(), label(), etc. by passing them as the ``name`` argument with
    ``match_mode="literal"`` (exact match) or deriving a ``*``-pattern and
    using ``match_mode="wildcard"``.

    CD scope covered
    ----------------
    Any destination accepted by navigate_console() works here:
      - Keyword form:      "Group", "Sequence", "Preset", "Macro", "Effect", …
      - Numeric index:     "22" (Groups), "25" (Sequences), "17" (Presets), …
      - Dot-notation:      "10.3" (LiveSetup/FixtureTypes)

    Object pool destinations (cd 1–42 that have named user objects):
      Group=22, Sequence=25, Preset=17, Macro=13, Effect=24, Gel=16, World=18,
      Filter=19, Form=23, Timer=26, Layout=38, Timecode=35, Agenda=34,
      UserProfile=39, Remote=36.

    System-config branches (cd 1=Showfile, cd 2=TimeConfig, cd 3=Settings,
    cd 4=DMX_Protocols, …) hold property nodes, not named user objects — they
    return empty names and are not useful for wildcard matching.

    After this call the console is left at root (cd /).

    Args:
        destination: Object pool to inspect.  Any format accepted by
            navigate_console: keyword ("Group"), numeric index ("22"),
            or dot path ("10.3").

    Returns:
        str: JSON with destination, entries (id + name), names_only list,
             and a wildcard_tip suggesting how to build a pattern.

    Example workflow::

        discover_object_names("Group")
        # → names: ["Mac700 Front", "Mac700 Back", "Wash", "ALL LASERS"]

        # Derive prefix pattern and use with list_objects:
        # list_objects("group", name="Mac700*", match_mode="wildcard")
        # → "list group Mac700*"
    """
    client = await _srv.get_client()

    # Navigate to the destination
    nav = await _srv.navigate(client, destination)

    # List all objects there
    lst = await _srv.list_destination(client)

    # Collect non-empty names
    named_entries = [
        {"object_id": e.object_id, "name": e.name}
        for e in lst.parsed_list.entries
        if e.name
    ]
    names_only = [e["name"] for e in named_entries]

    # Build a wildcard tip based on common prefix (if any)
    tip = None
    if names_only:
        first = names_only[0]
        prefix = first.split()[0] if " " in first else first
        if len(names_only) > 1 and all(n.startswith(prefix) for n in names_only):
            tip = f'Common prefix detected — try: name="{prefix}*", match_mode="wildcard"'
        else:
            tip = 'No common prefix — use exact names with match_mode="literal" or derive your own pattern'

    # Return to root
    await _srv.navigate(client, "/")

    return json.dumps(
        {
            "destination": destination,
            "navigate_command": nav.command_sent,
            "entry_count": len(lst.parsed_list.entries),
            "named_count": len(named_entries),
            "entries": named_entries,
            "names_only": names_only,
            "wildcard_tip": tip,
        },
        indent=2,
    )
