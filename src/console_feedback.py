"""
Console feedback classification — pure functions, no I/O.

grandMA2 reports a rejected command inside the Telnet text (``Error #66 CANNOT
ASSIGN``), not as a transport failure. Tools pass that text through as
``raw_response``, so without this module a rejected command looks identical to
an accepted one. ``annotate_tool_result`` gives every tool reply a uniform
``ok`` field plus structured ``console_errors`` so callers (LLMs, the agent
executor, telemetry) can tell the difference.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# "Error #66 CANNOT ASSIGN", "Error #1: UNKNOWN COMMAND", "ERROR #72 : COMMAND NOT EXECUTED"
_NUMBERED_ERROR_RE = re.compile(
    r"\berror\s*#\s*(\d+)\s*:?\s*([A-Z][A-Z0-9 ./'_-]*[A-Z0-9])?",
    re.IGNORECASE,
)

# Unnumbered rejections MA2 prints in upper case. Matched case-sensitively so
# lower-case user labels ("unknown command test") don't trip them.
_BARE_ERROR_PHRASES: dict[str, str] = {
    "UNKNOWN COMMAND": "syntax",
    "ILLEGAL COMMAND": "syntax",
    "ILLEGAL CHARACTER": "syntax",
    "COMMAND NOT EXECUTED": "rejected",
    "CANNOT ASSIGN": "rejected",
    "FILE NOT FOUND": "not_found",
}

# Informational — the command ran but matched nothing. Not a failure for reads.
_WARNING_PHRASES = ("NO OBJECTS FOUND",)

_CODE_KINDS: dict[int, str] = {1: "syntax", 72: "rejected"}

# Keys under which tools return raw console text (a string, or a list of strings
# paired with "commands_sent" for multi-command tools).
CONSOLE_TEXT_KEYS = ("raw_response", "response")
CONSOLE_TEXT_LIST_KEYS = ("raw_responses", "responses")

# A console pop-up waiting for an answer: "[1]: Ok   2 : Cancel"
_POPUP_OPTION_RE = re.compile(
    r"\[?(\d)\]?\s*:\s*(Ok|Cancel|Yes|No|Overwrite|Merge|Abort|Create|Retry|Ignore|Replace|New)\b",
    re.IGNORECASE,
)

_DEFAULT_MAX_REPLY_CHARS = 20000


def _max_reply_chars() -> int:
    try:
        return max(1000, int(os.getenv("GMA_MAX_REPLY_CHARS", _DEFAULT_MAX_REPLY_CHARS)))
    except ValueError:
        return _DEFAULT_MAX_REPLY_CHARS


def find_pending_popup(raw: str) -> dict | None:
    """Return the open pop-up's options when the reply ends waiting on one."""
    if not raw:
        return None
    text = strip_ansi(raw)
    options = {int(m.group(1)): m.group(2).title() for m in _POPUP_OPTION_RE.finditer(text)}
    if len(options) < 2:
        return None
    first = _POPUP_OPTION_RE.search(text)
    lead = text[: first.start()].strip().splitlines() if first else []
    return {
        "text": " ".join(lead[-2:])[:200],
        "options": [{"choice": n, "label": label} for n, label in sorted(options.items())],
    }


@dataclass(frozen=True)
class ConsoleError:
    code: int | None
    message: str
    kind: str  # "syntax" | "rejected" | "not_found"

    def describe(self) -> str:
        prefix = f"Error #{self.code}" if self.code is not None else "Error"
        return f"{prefix} {self.message}".strip()


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _without_echo(text: str, command: str | None) -> str:
    # The console echoes the command; a label like "CANNOT ASSIGN" must not count.
    if command:
        text = text.replace(command, " ")
    return text


def find_console_errors(raw: str, command: str | None = None) -> list[ConsoleError]:
    """Return every console rejection found in *raw* Telnet text."""
    if not raw:
        return []
    text = _without_echo(strip_ansi(raw), command)
    errors: list[ConsoleError] = []
    covered: list[str] = []
    for m in _NUMBERED_ERROR_RE.finditer(text):
        code = int(m.group(1))
        message = (m.group(2) or "").strip().upper()
        kind = _CODE_KINDS.get(code) or next(
            (k for phrase, k in _BARE_ERROR_PHRASES.items() if phrase in message), "rejected"
        )
        errors.append(ConsoleError(code=code, message=message, kind=kind))
        covered.append(message)
    for phrase, kind in _BARE_ERROR_PHRASES.items():
        if phrase in text and not any(phrase in msg for msg in covered):
            errors.append(ConsoleError(code=None, message=phrase, kind=kind))
    return errors


def find_console_warnings(raw: str, command: str | None = None) -> list[str]:
    if not raw:
        return []
    text = _without_echo(strip_ansi(raw), command)
    return [phrase for phrase in _WARNING_PHRASES if phrase in text]


def annotate_tool_result(
    result: str, transport_warnings: list[str] | None = None
) -> tuple[str, list[ConsoleError]]:
    """Add ``ok`` plus ``console_errors``/``console_warnings``/``transport_warnings`` to a JSON reply.

    Non-JSON and non-object replies are returned unchanged. Returns the new
    reply and the console errors found (empty when the console accepted it).
    """
    try:
        data = json.loads(result)
    except (TypeError, ValueError):
        return result, []
    if not isinstance(data, dict):
        return result, []

    command = data.get("command_sent") if isinstance(data.get("command_sent"), str) else None
    errors: list[ConsoleError] = []
    warnings: list[str] = []
    popup: dict | None = None
    texts: list[tuple[str, str | None]] = []
    for key in CONSOLE_TEXT_KEYS:
        value = data.get(key)
        if isinstance(value, str):
            data[key] = value = strip_ansi(value)
            texts.append((value, command))
    sent = data.get("commands_sent") if isinstance(data.get("commands_sent"), list) else []
    for key in CONSOLE_TEXT_LIST_KEYS:
        values = data.get(key)
        if isinstance(values, list):
            data[key] = values = [strip_ansi(v) if isinstance(v, str) else v for v in values]
            for i, v in enumerate(values):
                if isinstance(v, str):
                    texts.append((v, sent[i] if i < len(sent) and isinstance(sent[i], str) else None))
    for text, cmd in texts:
        errors.extend(find_console_errors(text, cmd))
        warnings.extend(w for w in find_console_warnings(text, cmd) if w not in warnings)
    if texts:
        popup = find_pending_popup(texts[-1][0])

    if popup:
        data["ok"] = False
        data["pending_popup"] = popup
        if not data.get("error"):
            choices = ", ".join(f"{o['choice']}={o['label']}" for o in popup["options"])
            data["error"] = (
                f"Console is waiting on a pop-up ({choices}); nothing else will run until it "
                "is answered. Use answer_console_popup(choice=N)."
            )
    if errors:
        data["ok"] = False
        data["console_errors"] = [asdict(e) for e in errors]
        if not data.get("error"):
            data["error"] = "Console rejected the command: " + "; ".join(e.describe() for e in errors)
    elif "ok" not in data and not popup:
        data["ok"] = not (data.get("blocked") is True or bool(data.get("error")))
    if warnings:
        data["console_warnings"] = warnings
    limit = _max_reply_chars()
    for key in CONSOLE_TEXT_KEYS:
        value = data.get(key)
        if isinstance(value, str) and len(value) > limit:
            data[key] = value[:limit] + f"\n… [truncated {len(value) - limit} of {len(value)} chars]"
            data[f"{key}_truncated"] = True
            data[f"{key}_chars"] = len(value)
    if transport_warnings:
        data["transport_warnings"] = list(transport_warnings)

    return json.dumps(data, indent=2, default=str), errors
