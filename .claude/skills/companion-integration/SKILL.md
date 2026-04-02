---
title: Companion Integration
description: Guide for setting up Bitfocus Companion button pages that mirror the MA2 executor layout
version: 1.0.0
safety_scope: SAFE_READ
created: 2026-04-02T00:00:00Z
last_updated: 2026-04-02T00:00:00Z
---

# Companion Integration

## Charter

SAFE_READ skill — generates configuration files and provides setup guidance. No console state is modified.

## Invocation

Use when an operator wants to control their grandMA2 console from a Stream Deck, touch screen, or other Companion-connected surface. This skill bridges the MA2 executor layout to Companion button pages.

## Target Users

Lighting operators and technicians who use Bitfocus Companion alongside grandMA2. Assumes Companion is installed and running.

---

## Prerequisites

Before starting, the operator needs:
- Bitfocus Companion installed and running (v3.x or v4.x)
- grandMA2 console with Telnet enabled (Setup → Console → Global Settings → Telnet)
- Network connectivity between the Companion machine and the console

---

## Phase 1: Read Current Layout (SAFE_READ)

**Goal:** Understand what's on the MA2 executor page.

1. Call `scan_page_executor_layout(page=1)` to read the current executor assignments
2. Present findings: "Page 1 has 12 executors assigned — 4 intensity groups, 3 color effects, 2 position presets, 3 macros"
3. Ask the operator which page(s) they want on their Companion surface

**Allowed tools:** `scan_page_executor_layout`, `get_executor_status`

---

## Phase 2: Generate Config (SAFE_READ)

**Goal:** Create a Companion-importable button page.

1. Call `generate_companion_config(page=1, grid_columns=8)` for Stream Deck XL, or `grid_columns=5` for standard Stream Deck
2. Present the result — number of buttons generated, layout preview
3. Instruct the operator to save the `companion_config` JSON to a `.companionconfig` file

**Allowed tools:** `generate_companion_config`

---

## Phase 3: Guide Companion Setup

**Goal:** Walk the operator through importing and configuring.

### Step 1: Add the grandMA2 Connection
1. Open Companion web UI (usually `http://localhost:8000`)
2. Go to **Connections** tab
3. Click **Add Connection**
4. Search for **"grandMA2"** (module: malighting-grandma2)
5. Configure:
   - **Host:** the console's IP address (e.g., `192.168.1.100`)
   - **Port:** `30000` (default MA2 Telnet port)
   - **Label:** give it a name like "MA2 Console"
6. Save — the connection status should show green

### Step 2: Import the Button Page
1. Go to **Buttons** tab
2. Click the **Import** button (top-right)
3. Select the `.companionconfig` file generated in Phase 2
4. Choose which Companion page to import to
5. Click **Import**

### Step 3: Verify
1. Press any button on the Companion surface
2. Check that the MA2 console responds (executor should fire)
3. If no response, check:
   - Companion connection status (should be green)
   - MA2 Telnet is enabled
   - Firewall isn't blocking port 30000

---

## Phase 4: Advanced Configuration

### Custom Button Actions
Each generated button sends `Go+ Executor {page}.{id}` by default. Operators can customize:
- **Flash:** Change action to `Flash Executor {page}.{id}` (button down) + `Flash Off` (button up)
- **Toggle:** Change action to `Toggle Executor {page}.{id}`
- **Goto Cue:** Change action to `Goto Cue {N} Executor {page}.{id}`
- **Blackout:** Add a dedicated B.O. button with action `Blackout`

### Multiple Pages
Generate configs for multiple MA2 pages:
- Page 1: Main playback executors
- Page 2: Effect executors
- Page 3: Macro buttons

### Remote Button Press
Use `companion_button_press(page=1, button=0)` to programmatically trigger Companion buttons from the AI agent — useful for automated show control sequences.

---

## Allowed Tools

`scan_page_executor_layout`, `get_executor_status`, `generate_companion_config`, `companion_button_press`
