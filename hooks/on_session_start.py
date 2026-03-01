"""CogniLayer SessionStart hook — runs when Claude Code starts."""

import json
import sys
import sqlite3
import time
import os
import uuid
from datetime import datetime
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"
ACTIVE_SESSION_FILE = COGNILAYER_HOME / "active_session.json"

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


def open_db():
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.row_factory = sqlite3.Row
    return db


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


def build_emergency_bridge(db, session_id: str) -> str:
    """Build emergency bridge from changes and facts of a crashed session."""
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


def check_crash_recovery(db, project: str) -> str | None:
    from datetime import timedelta
    # Only treat sessions as crashed if they started more than 60 seconds ago.
    # This avoids false positives from a concurrent session that is still running
    # (e.g. two Claude Code windows on the same project).
    cutoff = (datetime.now() - timedelta(seconds=60)).isoformat()
    orphan = db.execute("""
        SELECT s.id, s.start_time, s.bridge_content,
               (SELECT COUNT(*) FROM changes WHERE session_id = s.id) as change_count,
               (SELECT GROUP_CONCAT(file_path, ', ')
                FROM (SELECT DISTINCT file_path FROM changes
                      WHERE session_id = s.id
                      ORDER BY timestamp DESC LIMIT 5)) as last_files
        FROM sessions s
        WHERE project = ? AND end_time IS NULL AND start_time < ?
        ORDER BY start_time DESC LIMIT 1
    """, (project, cutoff)).fetchone()
    if orphan:
        session_id, start_time, bridge_content, changes, last_files = (
            orphan[0], orphan[1], orphan[2], orphan[3], orphan[4]
        )
        # Build emergency bridge if the crashed session has none
        if not bridge_content:
            bridge_content = build_emergency_bridge(db, session_id)
            db.execute("UPDATE sessions SET bridge_content = ? WHERE id = ?",
                       (bridge_content, session_id))
        # Close the orphan session
        db.execute("""
            UPDATE sessions SET end_time = start_time,
                summary = ?
            WHERE id = ?
        """, (t("crash.session_summary"), session_id))
        return t("crash.recovery",
                 start_time=start_time,
                 changes=changes,
                 last_files=last_files or t("crash.no_files"))
    return None


def auto_detect_identity(db, project: str, project_path: Path):
    """Auto-detect tech stack from project files. 0 tokens."""
    existing = db.execute("SELECT project FROM project_identity WHERE project = ?", (project,)).fetchone()
    if existing:
        return  # Already has identity card

    card = {}
    now = datetime.now().isoformat()

    # package.json detection
    pkg = project_path / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "next" in deps:
                ver = deps["next"].lstrip("^~").split(".")[0]
                card["framework"] = f"nextjs-{ver}"
                card["language"] = "typescript" if "typescript" in deps else "javascript"
            if "tailwindcss" in deps:
                ver = deps["tailwindcss"].lstrip("^~").split(".")[0]
                card["css_approach"] = f"tailwind-v{ver}"
            if "better-sqlite3" in deps:
                card["db_technology"] = "better-sqlite3"
                card["db_type"] = "sqlite"
            elif "@prisma/client" in deps:
                card["db_technology"] = "prisma"
            card["package_manager"] = (
                "bun" if (project_path / "bun.lockb").exists()
                else "pnpm" if (project_path / "pnpm-lock.yaml").exists()
                else "npm"
            )
        except Exception:
            pass

    # PHP detection
    if list(project_path.glob("*.php"))[:1] and "framework" not in card:
        card["framework"] = "php"
        card["language"] = "php"

    # Python detection
    if (project_path / "pyproject.toml").exists() and "framework" not in card:
        card["language"] = "python"
        try:
            content = (project_path / "pyproject.toml").read_text(encoding="utf-8")
            if "fastapi" in content.lower():
                card["framework"] = "fastapi"
            elif "django" in content.lower():
                card["framework"] = "django"
        except Exception:
            pass

    # Docker detection
    if (project_path / "docker-compose.yml").exists() or (project_path / "docker-compose.yaml").exists():
        card["containerization"] = "docker-compose"
        card["hosting_pattern"] = "docker"

    # Git remote detection
    git_config = project_path / ".git" / "config"
    if git_config.exists():
        try:
            for line in git_config.read_text(encoding="utf-8").splitlines():
                if "url = " in line and "github.com" in line:
                    card["github_repo_url"] = line.split("url = ")[1].strip()
                    break
        except Exception:
            pass

    # Category heuristic
    fw = card.get("framework", "")
    if card.get("containerization") and fw.startswith("nextjs"):
        card["project_category"] = "saas-app"
    elif fw == "php":
        card["project_category"] = "simple-website"
    elif fw.startswith("nextjs"):
        card["project_category"] = "agency-site"

    if card:
        columns = ["project", "created", "updated"]
        values = [project, now, now]
        for k, v in card.items():
            columns.append(k)
            values.append(v)
        placeholders = ", ".join(["?"] * len(columns))
        db.execute(
            f"INSERT INTO project_identity ({', '.join(columns)}) VALUES ({placeholders})",
            values
        )


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


def create_session(db, project: str) -> str:
    session_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO sessions (id, project, start_time) VALUES (?, ?, ?)",
        (session_id, project, datetime.now().isoformat())
    )
    return session_id


def write_active_session(session_id: str, project: str, project_path: str):
    data = {
        "session_id": session_id,
        "project": project,
        "project_path": str(project_path).replace("\\", "/"),
        "start_time": datetime.now().isoformat()
    }
    ACTIVE_SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_cognilayer_block(dna: str, bridge: str | None, crash_info: str | None) -> str:
    """Build the CLAUDE.md injection block."""
    lines = [COGNILAYER_START, ""]
    lines.append(t("claude_md.template"))

    lines.append("")
    lines.append(dna)

    if bridge:
        lines.append("")
        lines.append(f"## Last Session Bridge\n{bridge}")

    if crash_info:
        lines.append("")
        lines.append(crash_info)

    lines.append("")
    lines.append(COGNILAYER_END)
    return "\n".join(lines)


def inject_cognilayer_block(claude_md_path: Path, dna: str, bridge: str | None, crash_info: str | None):
    """Inject CogniLayer block into CLAUDE.md."""
    block = get_cognilayer_block(dna, bridge, crash_info)

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


def main():
    start = time.time()

    if not DB_PATH.exists():
        # DB not initialized yet — skip
        return

    project_path = Path.cwd()
    project_name = detect_project(project_path)

    db = open_db()
    try:
        register_project_if_new(db, project_name, project_path)
        crash_info = check_crash_recovery(db, project_name)
        auto_detect_identity(db, project_name, project_path)
        dna = get_or_generate_dna(db, project_name, project_path)
        bridge = get_latest_bridge(db, project_name)
        session_id = create_session(db, project_name)
        write_active_session(session_id, project_name, project_path)
        inject_cognilayer_block(project_path / "CLAUDE.md", dna, bridge, crash_info)

        # Re-index if time allows
        elapsed = time.time() - start
        if elapsed < 1.5:
            try:
                sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))
                from indexer.file_indexer import reindex_project
                reindex_project(db, project_name, project_path, time_budget=2.0 - elapsed)
            except Exception:
                pass  # Indexer not critical

        db.commit()
    except Exception as e:
        sys.stderr.write(f"CogniLayer SessionStart error: {e}\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
