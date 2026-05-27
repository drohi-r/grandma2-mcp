"""Layout expert-lint rules (LAYOUT-*).

Plan shape:

    {"kind": "layout",
     "screen": int,
     "template": str | None,
     "content": [{
         "kind": "group"|"preset"|"executor"|"macro"|"label"|"image"|"fader",
         "target": str | int,
         "label": str | None,
         "grid_x": int, "grid_y": int,
         "width": int, "height": int,
         "role": str (optional, for template requirements),
     }, ...],
     "screen_native_resolution": (width_px, height_px),
     "cell_size": (cell_w, cell_h)}
"""

from __future__ import annotations

from src.expert_lint.types import Violation


_TEMPLATE_REQUIREMENTS: dict[str, set[str]] = {
    "busking-master": {"intensity", "color", "fx", "specials"},
    "preset-access": {"color-preset-bank", "position-preset-bank"},
    "executor-monitor": {"executor-row"},
    "macro-page": {"macro-grid"},
    "programmer-view": {"selection-row", "attribute-grid"},
    "troubleshoot-view": {"diagnostic-readouts"},
}


def _content(plan: dict) -> list[dict]:
    return plan.get("content", [])


def _cell_rect(c: dict) -> tuple[int, int, int, int]:
    """Return (x0, y0, x1, y1) in grid coordinates (exclusive on x1, y1)."""
    x0 = c.get("grid_x", 0)
    y0 = c.get("grid_y", 0)
    w = max(1, c.get("width", 1))
    h = max(1, c.get("height", 1))
    return (x0, y0, x0 + w, y0 + h)


# REQ-001
def check_req_001_required_content_missing(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """LAYOUT-REQ-001 (error): template requires content of role X but layout lacks it."""
    template = plan.get("template")
    if template is None or template not in _TEMPLATE_REQUIREMENTS:
        return []
    required_roles = _TEMPLATE_REQUIREMENTS[template]
    present_roles = {c.get("role") for c in _content(plan)}
    missing = required_roles - present_roles
    if not missing:
        return []
    return [Violation(
        rule_id="LAYOUT-REQ-001",
        severity="error",
        domain="layout",
        target=f"template:{template}",
        expert_says=(
            f"Template {template!r} requires roles {sorted(required_roles)}; "
            f"missing {sorted(missing)}"
        ),
        fix_suggestion="Add the missing required content per the template spec",
    )]


# COLLIDE-001
def check_collide_001_overlap(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """LAYOUT-COLLIDE-001 (error): two content items overlap on the grid."""
    items = _content(plan)
    out: list[Violation] = []
    for i, a in enumerate(items):
        ax0, ay0, ax1, ay1 = _cell_rect(a)
        for b in items[i + 1:]:
            bx0, by0, bx1, by1 = _cell_rect(b)
            # axis-aligned rectangle overlap test
            if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                out.append(Violation(
                    rule_id="LAYOUT-COLLIDE-001",
                    severity="error",
                    domain="layout",
                    target=f"content:{a.get('target')}-vs-{b.get('target')}",
                    expert_says=(
                        f"Content {a.get('target')!r} and {b.get('target')!r} overlap on grid"
                    ),
                    fix_suggestion="Re-place one or both items",
                ))
    return out


# DANGLE-001
def check_dangle_001_target_missing(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """LAYOUT-DANGLE-001 (error): content references a non-existent target."""
    existing = (context or {}).get("existing_executors")
    if existing is None:
        # Without context we can't evaluate
        return []
    out: list[Violation] = []
    for c in _content(plan):
        if c.get("kind") != "executor":
            continue
        target = str(c.get("target", ""))
        if target not in existing:
            out.append(Violation(
                rule_id="LAYOUT-DANGLE-001",
                severity="error",
                domain="layout",
                target=f"content:{target}",
                expert_says=f"Layout cell references non-existent executor {target!r}",
                fix_suggestion="Either create the target or remove the layout entry",
            ))
    return out


# LABEL-001
def check_label_001_cell_label_missing(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """LAYOUT-LABEL-001 (warning): cell has no label and target is cryptic."""
    out: list[Violation] = []
    for c in _content(plan):
        label = (c.get("label") or "").strip()
        target = str(c.get("target", ""))
        # Numeric or short targets without a label are cryptic
        if label:
            continue
        is_cryptic = target.isdigit() or len(target) <= 3
        if is_cryptic:
            out.append(Violation(
                rule_id="LAYOUT-LABEL-001",
                severity="warning",
                domain="layout",
                target=f"content:{target}",
                expert_says=f"Cell with target {target!r} has no label",
                fix_suggestion="Add an explicit label",
            ))
    return out


# SIZE-001
def check_size_001_exceeds_screen(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """LAYOUT-SIZE-001 (warning): content exceeds screen native resolution."""
    sw, sh = plan.get("screen_native_resolution", (1920, 1080))
    cw, ch = plan.get("cell_size", (100, 50))
    out: list[Violation] = []
    for c in _content(plan):
        x0, y0, x1, y1 = _cell_rect(c)
        right_px = x1 * cw
        bottom_px = y1 * ch
        if right_px > sw or bottom_px > sh:
            out.append(Violation(
                rule_id="LAYOUT-SIZE-001",
                severity="warning",
                domain="layout",
                target=f"content:{c.get('target')}",
                expert_says=(
                    f"Cell at ({x0},{y0}) extends to ({right_px}, {bottom_px}) "
                    f"px — exceeds screen {sw}x{sh}"
                ),
                fix_suggestion="Resize or split into a second screen",
            ))
    return out


# DENSE-001
def check_dense_001_density_high(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """LAYOUT-DENSE-001 (advice): >70% of screen real estate used."""
    sw, sh = plan.get("screen_native_resolution", (1920, 1080))
    cw, ch = plan.get("cell_size", (100, 50))
    total_px = sw * sh
    used_px = 0
    for c in _content(plan):
        x0, y0, x1, y1 = _cell_rect(c)
        used_px += (x1 - x0) * (y1 - y0) * cw * ch
    if used_px / max(1, total_px) <= 0.70:
        return []
    return [Violation(
        rule_id="LAYOUT-DENSE-001",
        severity="advice",
        domain="layout",
        target="layout",
        expert_says=(
            f"Layout uses {used_px / total_px:.0%} of screen real estate — leaves little room for status/info"
        ),
        fix_suggestion="Reduce density or split into multiple screens",
    )]


# COVER-001 (layout)
def check_cover_001_executor_monitor_underused(
    plan: dict, context: dict | None = None
) -> list[Violation]:
    """LAYOUT-COVER-001 (advice): executor-monitor template covers <50% of active executors."""
    if plan.get("template") != "executor-monitor":
        return []
    active = set((context or {}).get("active_executors", []))
    if not active:
        return []
    shown = {str(c.get("target")) for c in _content(plan) if c.get("kind") == "executor"}
    coverage = len(shown & active) / len(active)
    if coverage >= 0.50:
        return []
    return [Violation(
        rule_id="LAYOUT-COVER-001",
        severity="advice",
        domain="layout",
        target="layout",
        expert_says=(
            f"executor-monitor template shows {coverage:.0%} of active executors"
        ),
        fix_suggestion="Expand layout to cover more executors",
    )]


__all__ = [
    "check_req_001_required_content_missing",
    "check_collide_001_overlap",
    "check_dangle_001_target_missing",
    "check_label_001_cell_label_missing",
    "check_size_001_exceeds_screen",
    "check_dense_001_density_high",
    "check_cover_001_executor_monitor_underused",
]
