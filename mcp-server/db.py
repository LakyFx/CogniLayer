"""Shared DB helper for CogniLayer. Used by MCP server, hooks, and scripts."""

import sqlite3
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"

# Cache: None = not checked, True = available, False = not available
_vec_system_available = None


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

    Safe to call multiple times — uses module-level cache to avoid
    repeated ImportError exceptions when sqlite-vec is not installed.
    """
    global _vec_system_available

    # Fast path: already know it's not available on this system
    if _vec_system_available is False:
        return False

    # Check if already loaded on this connection
    try:
        db.execute("SELECT vec_version()")
        _vec_system_available = True
        return True
    except Exception:
        pass

    # Try loading
    return _load_sqlite_vec(db)


def _load_sqlite_vec(db: sqlite3.Connection) -> bool:
    """Load sqlite-vec extension if available. Returns True on success."""
    global _vec_system_available

    try:
        import sqlite_vec
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        _vec_system_available = True
        return True
    except ImportError:
        _vec_system_available = False  # Not installed — cache this
        return False
    except Exception:
        return False  # Extension load failed (connection-specific issue)
