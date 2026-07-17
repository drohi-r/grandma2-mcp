"""plugin_manifests.py — declarative requirement manifests for console plugins.

Pure module (no I/O). A manifest declares what a plugin needs before it can
run safely — free pool ranges, existing groups, selection discipline — and
what outputs it produces (so callers can diff pools after the run).

Adding support for a new plugin means registering a manifest here (or passing
an ad-hoc manifest dict to the run_preset_plugin tool), not writing code.
"""

from __future__ import annotations

from typing import TypedDict


class PluginManifest(TypedDict, total=False):
    """Declarative requirements + outputs for one console plugin."""

    name: str                       # human name; matched against plugin pool
    description: str
    required_groups: list[int]      # group pool IDs that must exist
    pool_ranges: dict[str, list[int]]   # pool type → [start, end] that must be FREE
    selection: str                  # "type-ordered" | "none"
    outputs: list[str]              # pool types the plugin writes (diffed after run)
    notes: str


BUILTIN_MANIFESTS: dict[str, PluginManifest] = {
    "auto-layout-color-picker": {
        "name": "Auto Layout Color Picker",
        "description": (
            "Egidius/leonreucher auto-layout color picker — builds a color "
            "layout with macros, sequences, and copied color images from "
            "fixture groups."
        ),
        "required_groups": [],          # operator supplies grpNum groups per show
        "pool_ranges": {
            "macro": [900, 999],
            "sequence": [900, 999],
            "image": [900, 999],
        },
        "selection": "type-ordered",
        "outputs": ["macro", "sequence", "image", "layout"],
        "notes": (
            "Fixtures must be selected in fixture-type order before the run; "
            "pool ranges are the plugin defaults and can be overridden per show."
        ),
    },
}


def get_manifest(key: str) -> PluginManifest | None:
    """Fetch a builtin manifest by registry key or (case-insensitive) name."""
    if key in BUILTIN_MANIFESTS:
        return dict(BUILTIN_MANIFESTS[key])
    lowered = key.strip().lower()
    for manifest in BUILTIN_MANIFESTS.values():
        if manifest.get("name", "").lower() == lowered:
            return dict(manifest)
    return None


def merge_manifest(
    base: PluginManifest | None, overrides: dict | None
) -> PluginManifest:
    """Overlay ad-hoc overrides onto a base manifest (overrides win)."""
    merged: dict = dict(base or {})
    for k, v in (overrides or {}).items():
        merged[k] = v
    return merged  # type: ignore[return-value]


def occupied_ids_in_range(ids: list[int], start: int, end: int) -> list[int]:
    """IDs from a pool listing that fall inside [start, end]."""
    return sorted(i for i in ids if start <= i <= end)


__all__ = [
    "PluginManifest",
    "BUILTIN_MANIFESTS",
    "get_manifest",
    "merge_manifest",
    "occupied_ids_in_range",
]
