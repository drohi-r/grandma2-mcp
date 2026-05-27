"""GMA_MOCK — in-memory SessionManager + TelnetClient.

Tier 1 (``GMA_MOCK=1`` or ``GMA_MOCK=canned``):
    Regex-keyed canned responses for the most common command shapes.
    Unknown commands return ``"MOCK: command not stubbed"``.

Tier 2 (``GMA_MOCK=schema``):
    Stateful in-memory show fixture (``tests/fixtures/mock_show_state.json``).
    Supports list group / list executor / list preset via fixture data.

Tier 3 (``GMA_MOCK=replay:<path>``):
    Replay a JSONL transcript captured from a real console. Stub in Path A.
"""
