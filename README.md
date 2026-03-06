# 🧠 CogniLayer v4

### Stop re-explaining your codebase to AI.
**Infinite speed memory · Code graph · 200K+ tokens saved**

Without CogniLayer, your AI agent starts every session blind. It re-reads files, re-discovers architecture, re-learns decisions you explained last week. On a 50-file project, that's 80-100K tokens burned before real work begins.

With CogniLayer, it already knows. Three things your agent doesn't have today:

🔗 **Persistent knowledge across agents** - facts, decisions, error fixes, gotchas survive across sessions, crashes, and agents. Start in Claude Code, continue in Codex CLI - zero context loss

🔍 **Code intelligence** - who calls what, what depends on what, what breaks if you rename a function. Tree-sitter AST parsing across 10+ languages, not grep

🤖 **Subagent context compression** - research subagents write findings to DB instead of dumping 40K+ tokens into parent context. Parent gets a 500-token summary + on-demand `memory_search` retrieval

⚡ **80-200K+ tokens saved per session** - semantic search replaces file reads, subagent findings go to DB instead of context. Longer sessions with subagents save more

[![Version](https://img.shields.io/badge/version-4.2.0-orange.svg)](#)
[![License: Elastic-2.0](https://img.shields.io/badge/License-Elastic%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green.svg)](https://www.python.org/)
[![MCP Server](https://img.shields.io/badge/MCP-18%20tools-purple.svg)](https://modelcontextprotocol.io/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-supported-blueviolet.svg)](#)
[![Codex CLI](https://img.shields.io/badge/Codex%20CLI-supported-blueviolet.svg)](#)

---

## See the Difference

### Without CogniLayer

```
You: "Fix the login bug"

Claude: Let me read the project structure...
        Let me read src/auth/login.ts...
        Let me read src/auth/middleware.ts...
        Let me read src/config/database.ts...
        Let me understand your auth flow...
        (8 files read, 45K tokens burned, 2 minutes spent on orientation)

Claude: "Ok, I see the issue..."
```

### With CogniLayer

```
You: "Fix the login bug"

Claude: [memory_search → "login auth flow"] → 3 facts loaded (200 tokens)
        [code_context → "handleLogin"] → caller/callee map in 0.2s
        Already knows: Express + Passport, JWT in httpOnly cookies,
        last login bug was a race condition in session refresh (fixed 2 weeks ago)

Claude: "This looks like the same pattern as the session refresh issue
         from March 1st. The fix is..."
```

**That's not a small improvement. That's the difference between an agent that guesses and one that knows.**

---

## Real-World Examples

### Debugging: "Why is checkout failing?"

Without CogniLayer, Claude reads 15 files to understand your e-commerce flow. With it:

```
memory_search("checkout payment flow")
→ fact: "Stripe webhook hits /api/webhooks/stripe, validates signature
   with STRIPE_WEBHOOK_SECRET, then calls processOrder()"
→ gotcha: "Stripe sends webhooks with 5s timeout - processOrder must
   complete within 5s or webhook retries cause duplicate orders"
→ error_fix: "Fixed duplicate orders on 2026-02-20 by adding
   idempotency key check in processOrder()"

code_impact("processOrder")
→ depth 1: createOrderRecord, sendConfirmationEmail, updateInventory
→ depth 2: InventoryService.reserve, EmailQueue.push
→ "Changing processOrder will affect 6 functions across 4 files"
```

Claude already knows the architecture, the past bugs, **and** what will break if it touches the wrong thing. Instead of 15 file reads (~60K tokens), it uses **3 targeted queries (~800 tokens)**.

### Code Intelligence: "What happens if I change processOrder?"

Without CogniLayer, Claude greps for the function name and hopes for the best. With it:

```
code_context("processOrder")
→ definition: src/services/order.ts:42
→ incoming (who calls it): StripeWebhookHandler.handle, OrderController.retry,
   AdminPanel.reprocessOrder
→ outgoing (what it calls): createOrderRecord, sendConfirmationEmail,
   updateInventory, PaymentLog.write

code_impact("processOrder")
→ depth 1 (WILL BREAK):  StripeWebhookHandler, OrderController, AdminPanel
→ depth 2 (LIKELY AFFECTED): WebhookRouter, RetryQueue, AdminRoutes
→ depth 3 (NEED TESTING): 3 test files, 1 integration test
→ "Changing processOrder will affect 9 symbols across 7 files"
```

Before touching a single line, Claude knows the **full blast radius** - which files will break, which need testing, and which callers depend on the current behavior. No more surprise failures after a refactor.

### Refactoring: "Rename UserService to AccountService"

```
code_search("UserService")
→ class UserService in src/services/user.ts (line 14)
→ 12 references across 8 files

code_impact("UserService")
→ depth 1: AuthController, ProfileController, AdminPanel (WILL BREAK)
→ depth 2: LoginRoute, RegisterRoute, middleware/auth (LIKELY AFFECTED)
→ depth 3: 4 test files (NEED UPDATING)

memory_search("UserService")
→ decision: "UserService handles both auth and profile - planned split
   into AuthService + ProfileService (decided 2026-02-15, not yet done)"
```

Claude doesn't just find-and-replace. It knows there's a **planned split** and can suggest doing both changes at once - saving you a future refactoring session.

### New session after a crash: "What was I working on?"

```
[SessionStart hook fires automatically]
→ bridge loaded: "Progress: Migrated 3/5 API endpoints to v2 format.
   Done: /users, /products, /orders. Open: /payments, /shipping.
   Blocker: /payments needs Stripe SDK v12 upgrade first."

memory_search("stripe sdk upgrade")
→ gotcha: "Stripe SDK v12 changed webhook signature verification -
   verify() is now async, breaks all sync handlers"
```

Zero re-explanation. Claude picks up exactly where it left off, **including the blocker you hadn't mentioned yet**.

### Subagent research: "What MCP frameworks exist?"

Without CogniLayer, the subagent returns a 40K-token dump into parent context:

```
Parent (200K context):
  → spawn subagent: "Research community MCP servers"
  ← subagent returns: 40K tokens about 15 projects
  → all 40K crammed into parent context
  → remaining: 160K → next subagent → 120K → next → 80K...
```

With CogniLayer's Subagent Memory Protocol:

```
Parent (200K context):
  → spawn subagent: "Research MCP servers, save to memory"
  ← subagent writes details to DB, returns: "Saved 3 facts,
     search 'MCP server ecosystem'. Summary: Python dominates,
     FastMCP most popular, 3 architectural patterns."
  → parent context: ~500 tokens
  → need details? memory_search("MCP server ecosystem") → targeted pull
```

40K tokens compressed to 500. The findings persist in DB across sessions - not just for this conversation, but forever.

---

## Killer Features

| Feature | What it means |
|---------|--------------|
| **Code Intelligence** | `code_context` shows who calls what. `code_impact` maps blast radius before you touch anything. Powered by tree-sitter AST parsing |
| **Semantic Search** | Hybrid FTS5 + vector search finds the right fact even with different wording. Sub-millisecond response |
| **18 MCP Tools** | Memory, code analysis, safety, project context - Claude uses them automatically, no commands needed |
| **Token Savings** | 3 targeted queries (~800 tokens) replace 15 file reads (~60K tokens). Typical session saves 80-200K+ tokens |
| **Subagent Protocol** | Research subagents save findings to DB instead of flooding parent context. 40K → 500 tokens per subagent task |
| **Crash Recovery** | Session dies? Next one auto-recovers from the change log. Works across both agents |
| **Cross-Project Knowledge** | Solved a CORS issue in project A? Search it from project B. Your experience compounds |
| **14 Fact Types** | Not dumb notes - error_fix, gotcha, api_contract, decision, pattern, procedure, and more |
| **Heat Decay** | Hot facts surface first, cold facts fade. Each search hit boosts relevance |
| **Safety Gates** | Identity Card system blocks deploy to wrong server. Audit trail on every safety change |
| **Agent Interop** | Claude Code and Codex CLI share the same brain. Switch agents mid-task, zero context loss |
| **Session Bridges** | Every session starts with a summary of what happened last time |
| **TUI Dashboard** | Visual memory browser with 8 tabs - see everything at a glance |

---

## How It Works

```
You start a session
    ↓
SessionStart hook fires → injects project DNA, last session bridge, crash recovery
    ↓
You work normally - Claude saves facts, decisions, gotchas automatically via MCP tools
    ↓
You ask about code → code_context / code_impact answer in milliseconds from AST index
    ↓
Session ends (or crashes)
    ↓
Next session starts with full context - no re-reading, no re-explaining
```

**Zero effort after install.** No commands to learn, no workflow changes. CogniLayer runs in the background via hooks and MCP tools. Claude knows how to use it automatically.

---

## Quick Start

### 1. Install (30 seconds)

```bash
git clone https://github.com/LakyFx/CogniLayer.git
cd CogniLayer
python install.py
```

That's it. Next time you start Claude Code, CogniLayer is active.

### 2. Optional: Turbocharge search

```bash
# AI-powered vector search (recommended - finds facts even with different wording)
pip install fastembed sqlite-vec
```

### 3. Optional: Add Codex CLI support

```bash
python install.py --codex    # Codex CLI only
python install.py --both     # Claude Code + Codex CLI
```

### 4. Verify

```bash
python ~/.cognilayer/mcp-server/server.py --test
# → "OK: All 18 tools registered."
```

### Troubleshooting

MCP server not connecting? Run the diagnostic tool:
```bash
python diagnose.py          # Check everything
python diagnose.py --fix    # Check + auto-fix missing dependencies
```

### Requirements
- Python 3.11+
- Claude Code and/or Codex CLI
- pip packages: `mcp`, `pyyaml`, `textual` (installed automatically), `fastembed`, `sqlite-vec` (optional), `tree-sitter-language-pack` (optional, for code intelligence)

---

## Slash Commands (Claude Code only)

Once installed, use these in Claude Code:

| Command | What it does |
|---------|-------------|
| `/status` | Show memory stats and project health |
| `/recall [query]` | Search memory for specific knowledge |
| `/harvest` | Extract and save knowledge from current session |
| `/onboard` | Scan your project and build initial memory |
| `/onboard-all` | Batch onboard all projects in your workspace |
| `/forget [query]` | Delete specific facts from memory |
| `/identity` | Manage deployment Identity Card |
| `/consolidate` | Organize memory - cluster, detect contradictions, assign tiers |
| `/tui` | Launch the visual dashboard |
| `/cognihelp` | Show all available commands |

> **Codex CLI users:** Slash commands are not available in Codex. Instead, CogniLayer uses AGENTS.md instructions + MCP tools directly. See [Codex CLI Integration](#codex-cli-integration) below.

---

## TUI Dashboard

A visual memory browser right in your terminal. 8 tabs, keyboard navigation, works on Windows, Mac, and Linux.

```bash
cognilayer                    # All projects
cognilayer --project my-app   # Specific project
cognilayer --demo             # Demo mode with sample data (try it!)
```

### Overview - stats at a glance
![Overview](docs/screenshots/overview.jpg)

### Facts - searchable, filterable, color-coded by heat
![Facts](docs/screenshots/facts.jpg)

### Heatmap - see which knowledge is hot, warm, or cold
![Heatmap](docs/screenshots/heatmap.jpg)

### Clusters - related facts organized into groups
![Clusters](docs/screenshots/clusters.jpg)

### Timeline - full session history with outcomes
![Timeline](docs/screenshots/timeline.jpg)

*Screenshots show demo mode (`cognilayer --demo`) with sample data.*

---

## Upgrading

The upgrade is safe and non-destructive. Your memory is never lost:

```bash
git pull
python install.py
```

What happens under the hood:
- Code files are replaced with the latest versions
- `config.yaml` is **never overwritten** (your settings are safe)
- `memory.db` is **backed up automatically** before any migration
- Schema migration is **purely additive** (new columns/tables, never deletions)
- CLAUDE.md blocks update automatically on next session start

### Rollback

If something goes wrong:
```bash
# Your backup is timestamped
cp ~/.cognilayer/memory.db.backup-YYYYMMDD-HHMMSS ~/.cognilayer/memory.db
# Restore old code
git checkout <previous-commit> && python install.py
```

---

## Configuration

Edit `~/.cognilayer/config.yaml`:

```yaml
# Language - "en" (default) or "cs" (Czech)
language: "en"

# Your projects directory
projects:
  base_path: "~/projects"

# Indexer settings
indexer:
  scan_depth: 3
  chunk_max_chars: 2000

# Search defaults
search:
  default_limit: 5
  max_limit: 10
```

---

## Known Limitations

- **Concurrent CLIs**: Running Claude Code and Codex CLI simultaneously on the same project may cause session tracking conflicts. Use one CLI at a time per project.
- **Codex file tracking**: Codex CLI has no hooks, so automatic file change tracking is not available for Codex sessions.
- **Code intelligence**: Requires `tree-sitter-language-pack` (~20MB). Without it, all other 14 tools work normally.
- **TUI**: Requires `textual` package. Read-only except for resolving contradictions.

---

# Architecture (for the curious)

*Everything below is for developers who want to understand how CogniLayer works under the hood.*

## System Overview

```
Claude Code / Codex CLI Session
    │
    ├── SessionStart hook (Claude Code) / session_init tool (Codex)
    │   └── Injects Project DNA + last session bridge into CLAUDE.md
    │
    ├── MCP Server (18 tools)
    │   ├── memory_search    - Hybrid FTS5 + vector search with staleness detection
    │   ├── memory_write     - Store facts (14 types, deduplication, auto-embedding)
    │   ├── memory_delete    - Remove outdated facts by ID
    │   ├── memory_link      - Bidirectional Zettelkasten-style fact linking
    │   ├── memory_chain     - Causal chains (caused, led_to, blocked, fixed, broke)
    │   ├── file_search      - Search indexed project docs (chunked, not full files)
    │   ├── file_index       - Index project docs (README, configs, PRD) into file_chunks
    │   ├── project_context  - Get project DNA + health metrics
    │   ├── session_bridge   - Save/load session continuity summaries
    │   ├── session_init     - Initialize session for Codex CLI (replaces hooks)
    │   ├── decision_log     - Query append-only decision history
    │   ├── verify_identity  - Safety gate before deploy/SSH/push
    │   ├── identity_set     - Configure project Identity Card
    │   ├── recommend_tech   - Suggest tech stacks from similar projects
    │   ├── code_index       - Index codebase via tree-sitter AST parsing
    │   ├── code_search      - Find symbols (functions, classes, methods) by name
    │   ├── code_context     - 360° view: callers, callees, child methods
    │   └── code_impact      - Blast radius analysis (BFS traversal of references)
    │
    ├── PostToolUse hook (Claude Code only)
    │   └── Logs every file Write/Edit to changes table (<1ms overhead)
    │
    ├── PreCompact hook (Claude Code only)
    │   └── Saves comprehensive bridge before context compaction
    │
    └── SessionEnd hook / session_bridge(save)
        └── Closes session, builds emergency bridge if needed
```

## File Structure

```
~/.cognilayer/
├── memory.db              # SQLite (WAL mode, FTS5, 17 tables)
├── config.yaml            # Configuration (never overwritten by installer)
├── active_session.json    # Current session state (runtime)
├── mcp-server/
│   ├── server.py          # MCP entry point (18 tools)
│   ├── db.py              # Shared DB helper (WAL, busy_timeout, lazy vec loading)
│   ├── i18n.py            # Translations (EN + CS)
│   ├── init_db.py         # Schema creation + migration
│   ├── embedder.py        # fastembed wrapper (BAAI/bge-small-en-v1.5, 384-dim)
│   ├── register_codex.py  # Codex CLI config.toml registration
│   ├── indexer/           # File scanning and chunking
│   ├── search/            # FTS5 + vector hybrid search
│   ├── code/              # Code Intelligence (tree-sitter parsers, indexer, resolver)
│   └── tools/             # 18 MCP tool implementations
├── hooks/
│   ├── on_session_start.py    # Project detection, DNA injection, crash recovery
│   ├── on_session_end.py      # Session close, emergency bridge, episode building
│   ├── on_file_change.py      # PostToolUse file change logger + context monitoring
│   ├── on_pre_compact.py      # PreCompact bridge preservation
│   ├── generate_agents_md.py  # Codex AGENTS.md generator
│   └── register.py            # Claude Code settings.json registration
├── tui/                       # TUI Dashboard (Textual)
│   ├── app.py                 # Main application (8 tabs, keyboard nav)
│   ├── data.py                # Read-only SQLite data access layer
│   ├── styles.tcss            # CSS stylesheet
│   ├── screens/               # 8 tab screen modules
│   └── widgets/               # Heat cell, stats card widgets
└── logs/
    └── cognilayer.log
```

## Database Schema (17 tables)

| Table | Purpose |
|-------|---------|
| `projects` | Registered projects with auto-generated DNA |
| `facts` | 14 types of atomic knowledge units with heat scores |
| `facts_fts` | FTS5 fulltext index on facts |
| `file_chunks` | Indexed project documentation (PRDs, READMEs, configs) |
| `chunks_fts` | FTS5 fulltext index on chunks |
| `decisions` | Append-only decision log |
| `sessions` | Session records with bridges, episodes, and outcomes |
| `changes` | Automatic file change log (PostToolUse) |
| `project_identity` | Identity Card (SSH, ports, domains, safety locks) |
| `identity_audit_log` | Safety field change audit trail |
| `tech_templates` | Reusable tech stack templates |
| `fact_links` | Zettelkasten bidirectional links between facts |
| `knowledge_gaps` | Tracked weak/failed searches |
| `fact_clusters` | Memory consolidation output clusters |
| `contradictions` | Detected conflicting facts |
| `causal_chains` | Cause → effect relationship tracking |
| `retrieval_log` | Search quality tracking (queries, hit counts, latency) |
| `code_files` | Indexed source files with hash-based change detection |
| `code_symbols` | AST-parsed symbols (functions, classes, methods, interfaces) |
| `code_references` | Symbol cross-references (calls, imports, inheritance) |
| `facts_vec` / `chunks_vec` | Vector embeddings (sqlite-vec, optional) |

## Hybrid Search

Two search engines combined for maximum recall:

1. **FTS5** - SQLite fulltext search for exact keyword matching
2. **Vector embeddings** - [fastembed](https://github.com/qdrant/fastembed) (BAAI/bge-small-en-v1.5, 384-dim, CPU-only ONNX) with [sqlite-vec](https://github.com/asg017/sqlite-vec) for cosine similarity
3. **Hybrid ranker** - 40% FTS5 + 60% vector similarity, with heat score boosting

Vector search is optional - FTS5 works standalone without any extra dependencies.

## Heat Decay

Facts have a "temperature" that models relevance over time:

| Range | Label | Meaning |
|-------|-------|---------|
| 0.7 - 1.0 | **Hot** | Recently accessed, high relevance |
| 0.3 - 0.7 | **Warm** | Moderately recent |
| 0.05 - 0.3 | **Cold** | Old, rarely accessed |

Decay rates vary by fact type - `error_fix` and `gotcha` facts decay slower (they stay relevant longer) than `task` facts. Each search hit boosts a fact's heat score.

## Code Intelligence

Powered by [tree-sitter](https://tree-sitter.github.io/) AST parsing with language-pack support for 10+ languages:

| Tool | What it does |
|------|-------------|
| `code_index` | Scans project files, parses AST, extracts symbols and references into SQLite. Incremental - only re-indexes changed files |
| `code_search` | FTS5 search over symbol names. Find any function, class, or method by name or partial match |
| `code_context` | 360° view of a symbol: definition, who calls it (incoming), what it calls (outgoing), child methods |
| `code_impact` | Blast radius analysis - BFS traversal of incoming references. Shows what breaks at depth 1/2/3 |

Indexing runs with a configurable time budget (default 30s). Partial results are usable immediately. Unresolved references are re-resolved on the next incremental run.

## Subagent Memory Protocol

When Claude spawns research subagents, the raw findings can be 40K+ tokens. Without the protocol, all of that goes into the parent's context window. The Subagent Memory Protocol uses the CogniLayer database as a side channel:

```
Subagent                              Parent
   │                                     │
   ├── research (WebSearch, Read...)     │
   ├── synthesize findings               │
   ├── memory_write(consolidated facts)  │  ← data goes to DB, not context
   └── return: 500-token summary ────────┤  ← only summary enters context
                                         │
                        memory_search() ──┤  ← parent pulls details on demand
```

Key design decisions:
- **Synthesis over granularity** - subagents group related findings into cohesive facts, not one-per-discovery
- **Task-specific tags** - each subagent gets a unique tag (e.g. `tags="subagent,auth-review"`) for filtering via `memory_search(tags="auth-review")`
- **Keywords inside facts** - each fact ends with `Search: keyword1, keyword2` so retrieval works even after context compaction
- **Write-last pattern** - all `memory_write` calls happen as the last step before return, saving subagent turns and tokens
- **Foreground-first** - subagents launch as foreground (reliable MCP access), user can Ctrl+B to background
- **Graceful fallback** - if MCP tools are unavailable, findings go directly in return text

The protocol is injected into CLAUDE.md automatically and requires no user configuration.

## Codex CLI Integration

Codex CLI has no hook system, so CogniLayer adapts:

| Aspect | Claude Code | Codex CLI |
|--------|------------|-----------|
| Config | `~/.claude/settings.json` | `~/.codex/config.toml` |
| Hooks | SessionStart/End/PreCompact/PostToolUse | None - uses MCP tools + AGENTS.md instructions |
| Instructions | `CLAUDE.md` | `AGENTS.md` (generated by `generate_agents_md.py`) |
| Session init | Automatic via hook | `session_init` MCP tool called per AGENTS.md instructions |
| Onboarding | `/onboard` slash command | `file_index()` + `code_index()` MCP tools + AGENTS.md FIRST RUN instructions |
| File tracking | Automatic via PostToolUse | Not available (acceptable limitation) |

Same memory database shared between both CLIs.

### Codex onboarding workflow

AGENTS.md includes a FIRST RUN section that instructs Codex to:

1. `session_init()` - register project, load DNA + bridge
2. `file_index()` - index documentation files so `file_search` works
3. `code_index()` - index source code so `code_search/context/impact` work
4. Read key files and save findings via `memory_write()` (the AI does intelligent analysis)

This matches what `/onboard` does in Claude Code, but through AGENTS.md instructions instead of a slash command.

## Project Identity Card

Deployment safety system that prevents "oops, wrong server" incidents:

- **Safety locking** - locked fields require explicit update + audit log entry
- **Hash verification** - SHA-256 detects tampering of safety-critical fields
- **Required field checks** - `verify_identity` blocks deploy if critical fields are missing
- **Audit trail** - every safety field change is logged with timestamp and reason

---

## Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

## License

[Elastic License 2.0](LICENSE) - Free to use, modify, and distribute. You may not provide it as a managed/hosted service.
