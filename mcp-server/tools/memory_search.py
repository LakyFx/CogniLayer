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


def _apply_heat_decay(db, project: str):
    """Apply time-based heat decay to all facts in the project.

    Decay formula: heat = heat * decay_factor
    - Facts accessed in last 24h: no decay
    - Facts accessed 1-7 days ago: decay 0.95
    - Facts accessed 7-30 days ago: decay 0.85
    - Facts accessed 30+ days ago: decay 0.70
    - Minimum heat: 0.05 (never fully forgotten)
    """
    now = datetime.now()
    thresholds = [
        (timedelta(days=1), 1.0),     # <24h: no decay
        (timedelta(days=7), 0.95),    # 1-7 days
        (timedelta(days=30), 0.85),   # 7-30 days
        (None, 0.70),                  # 30+ days
    ]

    rows = db.execute("""
        SELECT id, heat_score, last_accessed, timestamp
        FROM facts WHERE project = ? AND heat_score > 0.05
    """, (project,)).fetchall()

    for row in rows:
        fact_id = row[0]
        heat = row[1] or 1.0
        last_access = row[2] or row[3]  # fallback to creation time

        try:
            access_time = datetime.fromisoformat(last_access)
            # Strip timezone to avoid naive/aware mismatch
            if access_time.tzinfo is not None:
                access_time = access_time.replace(tzinfo=None)
        except (ValueError, TypeError):
            continue

        age = now - access_time
        decay_factor = 1.0
        for threshold, factor in thresholds:
            if threshold is None or age <= threshold:
                decay_factor = factor
                break

        if decay_factor < 1.0:
            new_heat = max(0.05, heat * decay_factor)
            if abs(new_heat - heat) > 0.001:
                db.execute(
                    "UPDATE facts SET heat_score = ? WHERE id = ?",
                    (new_heat, fact_id)
                )

    db.commit()


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

        # Boost accessed facts' heat score
        now = datetime.now().isoformat()
        for r in results:
            db.execute("""
                UPDATE facts SET heat_score = MIN(1.0, heat_score + 0.2),
                                 last_accessed = ?
                WHERE id = ?
            """, (now, r["id"]))
        db.commit()
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

        lines.append(line)

    return "\n\n".join(lines)
