---
title: ma2 onPC MCP — VS Code Extension
description: VS Code extension that registers the ma2 onPC MCP server for AI assistants
version: 1.2.0
created: 2026-02-28T22:50:23Z
last_updated: 2026-04-01T00:25:43Z
---

# ma2 onPC MCP — VS Code Extension

This extension registers your ma2 onPC MCP server for AI assistants in VS Code using the Model Context Protocol (MCP) stdio transport.

## Features
- Registers the MCP server for discovery by compatible AI assistants (Claude, Copilot when supported, etc.)
- Launches the server using `uv run python -m src.server` in your workspace directory

## Usage
1. Open your workspace in VS Code.
2. Build and install this extension.
3. Compatible AI assistants will discover and connect to your MCP server automatically.

## Development
- Main activation code: `src/extension.ts`
- MCP server definition provider registered in `package.json`

## Requirements
- Node.js, npm, and VS Code
- Your Python environment and dependencies set up for the MCP server

---
Apache 2.0 License
