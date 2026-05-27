"""Dispatcher — route plan + domain to the appropriate rule list."""

from __future__ import annotations

from typing import Callable

from src.expert_lint import (
    busking_rules,
    layout_rules,
    macro_rules,
    preset_rules,
    show_rules,
)
from src.expert_lint.types import Domain, Violation

_RuleFn = Callable[[dict, dict | None], list[Violation]]

_DOMAIN_MODULES = {
    "macro": macro_rules,
    "busking": busking_rules,
    "show": show_rules,
    "preset": preset_rules,
    "layout": layout_rules,
}


def _rules_for(domain: Domain) -> list[_RuleFn]:
    if domain not in _DOMAIN_MODULES:
        raise ValueError(f"unknown domain: {domain!r}")
    mod = _DOMAIN_MODULES[domain]
    return [getattr(mod, name) for name in mod.__all__ if name.startswith("check_")]


def _cross_cutting(plan: dict, domain: Domain) -> list[Violation]:
    """§C.6 — domain-agnostic conventions."""
    out: list[Violation] = []
    for step in plan.get("steps", []):
        if not step.get("purpose"):
            out.append(Violation(
                rule_id="CROSSCUT-PURPOSE-001",
                severity="advice",
                domain=domain,
                target=f"step:{step.get('order', '?')}",
                expert_says="Plan step has empty purpose field",
                fix_suggestion="Add a one-line `purpose` describing why this step exists",
            ))
    return out


def expert_lint(
    plan: dict, *, domain: Domain, context: dict | None = None
) -> list[Violation]:
    """Run all rules in `domain` (plus cross-cutting rules) and return findings."""
    findings: list[Violation] = []
    for fn in _rules_for(domain):
        findings.extend(fn(plan, context))
    findings.extend(_cross_cutting(plan, domain))
    return findings


__all__ = ["expert_lint"]
