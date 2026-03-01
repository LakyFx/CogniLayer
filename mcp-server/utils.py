"""Shared utilities for CogniLayer MCP tools."""

import json
from pathlib import Path


def get_active_session() -> dict:
    """Load active session info from ~/.cognilayer/active_session.json."""
    session_file = Path.home() / ".cognilayer" / "active_session.json"
    if session_file.exists():
        return json.loads(session_file.read_text(encoding="utf-8"))
    return {}
