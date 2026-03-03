"""session_init — MCP tool replacing SessionStart hook for Codex CLI.

Does the same work as on_session_start.py but as an MCP tool call:
1. Detects project from CWD (or provided path)
2. Registers project if new
3. Checks crash recovery
4. Auto-detects identity
5. Generates/loads DNA
6. Loads latest bridge
7. Creates session
8. Returns full context (DNA + bridge + crash info)

No file injection — Codex reads AGENTS.md separately.
Reindexing is skipped here (handled by hooks separately) to avoid
hanging on model downloads or slow I/O.
"""

import logging
import sys
import uuid
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"

# Import session start helpers
sys.path.insert(0, str(COGNILAYER_HOME / "hooks"))
sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))

try:
    from i18n import t
except ImportError:
    def t(key, **kwargs):
        return key

logger = logging.getLogger("cognilayer.session_init")


def session_init(project_path: str | None = None) -> str:
    """Initialize a CogniLayer session and return full context."""
    logger.info("session_init called with project_path=%s", project_path)
    from on_session_start import (
        detect_project, register_project_if_new,
        get_or_generate_dna, get_latest_bridge,
        create_session, write_session_file, open_db
    )
    from tools.project_context import _check_crash_recovery, _auto_detect_identity

    if not DB_PATH.exists():
        logger.warning("DB not found at %s", DB_PATH)
        return t("session_init.no_db")

    if project_path:
        path = Path(project_path).resolve()
    else:
        path = Path.cwd()

    if not path.exists() or not path.is_dir():
        return t("session_init.invalid_path", path=str(path))

    project_name = detect_project(path)
    logger.info("Detected project: %s at %s", project_name, path)

    # Generate claude_session_id for Codex CLI (it doesn't provide one)
    claude_session_id = str(uuid.uuid4())

    db = open_db()
    try:
        register_project_if_new(db, project_name, path)
        crash_info = _check_crash_recovery(db, project_name)
        _auto_detect_identity(db, project_name, path)
        dna = get_or_generate_dna(db, project_name, path)
        bridge = get_latest_bridge(db, project_name)
        session_id = create_session(db, project_name, claude_session_id)
        write_session_file(session_id, project_name, str(path), claude_session_id)

        # NOTE: reindex_project intentionally NOT called here.
        # It can hang on first run (fastembed model download ~130MB)
        # or on large projects. The SessionStart hook handles reindexing.

        db.commit()
        logger.info("session_init complete: session=%s project=%s", session_id, project_name)
    except Exception as e:
        logger.error("session_init failed: %s", e, exc_info=True)
        return t("session_init.error", error=str(e))
    finally:
        try:
            db.close()
        except Exception:
            pass

    # Build response
    parts = [t("session_init.header", project=project_name, session_id=session_id)]
    parts.append("")
    parts.append(dna)

    if bridge:
        parts.append("")
        parts.append(f"## Last Session Bridge\n{bridge}")

    if crash_info:
        parts.append("")
        parts.append(crash_info)

    parts.append("")
    parts.append(t("session_init.instructions"))

    return "\n".join(parts)
