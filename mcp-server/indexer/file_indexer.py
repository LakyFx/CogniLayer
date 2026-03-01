"""CogniLayer file indexer — indexes project docs into file_chunks table."""

import os
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from indexer.chunker import chunk_file

# Extensions to index
DOC_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".toml"}
IGNORE_DIRS = {"node_modules", ".git", "__pycache__", ".next", "dist", "build",
               "venv", ".venv", "stary", ".claude"}
IGNORE_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}
NEVER_INDEX = {".env", ".env.local", ".env.production", ".env.development",
               "credentials.json"}
MAX_FILE_SIZE = 200_000  # 200KB


def scan_project_files(project_path: Path, scan_depth: int = 3) -> list[Path]:
    """Scan project directory for indexable files."""
    files = []
    project_path = Path(project_path)

    def _scan(directory: Path, depth: int):
        if depth > scan_depth:
            return
        try:
            for entry in directory.iterdir():
                if entry.is_dir():
                    if entry.name not in IGNORE_DIRS:
                        _scan(entry, depth + 1)
                elif entry.is_file():
                    if entry.name in NEVER_INDEX:
                        continue
                    if entry.name in IGNORE_FILES:
                        continue
                    if entry.suffix.lower() in DOC_EXTENSIONS:
                        if entry.stat().st_size <= MAX_FILE_SIZE:
                            files.append(entry)
        except PermissionError:
            pass

    _scan(project_path, 0)
    return files


def reindex_project(db, project: str, project_path: Path,
                    time_budget: float = 1.5):
    """Re-index changed/new files for a project. Respects time budget."""
    start = time.time()
    project_path = Path(project_path)

    # Get currently indexed files from DB
    indexed = {}
    for row in db.execute(
        "SELECT DISTINCT file_path, file_mtime FROM file_chunks WHERE project = ?",
        (project,)
    ).fetchall():
        indexed[row[0]] = row[1]

    # Scan project files
    project_files = scan_project_files(project_path)

    indexed_count = 0
    for file_path in project_files:
        if time.time() - start > time_budget:
            break

        rel_path = str(file_path.relative_to(project_path)).replace("\\", "/")
        current_mtime = file_path.stat().st_mtime

        # Skip if unchanged
        if rel_path in indexed and abs(indexed[rel_path] - current_mtime) < 1:
            continue

        # Read and chunk file
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        chunks = chunk_file(content, rel_path)
        if not chunks:
            continue

        # Delete old chunks for this file
        db.execute(
            "DELETE FROM file_chunks WHERE project = ? AND file_path = ?",
            (project, rel_path)
        )

        # Insert new chunks + embeddings
        new_rowids = []
        chunk_texts = []
        for chunk in chunks:
            db.execute("""
                INSERT INTO file_chunks (project, file_path, file_mtime,
                                        section_title, chunk_index, content)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project, rel_path, current_mtime,
                chunk["section_title"], chunk["chunk_index"], chunk["content"]
            ))
            rowid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            new_rowids.append(rowid)
            text = chunk["content"]
            if chunk["section_title"]:
                text = f"{chunk['section_title']}: {text}"
            chunk_texts.append(text)

        # Generate embeddings for new chunks
        try:
            from embedder import embed_texts
            embeddings = embed_texts(chunk_texts)
            for rowid, emb in zip(new_rowids, embeddings):
                db.execute(
                    "INSERT OR REPLACE INTO chunks_vec(rowid, embedding) VALUES (?, ?)",
                    (rowid, emb)
                )
        except Exception:
            pass  # Embedding not available, FTS5 still works

        indexed_count += 1

    # Clean up deleted files
    current_files = {
        str(f.relative_to(project_path)).replace("\\", "/")
        for f in project_files
    }
    for indexed_path in list(indexed.keys()):
        if indexed_path not in current_files:
            db.execute(
                "DELETE FROM file_chunks WHERE project = ? AND file_path = ?",
                (project, indexed_path)
            )

    return indexed_count
