"""CogniLayer SessionStart hook — runs when Claude Code starts.

FAST PATH ONLY — must complete in <200ms.
Heavy operations (crash recovery, identity detection, session cleanup)
are deferred to MCP server tools (project_context, session_end).
"""

import json
import sys
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"
ACTIVE_SESSION_FILE = COGNILAYER_HOME / "active_session.json"
SESSIONS_DIR = COGNILAYER_HOME / "sessions"

# Import i18n (must be after COGNILAYER_HOME is defined)
sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))
try:
    from i18n import t
except ImportError:
    def t(key, **kwargs):
        return key  # fallback if i18n not installed yet

COGNILAYER_START = f"# === COGNILAYER ({t('claude_md.do_not_delete')}) ==="
COGNILAYER_END = "# === END COGNILAYER ==="
# Also match old Czech marker for replacement
COGNILAYER_START_LEGACY = "# === COGNILAYER (auto-generated, nemaz) ==="


def read_claude_session_id() -> str:
    """Read claude_session_id from stdin (Claude Code hook protocol)."""
    try:
        raw = sys.stdin.buffer.read()
        if raw:
            data = json.loads(raw.decode("utf-8"))
            sid = data.get("session_id", "")
            if sid:
                return sid
    except Exception:
        pass
    return str(uuid.uuid4())


def open_db():
    from db import open_db_fast
    return open_db_fast()


def detect_project(path: Path) -> str:
    pkg = path / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if "name" in data:
                return data["name"]
        except Exception:
            pass
    pyproj = path / "pyproject.toml"
    if pyproj.exists():
        try:
            for line in pyproj.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("name"):
                    return line.split("=")[1].strip().strip('"')
        except Exception:
            pass
    return path.name


def register_project_if_new(db, name: str, path: Path):
    existing = db.execute("SELECT name FROM projects WHERE name = ?", (name,)).fetchone()
    if not existing:
        db.execute(
            "INSERT INTO projects (name, path, created, last_session) VALUES (?, ?, ?, ?)",
            (name, str(path).replace("\\", "/"), datetime.now().isoformat(), datetime.now().isoformat())
        )
    else:
        db.execute("UPDATE projects SET last_session = ? WHERE name = ?",
                   (datetime.now().isoformat(), name))


def get_or_generate_dna(db, project: str, project_path: Path) -> str:
    """Get existing DNA or generate deterministic one."""
    proj = db.execute("SELECT dna_content FROM projects WHERE name = ?", (project,)).fetchone()
    if proj and proj[0]:
        return proj[0]

    # Generate deterministic DNA from project files
    stack_parts = []
    structure_parts = []

    pkg = project_path / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "next" in deps:
                stack_parts.append(f"Next.js {deps['next'].lstrip('^~')}")
            if "react" in deps:
                stack_parts.append(f"React {deps['react'].lstrip('^~')}")
            if "typescript" in deps:
                stack_parts.append("TypeScript")
            if "tailwindcss" in deps:
                stack_parts.append("Tailwind CSS")
        except Exception:
            pass

    if list(project_path.glob("*.php"))[:1] and not stack_parts:
        stack_parts.append("PHP")

    # Structure from top-level dirs
    try:
        for d in sorted(project_path.iterdir()):
            if d.is_dir() and d.name not in {"node_modules", ".git", ".next", "__pycache__", "dist", "build", ".venv", "venv", ".claude"}:
                structure_parts.append(d.name)
    except Exception:
        pass

    stack = ", ".join(stack_parts) or t("dna.unknown_stack")
    structure = ", ".join(structure_parts[:8]) or "?"
    deploy = t("dna.deploy_not_set")

    # Check identity for deploy info
    identity = db.execute("SELECT deploy_ssh_alias, deploy_ssh_host, deploy_app_port, domain_primary FROM project_identity WHERE project = ?", (project,)).fetchone()
    if identity and identity[0]:
        deploy = f"ssh {identity[0]} ({identity[1]}), port {identity[2]}, {identity[3] or '?'}"

    dna = (
        f"## Project DNA: {project}\n"
        f"Stack: {stack}\n"
        f"Style: {t('dna.unknown_style')}\n"
        f"Structure: {structure}\n"
        f"Deploy: {deploy}\n"
        f"Active: {t('dna.new_session')}\n"
        f"Last: {t('dna.first_session')}"
    )

    db.execute("UPDATE projects SET dna_content = ?, dna_updated = ? WHERE name = ?",
               (dna, datetime.now().isoformat(), project))
    return dna


def get_latest_bridge(db, project: str) -> str | None:
    row = db.execute("""
        SELECT bridge_content FROM sessions
        WHERE project = ? AND end_time IS NOT NULL AND bridge_content IS NOT NULL
        ORDER BY start_time DESC LIMIT 1
    """, (project,)).fetchone()
    if row and row[0]:
        return row[0]
    return None


def create_session(db, project: str, claude_session_id: str | None = None) -> str:
    now = datetime.now().isoformat()

    # Close any previous open sessions with the same claude_session_id
    # (happens on context compacting — SessionStart fires again).
    # Preserve data: build emergency bridge if none exists.
    if claude_session_id:
        prev_sessions = db.execute("""
            SELECT id, bridge_content FROM sessions
            WHERE claude_session_id = ? AND end_time IS NULL
        """, (claude_session_id,)).fetchall()
        for prev in prev_sessions:
            prev_id, prev_bridge = prev[0], prev[1]
            if not prev_bridge:
                # Build emergency bridge from changes + facts of the old session
                changed = db.execute("""
                    SELECT DISTINCT file_path, action FROM changes
                    WHERE session_id = ? ORDER BY timestamp
                """, (prev_id,)).fetchall()
                facts = db.execute("""
                    SELECT type, substr(content, 1, 80) FROM facts
                    WHERE session_id = ? ORDER BY timestamp
                """, (prev_id,)).fetchall()
                parts = ["[auto-bridge from context compacting]"]
                if changed:
                    parts.append("Files: " + ", ".join(
                        f"{c[0]} ({c[1]})" for c in changed[:10]))
                if facts:
                    parts.append("Facts: " + "; ".join(
                        f"[{f[0]}] {f[1]}" for f in facts[:5]))
                if changed or facts:
                    prev_bridge = "\n".join(parts)
                    db.execute("UPDATE sessions SET bridge_content = ? WHERE id = ?",
                               (prev_bridge, prev_id))
            db.execute("""
                UPDATE sessions SET end_time = ?, summary = 'closed: context compacting'
                WHERE id = ?
            """, (now, prev_id))

    # Also close very old orphaned sessions for this project (>6 hours)
    cutoff_6h = (datetime.now() - __import__('datetime').timedelta(hours=6)).isoformat()
    old_orphans = db.execute("""
        SELECT id, bridge_content FROM sessions
        WHERE project = ? AND end_time IS NULL AND start_time < ?
    """, (project, cutoff_6h)).fetchall()
    for orphan in old_orphans:
        orphan_id, orphan_bridge = orphan[0], orphan[1]
        if not orphan_bridge:
            changed = db.execute("""
                SELECT DISTINCT file_path, action FROM changes
                WHERE session_id = ? ORDER BY timestamp
            """, (orphan_id,)).fetchall()
            if changed:
                orphan_bridge = "[auto-bridge from orphan cleanup]\nFiles: " + \
                    ", ".join(f"{c[0]} ({c[1]})" for c in changed[:10])
                db.execute("UPDATE sessions SET bridge_content = ? WHERE id = ?",
                           (orphan_bridge, orphan_id))
        db.execute("""
            UPDATE sessions SET end_time = ?, summary = 'closed: orphan >6h'
            WHERE id = ?
        """, (now, orphan_id))

    session_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO sessions (id, project, start_time, claude_session_id) VALUES (?, ?, ?, ?)",
        (session_id, project, now, claude_session_id)
    )
    return session_id


def write_session_file(session_id: str, project: str, project_path: str,
                       claude_session_id: str | None = None):
    """Write per-session file + legacy active_session.json for backwards compat."""
    data = {
        "session_id": session_id,
        "project": project,
        "project_path": str(project_path).replace("\\", "/"),
        "start_time": datetime.now().isoformat(),
        "claude_session_id": claude_session_id,
    }
    payload = json.dumps(data, indent=2)

    # Per-session file
    if claude_session_id:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        (SESSIONS_DIR / f"{claude_session_id}.json").write_text(payload, encoding="utf-8")

    # Legacy fallback (always write for backwards compat)
    ACTIVE_SESSION_FILE.write_text(payload, encoding="utf-8")


# Keep old name as alias for backwards compat (session_init.py imports it)
def write_active_session(session_id: str, project: str, project_path: str):
    write_session_file(session_id, project, project_path)


def get_cognilayer_block(dna: str, bridge: str | None) -> str:
    """Build the CLAUDE.md injection block."""
    lines = [COGNILAYER_START, ""]
    lines.append(t("claude_md.template"))

    lines.append("")
    lines.append(dna)

    if bridge:
        lines.append("")
        lines.append(f"## Last Session Bridge\n{bridge}")

    lines.append("")
    lines.append(COGNILAYER_END)
    return "\n".join(lines)


def _inject_once(claude_md_path: Path, dna: str, bridge: str | None):
    """Actual injection logic (no retry)."""
    block = get_cognilayer_block(dna, bridge)

    if claude_md_path.exists():
        content = claude_md_path.read_text(encoding="utf-8")
        # Match current or legacy start marker
        start_marker = None
        if COGNILAYER_START in content:
            start_marker = COGNILAYER_START
        elif COGNILAYER_START_LEGACY in content:
            start_marker = COGNILAYER_START_LEGACY

        if start_marker and COGNILAYER_END in content:
            # Replace existing block
            before = content[:content.index(start_marker)]
            after = content[content.index(COGNILAYER_END) + len(COGNILAYER_END):]
            new_content = before + block + after
        else:
            # Append to end
            new_content = content.rstrip() + "\n\n" + block + "\n"
    else:
        new_content = block + "\n"

    claude_md_path.write_text(new_content, encoding="utf-8", newline="\n")


def inject_cognilayer_block(claude_md_path: Path, dna: str, bridge: str | None):
    """Inject CogniLayer block into CLAUDE.md with retry for concurrent writes on Windows."""
    for attempt in range(3):
        try:
            _inject_once(claude_md_path, dna, bridge)
            return
        except (PermissionError, OSError):
            if attempt < 2:
                time.sleep(0.2 * (attempt + 1))
            else:
                raise


def main():
    if not DB_PATH.exists():
        # DB not initialized yet — skip
        return

    # Read claude_session_id from stdin (Claude Code hook protocol)
    claude_session_id = read_claude_session_id()

    project_path = Path.cwd()
    project_name = detect_project(project_path)

    db = open_db()
    try:
        register_project_if_new(db, project_name, project_path)
        # Heavy operations REMOVED from here — deferred to MCP tools:
        # - cleanup_old_sessions → on_session_end.py
        # - check_crash_recovery → project_context tool (lazy)
        # - auto_detect_identity → project_context tool (lazy)
        dna = get_or_generate_dna(db, project_name, project_path)
        bridge = get_latest_bridge(db, project_name)
        session_id = create_session(db, project_name, claude_session_id)

        # Commit DB changes BEFORE file I/O to release write lock early
        db.commit()
    except Exception as e:
        sys.stderr.write(f"CogniLayer SessionStart error: {e}\n")
    finally:
        db.close()

    # File I/O outside DB lock — safe for concurrent access
    try:
        write_session_file(session_id, project_name, project_path, claude_session_id)
        inject_cognilayer_block(project_path / "CLAUDE.md", dna, bridge)
    except Exception as e:
        sys.stderr.write(f"CogniLayer SessionStart file write error: {e}\n")

    # Cleanup stale session files (best-effort, after our own session file is written)
    try:
        _cleanup_stale_session_files()
    except Exception:
        pass


def _cleanup_stale_session_files():
    """Remove session files for sessions already closed in DB or orphaned >24h."""
    if not SESSIONS_DIR.exists():
        return

    db = open_db()
    try:
        now = time.time()
        for f in SESSIONS_DIR.iterdir():
            if not f.name.endswith(".json"):
                continue
            claude_sid = f.stem
            row = db.execute(
                "SELECT end_time FROM sessions WHERE claude_session_id = ? ORDER BY start_time DESC LIMIT 1",
                (claude_sid,)
            ).fetchone()

            if row and row[0]:
                # Session is closed in DB — safe to delete
                try:
                    f.unlink()
                except OSError:
                    pass
            elif row is None:
                # Not in DB at all — delete only if older than 24h
                try:
                    age_hours = (now - f.stat().st_mtime) / 3600
                    if age_hours > 24:
                        f.unlink()
                except OSError:
                    pass
            # else: row exists but end_time is NULL — session is alive, leave it
    finally:
        db.close()


if __name__ == "__main__":
    main()
