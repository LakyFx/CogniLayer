"""Tests for session_bridge tool."""

from datetime import datetime


def test_save_and_load_bridge(temp_db, active_session):
    """Should save and load a session bridge."""
    from tools.session_bridge import session_bridge
    import db as db_module

    save_result = session_bridge(action="save", content="Progress: fixed auth bug; Open: write tests")
    assert "saved" in save_result.lower() or "ulozen" in save_result.lower()

    # Close the session so load can find it (load queries end_time IS NOT NULL)
    conn = db_module.open_db()
    conn.execute("UPDATE sessions SET end_time = ? WHERE id = ?",
                 (datetime.now().isoformat(), active_session["session_id"]))
    conn.commit()
    conn.close()

    load_result = session_bridge(action="load")
    assert "fixed auth bug" in load_result


def test_load_empty_bridge(temp_db, active_session):
    """Loading with no bridge should return appropriate message."""
    from tools.session_bridge import session_bridge

    result = session_bridge(action="load")
    assert "no" in result.lower() or "zadny" in result.lower()


def test_save_missing_content(temp_db, active_session):
    """Saving without content should return error."""
    from tools.session_bridge import session_bridge

    result = session_bridge(action="save", content=None)
    assert "missing" in result.lower() or "chybi" in result.lower()


def test_unknown_action(temp_db, active_session):
    """Unknown action should return error."""
    from tools.session_bridge import session_bridge

    result = session_bridge(action="invalid")
    assert "unknown" in result.lower() or "neznama" in result.lower()
