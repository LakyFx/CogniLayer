"""Shared test fixtures for CogniLayer tests."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add mcp-server to path so tools can be imported
REPO_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_DIR / "mcp-server"))


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create a temporary database for testing.

    Patches db.DB_PATH and COGNILAYER_HOME so all tools use the temp DB.
    Returns the DB path.
    """
    db_path = tmp_path / "test_memory.db"
    home_path = tmp_path

    import db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    monkeypatch.setattr(db_module, "COGNILAYER_HOME", home_path)

    # Create schema
    from init_db import SCHEMA, FTS_SCHEMA
    conn = db_module.open_db()
    conn.executescript(SCHEMA)
    conn.commit()
    try:
        conn.executescript(FTS_SCHEMA)
        conn.commit()
    except Exception:
        pass  # FTS5 not available in this Python build
    conn.close()

    return db_path


@pytest.fixture
def active_session(tmp_path, monkeypatch, temp_db):
    """Create a fake active session for tests.

    Patches get_active_session() to return test session data.
    Requires temp_db fixture (uses its patched DB).
    """
    session_data = {
        "project": "test-project",
        "project_path": str(tmp_path),
        "session_id": "test-session-001",
    }

    # Patch get_active_session in utils AND in every tool module that imports it
    import utils
    monkeypatch.setattr(utils, "get_active_session", lambda: session_data)

    # Also patch in tool modules (they import get_active_session at module level)
    for mod_name in [
        "tools.memory_write", "tools.memory_search", "tools.memory_delete",
        "tools.file_search", "tools.session_bridge", "tools.decision_log",
        "tools.project_context", "tools.verify_identity", "tools.identity_set",
        "tools.memory_link", "tools.memory_chain",
    ]:
        try:
            mod = __import__(mod_name, fromlist=["get_active_session"])
            if hasattr(mod, "get_active_session"):
                monkeypatch.setattr(mod, "get_active_session", lambda: session_data)
        except (ImportError, AttributeError):
            pass

    # Register project and session in DB
    import db as db_module
    from datetime import datetime
    conn = db_module.open_db()
    conn.execute(
        "INSERT OR IGNORE INTO projects (name, path, created) VALUES (?, ?, ?)",
        ("test-project", str(tmp_path), datetime.now().isoformat()),
    )
    conn.execute(
        "INSERT OR IGNORE INTO sessions (id, project, start_time) VALUES (?, ?, ?)",
        ("test-session-001", "test-project", datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    # Also patch code tool modules
    for mod_name in [
        "tools.code_index", "tools.code_search",
        "tools.code_context", "tools.code_impact",
    ]:
        try:
            mod = __import__(mod_name, fromlist=["get_active_session"])
            if hasattr(mod, "get_active_session"):
                monkeypatch.setattr(mod, "get_active_session", lambda: session_data)
        except (ImportError, AttributeError):
            pass

    return session_data
