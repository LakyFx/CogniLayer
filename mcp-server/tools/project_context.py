"""project_context — Return Project DNA and current context.

Includes lazy crash recovery and auto-identity detection
(moved from session_start for faster startup).
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

_log = logging.getLogger("cognilayer.tools.project_context")

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session
from i18n import t
from tools.identity_set import ALL_FIELDS as _IDENTITY_COLUMNS

COGNILAYER_HOME = Path.home() / ".cognilayer"
SESSIONS_DIR = COGNILAYER_HOME / "sessions"


def _build_emergency_bridge(db, session_id: str) -> str:
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


def _check_crash_recovery(db, project: str) -> str | None:
    """Detect and recover orphaned sessions (lazy — runs on first context request)."""
    cutoff = (datetime.now() - timedelta(seconds=120)).isoformat()
    orphans = db.execute("""
        SELECT s.id, s.start_time, s.bridge_content, s.claude_session_id,
               (SELECT COUNT(*) FROM changes WHERE session_id = s.id) as change_count,
               (SELECT GROUP_CONCAT(file_path, ', ')
                FROM (SELECT DISTINCT file_path FROM changes
                      WHERE session_id = s.id
                      ORDER BY timestamp DESC LIMIT 5)) as last_files
        FROM sessions s
        WHERE project = ? AND end_time IS NULL AND start_time < ?
        ORDER BY start_time DESC
    """, (project, cutoff)).fetchall()

    crash_info = None
    for orphan in orphans:
        session_id, start_time, bridge_content, claude_sid, changes, last_files = (
            orphan[0], orphan[1], orphan[2], orphan[3], orphan[4], orphan[5]
        )
        # Check if session is still alive via per-session file
        if claude_sid:
            session_file = SESSIONS_DIR / f"{claude_sid}.json"
            if session_file.exists():
                # Time-based override: if session is >6 hours old, treat file as stale
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    if start_dt.tzinfo:
                        start_dt = start_dt.replace(tzinfo=None)
                    age_hours = (datetime.now() - start_dt).total_seconds() / 3600
                    if age_hours < 6:
                        continue  # Session likely still alive, skip
                    # Stale file — clean it up and proceed with recovery
                    try:
                        session_file.unlink()
                    except OSError:
                        pass
                except (ValueError, TypeError):
                    continue  # Can't parse start_time, skip

        # Build emergency bridge if the crashed session has none
        if not bridge_content:
            bridge_content = _build_emergency_bridge(db, session_id)
            db.execute("UPDATE sessions SET bridge_content = ? WHERE id = ?",
                       (bridge_content, session_id))
        # Close the orphan session
        db.execute("""
            UPDATE sessions SET end_time = start_time,
                summary = ?
            WHERE id = ?
        """, (t("crash.session_summary"), session_id))
        # Report the most recent crash only
        if crash_info is None:
            crash_info = t("crash.recovery",
                           start_time=start_time,
                           changes=changes,
                           last_files=last_files or t("crash.no_files"))

    if crash_info:
        db.commit()
    return crash_info


def _auto_detect_identity(db, project: str, project_path: Path):
    """Auto-detect tech stack from project files (lazy — runs once per project)."""
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
        except Exception as e:
            _log.debug("Auto-detect: package.json parse failed for %s: %s", project, e)

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
        except Exception as e:
            _log.debug("Auto-detect: pyproject.toml parse failed for %s: %s", project, e)

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
        except Exception as e:
            _log.debug("Auto-detect: .git/config parse failed for %s: %s", project, e)

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
            if k not in _IDENTITY_COLUMNS:
                continue  # Skip unknown columns — safety whitelist
            columns.append(k)
            values.append(v)
        placeholders = ", ".join(["?"] * len(columns))
        db.execute(
            f"INSERT OR IGNORE INTO project_identity ({', '.join(columns)}) VALUES ({placeholders})",
            values
        )
        db.commit()


def project_context() -> str:
    """Return Project DNA, last bridge, and stats for current project."""
    session = get_active_session()
    project = session.get("project", "")
    project_path_str = session.get("project_path", "")

    if not project:
        return t("project_context.no_project")

    db = open_db()
    try:
        # Lazy crash recovery (moved from session_start for faster startup)
        crash_info = _check_crash_recovery(db, project)

        # Lazy auto-detect identity (moved from session_start for faster startup)
        if project_path_str:
            _auto_detect_identity(db, project, Path(project_path_str))

        # Get project DNA
        proj = db.execute(
            "SELECT dna_content, created, last_session FROM projects WHERE name = ?",
            (project,)
        ).fetchone()

        if not proj:
            return t("project_context.not_registered", project=project)

        dna = proj[0] or t("project_context.dna_placeholder", project=project)

        # Get latest bridge from last completed session (unified filter across all components)
        bridge_row = db.execute("""
            SELECT bridge_content, start_time, end_time FROM sessions
            WHERE project = ? AND end_time IS NOT NULL AND bridge_content IS NOT NULL
            ORDER BY start_time DESC LIMIT 1
        """, (project,)).fetchone()

        bridge = ""
        if bridge_row and bridge_row[0]:
            bridge = f"\n\n## Last Session Bridge\n{bridge_row[0]}"

        # Stats
        facts_count = db.execute(
            "SELECT COUNT(*) FROM facts WHERE project = ?", (project,)
        ).fetchone()[0]

        hot_count = db.execute(
            "SELECT COUNT(*) FROM facts WHERE project = ? AND heat_score >= 0.8",
            (project,)
        ).fetchone()[0]

        chunks_count = db.execute(
            "SELECT COUNT(*) FROM file_chunks WHERE project = ?", (project,)
        ).fetchone()[0]

        sessions_count = db.execute(
            "SELECT COUNT(*) FROM sessions WHERE project = ?", (project,)
        ).fetchone()[0]

        changes_count = db.execute(
            "SELECT COUNT(*) FROM changes WHERE project = ?", (project,)
        ).fetchone()[0]

        # V3: Memory Health
        warm_count = db.execute(
            "SELECT COUNT(*) FROM facts WHERE project = ? AND heat_score >= 0.3 AND heat_score < 0.8",
            (project,)
        ).fetchone()[0]
        cold_count = facts_count - hot_count - warm_count

        most_retrieved = None
        never_retrieved = 0
        avg_retrievals = 0.0
        try:
            row = db.execute(
                "SELECT content, retrieval_count FROM facts WHERE project = ? ORDER BY retrieval_count DESC LIMIT 1",
                (project,)
            ).fetchone()
            if row and row[1]:
                most_retrieved = (row[0][:50], row[1])
            never_retrieved = db.execute(
                "SELECT COUNT(*) FROM facts WHERE project = ? AND (retrieval_count IS NULL OR retrieval_count = 0)",
                (project,)
            ).fetchone()[0]
            avg_row = db.execute(
                "SELECT AVG(COALESCE(retrieval_count, 0)) FROM facts WHERE project = ?",
                (project,)
            ).fetchone()
            avg_retrievals = avg_row[0] or 0.0
        except Exception:
            pass  # retrieval_count column might not exist yet

        # V3: Knowledge Gaps
        knowledge_gaps = []
        try:
            gap_rows = db.execute("""
                SELECT query, times_seen, last_seen FROM knowledge_gaps
                WHERE project = ? AND resolved = 0
                ORDER BY times_seen DESC LIMIT 5
            """, (project,)).fetchall()
            knowledge_gaps = [(r[0], r[1], r[2]) for r in gap_rows]
        except Exception:
            pass  # knowledge_gaps table might not exist yet

        # V3 Tier 2: Recent Episodes
        episodes = []
        try:
            ep_rows = db.execute("""
                SELECT episode_title, outcome, start_time FROM sessions
                WHERE project = ? AND episode_title IS NOT NULL
                ORDER BY start_time DESC LIMIT 5
            """, (project,)).fetchall()
            episodes = [(r[0], r[1], r[2]) for r in ep_rows]
        except Exception:
            pass  # episode columns might not exist yet

        # Auto-consolidation: run if >24h since last run and project has enough facts
        try:
            from tools.consolidate import should_auto_consolidate, consolidate as _consolidate
            if should_auto_consolidate(db, project):
                _consolidate(project)
        except Exception:
            pass  # Consolidation failure must not break project_context

        # V3 Tier 2: Memory Organization
        cluster_count = 0
        tier_counts = {"active": 0, "reference": 0, "archive": 0}
        contradiction_count = 0
        try:
            cluster_count = db.execute(
                "SELECT COUNT(*) FROM fact_clusters WHERE project = ?", (project,)
            ).fetchone()[0]

            for tier in ("active", "reference", "archive"):
                tier_counts[tier] = db.execute(
                    "SELECT COUNT(*) FROM facts WHERE project = ? AND knowledge_tier = ?",
                    (project, tier)
                ).fetchone()[0]

            contradiction_count = db.execute(
                "SELECT COUNT(*) FROM contradictions WHERE project = ? AND resolved = 0",
                (project,)
            ).fetchone()[0]
        except Exception:
            pass  # Tier 2 tables might not exist yet
    finally:
        db.close()

    stats = t("project_context.stats",
              facts_count=facts_count, hot_count=hot_count,
              chunks_count=chunks_count, sessions_count=sessions_count,
              changes_count=changes_count)

    # Memory Health section
    health = t("project_context.health_header")
    health += t("project_context.health_stats",
                total=facts_count, hot=hot_count, warm=warm_count, cold=cold_count)
    if most_retrieved:
        health += "\n" + t("project_context.most_retrieved",
                           content=most_retrieved[0], count=most_retrieved[1])
    health += "\n" + t("project_context.never_retrieved", count=never_retrieved)
    health += "\n" + t("project_context.avg_retrievals", avg=avg_retrievals)

    # Knowledge Gaps section
    gaps = ""
    if knowledge_gaps:
        gaps = "\n" + t("project_context.gaps_header")
        for query, times, last_seen in knowledge_gaps:
            gaps += "\n" + t("project_context.gaps_item",
                             query=query, times=times)
    elif facts_count > 0:
        gaps = "\n" + t("project_context.no_gaps")

    # Episodes section
    ep_section = ""
    if episodes:
        ep_section = "\n" + t("project_context.episodes_header")
        for title, outcome, start_time in episodes:
            ep_section += "\n" + t("project_context.episodes_item",
                                    outcome=outcome or "unknown",
                                    title=title,
                                    date=start_time[:10] if start_time else "?")

    # Organization section
    org_section = ""
    if cluster_count > 0 or any(v > 0 for v in tier_counts.values()):
        org_section = "\n" + t("project_context.org_header")
        org_section += "\n" + t("project_context.org_stats",
                                 clusters=cluster_count,
                                 active=tier_counts["active"],
                                 reference=tier_counts["reference"],
                                 archive=tier_counts["archive"])
        if contradiction_count > 0:
            org_section += "\n" + t("project_context.org_contradictions",
                                     count=contradiction_count)

    # Include crash recovery info if detected
    crash_section = ""
    if crash_info:
        crash_section = f"\n\n{crash_info}"

    return f"{dna}{bridge}\n{stats}\n{health}{gaps}{ep_section}{org_section}{crash_section}"
