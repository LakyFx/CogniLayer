"""Search helpers for CogniLayer — FTS5 + vector hybrid search (Phase 2)."""

import sqlite3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import ensure_vec


# --- Helpers ---

def _vec_tables_exist(db: sqlite3.Connection) -> bool:
    """Check if vector tables exist in the database."""
    try:
        db.execute("SELECT COUNT(*) FROM facts_vec")
        return True
    except Exception:
        return False


def _is_trivial_query(query: str) -> bool:
    """Check if query is too short/generic to benefit from vector search."""
    stripped = query.strip().strip('"').strip("'").strip("*")
    return len(stripped) < 3


def _escape_fts5(query: str) -> str:
    """Escape a query string for safe FTS5 MATCH use.

    Wraps in double quotes to treat as phrase (disables OR/AND/NOT/NEAR operators).
    """
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def _fact_row_to_dict(row) -> dict:
    """Convert a facts row to dict using column names."""
    return {
        "id": row["id"], "project": row["project"], "content": row["content"],
        "type": row["type"], "domain": row["domain"], "tags": row["tags"],
        "timestamp": row["timestamp"], "heat_score": row["heat_score"],
        "source_file": row["source_file"], "source_mtime": row["source_mtime"],
        "session_id": row["session_id"], "rowid": row["rowid"],
    }


def _chunk_row_to_dict(row) -> dict:
    """Convert a file_chunks row to dict using column names.

    Note: file_chunks.id IS the rowid (INTEGER PRIMARY KEY AUTOINCREMENT),
    so we alias it as row_id in SELECT to avoid duplicate column names.
    """
    return {
        "id": row["id"], "project": row["project"], "file_path": row["file_path"],
        "section_title": row["section_title"], "chunk_index": row["chunk_index"],
        "content": row["content"], "file_mtime": row["file_mtime"],
        "rowid": row["row_id"],
    }


# --- Vector search ---

def _vec_search_facts(db: sqlite3.Connection, query_embedding: bytes,
                      project: str = None, fact_type: str = None,
                      scope: str = "project", limit: int = 20) -> dict[int, float]:
    """Vector similarity search on facts. Returns {rowid: distance}."""
    rows = db.execute("""
        SELECT rowid, distance
        FROM facts_vec
        WHERE embedding MATCH ? AND k = ?
    """, (query_embedding, limit * 3)).fetchall()

    results = {}
    for row in rows:
        rowid, distance = row[0], row[1]
        fact = db.execute("SELECT project, type FROM facts WHERE rowid = ?", (rowid,)).fetchone()
        if not fact:
            continue
        if scope == "project" and project and fact["project"] != project:
            continue
        if scope != "all" and scope != "project" and fact["project"] != scope:
            continue
        if fact_type and fact["type"] != fact_type:
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
        if project and chunk["project"] != project:
            continue
        if file_filter:
            pattern = file_filter.replace("*", "")
            if pattern not in chunk["file_path"]:
                continue
        results[rowid] = distance

    return results


# --- Hybrid ranking ---

def _hybrid_rank(fts_results: list[dict], vec_distances: dict[int, float],
                 fts_weight: float = 0.4, vec_weight: float = 0.6) -> list[dict]:
    """Combine FTS5 and vector results with weighted ranking.

    FTS5 rank: position-based (1st result = 1.0, last = 0.0)
    Vector distance: converted to similarity (lower distance = higher score)

    Note: vec-only results must be pre-fetched and added to fts_results
    before calling this function.
    """
    fts_scores = {}
    vec_scores = {}

    # FTS5 scores: position-based
    for i, result in enumerate(fts_results):
        rowid = result["rowid"]
        fts_scores[rowid] = 1.0 - (i / max(len(fts_results), 1))

    # Vector scores: distance -> similarity (0-1)
    if vec_distances:
        max_dist = max(vec_distances.values()) if vec_distances else 1.0
        for rowid, distance in vec_distances.items():
            vec_scores[rowid] = 1.0 - (distance / max(max_dist * 1.2, 0.001))

    # Score all results (both FTS and vec-only are already in fts_results)
    for result in fts_results:
        rowid = result["rowid"]
        fts_s = fts_scores.get(rowid, 0.0)
        vec_s = vec_scores.get(rowid, 0.0)
        result["_hybrid_score"] = (fts_weight * fts_s) + (vec_weight * vec_s)

    fts_results.sort(key=lambda x: x["_hybrid_score"], reverse=True)
    return fts_results


# --- Facts search ---

_FACTS_COLUMNS = "id, project, content, type, domain, tags, timestamp, heat_score, source_file, source_mtime, session_id, rowid"


def fts_search_facts(db: sqlite3.Connection, query: str, project: str = None,
                     fact_type: str = None, limit: int = 5,
                     scope: str = "project") -> list[dict]:
    """Search facts using FTS5 + optional vector hybrid search."""
    conditions = []
    params = []

    if scope == "project" and project:
        conditions.append("project = ?")
        params.append(project)
    elif scope != "all" and scope != "project":
        conditions.append("project = ?")
        params.append(scope)

    if fact_type:
        conditions.append("type = ?")
        params.append(fact_type)

    # Wildcard/trivial query — return hottest/newest facts without FTS5
    if _is_trivial_query(query):
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT {_FACTS_COLUMNS}
            FROM facts
            {where}
            ORDER BY heat_score DESC, timestamp DESC
            LIMIT ?
        """
        rows = db.execute(sql, params + [limit]).fetchall()
        return [_fact_row_to_dict(row) for row in rows]

    # FTS5 search
    fts_query = _escape_fts5(query)
    fts_where = f"AND {' AND '.join(['f.' + c for c in conditions])}" if conditions else ""

    vec_ready = ensure_vec(db) and _vec_tables_exist(db)
    fetch_limit = limit * 3 if vec_ready else limit

    sql = f"""
        SELECT f.{_FACTS_COLUMNS.replace(', ', ', f.')}
        FROM facts f
        JOIN facts_fts fts ON f.rowid = fts.rowid
        WHERE facts_fts MATCH ? {fts_where}
        ORDER BY rank
        LIMIT ?
    """
    fts_params = [fts_query] + params + [fetch_limit]

    try:
        rows = db.execute(sql, fts_params).fetchall()
    except sqlite3.OperationalError:
        # Fallback: LIKE search if FTS5 query syntax fails
        where_parts = list(conditions) + ["content LIKE ?"]
        where = "WHERE " + " AND ".join(where_parts)
        sql = f"""
            SELECT {_FACTS_COLUMNS}
            FROM facts
            {where}
            ORDER BY heat_score DESC
            LIMIT ?
        """
        fts_params = params + [f"%{query}%"] + [fetch_limit]
        rows = db.execute(sql, fts_params).fetchall()

    fts_results = [_fact_row_to_dict(row) for row in rows]

    # Hybrid search: combine with vector results if available
    if vec_ready:
        try:
            from embedder import embed_text
            query_embedding = embed_text(query)
            vec_distances = _vec_search_facts(db, query_embedding, project, fact_type, scope, limit)
            if vec_distances:
                # Fetch vec-only results not already in FTS results
                fts_rowids = {r["rowid"] for r in fts_results}
                for rowid in vec_distances:
                    if rowid not in fts_rowids:
                        row = db.execute(f"""
                            SELECT {_FACTS_COLUMNS} FROM facts WHERE rowid = ?
                        """, (rowid,)).fetchone()
                        if row:
                            fts_results.append(_fact_row_to_dict(row))
                fts_results = _hybrid_rank(fts_results, vec_distances)
        except Exception as e:
            import sys
            print(f"[CogniLayer] Vector search failed, using FTS5 only: {e}", file=sys.stderr)

    return fts_results[:limit]


# --- Chunks search ---

_CHUNKS_COLUMNS = "id, project, file_path, section_title, chunk_index, content, file_mtime, id AS row_id"


def fts_search_chunks(db: sqlite3.Connection, query: str, project: str = None,
                      file_filter: str = None, limit: int = 5) -> list[dict]:
    """Search file chunks using FTS5 + optional vector hybrid search."""
    conditions = []
    params = []

    if project:
        conditions.append("project = ?")
        params.append(project)

    if file_filter:
        conditions.append("file_path LIKE ?")
        params.append(f"%{file_filter.replace('*', '%')}%")

    # Trivial query — return recent chunks
    if _is_trivial_query(query):
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT {_CHUNKS_COLUMNS}
            FROM file_chunks
            {where}
            ORDER BY id DESC
            LIMIT ?
        """
        rows = db.execute(sql, params + [limit]).fetchall()
        return [_chunk_row_to_dict(row) for row in rows]

    # FTS5 search
    fts_query = _escape_fts5(query)
    fts_where = f"AND {' AND '.join(['fc.' + c for c in conditions])}" if conditions else ""

    vec_ready = ensure_vec(db) and _vec_tables_exist(db)
    fetch_limit = limit * 3 if vec_ready else limit

    sql = f"""
        SELECT fc.{_CHUNKS_COLUMNS.replace(', ', ', fc.')}
        FROM file_chunks fc
        JOIN chunks_fts cfts ON fc.rowid = cfts.rowid
        WHERE chunks_fts MATCH ? {fts_where}
        ORDER BY rank
        LIMIT ?
    """
    fts_params = [fts_query] + params + [fetch_limit]

    try:
        rows = db.execute(sql, fts_params).fetchall()
    except sqlite3.OperationalError:
        # Fallback: LIKE search
        where_parts = list(conditions) + ["content LIKE ?"]
        where = "WHERE " + " AND ".join(where_parts)
        sql = f"""
            SELECT {_CHUNKS_COLUMNS}
            FROM file_chunks
            {where}
            ORDER BY id DESC
            LIMIT ?
        """
        fts_params = params + [f"%{query}%"] + [fetch_limit]
        rows = db.execute(sql, fts_params).fetchall()

    fts_results = [_chunk_row_to_dict(row) for row in rows]

    # Hybrid search
    if vec_ready:
        try:
            from embedder import embed_text
            query_embedding = embed_text(query)
            vec_distances = _vec_search_chunks(db, query_embedding, project, file_filter, limit)
            if vec_distances:
                # Fetch vec-only results
                fts_rowids = {r["rowid"] for r in fts_results}
                for rowid in vec_distances:
                    if rowid not in fts_rowids:
                        row = db.execute(f"""
                            SELECT {_CHUNKS_COLUMNS} FROM file_chunks WHERE rowid = ?
                        """, (rowid,)).fetchone()
                        if row:
                            fts_results.append(_chunk_row_to_dict(row))
                fts_results = _hybrid_rank(fts_results, vec_distances)
        except Exception as e:
            import sys
            print(f"[CogniLayer] Vector search failed, using FTS5 only: {e}", file=sys.stderr)

    return fts_results[:limit]
