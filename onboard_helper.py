"""Batch onboarding helper for CogniLayer — registers projects and writes facts."""

import sys
import json
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))
from db import open_db

def register_project(name: str, path: str):
    """Register a project in the DB if not exists."""
    db = open_db()
    try:
        existing = db.execute("SELECT name FROM projects WHERE name = ?", (name,)).fetchone()
        if existing:
            return f"Project '{name}' already registered."
        db.execute("""
            INSERT INTO projects (name, path, created, last_session)
            VALUES (?, ?, ?, ?)
        """, (name, path, datetime.now().isoformat(), datetime.now().isoformat()))
        db.commit()
        return f"Registered project '{name}' at {path}."
    finally:
        db.close()

def write_fact(project: str, content: str, fact_type: str = "fact",
               tags: str = None, domain: str = None, source_file: str = None):
    """Write a single fact to the DB."""
    db = open_db()
    try:
        # Dedup by content + project + type
        existing = db.execute("""
            SELECT id FROM facts WHERE project = ? AND content = ? AND type = ?
        """, (project, content, fact_type)).fetchone()
        if existing:
            return f"  [skip] Already exists: {content[:50]}..."

        fact_id = str(uuid.uuid4())
        db.execute("""
            INSERT INTO facts (id, project, content, type, domain, tags,
                              timestamp, heat_score, session_id,
                              source_file, source_mtime)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1.0, ?, ?, NULL)
        """, (
            fact_id, project, content, fact_type, domain, tags,
            datetime.now().isoformat(), None, source_file
        ))
        db.commit()
        return f"  [ok] {fact_type}: {content[:60]}..."
    finally:
        db.close()

def write_facts_batch(project: str, facts: list[dict]):
    """Write multiple facts at once. Each dict: {content, type, tags?, domain?, source_file?}"""
    db = open_db()
    written = 0
    skipped = 0
    try:
        for f in facts:
            content = f["content"]
            fact_type = f.get("type", "fact")
            existing = db.execute("""
                SELECT id FROM facts WHERE project = ? AND content = ? AND type = ?
            """, (project, content, fact_type)).fetchone()
            if existing:
                skipped += 1
                continue

            fact_id = str(uuid.uuid4())
            db.execute("""
                INSERT INTO facts (id, project, content, type, domain, tags,
                                  timestamp, heat_score, session_id,
                                  source_file, source_mtime)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1.0, ?, ?, NULL)
            """, (
                fact_id, project, content, fact_type,
                f.get("domain"), f.get("tags"),
                datetime.now().isoformat(), None, f.get("source_file")
            ))
            written += 1
        db.commit()
    finally:
        db.close()
    return f"  Written: {written}, Skipped (dupes): {skipped}"

def set_identity(project: str, fields: dict):
    """Set or update project identity card fields."""
    db = open_db()
    try:
        existing = db.execute("SELECT project FROM project_identity WHERE project = ?", (project,)).fetchone()
        now = datetime.now().isoformat()
        if not existing:
            db.execute("INSERT INTO project_identity (project, created, updated) VALUES (?, ?, ?)",
                       (project, now, now))
            db.commit()
        else:
            db.execute("UPDATE project_identity SET updated = ? WHERE project = ?", (now, project))
            db.commit()

        for key, value in fields.items():
            try:
                db.execute(f"UPDATE project_identity SET {key} = ? WHERE project = ?", (value, project))
            except Exception as e:
                print(f"  [warn] Cannot set {key}: {e}")
        db.commit()
    finally:
        db.close()
    return f"  Identity card updated for {project}: {list(fields.keys())}"

def get_stats():
    """Get overall stats."""
    db = open_db()
    try:
        projects = db.execute("SELECT COUNT(*) as c FROM projects").fetchone()["c"]
        facts = db.execute("SELECT COUNT(*) as c FROM facts").fetchone()["c"]
        chunks = db.execute("SELECT COUNT(*) as c FROM file_chunks").fetchone()["c"]
        facts_by_project = db.execute("""
            SELECT project, COUNT(*) as c,
                   GROUP_CONCAT(DISTINCT type) as types
            FROM facts GROUP BY project
        """).fetchall()
        return {
            "projects": projects,
            "facts": facts,
            "chunks": chunks,
            "by_project": [(r["project"], r["c"], r["types"]) for r in facts_by_project]
        }
    finally:
        db.close()

if __name__ == "__main__":
    # Test
    print(get_stats())
