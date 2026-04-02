"""
pool_name_index.py — In-memory pool name/ID index for zero-cost object resolution.

Provides ObjectRef (a quoted MA2 command token) and PoolNameIndex (the index
populated during ConsoleStateSnapshot hydration). Agents can resolve any pool
object to a ready-to-use command token without extra telnet round-trips.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .commands.helpers import quote_name

# Pool types that support a preset_type sub-key (Preset pools 1-9)
_PRESET_POOL_TYPES = frozenset({"Preset", "preset"})


@dataclass
class ObjectRef:
    """
    A fully-resolved reference to a grandMA2 pool object.

    `token` is the correctly-quoted MA2 command token ready for command strings,
    e.g. 'Group "Front*Wash"' or 'Group 3' or 'Preset 4.2'.
    """

    object_type: str
    name: str | None
    id: int | None
    token: str
    match_mode: str = "literal"    # "literal" (Rule A) or "wildcard" (Rule B)
    preset_type: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "name": self.name,
            "id": self.id,
            "token": self.token,
            "match_mode": self.match_mode,
            "preset_type": self.preset_type,
        }


class PoolNameIndex:
    """
    In-memory name/ID registry for all 16 MA2 pool types.

    Populated by ConsoleStateHydrator once per session start.
    All queries are O(n) scans over small lists; no indexing needed.
    """

    def __init__(self) -> None:
        # Key: (object_type_lower, preset_type | None)
        # Value: list of {"name": str, "id": int, "object_type": str, "preset_type": int | None}
        self._store: dict[tuple[str, int | None], list[dict[str, Any]]] = {}

    def add_entry(
        self,
        object_type: str,
        name: str,
        id: int,
        preset_type: int | None = None,
    ) -> None:
        key = (object_type.lower(), preset_type)
        self._store.setdefault(key, []).append({
            "name": name,
            "id": id,
            "object_type": object_type,
            "preset_type": preset_type,
        })

    def all_entries(
        self,
        object_type: str,
        preset_type: int | None = None,
    ) -> list[dict[str, Any]]:
        return list(self._store.get((object_type.lower(), preset_type), []))

    def names_for_type(
        self,
        object_type: str,
        preset_type: int | None = None,
    ) -> list[str]:
        """Return a list of names for all entries of a given pool type."""
        return [e["name"] for e in self.all_entries(object_type, preset_type=preset_type)]

    def indexed_types(self) -> list[str]:
        """Return unique pool type names that have at least one entry."""
        seen: set[str] = set()
        result: list[str] = []
        for (ot, _) in self._store:
            if ot not in seen:
                seen.add(ot)
                result.append(ot)
        return sorted(result)

    def stats(self) -> dict[str, int]:
        """Return entry counts per pool type."""
        out: dict[str, int] = {}
        for (ot, pt), entries in self._store.items():
            label = f"{ot}" + (f":{pt}" if pt else "")
            out[label] = out.get(label, 0) + len(entries)
        return out

    def resolve(
        self,
        object_type: str,
        name: str | None = None,
        id: int | None = None,
        match_mode: str = "literal",
        preset_type: int | None = None,
    ) -> ObjectRef:
        """
        Resolve an object to an ObjectRef with a correctly-quoted token.

        Priority: if id is provided, look up by id and return with name filled in.
        If name is provided, look up by name (exact match, case-insensitive).
        If neither, return a bare type token.
        """
        entries = self.all_entries(object_type, preset_type)

        resolved_name: str | None = name
        resolved_id: int | None = id

        if id is not None and id > 0:
            match = next((e for e in entries if e["id"] == id), None)
            if match:
                resolved_name = match["name"]
        elif name:
            if match_mode == "wildcard":
                import fnmatch as _fnmatch
                wm = [e for e in entries if _fnmatch.fnmatch(e["name"], name)]
                if len(wm) == 1:
                    resolved_name = wm[0]["name"]
                    resolved_id   = wm[0]["id"]
                # 0 or >1 matches → leave id=None, keep name as pattern
            else:
                match = next((e for e in entries if e["name"].lower() == name.lower()), None)
                if match:
                    resolved_id = match["id"]

        token = _build_token(object_type, resolved_name, resolved_id, match_mode, preset_type)
        return ObjectRef(
            object_type=object_type,
            name=resolved_name,
            id=resolved_id,
            token=token,
            match_mode=match_mode,
            preset_type=preset_type,
        )


    def resolve_wildcard(
        self,
        object_type: str,
        pattern: str,
        preset_type: int | None = None,
    ) -> list[ObjectRef]:
        """Return an ObjectRef for every pool entry whose name matches a fnmatch pattern."""
        import fnmatch as _fnmatch
        entries = self.all_entries(object_type, preset_type)
        results = []
        for e in entries:
            if _fnmatch.fnmatch(e["name"], pattern):
                token = _build_token(object_type, e["name"], e["id"], "wildcard", preset_type)
                results.append(ObjectRef(
                    object_type=object_type,
                    name=e["name"],
                    id=e["id"],
                    token=token,
                    match_mode="wildcard",
                    preset_type=preset_type,
                ))
        return results


def _build_token(
    object_type: str,
    name: str | None,
    id: int | None,
    match_mode: str,
    preset_type: int | None,
) -> str:
    """Build the MA2 command token for an object reference."""
    if object_type.lower() == "preset" and preset_type is not None and id is not None:
        return f"preset {preset_type}.{id}"
    if name:
        quoted = quote_name(name, match_mode=match_mode)
        return f"{object_type} {quoted}"
    if id is not None and id > 0:
        return f"{object_type} {id}"
    return object_type
