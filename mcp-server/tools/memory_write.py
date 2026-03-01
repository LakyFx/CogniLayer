"""memory_write — Store facts into CogniLayer memory with vector embeddings."""

import uuid
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db, ensure_vec
from utils import get_active_session
from i18n import t


def _embed_fact(db, rowid: int, content: str, tags: str = None, domain: str = None) -> bytes | None:
    """Generate and store embedding for a fact. Returns embedding bytes or None."""
    try:
        if not ensure_vec(db):
            return None
        from embedder import embed_text
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
        return embedding
    except Exception:
        return None


def _auto_link_fact(db, fact_id: str, rowid: int, embedding: bytes, project: str):
    """Auto-link new fact to related facts via cosine similarity."""
    if embedding is None:
        return
    try:
        rows = db.execute("""
            SELECT rowid, distance FROM facts_vec
            WHERE embedding MATCH ? AND k = 6
        """, (embedding,)).fetchall()

        now = datetime.now().isoformat()
        for row in rows:
            vec_rowid, distance = row[0], row[1]
            if vec_rowid == rowid:
                continue  # Skip self
            if distance > 0.25:
                continue  # Too dissimilar (cosine distance > 0.25 = similarity < 0.75)
            # Get target fact ID and verify same project
            target = db.execute(
                "SELECT id, project FROM facts WHERE rowid = ?", (vec_rowid,)
            ).fetchone()
            if not target or target[1] != project:
                continue
            target_id = target[0]
            score = 1.0 - distance  # Convert distance to similarity
            # Insert bidirectional links (ignore duplicates)
            db.execute("""
                INSERT OR IGNORE INTO fact_links (source_id, target_id, score, link_type, created)
                VALUES (?, ?, ?, 'auto', ?)
            """, (fact_id, target_id, score, now))
            db.execute("""
                INSERT OR IGNORE INTO fact_links (source_id, target_id, score, link_type, created)
                VALUES (?, ?, ?, 'auto', ?)
            """, (target_id, fact_id, score, now))
    except Exception:
        pass  # Linking is best-effort


def _resolve_gaps(db, project: str, content: str):
    """Auto-resolve knowledge gaps when new knowledge is written."""
    try:
        # Check if any unresolved gaps match this new content via FTS5
        gaps = db.execute("""
            SELECT kg.id, kg.query FROM knowledge_gaps kg
            WHERE kg.project = ? AND kg.resolved = 0
        """, (project,)).fetchall()
        for gap in gaps:
            # Simple containment check — if gap query words appear in content
            query_words = gap[1].lower().split()
            content_lower = content.lower()
            if all(w in content_lower for w in query_words):
                db.execute("UPDATE knowledge_gaps SET resolved = 1 WHERE id = ?", (gap[0],))
    except Exception:
        pass  # Gap resolution is best-effort


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
                # Update embedding + auto-link
                emb = _embed_fact(db, existing[2], content, tags, domain)
                _auto_link_fact(db, existing[0], existing[2], emb, project)
                _resolve_gaps(db, project, content)
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

        # Get rowid for vector table and embed + auto-link
        rowid = db.execute("SELECT rowid FROM facts WHERE id = ?", (fact_id,)).fetchone()[0]
        emb = _embed_fact(db, rowid, content, tags, domain)
        _auto_link_fact(db, fact_id, rowid, emb, project)
        _resolve_gaps(db, project, content)

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
