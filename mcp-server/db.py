"""Shared DB helper for CogniLayer. Used by MCP server, hooks, and scripts."""

import sqlite3
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"


def get_db_path() -> Path:
    return DB_PATH


def open_db() -> sqlite3.Connection:
    """Open DB with WAL mode + busy_timeout for multi-CLI safety."""
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("PRAGMA wal_autocheckpoint=1000")
    db.row_factory = sqlite3.Row
    return db
