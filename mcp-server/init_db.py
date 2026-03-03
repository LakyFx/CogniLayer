"""CogniLayer v3 — Database schema creation and migration.

Run: python init_db.py
Creates ~/.cognilayer/memory.db with all tables, FTS5 indexes, vector tables, and regular indexes.
Supports: FTS5 fulltext, sqlite-vec vectors (optional), fact linking, knowledge gaps,
clusters, contradictions, causal chains, episode storage.
"""

import sqlite3
import sys
from datetime import datetime
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
    retrieval_count INTEGER DEFAULT 0,
    last_retrieved TEXT,
    knowledge_tier TEXT DEFAULT 'active',
    cluster_id INTEGER,
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- Fact version history (audit trail for updates and deletes)
CREATE TABLE IF NOT EXISTS facts_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id TEXT NOT NULL,
    project TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT NOT NULL,
    domain TEXT,
    tags TEXT,
    action TEXT NOT NULL CHECK(action IN ('update', 'delete')),
    changed_at TEXT NOT NULL,
    session_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_facts_history_fact ON facts_history(fact_id);

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
    episode_title TEXT,
    episode_tags TEXT,
    outcome TEXT,
    claude_session_id TEXT,
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

-- Fact links (Zettelkasten — bidirectional)
CREATE TABLE IF NOT EXISTS fact_links (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    score REAL NOT NULL,
    link_type TEXT DEFAULT 'auto',
    created TEXT NOT NULL,
    PRIMARY KEY (source_id, target_id),
    FOREIGN KEY (source_id) REFERENCES facts(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES facts(id) ON DELETE CASCADE
);

-- Knowledge gaps (failed/weak searches)
CREATE TABLE IF NOT EXISTS knowledge_gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    query TEXT NOT NULL,
    search_type TEXT,
    hit_count INTEGER DEFAULT 0,
    best_score REAL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    times_seen INTEGER DEFAULT 1,
    resolved INTEGER DEFAULT 0,
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- Fact clusters (consolidation output)
CREATE TABLE IF NOT EXISTS fact_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    label TEXT,
    summary TEXT,
    fact_count INTEGER DEFAULT 0,
    created TEXT NOT NULL,
    updated TEXT NOT NULL,
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- Contradictions detected during consolidation
CREATE TABLE IF NOT EXISTS contradictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    fact_id_a TEXT NOT NULL,
    fact_id_b TEXT NOT NULL,
    reason TEXT,
    detected TEXT NOT NULL,
    resolved INTEGER DEFAULT 0,
    FOREIGN KEY (project) REFERENCES projects(name),
    FOREIGN KEY (fact_id_a) REFERENCES facts(id) ON DELETE CASCADE,
    FOREIGN KEY (fact_id_b) REFERENCES facts(id) ON DELETE CASCADE
);

-- Causal chains (cause -> effect relationships)
CREATE TABLE IF NOT EXISTS causal_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    cause_id TEXT NOT NULL,
    effect_id TEXT NOT NULL,
    relationship TEXT DEFAULT 'caused',
    confidence REAL DEFAULT 1.0,
    created TEXT NOT NULL,
    session_id TEXT,
    FOREIGN KEY (project) REFERENCES projects(name),
    FOREIGN KEY (cause_id) REFERENCES facts(id) ON DELETE CASCADE,
    FOREIGN KEY (effect_id) REFERENCES facts(id) ON DELETE CASCADE
);

-- Code Intelligence: tracked source files
CREATE TABLE IF NOT EXISTS code_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    file_path TEXT NOT NULL,
    language TEXT NOT NULL,
    file_mtime REAL NOT NULL,
    file_size INTEGER DEFAULT 0,
    symbol_count INTEGER DEFAULT 0,
    is_dirty INTEGER DEFAULT 0,
    indexed_at TEXT NOT NULL,
    UNIQUE(project, file_path),
    FOREIGN KEY (project) REFERENCES projects(name)
);

-- Code Intelligence: symbols (functions, classes, methods, interfaces)
CREATE TABLE IF NOT EXISTS code_symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN
        ('function','class','method','interface','variable','type_alias','enum','module')),
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    parent_id INTEGER,
    signature TEXT,
    docstring TEXT,
    exported INTEGER DEFAULT 0,
    FOREIGN KEY (project) REFERENCES projects(name),
    FOREIGN KEY (file_id) REFERENCES code_files(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES code_symbols(id) ON DELETE SET NULL
);

-- Code Intelligence: references (calls, imports, inheritance)
CREATE TABLE IF NOT EXISTS code_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    from_symbol_id INTEGER,
    to_symbol_id INTEGER,
    to_name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN
        ('call','import','inherit','implement','type_ref','decorator')),
    line INTEGER NOT NULL,
    confidence REAL DEFAULT 0.5,
    FOREIGN KEY (project) REFERENCES projects(name),
    FOREIGN KEY (file_id) REFERENCES code_files(id) ON DELETE CASCADE,
    FOREIGN KEY (from_symbol_id) REFERENCES code_symbols(id) ON DELETE CASCADE,
    FOREIGN KEY (to_symbol_id) REFERENCES code_symbols(id) ON DELETE SET NULL
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
CREATE INDEX IF NOT EXISTS idx_sessions_claude_sid ON sessions(claude_session_id);
CREATE INDEX IF NOT EXISTS idx_identity_framework ON project_identity(framework);
CREATE INDEX IF NOT EXISTS idx_identity_category ON project_identity(project_category);
CREATE INDEX IF NOT EXISTS idx_identity_ssh ON project_identity(deploy_ssh_alias);
CREATE INDEX IF NOT EXISTS idx_identity_domain ON project_identity(domain_primary);
CREATE INDEX IF NOT EXISTS idx_audit_project ON identity_audit_log(project, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_fact_links_source ON fact_links(source_id);
CREATE INDEX IF NOT EXISTS idx_fact_links_target ON fact_links(target_id);
CREATE INDEX IF NOT EXISTS idx_gaps_project ON knowledge_gaps(project);
CREATE INDEX IF NOT EXISTS idx_gaps_resolved ON knowledge_gaps(resolved);
CREATE INDEX IF NOT EXISTS idx_code_files_project ON code_files(project);
CREATE INDEX IF NOT EXISTS idx_code_files_dirty ON code_files(project, is_dirty);
CREATE INDEX IF NOT EXISTS idx_code_symbols_project ON code_symbols(project);
CREATE INDEX IF NOT EXISTS idx_code_symbols_file ON code_symbols(file_id);
CREATE INDEX IF NOT EXISTS idx_code_symbols_name ON code_symbols(name);
CREATE INDEX IF NOT EXISTS idx_code_symbols_qname ON code_symbols(qualified_name);
CREATE INDEX IF NOT EXISTS idx_code_symbols_kind ON code_symbols(project, kind);
CREATE INDEX IF NOT EXISTS idx_code_refs_project ON code_references(project);
CREATE INDEX IF NOT EXISTS idx_code_refs_file ON code_references(file_id);
CREATE INDEX IF NOT EXISTS idx_code_refs_from ON code_references(from_symbol_id);
CREATE INDEX IF NOT EXISTS idx_code_refs_to ON code_references(to_symbol_id);
CREATE INDEX IF NOT EXISTS idx_code_refs_to_name ON code_references(to_name);
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

-- FTS5 fulltext index on code_symbols
CREATE VIRTUAL TABLE IF NOT EXISTS code_symbols_fts USING fts5(
    name, qualified_name, signature, docstring,
    content=code_symbols, content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS code_symbols_ai AFTER INSERT ON code_symbols BEGIN
    INSERT INTO code_symbols_fts(rowid, name, qualified_name, signature, docstring)
    VALUES (new.rowid, new.name, new.qualified_name, new.signature, new.docstring);
END;

CREATE TRIGGER IF NOT EXISTS code_symbols_ad AFTER DELETE ON code_symbols BEGIN
    INSERT INTO code_symbols_fts(code_symbols_fts, rowid, name, qualified_name, signature, docstring)
    VALUES ('delete', old.rowid, old.name, old.qualified_name, old.signature, old.docstring);
END;

CREATE TRIGGER IF NOT EXISTS code_symbols_au AFTER UPDATE ON code_symbols BEGIN
    INSERT INTO code_symbols_fts(code_symbols_fts, rowid, name, qualified_name, signature, docstring)
    VALUES ('delete', old.rowid, old.name, old.qualified_name, old.signature, old.docstring);
    INSERT INTO code_symbols_fts(rowid, name, qualified_name, signature, docstring)
    VALUES (new.rowid, new.name, new.qualified_name, new.signature, new.docstring);
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


def upgrade_schema(db):
    """Add new V3 columns/tables to existing database (safe idempotent migration)."""
    # New columns on facts table
    for col, typedef in [
        ("retrieval_count", "INTEGER DEFAULT 0"),
        ("last_retrieved", "TEXT"),
        ("knowledge_tier", "TEXT DEFAULT 'active'"),
        ("cluster_id", "INTEGER"),
    ]:
        try:
            db.execute(f"ALTER TABLE facts ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # New columns on sessions table (episode metadata + multi-CLI)
    for col, typedef in [
        ("episode_title", "TEXT"),
        ("episode_tags", "TEXT"),
        ("outcome", "TEXT"),
        ("claude_session_id", "TEXT"),
    ]:
        try:
            db.execute(f"ALTER TABLE sessions ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # New tables (CREATE IF NOT EXISTS is idempotent)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS fact_links (
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            score REAL NOT NULL,
            link_type TEXT DEFAULT 'auto',
            created TEXT NOT NULL,
            PRIMARY KEY (source_id, target_id),
            FOREIGN KEY (source_id) REFERENCES facts(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES facts(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS knowledge_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            query TEXT NOT NULL,
            search_type TEXT,
            hit_count INTEGER DEFAULT 0,
            best_score REAL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            times_seen INTEGER DEFAULT 1,
            resolved INTEGER DEFAULT 0,
            FOREIGN KEY (project) REFERENCES projects(name)
        );
        CREATE TABLE IF NOT EXISTS fact_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            label TEXT,
            summary TEXT,
            fact_count INTEGER DEFAULT 0,
            created TEXT NOT NULL,
            updated TEXT NOT NULL,
            FOREIGN KEY (project) REFERENCES projects(name)
        );
        CREATE TABLE IF NOT EXISTS contradictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            fact_id_a TEXT NOT NULL,
            fact_id_b TEXT NOT NULL,
            reason TEXT,
            detected TEXT NOT NULL,
            resolved INTEGER DEFAULT 0,
            FOREIGN KEY (project) REFERENCES projects(name),
            FOREIGN KEY (fact_id_a) REFERENCES facts(id) ON DELETE CASCADE,
            FOREIGN KEY (fact_id_b) REFERENCES facts(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS causal_chains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            cause_id TEXT NOT NULL,
            effect_id TEXT NOT NULL,
            relationship TEXT DEFAULT 'caused',
            confidence REAL DEFAULT 1.0,
            created TEXT NOT NULL,
            session_id TEXT,
            FOREIGN KEY (project) REFERENCES projects(name),
            FOREIGN KEY (cause_id) REFERENCES facts(id) ON DELETE CASCADE,
            FOREIGN KEY (effect_id) REFERENCES facts(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_fact_links_source ON fact_links(source_id);
        CREATE INDEX IF NOT EXISTS idx_fact_links_target ON fact_links(target_id);
        CREATE INDEX IF NOT EXISTS idx_gaps_project ON knowledge_gaps(project);
        CREATE INDEX IF NOT EXISTS idx_gaps_resolved ON knowledge_gaps(resolved);
        CREATE INDEX IF NOT EXISTS idx_clusters_project ON fact_clusters(project);
        CREATE INDEX IF NOT EXISTS idx_contradictions_project ON contradictions(project);
        CREATE INDEX IF NOT EXISTS idx_contradictions_resolved ON contradictions(resolved);
        CREATE INDEX IF NOT EXISTS idx_causal_cause ON causal_chains(cause_id);
        CREATE INDEX IF NOT EXISTS idx_causal_effect ON causal_chains(effect_id);
        CREATE INDEX IF NOT EXISTS idx_causal_project ON causal_chains(project);
        CREATE INDEX IF NOT EXISTS idx_facts_tier ON facts(knowledge_tier);
        CREATE INDEX IF NOT EXISTS idx_facts_cluster ON facts(cluster_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_claude_sid ON sessions(claude_session_id);

        -- Code Intelligence tables (V4)
        CREATE TABLE IF NOT EXISTS code_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            file_path TEXT NOT NULL,
            language TEXT NOT NULL,
            file_mtime REAL NOT NULL,
            file_size INTEGER DEFAULT 0,
            symbol_count INTEGER DEFAULT 0,
            is_dirty INTEGER DEFAULT 0,
            indexed_at TEXT NOT NULL,
            UNIQUE(project, file_path),
            FOREIGN KEY (project) REFERENCES projects(name)
        );
        CREATE TABLE IF NOT EXISTS code_symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            file_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            qualified_name TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN
                ('function','class','method','interface','variable','type_alias','enum','module')),
            line_start INTEGER NOT NULL,
            line_end INTEGER NOT NULL,
            parent_id INTEGER,
            signature TEXT,
            docstring TEXT,
            exported INTEGER DEFAULT 0,
            FOREIGN KEY (project) REFERENCES projects(name),
            FOREIGN KEY (file_id) REFERENCES code_files(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES code_symbols(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS code_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            file_id INTEGER NOT NULL,
            from_symbol_id INTEGER,
            to_symbol_id INTEGER,
            to_name TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN
                ('call','import','inherit','implement','type_ref','decorator')),
            line INTEGER NOT NULL,
            confidence REAL DEFAULT 0.5,
            FOREIGN KEY (project) REFERENCES projects(name),
            FOREIGN KEY (file_id) REFERENCES code_files(id) ON DELETE CASCADE,
            FOREIGN KEY (from_symbol_id) REFERENCES code_symbols(id) ON DELETE CASCADE,
            FOREIGN KEY (to_symbol_id) REFERENCES code_symbols(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_code_files_project ON code_files(project);
        CREATE INDEX IF NOT EXISTS idx_code_files_dirty ON code_files(project, is_dirty);
        CREATE INDEX IF NOT EXISTS idx_code_symbols_project ON code_symbols(project);
        CREATE INDEX IF NOT EXISTS idx_code_symbols_file ON code_symbols(file_id);
        CREATE INDEX IF NOT EXISTS idx_code_symbols_name ON code_symbols(name);
        CREATE INDEX IF NOT EXISTS idx_code_symbols_qname ON code_symbols(qualified_name);
        CREATE INDEX IF NOT EXISTS idx_code_symbols_kind ON code_symbols(project, kind);
        CREATE INDEX IF NOT EXISTS idx_code_refs_project ON code_references(project);
        CREATE INDEX IF NOT EXISTS idx_code_refs_file ON code_references(file_id);
        CREATE INDEX IF NOT EXISTS idx_code_refs_from ON code_references(from_symbol_id);
        CREATE INDEX IF NOT EXISTS idx_code_refs_to ON code_references(to_symbol_id);
        CREATE INDEX IF NOT EXISTS idx_code_refs_to_name ON code_references(to_name);

        -- Schema version tracking
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied TEXT NOT NULL,
            description TEXT
        );

        -- Retrieval log for tracking fact usage
        CREATE TABLE IF NOT EXISTS retrieval_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id TEXT NOT NULL,
            project TEXT NOT NULL,
            query TEXT,
            search_type TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (fact_id) REFERENCES facts(id) ON DELETE CASCADE,
            FOREIGN KEY (project) REFERENCES projects(name)
        );
        CREATE INDEX IF NOT EXISTS idx_retrieval_log_fact ON retrieval_log(fact_id);
        CREATE INDEX IF NOT EXISTS idx_retrieval_log_project ON retrieval_log(project);

        -- Fact version history (audit trail for updates and deletes)
        CREATE TABLE IF NOT EXISTS facts_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id TEXT NOT NULL,
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            type TEXT NOT NULL,
            domain TEXT,
            tags TEXT,
            action TEXT NOT NULL CHECK(action IN ('update', 'delete')),
            changed_at TEXT NOT NULL,
            session_id TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_facts_history_fact ON facts_history(fact_id);
    """)

    # New columns on projects table (cross-instance coordination)
    for col, typedef in [
        ("last_decay", "TEXT"),
        ("last_consolidated", "TEXT"),
    ]:
        try:
            db.execute(f"ALTER TABLE projects ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Record current schema version
    try:
        existing = db.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current_version = existing[0] if existing and existing[0] else 0
        if current_version < 5:
            db.execute("""
                INSERT OR IGNORE INTO schema_version (version, applied, description)
                VALUES (5, ?, 'QA fixes: schema_version, retrieval_log, last_decay, last_consolidated')
            """, (datetime.now().isoformat(),))
    except Exception:
        pass  # Table may not exist yet (first migration)

    db.commit()


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

    # Migrate existing databases to V3 schema
    upgrade_schema(db)

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
