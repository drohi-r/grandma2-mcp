"""Expert-lint types — Violation dataclass + typed literals.

Pure module; no I/O, no project-internal imports beyond stdlib.
Hygiene invariant in tests/test_architecture_hygiene.py enforces that.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["advice", "warning", "error"]
Domain = Literal["macro", "busking", "show", "preset", "layout"]


@dataclass(frozen=True)
class Violation:
    """A single lint finding."""

    rule_id: str          # e.g. "MACRO-JT-001"
    severity: Severity
    domain: Domain
    target: str           # plan step identifier, e.g. "step:3" or "executor:1.1.1"
    expert_says: str      # one-line justification
    fix_suggestion: str   # one-line remediation hint


__all__ = ["Violation", "Severity", "Domain"]
