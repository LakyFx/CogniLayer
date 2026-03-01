"""memory_write — Store facts into CogniLayer memory with vector embeddings."""

import uuid
import os
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db, ensure_vec
from utils import get_active_session
from i18n import t


def _embed_fact(db, rowid: int, content: str, tags: str = None, domain: str = None):
    """Generate and store embedding for a fact. Non-blocking — skips on error."""
    try:
        if not ensure_vec(db):
            return  # sqlite-vec not available, skip embedding storage
        from embedder import embed_text
        # Combine content with tags/domain for richer embedding
        embed_input = content
        if tags:
            embed_input += f" [{tags}]"
        if domain:
            embed_input += f" [{domain}]"
        embedding = embed_text(embed_input)
        db.execute(
            "INSERT OR REPLACE INTO facts_vec(rowid, embedding) VALUES (?, ?)",
            (rowid, embedding)
        )
    except Exception:
        pass  # Embedding failed, FTS5 still works


def memory_write(content: str, type: str = "fact", tags: str = None,
                 domain: str = None, source_file: str = None) -> str:
    """Write a fact to CogniLayer memory with deduplication."""
    session = get_active_session()
    project = session.get("project", "unknown")
    session_id = session.get("session_id", None)
    project_path = session.get("project_path", "")

    db = open_db()
    try:
        # Deduplication: check for existing fact with same source_file + type
        if source_file and type:
            existing = db.execute("""
                SELECT id, content, rowid FROM facts
                WHERE project = ? AND source_file = ? AND type = ?
            """, (project, source_file, type)).fetchone()

            if existing:
                if existing[1] == content:
                    return t("memory_write.exists_unchanged", preview=content[:60])
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
                # Update embedding
                _embed_fact(db, existing[2], content, tags, domain)
                db.commit()
                return t("memory_write.updated", preview=content[:60], project=project, type=type)

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

        # Get rowid for vector table and embed
        rowid = db.execute("SELECT rowid FROM facts WHERE id = ?", (fact_id,)).fetchone()[0]
        _embed_fact(db, rowid, content, tags, domain)

        db.commit()
    finally:
        db.close()

    return t("memory_write.saved", preview=content[:60], project=project, type=type)


def _get_mtime(project_path: str, source_file: str) -> float | None:
    if not project_path or not source_file:
        return None
    fp = Path(project_path) / source_file
    if fp.exists():
        return fp.stat().st_mtime
    return None
