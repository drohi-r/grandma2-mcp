"""Layout expert-lint rules (LAYOUT-*)."""

from src.expert_lint.layout_rules import (
    check_collide_001_overlap,
    check_cover_001_executor_monitor_underused,
    check_dangle_001_target_missing,
    check_dense_001_density_high,
    check_label_001_cell_label_missing,
    check_req_001_required_content_missing,
    check_size_001_exceeds_screen,
)


def _layout(**overrides) -> dict:
    base = {
        "kind": "layout",
        "screen": 1,
        "template": None,
        "content": [],
        "screen_native_resolution": (1920, 1080),
        "cell_size": (100, 50),
    }
    base.update(overrides)
    return base


# REQ-001
def test_req_001_clean_when_required_content_present():
    plan = _layout(template="busking-master", content=[
        {"kind": "executor", "target": "1.1.1", "label": "Wash Int", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1, "role": "intensity"},
        {"kind": "executor", "target": "1.1.2", "label": "Color", "grid_x": 1, "grid_y": 0, "width": 1, "height": 1, "role": "color"},
        {"kind": "executor", "target": "1.1.3", "label": "FX", "grid_x": 2, "grid_y": 0, "width": 1, "height": 1, "role": "fx"},
        {"kind": "executor", "target": "1.1.4", "label": "Specials", "grid_x": 3, "grid_y": 0, "width": 1, "height": 1, "role": "specials"},
    ])
    assert check_req_001_required_content_missing(plan, None) == []


def test_req_001_flags_missing_required_content():
    plan = _layout(template="busking-master", content=[
        {"kind": "executor", "target": "1.1.1", "label": "Wash Int", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1, "role": "intensity"},
    ])
    findings = check_req_001_required_content_missing(plan, None)
    assert any(v.rule_id == "LAYOUT-REQ-001" for v in findings)


# COLLIDE-001
def test_collide_001_clean_when_no_overlap():
    plan = _layout(content=[
        {"kind": "executor", "target": "1.1.1", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1},
        {"kind": "executor", "target": "1.1.2", "grid_x": 1, "grid_y": 0, "width": 1, "height": 1},
    ])
    assert check_collide_001_overlap(plan, None) == []


def test_collide_001_flags_overlap():
    plan = _layout(content=[
        {"kind": "executor", "target": "1.1.1", "grid_x": 0, "grid_y": 0, "width": 2, "height": 1},
        {"kind": "executor", "target": "1.1.2", "grid_x": 1, "grid_y": 0, "width": 1, "height": 1},
    ])
    findings = check_collide_001_overlap(plan, None)
    assert any(v.rule_id == "LAYOUT-COLLIDE-001" and v.severity == "error" for v in findings)


# DANGLE-001
def test_dangle_001_clean_when_targets_exist():
    plan = _layout(content=[
        {"kind": "executor", "target": "1.1.1", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1},
    ])
    ctx = {"existing_executors": {"1.1.1", "1.1.2"}}
    assert check_dangle_001_target_missing(plan, ctx) == []


def test_dangle_001_flags_missing_target():
    plan = _layout(content=[
        {"kind": "executor", "target": "9.9.9", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1},
    ])
    ctx = {"existing_executors": {"1.1.1", "1.1.2"}}
    findings = check_dangle_001_target_missing(plan, ctx)
    assert any(v.rule_id == "LAYOUT-DANGLE-001" for v in findings)


# LABEL-001
def test_layout_label_001_clean_when_labels_present():
    plan = _layout(content=[
        {"kind": "group", "target": 14, "label": "Wash Front", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1},
    ])
    assert check_label_001_cell_label_missing(plan, None) == []


def test_layout_label_001_flags_cryptic_target_no_label():
    plan = _layout(content=[
        {"kind": "group", "target": 14, "label": "", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1},
    ])
    findings = check_label_001_cell_label_missing(plan, None)
    assert any(v.rule_id == "LAYOUT-LABEL-001" for v in findings)


# SIZE-001
def test_size_001_clean_when_within_resolution():
    plan = _layout(content=[
        {"kind": "executor", "target": "1.1.1", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1},
    ])
    assert check_size_001_exceeds_screen(plan, None) == []


def test_size_001_flags_exceeds_screen():
    # Cells are 100x50; screen is 1920x1080. A cell at grid_x=20 (2000px right edge) exceeds.
    plan = _layout(content=[
        {"kind": "executor", "target": "1.1.1", "grid_x": 20, "grid_y": 0, "width": 1, "height": 1},
    ])
    findings = check_size_001_exceeds_screen(plan, None)
    assert any(v.rule_id == "LAYOUT-SIZE-001" for v in findings)


# DENSE-001
def test_dense_001_clean_when_density_low():
    # 2 cells × 100×50 = 10000 px²; screen 1920×1080 = 2073600 px²; density ~0.5%
    plan = _layout(content=[
        {"kind": "x", "target": "a", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1},
        {"kind": "x", "target": "b", "grid_x": 1, "grid_y": 0, "width": 1, "height": 1},
    ])
    assert check_dense_001_density_high(plan, None) == []


def test_dense_001_flags_high_density():
    # Many cells filling screen — density > 70%
    plan = _layout(content=[
        {"kind": "x", "target": str(i), "grid_x": i % 19, "grid_y": i // 19,
         "width": 1, "height": 1} for i in range(19 * 16)  # 304 cells * 100*50 = 1.52M of 2.07M
    ])
    findings = check_dense_001_density_high(plan, None)
    assert any(v.rule_id == "LAYOUT-DENSE-001" for v in findings)


# COVER-001 (layout)
def test_layout_cover_001_clean_when_template_not_executor_monitor():
    plan = _layout(template="busking-master")
    ctx = {"active_executors": ["1.1.1", "1.1.2", "1.1.3", "1.1.4"]}
    assert check_cover_001_executor_monitor_underused(plan, ctx) == []


def test_layout_cover_001_flags_underused_executor_monitor():
    plan = _layout(template="executor-monitor", content=[
        {"kind": "executor", "target": "1.1.1", "grid_x": 0, "grid_y": 0, "width": 1, "height": 1},
    ])
    ctx = {"active_executors": ["1.1.1", "1.1.2", "1.1.3", "1.1.4", "1.1.5"]}
    findings = check_cover_001_executor_monitor_underused(plan, ctx)
    assert any(v.rule_id == "LAYOUT-COVER-001" for v in findings)
