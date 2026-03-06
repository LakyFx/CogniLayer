"""file_index — MCP tool to index project documentation into file_chunks.

Indexes README, configs, PRDs, YAML, JSON, TOML, and other documentation files
into the file_chunks table so that file_search() returns results.

Without this, file_search returns empty because no other code path triggers
reindex_project() — the SessionStart hook skipped it for performance,
and session_init intentionally doesn't call it.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session
from indexer.file_indexer import reindex_project, scan_project_files
from i18n import t

logger = logging.getLogger("cognilayer.file_index")


def file_index(project_path: str | None = None, full: bool = False,
               time_budget: float = 30.0) -> str:
    """Index project documentation files into file_chunks for file_search."""
    session = get_active_session()
    project = session.get("project", "")
    path_str = project_path or session.get("project_path", "")

    if not path_str:
        return t("file_index.no_path")

    path = Path(path_str).resolve()
    if not path.exists() or not path.is_dir():
        return t("file_index.invalid_path", path=str(path))

    if not project:
        project = path.name

    logger.info("file_index: project=%s path=%s full=%s budget=%.1f",
                project, path, full, time_budget)

    db = open_db()
    try:
        # If full reindex, clear existing chunks first
        if full:
            db.execute("DELETE FROM file_chunks WHERE project = ?", (project,))
            logger.info("Full reindex: cleared existing chunks for %s", project)

        indexed_count = reindex_project(db, project, path, time_budget=time_budget)
        db.commit()

        # Get stats
        total_chunks = db.execute(
            "SELECT COUNT(*) FROM file_chunks WHERE project = ?", (project,)
        ).fetchone()[0]
        total_files = db.execute(
            "SELECT COUNT(DISTINCT file_path) FROM file_chunks WHERE project = ?",
            (project,)
        ).fetchone()[0]

    except Exception as e:
        logger.error("file_index failed: %s", e, exc_info=True)
        return t("file_index.error", error=str(e))
    finally:
        db.close()

    # Scan to report what's available
    available = len(scan_project_files(path))

    return t("file_index.success",
             project=project,
             indexed=indexed_count,
             total_files=total_files,
             total_chunks=total_chunks,
             available=available)
