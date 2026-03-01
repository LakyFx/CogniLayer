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

        # V3: Memory Health
        warm_count = db.execute(
            "SELECT COUNT(*) FROM facts WHERE project = ? AND heat_score >= 0.3 AND heat_score < 0.8",
            (project,)
        ).fetchone()[0]
        cold_count = facts_count - hot_count - warm_count

        most_retrieved = None
        never_retrieved = 0
        avg_retrievals = 0.0
        try:
            row = db.execute(
                "SELECT content, retrieval_count FROM facts WHERE project = ? ORDER BY retrieval_count DESC LIMIT 1",
                (project,)
            ).fetchone()
            if row and row[1]:
                most_retrieved = (row[0][:50], row[1])
            never_retrieved = db.execute(
                "SELECT COUNT(*) FROM facts WHERE project = ? AND (retrieval_count IS NULL OR retrieval_count = 0)",
                (project,)
            ).fetchone()[0]
            avg_row = db.execute(
                "SELECT AVG(COALESCE(retrieval_count, 0)) FROM facts WHERE project = ?",
                (project,)
            ).fetchone()
            avg_retrievals = avg_row[0] or 0.0
        except Exception:
            pass  # retrieval_count column might not exist yet

        # V3: Knowledge Gaps
        knowledge_gaps = []
        try:
            gap_rows = db.execute("""
                SELECT query, times_seen, last_seen FROM knowledge_gaps
                WHERE project = ? AND resolved = 0
                ORDER BY times_seen DESC LIMIT 5
            """, (project,)).fetchall()
            knowledge_gaps = [(r[0], r[1], r[2]) for r in gap_rows]
        except Exception:
            pass  # knowledge_gaps table might not exist yet
    finally:
        db.close()

    stats = t("project_context.stats",
              facts_count=facts_count, hot_count=hot_count,
              chunks_count=chunks_count, sessions_count=sessions_count,
              changes_count=changes_count)

    # Memory Health section
    health = t("project_context.health_header")
    health += t("project_context.health_stats",
                total=facts_count, hot=hot_count, warm=warm_count, cold=cold_count)
    if most_retrieved:
        health += "\n" + t("project_context.most_retrieved",
                           content=most_retrieved[0], count=most_retrieved[1])
    health += "\n" + t("project_context.never_retrieved", count=never_retrieved)
    health += f"\n- Avg retrievals/fact: {avg_retrievals:.1f}"

    # Knowledge Gaps section
    gaps = ""
    if knowledge_gaps:
        gaps = "\n" + t("project_context.gaps_header")
        for query, times, last_seen in knowledge_gaps:
            gaps += "\n" + t("project_context.gaps_item",
                             query=query, times=times)
    elif facts_count > 0:
        gaps = "\n" + t("project_context.no_gaps")

    return f"{dna}{bridge}\n{stats}\n{health}{gaps}"
