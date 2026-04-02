"""
context.py — Shared asyncio ContextVars for the MCP server.

These variables are set by the orchestrator before each SubTask execution so that
tool decorators (e.g. @_handle_errors in server.py) can read them without needing
to thread extra parameters through every call site.

Placing them in a neutral module avoids the circular import that would arise if
server.py and orchestrator.py both imported from each other.
"""

import contextvars

# Set by Orchestrator._run_sequential / _run_parallel before each SubTask call.
# Read by @_handle_errors to populate the session_id column in tool_invocations.
_current_session_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "_current_session_id", default=""
)
