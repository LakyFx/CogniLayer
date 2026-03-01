"""memory_delete — Delete facts from CogniLayer memory by ID."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db, ensure_vec


def memory_delete(ids: list[str]) -> str:
    """Delete facts by their UUIDs."""
    if not ids:
        return "Zadna ID ke smazani."

    db = open_db()
    try:
        # Check if vec tables exist for cleanup
        has_vec = ensure_vec(db)

        deleted = 0
        for fact_id in ids:
            # Get rowid before deletion (needed for vec cleanup)
            row = db.execute("SELECT rowid FROM facts WHERE id = ?", (fact_id,)).fetchone()
            if not row:
                continue

            rowid = row[0]

            # Delete from facts (triggers auto-delete from facts_fts via trigger)
            result = db.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            deleted += result.rowcount

            # Clean up vector embedding if vec is available
            if has_vec:
                try:
                    db.execute("DELETE FROM facts_vec WHERE rowid = ?", (rowid,))
                except Exception:
                    pass  # Vec table might not have this rowid

        db.commit()
    finally:
        db.close()

    return f"Smazano {deleted} faktu z pameti."
