"""
grandMA2 v3.9 — Telnet Command Vocabulary (full-context refactor)

Design goals
- Treat MA's "All keywords" list as the canonical *presence* vocabulary.
- Keep aliases/shortcuts as a separate overlay (runtime-authoritative via CmdHelp).
- Provide deterministic token normalization + classification hooks for safety middleware.
- Provide first-class handling for ChangeDest/CD and List/List*.
- Categorize keywords into Object, Function, Helping, and Special Char groups.

Files
- Vendored full keyword set JSON (schema v2.0):
  - grandMA2_v3_9_telnet_keyword_vocabulary.json
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)


# =============================================================================
# Core: loading + normalization
# =============================================================================

DEFAULT_V39_KEYWORD_JSON = os.path.join(
    os.path.dirname(__file__),
    "grandMA2_v3_9_telnet_keyword_vocabulary.json",
)


def _norm_token(tok: str) -> str:
    """
    Normalization used for dictionary lookups:
    - trim
    - lowercase
    - collapse internal whitespace
    """
    tok = tok.strip()
    tok = re.sub(r"\s+", " ", tok)
    return tok.lower()


# =============================================================================
# Safety tiers (middleware hooks)
# =============================================================================

class RiskTier(StrEnum):
    SAFE_READ = "SAFE_READ"
    SAFE_WRITE = "SAFE_WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"
    UNKNOWN = "UNKNOWN"


# =============================================================================
# Keyword categories (coarse classification)
# =============================================================================

class KeywordKind(StrEnum):
    KEYWORD = "KEYWORD"
    SPECIAL_CHAR_ENTRY = "SPECIAL_CHAR"
    PUNCT_TOKEN = "PUNCT_TOKEN"
    UNKNOWN = "UNKNOWN"


class KeywordCategory(StrEnum):
    """Vocabulary-level category for a keyword."""
    OBJECT = "OBJECT"
    FUNCTION = "FUNCTION"
    HELPING = "HELPING"
    SPECIAL_CHAR = "SPECIAL_CHAR"


# Explicit set of known special-character entry names from the MA keyword list.
# Using an explicit set instead of a regex (fixes V4: regex was overly broad).
_SPECIAL_CHAR_ENTRIES = frozenset({
    "asterisk *",
    "dot .",
    "dollar $",
    "slash /",
    "plus +",
    "minus -",
})


# =============================================================================
# Data structures for vocabulary payload (JSON schema v2.0)
# =============================================================================

@dataclass(frozen=True)
class ObjectKeywordEntry:
    """Metadata for an Object Keyword from the vocabulary JSON."""
    keyword: str
    canonical: str
    context_change: bool
    notes: str = ""


@dataclass(frozen=True)
class VocabPayload:
    """Parsed vocabulary payload from JSON (schema v2.0)."""
    object_keywords: list[ObjectKeywordEntry]
    function_keywords: list[str]
    helping_keywords: list[str]
    special_chars: list[str]
    aliases: dict[str, str]


# =============================================================================
# VocabSpec: full vocabulary + overlays
# =============================================================================

@dataclass(frozen=True)
class VocabSpec:
    """
    Full vocabulary + overlays.
    """
    # Canonical keyword presence (from MA "All keywords")
    canonical_keywords: set[str]  # stored in normalized form

    # Normalized -> canonical spelling map for exact round-tripping
    normalized_to_canonical: Mapping[str, str]

    # Aliases/shortcuts -> canonical keyword spelling
    aliases_to_canonical: Mapping[str, str]

    # CD (ChangeDest) specifics
    changedest_aliases: Mapping[str, str]
    changedest_specials: Mapping[str, str]

    # List specifics
    list_option_discovery: str

    # Safety tiers (canonical spellings)
    safe_read: set[str]
    safe_write: set[str]
    destructive: set[str]

    # Object keyword metadata
    object_keywords: frozenset[str] = field(default_factory=frozenset)
    object_keyword_entries: Mapping[str, ObjectKeywordEntry] = field(
        default_factory=dict,
    )

    # Keyword category map (canonical spelling -> category)
    keyword_categories: Mapping[str, KeywordCategory] = field(
        default_factory=dict,
    )


# =============================================================================
# JSON loader (schema v2.0)
# =============================================================================

def _load_keywords_from_json(path: str) -> VocabPayload:
    """
    Load the keyword vocabulary from the vendored JSON file (schema v2.0).

    The JSON file contains categorized keywords:
    - object_keywords: list of objects with keyword, canonical, context_change, notes
    - function_keywords: flat list of function keyword strings
    - helping_keywords: flat list of helping keyword strings
    - special_chars: flat list of special character entry strings
    - aliases: dict mapping alias -> canonical target

    Raises:
        FileNotFoundError: If the keyword vocabulary JSON file is missing.
        json.JSONDecodeError: If the JSON file is malformed.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"grandMA2 keyword vocabulary file not found: {path}. "
            "Ensure grandMA2_v3_9_telnet_keyword_vocabulary.json is present "
            "alongside vocab.py in the src/ directory."
        )
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    # Parse object keywords (rich entries)
    object_keywords = []
    for entry in payload.get("object_keywords", []):
        object_keywords.append(ObjectKeywordEntry(
            keyword=entry["keyword"],
            canonical=entry.get("canonical", entry["keyword"]),
            context_change=entry.get("context_change", True),
            notes=entry.get("notes", ""),
        ))

    return VocabPayload(
        object_keywords=object_keywords,
        function_keywords=list(payload.get("function_keywords", [])),
        helping_keywords=list(payload.get("helping_keywords", [])),
        special_chars=list(payload.get("special_chars", [])),
        aliases=dict(payload.get("aliases", {})),
    )


# =============================================================================
# Build the v3.9 spec
# =============================================================================

def build_v39_spec(
    keyword_json_path: str = DEFAULT_V39_KEYWORD_JSON,
) -> VocabSpec:
    vocab = _load_keywords_from_json(keyword_json_path)

    # Build canonical presence vocabulary (normalized) and reverse map
    canonical: set[str] = set()
    normalized_to_canonical: dict[str, str] = {}
    keyword_categories: dict[str, KeywordCategory] = {}
    object_keyword_entries: dict[str, ObjectKeywordEntry] = {}
    object_kw_canonicals: set[str] = set()

    # ---- Object Keywords (processed first; take category precedence)
    for entry in vocab.object_keywords:
        norm = _norm_token(entry.canonical)
        canonical.add(norm)
        if norm not in normalized_to_canonical:
            normalized_to_canonical[norm] = entry.canonical
        keyword_categories[entry.canonical] = KeywordCategory.OBJECT
        object_keyword_entries[entry.canonical] = entry
        object_kw_canonicals.add(entry.canonical)

    # ---- Function Keywords
    for kw in vocab.function_keywords:
        norm = _norm_token(kw)
        canonical.add(norm)
        if norm not in normalized_to_canonical:
            normalized_to_canonical[norm] = kw
        # Only set category if not already claimed by Object
        if kw not in keyword_categories:
            keyword_categories[kw] = KeywordCategory.FUNCTION

    # ---- Helping Keywords
    for kw in vocab.helping_keywords:
        norm = _norm_token(kw)
        canonical.add(norm)
        if norm not in normalized_to_canonical:
            normalized_to_canonical[norm] = kw
        if kw not in keyword_categories:
            keyword_categories[kw] = KeywordCategory.HELPING

    # ---- Special chars
    for kw in vocab.special_chars:
        norm = _norm_token(kw)
        canonical.add(norm)
        if norm not in normalized_to_canonical:
            normalized_to_canonical[norm] = kw
        keyword_categories[kw] = KeywordCategory.SPECIAL_CHAR

    # ---- ChangeDest/CD overlay
    changedest_aliases = {
        _norm_token("changedest"): "ChangeDest",
        _norm_token("cd"): "ChangeDest",
        _norm_token("chang"): "ChangeDest",
    }
    changedest_specials = {
        "..": "UP_ONE_LEVEL",
        "/": "ROOT",
    }

    # ---- Alias overlay (shortcuts + JSON-defined aliases)
    aliases: dict[str, str] = {
        _norm_token("li"): "List",
        _norm_token("listef"): "ListEffectLibrary",
        _norm_token("listm"): "ListMacroLibrary",
        _norm_token("listp"): "ListPluginLibrary",
    }
    # Add JSON-defined aliases (DMX->Dmx, DMXUniverse->DmxUniverse, etc.)
    for alias_name, canonical_target in vocab.aliases.items():
        aliases[_norm_token(alias_name)] = canonical_target

    # ---- Keywords verified live but absent from the JSON vocabulary.
    # Registered here as self-aliases so classify_token resolves them and
    # the safety tiers below can assign the correct RiskTier.
    _extra_keywords: dict[str, str] = {
        # SAFE_WRITE — extended playback
        "Kill": "Kill",
        "Swop": "Swop",
        "Stomp": "Stomp",
        "LoadNext": "LoadNext",
        "LoadPrev": "LoadPrev",
        # SAFE_WRITE — selection / programmer
        "Fix": "Fix",
        "Locate": "Locate",
        "Invert": "Invert",
        "Align": "Align",
        # DESTRUCTIVE — stored show data
        "Clone": "Clone",
        "Block": "Block",
        "Unblock": "Unblock",
    }
    for kw, canon in _extra_keywords.items():
        aliases[_norm_token(kw)] = canon
    keyword_categories["Kill"] = KeywordCategory.FUNCTION

    # ---- Safety tier defaults
    # NOTE: "Blackout" is classified as SAFE_WRITE because it is a toggle
    # and easily reversible. However, in a live show context, it kills all
    # lighting output and could be disruptive. Operators should be aware.
    safe_read = {
        "Info", "List", "ListEffectLibrary", "ListFaderModules",
        "ListLibrary", "ListMacroLibrary", "ListOops", "ListOwner",
        "ListPluginLibrary", "ListShows", "ListUpdate", "ListUserVar",
        "ListVar", "GetUserVar", "Select", "CmdHelp",
        "ChangeDest",
    }
    safe_write = {
        "At", "Go", "GoBack", "Goto", "On", "Off", "Toggle",
        "Top", "Temp", "TempFader", "Pause", "Release", "Blackout",
        "Blind", "Highlight", "Solo", "Clear", "ClearAll",
        "ClearSelection", "ClearActive", "Flash", "Freeze",
        "SetVar", "AddVar", "SetUserVar", "AddUserVar", "Park", "Unpark",
        "SelFix", "DefGoBack", "DefGoForward", "DefGoPause",
        "GoFastBack", "GoFastForward", "Oops", "Call",
        "All", "AllRows",
        "MAtricksInterleave", "MAtricksBlocks", "MAtricksGroups",
        "MAtricksWings", "MAtricksFilter", "MAtricksReset",
        "Next", "NextRow", "Previous",
        # Playback extended: Kill, Swop, Stomp, LoadNext, LoadPrev
        "Kill", "Swop", "Stomp", "LoadNext", "LoadPrev",
        # Selection / programmer: Fix, Locate, Invert, Align
        "Fix", "Locate", "Invert", "Align",
    }
    # All Object Keywords are SAFE_WRITE (they change programmer context)
    safe_write |= object_kw_canonicals

    destructive = {
        "Delete", "Store", "Copy", "Move", "Update", "Edit",
        "Assign", "Label", "Appearance", "Import", "Export",
        "Login", "Logout", "Remove", "Cut", "Paste", "Empty",
        "NewShow", "LoadShow", "SaveShow", "DeleteShow",
        "Shutdown", "Reboot", "Restart", "Reset",
        # Clone, Block, Unblock modify stored show data
        "Clone", "Block", "Unblock",
    }

    return VocabSpec(
        canonical_keywords=canonical,
        normalized_to_canonical=normalized_to_canonical,
        aliases_to_canonical=aliases,
        changedest_aliases=changedest_aliases,
        changedest_specials=changedest_specials,
        list_option_discovery="/?",
        safe_read=set(safe_read),
        safe_write=set(safe_write),
        destructive=set(destructive),
        object_keywords=frozenset(object_kw_canonicals),
        object_keyword_entries=object_keyword_entries,
        keyword_categories=keyword_categories,
    )


# =============================================================================
# Lookup / classification API
# =============================================================================

@dataclass(frozen=True)
class ResolvedToken:
    raw: str
    normalized: str
    kind: KeywordKind
    canonical: str | None
    risk: RiskTier
    category: KeywordCategory | None = None


def classify_token(tok: str, spec: VocabSpec) -> ResolvedToken:
    n = _norm_token(tok)

    # CD specials are punctuation tokens, not MA "keywords"
    if tok in spec.changedest_specials:
        return ResolvedToken(
            raw=tok,
            normalized=n,
            kind=KeywordKind.PUNCT_TOKEN,
            canonical=None,
            risk=RiskTier.SAFE_READ,
        )

    # Alias overlay (shortcuts, convenience tokens)
    if n in spec.aliases_to_canonical:
        canonical = spec.aliases_to_canonical[n]
        return ResolvedToken(
            raw=tok,
            normalized=n,
            kind=KeywordKind.KEYWORD,
            canonical=canonical,
            risk=_risk_for_canonical(canonical, spec),
            category=spec.keyword_categories.get(canonical),
        )

    # ChangeDest alias overlay
    if n in spec.changedest_aliases:
        canonical = spec.changedest_aliases[n]
        return ResolvedToken(
            raw=tok,
            normalized=n,
            kind=KeywordKind.KEYWORD,
            canonical=canonical,
            risk=_risk_for_canonical(canonical, spec),
            category=spec.keyword_categories.get(canonical),
        )

    # Canonical presence check (from "All keywords")
    if n in spec.canonical_keywords:
        canonical = spec.normalized_to_canonical.get(n, tok)
        return ResolvedToken(
            raw=tok,
            normalized=n,
            kind=_kind_for_normalized(n),
            canonical=canonical,
            risk=_risk_for_canonical(canonical, spec),
            category=spec.keyword_categories.get(canonical),
        )

    return ResolvedToken(
        raw=tok,
        normalized=n,
        kind=KeywordKind.UNKNOWN,
        canonical=None,
        risk=RiskTier.UNKNOWN,
    )


def _kind_for_normalized(normalized: str) -> KeywordKind:
    """Classify keyword kind using the explicit special-char entry set."""
    if normalized in _SPECIAL_CHAR_ENTRIES:
        return KeywordKind.SPECIAL_CHAR_ENTRY
    return KeywordKind.KEYWORD


def _risk_for_canonical(canonical: str, spec: VocabSpec) -> RiskTier:
    if canonical in spec.safe_read:
        return RiskTier.SAFE_READ
    if canonical in spec.safe_write:
        return RiskTier.SAFE_WRITE
    if canonical in spec.destructive:
        return RiskTier.DESTRUCTIVE
    return RiskTier.UNKNOWN


# =============================================================================
# High-level helpers: CD parsing + List parsing
# =============================================================================

@dataclass(frozen=True)
class ChangeDestOp:
    """Parsed ChangeDest intent. (Does not execute anything.)"""
    mode: str  # ROOT | UP_ONE_LEVEL | INDEX | NAME | OBJECT | UNKNOWN
    arg1: str | None = None
    arg2: str | None = None


def parse_changedest(args: Sequence[str], spec: VocabSpec) -> ChangeDestOp:
    """
    Implements MA's documented CD forms:
      CD [Element-index]
      CD "Element name"
      CD [Object-type] [Object-ID]
      CD ..
      CD /
    """
    if not args:
        return ChangeDestOp(mode="UNKNOWN")

    if args[0] in spec.changedest_specials:
        return ChangeDestOp(mode=spec.changedest_specials[args[0]])

    # Element-index (integer)
    if args[0].isdigit():
        return ChangeDestOp(mode="INDEX", arg1=args[0])

    # Name (quoted or raw)
    if len(args) == 1:
        return ChangeDestOp(mode="NAME", arg1=args[0].strip('"'))

    # Object-type + Object-ID
    return ChangeDestOp(mode="OBJECT", arg1=args[0], arg2=args[1])


@dataclass(frozen=True)
class ListOp:
    """Parsed List intent. (Does not execute anything.)"""
    object_list: str | None
    options: Mapping[str, str]
    discovery: bool


_LIST_OPT_RE = re.compile(r"^/([A-Za-z0-9_]+)(?:=(.*))?$")


def parse_list(tokens_after_list: Sequence[str], spec: VocabSpec) -> ListOp:
    """
    Minimal deterministic List parser:
      - If "/?" present => discovery=True
      - Parses /option=value or /option as flags
      - Everything before first /option token is treated as object_list text
    """
    discovery = False
    options: dict[str, str] = {}
    obj_parts: list[str] = []

    for t in tokens_after_list:
        if t == spec.list_option_discovery:
            discovery = True
            continue

        m = _LIST_OPT_RE.match(t)
        if m:
            k = m.group(1)
            v = m.group(2) if m.group(2) is not None else "true"
            options[k] = v
        else:
            obj_parts.append(t)

    object_list = " ".join(obj_parts).strip() or None
    return ListOp(object_list=object_list, options=options, discovery=discovery)


# =============================================================================
# CD Numeric Index Map (live-validated on grandMA2 onPC 3.9.60.65)
# =============================================================================

CD_NUMERIC_INDEX: dict[int, str] = {
    1: "Showfile",           2: "TimeConfig",         3: "Settings",
    4: "DMX_Protocols",      5: "NetConfig",           6: "CITPNetConfig",
    7: "TrackingSystems",    8: "UserImagePool",       9: "RDM_Data",
    10: "LiveSetup",         11: "EditSetup",          13: "Macros",
    14: "FlightRecordings",  15: "Plugins",            16: "Gels",
    17: "Presets",           18: "Worlds",             19: "Filters",
    20: "FadePaths",         21: "Programmer",         22: "Groups",
    23: "Forms",             24: "Effects",            25: "Sequences",
    26: "Timers",            27: "MasterSections",     30: "ExecutorPages",
    31: "ChannelPages",      33: "Songs",              34: "Agendas",
    35: "Timecodes",         36: "RemoteTypes",        37: "DMXSnapshotPool",
    38: "Layouts",           39: "UserProfiles",       40: "Users",
    41: "PixelMapperContainer", 42: "NDP_Root",        43: "UserStationCollect",
    46: "Temp",
}

# Indexes confirmed INVALID (Error #72: COMMAND NOT EXECUTED) on MA2 3.9.60.65
CD_INVALID_INDEXES: frozenset[int] = frozenset({12, 28, 29, 32, 44, 45, 47, 48, 49, 50})


# =============================================================================
# Functional Domains (from grandMA2_KMeans_Complete.json — keyword_taxonomy)
# =============================================================================
# 10 functional domains grouping 288 keywords by operational role.
# Complements KeywordCategory (OBJECT/FUNCTION/HELPING) with semantic grouping.

class FunctionalDomain(StrEnum):
    OBJECT_MANIPULATION  = "object_manipulation"
    PLAYBACK_CONTROL     = "playback_control"
    SELECTION_FILTERING  = "selection_filtering"
    TIMING_EFFECTS       = "timing_effects"
    NETWORK_SESSION      = "network_session"
    SYSTEM_ADMIN         = "system_admin"
    DATA_QUERY           = "data_query"
    VARIABLES_SCRIPTING  = "variables_scripting"
    MATRICKS             = "matricks"
    RDM                  = "rdm"


# Maps canonical keyword spelling → FunctionalDomain.
# A keyword may appear in only one domain (primary assignment).
KEYWORD_DOMAINS: dict[str, FunctionalDomain] = {
    # object_manipulation (21)
    "Assign":           FunctionalDomain.OBJECT_MANIPULATION,
    "Label":            FunctionalDomain.OBJECT_MANIPULATION,
    "Appearance":       FunctionalDomain.OBJECT_MANIPULATION,
    "Copy":             FunctionalDomain.OBJECT_MANIPULATION,
    "Move":             FunctionalDomain.OBJECT_MANIPULATION,
    "Delete":           FunctionalDomain.OBJECT_MANIPULATION,
    "Edit":             FunctionalDomain.OBJECT_MANIPULATION,
    "Store":            FunctionalDomain.OBJECT_MANIPULATION,
    "Record":           FunctionalDomain.OBJECT_MANIPULATION,
    "Insert":           FunctionalDomain.OBJECT_MANIPULATION,
    "Remove":           FunctionalDomain.OBJECT_MANIPULATION,
    "Replace":          FunctionalDomain.OBJECT_MANIPULATION,
    "Paste":            FunctionalDomain.OBJECT_MANIPULATION,
    "Cut":              FunctionalDomain.OBJECT_MANIPULATION,
    "Clone":            FunctionalDomain.OBJECT_MANIPULATION,
    "Import":           FunctionalDomain.OBJECT_MANIPULATION,
    "Export":           FunctionalDomain.OBJECT_MANIPULATION,
    "Extract":          FunctionalDomain.OBJECT_MANIPULATION,
    "CircularCopy":     FunctionalDomain.OBJECT_MANIPULATION,
    "RemoveIndividuals":FunctionalDomain.OBJECT_MANIPULATION,
    "StoreLook":        FunctionalDomain.OBJECT_MANIPULATION,
    # playback_control (26)
    "Go":               FunctionalDomain.PLAYBACK_CONTROL,
    "GoBack":           FunctionalDomain.PLAYBACK_CONTROL,
    "Goto":             FunctionalDomain.PLAYBACK_CONTROL,
    "Pause":            FunctionalDomain.PLAYBACK_CONTROL,
    "Kill":             FunctionalDomain.PLAYBACK_CONTROL,
    "Off":              FunctionalDomain.PLAYBACK_CONTROL,
    "On":               FunctionalDomain.PLAYBACK_CONTROL,
    "Flash":            FunctionalDomain.PLAYBACK_CONTROL,
    "FlashGo":          FunctionalDomain.PLAYBACK_CONTROL,
    "FlashOn":          FunctionalDomain.PLAYBACK_CONTROL,
    "Swop":             FunctionalDomain.PLAYBACK_CONTROL,
    "SwopGo":           FunctionalDomain.PLAYBACK_CONTROL,
    "SwopOn":           FunctionalDomain.PLAYBACK_CONTROL,
    "Toggle":           FunctionalDomain.PLAYBACK_CONTROL,
    "Temp":             FunctionalDomain.PLAYBACK_CONTROL,
    "TempFader":        FunctionalDomain.PLAYBACK_CONTROL,
    "Solo":             FunctionalDomain.PLAYBACK_CONTROL,
    "Freeze":           FunctionalDomain.PLAYBACK_CONTROL,
    "Release":          FunctionalDomain.PLAYBACK_CONTROL,
    "Stomp":            FunctionalDomain.PLAYBACK_CONTROL,
    "Load":             FunctionalDomain.PLAYBACK_CONTROL,
    "LoadNext":         FunctionalDomain.PLAYBACK_CONTROL,
    "LoadPrev":         FunctionalDomain.PLAYBACK_CONTROL,
    "DefGoBack":        FunctionalDomain.PLAYBACK_CONTROL,
    "DefGoForward":     FunctionalDomain.PLAYBACK_CONTROL,
    "DefGoPause":       FunctionalDomain.PLAYBACK_CONTROL,
    # selection_filtering (28)
    "Select":           FunctionalDomain.SELECTION_FILTERING,
    "Clear":            FunctionalDomain.SELECTION_FILTERING,
    "ClearAll":         FunctionalDomain.SELECTION_FILTERING,
    "ClearActive":      FunctionalDomain.SELECTION_FILTERING,
    "ClearSelection":   FunctionalDomain.SELECTION_FILTERING,
    "If":               FunctionalDomain.SELECTION_FILTERING,
    "IfActive":         FunctionalDomain.SELECTION_FILTERING,
    "IfOutput":         FunctionalDomain.SELECTION_FILTERING,
    "IfProg":           FunctionalDomain.SELECTION_FILTERING,
    "EndIf":            FunctionalDomain.SELECTION_FILTERING,
    "Park":             FunctionalDomain.SELECTION_FILTERING,
    "Unpark":           FunctionalDomain.SELECTION_FILTERING,
    "Block":            FunctionalDomain.SELECTION_FILTERING,
    "Unblock":          FunctionalDomain.SELECTION_FILTERING,
    "Fix":              FunctionalDomain.SELECTION_FILTERING,
    "Locate":           FunctionalDomain.SELECTION_FILTERING,
    "Highlight":        FunctionalDomain.SELECTION_FILTERING,
    "FullHighlight":    FunctionalDomain.SELECTION_FILTERING,
    "Blind":            FunctionalDomain.SELECTION_FILTERING,
    "BlindEdit":        FunctionalDomain.SELECTION_FILTERING,
    "Preview":          FunctionalDomain.SELECTION_FILTERING,
    "PreviewEdit":      FunctionalDomain.SELECTION_FILTERING,
    "PreviewExecutor":  FunctionalDomain.SELECTION_FILTERING,
    "ShuffleSelection": FunctionalDomain.SELECTION_FILTERING,
    "ShuffleValues":    FunctionalDomain.SELECTION_FILTERING,
    "Invert":           FunctionalDomain.SELECTION_FILTERING,
    "Align":            FunctionalDomain.SELECTION_FILTERING,
    "SelFix":           FunctionalDomain.SELECTION_FILTERING,
    # timing_effects (38 — helping keywords + effect keywords)
    "Fade":             FunctionalDomain.TIMING_EFFECTS,
    "FadePath":         FunctionalDomain.TIMING_EFFECTS,
    "Delay":            FunctionalDomain.TIMING_EFFECTS,
    "OutDelay":         FunctionalDomain.TIMING_EFFECTS,
    "OutFade":          FunctionalDomain.TIMING_EFFECTS,
    "Speed":            FunctionalDomain.TIMING_EFFECTS,
    "Rate":             FunctionalDomain.TIMING_EFFECTS,
    "Rate1":            FunctionalDomain.TIMING_EFFECTS,
    "DoubleRate":       FunctionalDomain.TIMING_EFFECTS,
    "DoubleSpeed":      FunctionalDomain.TIMING_EFFECTS,
    "HalfRate":         FunctionalDomain.TIMING_EFFECTS,
    "HalfSpeed":        FunctionalDomain.TIMING_EFFECTS,
    "Crossfade":        FunctionalDomain.TIMING_EFFECTS,
    "CrossfadeA":       FunctionalDomain.TIMING_EFFECTS,
    "CrossfadeB":       FunctionalDomain.TIMING_EFFECTS,
    "ManualXFade":      FunctionalDomain.TIMING_EFFECTS,
    "StepFade":         FunctionalDomain.TIMING_EFFECTS,
    "StepInFade":       FunctionalDomain.TIMING_EFFECTS,
    "StepOutFade":      FunctionalDomain.TIMING_EFFECTS,
    "CmdDelay":         FunctionalDomain.TIMING_EFFECTS,
    "SnapPercent":      FunctionalDomain.TIMING_EFFECTS,
    "MasterFade":       FunctionalDomain.TIMING_EFFECTS,
    "SyncEffects":      FunctionalDomain.TIMING_EFFECTS,
    "EffectAttack":     FunctionalDomain.TIMING_EFFECTS,
    "EffectDecay":      FunctionalDomain.TIMING_EFFECTS,
    "EffectDelay":      FunctionalDomain.TIMING_EFFECTS,
    "EffectFade":       FunctionalDomain.TIMING_EFFECTS,
    "EffectHigh":       FunctionalDomain.TIMING_EFFECTS,
    "EffectLow":        FunctionalDomain.TIMING_EFFECTS,
    "EffectPhase":      FunctionalDomain.TIMING_EFFECTS,
    "EffectWidth":      FunctionalDomain.TIMING_EFFECTS,
    "EffectBPM":        FunctionalDomain.TIMING_EFFECTS,
    "EffectHZ":         FunctionalDomain.TIMING_EFFECTS,
    "EffectSec":        FunctionalDomain.TIMING_EFFECTS,
    "EffectSpeedGroup": FunctionalDomain.TIMING_EFFECTS,
    "EffectForm":       FunctionalDomain.TIMING_EFFECTS,
    "EffectID":         FunctionalDomain.TIMING_EFFECTS,
    # network_session (19)
    "JoinSession":        FunctionalDomain.NETWORK_SESSION,
    "LeaveSession":       FunctionalDomain.NETWORK_SESSION,
    "EndSession":         FunctionalDomain.NETWORK_SESSION,
    "InviteStation":      FunctionalDomain.NETWORK_SESSION,
    "DisconnectStation":  FunctionalDomain.NETWORK_SESSION,
    "TakeControl":        FunctionalDomain.NETWORK_SESSION,
    "DropControl":        FunctionalDomain.NETWORK_SESSION,
    "SetIP":              FunctionalDomain.NETWORK_SESSION,
    "SetHostname":        FunctionalDomain.NETWORK_SESSION,
    "SetNetworkSpeed":    FunctionalDomain.NETWORK_SESSION,
    "NetworkInfo":        FunctionalDomain.NETWORK_SESSION,
    "NetworkNodeInfo":    FunctionalDomain.NETWORK_SESSION,
    "NetworkNodeUpdate":  FunctionalDomain.NETWORK_SESSION,
    "NetworkSpeedTest":   FunctionalDomain.NETWORK_SESSION,
    "Telnet":             FunctionalDomain.NETWORK_SESSION,
    "Remote":             FunctionalDomain.NETWORK_SESSION,
    "RemoteCommand":      FunctionalDomain.NETWORK_SESSION,
    "WebRemoteProgOnly":  FunctionalDomain.NETWORK_SESSION,
    "Chat":               FunctionalDomain.NETWORK_SESSION,
    "Message":            FunctionalDomain.NETWORK_SESSION,
    # system_admin (26)
    "Shutdown":           FunctionalDomain.SYSTEM_ADMIN,
    "Reboot":             FunctionalDomain.SYSTEM_ADMIN,
    "Restart":            FunctionalDomain.SYSTEM_ADMIN,
    "Login":              FunctionalDomain.SYSTEM_ADMIN,
    "Logout":             FunctionalDomain.SYSTEM_ADMIN,
    "SaveShow":           FunctionalDomain.SYSTEM_ADMIN,
    "LoadShow":           FunctionalDomain.SYSTEM_ADMIN,
    "NewShow":            FunctionalDomain.SYSTEM_ADMIN,
    "DeleteShow":         FunctionalDomain.SYSTEM_ADMIN,
    "UpdateFirmware":     FunctionalDomain.SYSTEM_ADMIN,
    "UpdateSoftware":     FunctionalDomain.SYSTEM_ADMIN,
    "UpdateThumbnails":   FunctionalDomain.SYSTEM_ADMIN,
    "CrashLogCopy":       FunctionalDomain.SYSTEM_ADMIN,
    "CrashLogDelete":     FunctionalDomain.SYSTEM_ADMIN,
    "CrashLogList":       FunctionalDomain.SYSTEM_ADMIN,
    "ReloadPlugins":      FunctionalDomain.SYSTEM_ADMIN,
    "BlackScreen":        FunctionalDomain.SYSTEM_ADMIN,
    "Blackout":           FunctionalDomain.SYSTEM_ADMIN,
    "Alert":              FunctionalDomain.SYSTEM_ADMIN,
    "SelectDrive":        FunctionalDomain.SYSTEM_ADMIN,
    "ResetGuid":          FunctionalDomain.SYSTEM_ADMIN,
    "ResetDmxSelection":  FunctionalDomain.SYSTEM_ADMIN,
    "ListShows":          FunctionalDomain.SYSTEM_ADMIN,
    "ListUpdate":         FunctionalDomain.SYSTEM_ADMIN,
    "ListOops":           FunctionalDomain.SYSTEM_ADMIN,
    # data_query (19)
    "List":               FunctionalDomain.DATA_QUERY,
    "ListLibrary":        FunctionalDomain.DATA_QUERY,
    "ListEffectLibrary":  FunctionalDomain.DATA_QUERY,
    "ListMacroLibrary":   FunctionalDomain.DATA_QUERY,
    "ListPluginLibrary":  FunctionalDomain.DATA_QUERY,
    "ListFaderModules":   FunctionalDomain.DATA_QUERY,
    "ListOwner":          FunctionalDomain.DATA_QUERY,
    "ListUserVar":        FunctionalDomain.DATA_QUERY,
    "ListVar":            FunctionalDomain.DATA_QUERY,
    "Search":             FunctionalDomain.DATA_QUERY,
    "SearchResult":       FunctionalDomain.DATA_QUERY,
    "Info":               FunctionalDomain.DATA_QUERY,
    "Help":               FunctionalDomain.DATA_QUERY,
    "CmdHelp":            FunctionalDomain.DATA_QUERY,
    "PSR":                FunctionalDomain.DATA_QUERY,
    "PSRList":            FunctionalDomain.DATA_QUERY,
    "PSRPrepare":         FunctionalDomain.DATA_QUERY,
    "Oops":               FunctionalDomain.DATA_QUERY,
    # variables_scripting (10)
    "SetUserVar":         FunctionalDomain.VARIABLES_SCRIPTING,
    "SetVar":             FunctionalDomain.VARIABLES_SCRIPTING,
    "AddUserVar":         FunctionalDomain.VARIABLES_SCRIPTING,
    "AddVar":             FunctionalDomain.VARIABLES_SCRIPTING,
    "Call":               FunctionalDomain.VARIABLES_SCRIPTING,
    "Macro":              FunctionalDomain.VARIABLES_SCRIPTING,
    "Plugin":             FunctionalDomain.VARIABLES_SCRIPTING,
    # matricks (8)
    "MAtricks":           FunctionalDomain.MATRICKS,
    "MAtricksBlocks":     FunctionalDomain.MATRICKS,
    "MAtricksFilter":     FunctionalDomain.MATRICKS,
    "MAtricksGroups":     FunctionalDomain.MATRICKS,
    "MAtricksInterleave": FunctionalDomain.MATRICKS,
    "MAtricksReset":      FunctionalDomain.MATRICKS,
    "MAtricksWings":      FunctionalDomain.MATRICKS,
    "Interleave":         FunctionalDomain.MATRICKS,
    # rdm (8)
    "RdmAutomatch":       FunctionalDomain.RDM,
    "RdmAutopatch":       FunctionalDomain.RDM,
    "RdmFixtureType":     FunctionalDomain.RDM,
    "RdmInfo":            FunctionalDomain.RDM,
    "RdmList":            FunctionalDomain.RDM,
    "RdmSetParameter":    FunctionalDomain.RDM,
    "RdmSetpatch":        FunctionalDomain.RDM,
    "RdmUnmatch":         FunctionalDomain.RDM,
}


# =============================================================================
# CD Keyword Destinations (keyword-name navigation)
# =============================================================================
# Source: grandMA2_KMeans_Complete.json — command_line_state_model.cd_destinations
# Complements CD_NUMERIC_INDEX (numeric index map) with keyword-name forms.
# Usage: cd [keyword] — navigates into that object pool.

CD_KEYWORD_DESTINATIONS: dict[str, str] = {
    "Effect":        "cd Effect [ID] → macro lines/params",
    "Sequence":      "cd Sequence [ID] → shows cues",
    "Executor":      "cd Executor → executor pool",
    "Macro":         "cd Macro [ID] → macro lines",
    "Layout":        "cd Layout [ID] → layout elements",
    "Group":         "cd Group → group pool",
    "Preset":        "cd Preset → preset pool (all types)",
    "PresetType":    "cd PresetType [1-9] → specific type pool",
    "Fixture":       "cd Fixture → fixture pool",
    "FixtureType":   "cd FixtureType → fixture type library",
    "Channel":       "cd Channel → channel pool",
    "World":         "cd World → world pool",
    "Filter":        "cd Filter → filter pool",
    "Mask":          "cd Mask → mask pool",
    "Timer":         "cd Timer → timer pool",
    "Timecode":      "cd Timecode → timecode pool",
    "Image":         "cd Image → image pool",
    "Plugin":        "cd Plugin → plugin pool",
    "DmxUniverse":   "cd DmxUniverse → DMX universe config",
    "User":          "cd User → user pool",
    "UserProfile":   "cd UserProfile → user profile pool",
    "Setup":         "cd Setup → setup tree",
    "MAtricks":      "cd MAtricks → MAtricks pool",
    "Camera":        "cd Camera → 3D camera pool",
    "Item3D":        "cd Item3D → 3D item pool",
    "Model":         "cd Model → 3D model pool",
    "Dmx":           "cd Dmx → DMX address tree",
    "Agenda":        "cd Agenda → agenda pool",
    "Page":          "cd Page → page pool",
    "View":          "cd View → view pool",
    "Screen":        "cd Screen → screen config",
    "Surface":       "cd Surface → surface pool",
    "Protocol":      "cd Protocol → protocol config",
    "Master":        "cd Master → master pool",
    "SpecialMaster": "cd SpecialMaster → special master pool",
    "Profile":       "cd Profile → DMX profile pool",
}


# =============================================================================
# Default Keyword States (command line prompt → behavior)
# =============================================================================
# Source: grandMA2_KMeans_Complete.json — command_line_state_model.default_keyword_states
# The Default Keyword determines how bare numbers are interpreted on the command line.
# Prompt format: [Keyword]>

DEFAULT_KEYWORD_STATES: list[dict] = [
    {
        "keyword": "Channel",
        "prompt": "[Channel]>",
        "bare_number": "Selects Channel N (SelFix)",
        "default_function": "SelFix",
        "notes": "FACTORY DEFAULT on new empty show",
    },
    {
        "keyword": "Fixture",
        "prompt": "[Fixture]>",
        "bare_number": "Selects Fixture N (SelFix)",
        "default_function": "SelFix",
        "notes": "Use when show uses Fixture IDs",
    },
    {
        "keyword": "Group",
        "prompt": "[Group]>",
        "bare_number": "Selects fixtures in Group N",
        "default_function": "SelFix/At (context)",
        "notes": "Resolves to stored fixture selection",
    },
    {
        "keyword": "Preset",
        "prompt": "[Preset]>",
        "bare_number": "Applies Preset N to selection",
        "default_function": "SelFix/At (context)",
        "notes": "Preset type = currently selected pool",
    },
    {
        "keyword": "Executor",
        "prompt": "[Executor]>",
        "bare_number": "SelFix on Executor N",
        "default_function": "SelFix",
        "notes": "Format: [Page].[ID] or just [ID]",
    },
    {
        "keyword": "Sequence",
        "prompt": "[Sequence]>",
        "bare_number": "Addresses Sequence N",
        "default_function": "SelFix",
        "notes": "",
    },
    {
        "keyword": "Cue",
        "prompt": "[Cue]>",
        "bare_number": "Addresses Cue N of selected executor",
        "default_function": "Context-dependent",
        "notes": "Format: [ID] or [Seq].[ID]",
    },
    {
        "keyword": "Page",
        "prompt": "[Page]>",
        "bare_number": "Addresses Page N",
        "default_function": "N/A",
        "notes": "Executor page number",
    },
    {
        "keyword": "Effect",
        "prompt": "[Effect]>",
        "bare_number": "Addresses Effect N",
        "default_function": "SelFix",
        "notes": "",
    },
    {
        "keyword": "Macro",
        "prompt": "[Macro]>",
        "bare_number": "Executes Macro N (Go+)",
        "default_function": "Go+",
        "notes": "Bare number RUNS the macro",
    },
]


# =============================================================================
# MA2 RIGHTS LEVELS (6-tier console rights model)
# =============================================================================
# Maps grandMA2's built-in 6-level rights system to named integer tiers.
# Used to annotate MCP tools with their minimum required console rights.
# Reference: grandMA2 Setup → User & Profiles Setup → Rights column.
#
# Rights levels are cumulative downward: Admin implies all lower tiers.
# Comparison via >= works correctly because this is an IntEnum.

from enum import IntEnum as _IntEnum  # noqa: E402


class RightsLevel(_IntEnum):
    """grandMA2 console user rights levels (6 tiers, 0 = least privileged)."""

    NONE      = 0   # View-only: change views, select fixtures for sorting
    PLAYBACK  = 1   # Playback operators: Go/Off/On, page navigation, faders
    PRESETS   = 2   # Preset operators: programmer writes, preset recall/update
    PROGRAM   = 3   # Programmers: cue/group/sequence/macro/effect editing
    SETUP     = 4   # Technical directors: patch, fixture import, console setup
    ADMIN     = 5   # System admins: user management, show load, network config


# Mapping from MA2 RightsLevel → corresponding OAuth scope tier (0-5).
# The OAuth tier is equal to the rights level integer (1-to-1 mapping by design).
RIGHTS_TO_OAUTH_TIER: dict[int, int] = {
    RightsLevel.NONE:     0,
    RightsLevel.PLAYBACK: 1,
    RightsLevel.PRESETS:  2,
    RightsLevel.PROGRAM:  3,
    RightsLevel.SETUP:    4,
    RightsLevel.ADMIN:    5,
}
