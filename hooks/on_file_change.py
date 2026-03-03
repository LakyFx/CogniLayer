"""CogniLayer PostToolUse hook — logs file changes + context monitoring.

Must be <100ms for the core path. Context monitoring adds ~10ms (best-effort).
"""

import json
import logging
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

_log = logging.getLogger("cognilayer.hooks.on_file_change")

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"
ACTIVE_SESSION_FILE = COGNILAYER_HOME / "active_session.json"
SESSIONS_DIR = COGNILAYER_HOME / "sessions"
LOG_PATH = COGNILAYER_HOME / "logs" / "cognilayer.log"

# Context thresholds for proactive bridge saves
CONTEXT_WARN_THRESHOLD = 75   # Save proactive bridge at 75%
CONTEXT_CRITICAL_THRESHOLD = 85  # Save comprehensive bridge at 85%
# File to track last saved threshold per session (avoid repeated saves)
CONTEXT_STATE_DIR = COGNILAYER_HOME / "context_state"


def _get_context_percentage(transcript_path: str) -> float | None:
    """Read context usage % from transcript JSONL. Fast: reads only last ~8KB.

    Returns percentage (0-100) or None if unavailable.
    """
    try:
        fpath = Path(transcript_path)
        if not fpath.exists():
            return None

        file_size = fpath.stat().st_size
        if file_size == 0:
            return None

        # Read last ~8KB — enough for the last few messages
        read_size = min(file_size, 8192)
        with open(fpath, "rb") as f:
            f.seek(max(0, file_size - read_size))
            tail = f.read().decode("utf-8", errors="replace")

        # Find the last assistant message with usage data (scan lines in reverse)
        lines = tail.strip().split("\n")
        for line in reversed(lines):
            if '"type":"assistant"' not in line and '"type": "assistant"' not in line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("type") != "assistant":
                    continue
                usage = obj.get("message", {}).get("usage", {})
                if not usage:
                    continue
                input_t = usage.get("input_tokens", 0) or 0
                cache_create = usage.get("cache_creation_input_tokens", 0) or 0
                cache_read = usage.get("cache_read_input_tokens", 0) or 0
                total = input_t + cache_create + cache_read
                if total > 0:
                    return (total / 200000) * 100
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    except Exception:
        pass
    return None


def _save_proactive_bridge(db, session_id: str, project: str, pct: float):
    """Save proactive bridge when context is getting full."""
    # Build comprehensive bridge (same as PreCompact)
    changes = db.execute("""
        SELECT DISTINCT file_path, action FROM changes
        WHERE session_id = ? ORDER BY timestamp
    """, (session_id,)).fetchall()

    facts = db.execute("""
        SELECT type, content FROM facts
        WHERE session_id = ? ORDER BY timestamp
    """, (session_id,)).fetchall()

    parts = [f"[proactive bridge @ {pct:.0f}% context — saved before compacting]"]

    if changes:
        parts.append(f"Files ({len(changes)}):")
        for c in changes[:20]:
            parts.append(f"  {c[0]} ({c[1]})")
        if len(changes) > 20:
            parts.append(f"  ... +{len(changes) - 20} more")

    if facts:
        parts.append(f"Facts ({len(facts)}):")
        for f in facts[:15]:
            preview = f[1][:120] if f[1] else ""
            parts.append(f"  [{f[0]}] {preview}")
        if len(facts) > 15:
            parts.append(f"  ... +{len(facts) - 15} more")

    # Preserve manual bridge content
    existing = db.execute(
        "SELECT bridge_content FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if existing and existing[0]:
        old = existing[0]
        if not old.startswith("[auto-bridge") and not old.startswith("[proactive") and not old.startswith("[pre-compact"):
            parts.append("Manual bridge:")
            parts.append(old)

    bridge = "\n".join(parts)

    # Overwrite — proactive bridge is better than auto-bridge snapshots
    db.execute("UPDATE sessions SET bridge_content = ? WHERE id = ?",
               (bridge, session_id))
    db.commit()


def _check_context_and_save(hook_input: dict, db, session_id: str, project: str):
    """Check context usage and save proactive bridge at thresholds.

    Uses a state file to avoid repeated saves at the same threshold.
    """
    transcript_path = hook_input.get("transcript_path", "")
    if not transcript_path:
        return

    pct = _get_context_percentage(transcript_path)
    if pct is None or pct < CONTEXT_WARN_THRESHOLD:
        return

    # Check if we already saved at this threshold level
    claude_sid = hook_input.get("session_id", "")
    state_file = CONTEXT_STATE_DIR / f"{claude_sid}.txt" if claude_sid else None

    last_threshold = 0
    if state_file and state_file.exists():
        try:
            last_threshold = int(state_file.read_text().strip())
        except (ValueError, OSError):
            pass

    # Determine current threshold level
    if pct >= CONTEXT_CRITICAL_THRESHOLD:
        current_level = CONTEXT_CRITICAL_THRESHOLD
    elif pct >= CONTEXT_WARN_THRESHOLD:
        current_level = CONTEXT_WARN_THRESHOLD
    else:
        return

    # Skip if we already saved at this level or higher
    if last_threshold >= current_level:
        return

    # Save proactive bridge
    _save_proactive_bridge(db, session_id, project, pct)

    # Record that we saved at this level
    if state_file:
        try:
            CONTEXT_STATE_DIR.mkdir(parents=True, exist_ok=True)
            state_file.write_text(str(current_level))
        except OSError:
            pass

    # Log it
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} ContextMonitor: "
                    f"saved proactive bridge at {pct:.1f}% "
                    f"session={session_id[:8]} project={project}\n")
    except Exception:
        pass


def main():
    if not DB_PATH.exists():
        return

    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.buffer.read().decode("utf-8"))
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

    # Extract claude_session_id from hook input and find CogniLayer session
    claude_sid = hook_input.get("session_id", "")
    session_id = ""
    project_name = ""
    project_path = ""

    # Try per-session file first
    if claude_sid:
        session_file = SESSIONS_DIR / f"{claude_sid}.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                session_id = data.get("session_id", "")
                project_name = data.get("project", "")
                project_path = data.get("project_path", "")
            except Exception:
                pass

    # Fallback to legacy active_session.json
    if not session_id:
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
    # Use consistent PRAGMAs (WAL, 30s timeout) to avoid silent data loss.
    db = None
    try:
        db = sqlite3.connect(str(DB_PATH))
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("""
            INSERT INTO changes (session_id, project, file_path, action, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, project_name, rel_path, action, datetime.now().isoformat()))

        # Mark file as dirty in code_files (for incremental code re-indexing).
        # Fire-and-forget: table may not exist, DB may be locked — that's OK.
        try:
            db.execute("""
                UPDATE code_files SET is_dirty = 1
                WHERE project = ? AND file_path = ?
            """, (project_name, rel_path))
        except sqlite3.OperationalError:
            pass  # code_files table may not exist yet

        db.commit()

        # Periodic bridge snapshot: every 10 changes, auto-save a lightweight bridge
        # from accumulated changes. This protects against data loss on context compacting
        # (which can happen any time without warning — there is no hook for it).
        try:
            change_count = db.execute("""
                SELECT COUNT(*) FROM changes WHERE session_id = ?
            """, (session_id,)).fetchone()[0]
            if change_count > 0 and change_count % 10 == 0:
                # Build snapshot bridge from changes
                recent = db.execute("""
                    SELECT DISTINCT file_path, action FROM changes
                    WHERE session_id = ? ORDER BY timestamp DESC
                """, (session_id,)).fetchall()
                if recent:
                    snapshot = "[auto-bridge snapshot @ {} changes]\nFiles: {}".format(
                        change_count,
                        ", ".join(f"{r[0]} ({r[1]})" for r in recent[:15])
                    )
                    # Only update if no manual bridge exists yet (don't overwrite better data)
                    db.execute("""
                        UPDATE sessions SET bridge_content = ?
                        WHERE id = ? AND bridge_content IS NULL
                    """, (snapshot, session_id))
                    db.commit()
        except Exception:
            pass  # Snapshot is best-effort, must not break the hook

        # Context monitoring: check if context is getting full and save proactively
        try:
            _check_context_and_save(hook_input, db, session_id, project_name)
        except Exception:
            pass  # Context monitoring is best-effort, must not break the hook

    except sqlite3.OperationalError as e:
        _log.warning("on_file_change DB write FAILED (data loss): %s", e)
        sys.stderr.write(f"CogniLayer PostToolUse: DB write failed: {e}\n")
    finally:
        if db:
            try:
                db.close()
            except sqlite3.OperationalError:
                pass


if __name__ == "__main__":
    main()
