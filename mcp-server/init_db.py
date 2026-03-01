"""CogniLayer v2.9 — Database schema creation.

Run: python init_db.py
Creates ~/.cognilayer/memory.db with all tables, FTS5 indexes, and regular indexes.
Phase 1: No sqlite-vec (facts_vec, chunks_vec skipped).
"""

import sqlite3
import sys
from pathlib import Path

# Allow running standalone or as module
try:
    from db import open_db, get_db_path
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from db import open_db, get_db_path


SCHEMA = """
-- Registered projects
CREATE TABLE IF NOT EXISTS projects (
    name TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    dna_content TEXT,
    dna_updated TEXT,
    created TEXT NOT NULL,
    last_session TEXT
);

-- Atomic Memory Units (14 types)
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN
        ('decision','fact','pattern','issue','task','skill',
         'gotcha','procedure','error_fix','command',
         'performance','api_contract','dependency','client_rule')),
    domain TEXT,
    tags TEXT,
    timestamp TEXT NOT NULL,
    heat_score REAL DEFAULT 1.0,
    last_accessed TEXT,
    session_id TEXT,
    source_file TEXT,
    source_mtime REAL,
    embedding BLOB,
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- Indexed project files (chunks)
CREATE TABLE IF NOT EXISTS file_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_mtime REAL NOT NULL,
    section_title TEXT,
    chunk_index INTEGER DEFAULT 0,
    content TEXT NOT NULL,
    embedding BLOB,
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- Decision log (append-only)
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT,
    alternatives TEXT,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- Session records
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    summary TEXT,
    bridge_content TEXT,
    facts_count INTEGER DEFAULT 0,
    changes_count INTEGER DEFAULT 0,
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- Automatic change log
CREATE TABLE IF NOT EXISTS changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    project TEXT NOT NULL,
    file_path TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('create','edit','delete')),
    timestamp TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- Project Identity Card
CREATE TABLE IF NOT EXISTS project_identity (
    project TEXT PRIMARY KEY,
    deploy_ssh_alias TEXT,
    deploy_ssh_host TEXT,
    deploy_ssh_port INTEGER DEFAULT 22,
    deploy_ssh_user TEXT DEFAULT 'root',
    deploy_app_port INTEGER,
    deploy_path TEXT,
    deploy_method TEXT,
    pm2_process_name TEXT,
    pm2_process_id INTEGER,
    github_repo_url TEXT,
    github_org TEXT,
    git_production_branch TEXT DEFAULT 'main',
    domain_primary TEXT,
    domain_aliases TEXT,
    reverse_proxy TEXT,
    reverse_proxy_config_path TEXT,
    db_type TEXT,
    db_connection_hint TEXT,
    env_file_pattern TEXT,
    env_secrets_note TEXT,
    safety_locked_at TEXT,
    safety_locked_by TEXT,
    safety_last_verified TEXT,
    safety_lock_hash TEXT,
    framework TEXT,
    framework_version TEXT,
    language TEXT,
    css_approach TEXT,
    ui_library TEXT,
    db_technology TEXT,
    hosting_pattern TEXT,
    containerization TEXT,
    design_system TEXT,
    design_fonts TEXT,
    design_notes TEXT,
    build_tool TEXT,
    package_manager TEXT,
    project_category TEXT,
    created TEXT NOT NULL,
    updated TEXT NOT NULL,
    FOREIGN KEY (project) REFERENCES projects(name) ON DELETE CASCADE
);

-- Identity audit log
CREATE TABLE IF NOT EXISTS identity_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by TEXT NOT NULL,
    reason TEXT,
    session_id TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- Tech stack templates
CREATE TABLE IF NOT EXISTS tech_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    derived_from_project TEXT,
    framework TEXT, framework_version TEXT, language TEXT,
    css_approach TEXT, ui_library TEXT, db_technology TEXT,
    hosting_pattern TEXT, containerization TEXT, design_system TEXT,
    build_tool TEXT, package_manager TEXT, project_category TEXT,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_facts_project ON facts(project);
CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(project, type);
CREATE INDEX IF NOT EXISTS idx_facts_heat ON facts(heat_score DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_project ON file_chunks(project);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON file_chunks(project, file_path);
CREATE INDEX IF NOT EXISTS idx_changes_session ON changes(session_id);
CREATE INDEX IF NOT EXISTS idx_changes_project ON changes(project, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_identity_framework ON project_identity(framework);
CREATE INDEX IF NOT EXISTS idx_identity_category ON project_identity(project_category);
CREATE INDEX IF NOT EXISTS idx_identity_ssh ON project_identity(deploy_ssh_alias);
CREATE INDEX IF NOT EXISTS idx_identity_domain ON project_identity(domain_primary);
CREATE INDEX IF NOT EXISTS idx_audit_project ON identity_audit_log(project, timestamp DESC);
"""

# FTS5 virtual tables and sync triggers (separated for graceful fallback)
FTS_SCHEMA = """
-- FTS5 fulltext index on facts
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    content, tags, domain,
    content=facts, content_rowid=rowid
);

-- Triggers to keep FTS5 in sync with facts table
CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(rowid, content, tags, domain)
    VALUES (new.rowid, new.content, new.tags, new.domain);
END;

CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content, tags, domain)
    VALUES ('delete', old.rowid, old.content, old.tags, old.domain);
END;

CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content, tags, domain)
    VALUES ('delete', old.rowid, old.content, old.tags, old.domain);
    INSERT INTO facts_fts(rowid, content, tags, domain)
    VALUES (new.rowid, new.content, new.tags, new.domain);
END;

-- FTS5 fulltext index on file_chunks
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content, section_title, file_path,
    content=file_chunks, content_rowid=rowid
);

-- Triggers to keep chunks_fts in sync
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON file_chunks BEGIN
    INSERT INTO chunks_fts(rowid, content, section_title, file_path)
    VALUES (new.rowid, new.content, new.section_title, new.file_path);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON file_chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, section_title, file_path)
    VALUES ('delete', old.rowid, old.content, old.section_title, old.file_path);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON file_chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, section_title, file_path)
    VALUES ('delete', old.rowid, old.content, old.section_title, old.file_path);
    INSERT INTO chunks_fts(rowid, content, section_title, file_path)
    VALUES (new.rowid, new.content, new.section_title, new.file_path);
END;
"""

# Phase 2: Vector tables (require sqlite-vec extension)
VEC_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS facts_vec USING vec0(
    embedding float[384]
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(
    embedding float[384]
);
"""


def rebuild_fts(db):
    """Rebuild FTS5 indexes from source tables."""
    try:
        db.execute("INSERT INTO facts_fts(facts_fts) VALUES('rebuild')")
        db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        db.commit()
    except Exception as e:
        print(f"FTS rebuild failed: {e}", file=sys.stderr)


def init_db():
    """Create all tables and indexes."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = open_db(with_vec=True)
    db.executescript(SCHEMA)
    db.commit()

    # Create FTS5 virtual tables and triggers (graceful if FTS5 unavailable)
    try:
        db.executescript(FTS_SCHEMA)
        db.commit()
    except Exception as e:
        print(f"FTS5 not available, fulltext search disabled: {e}",
              file=sys.stderr)

    # Phase 2: Create vector tables if sqlite-vec is available
    try:
        db.execute("SELECT vec_version()")
        db.executescript(VEC_SCHEMA)
        db.commit()
    except Exception:
        pass  # sqlite-vec not loaded, skip vector tables

    # Verify
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    all_names = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master ORDER BY name"
    ).fetchall()]

    db.close()
    return tables, all_names


if __name__ == "__main__":
    tables, all_names = init_db()
    print(f"Database created at: {get_db_path()}")
    print(f"Objects created: {len(all_names)}")
    for name in sorted(all_names):
        print(f"  - {name}")
