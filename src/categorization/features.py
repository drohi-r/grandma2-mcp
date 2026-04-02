"""AST-based feature extraction from MCP tool definitions.

Parses ``src/server.py`` without importing it (avoids Telnet side-effects)
and builds a feature vector per ``@mcp.tool()``-decorated function.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


def _discover_modules(subdir: str) -> list[str]:
    """Auto-discover command submodules from ``src/commands/{subdir}/``."""
    pkg_dir = Path(__file__).resolve().parent.parent / "commands" / subdir
    if not pkg_dir.is_dir():
        return []
    return sorted(
        p.stem for p in pkg_dir.glob("*.py") if p.stem != "__init__"
    )


# Command builder submodule names used for multi-hot encoding.
# Auto-discovered from src/commands/{functions,objects}/ to stay in sync.
FUNCTION_MODULES = _discover_modules("functions")
OBJECT_MODULES = _discover_modules("objects")
ALL_MODULES = FUNCTION_MODULES + OBJECT_MODULES

# MA2 action verbs looked-up in docstring / body for multi-hot.
ACTION_VERBS = [
    "assign",
    "blackout",
    "clear",
    "copy",
    "delete",
    "edit",
    "export",
    "go",
    "goto",
    "highlight",
    "import",
    "info",
    "label",
    "list",
    "move",
    "park",
    "release",
    "remove",
    "select",
    "store",
]


@dataclass
class ToolFeatures:
    """Feature bundle for a single MCP tool."""

    name: str
    docstring: str = ""
    param_names: list[str] = field(default_factory=list)
    param_count: int = 0
    optional_param_count: int = 0
    has_confirm_destructive: bool = False
    risk_tier: str = "SAFE_WRITE"  # SAFE_READ | SAFE_WRITE | DESTRUCTIVE
    has_target_type: bool = False
    has_object_id: bool = False
    returns_list: bool = False
    navigates: bool = False
    command_modules: list[str] = field(default_factory=list)
    action_verbs: list[str] = field(default_factory=list)

    # ---- derived numeric vector ------------------------------------------

    def to_structural_vector(self) -> list[float]:
        """Return a flat numeric feature vector (deterministic ordering)."""
        vec: list[float] = []

        # Risk tier one-hot (3 dims)
        for tier in ("SAFE_READ", "SAFE_WRITE", "DESTRUCTIVE"):
            vec.append(1.0 if self.risk_tier == tier else 0.0)

        # Binary flags (5 dims)
        vec.append(1.0 if self.has_confirm_destructive else 0.0)
        vec.append(1.0 if self.has_target_type else 0.0)
        vec.append(1.0 if self.has_object_id else 0.0)
        vec.append(1.0 if self.returns_list else 0.0)
        vec.append(1.0 if self.navigates else 0.0)

        # Scalars (2 dims) — will be normalised later
        vec.append(float(self.param_count))
        vec.append(float(self.optional_param_count))

        # Command module multi-hot (24 dims)
        for mod in ALL_MODULES:
            vec.append(1.0 if mod in self.command_modules else 0.0)

        # Action verb multi-hot (20 dims) — L2-normalised per tool so that
        # tools with many verbs (e.g. send_raw_command with 9) don't dominate
        # distance calculations over tools with 1-2 verbs.
        verb_vec = [1.0 if verb in self.action_verbs else 0.0 for verb in ACTION_VERBS]
        norm = sum(v * v for v in verb_vec) ** 0.5
        if norm > 0:
            verb_vec = [v / norm for v in verb_vec]
        vec.extend(verb_vec)

        return vec

    @staticmethod
    def structural_dim() -> int:
        """Number of structural feature dimensions."""
        return 3 + 5 + 2 + len(ALL_MODULES) + len(ACTION_VERBS)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

_TARGET_TYPE_NAMES = {"target_type", "object_type"}
_OBJECT_ID_RE = re.compile(r"(object_id|target_id|\w+_id)$")
_NAVIGATE_NAMES = {"_navigate_to", "navigate", "cd", "changedest"}

# Build names imported from src.commands so we can map call sites → modules.
_BUILDER_TO_MODULE: dict[str, str] = {}


def _build_import_map(tree: ast.Module) -> dict[str, str]:
    """Map each imported builder name → commands submodule it comes from.

    We inspect ``from src.commands import ...`` and ``from src.commands.functions.X import ...``
    to know which submodule each builder belongs to.
    """
    mapping: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        mod = node.module
        # Direct imports: from src.commands import foo  →  map foo to its origin
        # We can't know the submodule from this alone, so we map to "commands"
        # and resolve later via the builder name patterns.
        if mod == "src.commands":
            for alias in node.names:
                local = alias.asname or alias.name
                # Try to infer submodule from builder name
                submod = _infer_submodule(alias.name)
                mapping[local] = submod
        # Explicit submodule: from src.commands.functions.playback import go
        elif mod.startswith("src.commands.functions.") or mod.startswith("src.commands.objects."):
            submod = mod.rsplit(".", 1)[-1]
            for alias in node.names:
                local = alias.asname or alias.name
                mapping[local] = submod
    return mapping


def _infer_submodule(builder_name: str) -> str:
    """Best-effort mapping from a builder function name to its submodule."""
    name = builder_name.lower()
    # store_* → store
    if name.startswith("store"):
        return "store"
    if name.startswith("delete"):
        return "edit"
    if name.startswith(("go", "goto", "pause")):
        return "playback"
    if name.startswith("list_") or name.startswith("info"):
        return "info"
    if name.startswith("assign"):
        return "assignment"
    if name.startswith("label") or name.startswith("appearance"):
        return "labeling"
    if name.startswith(("clear", "select", "highlight", "blind", "solo", "selfix")):
        return "selection"
    if name.startswith(("copy", "move", "edit", "cut", "paste", "remove")):
        return "edit"
    if name.startswith(("set_var", "set_user_var", "add_var", "add_user_var", "get_user_var", "list_var", "list_user_var")):
        return "variables"
    if name.startswith(("park", "unpark")):
        return "park"
    if name.startswith(("import", "export")):
        return "importexport"
    if name.startswith(("at", "fixture_at", "channel_at", "group_at", "executor_at", "attribute_at", "preset_type_at")):
        return "values"
    if name.startswith("call"):
        return "call"
    if name.startswith("macro"):
        return "macro"
    if name.startswith("matricks"):
        return "matricks"
    if name.startswith(("blackout", "release", "flash", "on_", "off_", "toggle", "solo", "temp")):
        return "playback"
    if name.startswith(("page_", "add_to_selection", "remove_from_selection", "if_condition", "condition")):
        return "helping"
    if name.startswith(("changedest", "navigate")):
        return "navigation"
    if name.startswith("new_show") or name.startswith("load_show") or name.startswith("save_show"):
        return "store"
    if name.startswith("oops"):
        return "edit"
    # Fallback
    for mod in FUNCTION_MODULES + OBJECT_MODULES:
        if mod in name:
            return mod
    return "unknown"


def _has_decorator(node: ast.AsyncFunctionDef, name: str) -> bool:
    """Check if *node* has a decorator whose name or attribute ends with *name*."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call):
            dec = dec.func  # type: ignore[assignment]
        if isinstance(dec, ast.Attribute) and dec.attr == name:
            return True
        if isinstance(dec, ast.Name) and dec.id == name:
            return True
    return False


def _detect_risk_tier(docstring: str, has_destructive_param: bool) -> str:
    doc_upper = docstring.upper()
    if has_destructive_param or "DESTRUCTIVE" in doc_upper:
        return "DESTRUCTIVE"
    if "SAFE_READ" in doc_upper:
        return "SAFE_READ"
    return "SAFE_WRITE"


def _detect_action_verbs(docstring: str, body_source: str) -> list[str]:
    combined = (docstring + " " + body_source).lower()
    # Use word-boundary matching to avoid false positives
    # (e.g. "clear" matching "unclear", "nuclear")
    return [v for v in ACTION_VERBS if re.search(rf"\b{re.escape(v)}\b", combined)]


def _detect_command_modules(
    body: list[ast.stmt],
    import_map: dict[str, str],
) -> list[str]:
    """Walk the function body AST and collect which command submodules are referenced."""
    modules: set[str] = set()
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        # Direct call: build_go(...)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in import_map:
                modules.add(import_map[func.id])
            elif isinstance(func, ast.Attribute) and func.attr in import_map:
                modules.add(import_map[func.attr])
        # Name reference without call
        elif isinstance(node, ast.Name) and node.id in import_map:
            modules.add(import_map[node.id])
    # Filter to known module names
    return [m for m in ALL_MODULES if m in modules]


def _detect_navigates(body: list[ast.stmt]) -> bool:
    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if isinstance(node, ast.Name) and node.id in _NAVIGATE_NAMES:
            return True
        if isinstance(node, ast.Attribute) and node.attr in _NAVIGATE_NAMES:
            return True
        # String literal containing "cd " (raw command navigation)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and (
            "cd " in node.value.lower() or "changedest" in node.value.lower()
        ):
            return True
    return False


def _detect_returns_list(docstring: str) -> bool:
    doc_lower = docstring.lower()
    return any(
        kw in doc_lower
        for kw in ("list ", "query ", "returns entries", "returns all", "returns parsed", "returns ranked")
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_tool_features(server_path: str | Path) -> list[ToolFeatures]:
    """Parse *server_path* and return a :class:`ToolFeatures` per ``@mcp.tool()`` function."""
    source = Path(server_path).read_text()
    tree = ast.parse(source)
    import_map = _build_import_map(tree)

    tools: list[ToolFeatures] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if not _has_decorator(node, "tool"):
            continue

        name = node.name
        docstring = ast.get_docstring(node) or ""

        # Parameters
        args = node.args
        param_names = [a.arg for a in args.args]
        defaults_count = len(args.defaults)
        kw_defaults_count = sum(1 for d in args.kw_defaults if d is not None)
        optional_count = defaults_count + kw_defaults_count
        all_params = param_names + [a.arg for a in args.kwonlyargs]
        param_count = len(all_params)

        has_destructive = "confirm_destructive" in all_params
        has_target = bool(_TARGET_TYPE_NAMES & set(all_params))
        has_obj_id = any(_OBJECT_ID_RE.match(p) for p in all_params)

        risk = _detect_risk_tier(docstring, has_destructive)

        # Body analysis
        body_source = ast.unparse(node)
        verbs = _detect_action_verbs(docstring, body_source)
        cmd_modules = _detect_command_modules(node.body, import_map)
        navigates = _detect_navigates(node.body)
        returns_list = _detect_returns_list(docstring)

        tools.append(
            ToolFeatures(
                name=name,
                docstring=docstring,
                param_names=all_params,
                param_count=param_count,
                optional_param_count=optional_count,
                has_confirm_destructive=has_destructive,
                risk_tier=risk,
                has_target_type=has_target,
                has_object_id=has_obj_id,
                returns_list=returns_list,
                navigates=navigates,
                command_modules=cmd_modules,
                action_verbs=verbs,
            )
        )

    return tools
