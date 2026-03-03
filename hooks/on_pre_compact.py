"""CogniLayer PreCompact hook — saves comprehensive bridge before context compaction.

Fires BEFORE Claude Code compacts context. This is our last chance to save
session state that would otherwise be lost during compaction.

Must be fast (<200ms). Comprehensive bridge is built from all session data.
"""

import json
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"
SESSIONS_DIR = COGNILAYER_HOME / "sessions"
ACTIVE_SESSION_FILE = COGNILAYER_HOME / "active_session.json"
LOG_PATH = COGNILAYER_HOME / "logs" / "cognilayer.log"

sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))
try:
    from i18n import t
except ImportError:
    def t(key, **kwargs):
        return key


def open_db():
    from db import open_db_fast
    return open_db_fast()


def _find_session(claude_sid: str):
    """Find CogniLayer session_id and project from claude_session_id."""
    session_id = ""
    project_name = ""

    if claude_sid:
        session_file = SESSIONS_DIR / f"{claude_sid}.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                session_id = data.get("session_id", "")
                project_name = data.get("project", "")
            except Exception:
                pass

    if not session_id:
        try:
            data = json.loads(ACTIVE_SESSION_FILE.read_text(encoding="utf-8"))
            session_id = data.get("session_id", "")
            project_name = data.get("project", "")
        except Exception:
            pass

    return session_id, project_name


def _build_comprehensive_bridge(db, session_id: str) -> str:
    """Build a comprehensive bridge from ALL session data.

    This is the most complete bridge we can build — includes all changes,
    all facts, and any existing manual bridge content.
    """
    parts = ["[pre-compact bridge — saved before context compaction]"]

    # 1. All file changes
    changes = db.execute("""
        SELECT DISTINCT file_path, action FROM changes
        WHERE session_id = ? ORDER BY timestamp
    """, (session_id,)).fetchall()

    if changes:
        parts.append(f"Files ({len(changes)}):")
        for c in changes[:20]:
            parts.append(f"  {c[0]} ({c[1]})")
        if len(changes) > 20:
            parts.append(f"  ... +{len(changes) - 20} more")

    # 2. All facts from this session
    facts = db.execute("""
        SELECT type, content FROM facts
        WHERE session_id = ? ORDER BY timestamp
    """, (session_id,)).fetchall()

    if facts:
        parts.append(f"Facts ({len(facts)}):")
        for f in facts[:15]:
            content_preview = f[1][:120] if f[1] else ""
            parts.append(f"  [{f[0]}] {content_preview}")
        if len(facts) > 15:
            parts.append(f"  ... +{len(facts) - 15} more")

    # 3. Preserve existing manual bridge if it was better quality
    existing = db.execute("""
        SELECT bridge_content FROM sessions WHERE id = ?
    """, (session_id,)).fetchone()

    if existing and existing[0]:
        bridge_text = existing[0]
        # Only include if it's a manual bridge (not auto-generated)
        if not bridge_text.startswith("[auto-bridge") and not bridge_text.startswith("[pre-compact"):
            parts.append("Manual bridge:")
            parts.append(bridge_text)

    if not changes and not facts:
        parts.append("(no changes or facts recorded in this session segment)")

    return "\n".join(parts)


def _log(message: str):
    """Append to log file."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} PreCompact: {message}\n")
    except Exception:
        pass


def main():
    if not DB_PATH.exists():
        return

    # Read hook input from stdin
    try:
        raw = sys.stdin.buffer.read()
        hook_input = json.loads(raw.decode("utf-8")) if raw else {}
    except Exception:
        hook_input = {}

    claude_sid = hook_input.get("session_id", "")
    trigger = hook_input.get("trigger", "unknown")

    session_id, project = _find_session(claude_sid)
    if not session_id:
        _log(f"No session found for claude_sid={claude_sid[:8] if claude_sid else '?'}")
        return

    db = open_db()
    try:
        bridge = _build_comprehensive_bridge(db, session_id)

        # Always overwrite — pre-compact bridge is the highest priority save.
        # It captures everything right before context is lost.
        db.execute("""
            UPDATE sessions SET bridge_content = ? WHERE id = ?
        """, (bridge, session_id))
        db.commit()

        _log(f"OK session={session_id[:8]} project={project} trigger={trigger}")
    except Exception as e:
        _log(f"ERROR: {e}")
        sys.stderr.write(f"CogniLayer PreCompact error: {e}\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
