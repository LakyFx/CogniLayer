"""memory_search — FTS5 search on facts, with staleness detection."""

import json
import os
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from search.fts_search import fts_search_facts


def _get_active_session():
    session_file = Path.home() / ".cognilayer" / "active_session.json"
    if session_file.exists():
        return json.loads(session_file.read_text(encoding="utf-8"))
    return {}


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


def memory_search(query: str, scope: str = "project",
                  type: str = None, limit: int = 5) -> str:
    """Search CogniLayer memory using FTS5."""
    session = _get_active_session()
    project = session.get("project", "")
    project_path = session.get("project_path", "")

    limit = min(limit, 10)

    db = open_db()
    try:
        results = fts_search_facts(
            db, query, project=project, fact_type=type,
            limit=limit, scope=scope
        )

        # Update heat_score for accessed facts
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
        return f"Zadne vysledky pro '{query}'. Pamet je prazdna nebo dotaz neodpovida zadnym faktum."

    lines = [f"## Nalezeno {len(results)} vysledku pro '{query}'\n"]

    for i, r in enumerate(results, 1):
        staleness = _check_staleness(r, project_path)
        heat = f"{r['heat_score']:.2f}" if r['heat_score'] else "1.00"

        line = f"{i}. [{r['type']}] {r['content']}\n"
        line += f"   (projekt: {r['project']}, {r['timestamp'][:10]}, heat: {heat})"

        if r['source_file']:
            line += f"\n   source: {r['source_file']}"

        if staleness == "STALE":
            line += f"\n   ⚠ STALE — source file {r['source_file']} se zmenil od zapisu tohoto faktu!"
            line += f"\n   → OVER pred pouzitim: Read {r['source_file']}"
        elif staleness == "DELETED":
            line += f"\n   ⚠ DELETED — source file {r['source_file']} byl smazan!"

        if r.get("project") != project and scope == "all":
            line += f"\n   🔗 CROSS-PROJECT — z projektu {r['project']}"

        lines.append(line)

    return "\n\n".join(lines)
