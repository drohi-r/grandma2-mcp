---
title: Terms of Use
description: Hardware safety disclaimers, liability limitations, acceptable use policy, and network security warnings for MA2 Agent
version: 1.0.0
created: 2026-04-01T00:00:00Z
last_updated: 2026-04-02T04:16:48Z
---

# Terms of Use

## 1. Hardware Safety Disclaimer

**THIS SOFTWARE CONTROLS PHYSICAL LIGHTING EQUIPMENT.**

MA2 Agent issues commands over a network connection to grandMA2 lighting consoles and software. Commands sent through this software can:

- Change or extinguish stage lighting during live performances
- Overwrite or delete show programming stored on the console
- Issue `new_show` commands that reset the console to factory state
- Modify DMX output in ways that affect physical fixtures, dimmers, and automated lights
- Disrupt communication between networked MA2 nodes

Incorrect operation, misconfigured automation, or software defects **can cause property damage, personal injury, or disruption to live events**. Before deploying this software in any production environment:

1. Verify that your network is isolated from the control console (see Section 6).
2. Test all automation scripts in a rehearsal environment before a live show.
3. Ensure that a qualified operator is present and can override AI-generated commands at any time.
4. Never allow autonomous agents to issue DESTRUCTIVE commands (`delete`, `store`, `new_show`) without human review.

---

## 2. Warranty Disclaimer

THIS SOFTWARE IS PROVIDED **"AS IS"**, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.

The authors and contributors make no representations or warranties of any kind, including but not limited to:

- Fitness for a particular purpose
- Merchantability
- Non-infringement
- Accuracy or reliability of console commands generated

You assume all risk associated with the use, operation, and results of this software. This disclaimer applies whether or not the authors were advised of the possibility of such damages.

This plain-language disclaimer supplements — and does not replace — the warranty disclaimer in the Apache License 2.0 (Section 7), which governs all use of this software.

---

## 3. Liability Limitation

TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT SHALL THE AUTHORS, CONTRIBUTORS, OR COPYRIGHT HOLDERS BE LIABLE FOR ANY:

- Direct, indirect, incidental, special, or consequential damages
- Loss of show data, show files, or programming
- Equipment damage caused by unintended DMX output
- Revenue loss resulting from show disruption
- Personal injury resulting from unintended lighting changes

arising out of or in connection with the use of this software, even if advised of the possibility of such damages.

The total cumulative liability of the authors to you for all claims shall not exceed the amount you paid for this software. Because this software is provided free of charge under an open-source license, that amount is **zero (USD $0.00)**.

---

## 4. Acceptable Use Policy

This software may NOT be used in:

- **Life-safety applications** — fire suppression control, emergency egress lighting (unless explicitly required by a qualified engineer with appropriate safety interlocks), or any system where failure could endanger human life
- **Medical equipment** — operating theater lighting or any equipment classified as a medical device
- **Unattended critical infrastructure** — automated control of venues or equipment where no qualified operator is available to respond to failures

This software is designed for:

- Stage lighting programming and control by qualified lighting technicians
- Educational environments with instructor supervision
- Busking and touring productions with an operator present
- Development and testing environments

---

## 5. IATSE / SB 132 Compliance Notice

**California SB 132 (effective July 2025)** establishes documentation requirements for AI-assisted work on covered productions.

MA2 Agent provides telemetry logging (`tool_invocations` table, `generate_compliance_report` tool) that can assist in meeting SB 132 documentation obligations. However:

- **Compliance with SB 132 remains solely the operator's and producer's responsibility.**
- This software does not guarantee that its audit trails satisfy any specific regulatory requirement.
- The `generate_compliance_report` tool produces a best-effort summary; it should be reviewed by qualified personnel before submission.

**IATSE Kit Rental:** Under the 2024 IATSE-AMPTP Basic Agreement, AI tools used in covered work may be classified as operator-provided equipment eligible for kit rental charges. Operators should consult their local IATSE agreement for applicable rates and procedures.

---

## 6. Network and Telnet Security Warning

**grandMA2 consoles ship with Telnet (port 30000) unauthenticated by default.**

Anyone with network access to port 30000 on your MA2 console can issue any console command without authentication. MA2 Agent does not add authentication to the Telnet connection itself; it adds an OAuth scope layer in the MCP server that governs which AI-issued commands are permitted.

**Operator responsibilities:**

1. **Isolate the MA2 console network.** Place the console on a dedicated VLAN or air-gapped network segment. Do not expose port 30000 to the internet or untrusted networks.
2. **Enable MA2 Telnet login.** In MA2 Setup → Console → Global Settings, enable "Login" for the Telnet service and set a strong password.
3. **Use `GMA_AUTH_BYPASS=0`** in all production deployments. Never set `GMA_AUTH_BYPASS=1` in a production environment.
4. **Rotate credentials.** Change the `GMA_OPERATOR_PASSWORD`, `GMA_PROGRAMMER_PASSWORD`, and `GMA_ADMIN_PASSWORD` environment variables from their default values before deployment.

The authors accept no liability for unauthorized access to a console resulting from misconfigured network security.

---

## 7. Governing Law

These terms are provided for informational purposes. The binding license for this software is the Apache License 2.0, included in the `LICENSE` file at the root of this repository. In the event of any conflict between these terms and the Apache License 2.0, the Apache License 2.0 governs.
