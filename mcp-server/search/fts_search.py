"""Search helpers for CogniLayer — FTS5 + vector hybrid search (Phase 2)."""

import sqlite3
from pathlib import Path


def _vec_available(db: sqlite3.Connection) -> bool:
    """Check if sqlite-vec is loaded and vector tables exist."""
    try:
        db.execute("SELECT COUNT(*) FROM facts_vec")
        return True
    except Exception:
        return False


def _vec_search_facts(db: sqlite3.Connection, query_embedding: bytes,
                      project: str = None, fact_type: str = None,
                      scope: str = "project", limit: int = 20) -> dict[int, float]:
    """Vector similarity search on facts. Returns {rowid: distance}."""
    rows = db.execute("""
        SELECT rowid, distance
        FROM facts_vec
        WHERE embedding MATCH ? AND k = ?
    """, (query_embedding, limit * 3)).fetchall()

    # Filter by project/type using facts table
    results = {}
    for row in rows:
        rowid, distance = row[0], row[1]
        fact = db.execute("SELECT project, type FROM facts WHERE rowid = ?", (rowid,)).fetchone()
        if not fact:
            continue
        if scope == "project" and project and fact[0] != project:
            continue
        if scope != "all" and scope != "project" and fact[0] != scope:
            continue
        if fact_type and fact[1] != fact_type:
            continue
        results[rowid] = distance

    return results


def _vec_search_chunks(db: sqlite3.Connection, query_embedding: bytes,
                       project: str = None, file_filter: str = None,
                       limit: int = 20) -> dict[int, float]:
    """Vector similarity search on chunks. Returns {rowid: distance}."""
    rows = db.execute("""
        SELECT rowid, distance
        FROM chunks_vec
        WHERE embedding MATCH ? AND k = ?
    """, (query_embedding, limit * 3)).fetchall()

    results = {}
    for row in rows:
        rowid, distance = row[0], row[1]
        chunk = db.execute(
            "SELECT project, file_path FROM file_chunks WHERE rowid = ?", (rowid,)
        ).fetchone()
        if not chunk:
            continue
        if project and chunk[0] != project:
            continue
        if file_filter:
            pattern = file_filter.replace("*", "")
            if pattern not in chunk[1]:
                continue
        results[rowid] = distance

    return results


def _hybrid_rank(fts_results: list[dict], vec_distances: dict[int, float],
                 fts_weight: float = 0.4, vec_weight: float = 0.6) -> list[dict]:
    """Combine FTS5 and vector results with weighted ranking.

    FTS5 rank: position-based (1st result = 1.0, last = 0.0)
    Vector distance: converted to similarity (lower distance = higher score)
    """
    all_rowids = set()
    fts_scores = {}
    vec_scores = {}

    # FTS5 scores: position-based
    for i, result in enumerate(fts_results):
        rowid = result["rowid"]
        all_rowids.add(rowid)
        fts_scores[rowid] = 1.0 - (i / max(len(fts_results), 1))

    # Vector scores: distance -> similarity (0-1)
    if vec_distances:
        max_dist = max(vec_distances.values()) if vec_distances else 1.0
        for rowid, distance in vec_distances.items():
            all_rowids.add(rowid)
            vec_scores[rowid] = 1.0 - (distance / max(max_dist * 1.2, 0.001))

    # Build result lookup from FTS results
    result_lookup = {r["rowid"]: r for r in fts_results}

    # Combine scores
    scored = []
    for rowid in all_rowids:
        fts_s = fts_scores.get(rowid, 0.0)
        vec_s = vec_scores.get(rowid, 0.0)
        combined = (fts_weight * fts_s) + (vec_weight * vec_s)

        if rowid in result_lookup:
            result = result_lookup[rowid]
            result["_hybrid_score"] = combined
            scored.append(result)

    scored.sort(key=lambda x: x["_hybrid_score"], reverse=True)
    return scored


def fts_search_facts(db: sqlite3.Connection, query: str, project: str = None,
                     fact_type: str = None, limit: int = 5,
                     scope: str = "project") -> list[dict]:
    """Search facts using FTS5 + optional vector hybrid search."""
    # Build FTS5 query — escape special chars
    fts_query = query.replace('"', '""')

    conditions = []
    params = []

    if scope == "project" and project:
        conditions.append("f.project = ?")
        params.append(project)
    elif scope != "all" and scope != "project":
        conditions.append("f.project = ?")
        params.append(scope)

    if fact_type:
        conditions.append("f.type = ?")
        params.append(fact_type)

    where = f"AND {' AND '.join(conditions)}" if conditions else ""

    # FTS5 search (fetch more for hybrid merge)
    fetch_limit = limit * 3 if _vec_available(db) else limit

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
    fts_params = [fts_query] + params + [fetch_limit]

    try:
        rows = db.execute(sql, fts_params).fetchall()
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
        fts_params = [like_pattern] + ([p for p in params]) + [fetch_limit]
        rows = db.execute(sql, fts_params).fetchall()

    fts_results = []
    for row in rows:
        fts_results.append({
            "id": row[0], "project": row[1], "content": row[2],
            "type": row[3], "domain": row[4], "tags": row[5],
            "timestamp": row[6], "heat_score": row[7],
            "source_file": row[8], "source_mtime": row[9],
            "session_id": row[10], "rowid": row[11],
        })

    # Hybrid search: combine with vector results if available
    if _vec_available(db):
        try:
            from embedder import embed_text
            query_embedding = embed_text(query)
            vec_distances = _vec_search_facts(db, query_embedding, project, fact_type, scope, limit)
            if vec_distances:
                fts_results = _hybrid_rank(fts_results, vec_distances)
        except Exception:
            pass  # Vector search failed, use FTS5 only

    return fts_results[:limit]


def fts_search_chunks(db: sqlite3.Connection, query: str, project: str = None,
                      file_filter: str = None, limit: int = 5) -> list[dict]:
    """Search file chunks using FTS5 + optional vector hybrid search."""
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

    fetch_limit = limit * 3 if _vec_available(db) else limit

    sql = f"""
        SELECT fc.id, fc.project, fc.file_path, fc.section_title,
               fc.chunk_index, fc.content, fc.file_mtime, fc.rowid
        FROM file_chunks fc
        JOIN chunks_fts cfts ON fc.rowid = cfts.rowid
        WHERE chunks_fts MATCH ? {where}
        ORDER BY rank
        LIMIT ?
    """
    fts_params = [fts_query] + params + [fetch_limit]

    try:
        rows = db.execute(sql, fts_params).fetchall()
    except sqlite3.OperationalError:
        like_pattern = f"%{query}%"
        sql = f"""
            SELECT id, project, file_path, section_title,
                   chunk_index, content, file_mtime, rowid
            FROM file_chunks
            WHERE content LIKE ? {where.replace('fc.', '')}
            ORDER BY id
            LIMIT ?
        """
        fts_params = [like_pattern] + ([p for p in params]) + [fetch_limit]
        rows = db.execute(sql, fts_params).fetchall()

    fts_results = []
    for row in rows:
        fts_results.append({
            "id": row[0], "project": row[1], "file_path": row[2],
            "section_title": row[3], "chunk_index": row[4],
            "content": row[5], "file_mtime": row[6], "rowid": row[7],
        })

    # Hybrid search
    if _vec_available(db):
        try:
            from embedder import embed_text
            query_embedding = embed_text(query)
            vec_distances = _vec_search_chunks(db, query_embedding, project, file_filter, limit)
            if vec_distances:
                fts_results = _hybrid_rank(fts_results, vec_distances)
        except Exception:
            pass

    return fts_results[:limit]
