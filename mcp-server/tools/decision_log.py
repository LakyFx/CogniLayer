"""decision_log — Query decision log for current project."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session
from i18n import t


def decision_log(query: str = None, project: str = None, limit: int = 5) -> str:
    """Query decision log entries."""
    session = get_active_session()
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
        search_info = t("decision_log.search_info", query=query) if query else ""
        return t("decision_log.no_decisions", search_info=search_info, project=project)

    lines = [t("decision_log.header", project=project)]
    for i, row in enumerate(rows, 1):
        alts = row[3] or ""
        line = f"{i}. [{row[4][:10]}] {row[1]}"
        if row[2]:
            line += f"\n   {t('decision_log.reason_label')}{row[2]}"
        if alts:
            line += f"\n   {t('decision_log.alternatives_label')}{alts}"
        lines.append(line)

    return "\n\n".join(lines)
