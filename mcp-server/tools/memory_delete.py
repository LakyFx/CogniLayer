"""memory_delete — Delete facts from CogniLayer memory by ID."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db


def memory_delete(ids: list[str]) -> str:
    """Delete facts by their UUIDs."""
    if not ids:
        return "Zadna ID ke smazani."

    db = open_db()
    try:
        deleted = 0
        for fact_id in ids:
            # Get rowid for FTS cleanup (trigger handles it automatically)
            result = db.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            deleted += result.rowcount
        db.commit()
    finally:
        db.close()

    return f"Smazano {deleted} faktu z pameti."
