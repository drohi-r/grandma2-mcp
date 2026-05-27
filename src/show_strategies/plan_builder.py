"""Plan builder — strategy + patch summary → ordered list of ShowBuildStep.

Pure function over ``PatchSummary`` and ``Strategy``. No I/O.

Output shape:
    [ShowBuildStep, ...]  where each step has order/kind/command/purpose/
    expert_says/risk_tier/meta. The plan is deterministic for a given
    (strategy, patch, options) triple.

Plan section ordering (deterministic — feeds the lint dispatcher's plan rules):
    1. create-group     — per-fixture-type groups (skip already-grouped types)
    2. store-preset     — universal color presets (always: red/green/blue/white)
    3. store-preset     — universal position presets (only when patch has movers)
    4. store-preset     — selective gobo (full-coverage strategy + movers only)
    5. store-preset     — selective beam   (full-coverage strategy + movers only)
    6. assign-executor  — intensity/color/position/beam/fx bank (5 executors)
    7. assign-executor  — blackout sub (Super), speed master, tap-tempo
    8. store-cue        — per-song-section cues (count = songs * sections)
    9. create-world     — per-section worlds (only when world_filter_scope is per-section)
"""

from __future__ import annotations

from src.show_strategies.strategy_table import get_strategy
from src.show_strategies.types import (
    PatchSummary,
    ShowBuildOptions,
    ShowBuildStep,
    Strategy,
)


_GENERIC_TYPE_NAMES = ("universal attributes", "dimmer")
_MOVER_KEYWORDS = ("mover", "head", "spot", "wash", "b-eye", "beam")
_DEFAULT_SECTIONS = ["intro", "verse", "chorus", "bridge", "outro"]


def _has_movers(patch: PatchSummary) -> bool:
    for ft in patch.get("fixture_types", []):
        ln = (ft.get("long_name") or "").lower()
        if any(kw in ln for kw in _MOVER_KEYWORDS):
            return True
    return False


def _format_label(template: str, **fields: object) -> str:
    """Apply naming-convention template; missing fields render as literal markers."""
    try:
        return template.format(**fields)
    except (KeyError, IndexError):
        # Fall back to a best-effort string
        return template


def build_plan_for(
    *,
    strategy: str,
    patch: PatchSummary,
    options: ShowBuildOptions | None = None,
) -> list[ShowBuildStep]:
    """Build a strategy-specific show plan from a patch summary."""
    s: Strategy = get_strategy(strategy)
    opts = dict(options or {})
    plan: list[ShowBuildStep] = []
    order = 0

    def add(
        kind: str,
        command: str,
        purpose: str,
        expert_says: str,
        risk_tier: str = "SAFE_WRITE",
        **meta: object,
    ) -> None:
        nonlocal order
        order += 1
        plan.append(ShowBuildStep(
            order=order,
            kind=kind,
            command=command,
            purpose=purpose,
            expert_says=expert_says,
            risk_tier=risk_tier,
            meta=dict(meta),
        ))

    # 1. Per-fixture-type groups (idempotent — skip types already grouped or
    #    generic Universal Attributes / Dimmer).
    existing_group_names = {
        (g.get("name") or "").lower() for g in patch.get("groups", [])
    }
    next_group_id = max(
        (g.get("id", 0) for g in patch.get("groups", [])), default=0,
    ) + 1
    for ft in patch.get("fixture_types", []):
        long_name = (ft.get("long_name") or "").lower()
        if any(generic in long_name for generic in _GENERIC_TYPE_NAMES):
            continue
        short = ft.get("short_name") or ft.get("long_name", "Unknown")
        if short.lower() in existing_group_names:
            continue
        add(
            kind="create-group",
            command=f'Store Group {next_group_id} /o',
            purpose=f"Per-type group for {short}",
            expert_says=(
                "Per-fixture-type groups are the foundation for selective "
                "presets and executor banking."
            ),
            risk_tier="DESTRUCTIVE",
            fixture_type=short,
            group_id=next_group_id,
        )
        next_group_id += 1

    # 2. Universal color presets — always.
    for i, (name, rgb) in enumerate(
        [
            ("Red", (100, 0, 0)),
            ("Green", (0, 100, 0)),
            ("Blue", (0, 0, 100)),
            ("White", (100, 100, 100)),
        ],
        start=1,
    ):
        add(
            kind="store-preset",
            command=f'Store Preset 4.{i} /o',
            purpose=f"Universal color preset {name}",
            expert_says=(
                "Universal color presets cover all fixture types; clamp to "
                "rig capability is automatic per MA2 universal scope."
            ),
            risk_tier="DESTRUCTIVE",
            preset_type=4,
            preset_id=i,
            scope="universal",
            name=name,
            values={"rgb": rgb},
            covers_attributes=["R", "G", "B"],
        )

    has_movers = _has_movers(patch)

    # 3. Universal position presets — only if the rig has movers.
    if has_movers:
        for i, name in enumerate(
            ["Home", "Audience", "Stage Left", "Stage Right"], start=1,
        ):
            add(
                kind="store-preset",
                command=f'Store Preset 2.{i} /o',
                purpose=f"Universal position preset {name}",
                expert_says=(
                    "Per spec §B.1 — position presets stay universal for "
                    "mover groups; per-mover deltas live in subgroups."
                ),
                risk_tier="DESTRUCTIVE",
                preset_type=2,
                preset_id=i,
                scope="universal",
                name=name,
                covers_attributes=["Pan", "Tilt"],
            )

    # 4. Selective gobo presets (full-coverage + movers only).
    if s.preset_strategy == "full-coverage" and has_movers:
        for j, ft in enumerate(patch.get("fixture_types", []), start=10):
            short = ft.get("short_name") or ""
            ln = (ft.get("long_name") or "").lower()
            if not short or any(g in ln for g in _GENERIC_TYPE_NAMES):
                continue
            # Skip pure-wash fixtures (no gobo wheel)
            if ("wash" in ln) and ("spot" not in ln):
                continue
            add(
                kind="store-preset",
                command=f'Store Preset 3.{j} /o',
                purpose=f"Selective gobo for {short}",
                expert_says=(
                    "Gobo is fixture-specific — selective scope so the pool "
                    "entry doesn't smash other types' gobo wheels."
                ),
                risk_tier="DESTRUCTIVE",
                preset_type=3,
                preset_id=j,
                scope="selective",
                target_fixture_types=[short],
                name=f"{short} Gobo Set",
            )

    # 5. Selective beam presets (full-coverage + movers only).
    if s.preset_strategy == "full-coverage" and has_movers:
        for j, ft in enumerate(patch.get("fixture_types", []), start=10):
            short = ft.get("short_name") or ""
            ln = (ft.get("long_name") or "").lower()
            if not short or any(g in ln for g in _GENERIC_TYPE_NAMES):
                continue
            if ("wash" in ln) and ("spot" not in ln):
                continue
            add(
                kind="store-preset",
                command=f'Store Preset 5.{j} /o',
                purpose=f"Selective beam for {short}",
                expert_says=(
                    "Beam attributes (zoom/focus/iris) are fixture-specific."
                ),
                risk_tier="DESTRUCTIVE",
                preset_type=5,
                preset_id=j,
                scope="selective",
                target_fixture_types=[short],
                name=f"{short} Beam Set",
            )

    # 6. Executor bank assignment — intensity/color/position/beam/fx.
    bank_layout = [
        ("1.1.1", "intensity"),
        ("1.1.2", "color"),
        ("1.1.3", "position"),
        ("1.1.4", "beam"),
        ("1.1.5", "fx"),
    ]
    for slot, role in bank_layout:
        add(
            kind="assign-executor",
            command=f'Assign Executor {slot}',
            purpose=f"{role.title()} master executor",
            expert_says=(
                f"Bank position for {role} per the muscle-memory map: "
                "intensity left → specials right."
            ),
            risk_tier="DESTRUCTIVE",
            slot=slot,
            role=role,
            label=f"{role.title()} Master",
            priority=("htp" if role == "intensity" else "normal"),
        )

    # 7. Blackout sub + speed master + tap (per strategy).
    add(
        kind="assign-executor",
        command='Assign Executor 1.1.10 /priority=super',
        purpose="Blackout sub-master (Super priority, independent of GM)",
        expert_says=(
            "Blackout sub at Super priority — non-negotiable for any live rig."
        ),
        risk_tier="DESTRUCTIVE",
        slot="1.1.10",
        role="blackout-sub",
        priority="super",
        function="macro",
        label="BLACKOUT",
    )
    if s.name in {"rock-band", "dj", "festival"}:
        add(
            kind="assign-executor",
            command='Assign Executor 1.1.11 /speedmaster=speed1',
            purpose="Speed master bound to FX bank",
            expert_says=(
                "Speed master is essential for live BPM control of chases."
            ),
            risk_tier="DESTRUCTIVE",
            slot="1.1.11",
            role="speedmaster",
            function="speedmaster",
            label="Speed Master",
        )
    if s.name in {"rock-band", "dj"}:
        add(
            kind="assign-executor",
            command='Assign Executor 1.1.12 /function=tap',
            purpose="Tap-tempo executor",
            expert_says=(
                "Tap-tempo lets the LD lock chase speed to live tempo."
            ),
            risk_tier="DESTRUCTIVE",
            slot="1.1.12",
            role="tap",
            function="tap",
            label="Tap",
        )

    # 8. Per-strategy cues (named per naming_convention).
    songs = int(opts.get("songs", s.default_songs))
    sections = _DEFAULT_SECTIONS
    for song_n in range(1, songs + 1):
        for i, section in enumerate(sections, start=1):
            cue_id = song_n + (i / 10.0)
            label = _format_label(
                s.naming_convention,
                song=f"song{song_n}",
                section=section,
                intent="lift" if section == "chorus" else "look",
                slot=str(song_n),
                look=section,
                act=str(song_n),
                scene=section,
                beat="A",
                set=str(song_n),
                moment=section,
                shot=str(song_n),
            )
            add(
                kind="store-cue",
                command=f'Store Cue {cue_id} Sequence 99 /o',
                purpose=f"Cue for {label}",
                expert_says=(
                    f"Cue density {s.cue_density!r} → {len(sections)} cues per song."
                ),
                risk_tier="DESTRUCTIVE",
                cue_id=cue_id,
                label=label,
                song=song_n,
                section=section,
            )

    # 9. Per-section worlds — only when scope is per-section.
    if s.world_filter_scope == "per-section":
        for section in sections:
            add(
                kind="create-world",
                command=f'Store World "{section}"',
                purpose=f"Per-section world for {section}",
                expert_says=(
                    "World per song-section enables scoped programming."
                ),
                risk_tier="DESTRUCTIVE",
                world_name=section,
            )

    return plan


__all__ = ["build_plan_for"]
