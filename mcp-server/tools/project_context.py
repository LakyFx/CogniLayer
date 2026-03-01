"""project_context — Return Project DNA and current context."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session
from i18n import t


def project_context() -> str:
    """Return Project DNA, last bridge, and stats for current project."""
    session = get_active_session()
    project = session.get("project", "")

    if not project:
        return t("project_context.no_project")

    db = open_db()
    try:
        # Get project DNA
        proj = db.execute(
            "SELECT dna_content, created, last_session FROM projects WHERE name = ?",
            (project,)
        ).fetchone()

        if not proj:
            return t("project_context.not_registered", project=project)

        dna = proj[0] or t("project_context.dna_placeholder", project=project)

        # Get latest bridge from last completed session
        bridge_row = db.execute("""
            SELECT bridge_content, start_time, end_time FROM sessions
            WHERE project = ? AND bridge_content IS NOT NULL
            ORDER BY start_time DESC LIMIT 1
        """, (project,)).fetchone()

        bridge = ""
        if bridge_row and bridge_row[0]:
            bridge = f"\n\n## Last Session Bridge\n{bridge_row[0]}"

        # Stats
        facts_count = db.execute(
            "SELECT COUNT(*) FROM facts WHERE project = ?", (project,)
        ).fetchone()[0]

        hot_count = db.execute(
            "SELECT COUNT(*) FROM facts WHERE project = ? AND heat_score > 0.8",
            (project,)
        ).fetchone()[0]

        chunks_count = db.execute(
            "SELECT COUNT(*) FROM file_chunks WHERE project = ?", (project,)
        ).fetchone()[0]

        sessions_count = db.execute(
            "SELECT COUNT(*) FROM sessions WHERE project = ?", (project,)
        ).fetchone()[0]

        changes_count = db.execute(
            "SELECT COUNT(*) FROM changes WHERE project = ?", (project,)
        ).fetchone()[0]
    finally:
        db.close()

    stats = t("project_context.stats",
              facts_count=facts_count, hot_count=hot_count,
              chunks_count=chunks_count, sessions_count=sessions_count,
              changes_count=changes_count)

    return f"{dna}{bridge}\n{stats}"
