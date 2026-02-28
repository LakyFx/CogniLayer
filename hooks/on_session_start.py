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
COGNILAYER_START = "# === COGNILAYER (auto-generated, nemaz) ==="
COGNILAYER_END = "# === END COGNILAYER ==="


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


def check_crash_recovery(db, project: str) -> str | None:
    orphan = db.execute("""
        SELECT s.id, s.start_time,
               (SELECT COUNT(*) FROM changes WHERE session_id = s.id) as change_count,
               (SELECT GROUP_CONCAT(file_path, ', ')
                FROM (SELECT DISTINCT file_path FROM changes
                      WHERE session_id = s.id
                      ORDER BY timestamp DESC LIMIT 5)) as last_files
        FROM sessions s
        WHERE project = ? AND end_time IS NULL
        ORDER BY start_time DESC LIMIT 1
    """, (project,)).fetchone()
    if orphan:
        session_id, start_time, changes, last_files = orphan[0], orphan[1], orphan[2], orphan[3]
        db.execute("""
            UPDATE sessions SET end_time = start_time,
                summary = '[CRASH] Session nebyla korektne ukoncena'
            WHERE id = ?
        """, (session_id,))
        return (
            f"## Crash Recovery\n"
            f"Posledni session ({start_time}) nebyla korektne ukoncena (pad/kill).\n"
            f"Zaznamenano {changes} zmen souboru pred padem.\n"
            f"Posledni zmenene soubory: {last_files or 'zadne'}\n"
            f"Bridge z predposledni session je platny (vyse).\n"
            f"Pro detail pouzij: memory_search(\"zmeny posledni session\")"
        )
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
                ver = deps["tailwindcss"].lstrip("^~")[0]
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
    if (project_path / "docker-compose.yml").exists():
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
    style_parts = []
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

    stack = ", ".join(stack_parts) or "neznamy"
    structure = ", ".join(structure_parts[:8]) or "?"
    deploy = "[NENASTAVENO]"

    # Check identity for deploy info
    identity = db.execute("SELECT deploy_ssh_alias, deploy_ssh_host, deploy_app_port, domain_primary FROM project_identity WHERE project = ?", (project,)).fetchone()
    if identity and identity[0]:
        deploy = f"ssh {identity[0]} ({identity[1]}), port {identity[2]}, {identity[3] or '?'}"

    dna = (
        f"## Project DNA: {project}\n"
        f"Stack: {stack}\n"
        f"Structure: /{', /'.join(structure_parts[:6])}\n" if structure_parts else f"## Project DNA: {project}\nStack: {stack}\n"
    )
    dna = (
        f"## Project DNA: {project}\n"
        f"Stack: {stack}\n"
        f"Style: [neznamy]\n"
        f"Structure: {structure}\n"
        f"Deploy: {deploy}\n"
        f"Active: [nova session]\n"
        f"Last: [prvni session]"
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
    lines.append("""## Pametove nastroje
Mas pristup k MCP serveru `cognilayer`:
- memory_search(query) — prohledej pamet semanticky
- memory_write(content) — zapamatuj si dulezitou informaci
- file_search(query) — hledej v projektovych souborech (PRD, docs...)
- decision_log(query) — najdi minula rozhodnuti

Kdyz si nejsi jisty kontextem nebo historii projektu,
VZDY nejdriv prohledej pamet pomoci memory_search.
Kdyz potrebujes info z PRD nebo docs, pouzij file_search
MISTO cteni celeho souboru.

## VERIFY-BEFORE-ACT — POVINNE
Kdyz memory_search vrati fakt oznaceny ⚠ STALE:
1. VZDY precti zdrojovy soubor a over ze fakt stale plati
2. Pokud se fakt zmenil → aktualizuj ho pres memory_write
3. NIKDY nedelej zmeny na zaklade STALE faktu bez overeni

## PROAKTIVNI PAMET — DULEZITE
Kdyz behem prace zjistis neco duleziteho, OKAMZITE to uloz:
- Chyba a oprava → memory_write(type="error_fix")
- Past/nebezpeci → memory_write(type="gotcha")
- Presny postup → memory_write(type="procedure")
- Jak komponenty komunikuji → memory_write(type="api_contract")
- Vykonovy problem → memory_write(type="performance")
- Dulezity prikaz → memory_write(type="command")
NECEKEJ na /harvest — session muze crashnout.

## RUNNING BRIDGE — KRITICKE
Po kazdem dokonceni ukolu AUTOMATICKY aktualizuj session bridge:
  session_bridge(action="save", content="Progress: ...; Open: ...")
Toto je Tier 1 — delej sam, neoznamuj, je to soucast prace.

## Safety pravidla — POVINNE
- Pred JAKYMKOLIV deployem, push, ssh, pm2, docker, db migraci:
  1. VZDY nejdriv zavolej verify_identity(action_type="...")
  2. Pokud vrati BLOCKED — ZASTAV a zeptej se uzivatele
  3. Pokud vrati VERIFIED — PRECTI uzivateli cilovy server a pozadej potvrzeni

## Git pravidla
- Commituj casto, male atomicke zmeny. Format: "[typ] co a proc"
- commit = Tier 1 (delej sam). push = Tier 3 (verify_identity).""")

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
        if COGNILAYER_START in content and COGNILAYER_END in content:
            # Replace existing block
            before = content[:content.index(COGNILAYER_START)]
            after = content[content.index(COGNILAYER_END) + len(COGNILAYER_END):]
            new_content = before + block + after
        else:
            # Append to end
            new_content = content.rstrip() + "\n\n" + block + "\n"
    else:
        new_content = block + "\n"

    claude_md_path.write_text(new_content, encoding="utf-8")


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
