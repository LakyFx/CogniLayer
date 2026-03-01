"""Shared DB helper for CogniLayer. Used by MCP server, hooks, and scripts."""

import sqlite3
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"

_vec_loaded = False


def get_db_path() -> Path:
    return DB_PATH


def open_db(with_vec: bool = False) -> sqlite3.Connection:
    """Open DB with WAL mode + busy_timeout for multi-CLI safety.

    Args:
        with_vec: Load sqlite-vec extension. Only needed for vector search/write.
    """
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("PRAGMA wal_autocheckpoint=1000")
    db.row_factory = sqlite3.Row
    if with_vec:
        _load_sqlite_vec(db)
    return db


def ensure_vec(db: sqlite3.Connection) -> bool:
    """Ensure sqlite-vec is loaded on this connection. Returns True if available.

    Safe to call multiple times — checks first, loads only if needed.
    """
    try:
        db.execute("SELECT vec_version()")
        return True
    except Exception:
        return _load_sqlite_vec(db)


def _load_sqlite_vec(db: sqlite3.Connection) -> bool:
    """Load sqlite-vec extension if available. Returns True on success."""
    try:
        import sqlite_vec
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        return True
    except ImportError:
        return False  # sqlite-vec not installed
    except Exception:
        return False  # Extension load failed
