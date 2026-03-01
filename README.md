# CogniLayer

**Persistent memory for Claude Code.** CogniLayer gives Claude Code a long-term memory that survives across sessions, projects, and crashes.

**Save ~80-100K tokens per session** — instead of re-reading files and re-discovering architecture from scratch, CogniLayer injects compact context in a few kilobytes.

Built as an [MCP server](https://modelcontextprotocol.io/) + hooks system that integrates directly into Claude Code's workflow.

## The Problem

Every time you start a new Claude Code session, it forgets everything. Your project's architecture, past decisions, deployment details, debugging insights — all gone. You waste tokens re-explaining the same context over and over.

## The Solution

CogniLayer automatically:
- **Remembers** facts, decisions, patterns, and gotchas across sessions
- **Detects staleness** — warns you when a remembered fact references a changed file
- **Bridges sessions** — summarizes what happened last time so the next session can pick up where you left off
- **Indexes your docs** — chunks PRDs, READMEs, and configs into searchable pieces
- **Guards deployments** — Identity Card system prevents deploying to the wrong server
- **Works across projects** — search knowledge from one project while working on another

## How It Works

```
Claude Code Session
    │
    ├── SessionStart hook
    │   └── Injects Project DNA + last session bridge into CLAUDE.md
    │
    ├── MCP Server (10 tools)
    │   ├── memory_search  — Find facts with staleness detection
    │   ├── memory_write   — Store facts (14 types, deduplication)
    │   ├── memory_delete  — Remove outdated facts
    │   ├── file_search    — Search indexed project docs
    │   ├── project_context — Get project DNA + stats
    │   ├── session_bridge — Save/load session continuity
    │   ├── decision_log   — Query past decisions
    │   ├── verify_identity — Safety gate before deploy/SSH/push
    │   ├── identity_set   — Configure project Identity Card
    │   └── recommend_tech — Suggest tech stacks from similar projects
    │
    ├── PostToolUse hook
    │   └── Logs every file Write/Edit (<1ms overhead)
    │
    └── SessionEnd hook
        └── Closes session, builds emergency bridge if needed
```

## Features

### 14 Fact Types
Not just dumb notes — structured knowledge:
`decision` `fact` `pattern` `issue` `task` `skill` `gotcha` `procedure` `error_fix` `command` `performance` `api_contract` `dependency` `client_rule`

### Staleness Detection
When you search memory, CogniLayer checks if the source file has changed since the fact was recorded. Changed facts are marked with `STALE` so you know to verify before acting.

### Session Bridges
Every session gets a summary — what was done, what's open, key decisions. The next session automatically gets this context injected into CLAUDE.md.

### Project Identity Card
Stores deployment configuration (SSH, ports, domains, PM2 processes) with:
- **Safety locking** — locked fields can't be changed without explicit update + audit log
- **Hash verification** — detects tampering of safety fields
- **Required field checks** — blocks deploy if critical fields are missing

### Crash Recovery
If a session crashes (kill, timeout, error), the next session detects the orphan and builds an emergency bridge from the change log.

### Hybrid Search (Phase 2)
- **FTS5** fulltext search for keyword matching
- **Vector embeddings** via [fastembed](https://github.com/qdrant/fastembed) (CPU-only, ONNX, no GPU needed)
- **sqlite-vec** for vector storage directly in SQLite
- Hybrid ranker combines both scores (40% FTS5 + 60% vector similarity)
- Finds semantically similar facts even when keywords don't match

### Heat Decay
Facts have a "temperature" that changes over time:
- **Hot** (0.7-1.0) — recently accessed, high relevance
- **Warm** (0.3-0.7) — moderately recent
- **Cold** (0.05-0.3) — old, rarely accessed
- Decay runs automatically on every search
- Accessed facts get a heat boost (+0.2)

### Zero Configuration
- No daemon, no server to run
- SQLite with WAL mode — zero setup, works everywhere
- Auto-detects project name, framework, tech stack from project files
- Phase 1 (FTS5 only) works with zero extra dependencies
- Phase 2 (hybrid search) needs: `pip install fastembed sqlite-vec`

## Installation

### Requirements
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+
- pip packages: `mcp` (required), `fastembed sqlite-vec` (optional, for vector search)

### Quick Install

```bash
# Clone the repo
git clone https://github.com/LakyFx/CogniLayer.git
cd CogniLayer

# Install
python install.py
```

The installer will:
1. Copy files to `~/.cognilayer/`
2. Copy slash commands to `~/.claude/commands/`
3. Initialize the SQLite database
4. Register MCP server and hooks in `~/.claude/settings.json`

### Manual Install

```bash
# Install dependency
pip install mcp

# Copy files
mkdir -p ~/.cognilayer/mcp-server ~/.cognilayer/hooks ~/.cognilayer/logs
cp -r mcp-server/* ~/.cognilayer/mcp-server/
cp -r hooks/* ~/.cognilayer/hooks/
cp config.yaml ~/.cognilayer/
cp -r commands/en/* ~/.claude/commands/  # or commands/cs/ for Czech

# Initialize database
cd ~/.cognilayer/mcp-server && python init_db.py

# Register in Claude Code
cd ~/.cognilayer/hooks && python register.py
```

### Verify Installation

```bash
# Test MCP server
python ~/.cognilayer/mcp-server/server.py --test
# Should output: "OK: All 10 tools registered."
```

## Usage

### Slash Commands

| Command | Description |
|---------|-------------|
| `/status` | Show memory stats and project context |
| `/recall [query]` | Search memory for specific knowledge |
| `/harvest` | Manually trigger knowledge extraction from current session |
| `/onboard` | Scan current project and build initial memory |
| `/onboard-all` | Batch onboard all projects in your workspace |
| `/forget [query]` | Delete specific facts from memory |
| `/identity` | Manage Project Identity Card (deploy config, safety) |

### Automatic Behavior

CogniLayer works automatically once installed:
- **Session start**: Injects project DNA and last session bridge into CLAUDE.md
- **During session**: Claude proactively saves important facts to memory
- **File changes**: Every Write/Edit is logged for crash recovery
- **Session end**: Closes session, builds emergency bridge if needed

### Example Workflow

```
# Start working on a project
cd ~/projects/my-app && claude

# Claude automatically knows:
# - Project DNA (Next.js 14, Tailwind, SQLite)
# - What happened last session
# - Past decisions and their reasons
# - Known gotchas and patterns

# Search memory explicitly
/recall authentication flow

# Check project status
/status

# Before deploying — safety check happens automatically
# Claude calls verify_identity() and shows you the target server
```

## Architecture

```
~/.cognilayer/
├── memory.db          # SQLite (WAL mode, FTS5, 11 tables)
├── config.yaml        # Configuration
├── active_session.json  # Current session state (runtime)
├── mcp-server/
│   ├── server.py      # MCP entry point (10 tools)
│   ├── db.py          # Shared DB helper
│   ├── init_db.py     # Schema creation
│   ├── indexer/       # File scanning and chunking
│   ├── search/        # FTS5 search helpers
│   └── tools/         # 10 MCP tool implementations
├── hooks/
│   ├── on_session_start.py
│   ├── on_session_end.py
│   ├── on_file_change.py
│   └── register.py
└── logs/
    └── cognilayer.log
```

### Database Schema (11 tables)

| Table | Purpose |
|-------|---------|
| `projects` | Registered projects with DNA |
| `facts` | 14 types of atomic knowledge units |
| `facts_fts` | FTS5 fulltext index on facts |
| `file_chunks` | Indexed project documentation |
| `chunks_fts` | FTS5 fulltext index on chunks |
| `decisions` | Append-only decision log |
| `sessions` | Session records with bridges |
| `changes` | Automatic file change log |
| `project_identity` | Identity Card (deploy, safety) |
| `identity_audit_log` | Safety field change history |
| `tech_templates` | Reusable tech stack templates |

## Configuration

Edit `~/.cognilayer/config.yaml`:

```yaml
# Language — "en" (default) or "cs" (Czech)
language: "en"

# Set your projects directory
projects:
  base_path: "~/projects"

# Adjust indexer settings
indexer:
  scan_depth: 3
  chunk_max_chars: 2000

# Search defaults
search:
  default_limit: 5
  max_limit: 10
```

### Language Support

CogniLayer supports English (`en`) and Czech (`cs`). Set the `language` field in `config.yaml` to switch. This affects:
- MCP tool descriptions and parameter hints
- All tool output messages (errors, confirmations, warnings)
- CLAUDE.md auto-generated instructions
- Slash command prompts (`/status`, `/recall`, etc.)

After changing the language, re-run `python install.py` to update slash commands.

## Roadmap

### Phase 1 (Complete)
- SQLite + FTS5 fulltext search
- 10 MCP tools, 3 hooks, 7 slash commands
- Session bridges and crash recovery
- Identity Card with safety locking

### Phase 2 (Complete)
- Vector embeddings via [fastembed](https://github.com/qdrant/fastembed) (CPU-only, ONNX)
- [sqlite-vec](https://github.com/asg017/sqlite-vec) for vector storage
- Hybrid search (FTS5 + vector ranking with configurable weights)
- Heat decay (temporal aging: hot/warm/cold)
- Backfill script for embedding existing facts/chunks

### Phase 3 (Ideas)
- Web UI dashboard for memory browsing
- Multi-user support
- Export/import memory between machines
- Custom embedding models

## Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

## License

[GPL-3.0](LICENSE)
