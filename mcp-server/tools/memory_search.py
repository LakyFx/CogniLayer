"""memory_search — Hybrid search (FTS5 + vector) with staleness detection and heat decay."""

from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session
from search.fts_search import fts_search_facts
from i18n import t


def _check_staleness(fact: dict, project_path: str) -> str | None:
    if not fact.get("source_file") or not project_path:
        return None
    file_path = Path(project_path) / fact["source_file"]
    if not file_path.exists():
        return "DELETED"
    if fact.get("source_mtime"):
        current_mtime = file_path.stat().st_mtime
        if current_mtime > fact["source_mtime"]:
            return "STALE"
    return None


def _heat_label(score: float) -> str:
    """Classify heat score into hot/warm/cold."""
    if score >= 0.7:
        return "hot"
    elif score >= 0.3:
        return "warm"
    return "cold"


_last_decay_time = None

# Type-based half-lives in days — longer = decays slower
DECAY_HALF_LIVES = {
    "decision":     180,  # 6 months — decisions are long-lived
    "pattern":      120,  # 4 months
    "api_contract": 120,
    "procedure":    90,   # 3 months
    "client_rule":  90,
    "skill":        90,
    "fact":         60,   # 2 months — general knowledge
    "dependency":   60,
    "gotcha":       45,
    "error_fix":    45,
    "performance":  30,   # 1 month — can change fast
    "command":      30,
    "issue":        21,   # 3 weeks — should resolve quickly
    "task":         14,   # 2 weeks — most ephemeral
}


def _apply_heat_decay(db, project: str):
    """Apply type-based exponential heat decay to all facts in the project.

    Formula: heat = max(0.05, 0.5 ^ (age_days / half_life_days))
    Each fact type has a different half-life — decisions persist longer, tasks fade faster.
    Throttled to run at most once per hour.
    """
    global _last_decay_time
    now = datetime.now()
    if _last_decay_time and (now - _last_decay_time).total_seconds() < 3600:
        return
    _last_decay_time = now

    rows = db.execute("""
        SELECT id, type, heat_score, last_accessed, timestamp
        FROM facts WHERE project = ? AND heat_score > 0.05
    """, (project,)).fetchall()

    for row in rows:
        fact_id, fact_type, heat, last_access, created = row
        heat = heat or 1.0
        ref_time = last_access or created

        try:
            access_time = datetime.fromisoformat(ref_time)
            if access_time.tzinfo is not None:
                access_time = access_time.replace(tzinfo=None)
        except (ValueError, TypeError):
            continue

        age_days = (now - access_time).total_seconds() / 86400
        if age_days < 1:
            continue  # No decay for facts accessed within last day

        half_life = DECAY_HALF_LIVES.get(fact_type, 60)
        new_heat = max(0.05, 0.5 ** (age_days / half_life))

        if abs(new_heat - heat) > 0.001:
            db.execute(
                "UPDATE facts SET heat_score = ? WHERE id = ?",
                (new_heat, fact_id)
            )

    db.commit()


def _normalize_query(query: str) -> str:
    """Normalize query for gap deduplication."""
    return " ".join(query.lower().split())


def _log_knowledge_gap(db, query: str, project: str, search_type: str, results: list):
    """Log query as knowledge gap if no/weak results. Auto-resolve if good results."""
    if not project:
        return
    normalized = _normalize_query(query)
    now = datetime.now().isoformat()

    best_score = max((r.get("_hybrid_score", r.get("heat_score", 0)) for r in results), default=0) if results else 0

    if len(results) == 0 or best_score < 0.3:
        # Check if this gap already exists
        existing = db.execute("""
            SELECT id FROM knowledge_gaps
            WHERE project = ? AND query = ? AND resolved = 0
        """, (project, normalized)).fetchone()
        if existing:
            db.execute("""
                UPDATE knowledge_gaps SET times_seen = times_seen + 1,
                    last_seen = ?, hit_count = ?, best_score = ?
                WHERE id = ?
            """, (now, len(results), best_score if results else None, existing[0]))
        else:
            db.execute("""
                INSERT INTO knowledge_gaps
                    (project, query, search_type, hit_count, best_score, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project, normalized, search_type, len(results),
                  best_score if results else None, now, now))
    elif results:
        # Good results — auto-resolve matching gaps
        db.execute("""
            UPDATE knowledge_gaps SET resolved = 1
            WHERE project = ? AND query = ? AND resolved = 0
        """, (project, normalized))
    db.commit()


def _get_linked_facts(db, results: list) -> dict:
    """Get linked facts for each result. Returns {fact_id: [linked_fact_dicts]}."""
    linked_map = {}
    for r in results:
        try:
            rows = db.execute("""
                SELECT f.id, f.content FROM fact_links fl
                JOIN facts f ON (fl.target_id = f.id AND fl.source_id = ?)
                            OR (fl.source_id = f.id AND fl.target_id = ?)
                WHERE f.id != ?
                ORDER BY fl.score DESC LIMIT 3
            """, (r["id"], r["id"], r["id"])).fetchall()
            if rows:
                linked_map[r["id"]] = [{"id": row[0], "content": row[1]} for row in rows]
        except Exception:
            pass  # fact_links table might not exist yet
    return linked_map


def memory_search(query: str, scope: str = "project",
                  type: str = None, limit: int = 5) -> str:
    """Search CogniLayer memory using hybrid FTS5 + vector search."""
    session = get_active_session()
    project = session.get("project", "")
    project_path = session.get("project_path", "")

    limit = min(limit, 10)

    db = open_db()
    try:
        # Apply heat decay before searching
        if project:
            _apply_heat_decay(db, project)

        results = fts_search_facts(
            db, query, project=project, fact_type=type,
            limit=limit, scope=scope
        )

        # Boost accessed facts' heat + track retrieval
        now_str = datetime.now().isoformat()
        for r in results:
            db.execute("""
                UPDATE facts SET heat_score = MIN(1.0, heat_score + 0.2),
                                 last_accessed = ?,
                                 retrieval_count = COALESCE(retrieval_count, 0) + 1,
                                 last_retrieved = ?
                WHERE id = ?
            """, (now_str, now_str, r["id"]))
        db.commit()

        # Knowledge gap tracking
        _log_knowledge_gap(db, query, project, type, results)

        # Fetch linked facts for display
        linked_map = _get_linked_facts(db, results)
    finally:
        db.close()

    if not results:
        return t("memory_search.no_results", query=query)

    lines = [t("memory_search.header", count=len(results), query=query)]

    for i, r in enumerate(results, 1):
        staleness = _check_staleness(r, project_path)
        heat = r['heat_score'] if r['heat_score'] is not None else 1.0
        heat_lbl = _heat_label(heat)

        line = f"{i}. [{r['type']}] {r['content']}\n"
        line += f"   (projekt: {r['project']}, {r['timestamp'][:10]}, heat: {heat:.2f} [{heat_lbl}])"

        if r.get("_hybrid_score") is not None:
            line += f" hybrid: {r['_hybrid_score']:.2f}"

        if r['source_file']:
            line += f"\n   source: {r['source_file']}"

        if staleness == "STALE":
            line += "\n   ⚠ " + t("memory_search.stale", source_file=r['source_file'])
            line += "\n   " + t("memory_search.stale_hint", source_file=r['source_file'])
        elif staleness == "DELETED":
            line += "\n   ⚠ " + t("memory_search.deleted", source_file=r['source_file'])

        if r.get("project") != project and scope == "all":
            line += "\n   \U0001f517 " + t("memory_search.cross_project", project=r['project'])

        # Show linked facts
        if r["id"] in linked_map:
            for link in linked_map[r["id"]][:3]:
                line += f"\n   \u2194 " + t("memory_search.linked_fact",
                    id=link["id"][:8], preview=link["content"][:60])

        lines.append(line)

    return "\n\n".join(lines)
