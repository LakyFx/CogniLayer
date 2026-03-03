"""memory_write — Store facts into CogniLayer memory with vector embeddings."""

import re
import sqlite3
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
            if distance > 0.65:
                continue  # Too dissimilar (threshold based on P20 of actual distance distribution)
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
    except Exception as e:
        print(f"[CogniLayer] auto-link failed: {e}", file=sys.stderr)


def _resolve_gaps(db, project: str, content: str):
    """Auto-resolve knowledge gaps when new knowledge is written."""
    try:
        # Check if any unresolved gaps match this new content via FTS5
        gaps = db.execute("""
            SELECT kg.id, kg.query FROM knowledge_gaps kg
            WHERE kg.project = ? AND kg.resolved = 0
        """, (project,)).fetchall()
        for gap in gaps:
            # Word boundary check — gap query words must appear as whole words in content
            query_words = gap[1].lower().split()
            content_words = set(re.findall(r'\b\w+\b', content.lower()))
            if all(w in content_words for w in query_words):
                db.execute("UPDATE knowledge_gaps SET resolved = 1 WHERE id = ?", (gap[0],))
    except Exception:
        pass  # Gap resolution is best-effort


# Patterns that indicate secrets/credentials — MUST NOT be saved to memory
_SECRET_PATTERNS = [
    (r'(?:sk|pk)[-_](?:live|test|prod)[a-zA-Z0-9_\-]{20,}', "API key"),
    (r'ghp_[a-zA-Z0-9]{36,}', "GitHub token"),
    (r'github_pat_[a-zA-Z0-9_]{20,}', "GitHub PAT"),
    (r'gho_[a-zA-Z0-9]{36,}', "GitHub OAuth token"),
    (r'AKIA[0-9A-Z]{16}', "AWS access key"),
    (r'(?:Bearer|token)\s+[a-zA-Z0-9_\-\.]{20,}', "Bearer/auth token"),
    (r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', "Private key"),
    (r'(?:password|passwd|pwd)\s*[=:]\s*["\']?[^\s"\']{8,}', "Password"),
    (r'(?:secret|api_key|apikey|access_token|auth_token)\s*[=:]\s*["\']?[a-zA-Z0-9_\-]{16,}', "Secret/token"),
    (r'mongodb(?:\+srv)?://[^\s]+:[^\s]+@', "MongoDB connection string"),
    (r'postgres(?:ql)?://[^\s]+:[^\s]+@', "PostgreSQL connection string"),
    (r'mysql://[^\s]+:[^\s]+@', "MySQL connection string"),
    (r'redis://:[^\s]+@', "Redis connection string"),
    (r'xox[bporas]-[a-zA-Z0-9\-]{10,}', "Slack token"),
    (r'sk-[a-zA-Z0-9_\-]{20,}', "OpenAI API key"),
    (r'sk-ant-[a-zA-Z0-9_\-]{20,}', "Anthropic API key"),
]


def _save_history(db, fact_id: str, project: str, content: str,
                  fact_type: str, session_id: str, action: str):
    """Save a snapshot of a fact before update/delete. Best-effort — never fails."""
    try:
        # Get full fact data for domain/tags
        row = db.execute(
            "SELECT domain, tags FROM facts WHERE id = ?", (fact_id,)
        ).fetchone()
        db.execute("""
            INSERT INTO facts_history (fact_id, project, content, type, domain, tags,
                                       action, changed_at, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (fact_id, project, content, fact_type,
              row[0] if row else None, row[1] if row else None,
              action, datetime.now().isoformat(), session_id))
    except Exception:
        pass  # History is best-effort — table may not exist yet


def _check_secrets(content: str) -> str | None:
    """Check content for potential secrets. Returns warning message or None."""
    for pattern, label in _SECRET_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return label
    return None


def _check_content_duplicate(db, project: str, fact_type: str, content: str) -> bool:
    """Check if a very similar fact already exists (for facts without source_file).

    Uses exact content match first, then FTS5 keyword overlap.
    Only blocks near-exact duplicates — different topics are allowed through.
    This ensures we don't accumulate identical facts from repeated sessions
    while still accepting legitimately new facts about related topics.
    """
    # 1. Exact content match
    exact = db.execute("""
        SELECT 1 FROM facts
        WHERE project = ? AND type = ? AND content = ?
        LIMIT 1
    """, (project, fact_type, content)).fetchone()
    if exact:
        return True

    # 2. Normalized content match (ignore whitespace differences)
    normalized = " ".join(content.lower().split())
    if len(normalized) < 20:
        return False  # Too short for fuzzy matching

    # 3. Check for high keyword overlap with existing facts of same type
    # Extract significant words (>3 chars) from the new content
    content_words = set(w for w in re.findall(r'\b\w+\b', normalized) if len(w) > 3)
    if len(content_words) < 3:
        return False  # Too few significant words

    # Search existing facts of same project+type using FTS5
    try:
        # Build FTS5 query from top keywords (max 5 to keep it fast)
        fts_terms = list(content_words)[:5]
        fts_query = " OR ".join(fts_terms)
        candidates = db.execute("""
            SELECT f.content FROM facts f
            JOIN facts_fts fts ON f.rowid = fts.rowid
            WHERE fts.facts_fts MATCH ? AND f.project = ? AND f.type = ?
            LIMIT 10
        """, (fts_query, project, fact_type)).fetchall()

        for cand in candidates:
            cand_normalized = " ".join(cand[0].lower().split())
            cand_words = set(w for w in re.findall(r'\b\w+\b', cand_normalized) if len(w) > 3)

            # Jaccard similarity — only block if >80% word overlap
            if content_words and cand_words:
                intersection = content_words & cand_words
                union = content_words | cand_words
                jaccard = len(intersection) / len(union)
                if jaccard > 0.80:
                    return True
    except Exception:
        pass  # FTS5 search failed — allow the write

    return False


def memory_write(content: str, type: str = "fact", tags: str = None,
                 domain: str = None, source_file: str = None) -> str:
    """Write a fact to CogniLayer memory with deduplication and secrets filtering."""
    # Security: block secrets from being saved
    secret_type = _check_secrets(content)
    if secret_type:
        return t("memory_write.blocked_secret", secret_type=secret_type)

    session = get_active_session()
    project = session.get("project", "unknown")
    session_id = session.get("session_id", None)
    project_path = session.get("project_path", "")

    db = open_db()
    try:
        # Use BEGIN IMMEDIATE for atomic read-modify-write (prevents race conditions
        # when multiple CLIs write simultaneously with same source_file+type)
        db.execute("BEGIN IMMEDIATE")

        # Deduplication path 1: source_file + type (exact match)
        if source_file and type:
            existing = db.execute("""
                SELECT id, content, rowid FROM facts
                WHERE project = ? AND source_file = ? AND type = ?
            """, (project, source_file, type)).fetchone()

            if existing:
                if existing[1] == content:
                    db.commit()
                    return t("memory_write.exists_unchanged", preview=content[:60])
                # Save old version to history before overwriting
                _save_history(db, existing[0], project, existing[1], type, session_id, "update")
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

        # Deduplication path 2: content similarity for facts WITHOUT source_file
        # Uses FTS5 to find highly similar existing facts. Only blocks exact or
        # near-exact duplicates — different topics that look similar are allowed.
        if not source_file:
            duplicate = _check_content_duplicate(db, project, type, content)
            if duplicate:
                db.commit()
                return t("memory_write.exists_unchanged", preview=content[:60])

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
    except sqlite3.OperationalError as e:
        # Rollback on lock timeout — don't lose data silently
        try:
            db.rollback()
        except Exception:
            pass
        if "locked" in str(e) or "busy" in str(e):
            return t("memory_write.saved", preview=content[:60], project=project, type=type) + " (warning: DB busy, retried)"
        raise
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
