"""src/expert_lint/types — Violation dataclass + typed literals.

Per plan §Task 2 steps 2.1-2.4.
"""

from src.expert_lint.types import Domain, Severity, Violation


def test_violation_required_fields():
    v = Violation(
        rule_id="MACRO-JT-001",
        severity="error",
        domain="macro",
        target="step:3",
        expert_says="Jump target line number does not exist in the macro",
        fix_suggestion="Recompute target after insertion",
    )
    assert v.rule_id == "MACRO-JT-001"
    assert v.severity == "error"
    assert v.domain == "macro"
    assert v.target == "step:3"


def test_severity_literal_values():
    valid: list[Severity] = ["advice", "warning", "error"]
    assert sorted(valid) == ["advice", "error", "warning"]


def test_domain_literal_values():
    valid: list[Domain] = ["macro", "busking", "show", "preset", "layout"]
    assert "macro" in valid
    assert "busking" in valid
    assert "show" in valid
    assert "preset" in valid
    assert "layout" in valid


def test_violation_is_frozen():
    """Violation is immutable — protects callers that pass findings into reports."""
    import pytest
    v = Violation(
        rule_id="X", severity="advice", domain="macro",
        target="t", expert_says="why", fix_suggestion="fix",
    )
    with pytest.raises((AttributeError, Exception)):  # frozen dataclass raises FrozenInstanceError
        v.severity = "error"  # type: ignore[misc]
