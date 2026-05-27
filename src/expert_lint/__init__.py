"""src.expert_lint — pure-function rule engine for plan validation.

Public API: ``expert_lint(plan, domain, context=None) -> list[Violation]``

Domains: ``macro``, ``busking``, ``show``, ``preset``, ``layout``.

The rule engine is pure — no network I/O, no event-loop primitives, no
imports from the project's transport / navigation / server layers.
Architecture-hygiene test ``TestExpertLintPurity`` enforces this.
"""

from src.expert_lint.dispatcher import expert_lint
from src.expert_lint.types import Domain, Severity, Violation

# Sub-modules are intentionally importable so the dispatcher can introspect
# their __all__ exports. Users should call expert_lint() rather than reaching
# into the rule modules directly.
from src.expert_lint import (  # noqa: F401 — re-export for introspection
    busking_rules,
    layout_rules,
    macro_rules,
    preset_rules,
    show_rules,
)

__all__ = ["expert_lint", "Violation", "Severity", "Domain"]
