"""session_bridge — Load or save session bridge for continuity."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session


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
        return "Zadny session bridge k dispozici."

    elif action == "save":
        if not content:
            return "Chybi obsah bridge ke ulozeni."
        if not session_id:
            return "Zadna aktivni session."

        db = open_db()
        try:
            db.execute("""
                UPDATE sessions SET bridge_content = ? WHERE id = ?
            """, (content, session_id))
            db.commit()
        finally:
            db.close()

        return "Session bridge ulozen."

    return f"Neznama akce: {action}. Pouzij 'load' nebo 'save'."
