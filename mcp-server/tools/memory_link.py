"""memory_link — Manually link two facts in CogniLayer memory."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from i18n import t


def memory_link(source_id: str, target_id: str) -> str:
    """Create a manual bidirectional link between two facts."""
    db = open_db()
    try:
        # Validate both facts exist
        source = db.execute("SELECT id, content FROM facts WHERE id = ?", (source_id,)).fetchone()
        if not source:
            return t("memory_link.not_found", id=source_id)

        target = db.execute("SELECT id, content FROM facts WHERE id = ?", (target_id,)).fetchone()
        if not target:
            return t("memory_link.not_found", id=target_id)

        # Check if link already exists
        existing = db.execute("""
            SELECT 1 FROM fact_links WHERE source_id = ? AND target_id = ?
        """, (source_id, target_id)).fetchone()
        if existing:
            return t("memory_link.already_linked",
                      source=source[1][:50], target=target[1][:50])

        # Insert bidirectional links
        now = datetime.now().isoformat()
        db.execute("""
            INSERT INTO fact_links (source_id, target_id, score, link_type, created)
            VALUES (?, ?, 1.0, 'manual', ?)
        """, (source_id, target_id, now))
        db.execute("""
            INSERT OR IGNORE INTO fact_links (source_id, target_id, score, link_type, created)
            VALUES (?, ?, 1.0, 'manual', ?)
        """, (target_id, source_id, now))

        db.commit()
    finally:
        db.close()

    return t("memory_link.linked",
             source=source[1][:50], target=target[1][:50])
