"""FTS5 search helpers for CogniLayer Phase 1."""

import sqlite3
from pathlib import Path


def fts_search_facts(db: sqlite3.Connection, query: str, project: str = None,
                     fact_type: str = None, limit: int = 5,
                     scope: str = "project") -> list[dict]:
    """Search facts using FTS5 fulltext index."""
    # Build FTS5 query — escape special chars
    fts_query = query.replace('"', '""')

    conditions = []
    params = []

    if scope == "project" and project:
        conditions.append("f.project = ?")
        params.append(project)
    elif scope != "all" and scope != "project":
        # scope is a specific project name
        conditions.append("f.project = ?")
        params.append(scope)

    if fact_type:
        conditions.append("f.type = ?")
        params.append(fact_type)

    where = f"AND {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT f.id, f.project, f.content, f.type, f.domain, f.tags,
               f.timestamp, f.heat_score, f.source_file, f.source_mtime,
               f.session_id, f.rowid
        FROM facts f
        JOIN facts_fts fts ON f.rowid = fts.rowid
        WHERE facts_fts MATCH ? {where}
        ORDER BY rank
        LIMIT ?
    """
    params = [fts_query] + params + [limit]

    try:
        rows = db.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        # Fallback: LIKE search if FTS5 query syntax fails
        like_pattern = f"%{query}%"
        sql = f"""
            SELECT id, project, content, type, domain, tags,
                   timestamp, heat_score, source_file, source_mtime,
                   session_id, rowid
            FROM facts
            WHERE content LIKE ? {where.replace('f.', '')}
            ORDER BY heat_score DESC
            LIMIT ?
        """
        params = [like_pattern] + ([p for p in params[1:-1]]) + [limit]
        rows = db.execute(sql, params).fetchall()

    results = []
    for row in rows:
        results.append({
            "id": row[0], "project": row[1], "content": row[2],
            "type": row[3], "domain": row[4], "tags": row[5],
            "timestamp": row[6], "heat_score": row[7],
            "source_file": row[8], "source_mtime": row[9],
            "session_id": row[10], "rowid": row[11],
        })
    return results


def fts_search_chunks(db: sqlite3.Connection, query: str, project: str = None,
                      file_filter: str = None, limit: int = 5) -> list[dict]:
    """Search file chunks using FTS5 fulltext index."""
    fts_query = query.replace('"', '""')

    conditions = []
    params = []

    if project:
        conditions.append("fc.project = ?")
        params.append(project)

    if file_filter:
        conditions.append("fc.file_path LIKE ?")
        params.append(f"%{file_filter.replace('*', '%')}%")

    where = f"AND {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT fc.id, fc.project, fc.file_path, fc.section_title,
               fc.chunk_index, fc.content, fc.file_mtime
        FROM file_chunks fc
        JOIN chunks_fts cfts ON fc.rowid = cfts.rowid
        WHERE chunks_fts MATCH ? {where}
        ORDER BY rank
        LIMIT ?
    """
    params = [fts_query] + params + [limit]

    try:
        rows = db.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        like_pattern = f"%{query}%"
        sql = f"""
            SELECT id, project, file_path, section_title,
                   chunk_index, content, file_mtime
            FROM file_chunks
            WHERE content LIKE ? {where.replace('fc.', '')}
            ORDER BY id
            LIMIT ?
        """
        params = [like_pattern] + ([p for p in params[1:-1]]) + [limit]
        rows = db.execute(sql, params).fetchall()

    results = []
    for row in rows:
        results.append({
            "id": row[0], "project": row[1], "file_path": row[2],
            "section_title": row[3], "chunk_index": row[4],
            "content": row[5], "file_mtime": row[6],
        })
    return results
