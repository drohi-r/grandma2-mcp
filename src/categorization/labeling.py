"""Auto-generate human-readable category labels from cluster contents.

Inspects the dominant structural features of each cluster and maps them
to descriptive names like "Playback Control" or "Inspection & Queries".
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from numpy.typing import NDArray

from src.categorization.features import ToolFeatures

# Priority rules: (condition_fn, label)
# condition_fn receives (tools_in_cluster) and returns True/False.

_VERB_LABEL_MAP: list[tuple[list[str], str]] = [
    (["list", "info"], "Inspection & Queries"),
    (["go", "goto", "release"], "Playback Control"),
    (["store"], "Programming & Storage"),
    (["select", "highlight", "clear"], "Selection & Programmer"),
    (["assign", "label"], "Assignment & Labeling"),
    (["delete", "copy", "move", "edit", "remove"], "Object Editing"),
    (["import", "export"], "Import & Export"),
    (["park"], "Fixture Parking"),
]

_MODULE_LABEL_MAP: list[tuple[list[str], str]] = [
    (["playback"], "Playback Control"),
    (["info"], "Inspection & Queries"),
    (["store"], "Programming & Storage"),
    (["selection"], "Selection & Programmer"),
    (["assignment", "labeling"], "Assignment & Labeling"),
    (["edit"], "Object Editing"),
    (["values"], "Value Setting"),
    (["variables"], "Variable Management"),
    (["importexport"], "Import & Export"),
    (["park"], "Fixture Parking"),
    (["navigation"], "Navigation"),
    (["fixtures", "groups"], "Fixture Management"),
    (["cues", "executors"], "Cue & Executor Control"),
    (["presets"], "Preset Management"),
    (["matricks"], "MAtricks & Selection"),
    (["macro"], "Macro Execution"),
    (["call"], "Calling & Recall"),
]


def generate_labels(
    tools: list[ToolFeatures],
    labels: NDArray[np.int64],
) -> dict[int, str]:
    """Generate a human-readable label for each cluster.

    Parameters
    ----------
    tools : list of ToolFeatures (same order as *labels*)
    labels : (n,) cluster assignments from K-Means

    Returns
    -------
    dict mapping cluster id → label string
    """
    unique_labels = sorted(set(int(lbl) for lbl in labels))
    cluster_labels: dict[int, str] = {}
    used_labels: set[str] = set()

    for cid in unique_labels:
        cluster_tools = [t for t, lbl in zip(tools, labels, strict=False) if int(lbl) == cid]
        label = _label_for_cluster(cluster_tools)

        # Deduplicate
        if label in used_labels:
            label = _disambiguate(label, cluster_tools, used_labels)
        used_labels.add(label)
        cluster_labels[cid] = label

    return cluster_labels


def dominant_features(tools: list[ToolFeatures]) -> dict[str, list[str]]:
    """Return the most common verbs and modules for a set of tools."""
    verb_counter: Counter[str] = Counter()
    module_counter: Counter[str] = Counter()
    for t in tools:
        verb_counter.update(t.action_verbs)
        module_counter.update(t.command_modules)
    return {
        "verbs": [v for v, _ in verb_counter.most_common(5)],
        "modules": [m for m, _ in module_counter.most_common(5)],
    }


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _label_for_cluster(tools: list[ToolFeatures]) -> str:
    n = len(tools)
    if n == 0:
        return "Empty"

    # Collect feature distributions
    verb_counter: Counter[str] = Counter()
    module_counter: Counter[str] = Counter()
    risk_counter: Counter[str] = Counter()

    for t in tools:
        verb_counter.update(t.action_verbs)
        module_counter.update(t.command_modules)
        risk_counter[t.risk_tier] += 1

    # Check DESTRUCTIVE dominance first — avoids lumping destructive tools
    # under "Inspection & Queries" when they happen to also have read verbs
    if risk_counter.get("DESTRUCTIVE", 0) / n > 0.5:
        # Try write-oriented verb labels only (skip "Inspection & Queries")
        for verbs, label in _VERB_LABEL_MAP:
            if label == "Inspection & Queries":
                continue
            count = sum(verb_counter.get(v, 0) for v in verbs)
            if count > 0 and count / n >= 0.4:
                return label
        return "Destructive Operations"

    # Check risk-tier dominance
    if risk_counter.get("SAFE_READ", 0) / n > 0.6:
        # Mostly read-only — try module specificity before generic label
        for modules, label in _MODULE_LABEL_MAP:
            count = sum(module_counter.get(m, 0) for m in modules)
            if count > 0 and count / n >= 0.4:
                return label
        return "Inspection & Queries"

    # Check verb dominance
    for verbs, label in _VERB_LABEL_MAP:
        count = sum(verb_counter.get(v, 0) for v in verbs)
        # If these verbs appear in >50% of tools
        if count > 0 and count / n >= 0.5:
            return label

    # Check module dominance
    for modules, label in _MODULE_LABEL_MAP:
        count = sum(module_counter.get(m, 0) for m in modules)
        if count > 0 and count / n >= 0.4:
            return label

    # Navigation tools
    nav_count = sum(1 for t in tools if t.navigates)
    if nav_count / n > 0.5:
        return "Navigation"

    # Fallback: most common verb + "Operations"
    if verb_counter:
        top_verb = verb_counter.most_common(1)[0][0]
        return f"{top_verb.title()} Operations"

    # Last resort
    return "General Tools"


def _disambiguate(
    label: str,
    tools: list[ToolFeatures],
    used: set[str],
) -> str:
    """Append a distinguishing suffix to avoid label collisions."""
    # Try adding the most common module
    module_counter: Counter[str] = Counter()
    for t in tools:
        module_counter.update(t.command_modules)
    if module_counter:
        top_mod = module_counter.most_common(1)[0][0]
        candidate = f"{label} ({top_mod.title()})"
        if candidate not in used:
            return candidate

    # Try most common risk tier
    risk_counter: Counter[str] = Counter()
    for t in tools:
        risk_counter[t.risk_tier] += 1
    top_risk = risk_counter.most_common(1)[0][0]
    candidate = f"{label} [{top_risk}]"
    if candidate not in used:
        return candidate

    # Number suffix
    suffix = 2
    while f"{label} {suffix}" in used:
        suffix += 1
    return f"{label} {suffix}"
