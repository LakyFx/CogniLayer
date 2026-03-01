"""session_bridge — Load or save session bridge for continuity."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session
from i18n import t


def session_bridge(action: str, content: str = None) -> str:
    """Load or save session bridge."""
    session = get_active_session()
    project = session.get("project", "")
    session_id = session.get("session_id", "")

    if action == "load":
        db = open_db()
        try:
            row = db.execute("""
                SELECT bridge_content, start_time, end_time FROM sessions
                WHERE project = ? AND bridge_content IS NOT NULL
                ORDER BY start_time DESC LIMIT 1
            """, (project,)).fetchone()
        finally:
            db.close()

        if row and row[0]:
            return f"## Session Bridge\n{row[0]}"
        return t("session_bridge.no_bridge")

    elif action == "save":
        if not content:
            return t("session_bridge.missing_content")
        if not session_id:
            return t("session_bridge.no_session")

        db = open_db()
        try:
            cursor = db.execute("""
                UPDATE sessions SET bridge_content = ? WHERE id = ?
            """, (content, session_id))
            if cursor.rowcount == 0:
                return "Warning: Session not found in DB. Bridge not saved."
            db.commit()
        finally:
            db.close()

        return t("session_bridge.saved")

    return t("session_bridge.unknown_action", action=action)
