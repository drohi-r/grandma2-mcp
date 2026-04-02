---
title: Codex Consistency Pass Handover — MA2 Agent
description: Targeted documentation and metadata consistency cleanup summary for MA2 Agent
version: 1.0.0
created: 2026-04-02T04:16:48Z
last_updated: 2026-04-02T04:31:14Z
---

# Codex Consistency Pass Handover — MA2 Agent

## 1. Purpose

This pass was a targeted documentation and metadata consistency cleanup. It was not a broad rewrite. The goal was to normalize stale branding, counts, repo/path references, tool-range math, and current-facing provenance wording against the current repo state.

Follow-up: after the consistency pass, a narrow MCP server correctness fix was applied locally to address agent-harness confirmation and auth-gating defects discovered during read-only review. That follow-up also added 5 regression tests, so the repo test totals increased accordingly.

## 2. Source of truth used

- Project name: MA2 Agent
- Version: 1.0.0
- Public repo: `drohi-r/grandma2-mcp`
- Tool totals: 210 tools = 176 server tools + 34 orchestration tools
- Skills: 44
- Tests: 2773 total = 2631 passing, 142 skipped, 0 failed
- Recent additions accounted for: 10 analysis/intelligence tools and 5 new skills from the latest development push
- Repo/MCP work attribution kept accurate to Claude Code where already documented
- Factual Sonnet -> Opus correction rule preserved, but no such correction was needed in the files edited during this pass
- Attribution chain preserved exactly as required: `chienchuanw -> thisis-romar -> drohi-r`

## 3. Files changed

- `README.md`
  Reason: normalized current-facing repo path examples, reconciled tool-layer math, updated the skill catalog to match the actual 44 directories, and fixed current resource/catalog counts.
  Class: stale branding, stale repo/path reference, stale skill catalog, stale tool count, architecture math mismatch, numeric range clarification.
- `TERMS.md`
  Reason: updated current-facing product naming from the upstream repo name to MA2 Agent without changing legal disclaimers or license language.
  Class: stale branding.
- `SESSION-HANDOVER.md`
  Reason: corrected the current stats block to present repo truth and clarified that older "new tools/new skills" lists describe the earlier hardening wave rather than the present totals.
  Class: stale tool count, stale skill count, stale test count, historical-context clarification.
- `CLAUDE.md`
  Reason: corrected the orchestration tool-range description to match the actual 34-tool layout.
  Class: architecture math mismatch, numeric range clarification.
- `src/server_orchestration_tools.py`
  Reason: fixed the top module docstring/comment so it no longer claims 35 tools or implies a contiguous 110-144 range.
  Class: stale tool count, inclusive range mistake.
- `doc/transcript-architecture-audit.md`
  Reason: updated current repo naming and tool-surface counts in the audit framing and evidence table.
  Class: stale branding, stale tool count.
- `doc/openspace-comparison-audit.md`
  Reason: updated current repo naming, tool totals, category description, and test totals.
  Class: stale branding, stale tool count, stale test count.
- `doc/responsibility-map.md`
  Reason: updated current repo naming and planner/tool-surface counts; corrected orchestration tool-range wording.
  Class: stale branding, stale tool count, architecture math mismatch.
- `doc/tool-surface-tiers.md`
  Reason: updated current tool-surface counts in the framing text and document description.
  Class: stale tool count.
- `doc/cd-tree-mcp-tool-correlation-matrix.md`
  Reason: reconciled the headline totals and the unmapped-tools math with the current 210-tool layout.
  Class: stale tool count, architecture math mismatch.
- `vscode-mcp-provider/README.md`
  Reason: updated extension branding to MA2 Agent.
  Class: stale branding.
- `vscode-mcp-provider/package.json`
  Reason: updated extension display metadata and provider label to the MA2 Agent brand without changing the stable extension package identifier.
  Class: stale branding.
- `vscode-mcp-provider/src/extension.ts`
  Reason: updated the VS Code MCP server display label to the MA2 Agent brand.
  Class: stale branding.
- `docs/CODEX-CONSISTENCY-PASS-HANDOVER.md`
  Reason: created the required handoff artifact for Opus / maintainers.
  Class: handoff documentation.
- `src/server.py`
  Reason: fixed `run_agent_goal` confirmation behavior, added explicit scope gating to agent-harness entrypoints, corrected the stale top-level execution hint in the FastMCP instructions, and aligned the runtime server name with the MA2 Agent brand.
  Class: confirmation semantics fix, auth gating fix, stale tool entrypoint reference, runtime branding fix.
- `doc/tool-surface-tiers.md`
  Reason: replaced the stale `run_orchestrated_task` entry with the real agent-harness entrypoint.
  Class: stale tool entrypoint reference.
- `tests/test_agent_harness_tools.py`
  Reason: added targeted coverage for `run_agent_goal` and `plan_agent_goal` auth and confirmation behavior.
  Class: regression test coverage.
- `vscode-mcp-provider/package.json`
  Reason: aligned the extension runtime version with the project’s current 1.0.0 release while preserving the stable extension package identifier.
  Class: runtime branding fix.

## 4. Exact inconsistency categories fixed

- stale branding
- stale repo/path reference
- stale tool count
- stale skill count
- stale test count
- stale skill catalog
- stale tool catalog summary
- architecture math mismatch
- inclusive numeric range mistake
- old current-facing `ma2-onPC-MCP` naming in repo-facing docs
- stale tool entrypoint reference
- auth gating gap on agent-harness MCP tools
- destructive confirmation semantics bug
- runtime branding drift
- stale test count after adding regression coverage

## 5. Notable before/after corrections

- `39 skills` -> `44 skills`
- `200 tools (166 server + 34 orchestration)` -> `210 tools (176 server + 34 orchestration)`
- `2751 tests (2609 passing, 142 skipped, 0 failed)` -> `2773 tests (2631 passing, 142 skipped, 0 failed)`
- `/path/to/ma2-onPC-MCP` -> `/path/to/grandma2-mcp`
- `ma2-onPC-MCP/` -> `grandma2-mcp/`
- README skill catalog missing 10 actual skill directories -> README skill catalog expanded to match all 44 current skills
- `34 tools (110–144)` interpreted as a contiguous inclusive range -> clarified as `34 tools` with IDs `110–144`, excluding `130`
- `177 tools` / `143 + 34` / `143 interactive + 33 agentic` audit math -> reconciled to current repo truth where those sections were meant to describe the present repo
- `run_orchestrated_task` -> `run_task` / `run_agent_goal` in current entrypoint guidance
- `run_agent_goal(auto_confirm=False)` effectively auto-confirmed anyway -> now passes no confirmation callback unless `auto_confirm=True`
- FastMCP runtime name `grandMA2-MCP` -> `MA2 Agent`
- VS Code extension version `0.0.1` -> `1.0.0`

## 6. What was intentionally left unchanged

- `LICENSE` and `NOTICE` were left unchanged.
- Required attribution and provenance language for the fork chain was preserved.
- Historical references to upstream `ma2-onPC-MCP` and GrandPA2-Buddy were left in place where they are intentionally historical.
- Historical commit-log lines in `SESSION-HANDOVER.md` were left unchanged because they document earlier commit messages and point-in-time totals.
- No Sonnet -> Opus change was applied because no edited file contained a factual project-history Sonnet claim that needed correction.

## 7. Manual review recommendations

- Review older audit documents for deeper content drift beyond counts if they are intended to stay user-facing long term; this pass corrected the obvious current-state inconsistencies but did not rewrite whole audit narratives.
- Review whether `doc/tool-surface-tiers.md` should be expanded later into a fully refreshed 210-tool classification document; only the stale current-state framing was normalized here.
- Review whether `doc/cd-tree-mcp-tool-correlation-matrix.md` should later be fully regenerated from source if maintainers want every category subtotal refreshed, not just the stale headline math.

## 8. Final repo truth summary

MA2 Agent is the current project identity at version 1.0.0 in public repo `drohi-r/grandma2-mcp`. The current documented totals are 210 tools overall, split into 176 server tools and 34 orchestration tools, with 44 skills and 2773 tests total (2631 passing, 142 skipped, 0 failed). Current-facing docs now point to the present repo identity while preserving the required upstream attribution chain `chienchuanw -> thisis-romar -> drohi-r`.
