"""
scripts/demo_skills_live.py -- Execute a .claude/skills/ instruction module against
the live grandMA2 console via Telnet, printing each step with real tool output.

This is the "runtime" layer that turns a SKILL.md instruction module into actual
MCP tool calls. Without a live LLM, this script hard-codes the tool-call sequence
prescribed by each skill and shows the real telnet responses.

Supported skills:
  cue-list-auditor          (default) -- read-only sequence audit
  feedback-investigator               -- classify a raw telnet response
  color-preset-creator                -- store 8 universal color presets (4.1-4.8)
  color-palette-sequence-builder      -- build 8-cue palette sequence from presets
  sequence-executor-assigner          -- assign a sequence to a free executor
  hue-palette-creator                 -- store 96 hue presets (4.101-4.196)
  hue-sequence-builder                -- build one 16-cue adjacent hue pair sequence
  full-hue-expansion                  -- build all 96 presets + 6 hue pair sequences (Pages 1)
  sat-bands                           -- Group A: 8 saturation-band sequences (Page 2, Seq 106-113)
  hue-faders                          -- Group B: 12 single-hue sequences (Page 3, Seq 114-125)
  temperature                         -- Group C: Warm + Cool sequences (Page 4, Seq 126-127)
  complements                         -- Group D: 6 complementary pair sequences (Page 5, Seq 128-133)
  all-color-groups                    -- build all 4 groups above (Pages 2-5, 28 seq, 384 cues)

Usage:
    python scripts/demo_skills_live.py                       # cue-list-auditor on seq 1
    python scripts/demo_skills_live.py --sequence 2
    python scripts/demo_skills_live.py --skill feedback-investigator \\
        --response "Command failed: RIGHTS DENIED for user programmer"
    python scripts/demo_skills_live.py --skill sequence-executor-assigner --sequence 99
    python scripts/demo_skills_live.py --skill sat-bands
    python scripts/demo_skills_live.py --skill hue-faders
    python scripts/demo_skills_live.py --skill temperature
    python scripts/demo_skills_live.py --skill complements
    python scripts/demo_skills_live.py --skill all-color-groups
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap -- must happen before any src.* imports
# ---------------------------------------------------------------------------

os.environ.setdefault("GMA_AUTH_BYPASS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.server import (  # noqa: E402
    apply_preset,
    assign_object,
    get_client,
    get_executor_status,
    get_object_info,
    label_or_appearance,
    list_preset_pool,
    list_system_variables,
    navigate_console,
    navigate_page,
    query_object_list,
    store_current_cue,
    store_new_preset,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SKILLS_DIR = _REPO_ROOT / ".claude" / "skills"
_WIDTH = 72
_current_show: str = "unknown"

# Standard 8-color LED palette -- RGB values on 0-100 scale (not 0-255)
# id matches the expected preset pool slot; name is the human label.
STANDARD_COLOR_PALETTE = [
    {"id": 1, "name": "Red",     "r": 100, "g":   0, "b":   0},
    {"id": 2, "name": "Blue",    "r":   0, "g":   0, "b": 100},
    {"id": 3, "name": "Green",   "r":   0, "g": 100, "b":   0},
    {"id": 4, "name": "Amber",   "r": 100, "g":  55, "b":   0},
    {"id": 5, "name": "White",   "r": 100, "g": 100, "b": 100},
    {"id": 6, "name": "Magenta", "r": 100, "g":   0, "b": 100},
    {"id": 7, "name": "Cyan",    "r":   0, "g": 100, "b": 100},
    {"id": 8, "name": "UV",      "r":  20, "g":   0, "b": 100},
]

# ---------------------------------------------------------------------------
# 12-hue × 8-saturation expanded palette (presets 4.101–4.196)
# ---------------------------------------------------------------------------

def _hsb_to_rgb100(h: float, s: float, b: float) -> tuple[int, int, int]:
    """Convert HSB (h:0-360, s:0-100, b:0-100) to RGB on the MA2 0-100 scale."""
    s_frac = s / 100.0
    v_frac = b / 100.0
    if s_frac == 0:
        val = round(v_frac * 100)
        return val, val, val
    h_norm = (h % 360) / 60.0
    i = int(h_norm) % 6
    f = h_norm - int(h_norm)
    p = v_frac * (1 - s_frac)
    q = v_frac * (1 - s_frac * f)
    t = v_frac * (1 - s_frac * (1 - f))
    if i == 0:   rv, gv, bv = v_frac, t,      p
    elif i == 1: rv, gv, bv = q,      v_frac,  p
    elif i == 2: rv, gv, bv = p,      v_frac,  t
    elif i == 3: rv, gv, bv = p,      q,       v_frac
    elif i == 4: rv, gv, bv = t,      p,       v_frac
    else:        rv, gv, bv = v_frac, p,       q
    return round(rv * 100), round(gv * 100), round(bv * 100)


_HUES = [
    ("Red",     0),
    ("Orange",  30),
    ("Amber",   60),
    ("Yellow",  90),
    ("Lime",    120),
    ("Green",   150),
    ("Teal",    180),
    ("Cyan",    210),
    ("Azure",   240),
    ("Blue",    270),
    ("Violet",  300),
    ("Magenta", 330),
]

_SAT_STEPS = [
    (100, "Full"),
    (88,  "Deep"),
    (75,  "Rich"),
    (63,  "Mid"),
    (50,  "Soft"),
    (38,  "Pale"),
    (25,  "Blush"),
    (13,  "Hint"),
]

# 6 adjacent hue pairs -> sequences 100-105, executors 202-207
# Each tuple: (hue_idx_a, hue_idx_b, seq_label, sequence_id, executor_id)
HUE_PAIRS = [
    (0,  1,  "Red / Orange",      100, 202),
    (2,  3,  "Amber / Yellow",    101, 203),
    (4,  5,  "Lime / Green",      102, 204),
    (6,  7,  "Teal / Cyan",       103, 205),
    (8,  9,  "Azure / Blue",      104, 206),
    (10, 11, "Violet / Magenta",  105, 207),
]

# 6 true-complement pairs (hues 180 degrees apart) -> sequences 128-133, Page 5
# Each tuple: (hue_idx_a, hue_idx_b, seq_label, executor_midpoint_hue)
COMPLEMENT_PAIRS = [
    (0,  6,  "Red / Teal",        90),
    (1,  7,  "Orange / Cyan",    120),
    (2,  8,  "Amber / Azure",    150),
    (3,  9,  "Yellow / Blue",    180),
    (4,  10, "Lime / Violet",    210),
    (5,  11, "Green / Magenta",  240),
]

HUE_PALETTE_96: list[dict] = []
for _hi, (_hname, _hdeg) in enumerate(_HUES):
    for _si, (_sval, _ssuffix) in enumerate(_SAT_STEPS):
        _pid = 101 + _hi * 8 + _si
        _name = f"{_hname} {_ssuffix}"
        _r, _g, _b = _hsb_to_rgb100(_hdeg, _sval, 100)
        HUE_PALETTE_96.append({
            "id": _pid, "name": _name,
            "r": _r, "g": _g, "b": _b,
            "h": _hdeg, "s": _sval, "br": 100,
        })

# Name-keyed RGB lookup (lowercase) -- primary key for appearance calls so that
# cue appearance is driven by the cue label, not by the numeric preset slot id.
# Covers both STANDARD_COLOR_PALETTE (4.1-4.8) and HUE_PALETTE_96 (4.101-4.196).
COLOR_NAME_RGB: dict[str, dict[str, int]] = {
    e["name"].lower(): {"r": e["r"], "g": e["g"], "b": e["b"]}
    for palette in (STANDARD_COLOR_PALETTE, HUE_PALETTE_96)
    for e in palette
}

# ---------------------------------------------------------------------------
# Formatting helpers (same style as demo.py)
# ---------------------------------------------------------------------------


def banner(title: str) -> None:
    print()
    print("=" * _WIDTH)
    print(f"  {title}")
    print("=" * _WIDTH)


def section(label: str, *, step: int | None = None) -> None:
    prefix = f"Step {step}: " if step is not None else ""
    full = f"-- {prefix}{label} "
    pad = _WIDTH - len(full)
    print(f"\n{full}{'-' * max(pad, 0)}")


def skill_says(text: str) -> None:
    print(f"   Skill says : {text}")


def tool_call(expr: str) -> None:
    print(f"   Tool call  : {expr}")


def ok(msg: str) -> None:
    print(f"   [OK] {msg}")


def warn(msg: str) -> None:
    print(f"   [!!] {msg}")


def info(msg: str) -> None:
    print(f"   --> {msg}")


def telnet(cmd: str) -> None:
    print(f"   Telnet >>  {cmd}")


def show_raw(data: str | dict, max_lines: int = 20) -> None:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            lines = data.splitlines()
            for line in lines[:max_lines]:
                print(f"       {line}")
            if len(lines) > max_lines:
                print(f"       ... ({len(lines) - max_lines} more lines)")
            return
    rendered = json.dumps(data, indent=2)
    lines = rendered.splitlines()
    for line in lines[:max_lines]:
        print(f"       {line}")
    if len(lines) > max_lines:
        print(f"       ... ({len(lines) - max_lines} more lines)")


# ---------------------------------------------------------------------------
# SKILL.md loader
# ---------------------------------------------------------------------------


def _load_skill(slug: str) -> dict:
    matches = list(_SKILLS_DIR.glob(f"*{slug}*/SKILL.md"))
    if not matches:
        print(f"ERROR: no skill matching '{slug}' in {_SKILLS_DIR}", file=sys.stderr)
        sys.exit(1)
    path = matches[0]
    text = path.read_text(encoding="utf-8")
    fm: dict[str, str] = {}
    body = text
    if text.startswith("---\n"):
        end = text.index("---\n", 4)
        for line in text[4:end].splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()
        body = text[end + 4:]
    return {"slug": path.parent.name, "title": fm.get("title", slug),
            "version": fm.get("version", "?"), "body": body.strip()}


# ---------------------------------------------------------------------------
# Skill: cue-list-auditor
# ---------------------------------------------------------------------------


async def run_cue_list_auditor(sequence_id: int | None) -> None:
    skill = _load_skill("cue-list-auditor")

    # ── Auto-sequence detection ──────────────────────────────────────────────
    if sequence_id is None:
        section("Auto-detecting sequences")
        tool_call("query_object_list(object_type='sequence')")
        raw_seqs = await query_object_list(object_type="sequence")
        data_seqs = json.loads(raw_seqs) if isinstance(raw_seqs, str) else raw_seqs
        if isinstance(data_seqs, dict) and "command_sent" in data_seqs:
            telnet(data_seqs["command_sent"])
        if isinstance(data_seqs, dict) and data_seqs.get("blocked"):
            warn(f"query_object_list blocked: {data_seqs.get('error', 'unknown')}")
            sequence_id = 1
            info("Falling back to sequence_id=1")
        else:
            raw_text = (data_seqs.get("raw_response", "") if isinstance(data_seqs, dict)
                        else str(data_seqs))
            show_raw(data_seqs, max_lines=8)
            clean_seqs = re.sub(r"\x1b\[[0-9;]*m", "", raw_text)
            id_match = re.search(r"Sequ\s+\d+\s+(\d+)\s+(.*?)\s{2,}", clean_seqs)
            if id_match:
                sequence_id = int(id_match.group(1))
                seq_name = id_match.group(2).strip()
                ok(f"Auto-selected sequence {sequence_id} '{seq_name}'")
            elif "NO OBJECTS FOUND" in clean_seqs.upper():
                banner("NO SEQUENCES FOUND -- CANNOT AUDIT")
                warn("The currently loaded show has no sequences.")
                warn("Load a show with sequences (e.g. claude_ma2_ctrl),")
                warn("or pass --sequence N to force a specific ID.")
                warn(f"Show reported: {_current_show}")
                return
            else:
                sequence_id = 1
                info("Could not parse sequence list -- falling back to sequence_id=1")

    banner(f"[Skill: {skill['title']} v{skill['version']}]  --  Sequence {sequence_id}")

    findings: list[dict] = []
    cue_entries: list[dict] = []

    # ── Step 1: Get sequence info ────────────────────────────────────────────
    section("Get sequence info", step=1)
    skill_says("call query_object_list for the target sequence. Record cue count and label list.")
    tool_call(f"query_object_list(object_type='cue', sequence_id={sequence_id})")

    t0 = time.perf_counter()
    raw1 = await query_object_list(object_type="cue", sequence_id=sequence_id)
    elapsed = time.perf_counter() - t0
    ok(f"Response received in {elapsed:.2f}s")
    data1 = json.loads(raw1) if isinstance(raw1, str) else raw1
    if isinstance(data1, dict) and "command_sent" in data1:
        telnet(data1["command_sent"])
    show_raw(data1)

    # Parse cue entries from the raw telnet output
    raw_resp = data1.get("raw_response", "") if isinstance(data1, dict) else ""
    # Strip ANSI colour codes
    clean = re.sub(r"\x1b\[[0-9;]*m", "", raw_resp)
    # Match lines like: "Cue  1 1            Go    ..."
    # Columns: pool_idx  cue_num  MIB(optional)  trig  ...
    # list cue has no label column -- capture cue number and trigger type only
    for m in re.finditer(
        r"Cue\s+\d+\s+(\d+(?:\.\d+)?)\s+(\w+)", clean
    ):
        cid_str, trig = m.group(1), m.group(2)
        try:
            cue_entries.append({"id": float(cid_str), "label": "", "trig": trig})
        except ValueError:
            pass

    if cue_entries:
        ok(f"Parsed {len(cue_entries)} cue(s): {[c['id'] for c in cue_entries]}")
    elif "NO OBJECTS FOUND" in clean.upper():
        warn(f"Sequence {sequence_id} has no cues")
        findings.append({"kind": "warning", "detail": f"Sequence {sequence_id} has no cues"})
    else:
        info("Could not parse cue list -- showing raw response above")

    # ── Step 2: Check for gaps ───────────────────────────────────────────────
    section("Check for gaps in cue numbers", step=2)
    skill_says("examine cue numbers for missing integers or jumps > 10. Flag as 'gap' findings.")
    if cue_entries:
        ids = sorted(c["id"] for c in cue_entries)
        for i in range(1, len(ids)):
            gap = ids[i] - ids[i - 1]
            if gap > 10:
                msg = f"Jump of {gap:.0f} between cue {ids[i-1]} and cue {ids[i]}"
                warn(msg)
                findings.append({"kind": "gap", "detail": msg})
        if not any(f["kind"] == "gap" for f in findings):
            ok("No gaps > 10 detected")
    else:
        info("No cues to check")

    # ── Step 3: Check labels ─────────────────────────────────────────────────
    section("Check cue labels", step=3)
    skill_says("flag empty labels or labels matching 'Cue N' (auto-generated) as 'warning'.")
    if cue_entries:
        info("'list cue' has no label column -- label check skipped (navigate to cue pool for labels)")
        ok(f"Parsed {len(cue_entries)} cues")
    else:
        info("No cues to check")

    # ── Step 4: Check timing on suspect cues ────────────────────────────────
    section("Check timing on cues", step=4)
    skill_says("call get_object_info on cues that may have zero fade time.")
    if cue_entries:
        suspect = cue_entries[:2]  # Check first two as representative sample
        for c in suspect:
            obj_id = f"{int(c['id'])} sequence {sequence_id}"
            tool_call(f"get_object_info(object_type='cue', object_id='{obj_id}')")
            try:
                raw_info = await get_object_info(object_type="cue", object_id=obj_id)
                data_info = json.loads(raw_info) if isinstance(raw_info, str) else raw_info
                if isinstance(data_info, dict) and "command_sent" in data_info:
                    telnet(data_info["command_sent"])
                raw_text = (data_info.get("raw_response", "") if isinstance(data_info, dict)
                            else str(data_info))
                clean_info = re.sub(r"\x1b\[[0-9;]*m", "", raw_text)
                # Look for fade time indicators
                fade_match = re.search(r"(?:fade|in time)[:\s]+([\d.]+)", clean_info, re.I)
                fade_val = fade_match.group(1) if fade_match else None
                if fade_val == "0" or fade_val == "0.0":
                    msg = f"Cue {c['id']} has 0s fade time"
                    warn(msg)
                    findings.append({"kind": "timing", "detail": msg})
                else:
                    ok(f"Cue {c['id']}: fade={fade_val or 'not parsed'}")
                show_raw(data_info, max_lines=8)
            except Exception as e:
                info(f"Could not get info for cue {obj_id}: {e}")
    else:
        info("No cues to inspect")

    # ── Step 5: Check sequence trigger type ─────────────────────────────────
    section("Check sequence trigger type", step=5)
    skill_says("verify sequence trigger type (Time/Go/Follow) is consistent with its usage pattern.")
    # MA2 `info sequence N` returns empty -- use trigger types already parsed from the cue list
    if cue_entries:
        from collections import Counter
        trig_counts = Counter(c.get("trig", "?") for c in cue_entries)
        ok(f"Trigger distribution: {dict(trig_counts)}")
        follow_count = trig_counts.get("Follow", 0)
        go_count = trig_counts.get("Go", 0)
        if follow_count and go_count:
            msg = f"{follow_count} Follow cue(s) mixed with {go_count} Go cue(s)"
            warn(msg)
            findings.append({"kind": "warning", "detail": msg})
    else:
        info("No cues to check")

    # ── Step 6: Compress findings ────────────────────────────────────────────
    section("Compress findings (skill output envelope)", step=6)
    skill_says("do NOT return raw cue list -- return JSON with summary, findings, recommendations.")

    gap_count = sum(1 for f in findings if f["kind"] == "gap")
    warn_count = sum(1 for f in findings if f["kind"] == "warning")
    timing_count = sum(1 for f in findings if f["kind"] == "timing")
    mixed_trigger_count = sum(1 for f in findings if f["kind"] == "warning"
                              and "Follow" in f.get("detail", ""))
    summary = (
        f"Sequence {sequence_id}: {len(cue_entries)} cues, "
        f"{gap_count} gaps, {timing_count} timing issues, {mixed_trigger_count} trigger warnings"
    )

    actions: list[str] = []
    if gap_count:
        actions.append("Fill or renumber cues with large jumps")
    if mixed_trigger_count:
        actions.append("Review Follow cues -- verify intentional mix with Go-triggered cues")
    if timing_count:
        actions.append("Set fade times on zero-fade cues if time-triggered")
    if not findings:
        actions.append("Sequence looks healthy -- no action required")

    report = {
        "summary": summary,
        "findings": findings,
        "recommended_actions": actions,
        "state_changes": [],
        "confidence": "high" if cue_entries else "low",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Skill: feedback-investigator
# ---------------------------------------------------------------------------


async def run_feedback_investigator(raw_response: str) -> None:
    skill = _load_skill("feedback-investigator")
    banner(f"[Skill: {skill['title']} v{skill['version']}]")
    info(f"Input response: {raw_response!r}")

    findings: list[dict] = []

    # ── Step 1: Classify ─────────────────────────────────────────────────────
    section("Classify the raw response", step=1)
    skill_says("use decision tree to classify: SUCCESS / ERROR / RIGHTS_DENIED / SYNTAX_ERROR")

    resp_upper = raw_response.upper()
    if "RIGHTS DENIED" in resp_upper or "PERMISSION" in resp_upper:
        feedback_class = "RIGHTS_DENIED"
    elif "UNKNOWN COMMAND" in resp_upper or "SYNTAX" in resp_upper or "ILLEGAL" in resp_upper:
        feedback_class = "SYNTAX_ERROR"
    elif "ERROR" in resp_upper or "FAILED" in resp_upper or "FAULT" in resp_upper:
        feedback_class = "ERROR"
    else:
        feedback_class = "SUCCESS"

    ok(f"FeedbackClass: {feedback_class}")
    findings.append({"kind": "classification", "detail": feedback_class})

    # ── Step 2: Rights check (if RIGHTS_DENIED) ──────────────────────────────
    section("Rights check", step=2)
    if feedback_class == "RIGHTS_DENIED":
        skill_says("call list_system_variables to read $USERRIGHTS and $USER")
        tool_call("list_system_variables(filter_prefix='USER')")
        try:
            raw_vars = await list_system_variables(filter_prefix="USER")
            data_vars = json.loads(raw_vars) if isinstance(raw_vars, str) else raw_vars
            ok("System variables retrieved:")
            show_raw(data_vars, max_lines=12)
            raw_text = (data_vars.get("raw_response", "") if isinstance(data_vars, dict)
                        else str(data_vars))
            clean = re.sub(r"\x1b\[[0-9;]*m", "", raw_text)
            rights_m = re.search(r"\$USERRIGHTS\s*[=:]\s*(\w+)", clean, re.I)
            user_m = re.search(r"\$USER\s*[=:]\s*(\w+)", clean, re.I)
            rights = rights_m.group(1) if rights_m else "unknown"
            user = user_m.group(1) if user_m else "unknown"
            warn(f"User '{user}' has rights level '{rights}' -- insufficient for this operation")
            findings.append({
                "kind": "rights_denied",
                "detail": f"User {user} rights={rights} -- need higher privilege"
            })
        except Exception as e:
            info(f"Could not retrieve system variables: {e}")
    else:
        ok(f"Not a rights issue ({feedback_class}) -- skipping rights check")

    # ── Step 3: State check ──────────────────────────────────────────────────
    section("State check -- verify objects exist", step=3)
    skill_says("call query_object_list(object_type='sequence') to verify objects are present")
    tool_call("query_object_list(object_type='sequence')")
    try:
        raw_seqs = await query_object_list(object_type="sequence")
        data_seqs = json.loads(raw_seqs) if isinstance(raw_seqs, str) else raw_seqs
        ok("Sequences on console:")
        show_raw(data_seqs, max_lines=10)
    except Exception as e:
        info(f"Could not list sequences: {e}")

    # ── Step 4: Compress findings ────────────────────────────────────────────
    section("Compress findings (skill output envelope)", step=4)
    skill_says("return JSON envelope: summary, findings, recommended_actions, confidence")

    actions: list[str] = []
    if feedback_class == "RIGHTS_DENIED":
        actions.append("Log in as a user with higher rights (admin or operator)")
        actions.append("Use require_ma2_right() to check permissions before sending")
    elif feedback_class == "SYNTAX_ERROR":
        actions.append("Check command builder output -- look for quoting or flag errors")
        actions.append("Use search_codebase('command name') to find the builder function")
    elif feedback_class == "ERROR":
        actions.append("Retry with a simpler command to isolate the failure")
    else:
        actions.append("Response appears successful -- no action required")

    report = {
        "summary": f"Classified response as {feedback_class}",
        "findings": findings,
        "recommended_actions": actions,
        "state_changes": [],
        "confidence": "high",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Skill: color-preset-creator
# ---------------------------------------------------------------------------


async def run_color_preset_creator() -> None:
    skill = _load_skill("color-preset-creator")
    banner(f"[Skill: {skill['title']} v{skill['version']}]")

    findings: list[dict] = []
    presets_created: list[dict] = []
    state_changes: list[str] = []

    warn("DESTRUCTIVE -- storing universal color presets with confirm_destructive=True")
    info(f"About to store/overwrite {len(STANDARD_COLOR_PALETTE)} color presets "
         f"(Preset 4.1 - 4.{len(STANDARD_COLOR_PALETTE)})")

    client = await get_client()

    # ── Step 1: Create each preset ───────────────────────────────────────────
    section("Create universal color presets", step=1)
    skill_says("for each color: SelFix all -> set RGB attributes -> store universal preset -> ClearAll.")

    for color in STANDARD_COLOR_PALETTE:
        pid, name = color["id"], color["name"]
        r, g, b = color["r"], color["g"], color["b"]
        print(f"\n   -- Preset 4.{pid}  {name}  R={r} G={g} B={b} --")

        # a) Select all fixtures
        tool_call("client.send_command_with_response('SelFix 1 Thru 9999')")
        await client.send_command_with_response("SelFix 1 Thru 9999")
        telnet("SelFix 1 Thru 9999")

        # b-d) Set RGB channels
        for attr, val in [("ColorRgb1", r), ("ColorRgb2", g), ("ColorRgb3", b)]:
            cmd = f'attribute "{attr}" at {val}'
            tool_call(f"client.send_command_with_response('{cmd}')")
            await client.send_command_with_response(cmd)
            telnet(cmd)

        # e) Store as universal color preset
        tool_call(f"store_new_preset('color', {pid}, universal=True, overwrite=True, confirm_destructive=True)")
        try:
            raw_sp = await store_new_preset(
                preset_type="color",
                preset_id=pid,
                universal=True,
                overwrite=True,
                confirm_destructive=True,
            )
            data_sp = json.loads(raw_sp) if isinstance(raw_sp, str) else raw_sp
            if isinstance(data_sp, dict) and "command_sent" in data_sp:
                telnet(data_sp["command_sent"])
            # Label the preset explicitly (store /overwrite keeps old name)
            await label_or_appearance(
                action="label", object_type="preset", object_id=pid,
                preset_type="color", name=name, confirm_destructive=True,
            )
            ok(f"Stored Preset 4.{pid} '{name}' (universal)")
            presets_created.append({"preset_id": pid, "name": name, "r": r, "g": g, "b": b})
            state_changes.append(f"Preset 4.{pid} '{name}': universal color preset written")
        except Exception as e:
            warn(f"store_new_preset failed for Preset 4.{pid}: {e}")
            findings.append({"kind": "error", "detail": f"Preset 4.{pid} '{name}': {e}"})

        # f) Clear programmer
        await client.send_command_with_response("ClearAll")
        telnet("ClearAll")

    # ── Step 2: Verify pool ──────────────────────────────────────────────────
    section("Verify preset pool", step=2)
    skill_says("call list_preset_pool('color') and count entries.")
    tool_call("list_preset_pool(preset_type='color')")

    raw_pool = await list_preset_pool(preset_type="color")
    data_pool = json.loads(raw_pool) if isinstance(raw_pool, str) else raw_pool
    show_raw(data_pool, max_lines=20)

    # ── Step 3: Compress findings ────────────────────────────────────────────
    section("Compress findings (skill output envelope)", step=3)
    skill_says("return JSON with presets_created, state_changes, findings, confidence.")
    state_changes.append("Programmer: cleared (ClearAll after last store)")

    report = {
        "summary": (
            f"Created {len(presets_created)} universal color preset(s) "
            f"(Preset 4.1 - 4.{len(STANDARD_COLOR_PALETTE)})"
        ),
        "findings": findings,
        "presets_created": presets_created,
        "state_changes": state_changes,
        "recommended_actions": [
            "Run color-palette-sequence-builder to build a cue sequence from these presets",
            "Verify presets on console: list_preset_pool('color')",
        ],
        "confidence": "high" if not findings else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Skill: color-palette-sequence-builder
# ---------------------------------------------------------------------------


async def run_color_palette_sequence_builder(sequence_id: int) -> None:
    skill = _load_skill("color-palette-sequence-builder")
    banner(f"[Skill: {skill['title']} v{skill['version']}]  --  Sequence {sequence_id}")

    findings: list[dict] = []
    cues_created: list[dict] = []
    state_changes: list[str] = []

    # ── Step 1: Audit color presets ──────────────────────────────────────────
    section("Audit color presets", step=1)
    skill_says("call list_preset_pool('color') to discover all color presets in the show.")
    tool_call("list_preset_pool(preset_type='color')")

    raw_pool = await list_preset_pool(preset_type="color")
    data_pool = json.loads(raw_pool) if isinstance(raw_pool, str) else raw_pool
    show_raw(data_pool, max_lines=20)

    # Parse preset entries from the pool response
    color_presets: list[dict] = []
    if isinstance(data_pool, dict):
        entries = data_pool.get("entries", [])
        if entries:
            for entry in entries:
                pid = entry.get("id") or entry.get("index")
                name = entry.get("name") or entry.get("label") or f"Color {pid}"
                if pid is not None:
                    try:
                        color_presets.append({"id": int(pid), "name": str(name).strip()})
                    except (ValueError, TypeError):
                        pass
        if not color_presets:
            # Fallback: parse from raw_response if entries is empty
            # Format: "Color 4.1 4.1  Red      Normal"  or  "Color 4.1 4.1  Name  ..."
            raw_text = data_pool.get("raw_response", "")
            clean = re.sub(r"\x1b\[[0-9;]*m", "", raw_text)
            for m in re.finditer(r"Color\s+4\.(\d+)\s+4\.\d+\s+(\S+)", clean):
                pid_str, name = m.group(1), m.group(2).strip()
                if pid_str:
                    color_presets.append({"id": int(pid_str), "name": name or f"Color {pid_str}"})

    if not color_presets:
        warn("No color presets found in pool -- store color presets first")
        findings.append({"kind": "error", "detail": "No color presets found -- store presets first"})
        print()
        print(json.dumps({
            "summary": "Aborted -- no color presets to build sequence from",
            "findings": findings, "cues_created": [], "state_changes": [],
            "confidence": "high",
        }, indent=2))
        return

    ok(f"Found {len(color_presets)} color preset(s): {[p['id'] for p in color_presets]}")

    # ── Step 2: Validate target sequence ────────────────────────────────────
    section("Validate target sequence", step=2)
    skill_says(f"check whether sequence {sequence_id} already has cues.")
    tool_call(f"query_object_list(object_type='cue', sequence_id={sequence_id})")

    raw_check = await query_object_list(object_type="cue", sequence_id=sequence_id)
    data_check = json.loads(raw_check) if isinstance(raw_check, str) else raw_check
    if isinstance(data_check, dict) and "command_sent" in data_check:
        telnet(data_check["command_sent"])
    existing_clean = re.sub(r"\x1b\[[0-9;]*m", "",
                            data_check.get("raw_response", "") if isinstance(data_check, dict) else "")
    existing_cues = re.findall(r"Cue\s+\d+\s+(\d+(?:\.\d+)?)", existing_clean)
    if existing_cues:
        warn(f"Sequence {sequence_id} already has {len(existing_cues)} cue(s) -- overwrite=True will replace them")
    else:
        ok(f"Sequence {sequence_id} is empty -- safe to build")

    # ── Step 3: Select -> apply preset -> store cue (one per color preset) ────
    section("Build palette cues (SelFix -> Preset -> StoreCue)", step=3)
    skill_says("for each color preset: select all fixtures, apply preset (reference), store cue.")
    warn("DESTRUCTIVE -- storing cues into sequence with confirm_destructive=True")

    client = await get_client()

    for cue_num, preset in enumerate(sorted(color_presets, key=lambda p: p["id"]), start=1):
        pid, pname = preset["id"], preset["name"]
        print(f"\n   -- Preset {pid} '{pname}' -> Cue {cue_num} --")

        # a) Select all fixtures globally
        tool_call("client.send_command_with_response('SelFix 1 Thru 9999')")
        selfix_resp = await client.send_command_with_response("SelFix 1 Thru 9999")
        telnet("SelFix 1 Thru 9999")
        clean_sf = re.sub(r"\x1b\[[0-9;]*m", "", selfix_resp or "")
        if "error" in clean_sf.lower():
            warn(f"SelFix may have failed: {clean_sf[:80]}")

        # b) Apply preset to programmer (creates preset reference, not raw values)
        tool_call(f"apply_preset(preset_type='color', preset_id={pid})")
        try:
            raw_ap = await apply_preset(preset_type="color", preset_id=pid)
            data_ap = json.loads(raw_ap) if isinstance(raw_ap, str) else raw_ap
            if isinstance(data_ap, dict) and "command_sent" in data_ap:
                telnet(data_ap["command_sent"])
            ok(f"Preset 4.{pid} in programmer")
        except Exception as e:
            # Fallback: send Preset 4.N directly
            warn(f"apply_preset raised {e} -- using direct Preset 4.{pid} command")
            await client.send_command_with_response(f"Preset 4.{pid}")
            telnet(f"Preset 4.{pid}")
            ok(f"Preset 4.{pid} applied via direct command")

        # c) Store cue (with preset reference, not raw values)
        tool_call(f"store_current_cue(cue_number={cue_num}, sequence_id={sequence_id}, "
                  f"label='{pname}', overwrite=True, confirm_destructive=True)")
        try:
            raw_sc = await store_current_cue(
                cue_number=cue_num,
                sequence_id=sequence_id,
                label=pname,
                overwrite=True,
                confirm_destructive=True,
            )
            data_sc = json.loads(raw_sc) if isinstance(raw_sc, str) else raw_sc
            if isinstance(data_sc, dict):
                cmds = data_sc.get("commands_sent") or data_sc.get("command_sent", "")
                for cmd in (cmds if isinstance(cmds, list) else [cmds]):
                    if cmd:
                        telnet(cmd)
            ok(f"Stored cue {cue_num} '{pname}' (references Preset 4.{pid})")
            cues_created.append({"cue": cue_num, "preset_id": pid, "label": pname})
            state_changes.append(f"Sequence {sequence_id} cue {cue_num}: '{pname}' -> Preset 4.{pid} reference")
        except Exception as e:
            warn(f"store_current_cue failed: {e}")
            findings.append({"kind": "error", "detail": f"Cue {cue_num} (Preset {pid}): {e}"})

        # d) Set cue appearance color -- name-first lookup, id fallback
        rgb = COLOR_NAME_RGB.get(pname.lower())
        if rgb is None:
            fallback = next((p for p in STANDARD_COLOR_PALETTE if p["id"] == pid), None)
            if fallback:
                rgb = {"r": fallback["r"], "g": fallback["g"], "b": fallback["b"]}
        if rgb:
            obj_id = f"{cue_num} sequence {sequence_id}"
            r, g, b = rgb["r"], rgb["g"], rgb["b"]
            tool_call(f"label_or_appearance(action='appearance', object_type='cue', object_id='{obj_id}', "
                      f"red={r}, green={g}, blue={b}, confirm_destructive=True)")
            try:
                raw_app = await label_or_appearance(
                    action="appearance",
                    object_type="cue",
                    object_id=obj_id,
                    red=r,
                    green=g,
                    blue=b,
                    confirm_destructive=True,
                )
                data_app = json.loads(raw_app) if isinstance(raw_app, str) else raw_app
                if isinstance(data_app, dict) and "command_sent" in data_app:
                    telnet(data_app["command_sent"])
                ok(f"Cue {cue_num} '{pname}' color set (R={r} G={g} B={b})")
            except Exception as e:
                warn(f"label_or_appearance failed for cue {cue_num}: {e}")
        else:
            info(f"No RGB mapping for '{pname}' (id={pid}) -- skipping appearance")

        # e) Clear programmer before next iteration
        await client.send_command_with_response("ClearAll")
        telnet("ClearAll")

    # ── Label the sequence ───────────────────────────────────────────────────
    section("Label sequence", step=4)
    skill_says("set sequence name to 'Color Palette' so it is not auto-named from the first cue.")
    tool_call(f"label_or_appearance(action='label', object_type='sequence', object_id={sequence_id}, "
              f"name='Color Palette', confirm_destructive=True)")
    try:
        raw_lbl = await label_or_appearance(
            action="label",
            object_type="sequence",
            object_id=sequence_id,
            name="Color Palette",
            confirm_destructive=True,
        )
        data_lbl = json.loads(raw_lbl) if isinstance(raw_lbl, str) else raw_lbl
        if isinstance(data_lbl, dict) and "command_sent" in data_lbl:
            telnet(data_lbl["command_sent"])
        ok(f"Sequence {sequence_id} labeled 'Color Palette'")
        state_changes.append(f"Sequence {sequence_id}: labeled 'Color Palette'")
    except Exception as e:
        warn(f"label_or_appearance (sequence label) failed: {e}")

    # ── Step 5: Verify ───────────────────────────────────────────────────────
    section("Verify sequence", step=5)
    skill_says(f"list cues in sequence {sequence_id} and count them.")
    tool_call(f"query_object_list(object_type='cue', sequence_id={sequence_id})")

    raw_verify = await query_object_list(object_type="cue", sequence_id=sequence_id)
    data_verify = json.loads(raw_verify) if isinstance(raw_verify, str) else raw_verify
    if isinstance(data_verify, dict) and "command_sent" in data_verify:
        telnet(data_verify["command_sent"])
    verify_clean = re.sub(r"\x1b\[[0-9;]*m", "",
                          data_verify.get("raw_response", "") if isinstance(data_verify, dict) else "")
    found_cues = re.findall(r"Cue\s+\d+\s+(\d+(?:\.\d+)?)", verify_clean)
    if len(found_cues) == len(color_presets):
        ok(f"Verified: {len(found_cues)} cue(s) in sequence {sequence_id} -- matches preset count")
    else:
        warn(f"Mismatch: expected {len(color_presets)} cues, found {len(found_cues)}")
        findings.append({"kind": "error",
                         "detail": f"Expected {len(color_presets)} cues, found {len(found_cues)}"})

    # ── Step 6: Compress findings ────────────────────────────────────────────
    section("Compress findings (skill output envelope)", step=6)
    skill_says("return JSON with summary, cues_created, state_changes, findings, confidence.")

    report = {
        "summary": (
            f"Built {len(cues_created)}-cue color palette sequence in sequence {sequence_id} "
            f"({len(color_presets)} preset(s) -> {len(cues_created)} cue(s))"
        ),
        "findings": findings,
        "cues_created": cues_created,
        "state_changes": state_changes,
        "recommended_actions": [
            f"Assign sequence {sequence_id} to an executor to use as a color palette fader",
            "Set trigger type to 'Go' for manual step-through",
        ],
        "confidence": "high" if not findings else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Skill: sequence-executor-assigner
# ---------------------------------------------------------------------------


async def run_sequence_executor_assigner(sequence_id: int, executor_id: int | None) -> None:
    skill = _load_skill("sequence-executor-assigner")
    banner(f"[Skill: {skill['title']} v{skill['version']}]  --  Sequence {sequence_id}")

    findings: list[dict] = []
    state_changes: list[str] = []

    warn("DESTRUCTIVE -- assigning sequence to executor with confirm_destructive=True")
    info(f"Sequence {sequence_id} -> Executor {executor_id or 'auto-detect'}")

    # ── Step 1: Detect a free executor ───────────────────────────────────────
    section("Detect free executor", step=1)
    skill_says("call get_executor_status() to list all executors, parse for free slots.")
    tool_call("get_executor_status()")

    raw_all = await get_executor_status()
    data_all = json.loads(raw_all) if isinstance(raw_all, str) else raw_all
    if isinstance(data_all, dict) and "command_sent" in data_all:
        telnet(data_all["command_sent"])
    show_raw(data_all, max_lines=20)

    chosen_id: int
    if executor_id is not None:
        chosen_id = executor_id
        info(f"Using explicitly provided executor_id={chosen_id}")
    else:
        # Check whether default executor 201 is free
        raw_text_all = (data_all.get("raw_response", "") if isinstance(data_all, dict)
                        else str(data_all))
        clean_all = re.sub(r"\x1b\[[0-9;]*m", "", raw_text_all)
        # Occupied executors have "Seq N" or "Sequence=" next to their ID
        occupied_ids: set[int] = set()
        for m in re.finditer(r"Executor\s+\d+\s+(\d+)\s+\S+", clean_all):
            occupied_ids.add(int(m.group(1)))
        # Also match "Exec  N  Name  ..." style lines
        for m in re.finditer(r"Exec\s+\d+\s+(\d+)\s+\S+", clean_all):
            occupied_ids.add(int(m.group(1)))

        if 201 not in occupied_ids:
            chosen_id = 201
            ok(f"Default executor 201 is free -- using it")
        else:
            # Fall back to lowest free ID ≥ 1
            for candidate in range(1, 241):
                if candidate not in occupied_ids:
                    chosen_id = candidate
                    warn(f"Executor 201 occupied -- using first free executor {chosen_id}")
                    break
            else:
                warn("No free executors found (1-240)")
                findings.append({"kind": "error", "detail": "No free executors found"})
                print()
                print(json.dumps({
                    "summary": "Aborted -- no free executors",
                    "findings": findings, "assignment": None, "state_changes": [],
                    "confidence": "high",
                }, indent=2))
                return

    # ── Step 2: Assign the sequence ──────────────────────────────────────────
    section("Assign sequence to executor", step=2)
    skill_says(f"assign sequence {sequence_id} to executor {chosen_id}.")
    warn(f"About to assign Sequence {sequence_id} to Executor {chosen_id}")
    tool_call(
        f"assign_object(mode='assign', source_type='sequence', source_id={sequence_id}, "
        f"target_type='executor', target_id={chosen_id}, confirm_destructive=True)"
    )

    try:
        raw_assign = await assign_object(
            mode="assign",
            source_type="sequence",
            source_id=sequence_id,
            target_type="executor",
            target_id=chosen_id,
            confirm_destructive=True,
        )
        data_assign = json.loads(raw_assign) if isinstance(raw_assign, str) else raw_assign
        if isinstance(data_assign, dict) and "command_sent" in data_assign:
            telnet(data_assign["command_sent"])
        show_raw(data_assign, max_lines=10)
        ok(f"assign_object call completed")
        state_changes.append(
            f"Executor {chosen_id}: Sequence {sequence_id} assigned (color palette fader)"
        )
    except Exception as e:
        warn(f"assign_object failed: {e}")
        findings.append({"kind": "error", "detail": f"assign_object: {e}"})

    # ── Step 3: Verify the assignment ────────────────────────────────────────
    section("Verify assignment", step=3)
    skill_says(f"call get_executor_status(executor_id={chosen_id}) and confirm Sequence {sequence_id} appears.")
    tool_call(f"get_executor_status(executor_id={chosen_id})")

    confirmed = False
    try:
        raw_verify = await get_executor_status(executor_id=chosen_id)
        data_verify = json.loads(raw_verify) if isinstance(raw_verify, str) else raw_verify
        if isinstance(data_verify, dict) and "command_sent" in data_verify:
            telnet(data_verify["command_sent"])
        show_raw(data_verify, max_lines=15)

        raw_text_v = (data_verify.get("raw_response", "") if isinstance(data_verify, dict)
                      else str(data_verify))
        clean_v = re.sub(r"\x1b\[[0-9;]*m", "", raw_text_v)
        # Confirm sequence number appears anywhere in the response
        if re.search(rf"\b{sequence_id}\b", clean_v):
            confirmed = True
            ok(f"Confirmed: Executor {chosen_id} shows Sequence {sequence_id}")
            findings.append({"kind": "ok", "detail": f"Executor {chosen_id} assigned Sequence {sequence_id}"})
        else:
            warn(f"Assignment not confirmed -- Sequence {sequence_id} not found in executor status")
            findings.append({"kind": "error", "detail": "Assignment not confirmed in executor status"})
    except Exception as e:
        warn(f"get_executor_status failed: {e}")
        findings.append({"kind": "error", "detail": f"get_executor_status: {e}"})

    # ── Label executor (if assignment confirmed) ─────────────────────────────
    if confirmed:
        section("Label executor", step=4)
        skill_says(f"set executor {chosen_id} label to match sequence name.")
        tool_call(f"label_or_appearance(action='label', object_type='executor', object_id={chosen_id}, "
                  f"name='Color Palette', confirm_destructive=True)")
        try:
            raw_elbl = await label_or_appearance(
                action="label",
                object_type="executor",
                object_id=chosen_id,
                name="Color Palette",
                confirm_destructive=True,
            )
            data_elbl = json.loads(raw_elbl) if isinstance(raw_elbl, str) else raw_elbl
            if isinstance(data_elbl, dict) and "command_sent" in data_elbl:
                telnet(data_elbl["command_sent"])
            ok(f"Executor {chosen_id} labeled 'Color Palette'")
            state_changes.append(f"Executor {chosen_id}: labeled 'Color Palette'")
        except Exception as e:
            warn(f"label_or_appearance (executor label) failed: {e}")

    # ── Step 5: Compress findings ────────────────────────────────────────────
    section("Compress findings (skill output envelope)", step=5)
    skill_says("return JSON with assignment details, state_changes, confidence.")

    report = {
        "summary": f"Assigned Sequence {sequence_id} to Executor {chosen_id}",
        "findings": findings,
        "assignment": {
            "sequence_id": sequence_id,
            "executor_id": chosen_id,
            "confirmed": confirmed,
        },
        "state_changes": state_changes,
        "recommended_actions": [
            f"Press Go on Executor {chosen_id} to step through the 8 color cues",
            "Edit Preset 4.1 to change the Red hue live (reference update)",
        ],
        "confidence": "high" if confirmed else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Skill: hue-palette-creator  (96 presets, 4.101-4.196)
# ---------------------------------------------------------------------------


async def run_hue_palette_creator() -> None:
    skill = _load_skill("hue-palette-creator")
    banner(f"[Skill: {skill['title']} v{skill['version']}]")

    findings: list[dict] = []
    presets_created: list[dict] = []
    state_changes: list[str] = []

    warn("DESTRUCTIVE -- storing 96 universal color presets (4.101-4.196) with confirm_destructive=True")
    info(f"12 hues × 8 saturation steps = {len(HUE_PALETTE_96)} presets")

    client = await get_client()

    section("Create 96 universal hue presets (SelFix -> RGB attrs -> store -> label -> ClearAll)", step=1)
    skill_says("for each of 96 entries: set ColorRgb1/2/3, store universal, label, ClearAll.")

    for color in HUE_PALETTE_96:
        pid, name = color["id"], color["name"]
        r, g, b = color["r"], color["g"], color["b"]
        h, s, br = color["h"], color["s"], color["br"]
        print(f"\n   -- Preset 4.{pid}  {name}  H={h} S={s} Br={br}  ->  R={r} G={g} B={b} --")

        await client.send_command_with_response("SelFix 1 Thru 9999")
        telnet("SelFix 1 Thru 9999")

        for attr, val in [("ColorRgb1", r), ("ColorRgb2", g), ("ColorRgb3", b)]:
            cmd = f'attribute "{attr}" at {val}'
            await client.send_command_with_response(cmd)
            telnet(cmd)

        tool_call(f"store_new_preset('color', {pid}, universal=True, overwrite=True, confirm_destructive=True)")
        try:
            raw_sp = await store_new_preset(
                preset_type="color", preset_id=pid,
                universal=True, overwrite=True, confirm_destructive=True,
            )
            data_sp = json.loads(raw_sp) if isinstance(raw_sp, str) else raw_sp
            if isinstance(data_sp, dict) and "command_sent" in data_sp:
                telnet(data_sp["command_sent"])

            # Label immediately — store /overwrite never updates the slot name
            await label_or_appearance(
                action="label", object_type="preset", object_id=pid,
                preset_type="color", name=name, confirm_destructive=True,
            )
            ok(f"Preset 4.{pid} '{name}' stored + labeled")
            presets_created.append({"preset_id": pid, "name": name, "h": h, "s": s})
            state_changes.append(f"Preset 4.{pid} '{name}': universal hue preset written")
        except Exception as e:
            warn(f"store_new_preset failed for Preset 4.{pid}: {e}")
            findings.append({"kind": "error", "detail": f"Preset 4.{pid} '{name}': {e}"})

        await client.send_command_with_response("ClearAll")
        telnet("ClearAll")

    section("Verify preset pool (spot-check first and last)", step=2)
    skill_says("list_preset_pool and confirm 96 entries in 4.101-4.196 range.")
    tool_call("list_preset_pool(preset_type='color')")
    raw_pool = await list_preset_pool(preset_type="color")
    data_pool = json.loads(raw_pool) if isinstance(raw_pool, str) else raw_pool
    show_raw(data_pool, max_lines=25)

    section("Compress findings", step=3)
    report = {
        "summary": f"Created {len(presets_created)} universal hue presets (4.101–4.196)",
        "findings": findings,
        "presets_created": presets_created,
        "state_changes": state_changes,
        "recommended_actions": [
            "Run hue-sequence-builder to build the 6 paired sequences",
            "Or run full-hue-expansion to do everything in one pass",
        ],
        "confidence": "high" if not findings else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Skill: hue-sequence-builder  (one hue pair -> 16-cue sequence)
# ---------------------------------------------------------------------------


async def run_hue_sequence_builder(pair_index: int, sequence_id: int, executor_id: int) -> None:
    """Build a 16-cue sequence for one adjacent hue pair and assign it to an executor."""
    skill = _load_skill("hue-sequence-builder")

    hi_a, hi_b, seq_label, _default_seq, _default_exec = HUE_PAIRS[pair_index]
    hue_a_name = _HUES[hi_a][0]
    hue_b_name = _HUES[hi_b][0]

    banner(f"[Skill: {skill['title']} v{skill['version']}]  --  {seq_label}  ->  Seq {sequence_id}  Exec {executor_id}")

    findings: list[dict] = []
    cues_created: list[dict] = []
    state_changes: list[str] = []

    warn(f"DESTRUCTIVE -- building 16 cues in Seq {sequence_id} ({seq_label}) with confirm_destructive=True")

    # Slice the 16 preset entries for this hue pair
    slice_a = HUE_PALETTE_96[hi_a * 8 : hi_a * 8 + 8]
    slice_b = HUE_PALETTE_96[hi_b * 8 : hi_b * 8 + 8]
    presets_for_seq = slice_a + slice_b  # 16 entries total

    client = await get_client()

    # ── Step 1: Build 16 cues ────────────────────────────────────────────────
    section(f"Build 16 cues: {hue_a_name} (cues 1-8) + {hue_b_name} (cues 9-16)", step=1)
    skill_says("SelFix -> apply_preset -> store_cue (label) -> appearance (HSB) -> ClearAll, × 16.")

    for cue_num, preset in enumerate(presets_for_seq, start=1):
        pid, pname = preset["id"], preset["name"]
        h, s, br = preset["h"], preset["s"], preset["br"]
        r, g, b = preset["r"], preset["g"], preset["b"]
        print(f"\n   -- Cue {cue_num:2d}  Preset 4.{pid}  '{pname}'  H={h} S={s} --")

        # a) Select all fixtures
        await client.send_command_with_response("SelFix 1 Thru 9999")
        telnet("SelFix 1 Thru 9999")

        # b) Apply preset (puts live reference into programmer)
        tool_call(f"apply_preset(preset_type='color', preset_id={pid})")
        try:
            raw_ap = await apply_preset(preset_type="color", preset_id=pid)
            data_ap = json.loads(raw_ap) if isinstance(raw_ap, str) else raw_ap
            if isinstance(data_ap, dict) and "command_sent" in data_ap:
                telnet(data_ap["command_sent"])
        except Exception:
            await client.send_command_with_response(f"Preset 4.{pid}")
            telnet(f"Preset 4.{pid}")

        # c) Store cue with correct name
        tool_call(f"store_current_cue(cue_number={cue_num}, sequence_id={sequence_id}, label='{pname}', overwrite=True, confirm_destructive=True)")
        try:
            raw_sc = await store_current_cue(
                cue_number=cue_num, sequence_id=sequence_id,
                label=pname, overwrite=True, confirm_destructive=True,
            )
            data_sc = json.loads(raw_sc) if isinstance(raw_sc, str) else raw_sc
            if isinstance(data_sc, dict):
                for cmd in ([data_sc.get("commands_sent")] if not isinstance(data_sc.get("commands_sent"), list)
                            else data_sc.get("commands_sent", [])):
                    if cmd:
                        telnet(cmd)
            ok(f"Cue {cue_num} '{pname}' stored")
            cues_created.append({"cue": cue_num, "preset_id": pid, "label": pname})
            state_changes.append(f"Seq {sequence_id} cue {cue_num}: '{pname}' -> Preset 4.{pid}")
        except Exception as e:
            warn(f"store_current_cue failed for cue {cue_num}: {e}")
            findings.append({"kind": "error", "detail": f"Cue {cue_num} '{pname}': {e}"})

        # d) Color-code the cue using HSB (matches human perception of the hue)
        obj_id = f"{cue_num} sequence {sequence_id}"
        tool_call(f"label_or_appearance(action='appearance', object_type='cue', object_id='{obj_id}', hue={h}, saturation={s}, brightness={br}, confirm_destructive=True)")
        try:
            raw_app = await label_or_appearance(
                action="appearance", object_type="cue", object_id=obj_id,
                hue=h, saturation=s, brightness=br,
                confirm_destructive=True,
            )
            data_app = json.loads(raw_app) if isinstance(raw_app, str) else raw_app
            if isinstance(data_app, dict) and "command_sent" in data_app:
                telnet(data_app["command_sent"])
            ok(f"Cue {cue_num} appearance set H={h} S={s}")
        except Exception as e:
            warn(f"label_or_appearance failed for cue {cue_num}: {e}")

        # e) Clear programmer
        await client.send_command_with_response("ClearAll")
        telnet("ClearAll")

    # ── Step 2: Label the sequence ───────────────────────────────────────────
    section(f"Label sequence {sequence_id} -> '{seq_label}'", step=2)
    tool_call(f"label_or_appearance(action='label', object_type='sequence', object_id={sequence_id}, name='{seq_label}', confirm_destructive=True)")
    try:
        raw_lbl = await label_or_appearance(
            action="label", object_type="sequence", object_id=sequence_id,
            name=seq_label, confirm_destructive=True,
        )
        data_lbl = json.loads(raw_lbl) if isinstance(raw_lbl, str) else raw_lbl
        if isinstance(data_lbl, dict) and "command_sent" in data_lbl:
            telnet(data_lbl["command_sent"])
        ok(f"Sequence {sequence_id} labeled '{seq_label}'")
        state_changes.append(f"Sequence {sequence_id}: labeled '{seq_label}'")
    except Exception as e:
        warn(f"sequence label failed: {e}")

    # ── Step 3: Assign to executor ───────────────────────────────────────────
    section(f"Assign Seq {sequence_id} -> Executor {executor_id}", step=3)
    warn(f"About to assign Sequence {sequence_id} to Executor {executor_id}")
    tool_call(f"assign_object(mode='assign', source_type='sequence', source_id={sequence_id}, target_type='executor', target_id={executor_id}, confirm_destructive=True)")
    confirmed = False
    try:
        raw_asgn = await assign_object(
            mode="assign", source_type="sequence", source_id=sequence_id,
            target_type="executor", target_id=executor_id, confirm_destructive=True,
        )
        data_asgn = json.loads(raw_asgn) if isinstance(raw_asgn, str) else raw_asgn
        if isinstance(data_asgn, dict) and "command_sent" in data_asgn:
            telnet(data_asgn["command_sent"])

        # Verify and label executor
        raw_v = await get_executor_status(executor_id=executor_id)
        data_v = json.loads(raw_v) if isinstance(raw_v, str) else raw_v
        clean_v = re.sub(r"\x1b\[[0-9;]*m", "", data_v.get("raw_response", "") if isinstance(data_v, dict) else "")
        if re.search(rf"\b{sequence_id}\b", clean_v):
            confirmed = True
            ok(f"Executor {executor_id} confirmed Seq {sequence_id}")

        raw_elbl = await label_or_appearance(
            action="label", object_type="executor", object_id=executor_id,
            name=seq_label, confirm_destructive=True,
        )
        data_elbl = json.loads(raw_elbl) if isinstance(raw_elbl, str) else raw_elbl
        if isinstance(data_elbl, dict) and "command_sent" in data_elbl:
            telnet(data_elbl["command_sent"])
        ok(f"Executor {executor_id} labeled '{seq_label}'")
        state_changes.append(f"Executor {executor_id}: Seq {sequence_id} assigned + labeled '{seq_label}'")
    except Exception as e:
        warn(f"assign/label executor failed: {e}")
        findings.append({"kind": "error", "detail": f"Executor {executor_id}: {e}"})

    # ── Step 4: Verify cue count ─────────────────────────────────────────────
    section("Verify cue count", step=4)
    raw_vc = await query_object_list(object_type="cue", sequence_id=sequence_id)
    data_vc = json.loads(raw_vc) if isinstance(raw_vc, str) else raw_vc
    vc_clean = re.sub(r"\x1b\[[0-9;]*m", "", data_vc.get("raw_response", "") if isinstance(data_vc, dict) else "")
    found = re.findall(r"Cue\s+\d+\s+(\d+(?:\.\d+)?)", vc_clean)
    if len(found) == 16:
        ok(f"Verified: 16 cues in sequence {sequence_id}")
    else:
        warn(f"Expected 16 cues, found {len(found)}")
        findings.append({"kind": "error", "detail": f"Expected 16 cues, found {len(found)}"})

    # ── Step 5: Compress ─────────────────────────────────────────────────────
    section("Compress findings", step=5)
    report = {
        "summary": f"Built '{seq_label}' — {len(cues_created)} cues in Seq {sequence_id}, Exec {executor_id} {'confirmed' if confirmed else 'unconfirmed'}",
        "findings": findings,
        "cues_created": cues_created,
        "state_changes": state_changes,
        "confidence": "high" if not findings and confirmed else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Shared helper: build a sequence and assign to a page-qualified executor
# ---------------------------------------------------------------------------


async def _build_sequence_on_page(
    seq_id: int,
    seq_label: str,
    page: int,
    exec_num: int,
    presets: list[dict],
    exec_h: int,
    exec_s: int,
) -> dict:
    """Build N cues from preset entries, assign to Page P.exec_num, label + color executor.

    Uses page-qualified raw MA2 commands (``Page P.E`` syntax) for assign/label/appearance
    because those MCP tools only address executors on the current page.
    """
    client = await get_client()
    findings: list[dict] = []
    cues_created: list[dict] = []
    state_changes: list[str] = []

    # Build each cue
    for cue_num, preset in enumerate(presets, start=1):
        pid, pname = preset["id"], preset["name"]
        h, s, br = preset["h"], preset["s"], preset["br"]
        print(f"\n   -- Cue {cue_num:2d}  Preset 4.{pid}  '{pname}'  H={h} S={s} --")

        await client.send_command_with_response("SelFix 1 Thru 9999")
        telnet("SelFix 1 Thru 9999")

        try:
            raw_ap = await apply_preset(preset_type="color", preset_id=pid)
            data_ap = json.loads(raw_ap) if isinstance(raw_ap, str) else raw_ap
            if isinstance(data_ap, dict) and "command_sent" in data_ap:
                telnet(data_ap["command_sent"])
        except Exception:
            await client.send_command_with_response(f"Preset 4.{pid}")
            telnet(f"Preset 4.{pid}")

        tool_call(f"store_current_cue({cue_num}, seq={seq_id}, '{pname}')")
        try:
            raw_sc = await store_current_cue(
                cue_number=cue_num, sequence_id=seq_id,
                label=pname, overwrite=True, confirm_destructive=True,
            )
            data_sc = json.loads(raw_sc) if isinstance(raw_sc, str) else raw_sc
            if isinstance(data_sc, dict):
                for cmd in (
                    [data_sc.get("commands_sent")]
                    if not isinstance(data_sc.get("commands_sent"), list)
                    else data_sc.get("commands_sent", [])
                ):
                    if cmd:
                        telnet(cmd)
            ok(f"Cue {cue_num} '{pname}' stored")
            cues_created.append({"cue": cue_num, "preset_id": pid, "label": pname})
            state_changes.append(f"Seq {seq_id} cue {cue_num}: '{pname}' -> Preset 4.{pid}")
        except Exception as e:
            warn(f"store_current_cue failed cue {cue_num}: {e}")
            findings.append({"kind": "error", "detail": f"Cue {cue_num} '{pname}': {e}"})

        obj_id = f"{cue_num} sequence {seq_id}"
        try:
            raw_app = await label_or_appearance(
                action="appearance", object_type="cue", object_id=obj_id,
                hue=h, saturation=s, brightness=br,
                confirm_destructive=True,
            )
            data_app = json.loads(raw_app) if isinstance(raw_app, str) else raw_app
            if isinstance(data_app, dict) and "command_sent" in data_app:
                telnet(data_app["command_sent"])
            ok(f"Cue {cue_num} appearance H={h} S={s}")
        except Exception as e:
            warn(f"appearance failed cue {cue_num}: {e}")

        await client.send_command_with_response("ClearAll")
        telnet("ClearAll")

    # Label sequence
    try:
        raw_lbl = await label_or_appearance(
            action="label", object_type="sequence", object_id=seq_id,
            name=seq_label, confirm_destructive=True,
        )
        data_lbl = json.loads(raw_lbl) if isinstance(raw_lbl, str) else raw_lbl
        if isinstance(data_lbl, dict) and "command_sent" in data_lbl:
            telnet(data_lbl["command_sent"])
        ok(f"Sequence {seq_id} labeled '{seq_label}'")
        state_changes.append(f"Sequence {seq_id}: labeled '{seq_label}'")
    except Exception as e:
        warn(f"sequence label failed: {e}")

    # Assign, label, and color the page-qualified executor
    # Syntax: Executor P.E dot-notation (NOT "Page P.E" — that is rejected by MA2)
    for raw_cmd, desc in [
        (f"Assign Sequence {seq_id} At Executor {page}.{exec_num}",
         f"Seq {seq_id} -> Executor {page}.{exec_num}"),
        (f'Label Executor {page}.{exec_num} "{seq_label}"',
         f"Executor {page}.{exec_num} labeled '{seq_label}'"),
        (f"Appearance Executor {page}.{exec_num} /h={exec_h} /s={exec_s} /br=100",
         f"Executor {page}.{exec_num} appearance H={exec_h} S={exec_s}"),
    ]:
        telnet(raw_cmd)
        try:
            resp = await client.send_command_with_response(raw_cmd)
            if isinstance(resp, str) and resp.strip().startswith("Error"):
                raise RuntimeError(resp.strip())
            ok(desc)
            state_changes.append(desc)
        except Exception as e:
            warn(f"command failed: {raw_cmd}: {e}")
            findings.append({"kind": "error", "detail": f"{raw_cmd}: {e}"})

    return {
        "seq_id": seq_id,
        "seq_label": seq_label,
        "cues_created": cues_created,
        "findings": findings,
        "state_changes": state_changes,
    }


# ---------------------------------------------------------------------------
# Group A: Saturation Bands  (Page 2, Seq 106-113, 8 × 12 cues)
# ---------------------------------------------------------------------------


async def run_sat_bands_creator() -> None:
    """Build 8 saturation-band sequences on Page 2 -- one per saturation level, 12 hues each."""
    page = 2
    page_name = "Sat Bands"
    banner(f"GROUP A -- SAT BANDS  --  Page {page} '{page_name}'  Seq 106-113")
    warn(f"DESTRUCTIVE -- building 8 sequences x 12 cues on Page {page}")

    findings_all: list[dict] = []
    state_changes_all: list[str] = []

    client = await get_client()

    section(f"Create/label Page {page} '{page_name}'")
    await navigate_page(action="goto", page_number=page, create_if_missing=True)
    lp = f'Label Page {page} "{page_name}"'
    await client.send_command_with_response(lp)
    telnet(lp)
    ok(f"Page {page} '{page_name}' ready")

    for s_idx, (sval, ssuffix) in enumerate(_SAT_STEPS):
        seq_id = 106 + s_idx
        exec_num = s_idx + 1
        seq_label = f"{ssuffix} Band"
        # 12 cues: one per hue at this fixed saturation step
        presets = [HUE_PALETTE_96[hi * 8 + s_idx] for hi in range(12)]
        # Executor appearance: sweep rainbow hue as saturation decreases
        exec_h = s_idx * 30

        section(f"Seq {seq_id} '{seq_label}' -> Page {page}.{exec_num}", step=s_idx + 1)
        result = await _build_sequence_on_page(
            seq_id=seq_id, seq_label=seq_label,
            page=page, exec_num=exec_num,
            presets=presets, exec_h=exec_h, exec_s=sval,
        )
        findings_all.extend(result["findings"])
        state_changes_all.extend(result["state_changes"])

    section("Compress findings")
    report = {
        "summary": f"Built 8 saturation-band sequences on Page {page} '{page_name}'",
        "findings": findings_all,
        "state_changes": state_changes_all,
        "confidence": "high" if not findings_all else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Group B: Hue Faders  (Page 3, Seq 114-125, 12 × 8 cues)
# ---------------------------------------------------------------------------


async def run_hue_faders_creator() -> None:
    """Build 12 single-hue sequences on Page 3 -- one per hue, 8 saturation steps each."""
    page = 3
    page_name = "Hue Faders"
    banner(f"GROUP B -- HUE FADERS  --  Page {page} '{page_name}'  Seq 114-125")
    warn(f"DESTRUCTIVE -- building 12 sequences x 8 cues on Page {page}")

    findings_all: list[dict] = []
    state_changes_all: list[str] = []

    client = await get_client()

    section(f"Create/label Page {page} '{page_name}'")
    await navigate_page(action="goto", page_number=page, create_if_missing=True)
    lp = f'Label Page {page} "{page_name}"'
    await client.send_command_with_response(lp)
    telnet(lp)
    ok(f"Page {page} '{page_name}' ready")

    for h_idx, (hname, hdeg) in enumerate(_HUES):
        seq_id = 114 + h_idx
        exec_num = h_idx + 1
        presets = HUE_PALETTE_96[h_idx * 8 : h_idx * 8 + 8]

        section(f"Seq {seq_id} '{hname}' -> Page {page}.{exec_num}", step=h_idx + 1)
        result = await _build_sequence_on_page(
            seq_id=seq_id, seq_label=hname,
            page=page, exec_num=exec_num,
            presets=presets, exec_h=hdeg, exec_s=100,
        )
        findings_all.extend(result["findings"])
        state_changes_all.extend(result["state_changes"])

    section("Compress findings")
    report = {
        "summary": f"Built 12 single-hue sequences on Page {page} '{page_name}'",
        "findings": findings_all,
        "state_changes": state_changes_all,
        "confidence": "high" if not findings_all else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Group C: Temperature Split  (Page 4, Seq 126-127, 40+56 cues)
# ---------------------------------------------------------------------------


async def run_temperature_creator() -> None:
    """Build Warm (40 cues, hue indices 0-4) + Cool (56 cues, hue indices 5-11) on Page 4."""
    page = 4
    page_name = "Temperature"
    banner(f"GROUP C -- TEMPERATURE  --  Page {page} '{page_name}'  Seq 126-127")
    warn(f"DESTRUCTIVE -- building Warm (40 cues) + Cool (56 cues) on Page {page}")

    findings_all: list[dict] = []
    state_changes_all: list[str] = []

    client = await get_client()

    section(f"Create/label Page {page} '{page_name}'")
    await navigate_page(action="goto", page_number=page, create_if_missing=True)
    lp = f'Label Page {page} "{page_name}"'
    await client.send_command_with_response(lp)
    telnet(lp)
    ok(f"Page {page} '{page_name}' ready")

    warm = [HUE_PALETTE_96[hi * 8 + si] for hi in range(5) for si in range(8)]    # 40 cues
    cool = [HUE_PALETTE_96[hi * 8 + si] for hi in range(5, 12) for si in range(8)]  # 56 cues

    for seq_id, seq_label, exec_num, presets, exec_h in [
        (126, "Warm", 1, warm, 30),
        (127, "Cool", 2, cool, 210),
    ]:
        section(f"Seq {seq_id} '{seq_label}' ({len(presets)} cues) -> Page {page}.{exec_num}",
                step=exec_num)
        result = await _build_sequence_on_page(
            seq_id=seq_id, seq_label=seq_label,
            page=page, exec_num=exec_num,
            presets=presets, exec_h=exec_h, exec_s=100,
        )
        findings_all.extend(result["findings"])
        state_changes_all.extend(result["state_changes"])

    section("Compress findings")
    report = {
        "summary": f"Built Warm (40 cues) + Cool (56 cues) on Page {page} '{page_name}'",
        "findings": findings_all,
        "state_changes": state_changes_all,
        "confidence": "high" if not findings_all else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Group D: Complementary Pairs  (Page 5, Seq 128-133, 6 × 16 cues)
# ---------------------------------------------------------------------------


async def run_complements_creator() -> None:
    """Build 6 true-complement pair sequences on Page 5 (hues 180 degrees apart)."""
    page = 5
    page_name = "Complements"
    banner(f"GROUP D -- COMPLEMENTS  --  Page {page} '{page_name}'  Seq 128-133")
    warn(f"DESTRUCTIVE -- building 6 sequences x 16 cues on Page {page}")

    findings_all: list[dict] = []
    state_changes_all: list[str] = []

    client = await get_client()

    section(f"Create/label Page {page} '{page_name}'")
    await navigate_page(action="goto", page_number=page, create_if_missing=True)
    lp = f'Label Page {page} "{page_name}"'
    await client.send_command_with_response(lp)
    telnet(lp)
    ok(f"Page {page} '{page_name}' ready")

    for pair_idx, (hi_a, hi_b, seq_label, exec_h) in enumerate(COMPLEMENT_PAIRS):
        seq_id = 128 + pair_idx
        exec_num = pair_idx + 1
        presets = (HUE_PALETTE_96[hi_a * 8 : hi_a * 8 + 8]
                   + HUE_PALETTE_96[hi_b * 8 : hi_b * 8 + 8])

        section(f"Seq {seq_id} '{seq_label}' -> Page {page}.{exec_num}", step=pair_idx + 1)
        result = await _build_sequence_on_page(
            seq_id=seq_id, seq_label=seq_label,
            page=page, exec_num=exec_num,
            presets=presets, exec_h=exec_h, exec_s=100,
        )
        findings_all.extend(result["findings"])
        state_changes_all.extend(result["state_changes"])

    section("Compress findings")
    report = {
        "summary": f"Built 6 complement pair sequences on Page {page} '{page_name}'",
        "findings": findings_all,
        "state_changes": state_changes_all,
        "confidence": "high" if not findings_all else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Orchestrator: all-color-groups  (A + B + C + D in one pass)
# ---------------------------------------------------------------------------


async def run_all_color_groups() -> None:
    """Build all 4 color group pages -- 28 sequences, 384 cues across Pages 2-5."""
    banner("ALL COLOR GROUPS  --  Pages 2-5  --  28 sequences  --  384 cues")
    warn("This builds 384 cues across 4 pages. Estimated time: 30-40 min.")
    info("Page map:")
    info("  Page 2 'Sat Bands'    -- Group A: 8 seq x 12 cues (Seq 106-113)")
    info("  Page 3 'Hue Faders'   -- Group B: 12 seq x 8 cues (Seq 114-125)")
    info("  Page 4 'Temperature'  -- Group C: 2 seq (40+56 cues, Seq 126-127)")
    info("  Page 5 'Complements'  -- Group D: 6 seq x 16 cues (Seq 128-133)")
    print()

    section("Group A: Saturation Bands (Page 2, Seq 106-113)")
    await run_sat_bands_creator()

    section("Group B: Hue Faders (Page 3, Seq 114-125)")
    await run_hue_faders_creator()

    section("Group C: Temperature (Page 4, Seq 126-127)")
    await run_temperature_creator()

    section("Group D: Complements (Page 5, Seq 128-133)")
    await run_complements_creator()

    banner("ALL COLOR GROUPS COMPLETE")
    info("Pages 2-5 ready. 28 sequences, 384 cues across 4 themed pages.")


# ---------------------------------------------------------------------------
# Fix-assignments: re-run assign/label/appearance for all 28 group sequences
# ---------------------------------------------------------------------------

# Flat spec for all 28 group sequences: (seq_id, seq_label, page, exec_num, exec_h, exec_s)
_GROUP_SEQUENCE_SPECS: list[tuple[int, str, int, int, int, int]] = [
    # Group A — Sat Bands (Page 2, Seq 106-113)
    *[(106 + si, f"{sfx} Band", 2, si + 1, si * 30, sv)
      for si, (sv, sfx) in enumerate(_SAT_STEPS)],
    # Group B — Hue Faders (Page 3, Seq 114-125)
    *[(114 + hi, hname, 3, hi + 1, hdeg, 100)
      for hi, (hname, hdeg) in enumerate(_HUES)],
    # Group C — Temperature (Page 4, Seq 126-127)
    (126, "Warm", 4, 1, 30,  100),
    (127, "Cool", 4, 2, 210, 100),
    # Group D — Complements (Page 5, Seq 128-133)
    *[(128 + pi, lbl, 5, pi + 1, mh, 100)
      for pi, (_, __, lbl, mh) in enumerate(COMPLEMENT_PAIRS)],
]


async def run_fix_assignments() -> None:
    """Re-run assign/label/appearance for all 28 group sequences without rebuilding cues.

    Use this after fixing a syntax error or when executors need to be re-assigned.
    Completes in ~2 min vs 30-40 min for a full rebuild.
    """
    banner("FIX ASSIGNMENTS  --  28 sequences across Pages 2-5")
    warn("Re-assigning all 28 group sequences to page-qualified executors.")
    info("Cues are NOT rebuilt — only assign/label/appearance are re-run.")

    client = await get_client()
    findings_all: list[dict] = []
    state_changes_all: list[str] = []

    for seq_id, seq_label, page, exec_num, exec_h, exec_s in _GROUP_SEQUENCE_SPECS:
        print(f"\n   Seq {seq_id} '{seq_label}' -> Executor {page}.{exec_num}  H={exec_h} S={exec_s}")
        for raw_cmd, desc in [
            (f"Assign Sequence {seq_id} At Executor {page}.{exec_num}",
             f"Seq {seq_id} -> Executor {page}.{exec_num}"),
            (f'Label Executor {page}.{exec_num} "{seq_label}"',
             f"Executor {page}.{exec_num} labeled '{seq_label}'"),
            (f"Appearance Executor {page}.{exec_num} /h={exec_h} /s={exec_s} /br=100",
             f"Executor {page}.{exec_num} appearance H={exec_h} S={exec_s}"),
        ]:
            telnet(raw_cmd)
            try:
                resp = await client.send_command_with_response(raw_cmd)
                if isinstance(resp, str) and resp.strip().startswith("Error"):
                    raise RuntimeError(resp.strip())
                ok(desc)
                state_changes_all.append(desc)
            except Exception as e:
                warn(f"FAILED: {raw_cmd}: {e}")
                findings_all.append({"kind": "error", "detail": f"{raw_cmd}: {e}"})

    section("Compress findings")
    report = {
        "summary": f"Fix-assignments complete: {len(_GROUP_SEQUENCE_SPECS)} sequences processed",
        "findings": findings_all,
        "state_changes_count": len(state_changes_all),
        "confidence": "high" if not findings_all else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Diagnostic: query actual executor assignments on pages 2-5
# ---------------------------------------------------------------------------


async def run_diagnose_pages() -> None:
    """Query pages 2-5 to confirm what sequences are actually assigned to executors.

    Checks two things:
    1. list executor P.E  — what's assigned (page-qualified dot notation)
    2. Navigate to each page, then list executor N — what's on the current page
    """
    banner("DIAGNOSE PAGES 2-5 -- executor assignment verification")
    client = await get_client()

    PAGE_EXEC_COUNTS = {2: 8, 3: 12, 4: 2, 5: 6}  # page -> expected exec count
    PAGE_NAMES = {2: "Sat Bands", 3: "Hue Faders", 4: "Temperature", 5: "Complements"}
    results: dict = {}

    # --- Method 1: page-qualified dot notation (no navigation) ---
    section("Method 1: list executor P.E (no page nav)")
    for page, count in PAGE_EXEC_COUNTS.items():
        page_results = []
        for en in range(1, count + 1):
            ref = f"{page}.{en}"
            resp = await client.send_command_with_response(f"list executor {ref}")
            telnet(f"list executor {ref}")
            clean = re.sub(r"\x1b\[[0-9;]*m", "", resp or "").strip()
            page_results.append({"executor": ref, "response": clean[:120]})
            status = "OK" if clean and "NO OBJECTS" not in clean and "Error" not in clean else "EMPTY/ERR"
            print(f"   Exec {ref:6s}  [{status}]  {clean[:80]}")
        results[f"page_{page}_dot_notation"] = page_results

    # --- Method 2: navigate to each page, then list executors by position ---
    section("Method 2: navigate to page, then list executor 1 thru N")
    for page, count in PAGE_EXEC_COUNTS.items():
        # Navigate to the page
        nav_resp = await client.send_command_with_response(f"page {page}")
        telnet(f"page {page}")
        ok(f"Navigated to page {page} '{PAGE_NAMES[page]}': {(nav_resp or '').strip()[:60]}")

        page_results = []
        for en in range(1, count + 1):
            resp = await client.send_command_with_response(f"list executor {en}")
            telnet(f"list executor {en}")
            clean = re.sub(r"\x1b\[[0-9;]*m", "", resp or "").strip()
            page_results.append({"executor": en, "response": clean[:120]})
            status = "OK" if clean and "NO OBJECTS" not in clean and "Error" not in clean else "EMPTY/ERR"
            print(f"   Page {page} Exec {en:2d}  [{status}]  {clean[:80]}")
        results[f"page_{page}_after_nav"] = page_results

    # Navigate back to page 1
    await client.send_command_with_response("page 1")
    telnet("page 1")
    ok("Returned to page 1")

    section("Compress findings")
    report = {
        "summary": "Page executor diagnostic complete",
        "pages_checked": list(PAGE_EXEC_COUNTS.keys()),
        "results": results,
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Fix-assignments v2: navigate to each page before assigning
# ---------------------------------------------------------------------------


async def run_fix_assignments_with_nav() -> None:
    """Re-run assign/label/appearance for all 28 group sequences, navigating to each page first.

    Use this if Executor P.E dot-notation alone is not enough — navigating to the page
    may be required before MA2 accepts executor assignment on that page.
    """
    banner("FIX ASSIGNMENTS WITH PAGE NAVIGATION  --  Pages 2-5")
    warn("DESTRUCTIVE — re-assigns 28 sequences to page-qualified executors")

    client = await get_client()
    findings_all: list[dict] = []
    state_changes_all: list[str] = []

    # Group specs by page for batched navigation
    by_page: dict[int, list] = {}
    for spec in _GROUP_SEQUENCE_SPECS:
        page = spec[2]
        by_page.setdefault(page, []).append(spec)

    for page in sorted(by_page.keys()):
        page_specs = by_page[page]
        section(f"Page {page} — navigating first, then assigning {len(page_specs)} sequences")

        # Navigate to this page
        nav_resp = await client.send_command_with_response(f"page {page}")
        telnet(f"page {page}")
        ok(f"Page {page}: {(nav_resp or '').strip()[:60]}")

        for seq_id, seq_label, _page, exec_num, exec_h, exec_s in page_specs:
            print(f"\n   Seq {seq_id} '{seq_label}' -> Executor {page}.{exec_num}  H={exec_h} S={exec_s}")
            for raw_cmd, desc in [
                (f"Assign Sequence {seq_id} At Executor {exec_num}",
                 f"Seq {seq_id} -> Page {page} Exec {exec_num}"),
                (f'Label Executor {exec_num} "{seq_label}"',
                 f"Exec {exec_num} labeled '{seq_label}'"),
                (f"Appearance Executor {exec_num} /h={exec_h} /s={exec_s} /br=100",
                 f"Exec {exec_num} appearance H={exec_h} S={exec_s}"),
            ]:
                telnet(raw_cmd)
                try:
                    resp = await client.send_command_with_response(raw_cmd)
                    if isinstance(resp, str) and resp.strip().startswith("Error"):
                        raise RuntimeError(resp.strip())
                    ok(desc)
                    state_changes_all.append(desc)
                except Exception as e:
                    warn(f"FAILED: {raw_cmd}: {e}")
                    findings_all.append({"kind": "error", "detail": f"{raw_cmd}: {e}"})

    # Navigate back to page 1
    await client.send_command_with_response("page 1")
    telnet("page 1")
    ok("Returned to page 1")

    section("Compress findings")
    report = {
        "summary": f"Fix-assignments-with-nav complete: {len(_GROUP_SEQUENCE_SPECS)} sequences",
        "findings": findings_all,
        "state_changes_count": len(state_changes_all),
        "confidence": "high" if not findings_all else "medium",
    }
    print()
    print(json.dumps(report, indent=2))


# ---------------------------------------------------------------------------
# Orchestrator: full-hue-expansion  (all 6 pairs in one pass)
# ---------------------------------------------------------------------------


async def run_full_hue_expansion() -> None:
    banner("FULL HUE EXPANSION  --  96 presets + 6 sequences + 6 executors")
    warn("This stores 96 presets and builds 6 × 16-cue sequences. Takes ~10 min.")
    info("Pair map:")
    for hi_a, hi_b, label, seq_id, exec_id in HUE_PAIRS:
        info(f"  Seq {seq_id}  Exec {exec_id}  ->  {label}")
    print()

    # Phase 1: create all 96 presets
    section("Phase 1: Create 96 hue presets (4.101-4.196)")
    await run_hue_palette_creator()

    # Phase 2: build each of the 6 sequences
    for pair_idx, (hi_a, hi_b, label, seq_id, exec_id) in enumerate(HUE_PAIRS):
        section(f"Phase 2.{pair_idx + 1}: Build '{label}'  Seq {seq_id}  Exec {exec_id}")
        await run_hue_sequence_builder(pair_idx, seq_id, exec_id)

    banner("FULL HUE EXPANSION COMPLETE")
    info("6 sequences assigned to executors 202-207.")
    info("Original Seq 99 / Exec 201 (Color Palette) is untouched.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute a .claude/skills/ instruction module against the live console"
    )
    parser.add_argument(
        "--skill", default="cue-list-auditor",
        help="Skill slug to execute (default: cue-list-auditor)",
    )
    parser.add_argument(
        "--sequence", type=int, default=None,
        help="Sequence ID: auto-detect for cue-list-auditor, target (default 99) for color-palette-sequence-builder",
    )
    parser.add_argument(
        "--response", default="",
        help="Raw telnet response string for feedback-investigator",
    )
    parser.add_argument(
        "--executor", type=int, default=None,
        help="Executor ID to assign the sequence to (default: auto-detect first free, convention: 201)",
    )
    parser.add_argument(
        "--hue", type=int, default=None,
        help="Hue pair index 0-5 for hue-sequence-builder (0=Red/Orange, 1=Amber/Yellow, "
             "2=Lime/Green, 3=Teal/Cyan, 4=Azure/Blue, 5=Violet/Magenta)",
    )
    args = parser.parse_args()

    slug = args.skill.lower()

    # Connect to console
    print()
    print(f"grandMA2 MCP Server -- Live Skill Execution")
    print(f"Console : {os.getenv('GMA_HOST', '127.0.0.1')}:{os.getenv('GMA_PORT', '30000')}")
    print(f"Skill   : {slug}")
    info("Connecting to console...")
    try:
        await get_client()
    except Exception as e:
        print(f"\n   [!!] Could not connect to console: {e}")
        print("        Check GMA_HOST / GMA_PORT in .env and ensure grandMA2 onPC is running.")
        sys.exit(1)
    ok("Connected.")

    # ── Show discovery ───────────────────────────────────────────────────────
    global _current_show
    section("Show on console")
    tool_call("list_system_variables(filter_prefix='SHOW')")
    raw_sv = await list_system_variables(filter_prefix="SHOW")
    data_sv = json.loads(raw_sv) if isinstance(raw_sv, str) else raw_sv
    if isinstance(data_sv, dict) and "command_sent" in data_sv:
        telnet(data_sv["command_sent"])
    if isinstance(data_sv, dict) and data_sv.get("blocked"):
        warn(f"list_system_variables blocked: {data_sv.get('error', 'unknown')}")
    else:
        raw_text_sv = data_sv.get("raw_response", "") if isinstance(data_sv, dict) else str(data_sv)
        clean_sv = re.sub(r"\x1b\[[0-9;]*m", "", raw_text_sv)
        show_match = re.search(r"\$SHOWFILE\s*[=:]\s*(\S+)", clean_sv, re.I)
        _current_show = show_match.group(1) if show_match else "unknown"
        ok(f"Current show: {_current_show}")

    if "feedback" in slug:
        response = args.response or "Command failed: RIGHTS DENIED for user programmer"
        await run_feedback_investigator(response)
    elif "full-hue" in slug or "hue-expansion" in slug:
        await run_full_hue_expansion()
    elif "hue-palette" in slug:
        await run_hue_palette_creator()
    elif "hue-sequence" in slug:
        pair_idx = args.hue if args.hue is not None else 0
        _, _, _, default_seq, default_exec = HUE_PAIRS[pair_idx]
        await run_hue_sequence_builder(pair_idx, args.sequence or default_seq,
                                       args.executor or default_exec)
    elif "diagnose-page" in slug or "diag-page" in slug:
        await run_diagnose_pages()
    elif "fix-assign-nav" in slug:
        await run_fix_assignments_with_nav()
    elif "fix-assign" in slug:
        await run_fix_assignments()
    elif "sat-band" in slug or "saturation-band" in slug:
        await run_sat_bands_creator()
    elif "hue-fader" in slug or "single-hue" in slug:
        await run_hue_faders_creator()
    elif "temperature" in slug:
        await run_temperature_creator()
    elif "complement" in slug:
        await run_complements_creator()
    elif "all-color-group" in slug or "color-group" in slug:
        await run_all_color_groups()
    elif "preset-creator" in slug or "create-preset" in slug:
        await run_color_preset_creator()
    elif "palette" in slug or "color-palette" in slug:
        await run_color_palette_sequence_builder(args.sequence or 99)
    elif "executor-assigner" in slug or "assign-executor" in slug:
        await run_sequence_executor_assigner(args.sequence or 99, args.executor)
    else:
        await run_cue_list_auditor(args.sequence)

    print()
    banner("SKILL EXECUTION COMPLETE")
    print()


if __name__ == "__main__":
    asyncio.run(main())
