"""CogniLayer PostToolUse hook — logs file changes. Must be <100ms."""

import json
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"
ACTIVE_SESSION_FILE = COGNILAYER_HOME / "active_session.json"


def main():
    if not DB_PATH.exists():
        return

    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "") or tool_input.get("notebook_path", "")

    if not file_path:
        return

    # Determine action
    if tool_name == "Write":
        action = "create"
    else:
        action = "edit"

    # Read active session
    try:
        data = json.loads(ACTIVE_SESSION_FILE.read_text(encoding="utf-8"))
        session_id = data.get("session_id", "")
        project_name = data.get("project", "")
        project_path = data.get("project_path", "")
    except Exception:
        return

    if not session_id or not project_name:
        return

    # Make relative path
    try:
        rel_path = str(Path(file_path).relative_to(project_path)).replace("\\", "/")
    except (ValueError, TypeError):
        rel_path = file_path.replace("\\", "/")

    # Insert into DB (one INSERT + COMMIT = <1ms)
    try:
        db = sqlite3.connect(str(DB_PATH))
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("""
            INSERT INTO changes (session_id, project, file_path, action, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, project_name, rel_path, action, datetime.now().isoformat()))
        db.commit()
    except Exception:
        pass
    finally:
        try:
            db.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
