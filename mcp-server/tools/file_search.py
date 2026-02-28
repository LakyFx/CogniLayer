"""file_search — FTS5 search on indexed project file chunks."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from search.fts_search import fts_search_chunks


def _get_active_session():
    session_file = Path.home() / ".cognilayer" / "active_session.json"
    if session_file.exists():
        return json.loads(session_file.read_text(encoding="utf-8"))
    return {}


def file_search(query: str, scope: str = "project",
                file_filter: str = None, limit: int = 5) -> str:
    """Search indexed project files (PRD, docs, configs) via FTS5."""
    session = _get_active_session()
    project = session.get("project", "")

    if scope == "project":
        search_project = project
    elif scope != "all":
        search_project = scope
    else:
        search_project = None

    limit = min(limit, 10)

    db = open_db()
    try:
        results = fts_search_chunks(
            db, query, project=search_project,
            file_filter=file_filter, limit=limit
        )
    finally:
        db.close()

    if not results:
        return f"Zadne chunky nalezeny pro '{query}'. Soubory mozna nebyly zaindexovany."

    lines = [f"## Nalezeno {len(results)} chunku pro '{query}'\n"]

    for i, r in enumerate(results, 1):
        section = r["section_title"] or "(bez nadpisu)"
        line = f"{i}. [{r['file_path']}] sekce: {section}\n"
        # Truncate content to reasonable size
        content = r["content"]
        if len(content) > 500:
            content = content[:500] + "..."
        line += f"   {content}"
        lines.append(line)

    return "\n\n".join(lines)
