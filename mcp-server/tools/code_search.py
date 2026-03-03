"""MCP tool: code_search — fulltext search for symbols (FTS5 + LIKE fallback)."""

import logging
import sqlite3

from db import open_db
from i18n import t
from utils import get_active_session

_log = logging.getLogger("cognilayer.tools.code_search")


def code_search(query: str, kind: str | None = None,
                limit: int = 20) -> str:
    """Search for code symbols by name or signature.

    Uses FTS5 when available, falls back to LIKE.
    Auto-indexes if project has no code index yet.
    """
    db = None
    try:
        session = get_active_session()
        project = session.get("project")
        path = session.get("project_path")

        if not project:
            return t("code.no_project")

        db = open_db()

        # Auto-index check + dirty reindex
        if not _has_index(db, project):
            return _auto_index_hint(project, path)

        _reindex_dirty_if_needed(db, project, path)

        limit = min(limit, 50)

        # Try FTS5 first
        results = _search_fts(db, project, query, kind, limit)

        if results is None:
            # FTS not available, use LIKE
            results = _search_like(db, project, query, kind, limit)

        if not results:
            return t("code.search_no_results", query=query)

        lines = [t("code.search_header", count=len(results), query=query)]

        for row in results:
            r = dict(row)
            kind_icon = _kind_icon(r["kind"])
            exported = " [exported]" if r["exported"] else ""
            line_info = f"L{r['line_start']}"
            if r["line_end"] != r["line_start"]:
                line_info += f"-{r['line_end']}"

            lines.append(
                f"- {kind_icon} **{r['qualified_name']}** ({r['kind']}) "
                f"— `{r['file_path']}:{r['line_start']}`{exported}"
            )
            if r.get("signature"):
                lines.append(f"  `{r['signature']}`")

        return "\n".join(lines)

    except sqlite3.OperationalError as e:
        if "locked" in str(e) or "busy" in str(e):
            return t("code.db_busy")
        return t("code.db_error", error=str(e))
    except Exception as e:
        _log.error("code_search failed: %s", e, exc_info=True)
        return t("code.generic_error", error=str(e))
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


def _search_fts(db, project, query, kind, limit):
    """Search using FTS5. Returns None if FTS not available."""
    try:
        sql = """
            SELECT s.*, f.file_path
            FROM code_symbols_fts fts
            JOIN code_symbols s ON s.rowid = fts.rowid
            JOIN code_files f ON f.id = s.file_id
            WHERE code_symbols_fts MATCH ? AND s.project = ?
        """
        params = [query, project]

        if kind:
            sql += " AND s.kind = ?"
            params.append(kind)

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        return db.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e) or "fts5" in str(e).lower():
            return None
        raise


def _search_like(db, project, query, kind, limit):
    """Fallback LIKE search."""
    pattern = f"%{query}%"
    sql = """
        SELECT s.*, f.file_path
        FROM code_symbols s
        JOIN code_files f ON f.id = s.file_id
        WHERE s.project = ? AND (s.name LIKE ? OR s.qualified_name LIKE ? OR s.signature LIKE ?)
    """
    params = [project, pattern, pattern, pattern]

    if kind:
        sql += " AND s.kind = ?"
        params.append(kind)

    sql += " ORDER BY s.name LIMIT ?"
    params.append(limit)

    return db.execute(sql, params).fetchall()


def _has_index(db, project):
    """Check if project has any indexed files."""
    try:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM code_files WHERE project = ?",
            (project,)
        ).fetchone()
        return row["cnt"] > 0
    except sqlite3.OperationalError:
        return False


def _auto_index_hint(project, path):
    """Return hint to run code_index first."""
    return t("code.not_indexed", project=project)


def _reindex_dirty_if_needed(db, project, path):
    """Reindex dirty files if any."""
    if not path:
        return
    try:
        dirty = db.execute(
            "SELECT COUNT(*) as cnt FROM code_files WHERE project = ? AND is_dirty = 1",
            (project,)
        ).fetchone()
        if dirty and dirty["cnt"] > 0:
            from code.indexer import reindex_dirty
            reindex_dirty(db, project, path, time_budget=5.0)
    except Exception as e:
        _log.warning("Dirty reindex failed: %s", e)


def _kind_icon(kind: str) -> str:
    """Map symbol kind to icon."""
    icons = {
        "function": "fn",
        "class": "cls",
        "method": "mtd",
        "interface": "ifc",
        "variable": "var",
        "type_alias": "type",
        "enum": "enum",
        "module": "mod",
    }
    return icons.get(kind, kind)
