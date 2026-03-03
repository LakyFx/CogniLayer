"""Code indexer — 3-phase pipeline: scan → parse → store + resolve.

Handles full and incremental indexing with time budget enforcement.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

_log = logging.getLogger("cognilayer.code.indexer")

# Directories to always skip
DEFAULT_IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", ".nuxt", "dist", "build",
    ".tox", ".pytest_cache", ".mypy_cache", ".ruff_cache", "venv", ".venv",
    "env", ".env", "vendor", "coverage", ".coverage", "htmlcov",
    ".turbo", ".parcel-cache", ".svelte-kit", "out", ".output",
    "target",  # Rust
}

# Max file size to parse (500KB)
MAX_FILE_SIZE = 512_000


def _db_execute_with_retry(db, sql, params=(), max_retries=3, delay=0.5):
    """Execute SQL with retry on OperationalError (locked/busy)."""
    for attempt in range(max_retries):
        try:
            return db.execute(sql, params)
        except sqlite3.OperationalError as e:
            if attempt < max_retries - 1 and ("locked" in str(e) or "busy" in str(e)):
                time.sleep(delay * (attempt + 1))
                continue
            raise


def scan_files(project_path: str, ignore_dirs: set[str] | None = None,
               extensions: set[str] | None = None) -> list[dict]:
    """Scan project directory for source files.

    Returns list of dicts with: path, extension, mtime, size.
    """
    from code.parsers.registry import SUPPORTED_EXTENSIONS

    if extensions is None:
        extensions = SUPPORTED_EXTENSIONS
    if ignore_dirs is None:
        ignore_dirs = DEFAULT_IGNORE_DIRS

    results = []
    root = Path(project_path)

    if not root.is_dir():
        return results

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out ignored directories (modifies in-place to skip recursion)
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith(".")]

        for fname in filenames:
            ext = Path(fname).suffix
            if ext not in extensions:
                continue

            fpath = Path(dirpath) / fname
            try:
                stat = fpath.stat()
                if stat.st_size > MAX_FILE_SIZE:
                    continue
                results.append({
                    "path": str(fpath),
                    "rel_path": str(fpath.relative_to(root)).replace("\\", "/"),
                    "extension": ext,
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                })
            except OSError:
                continue

    return results


def index_project(db: sqlite3.Connection, project: str, project_path: str,
                  time_budget: float = 30.0, incremental: bool = True) -> dict:
    """Index a project's source code.

    3-phase pipeline:
    1. Scan — find source files
    2. Parse — extract symbols + references via tree-sitter
    3. Store — write to DB + resolve references

    Args:
        db: Database connection
        project: Project name
        project_path: Path to project root
        time_budget: Max seconds to spend (default 30s)
        incremental: If True, only re-index changed files

    Returns:
        dict with stats: files_total, files_indexed, symbols, references, errors, elapsed
    """
    from code.parsers.registry import get_parser, get_language
    from code.resolver import resolve_references

    start_time = time.time()
    stats = {
        "files_total": 0,
        "files_indexed": 0,
        "files_skipped": 0,
        "symbols": 0,
        "references": 0,
        "resolved": 0,
        "errors": [],
        "elapsed": 0.0,
        "partial": False,
    }

    # Phase 1: Scan
    files = scan_files(project_path)
    stats["files_total"] = len(files)

    if not files:
        stats["elapsed"] = time.time() - start_time
        return stats

    # Determine which files need indexing
    if incremental:
        files_to_index = _filter_changed_files(db, project, files)
    else:
        files_to_index = files

    stats["files_skipped"] = len(files) - len(files_to_index)

    if not files_to_index:
        stats["elapsed"] = time.time() - start_time
        return stats

    # Phase 2 + 3: Parse and store
    for finfo in files_to_index:
        # Time budget check
        elapsed = time.time() - start_time
        if elapsed >= time_budget:
            stats["partial"] = True
            _log.warning("Time budget exhausted after %.1fs, indexed %d/%d files",
                         elapsed, stats["files_indexed"], len(files_to_index))
            break

        ext = finfo["extension"]
        parser = get_parser(ext)
        if not parser:
            continue

        language = get_language(ext) or "unknown"

        try:
            result = parser.parse_file(finfo["path"])
        except Exception as e:
            stats["errors"].append(f"{finfo['rel_path']}: {e}")
            _log.warning("Parse failed for %s: %s", finfo["rel_path"], e)
            continue

        if result.errors:
            for err in result.errors:
                stats["errors"].append(f"{finfo['rel_path']}: {err}")
            if not result.symbols and not result.references:
                continue

        # Store to DB
        try:
            file_id = _store_file(db, project, finfo, language, len(result.symbols))
            _store_symbols(db, project, file_id, result.symbols)
            _store_references(db, project, file_id, result.references)
            db.commit()
            stats["files_indexed"] += 1
            stats["symbols"] += len(result.symbols)
            stats["references"] += len(result.references)
        except sqlite3.OperationalError as e:
            if "locked" in str(e) or "busy" in str(e):
                _log.warning("DB locked during store for %s, skipping", finfo["rel_path"])
                stats["errors"].append(f"{finfo['rel_path']}: DB locked")
                try:
                    db.rollback()
                except sqlite3.OperationalError:
                    _log.debug("Rollback also failed after DB lock")
            else:
                raise

    # Phase 3b: Resolve references (always run if there are unresolved refs, not just new files)
    try:
        unresolved = db.execute("""
            SELECT COUNT(*) FROM code_references
            WHERE project = ? AND to_symbol_id IS NULL
        """, (project,)).fetchone()[0]

        if stats["files_indexed"] > 0 or unresolved > 0:
            stats["resolved"] = resolve_references(db, project)
    except Exception as e:
        _log.warning("Reference resolution failed: %s", e)

    # If partial, mark remaining un-indexed files for next run
    if stats["partial"]:
        _log.info("Partial index: %d files remain, will be indexed on next run",
                  len(files_to_index) - stats["files_indexed"])

    stats["elapsed"] = time.time() - start_time
    return stats


def reindex_dirty(db: sqlite3.Connection, project: str, project_path: str,
                  time_budget: float = 10.0) -> dict:
    """Re-index only dirty (modified) files. Called before queries.

    Returns same stats dict as index_project.
    """
    from code.parsers.registry import get_parser, get_language
    from code.resolver import resolve_references

    start_time = time.time()
    stats = {
        "files_total": 0,
        "files_indexed": 0,
        "symbols": 0,
        "references": 0,
        "resolved": 0,
        "errors": [],
        "elapsed": 0.0,
        "partial": False,
    }

    # Find dirty files
    dirty = db.execute("""
        SELECT id, file_path, language FROM code_files
        WHERE project = ? AND is_dirty = 1
    """, (project,)).fetchall()

    if not dirty:
        stats["elapsed"] = time.time() - start_time
        return stats

    stats["files_total"] = len(dirty)

    for row in dirty:
        elapsed = time.time() - start_time
        if elapsed >= time_budget:
            stats["partial"] = True
            break

        row_dict = dict(row)
        file_path = row_dict["file_path"]
        file_id = row_dict["id"]

        # Reconstruct absolute path
        abs_path = Path(project_path) / file_path
        if not abs_path.exists():
            # File was deleted — remove from index
            _delete_file(db, file_id)
            stats["files_indexed"] += 1
            continue

        ext = abs_path.suffix
        parser = get_parser(ext)
        if not parser:
            continue

        language = get_language(ext) or row_dict["language"]

        try:
            result = parser.parse_file(str(abs_path))
        except Exception as e:
            stats["errors"].append(f"{file_path}: {e}")
            continue

        try:
            _stat = abs_path.stat()
            finfo = {
                "path": str(abs_path),
                "rel_path": file_path,
                "extension": ext,
                "mtime": _stat.st_mtime,
                "size": _stat.st_size,
            }
            # Delete old data and re-store
            _delete_file_data(db, file_id)
            _update_file(db, file_id, finfo, language, len(result.symbols))
            _store_symbols(db, project, file_id, result.symbols)
            _store_references(db, project, file_id, result.references)
            db.commit()
            stats["files_indexed"] += 1
            stats["symbols"] += len(result.symbols)
            stats["references"] += len(result.references)
        except sqlite3.OperationalError as e:
            stats["errors"].append(f"{file_path}: DB error: {e}")
            try:
                db.rollback()
            except sqlite3.OperationalError:
                _log.debug("Rollback also failed for %s", file_path)

    if stats["files_indexed"] > 0:
        try:
            stats["resolved"] = resolve_references(db, project)
        except Exception as e:
            _log.warning("Reference resolution failed in reindex_dirty: %s", e)

    stats["elapsed"] = time.time() - start_time
    return stats


def _filter_changed_files(db: sqlite3.Connection, project: str,
                          files: list[dict]) -> list[dict]:
    """Filter files to only those that changed since last index."""
    indexed = {}
    try:
        rows = db.execute("""
            SELECT file_path, file_mtime FROM code_files WHERE project = ?
        """, (project,)).fetchall()
        for row in rows:
            indexed[row["file_path"]] = row["file_mtime"]
    except sqlite3.OperationalError:
        return files  # Table might not exist yet

    changed = []
    for finfo in files:
        rel = finfo["rel_path"]
        if rel not in indexed or abs(finfo["mtime"] - indexed[rel]) > 0.01:
            changed.append(finfo)

    return changed


def _store_file(db: sqlite3.Connection, project: str, finfo: dict,
                language: str, symbol_count: int) -> int:
    """Insert or update code_files entry. Returns file_id."""
    now = datetime.now().isoformat()

    # Try to get existing file
    existing = db.execute("""
        SELECT id FROM code_files WHERE project = ? AND file_path = ?
    """, (project, finfo["rel_path"])).fetchone()

    if existing:
        file_id = existing["id"]
        # Clear old data for this file
        _delete_file_data(db, file_id)
        # Update file record
        _db_execute_with_retry(db, """
            UPDATE code_files SET
                language = ?, file_mtime = ?, file_size = ?,
                symbol_count = ?, is_dirty = 0, indexed_at = ?
            WHERE id = ?
        """, (language, finfo["mtime"], finfo["size"], symbol_count, now, file_id))
    else:
        cursor = _db_execute_with_retry(db, """
            INSERT INTO code_files (project, file_path, language, file_mtime,
                                    file_size, symbol_count, is_dirty, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """, (project, finfo["rel_path"], language, finfo["mtime"],
              finfo["size"], symbol_count, now))
        file_id = cursor.lastrowid

    return file_id


def _update_file(db: sqlite3.Connection, file_id: int, finfo: dict,
                 language: str, symbol_count: int) -> None:
    """Update existing code_files entry after re-index."""
    now = datetime.now().isoformat()
    _db_execute_with_retry(db, """
        UPDATE code_files SET
            language = ?, file_mtime = ?, file_size = ?,
            symbol_count = ?, is_dirty = 0, indexed_at = ?
        WHERE id = ?
    """, (language, finfo["mtime"], finfo["size"], symbol_count, now, file_id))


def _store_symbols(db: sqlite3.Connection, project: str, file_id: int,
                   symbols: list) -> None:
    """Store symbols in DB. Resolves parent_id references."""
    # First pass: insert all symbols and collect id mapping
    id_map: dict[str, int] = {}  # qualified_name → DB id

    for sym in symbols:
        cursor = _db_execute_with_retry(db, """
            INSERT INTO code_symbols (project, file_id, name, qualified_name, kind,
                                      line_start, line_end, signature, docstring, exported)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project, file_id, sym.name, sym.qualified_name, sym.kind,
              sym.line_start, sym.line_end, sym.signature, sym.docstring,
              1 if sym.exported else 0))
        sym_id = cursor.lastrowid
        id_map[sym.qualified_name] = sym_id

    # Second pass: set parent_id
    for sym in symbols:
        if sym.parent_name and sym.parent_name in id_map:
            sym_id = id_map.get(sym.qualified_name)
            parent_id = id_map.get(sym.parent_name)
            if sym_id and parent_id:
                _db_execute_with_retry(db, """
                    UPDATE code_symbols SET parent_id = ? WHERE id = ?
                """, (parent_id, sym_id))


def _store_references(db: sqlite3.Connection, project: str, file_id: int,
                      references: list) -> None:
    """Store references in DB."""
    for ref in references:
        cursor = _db_execute_with_retry(db, """
            INSERT INTO code_references (project, file_id, from_symbol_id,
                                         to_name, kind, line, confidence)
            VALUES (?, ?, NULL, ?, ?, ?, ?)
        """, (project, file_id, ref.to_name, ref.kind, ref.line, ref.confidence))

        # Try to set from_symbol_id if we know the source
        if ref.from_symbol:
            from_sym = db.execute("""
                SELECT id FROM code_symbols
                WHERE project = ? AND qualified_name = ? AND file_id = ?
            """, (project, ref.from_symbol, file_id)).fetchone()
            if from_sym:
                ref_id = cursor.lastrowid
                db.execute("""
                    UPDATE code_references SET from_symbol_id = ? WHERE id = ?
                """, (from_sym["id"], ref_id))


def _delete_file_data(db: sqlite3.Connection, file_id: int) -> None:
    """Delete symbols and references for a file (before re-indexing)."""
    _db_execute_with_retry(db, "DELETE FROM code_references WHERE file_id = ?", (file_id,))
    _db_execute_with_retry(db, "DELETE FROM code_symbols WHERE file_id = ?", (file_id,))


def _delete_file(db: sqlite3.Connection, file_id: int) -> None:
    """Delete a file and all its data."""
    _delete_file_data(db, file_id)
    _db_execute_with_retry(db, "DELETE FROM code_files WHERE id = ?", (file_id,))
    try:
        db.commit()
    except sqlite3.OperationalError as e:
        _log.warning("Commit failed in _delete_file for file_id=%d: %s", file_id, e)
