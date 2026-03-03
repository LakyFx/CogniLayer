"""MCP tool: code_context — 360-degree view of a symbol."""

import logging
import sqlite3

from db import open_db
from i18n import t
from utils import get_active_session

_log = logging.getLogger("cognilayer.tools.code_context")


def code_context(symbol: str, project_name: str | None = None) -> str:
    """Get full context for a symbol: definition, callers, callees, references.

    Args:
        symbol: Symbol name or qualified name to look up
        project_name: Optional project override
    """
    db = None
    try:
        session = get_active_session()
        project = project_name or session.get("project")
        path = session.get("project_path")

        if not project:
            return t("code.no_project")

        db = open_db()

        # Auto-index check
        if not _has_index(db, project):
            return t("code.not_indexed", project=project)

        # Reindex dirty files first
        _reindex_dirty(db, project, path)

        # Find the symbol
        sym = _find_symbol(db, project, symbol)
        if not sym:
            return t("code.symbol_not_found", symbol=symbol)

        sym_dict = dict(sym)
        sym_id = sym_dict["id"]

        lines = []

        # Header: symbol definition
        lines.append(t("code.context_header", symbol=sym_dict["qualified_name"]))
        lines.append(f"**Kind:** {sym_dict['kind']}")
        lines.append(f"**File:** `{sym_dict['file_path']}:{sym_dict['line_start']}`")
        if sym_dict.get("signature"):
            lines.append(f"**Signature:** `{sym_dict['signature']}`")
        if sym_dict.get("docstring"):
            doc = sym_dict["docstring"][:300]
            lines.append(f"**Docstring:** {doc}")
        lines.append("")

        # Incoming references (who calls/references this symbol)
        incoming = db.execute("""
            SELECT r.kind, r.line, r.confidence,
                   s.qualified_name as from_name, s.kind as from_kind,
                   f.file_path
            FROM code_references r
            JOIN code_files f ON f.id = r.file_id
            LEFT JOIN code_symbols s ON s.id = r.from_symbol_id
            WHERE r.to_symbol_id = ? AND r.project = ?
            ORDER BY r.kind, f.file_path
            LIMIT 50
        """, (sym_id, project)).fetchall()

        if incoming:
            lines.append(t("code.context_incoming", count=len(incoming)))
            for ref in incoming:
                r = dict(ref)
                from_name = r.get("from_name") or "(module level)"
                lines.append(
                    f"  - [{r['kind']}] `{from_name}` — "
                    f"`{r['file_path']}:{r['line']}`"
                )
        else:
            lines.append(t("code.context_no_incoming"))
        lines.append("")

        # Outgoing references (what this symbol calls/references)
        outgoing = db.execute("""
            SELECT r.kind, r.to_name, r.line, r.confidence,
                   ts.qualified_name as resolved_name, ts.kind as resolved_kind,
                   f.file_path as ref_file
            FROM code_references r
            LEFT JOIN code_symbols ts ON ts.id = r.to_symbol_id
            LEFT JOIN code_files f ON f.id = r.file_id
            WHERE r.from_symbol_id = ? AND r.project = ?
            ORDER BY r.kind, r.line
            LIMIT 50
        """, (sym_id, project)).fetchall()

        if outgoing:
            lines.append(t("code.context_outgoing", count=len(outgoing)))
            for ref in outgoing:
                r = dict(ref)
                target = r.get("resolved_name") or r["to_name"]
                resolved = "" if r.get("resolved_name") else " (unresolved)"
                lines.append(
                    f"  - [{r['kind']}] `{target}`{resolved} "
                    f"— L{r['line']}"
                )
        else:
            lines.append(t("code.context_no_outgoing"))

        # Children (methods of a class, etc.)
        children = db.execute("""
            SELECT s.name, s.kind, s.signature, s.line_start
            FROM code_symbols s
            WHERE s.parent_id = ? AND s.project = ?
            ORDER BY s.line_start
        """, (sym_id, project)).fetchall()

        if children:
            lines.append("")
            lines.append(t("code.context_children", count=len(children)))
            for child in children:
                c = dict(child)
                sig = f" — `{c['signature']}`" if c.get("signature") else ""
                lines.append(f"  - {c['kind']} **{c['name']}** L{c['line_start']}{sig}")

        return "\n".join(lines)

    except sqlite3.OperationalError as e:
        if "locked" in str(e) or "busy" in str(e):
            return t("code.db_busy")
        return t("code.db_error", error=str(e))
    except Exception as e:
        _log.error("code_context failed: %s", e, exc_info=True)
        return t("code.generic_error", error=str(e))
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


def _find_symbol(db, project, symbol):
    """Find a symbol by name or qualified_name."""
    # Try exact qualified_name first
    row = db.execute("""
        SELECT s.*, f.file_path
        FROM code_symbols s
        JOIN code_files f ON f.id = s.file_id
        WHERE s.project = ? AND s.qualified_name = ?
    """, (project, symbol)).fetchone()

    if row:
        return row

    # Try exact name
    row = db.execute("""
        SELECT s.*, f.file_path
        FROM code_symbols s
        JOIN code_files f ON f.id = s.file_id
        WHERE s.project = ? AND s.name = ?
        ORDER BY s.exported DESC, s.line_start
        LIMIT 1
    """, (project, symbol)).fetchone()

    if row:
        return row

    # Try LIKE match
    row = db.execute("""
        SELECT s.*, f.file_path
        FROM code_symbols s
        JOIN code_files f ON f.id = s.file_id
        WHERE s.project = ? AND (s.name LIKE ? OR s.qualified_name LIKE ?)
        ORDER BY s.exported DESC, s.line_start
        LIMIT 1
    """, (project, f"%{symbol}%", f"%{symbol}%")).fetchone()

    return row


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


def _reindex_dirty(db, project, path):
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
        _log.warning("Dirty reindex in code_context failed: %s", e)
