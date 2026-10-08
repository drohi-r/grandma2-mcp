"""MCP tools — prompts. Split out of src/server.py.

Tools register on ``src.server.mcp`` at import. Names that tests patch or
that live in other tool modules are looked up as ``_srv.<name>`` at call time.
"""

# ruff: noqa: E501


from src.server import (
    mcp,
)

# ============================================================
# MCP Prompts
# User-initiated workflow templates for console operations
# ============================================================


@mcp.prompt()
def preflight_destructive_change(operation: str, target: str, reason: str = "") -> str:
    """
    Run pre-flight checks before any destructive console operation.

    Use this prompt before calling any DESTRUCTIVE tool to ensure the
    operation is safe to proceed.

    Args:
        operation: The destructive operation to perform (e.g. "delete_object", "store_current_cue").
        target: The object or path being modified (e.g. "Group 5", "Sequence 1 Cue 3").
        reason: Why this change is needed (optional but recommended for audit trail).
    """
    return f"""Perform a safety pre-flight before executing: {operation} on {target}

Reason: {reason or "(not specified)"}

Pre-flight checklist:
1. Read `ma2://docs/rights-matrix` — confirm the current user has sufficient rights for {operation}.
2. Call `list_system_variables` — check $USERRIGHTS and $SHOWFILE.
3. Call `get_object_info` on {target} — confirm the target exists and capture its current state.
4. Check if Blind mode is active (`$BLINDMODE` or `mode_overrides["blind"]`).
5. If the operation affects executors, verify no cue is running on the target executor.

Only proceed with {operation} after all five checks pass.
If any check fails, report the finding and ask the user to confirm before proceeding.
Use `confirm_destructive=True` when calling the tool."""


@mcp.prompt()
def inspect_console(focus: str = "full") -> str:
    """
    Guided console state inspection — Inspect workflow.

    Produces a structured console overview without any mutations.

    Args:
        focus: What to inspect — "full" (default), "playback", "fixtures", "show", or "rights".
    """
    focus_map = {
        "full": "system variables, active executors, programmer state, and current show info",
        "playback": "active executors, running cues, fader levels, and executor assignments",
        "fixtures": "patched fixture types, selected fixtures, programmer content",
        "show": "show file name, universe count, group count, sequence count, and preset pool sizes",
        "rights": "current user, rights level, active world, and active filter",
    }
    scope = focus_map.get(focus, focus_map["full"])
    return f"""Inspect the grandMA2 console — {focus} focus.

Read-only inspection only. No mutations permitted.

Steps:
1. Call `list_system_variables` — capture all 26 system variables.
2. Inspect: {scope}.
3. Call `navigate_console` to `cd /` and `list_console_destination` to see the root object tree.
4. If focus includes executors: call `query_object_list` for active sequences and their cue counts.
5. Summarize findings in this structure:

{{
  "console_version": "$VERSION",
  "show_file": "$SHOWFILE",
  "active_user": "$USER",
  "rights": "$USERRIGHTS",
  "selected_exec": "$SELECTEDEXEC",
  "active_cue": "$SELECTEDEXECCUE",
  "fixture_count": <from list>,
  "findings": ["..."]
}}"""


@mcp.prompt()
def plan_cue_store(
    sequence_id: str,
    cue_number: str,
    fixture_selection: str,
    preset_or_values: str,
) -> str:
    """
    Plan a cue store operation with safety and rights checks — Plan workflow.

    Use this prompt to generate a structured cue store plan before executing.
    The plan includes pre-flight checks, proposed commands, and a verification step.

    Args:
        sequence_id: Sequence number (e.g. "1", "99").
        cue_number: Target cue number (e.g. "1", "3.5").
        fixture_selection: Fixture group or ID range to use (e.g. "Group 1", "Fixture 1 Thru 10").
        preset_or_values: Preset to apply or manual values (e.g. "Preset 4.5", "Full").
    """
    return f"""Plan a cue store operation without executing it yet.

Target: Store Cue {cue_number} in Sequence {sequence_id}
Fixtures: {fixture_selection}
Values/Preset: {preset_or_values}

Plan steps:
1. PRE-FLIGHT: Call `list_system_variables` — confirm $USERRIGHTS has Programmer or higher.
2. PRE-FLIGHT: Call `query_object_list` for Sequence {sequence_id} — check if Cue {cue_number} already exists.
   If it exists: plan a /merge store. If not: plan a clean store.
3. SELECT: Plan `SelFix {fixture_selection}` — verify fixture count > 0.
4. APPLY: Plan `{preset_or_values}` — identify whether this is a preset recall or direct value.
5. STORE PLAN: Emit the exact command to be executed:
   `Store Cue {cue_number} Sequence {sequence_id} /merge`
6. VERIFY PLAN: After store, plan `query_object_list` on Sequence {sequence_id} to confirm Cue {cue_number} exists.

Return the plan as a JSON object with "pre_flight", "commands", and "verify" arrays.
Do NOT execute any commands yet. This is a planning step only."""


@mcp.prompt()
def diagnose_playback_failure(executor_id: str, symptom: str) -> str:
    """
    Diagnose a playback failure on a specific executor — Inspect + Plan workflows.

    Use this prompt when a cue or executor is not behaving as expected.

    Args:
        executor_id: The executor identifier (e.g. "1", "201", "1.1.201").
        symptom: What is observed (e.g. "cue not advancing", "no output", "wrong fixtures responding").
    """
    return f"""Diagnose playback failure on Executor {executor_id}.

Observed symptom: {symptom}

Diagnostic steps:
1. Call `list_system_variables` — check $SELECTEDEXEC, $SELECTEDEXECCUE, $FADERPAGE.
2. Call `query_object_list` for the sequence assigned to Executor {executor_id} — count cues, check for gaps.
3. Call `get_object_info` on Executor {executor_id} — check assignment, priority, options.
4. Call `send_raw_command` with `list Executor {executor_id}` — capture raw executor state.
5. Load skill `ma2://skills/telnet-feedback-triage` — apply FeedbackClass classification to any UNKNOWN COMMAND or WARNING responses.

Common failure patterns:
- "no output": check blind mode ($BLINDMODE), check if output is patched, check DMX universe assignment.
- "cue not advancing": check trigger setting (Time/Go), check MIB settings, check if executor has "Kill" active.
- "wrong fixtures": check world assignment, check if programmer has conflicting values (call `clear_programmer`).

Return structured findings: {{"fault_class": "...", "root_cause": "...", "recommended_actions": [...]}}"""


@mcp.prompt()
def load_show_safely(show_name: str) -> str:
    """
    Safe show loading checklist — prevents accidental Telnet disconnection.

    Use this prompt before any new_show or load_show operation.

    Args:
        show_name: The show file to load (e.g. "my_show_2026").
    """
    return f"""Load show "{show_name}" safely without severing the MCP Telnet connection.

Pre-load checklist:
1. Call `list_system_variables` — record current $SHOWFILE, $HOSTIP, $VERSION.
2. Call `save_show` if any unsaved changes should be preserved.
3. CRITICAL: Verify that the load command will preserve connectivity:
   - For `new_show`: MUST use preserve_connectivity=True (passes /globalsettings /network /protocols).
   - For `load_show`: confirm the target show has Telnet enabled in its global settings.
4. Confirm the operator understands: loading a show with Telnet disabled will disconnect this MCP session.

Only proceed after the checklist is complete.
If loading a completely blank show, the user MUST manually re-enable Telnet in
Setup → Console → Global Settings before the next MCP connection."""


@mcp.prompt()
def bootstrap_rights_users() -> str:
    """
    Bootstrap the standard six-tier MA2 rights user accounts — guided provisioning workflow.

    Use this prompt when setting up a new show file with the standard
    operator rights ladder (Admin, LightOperator, Programmer, PlaybackOperator, Guest, Emergency).
    """
    return """Bootstrap the standard MA2 rights user accounts.

This is a DESTRUCTIVE workflow — it creates user accounts and modifies user profiles.
All steps require confirm_destructive=True.

Steps:
1. INSPECT: Call `list_console_users` — check which accounts already exist.
   Built-in accounts Administrator and Guest always exist and cannot be deleted.
2. READ RESOURCE: Load `ma2://docs/rights-matrix` — review the six-tier rights ladder.
3. PLAN: For each missing account in the standard set:
   - Admin (rights: Admin)
   - LightOperator (rights: Light-Operator)
   - Programmer (rights: Programmer)
   - PlaybackOp (rights: Playback-Operator)
   - Guest (rights: Guest)
4. EXECUTE: For each planned account, call `create_user(username=..., rights=..., confirm_destructive=True)`.
5. VERIFY: Call `list_console_users` again — confirm all accounts were created.
6. SAVE: Call `save_show` to persist the new accounts.

Return a summary of: accounts created, accounts skipped (already existed), any errors."""


# ============================================================
# New Prompts: Volunteer Preflight, Busking Template,
# Pre-Show Health Check, Adapt Show to Venue
# ============================================================


@mcp.prompt()
def volunteer_sunday_preflight(show_name: str = "", campus_name: str = "") -> str:
    """
    Sunday morning preflight checklist for volunteer operators — SAFE_READ guided verification
    that the correct show is loaded, presets are populated, and executors are assigned.
    """
    context = f"Show: {show_name}" if show_name else "Show: (use get_showfile_info to determine)"
    campus = f"Campus: {campus_name}" if campus_name else ""

    return f"""You are running a pre-show safety check for a volunteer operator.
{context}
{campus}

Execute the following SAFE_READ verification sequence in order. Stop and report
immediately if any step returns unexpected results.

STEP 1 -- SHOWFILE VERIFICATION
Call get_showfile_info(). Confirm the show name matches "{show_name or 'the expected show name'}".
Then call assert_showfile_unchanged(). If it returns False, STOP -- the show file has been modified
since the last programmer session. Do not proceed; contact the Technical Director.

STEP 2 -- STATE HYDRATION
Call hydrate_console_state(). Then call get_console_state().
Check for: unexpected parked fixtures (park_ledger not empty), active filter (may restrict fixtures),
unexpected world assignment.

STEP 3 -- PRESET POOL CHECK
Call list_preset_pool(preset_type="color") and list_preset_pool(preset_type="position").
Flag as AMBER if either pool has fewer than 3 entries.

STEP 4 -- EXECUTOR ASSIGNMENT CHECK
Call get_executor_detail(executor_id="1.1") and get_executor_detail(executor_id="1.2").
Confirm each has a sequence assigned and at least 1 cue.

STEP 5 -- CUE INTEGRITY CHECK
Call query_object_list(object_type="sequence", object_id=1).
Confirm the expected number of cues are present and the first cue is labeled.

STEP 6 -- GENERATE REPORT
Return a structured report:
{{
  "show_name": "<from step 1>",
  "campus": "{campus_name or 'N/A'}",
  "overall": "GREEN | AMBER | RED",
  "checks": {{
    "showfile": "GREEN | AMBER | RED",
    "console_state": "GREEN | AMBER | RED",
    "preset_pool": "GREEN | AMBER | RED",
    "executors": "GREEN | AMBER | RED",
    "cue_list": "GREEN | AMBER | RED"
  }},
  "findings": ["..."],
  "action_required": true | false
}}

GREEN = everything nominal. AMBER = non-blocking issue, report to TD. RED = stop, contact TD immediately."""


@mcp.prompt()
def generate_busking_template(
    target_page: str = "2",
    fixture_strategy: str = "by_type"
) -> str:
    """
    Generate a complete grandMA2 busking template from the current patch —
    groups, presets, effects, speed masters, and executor layout.
    """
    return f"""You are building a complete busking template for a grandMA2 rig.

Target executor page: {target_page}
Fixture grouping strategy: {fixture_strategy} (options: by_type, by_position, by_zone)

PHASE 0 -- SURVEY (SAFE_READ, always first -- present findings before proceeding)
1. Call hydrate_console_state() and list_fixtures() -- record total fixture count and types
2. Call list_fixture_types() -- identify unique fixture types in the rig
3. Call list_preset_pool(preset_type="color") -- check if color presets already exist
4. Call list_preset_pool(preset_type="position") -- check position presets
5. Present survey summary to operator and ask: "I found [N] fixtures of [M] types.
   Color pool has [K] existing presets. Shall I proceed with template generation?"
   STOP if operator says no.

PHASE 1 -- GROUP CREATION (confirm before executing DESTRUCTIVE operations)
Using the {fixture_strategy} strategy:
- by_type: one group per fixture type (all washes, all spots, all beams, all strobes)
- by_position: groups by stage position (front, back, left, right, truss)
- by_zone: groups by zone (audience, stage, backlight)

For each group: call create_fixture_group() then label_or_appearance() with HSB color coding.
Ask operator to confirm before executing: "I will create [N] groups in slots [X-Y]. Proceed?"

PHASE 2 -- COLOR PRESETS (8 per group -- confirm first)
Create 8 universal color presets using RGB 0-100 scale:
Red(100,0,0), Orange(100,40,0), Yellow(100,100,0), Green(0,100,0),
Cyan(0,100,100), Blue(0,0,100), Magenta(100,0,100), White(100,100,100)

PHASE 3 -- POSITION PRESETS (movers only -- 4 positions)
For fixture groups with Pan/Tilt attributes: create Home, DownCenter, SL_Top, SR_Top presets.

PHASE 4 -- EXECUTOR LAYOUT (confirm slot assignments before executing)
On page {target_page}:
- Exec 1: Song loader macro (label "LOAD")
- Exec 2-5: Effect sequences per fixture group
- Exec 6-8: Group intensity masters
- Exec 9: Speed master 1 (default 120 BPM)
- Exec 10: Emergency blackout macro

PHASE 5 -- VERIFY AND SAVE
Call get_console_state() to confirm all objects registered.
Call save_show(confirm_destructive=True) -- always save after template build.

At each DESTRUCTIVE phase, pause and confirm with the operator before proceeding.
Never auto-execute DESTRUCTIVE operations without explicit operator confirmation."""


@mcp.prompt()
def pre_show_health_check(sequence_ids: str = "1", strict: bool = False) -> str:
    """
    Full show health audit before going live — checks showfile, presets, executors,
    cue integrity, park ledger, and DMX. Returns GREEN/AMBER/RED per category.
    """
    sequences = sequence_ids or "1"
    mode = "strict" if strict else "standard"

    return f"""You are performing a pre-show health check in {mode} mode.
Target sequences: {sequences}

Run all checks in order. Collect ALL findings before returning the final report.
Do NOT stop at first AMBER -- run all categories.

CATEGORY 1 -- SHOWFILE (GREEN/RED)
Call get_showfile_info() -- record show name and version.
Call assert_showfile_unchanged() -- RED if fails (show was modified unexpectedly).

CATEGORY 2 -- HYDRATION
Call hydrate_console_state() then get_console_state().

CATEGORY 3 -- PRESET POOL (GREEN/AMBER)
For preset types Color, Position, Beam:
  Call list_preset_pool(preset_type=X).
  AMBER if any expected type has 0 entries.
  AMBER if fewer than 3 entries in Color preset pool.

CATEGORY 4 -- EXECUTOR ASSIGNMENTS (GREEN/AMBER/RED)
For each key executor (1.1, 1.2 minimum):
  Call get_executor_detail(executor_id=X).
  AMBER if executor has no assigned sequence.
  RED if main sequence executor has 0 cues.

CATEGORY 5 -- CUE INTEGRITY (GREEN/AMBER)
For each sequence in [{sequences}]:
  Call query_object_list(object_type="sequence", object_id=N).
  AMBER if gap > 10 between consecutive cue numbers.
  AMBER if more than 20% of cues are unlabeled.
  {"RED if any gap found." if strict else "AMBER if cue count < 3."}

CATEGORY 6 -- PARK LEDGER (GREEN/AMBER)
Call get_park_ledger().
AMBER if any fixtures are parked (may be intentional -- report don't assume error).

CATEGORY 7 -- DMX (GREEN/AMBER)
Call list_fixtures() -- count fixtures with no DMX address.
AMBER if any fixture has address 0 or None.

RETURN FORMAT:
{{
  "show_name": "...",
  "audit_mode": "{mode}",
  "overall": "GREEN | AMBER | RED",
  "categories": {{
    "showfile": {{"score": "...", "findings": [...]}},
    "preset_pool": {{"score": "...", "findings": [...]}},
    "executors": {{"score": "...", "findings": [...]}},
    "cue_integrity": {{"score": "...", "findings": [...]}},
    "park_ledger": {{"score": "...", "findings": [...]}},
    "dmx": {{"score": "...", "findings": [...]}}
  }},
  "recommended_actions": [...]
}}

Overall score = worst score across all categories."""


@mcp.prompt()
def adapt_show_to_venue(
    source_show_description: str = "",
    new_venue_notes: str = ""
) -> str:
    """
    Adapt an existing show file to a new venue's fixture rig — guided cross-venue
    adaptation with patch comparison, group remapping, and preset verification.
    """
    return f"""You are adapting a show file to a new venue rig.

Source show context: {source_show_description or "current loaded show"}
New venue notes: {new_venue_notes or "no additional context provided"}

PHASE 0 -- SURVEY (SAFE_READ -- complete before any changes)
1. Call hydrate_console_state()
2. Call list_fixtures() -- document: fixture ID, type, DMX address for ALL fixtures
3. Call list_fixture_types() -- document imported profiles
4. Call list_preset_pool(preset_type="color") and list_preset_pool(preset_type="position")
5. Sample group membership: call query_object_list(object_type="group", object_id=1)

Present comparison to operator:
"Current rig has [N] fixtures of types [A, B, C].
[Describe any type mismatches based on new_venue_notes].
Which types map to which in the new venue?"

WAIT for operator confirmation of the fixture type mapping before proceeding.

PHASE 1 -- IDENTIFY MISMATCHES
Cross-reference fixture types in the show against new venue patch.
Categorize each type as: COMPATIBLE (same attributes), SIMILAR (same Pan/Tilt/Dim but different gobos),
or INCOMPATIBLE (completely different attribute set).

DECISION: If >50% of fixture types are INCOMPATIBLE, recommend using generate_busking_template
prompt to rebuild from scratch rather than adapting.

PHASE 2 -- REMAP GROUPS (confirm before DESTRUCTIVE operations)
For each group containing old fixture IDs:
  Check current membership with query_object_list(object_type="group", object_id=N).
  If fixture type mapping is COMPATIBLE or SIMILAR: use remap_fixture_ids() to update
  group membership with new fixture IDs. Ask operator to confirm before each group.

PHASE 3 -- VERIFY PRESETS
For SIMILAR types: test universal color presets -- call apply_preset(preset_type="color", preset_id=1)
with new fixture selected and verify output.
For INCOMPATIBLE types: presets must be re-recorded. Guide operator through re-recording.

PHASE 4 -- TEST AND VERIFY
Select a sample group: select_fixtures_by_group(group_id=1).
Apply a color preset: apply_preset(preset_type="color", preset_id=1).
Confirm correct fixtures respond.

PHASE 5 -- SAVE
Call save_show(confirm_destructive=True).

At every DESTRUCTIVE phase: present what will change and ask "Proceed? (yes/no)" before executing."""
