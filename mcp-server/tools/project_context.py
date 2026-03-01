"""project_context — Return Project DNA and current context."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session


def project_context() -> str:
    """Return Project DNA, last bridge, and stats for current project."""
    session = get_active_session()
    project = session.get("project", "")

    if not project:
        return "Zadny aktivni projekt. Spust claude v projektovem adresari."

    db = open_db()
    try:
        # Get project DNA
        proj = db.execute(
            "SELECT dna_content, created, last_session FROM projects WHERE name = ?",
            (project,)
        ).fetchone()

        if not proj:
            return f"Projekt '{project}' neni registrovany v CogniLayer."

        dna = proj[0] or f"## Project DNA: {project}\n[DNA jeste nebyla vygenerovana]"

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

    stats = f"""
## Statistiky
- Faktu v pameti: {facts_count} (hot: {hot_count})
- Indexovanych chunku: {chunks_count}
- Sessions: {sessions_count}
- Zaznamenanych zmen: {changes_count}"""

    return f"{dna}{bridge}\n{stats}"
