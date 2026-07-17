"""Run the MA2 web UI with sensible local-operator defaults.

The dashboard needs elevated read scopes (session/user views) and the
Actions tab drives the agent runtime, so default to full local scope and
auth bypass unless the environment already says otherwise.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("GMA_SCOPE", "tier:5")
os.environ.setdefault("GMA_AUTH_BYPASS", "1")

from src.ui import main

if __name__ == "__main__":
    main()
