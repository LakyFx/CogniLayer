"""memory_write — Store facts into CogniLayer memory."""

import json
import uuid
import os
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db


def _get_active_session():
    session_file = Path.home() / ".cognilayer" / "active_session.json"
    if session_file.exists():
        return json.loads(session_file.read_text(encoding="utf-8"))
    return {}


def memory_write(content: str, type: str = "fact", tags: str = None,
                 domain: str = None, source_file: str = None) -> str:
    """Write a fact to CogniLayer memory with deduplication."""
    session = _get_active_session()
    project = session.get("project", "unknown")
    session_id = session.get("session_id", None)
    project_path = session.get("project_path", "")

    db = open_db()
    try:
        # Deduplication: check for existing fact with same source_file + type
        if source_file and type:
            existing = db.execute("""
                SELECT id, content FROM facts
                WHERE project = ? AND source_file = ? AND type = ?
            """, (project, source_file, type)).fetchone()

            if existing:
                if existing[1] == content:
                    return f"Fakt uz existuje (beze zmeny): {content[:60]}..."
                # Update existing
                db.execute("""
                    UPDATE facts SET content = ?, tags = ?, domain = ?,
                                     timestamp = ?, heat_score = 1.0,
                                     session_id = ?, source_mtime = ?
                    WHERE id = ?
                """, (
                    content, tags, domain, datetime.now().isoformat(),
                    session_id,
                    _get_mtime(project_path, source_file),
                    existing[0]
                ))
                db.commit()
                return f"Aktualizovano v pameti: {content[:60]}... [projekt: {project}, typ: {type}]"

        # Insert new fact
        fact_id = str(uuid.uuid4())
        source_mtime = _get_mtime(project_path, source_file) if source_file else None

        db.execute("""
            INSERT INTO facts (id, project, content, type, domain, tags,
                              timestamp, heat_score, session_id,
                              source_file, source_mtime)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1.0, ?, ?, ?)
        """, (
            fact_id, project, content, type, domain, tags,
            datetime.now().isoformat(), session_id,
            source_file, source_mtime
        ))
        db.commit()
    finally:
        db.close()

    return f"Ulozeno do pameti: {content[:60]}... [projekt: {project}, typ: {type}]"


def _get_mtime(project_path: str, source_file: str) -> float | None:
    if not project_path or not source_file:
        return None
    fp = Path(project_path) / source_file
    if fp.exists():
        return fp.stat().st_mtime
    return None
