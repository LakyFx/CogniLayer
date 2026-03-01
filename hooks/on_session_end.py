"""CogniLayer SessionEnd hook — runs when Claude Code session ends."""

import json
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"
ACTIVE_SESSION_FILE = COGNILAYER_HOME / "active_session.json"
LOG_PATH = COGNILAYER_HOME / "logs" / "cognilayer.log"

# Import i18n
sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))
try:
    from i18n import t
except ImportError:
    def t(key, **kwargs):
        return key


def open_db():
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.row_factory = sqlite3.Row
    return db


def read_active_session():
    if ACTIVE_SESSION_FILE.exists():
        data = json.loads(ACTIVE_SESSION_FILE.read_text(encoding="utf-8"))
        return data.get("session_id", ""), data.get("project", "")
    return "", ""


def build_emergency_bridge(db, session_id: str) -> str:
    changed_files = db.execute("""
        SELECT DISTINCT file_path, action FROM changes
        WHERE session_id = ? ORDER BY timestamp
    """, (session_id,)).fetchall()

    facts = db.execute("""
        SELECT type, substr(content, 1, 80) FROM facts
        WHERE session_id = ? ORDER BY timestamp
    """, (session_id,)).fetchall()

    lines = [t("session_end.emergency_header")]

    if changed_files:
        file_list = ", ".join(f"{f[0]} ({f[1]})" for f in changed_files[:10])
        lines.append(f"Files: {file_list}")
        if len(changed_files) > 10:
            lines.append(t("session_end.and_more", count=len(changed_files) - 10))

    if facts:
        facts_summary = "; ".join(f"[{f[0]}] {f[1]}" for f in facts[:5])
        lines.append(f"Facts: {facts_summary}")

    if not changed_files and not facts:
        lines.append(t("session_end.no_changes"))

    return "\n".join(lines)


def log_session_end(project: str, session_id: str, changes: int, facts: int):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} SessionEnd project={project} "
                    f"session={session_id[:8]} changes={changes} facts={facts}\n")
    except Exception:
        pass


def main():
    if not DB_PATH.exists():
        return

    session_id, project_name = read_active_session()
    if not session_id:
        return

    db = open_db()
    try:
        now = datetime.now().isoformat()
        db.execute("UPDATE sessions SET end_time = ? WHERE id = ?", (now, session_id))

        changes_count = db.execute(
            "SELECT COUNT(*) FROM changes WHERE session_id = ?", (session_id,)
        ).fetchone()[0]

        facts_count = db.execute(
            "SELECT COUNT(*) FROM facts WHERE session_id = ?", (session_id,)
        ).fetchone()[0]

        db.execute("""
            UPDATE sessions SET changes_count = ?, facts_count = ? WHERE id = ?
        """, (changes_count, facts_count, session_id))

        row = db.execute(
            "SELECT bridge_content FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        existing_bridge = row[0] if row else None

        if not existing_bridge:
            emergency_bridge = build_emergency_bridge(db, session_id)
            db.execute("UPDATE sessions SET bridge_content = ? WHERE id = ?",
                       (emergency_bridge, session_id))

        log_session_end(project_name, session_id, changes_count, facts_count)

        db.commit()
    except Exception as e:
        sys.stderr.write(f"CogniLayer SessionEnd error: {e}\n")
    finally:
        db.close()

    # Cleanup active session file
    try:
        ACTIVE_SESSION_FILE.unlink(missing_ok=True)
    except Exception:
        pass


if __name__ == "__main__":
    main()
