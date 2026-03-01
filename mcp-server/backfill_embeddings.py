"""Backfill embeddings for existing facts and file_chunks.

Run: python backfill_embeddings.py
Processes all facts/chunks that don't have embeddings yet.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import open_db
from embedder import embed_texts, is_available, EMBEDDING_DIM


def backfill_facts(db, batch_size: int = 50):
    """Backfill embeddings for facts missing from facts_vec."""
    # Find facts without embeddings
    rows = db.execute("""
        SELECT f.rowid, f.content, f.tags, f.domain
        FROM facts f
        WHERE f.rowid NOT IN (SELECT rowid FROM facts_vec)
    """).fetchall()

    if not rows:
        print("  All facts already have embeddings.")
        return 0

    total = len(rows)
    processed = 0
    print(f"  Backfilling {total} facts...")

    for i in range(0, total, batch_size):
        batch = rows[i:i + batch_size]
        texts = []
        for row in batch:
            text = row[1]  # content
            if row[2]:  # tags
                text += f" [{row[2]}]"
            if row[3]:  # domain
                text += f" [{row[3]}]"
            texts.append(text)

        embeddings = embed_texts(texts)
        for j, emb in enumerate(embeddings):
            db.execute(
                "INSERT OR REPLACE INTO facts_vec(rowid, embedding) VALUES (?, ?)",
                (batch[j][0], emb)
            )
        processed += len(batch)
        print(f"  [{processed}/{total}] facts embedded")

    db.commit()
    return processed


def backfill_chunks(db, batch_size: int = 50):
    """Backfill embeddings for chunks missing from chunks_vec."""
    rows = db.execute("""
        SELECT fc.rowid, fc.content, fc.section_title
        FROM file_chunks fc
        WHERE fc.rowid NOT IN (SELECT rowid FROM chunks_vec)
    """).fetchall()

    if not rows:
        print("  All chunks already have embeddings.")
        return 0

    total = len(rows)
    processed = 0
    print(f"  Backfilling {total} chunks...")

    for i in range(0, total, batch_size):
        batch = rows[i:i + batch_size]
        texts = []
        for row in batch:
            text = row[1]  # content
            if row[2]:  # section_title
                text = f"{row[2]}: {text}"
            texts.append(text)

        embeddings = embed_texts(texts)
        for j, emb in enumerate(embeddings):
            db.execute(
                "INSERT OR REPLACE INTO chunks_vec(rowid, embedding) VALUES (?, ?)",
                (batch[j][0], emb)
            )
        processed += len(batch)
        print(f"  [{processed}/{total}] chunks embedded")

    db.commit()
    return processed


def main():
    if not is_available():
        print("ERROR: fastembed not installed. Run: pip install fastembed")
        sys.exit(1)

    print("CogniLayer — Backfill Embeddings")
    print("=" * 40)

    db = open_db(with_vec=True)
    try:
        # Check if vec tables exist
        try:
            db.execute("SELECT COUNT(*) FROM facts_vec")
        except Exception:
            print("ERROR: Vector tables not found. Run init_db.py first.")
            sys.exit(1)

        start = time.time()

        print("\n[1/2] Facts:")
        facts_count = backfill_facts(db)

        print("\n[2/2] File chunks:")
        chunks_count = backfill_chunks(db)

        elapsed = time.time() - start
        print(f"\nDone in {elapsed:.1f}s: {facts_count} facts + {chunks_count} chunks embedded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
