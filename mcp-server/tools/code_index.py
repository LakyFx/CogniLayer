"""MCP tool: code_index — index project source code for code intelligence."""

import logging
import sqlite3
import time

from db import open_db
from i18n import t
from utils import get_active_session

_log = logging.getLogger("cognilayer.tools.code_index")


def code_index(project_path: str | None = None,
               full: bool = False,
               time_budget: float = 30.0) -> str:
    """Index project source code using tree-sitter.

    Extracts symbols (functions, classes, methods, interfaces) and references
    (calls, imports, inheritance) into SQLite for code intelligence queries.
    """
    db = None
    try:
        # Check tree-sitter availability
        try:
            import tree_sitter_language_pack  # noqa: F401
        except ImportError:
            return t("code.no_treesitter")

        session = get_active_session()
        project = session.get("project")
        path = project_path or session.get("project_path")

        if not project or not path:
            return t("code.no_project")

        db = open_db()

        # Ensure code tables exist
        _ensure_tables(db)

        from code.indexer import index_project

        incremental = not full

        stats = index_project(
            db=db,
            project=project,
            project_path=path,
            time_budget=time_budget,
            incremental=incremental,
        )

        # Format result
        lines = [t("code.index_header", project=project)]

        if stats["partial"]:
            lines.append(t("code.index_partial",
                           elapsed=f"{stats['elapsed']:.1f}",
                           files=stats["files_indexed"],
                           total=stats["files_total"]))
        else:
            lines.append(t("code.index_complete",
                           elapsed=f"{stats['elapsed']:.1f}"))

        lines.append(t("code.index_stats",
                        files_total=stats["files_total"],
                        files_indexed=stats["files_indexed"],
                        files_skipped=stats["files_skipped"],
                        symbols=stats["symbols"],
                        references=stats["references"],
                        resolved=stats["resolved"]))

        if stats["errors"]:
            lines.append(t("code.index_errors", count=len(stats["errors"])))
            for err in stats["errors"][:5]:
                lines.append(f"  - {err}")
            if len(stats["errors"]) > 5:
                lines.append(f"  ... and {len(stats['errors']) - 5} more")

        return "\n".join(lines)

    except sqlite3.OperationalError as e:
        if "locked" in str(e) or "busy" in str(e):
            return t("code.db_busy")
        return t("code.db_error", error=str(e))
    except Exception as e:
        _log.error("code_index failed: %s", e, exc_info=True)
        return t("code.generic_error", error=str(e))
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


def _ensure_tables(db: sqlite3.Connection) -> None:
    """Ensure code intelligence tables exist (idempotent)."""
    try:
        db.execute("SELECT 1 FROM code_files LIMIT 1")
    except sqlite3.OperationalError:
        # Tables don't exist — run migration
        from init_db import upgrade_schema
        upgrade_schema(db)
        # Also try to create FTS for code_symbols
        try:
            db.executescript("""
                CREATE VIRTUAL TABLE IF NOT EXISTS code_symbols_fts USING fts5(
                    name, qualified_name, signature, docstring,
                    content=code_symbols, content_rowid=rowid
                );
                CREATE TRIGGER IF NOT EXISTS code_symbols_ai AFTER INSERT ON code_symbols BEGIN
                    INSERT INTO code_symbols_fts(rowid, name, qualified_name, signature, docstring)
                    VALUES (new.rowid, new.name, new.qualified_name, new.signature, new.docstring);
                END;
                CREATE TRIGGER IF NOT EXISTS code_symbols_ad AFTER DELETE ON code_symbols BEGIN
                    INSERT INTO code_symbols_fts(code_symbols_fts, rowid, name, qualified_name, signature, docstring)
                    VALUES ('delete', old.rowid, old.name, old.qualified_name, old.signature, old.docstring);
                END;
                CREATE TRIGGER IF NOT EXISTS code_symbols_au AFTER UPDATE ON code_symbols BEGIN
                    INSERT INTO code_symbols_fts(code_symbols_fts, rowid, name, qualified_name, signature, docstring)
                    VALUES ('delete', old.rowid, old.name, old.qualified_name, old.signature, old.docstring);
                    INSERT INTO code_symbols_fts(rowid, name, qualified_name, signature, docstring)
                    VALUES (new.rowid, new.name, new.qualified_name, new.signature, new.docstring);
                END;
            """)
            db.commit()
        except Exception:
            pass  # FTS creation is optional
