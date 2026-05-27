"""NL intent → MA2 macro generation.

Rule-based classifier maps high-signal keywords to a small template library.
The generated plan is shaped for the :mod:`src.expert_lint` macro domain:

    {"kind": "macro",
     "label": str,
     "lines": [{"index": int, "command": str}, ...],
     "body_xml": str}

Pure module — no I/O, no telnet imports.
"""

from __future__ import annotations

from xml.sax.saxutils import escape


def _emit_xml(label: str, lines: list[str]) -> str:
    """Render an MA2-shaped <Macro> XML body. Used for both the body_xml field
    and the MACRO-XML-001 lint check."""
    parts = [f'<Macro name="{escape(label)}">']
    for i, cmd in enumerate(lines, start=1):
        parts.append(f'  <Line nr="{i}">{escape(cmd)}</Line>')
    parts.append("</Macro>")
    return "\n".join(parts)


def _classify_intent(intent: str) -> str:
    text = intent.lower()
    if "blackout" in text or "panic" in text:
        return "panic-blackout"
    if "tap" in text and "tempo" in text:
        return "tap-tempo"
    if "song-change" in text or ("song" in text and "change" in text):
        return "song-change"
    if "park" in text and ("mover" in text or "movers" in text):
        return "park-movers"
    if "restore" in text and ("sequence" in text or "cue" in text):
        return "sequence-restore"
    if "delete" in text:
        return "delete-generic"
    return "unknown"


_TEMPLATES: dict[str, tuple[str, list[str]]] = {
    "panic-blackout": (
        "Panic Blackout",
        [
            "ClearAll",
            "BlackScreen On /noconfirm",
        ],
    ),
    "tap-tempo": (
        "Tap Tempo",
        [
            "Tap",
        ],
    ),
    "song-change": (
        "Song Change",
        [
            "Page 2",
            "Goto Executor 1.1.1 Cue 1",
            "Go Executor 1.1.1",
        ],
    ),
    "park-movers": (
        "Park Movers",
        [
            "ClearAll",
            "Select Group 2",
            "Park Selected /noconfirm",
        ],
    ),
    "sequence-restore": (
        "Sequence Restore",
        [
            "ClearAll",
            "Goto Sequence 1 Cue 1",
            "Go Sequence 1",
        ],
    ),
    "delete-generic": (
        "Delete (review before use)",
        [
            "Delete Macro 99 /noconfirm",
        ],
    ),
}


def build_macro_from_intent(
    intent: str, scope_hints: dict | None = None,
) -> dict:
    """Return a plan dict suitable for expert_lint."""
    kind = _classify_intent(intent)
    hints = scope_hints or {}

    if hints.get("force_unsafe"):
        # Intentionally produce an unsafe macro so the lint catches it
        # (no /noconfirm on Delete → MACRO-SAFETY-001).
        label = "Forced Unsafe Delete"
        lines = ["Delete Macro 99"]
    elif kind in _TEMPLATES:
        label, lines = _TEMPLATES[kind]
        lines = list(lines)  # copy so callers can't mutate the template
    else:
        label = f"Generated: {intent[:30]}".strip()
        lines = ["ClearAll"]  # safe minimum

    body_xml = _emit_xml(label, lines)
    return {
        "kind": "macro",
        "label": label,
        "lines": [{"index": i, "command": c} for i, c in enumerate(lines, start=1)],
        "body_xml": body_xml,
    }


__all__ = ["build_macro_from_intent"]
