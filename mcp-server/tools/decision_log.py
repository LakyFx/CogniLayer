"""decision_log — Query decision log for current project."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db


def _get_active_session():
    session_file = Path.home() / ".cognilayer" / "active_session.json"
    if session_file.exists():
        return json.loads(session_file.read_text(encoding="utf-8"))
    return {}


def decision_log(query: str = None, project: str = None, limit: int = 5) -> str:
    """Query decision log entries."""
    session = _get_active_session()
    if not project:
        project = session.get("project", "")

    db = open_db()
    try:
        if query:
            rows = db.execute("""
                SELECT id, decision, reason, alternatives, timestamp
                FROM decisions
                WHERE project = ? AND (decision LIKE ? OR reason LIKE ?)
                ORDER BY timestamp DESC LIMIT ?
            """, (project, f"%{query}%", f"%{query}%", limit)).fetchall()
        else:
            rows = db.execute("""
                SELECT id, decision, reason, alternatives, timestamp
                FROM decisions
                WHERE project = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (project, limit)).fetchall()
    finally:
        db.close()

    if not rows:
        search_info = f" pro '{query}'" if query else ""
        return f"Zadna rozhodnuti{search_info} v projektu {project}."

    lines = [f"## Rozhodnuti pro {project}\n"]
    for i, row in enumerate(rows, 1):
        alts = row[3] or ""
        line = f"{i}. [{row[4][:10]}] {row[1]}"
        if row[2]:
            line += f"\n   Duvod: {row[2]}"
        if alts:
            line += f"\n   Alternativy: {alts}"
        lines.append(line)

    return "\n\n".join(lines)
