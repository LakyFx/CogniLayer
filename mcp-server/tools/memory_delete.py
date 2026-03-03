"""memory_delete — Delete facts from CogniLayer memory by ID."""

import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db, ensure_vec
from utils import get_active_session
from i18n import t

_log = logging.getLogger("cognilayer.tools.memory_delete")


def memory_delete(ids: list[str]) -> str:
    """Delete facts by their UUIDs."""
    if not ids:
        return t("memory_delete.no_ids")

    session = get_active_session()
    session_id = session.get("session_id")

    db = open_db()
    try:
        # Check if vec tables exist for cleanup
        has_vec = ensure_vec(db)

        deleted = 0
        for fact_id in ids:
            # Get full fact before deletion (for history + vec cleanup)
            fact = db.execute(
                "SELECT rowid, content, type, domain, tags, project FROM facts WHERE id = ?",
                (fact_id,)
            ).fetchone()
            if not fact:
                continue

            rowid = fact[0]

            # Save to history before deleting
            try:
                db.execute("""
                    INSERT INTO facts_history (fact_id, project, content, type, domain, tags,
                                               action, changed_at, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, 'delete', ?, ?)
                """, (fact_id, fact[5], fact[1], fact[2], fact[3], fact[4],
                      datetime.now().isoformat(), session_id))
            except sqlite3.OperationalError:
                pass  # facts_history table may not exist yet
            except Exception as e:
                _log.warning("Failed to save history for fact %s: %s", fact_id[:8], e)

            # Clean up fact links (bidirectional)
            try:
                db.execute("DELETE FROM fact_links WHERE source_id = ? OR target_id = ?",
                           (fact_id, fact_id))
            except sqlite3.OperationalError:
                pass  # fact_links table may not exist yet
            except Exception as e:
                _log.warning("Failed to clean fact_links for %s: %s", fact_id[:8], e)

            # Clean up causal chains
            try:
                db.execute("DELETE FROM causal_chains WHERE cause_id = ? OR effect_id = ?",
                           (fact_id, fact_id))
            except sqlite3.OperationalError:
                pass  # causal_chains table may not exist yet
            except Exception as e:
                _log.warning("Failed to clean causal_chains for %s: %s", fact_id[:8], e)

            # Clean up contradictions
            try:
                db.execute("DELETE FROM contradictions WHERE fact_id_a = ? OR fact_id_b = ?",
                           (fact_id, fact_id))
            except sqlite3.OperationalError:
                pass  # contradictions table may not exist yet
            except Exception as e:
                _log.warning("Failed to clean contradictions for %s: %s", fact_id[:8], e)

            # Delete from facts (triggers auto-delete from facts_fts via trigger)
            result = db.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            deleted += result.rowcount

            # Clean up vector embedding if vec is available
            if has_vec:
                try:
                    db.execute("DELETE FROM facts_vec WHERE rowid = ?", (rowid,))
                except sqlite3.OperationalError:
                    pass  # Vec table might not have this rowid
                except Exception as e:
                    _log.warning("Failed to clean facts_vec for rowid %s: %s", rowid, e)

        db.commit()
    finally:
        db.close()

    return t("memory_delete.deleted", deleted=deleted)
