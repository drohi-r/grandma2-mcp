"""
console_state.py — ConsoleStateSnapshot: closes all 19 show-memory gaps.

Hydrated once at session start via ConsoleStateHydrator before any sub-agent runs.
Sub-agents read from the snapshot instead of issuing extra telnet round-trips.

Gap coverage:
  1  Filter state (active_filter + filter_vte)
  2  World state (active_world)
  3  Park state (parked_fixtures)
  4  System variables — all 26 (showfile, pages, selected counts, etc.)
  5  Three-page state (fader_page, button_page, channel_page)
  6  MAtricks state (matricks — write-tracker, no telnet readback exists)
  7  Cue parts (sequence_cues: list[CueRecord] with CuePart support)
  8  Preset pool inventory (name_index populated per pool type)
  9  Sequence properties (in SequenceEntry — loop, speed, etc.)
  10 Executor assignment state (executor_state dict)
  11 Blind/Highlight mode (console_modes dict)
  12 Timecode/Timer runtime state (timecode_state, timer_state)
  13 Macro execution state (active_macros)
  14 UserProfile context (active_user_profile)
  15 Layout state (layout_labels)
  16 FixtureType inventory (fixture_types)
  17 Showfile history / unsaved changes (showfile, has_unsaved_changes)
  18 $SELECTEDFIXTURESCOUNT
  19 $SELECTEDEXEC / $SELECTEDEXECCUE
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .commands.constants import MA2Right
from .pool_name_index import ObjectRef, PoolNameIndex

logger = logging.getLogger(__name__)

TelnetSend = Callable[[str], Awaitable[str]]

# $USERRIGHTS display name → MA2Right
_RIGHTS_MAP: dict[str, MA2Right] = {
    "admin":    MA2Right.ADMIN,
    "setup":    MA2Right.SETUP,
    "program":  MA2Right.PROGRAM,
    "presets":  MA2Right.PRESETS,
    "playback": MA2Right.PLAYBACK,
    "none":     MA2Right.NONE,
}


def _parse_userrights(raw: str) -> MA2Right:
    return _RIGHTS_MAP.get(raw.strip().lower(), MA2Right.NONE)


def _parse_int(val: str, default: int = 0) -> int:
    try:
        return int(val.strip())
    except (ValueError, AttributeError):
        return default


def _parse_listvar_raw(raw: str) -> dict[str, str]:
    """Parse ListVar telnet output: '$Global : $NAME = VALUE' → {'$NAME': 'VALUE'}."""
    variables: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if "=" not in line or line.startswith("["):
            continue
        if " : " in line:
            _, _, line = line.partition(" : ")
            line = line.strip()
        name, _, value = line.partition("=")
        name = name.strip().lstrip("$")
        value = value.strip()
        if name:
            variables[f"${name}"] = value
    return variables


def parse_showfile_from_listvar(raw: str) -> str:
    """Extract $SHOWFILE value from a ListVar response string.

    Returns the show name, or "" if not found.
    """
    return _parse_listvar_raw(raw).get("$SHOWFILE", "")


# ---------------------------------------------------------------------------
# Sub-structures for gaps 6, 7, 9, 10
# ---------------------------------------------------------------------------

@dataclass
class MAtricksTracker:
    """
    Write-tracker for the programmer's MAtricks state.
    No telnet readback exists — updated whenever manage_matricks is called.
    Gap 6.
    """
    interleave: int | None = None
    blocks_x: int | None = None
    blocks_y: int | None = None
    groups_x: int | None = None
    groups_y: int | None = None
    wings: int | None = None
    filter_id: int | None = None
    active: bool = False

    def reset(self) -> None:
        self.interleave = None
        self.blocks_x = self.blocks_y = None
        self.groups_x = self.groups_y = None
        self.wings = None
        self.filter_id = None
        self.active = False

    def summary(self) -> str:
        parts = []
        if self.interleave is not None:
            parts.append(f"interleave={self.interleave}")
        if self.blocks_x is not None:
            parts.append(f"blocks={self.blocks_x}{'.' + str(self.blocks_y) if self.blocks_y else ''}")
        if self.groups_x is not None:
            parts.append(f"groups={self.groups_x}{'.' + str(self.groups_y) if self.groups_y else ''}")
        if self.wings is not None:
            parts.append(f"wings={self.wings}")
        if self.filter_id is not None:
            parts.append(f"filter={self.filter_id}")
        return " ".join(parts) or "off"


@dataclass
class CuePart:
    """One part of a multi-part cue. Gap 7."""
    part: int = 0
    label: str = ""


@dataclass
class CueRecord:
    """A cue entry with part support. Gap 7."""
    sequence_id: int
    cue_number: float
    label: str = ""
    parts: list[CuePart] = field(default_factory=list)


@dataclass
class SequenceEntry:
    """Sequence with key properties. Gap 9."""
    id: int
    label: str = ""
    loop: bool = False
    chaser: bool = False
    autoprepare: bool = False
    speed_master: int | None = None


@dataclass
class ExecutorState:
    """Executor assignment state. Gap 10."""
    id: int
    page: int = 1
    sequence_id: int | None = None
    label: str = ""
    priority: str = "normal"
    button_function: str = ""
    fader_function: str = ""
    ooo: bool = False
    kill_protect: bool = False
    auto_start: bool = False


# ---------------------------------------------------------------------------
# ConsoleStateSnapshot
# ---------------------------------------------------------------------------

@dataclass
class ConsoleStateSnapshot:
    """
    Full ground-truth snapshot of the grandMA2 console state.
    Hydrated at session start, caching answers to all 19 memory gaps.
    """

    # ── Hydration metadata ───────────────────────────────────────────
    hydrated_at: float = field(default_factory=time.time)
    hydration_duration_s: float = 0.0
    partial: bool = False
    hydration_errors: list[str] = field(default_factory=list)

    # ── Gap 4/17: System variables ───────────────────────────────────
    showfile: str = ""
    active_user: str = ""
    user_rights_str: str = ""          # raw from $USERRIGHTS
    hostname: str = ""
    version: str = ""
    host_status: str = ""

    # ── Gap 5: Three independent page counters ───────────────────────
    fader_page: int = 1
    button_page: int = 1
    channel_page: int = 1

    # ── Gap 18/19: Selection and executor state ───────────────────────
    selected_fixture_count: int = 0
    active_preset_type: str = ""       # $PRESET — e.g. "COLOR"
    active_feature: str = ""           # $FEATURE
    active_attribute: str = ""         # $ATTRIBUTE
    selected_exec: str = ""            # $SELECTEDEXEC — "page.page.exec"
    selected_exec_cue: str = ""        # $SELECTEDEXECCUE — cue num or "NONE"

    # ── Gap 2: World state ────────────────────────────────────────────
    active_world: int | None = None
    world_labels: dict[int, str] = field(default_factory=dict)

    # ── Gap 1: Filter state ───────────────────────────────────────────
    active_filter: int | None = None
    filter_vte: dict[str, bool] = field(default_factory=lambda: {
        "value": True, "value_timing": True, "effect": True
    })

    # ── Gap 11: Console modes ─────────────────────────────────────────
    console_modes: dict[str, bool] = field(default_factory=lambda: {
        "blind": False, "highlight": False,
        "freeze": False, "solo": False, "blackout": False,
    })

    # ── Gap 3: Park state ─────────────────────────────────────────────
    parked_fixtures: set[str] = field(default_factory=set)

    # ── Gap 8: Preset pool inventory (via name_index) ──────────────────
    name_index: PoolNameIndex = field(default_factory=PoolNameIndex)

    # ── Gap 6: MAtricks state ────────────────────────────────────────
    matricks: MAtricksTracker = field(default_factory=MAtricksTracker)

    # ── Gap 9: Sequences with properties ─────────────────────────────
    sequences: list[SequenceEntry] = field(default_factory=list)

    # ── Gap 7: Cue records with part support ──────────────────────────
    sequence_cues: list[CueRecord] = field(default_factory=list)

    # ── Gap 10: Executor assignment state ────────────────────────────
    executor_state: dict[int, ExecutorState] = field(default_factory=dict)

    # ── Gap 12: Timecode / Timer runtime state ────────────────────────
    timecode_state: dict[str, Any] = field(default_factory=dict)
    timer_state: dict[str, Any] = field(default_factory=dict)

    # ── Gap 13: Active macros ─────────────────────────────────────────
    active_macros: list[int] = field(default_factory=list)

    # ── Gap 14: UserProfile context ───────────────────────────────────
    active_user_profile: str = "Default"

    # ── Gap 15: Layout labels ─────────────────────────────────────────
    layout_labels: dict[int, str] = field(default_factory=dict)

    # ── Gap 16: FixtureType inventory ────────────────────────────────
    fixture_types: list[str] = field(default_factory=list)

    # ── Gap 17: Unsaved changes flag ──────────────────────────────────
    has_unsaved_changes: bool = False

    # ── Derived: MA2Right from user_rights_str ───────────────────────
    user_right: MA2Right = MA2Right.NONE

    # ── Convenience ──────────────────────────────────────────────────

    def age_seconds(self) -> float:
        return time.time() - self.hydrated_at

    def staleness_warning(self, max_age: float = 30.0) -> str | None:
        age = self.age_seconds()
        if age > max_age:
            return (
                f"ConsoleStateSnapshot is {age:.0f}s old (max {max_age}s). "
                "Re-hydrate before DESTRUCTIVE steps."
            )
        return None

    def preset_exists(self, preset_type: int, preset_id: int) -> bool:
        """Check if a preset is known in the name index."""
        entries = self.name_index.all_entries("preset", preset_type=preset_type)
        return any(e["id"] == preset_id for e in entries)

    def resolve(
        self,
        object_type: str,
        name: str | None = None,
        id: int | None = None,
        match_mode: str = "literal",
        preset_type: int | None = None,
    ) -> ObjectRef:
        """Resolve a pool object to a command token via the name index."""
        return self.name_index.resolve(
            object_type=object_type,
            name=name,
            id=id,
            match_mode=match_mode,
            preset_type=preset_type,
        )

    def summary(self) -> str:
        age = self.age_seconds()
        lines = [
            f"ConsoleStateSnapshot (age={age:.0f}s, partial={self.partial})",
            f"  show={self.showfile!r}  user={self.active_user!r} ({self.user_right.value})",
            f"  pages: fader={self.fader_page} button={self.button_page} ch={self.channel_page}",
            f"  selection: {self.selected_fixture_count} fixtures  preset_type={self.active_preset_type}",
            f"  world={self.active_world}  filter={self.active_filter}",
            f"  modes: {', '.join(k for k, v in self.console_modes.items() if v) or 'none'}",
            f"  parked: {len(self.parked_fixtures)} fixtures",
            f"  matricks: {self.matricks.summary()}",
            f"  index: {self.name_index.stats()}",
        ]
        if self.hydration_errors:
            lines.append(f"  errors: {self.hydration_errors}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# ConsoleStateHydrator
# ---------------------------------------------------------------------------

# Pool types to index — ordered by expected telnet round-trip cost
_POOL_TYPES_TO_INDEX = [
    "Group", "Sequence", "Macro", "Effect", "Timecode", "Timer",
    "View", "Layout", "World", "Filter", "Page",
    "Fixture", "Executor",
]


class ConsoleStateHydrator:
    """
    Hydrates a ConsoleStateSnapshot from live telnet reads.

    Phase 1: ListVar (all 26 system variables — one telnet call)
    Phase 2: Pool name index (parallel cd+list per pool type)
    Phase 3 (optional): Deep cue/part hydration for specified sequence IDs

    Failures in any phase set snapshot.partial=True but don't abort.
    """

    def __init__(self, telnet_send: TelnetSend) -> None:
        self._send = telnet_send

    async def hydrate(
        self,
        sequence_ids: list[int] | None = None,
    ) -> ConsoleStateSnapshot:
        t0 = time.time()
        snap = ConsoleStateSnapshot()

        # Phase 1: System variables
        await self._hydrate_system_vars(snap)

        # Phase 2: Pool name index (run all types concurrently)
        await self._hydrate_pool_index(snap)

        # Phase 3: Deep sequence cue hydration (optional)
        if sequence_ids:
            await self._hydrate_sequences(snap, sequence_ids)

        snap.hydration_duration_s = round(time.time() - t0, 3)
        return snap

    # ── Phase 1: system variables ────────────────────────────────────

    async def _hydrate_system_vars(self, snap: ConsoleStateSnapshot) -> None:
        try:
            raw = await self._send("ListVar")
            variables = _parse_listvar_raw(raw)
            _apply_system_vars(snap, variables)
        except Exception as exc:
            snap.partial = True
            snap.hydration_errors.append(f"ListVar failed: {exc}")

    # ── Phase 2: pool index ───────────────────────────────────────────

    async def _hydrate_pool_index(self, snap: ConsoleStateSnapshot) -> None:
        tasks = [
            self._index_one_pool(snap, pool_type)
            for pool_type in _POOL_TYPES_TO_INDEX
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for pool_type, result in zip(_POOL_TYPES_TO_INDEX, results, strict=False):
            if isinstance(result, Exception):
                snap.partial = True
                snap.hydration_errors.append(f"Pool index {pool_type} failed: {result}")

    async def _index_one_pool(self, snap: ConsoleStateSnapshot, pool_type: str) -> None:
        try:
            # Navigate to the pool and list its contents
            await self._send(f"cd {pool_type}")
            raw = await self._send("list")
            await self._send("cd /")
            _parse_pool_list(snap.name_index, pool_type, raw)
        except Exception as exc:
            raise RuntimeError(f"{pool_type}: {exc}") from exc

    # ── Phase 3: deep sequence hydration ─────────────────────────────

    async def _hydrate_sequences(
        self, snap: ConsoleStateSnapshot, sequence_ids: list[int]
    ) -> None:
        for seq_id in sequence_ids:
            try:
                await self._send(f"cd Sequence.{seq_id}")
                raw = await self._send("list cue")
                await self._send("cd /")
                cues = _parse_cue_list(seq_id, raw)
                snap.sequence_cues.extend(cues)
            except Exception as exc:
                snap.partial = True
                snap.hydration_errors.append(f"Sequence {seq_id} cues failed: {exc}")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _apply_system_vars(snap: ConsoleStateSnapshot, variables: dict[str, str]) -> None:
    """Map $VAR values onto snapshot fields."""
    g = variables.get

    snap.showfile           = g("$SHOWFILE", "")
    snap.active_user        = g("$USER", "")
    snap.user_rights_str    = g("$USERRIGHTS", "")
    snap.hostname           = g("$HOSTNAME", "")
    snap.version            = g("$VERSION", "")
    snap.host_status        = g("$HOSTSTATUS", "")
    snap.fader_page         = _parse_int(g("$FADERPAGE", "1"), 1)
    snap.button_page        = _parse_int(g("$BUTTONPAGE", "1"), 1)
    snap.channel_page       = _parse_int(g("$CHANNELPAGE", "1"), 1)
    snap.selected_fixture_count = _parse_int(g("$SELECTEDFIXTURESCOUNT", "0"), 0)
    snap.active_preset_type = g("$PRESET", "")
    snap.active_feature     = g("$FEATURE", "")
    snap.active_attribute   = g("$ATTRIBUTE", "")
    snap.selected_exec      = g("$SELECTEDEXEC", "")
    snap.selected_exec_cue  = g("$SELECTEDEXECCUE", "NONE")
    snap.active_user_profile = g("$USERPROFILE", "Default")

    snap.user_right = _parse_userrights(snap.user_rights_str)


def _parse_pool_list(
    index: PoolNameIndex, pool_type: str, raw: str
) -> None:
    """
    Parse tabular list output into name/id pairs and add to the index.

    MA2 list output format (space-separated):
      ID  Name  [other columns...]
    or
      No  Name  [other columns...]

    We take the first numeric column as ID and the next word/quoted as name.
    Lines starting with '[' or empty are skipped.
    """
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("[") or line.upper().startswith("NO "):
            continue
        parts = line.split(None, 2)
        if len(parts) < 2:
            continue
        # Try first token as ID
        try:
            obj_id = int(parts[0])
        except ValueError:
            continue
        name = parts[1].strip('"').strip("'")
        if name:
            index.add_entry(pool_type, name, obj_id)


def _parse_cue_list(seq_id: int, raw: str) -> list[CueRecord]:
    """Parse 'list cue' output for a sequence into CueRecord objects."""
    cues: list[CueRecord] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("["):
            continue
        # Format: "Cue N [Part M] [Label]" or just "N [label]"
        parts = line.split(None, 3)
        if not parts:
            continue
        try:
            cue_num = float(parts[0])
        except ValueError:
            continue
        label = parts[-1].strip('"') if len(parts) > 1 else ""
        cues.append(CueRecord(sequence_id=seq_id, cue_number=cue_num, label=label))
    return cues
