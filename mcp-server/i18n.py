"""CogniLayer i18n — lightweight translation layer.

Loaded once at import time. All translations are in-memory Python dicts.
No external dependencies beyond PyYAML. Uses str.format() for variable interpolation.
"""

import yaml
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"

# --- Load language from config ---

def _load_language() -> str:
    config_path = COGNILAYER_HOME / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            return cfg.get("language", "en")
        except Exception:
            pass
    return "en"


_language = _load_language()


# --- Translations ---

_EN: dict[str, str] = {
    # ======================================================================
    # server.py — tool descriptions
    # ======================================================================
    "tool.memory_search.desc": (
        "Search CogniLayer memory. Finds relevant information "
        "from past sessions, decisions, patterns and facts. "
        "Automatically detects STALE facts (source_file changed)."
    ),
    "tool.memory_search.param.query": "What to search for. Natural language.",
    "tool.memory_search.param.scope": "project (default) | all | {project_name}",
    "tool.memory_search.param.type": (
        "Fact type: decision|fact|pattern|issue|task|skill|gotcha|"
        "procedure|error_fix|command|performance|api_contract|dependency|client_rule"
    ),
    "tool.memory_search.param.tags": "Filter by tags (e.g. 'subagent' or 'subagent,auth-review'). All specified tags must match.",
    "tool.memory_search.param.limit": "Max results (default 5, max 10)",

    "tool.memory_write.desc": (
        "Save important information to CogniLayer memory. "
        "Use PROACTIVELY — save as you learn, not just during /harvest. "
        "Updates are versioned — previous content is saved to facts_history."
    ),
    "tool.memory_write.param.content": "What to remember. Must be self-contained.",
    "tool.memory_write.param.type": (
        "Type: fact|decision|pattern|issue|task|skill|gotcha|"
        "procedure|error_fix|command|performance|api_contract|dependency|client_rule"
    ),
    "tool.memory_write.param.tags": "Tags separated by comma.",
    "tool.memory_write.param.domain": "Domain: auth, ui, deploy, seo...",
    "tool.memory_write.param.source_file": "Relative path to the file where the fact was observed.",

    "tool.memory_delete.desc": "Delete facts from CogniLayer memory by ID. Previous content is saved to facts_history for undo.",
    "tool.memory_delete.param.ids": "UUIDs of facts to delete.",

    "tool.file_search.desc": (
        "Search indexed project files (PRD, handoff, docs). "
        "Returns relevant sections/chunks INSTEAD of whole files — saves context."
    ),
    "tool.file_search.param.query": "What to search for in project files.",
    "tool.file_search.param.scope": "project (default) | {project_name}",
    "tool.file_search.param.file_filter": "Glob pattern, e.g. *.md or PRD*",
    "tool.file_search.param.limit": "Max chunks (default 5, max 10)",

    "tool.project_context.desc": "Return Project DNA and current context for the detected project.",

    "tool.session_bridge.desc": "Load or save session bridge (session summary for continuity).",
    "tool.session_bridge.param.action": "load | save",
    "tool.session_bridge.param.content": "Bridge content (for save only).",

    "tool.decision_log.desc": "Search decision log for current or specified project.",
    "tool.decision_log.param.query": "Filter. Empty = latest decisions.",
    "tool.decision_log.param.project": "Specific project. Default: current.",
    "tool.decision_log.param.limit": "Number of results (default 5).",

    "tool.verify_identity.desc": (
        "MANDATORY before any deploy, SSH, push, PM2, DB migration. "
        "Verifies Identity Card and returns VERIFIED/BLOCKED/WARNING."
    ),
    "tool.verify_identity.param.action_type": (
        "deploy|ssh|push|pm2|db-migrate|docker-remote|proxy-reload|service-mgmt"
    ),

    "tool.identity_set.desc": "Set Project Identity Card fields.",
    "tool.identity_set.param.fields": (
        'Keys and values to set. E.g.: {{"deploy_ssh_alias": "my-server", "deploy_app_port": 3000}}'
    ),
    "tool.identity_set.param.lock_safety": "Lock safety fields?",

    "tool.recommend_tech.desc": "Recommend tech stack based on similar projects.",
    "tool.recommend_tech.param.description": "Project description (simple website, SaaS...)",
    "tool.recommend_tech.param.similar_to": "Name of existing project for inspiration.",
    "tool.recommend_tech.param.category": "saas-app|agency-site|simple-website|ecommerce|api|cli-tool",

    # ======================================================================
    # server.py — error messages
    # ======================================================================
    "server.unknown_tool": "Unknown tool: {name}",
    "server.tool_error": "Error in {name}: {error}",

    # ======================================================================
    # memory_search.py
    # ======================================================================
    "memory_search.no_results": (
        "No results for '{query}'. Memory is empty or query does not match any facts."
    ),
    "memory_search.header": "## Found {count} results for '{query}'\n",
    "memory_search.stale": "STALE — source file {source_file} changed since this fact was recorded!",
    "memory_search.stale_hint": "-> VERIFY before using: Read {source_file}",
    "memory_search.deleted": "DELETED — source file {source_file} was deleted!",
    "memory_search.cross_project": "CROSS-PROJECT — from project {project}",
    "memory_search.linked_fact": "[{id}] {preview}",

    # ======================================================================
    # memory_write.py
    # ======================================================================
    "memory_write.exists_unchanged": "Fact already exists (unchanged): {preview}...",
    "memory_write.updated": "Updated in memory: {preview}... [project: {project}, type: {type}]",
    "memory_write.saved": "Saved to memory: {preview}... [project: {project}, type: {type}]",
    "memory_write.failed_locked": "FAILED to save — database locked/busy, data was NOT persisted: {preview}... Include this content in your return text as fallback.",
    "memory_write.blocked_secret": (
        "BLOCKED — Content appears to contain a secret ({secret_type}). "
        "Secrets must NEVER be saved to memory. Remove the sensitive data and try again."
    ),

    # ======================================================================
    # memory_delete.py
    # ======================================================================
    "memory_delete.no_ids": "No IDs to delete.",
    "memory_delete.deleted": "Deleted {deleted} facts from memory.",

    # ======================================================================
    # memory_link.py
    # ======================================================================
    "tool.memory_link.desc": "Manually link two facts in CogniLayer memory.",
    "tool.memory_link.param.source_id": "UUID of the source fact.",
    "tool.memory_link.param.target_id": "UUID of the target fact.",
    "memory_link.not_found": "Fact not found: {id}",
    "memory_link.already_linked": "Already linked: '{source}' <-> '{target}'",
    "memory_link.linked": "Linked: '{source}' <-> '{target}'",
    "memory_link.self_link": "Cannot link a fact to itself.",

    # ======================================================================
    # file_search.py
    # ======================================================================
    "file_search.no_results": "No results found for '{query}'.",
    "file_search.not_indexed": "No results found for '{query}'.\nNote: No documents indexed for this project yet. Run file_index() to index project docs (PRD, README, configs).",
    "file_search.header": "## Found {count} chunks for '{query}'\n",
    "file_search.no_title": "(no heading)",
    "file_search.section_label": "section",

    # ======================================================================
    # project_context.py
    # ======================================================================
    "project_context.no_project": "No active project. Run claude in a project directory.",
    "project_context.not_registered": "Project '{project}' is not registered in CogniLayer.",
    "project_context.dna_placeholder": "## Project DNA: {project}\n[DNA not yet generated]",
    "project_context.stats": (
        "\n## Statistics\n"
        "- Facts in memory: {facts_count} (hot: {hot_count})\n"
        "- Indexed chunks: {chunks_count}\n"
        "- Sessions: {sessions_count}\n"
        "- Recorded changes: {changes_count}"
    ),
    "project_context.health_header": "\n## Memory Health\n",
    "project_context.health_stats": "- Total: {total} | Hot: {hot} | Warm: {warm} | Cold: {cold}",
    "project_context.most_retrieved": "- Most retrieved: \"{content}\" ({count}x)",
    "project_context.never_retrieved": "- Never retrieved: {count} facts",
    "project_context.gaps_header": "## Knowledge Gaps (unresolved)",
    "project_context.gaps_item": "- \"{query}\" (asked {times}x)",
    "project_context.no_gaps": "## Knowledge Gaps\nNo unresolved gaps.",
    "project_context.avg_retrievals": "- Avg retrievals/fact: {avg:.1f}",

    # ======================================================================
    # session_bridge.py
    # ======================================================================
    "session_bridge.no_bridge": "No session bridge available.",
    "session_bridge.missing_content": "Missing bridge content to save.",
    "session_bridge.no_session": "No active session.",
    "session_bridge.saved": "Session bridge saved.",
    "session_bridge.unknown_action": "Unknown action: {action}. Use 'load' or 'save'.",

    # ======================================================================
    # decision_log.py
    # ======================================================================
    "decision_log.no_decisions": "No decisions{search_info} in project {project}.",
    "decision_log.search_info": " for '{query}'",
    "decision_log.header": "## Decisions for {project}\n",
    "decision_log.reason_label": "Reason: ",
    "decision_log.alternatives_label": "Alternatives: ",

    # ======================================================================
    # verify_identity.py
    # ======================================================================
    "verify_identity.blocked_no_project": "BLOCKED — No active project.",
    "verify_identity.blocked_unknown_action": (
        "BLOCKED — Unknown action_type: {action_type}. Allowed: {allowed}"
    ),
    "verify_identity.not_set": "[NOT SET]",
    "verify_identity.blocked_no_identity": (
        "BLOCKED — Project '{project}' has no Identity Card.\n"
        "Missing safety fields for '{action_type}':\n{missing}\n\n"
        "ASK the user for these values.\n"
        "Use /identity set to configure."
    ),
    "verify_identity.blocked_missing_fields": (
        "BLOCKED — Missing safety fields for '{action_type}':\n{missing}\n\n"
        "ASK the user for these values.\n"
        "Use /identity set to configure."
    ),
    "verify_identity.warning_unlocked": (
        "WARNING — Identity fields exist but are NOT LOCKED.\n\n"
        "Current values:\n{fields}\n\n"
        "Present values to the user and request explicit confirmation.\n"
        "To lock: /identity lock"
    ),
    "verify_identity.blocked_tampered": (
        "BLOCKED — Safety fields were changed outside /identity update!\n"
        "Hash mismatch: expected {expected}, got {actual}\n"
        "Use /identity lock to re-lock."
    ),
    "verify_identity.verified": (
        "VERIFIED — Project: {project}\n"
        "Server: {ssh_alias} ({ssh_host})\n"
        "App Port: {app_port}\n"
        "Deploy Path: {deploy_path}\n"
        "PM2: {pm2_name} (id={pm2_id})\n"
        "Domain: {domain}\n"
        "Method: {method}\n"
        "Git Branch: {branch}\n\n"
        "CONFIRM with user: 'Will {action_type} on {ssh_alias} for {domain}.'"
    ),

    # ======================================================================
    # identity_set.py
    # ======================================================================
    "identity_set.no_project": "No active project.",
    "identity_set.unknown_fields": "Unknown fields: {invalid}. Allowed: {allowed}",
    "identity_set.blocked_locked": (
        "BLOCKED — Safety fields are locked.\n"
        "Attempted change: {changes}\n"
        "Use /identity update to change locked fields."
    ),
    "identity_set.updated": "Identity Card updated for {project}:",
    "identity_set.safety_locked": "locked",
    "identity_set.safety_unlocked": "unlocked",
    "identity_set.safety_status": "Safety fields: {status}",

    # ======================================================================
    # recommend_tech.py
    # ======================================================================
    "recommend_tech.header": "## Tech recommendation\n",
    "recommend_tech.based_on_project": "Based on project: {project}\n",
    "recommend_tech.recommended_stack": "Recommended stack:",
    "recommend_tech.apply_hint": "To apply: /identity tech-from {project}",
    "recommend_tech.no_identity": "Project '{project}' has no Identity Card.",
    "recommend_tech.no_projects": (
        "No projects with Identity Card in database. Use /onboard to register projects."
    ),
    "recommend_tech.based_on_desc": "Based on description: {description}\n",
    "recommend_tech.similar_projects": "Similar projects in portfolio:",
    "recommend_tech.apply_stack_hint": "To apply stack: /identity tech-from <project-name>",
    "recommend_tech.edit_hint": "To edit: /identity set framework=... css_approach=...",

    # ======================================================================
    # hooks/on_session_start.py
    # ======================================================================
    "claude_md.template": (
        "## CogniLayer v4 Active\n"
        "Persistent memory + code intelligence is ON.\n"
        "ON FIRST USER MESSAGE in this session, briefly tell the user:\n"
        "  'CogniLayer v4 active — persistent memory is on. Type /cognihelp for available commands.'\n"
        "Say it ONCE, keep it short, then continue with their request.\n"
        "\n"
        "## Tools — HOW TO WORK\n"
        "\n"
        "FIRST RUN ON A PROJECT:\n"
        'When DNA shows "[new session]" or "[first session]":\n'
        "1. Run /onboard — indexes project docs (PRD, README), builds initial memory\n"
        "2. Run code_index() — builds AST index for code intelligence\n"
        "Both are one-time. After that, updates are incremental.\n"
        "If file_search or code_search return empty → these haven't been run yet.\n"
        "\n"
        "UNDERSTAND FIRST (before making changes):\n"
        "- memory_search(query) → what do we know? Past bugs, decisions, gotchas\n"
        "- code_context(symbol) → how does the code work? Callers, callees, dependencies\n"
        "- file_search(query) → search project docs (PRD, README) without reading full files\n"
        "- code_search(query) → find where a function/class is defined\n"
        "Use BOTH memory + code tools for complete picture. They are fast — call in parallel.\n"
        "\n"
        "BEFORE RISKY CHANGES (mandatory):\n"
        "- Renaming, deleting, or moving a function/class → code_impact(symbol) FIRST\n"
        "- Changing a function's signature or return value → code_impact(symbol) FIRST\n"
        "- Modifying shared utilities used across multiple files → code_impact(symbol) FIRST\n"
        "- ALSO: memory_search(symbol) → check for related decisions or known gotchas\n"
        "Both required. Structure tells you what breaks, memory tells you WHY it was built that way.\n"
        "\n"
        "AFTER COMPLETING WORK:\n"
        "- memory_write(content) → save important discoveries immediately\n"
        "  (error_fix, gotcha, pattern, api_contract, procedure, decision)\n"
        '- session_bridge(action="save", content="Progress: ...; Open: ...")\n'
        "DO NOT wait for /harvest — session may crash.\n"
        "\n"
        "SUBAGENT MEMORY PROTOCOL:\n"
        "When spawning Agent tool for research or exploration:\n"
        "- Include in prompt: synthesize findings into consolidated memory_write(content, type, tags=\"subagent,<task-topic>\") facts\n"
        "  Assign a descriptive topic tag per subagent (e.g. tags=\"subagent,auth-review\", tags=\"subagent,perf-analysis\")\n"
        "- Do NOT write each discovery separately — group related findings into cohesive facts\n"
        "- Write to memory as the LAST step before return, not incrementally — saves turns and tokens\n"
        "- Each fact must be self-contained with specific details (file paths, values, code snippets)\n"
        "- When findings relate to specific files, include domain and source_file for better search and staleness detection\n"
        "- End each fact with 'Search: keyword1, keyword2' — keywords INSIDE the fact survive context compaction\n"
        "- Record significant negative findings too (e.g. 'no rate limiting exists in src/api/' — prevents repeat searches)\n"
        "- Return: actionable summary (file paths, function names, specific values) + what was saved + keywords for memory_search\n"
        "- If MCP tools unavailable or fail → include key findings directly in return text as fallback\n"
        "- Launch subagents as foreground (default) for reliable MCP access — user can Ctrl+B to background later\n"
        "Why: without this protocol, subagent returns dump all text into parent context (40K+ tokens).\n"
        "With protocol, findings go to DB and parent gets ~500 token summary + on-demand memory_search.\n"
        "\n"
        "BEFORE DEPLOY/PUSH:\n"
        '- verify_identity(action_type="...") → mandatory safety gate\n'
        "- If BLOCKED → STOP and ask the user\n"
        "- If VERIFIED → READ the target server to the user and request confirmation\n"
        "\n"
        "## VERIFY-BEFORE-ACT\n"
        "When memory_search returns a fact marked ⚠ STALE:\n"
        "1. Read the source file and verify the fact still holds\n"
        "2. If changed → update via memory_write\n"
        "3. NEVER act on STALE facts without verification\n"
        "\n"
        "## Process Management (Windows)\n"
        "- NEVER use `taskkill //F //IM node.exe` — kills ALL Node.js INCLUDING Claude Code CLI!\n"
        "- Use: `npx kill-port PORT` or find PID via `netstat -ano | findstr :PORT` then `taskkill //F //PID XXXX`\n"
        "\n"
        "## Git Rules\n"
        '- Commit often, small atomic changes. Format: "[type] what and why"\n'
        "- commit = Tier 1 (do it yourself). push = Tier 3 (verify_identity)."
    ),

    "claude_md.do_not_delete": "auto-generated, do not delete",

    "crash.session_summary": "[CRASH] Session was not properly closed",
    "crash.recovery": (
        "## Crash Recovery\n"
        "Last session ({start_time}) was not properly closed (crash/kill).\n"
        "Recorded {changes} file changes before crash.\n"
        "Last changed files: {last_files}\n"
        "Bridge from previous session is valid (above).\n"
        'For details use: memory_search("changes last session")'
    ),
    "crash.no_files": "none",

    "dna.unknown_stack": "unknown",
    "dna.unknown_style": "[unknown]",
    "dna.deploy_not_set": "[NOT SET]",
    "dna.new_session": "[new session]",
    "dna.first_session": "[first session]",
    "dna.not_generated": "[DNA not yet generated]",

    # ======================================================================
    # memory_chain.py
    # ======================================================================
    "tool.memory_chain.desc": (
        "Create a causal chain link between two facts. "
        "Tracks cause->effect relationships (caused, led_to, blocked, fixed, broke)."
    ),
    "tool.memory_chain.param.cause_id": "UUID of the cause fact.",
    "tool.memory_chain.param.effect_id": "UUID of the effect fact.",
    "tool.memory_chain.param.relationship": (
        "Relationship type: caused|led_to|blocked|fixed|broke (default: caused)"
    ),
    "memory_chain.self_chain": "Cannot create a causal chain from a fact to itself.",
    "memory_chain.invalid_relationship": (
        "Invalid relationship '{relationship}'. Valid: {valid}"
    ),
    "memory_chain.not_found": "Fact not found: {id}",
    "memory_chain.cross_project": (
        "Cannot link facts across projects: {cause_project} != {effect_project}"
    ),
    "memory_chain.already_exists": (
        "Causal chain already exists: '{cause}' -> '{effect}'"
    ),
    "memory_chain.created": (
        "Causal chain created: '{cause}' --[{relationship}]--> '{effect}'"
    ),

    # ======================================================================
    # memory_search.py — causal chain display
    # ======================================================================
    "memory_search.chain_caused": "{relationship}: [{id}] {preview}",
    "memory_search.chain_caused_by": "{relationship} by: [{id}] {preview}",

    # ======================================================================
    # project_context.py — episodes + organization
    # ======================================================================
    "project_context.episodes_header": "## Recent Episodes",
    "project_context.episodes_item": "- [{outcome}] \"{title}\" ({date})",
    "project_context.org_header": "## Memory Organization",
    "project_context.org_stats": (
        "- Clusters: {clusters} | Active: {active} | Reference: {reference} | Archive: {archive}"
    ),
    "project_context.org_contradictions": "- Contradictions: {count} unresolved",

    # ======================================================================
    # consolidate.py
    # ======================================================================
    "consolidate.no_project": "No active project. Specify project name or run in a project directory.",
    "consolidate.report": (
        "## Consolidation Report for {project}\n"
        "- Clusters found: {clusters} ({labeled} labeled)\n"
        "- Tiers: Active={active} | Reference={reference} | Archive={archive}\n"
        "- New contradictions detected: {contradictions}"
    ),
    "consolidate.stale_contradiction": (
        "Same file '{file}' has multiple {type} facts with different mtimes (one may be stale)"
    ),
    "consolidate.age_contradiction": (
        "Same domain '{domain}' has {type} facts >30 days apart (may be outdated)"
    ),

    # ======================================================================
    # hooks/on_session_end.py
    # ======================================================================
    "session_end.emergency_header": "[Emergency bridge — running bridge was not updated]",
    "session_end.and_more": "  ... and {count} more",
    "session_end.no_changes": "No changes or facts in this session.",

    # ======================================================================
    # session_init.py (Codex MCP tool)
    # ======================================================================
    "tool.session_init.desc": (
        "Initialize CogniLayer session (for Codex CLI ONLY — Claude Code uses hooks instead, "
        "do NOT call this if you already have CogniLayer context in CLAUDE.md). "
        "Returns DNA + bridge + crash recovery."
    ),
    "tool.session_init.param.project_path": (
        "Path to the project directory. Auto-detects from CWD if not provided."
    ),
    "session_init.no_db": "CogniLayer DB not found. Run install first.",
    "session_init.invalid_path": "Invalid project path: {path}",
    "session_init.error": "Session init error: {error}",
    "session_init.header": "## Session initialized for {project}\nSession ID: {session_id}",
    "session_init.instructions": (
        "## Reminders\n"
        "- Use memory_write proactively to save findings\n"
        "- At session end: session_bridge(action=\"save\", content=\"Progress: ...; Open: ...\")\n"
        "- Before deploy/push: verify_identity(action_type=\"...\")"
    ),

    # ======================================================================
    # File indexing (file_index)
    # ======================================================================
    "tool.file_index.desc": (
        "Index project documentation files (README, configs, PRD, YAML, JSON, TOML) "
        "into file_chunks so that file_search() returns results. "
        "Run once per project. Incremental — only re-indexes changed files."
    ),
    "tool.file_index.param.project_path": "Override project path. Default: detected from session.",
    "tool.file_index.param.full": "Force full re-index (clear all chunks first). Default: false (incremental).",
    "tool.file_index.param.time_budget": "Max seconds for indexing (default 30). Partial results returned on timeout.",
    "file_index.no_path": "Cannot determine project path. Provide project_path or run session_init first.",
    "file_index.invalid_path": "Invalid project path: {path}",
    "file_index.error": "File indexing failed: {error}",
    "file_index.success": (
        "File indexing complete for '{project}'.\n"
        "  Files indexed this run: {indexed}\n"
        "  Total indexed files: {total_files}\n"
        "  Total chunks: {total_chunks}\n"
        "  Indexable files found: {available}\n"
        "file_search() is now ready."
    ),

    # ======================================================================
    # Code Intelligence tools (code_index, code_search, code_context, code_impact)
    # ======================================================================
    "tool.code_index.desc": (
        "Index project source code (tree-sitter AST → symbols + references into SQLite). "
        "Enables code_context, code_impact, and code_search. Incremental by default."
    ),
    "tool.code_index.param.project_path": "Override project path. Default: detected from session.",
    "tool.code_index.param.full": "Force full re-index (ignore cache). Default: false (incremental).",
    "tool.code_index.param.time_budget": "Max seconds for indexing (default 30). Partial results returned on timeout.",

    "tool.code_search.desc": (
        "Search code symbols (functions, classes, methods, interfaces) by name or signature. "
        "Uses FTS5 fulltext. Requires code_index to be run first."
    ),
    "tool.code_search.param.query": "Search query — symbol name, partial name, or keyword.",
    "tool.code_search.param.kind": "Filter by kind: function|class|method|interface|variable|type_alias|enum",
    "tool.code_search.param.limit": "Max results (default 20, max 50).",

    "tool.code_context.desc": (
        "360° view of a code symbol: definition, who calls it (incoming), "
        "what it calls (outgoing), children (methods). Requires code_index."
    ),
    "tool.code_context.param.symbol": "Symbol name or qualified name (e.g. 'open_db' or 'MyClass.method').",
    "tool.code_context.param.project_name": "Override project. Default: current.",

    "tool.code_impact.desc": (
        "Blast radius analysis — BFS traversal of incoming references to find "
        "everything affected by changing a symbol. Requires code_index."
    ),
    "tool.code_impact.param.symbol": "Symbol to analyze impact for.",
    "tool.code_impact.param.max_depth": "Max BFS depth (1-5, default 3).",
    "tool.code_impact.param.project_name": "Override project. Default: current.",

    # Code Intelligence result messages
    "code.no_treesitter": (
        "tree-sitter-language-pack is not installed. "
        "Run: pip install tree-sitter-language-pack"
    ),
    "code.no_project": "No active project. Run Claude in a project directory.",
    "code.not_indexed": (
        "Project '{project}' has no code index yet. "
        "Run code_index first to build the symbol database."
    ),
    "code.db_busy": "Database is busy (another process holds the lock). Try again in a moment.",
    "code.db_error": "Database error: {error}",
    "code.generic_error": "Code intelligence error: {error}",

    # code_index results
    "code.index_header": "## Code Index: {project}",
    "code.index_partial": (
        "Indexing interrupted after {elapsed}s — partial result. "
        "Run code_index again to continue."
    ),
    "code.index_complete": "Indexing completed in {elapsed}s.",
    "code.index_stats": (
        "- Files scanned: {files_total}\n"
        "- Files indexed: {files_indexed} (skipped: {files_skipped})\n"
        "- Symbols extracted: {symbols}\n"
        "- References found: {references}\n"
        "- References resolved: {resolved}"
    ),
    "code.index_errors": "Errors ({count}):",
    "code.index_db_totals": "- **Total in index**: {symbols} symbols, {references} references",

    # code_search results
    "code.search_header": "## Found {count} symbols for '{query}'",
    "code.search_no_results": "No symbols found for '{query}'.",

    # code_context results
    "code.context_header": "## Symbol: {symbol}",
    "code.context_incoming": "### Incoming references ({count}):",
    "code.context_no_incoming": "### Incoming references: none",
    "code.context_outgoing": "### Outgoing references ({count}):",
    "code.context_no_outgoing": "### Outgoing references: none",
    "code.context_children": "### Children ({count}):",
    "code.symbol_not_found": "Symbol '{symbol}' not found in code index.",

    # code_impact results
    "code.impact_header": (
        "## Impact Analysis: {symbol}\n"
        "**Affected:** {total} symbols in {files} files"
    ),
    "code.impact_no_refs": "No incoming references found — this symbol is not referenced by other code.",
    "code.impact_depth": "### Depth {depth} ({count} symbols):",
    "code.impact_files": "### Affected files:",
    "code.impact_timeout": "Analysis timed out after {elapsed}s — results may be incomplete.",
}


_CS: dict[str, str] = {
    # ======================================================================
    # server.py — tool descriptions
    # ======================================================================
    "tool.memory_search.desc": (
        "Prohledej CogniLayer pamet. Najde relevantni informace "
        "z minulych sessions, rozhodnuti, patterns a faktu. "
        "Automaticky detekuje STALE fakty (source_file se zmenil)."
    ),
    "tool.memory_search.param.query": "Co hledas. Prirozeny jazyk.",
    "tool.memory_search.param.scope": "project (default) | all | {project_name}",
    "tool.memory_search.param.type": (
        "Typ faktu: decision|fact|pattern|issue|task|skill|gotcha|"
        "procedure|error_fix|command|performance|api_contract|dependency|client_rule"
    ),
    "tool.memory_search.param.tags": "Filtr podle tagu (napr. 'subagent' nebo 'subagent,auth-review'). Vsechny zadane tagy musi odpovidat.",
    "tool.memory_search.param.limit": "Max pocet vysledku (default 5, max 10)",

    "tool.memory_write.desc": (
        "Uloz dulezitou informaci do CogniLayer pameti. "
        "Pouzivej PROAKTIVNE — ukladej jak se ucis, ne jen pri /harvest. "
        "Aktualizace jsou verzovane — predchozi obsah se uklada do facts_history."
    ),
    "tool.memory_write.param.content": "Co si zapamatovat. Musi byt self-contained.",
    "tool.memory_write.param.type": (
        "Typ: fact|decision|pattern|issue|task|skill|gotcha|"
        "procedure|error_fix|command|performance|api_contract|dependency|client_rule"
    ),
    "tool.memory_write.param.tags": "Tagy oddelene carkou.",
    "tool.memory_write.param.domain": "Oblast: auth, ui, deploy, seo...",
    "tool.memory_write.param.source_file": "Relativni cesta k souboru kde byl fakt pozorovan.",

    "tool.memory_delete.desc": "Smaz fakty z CogniLayer pameti podle ID. Predchozi obsah se uklada do facts_history pro undo.",
    "tool.memory_delete.param.ids": "UUID faktu ke smazani.",

    "tool.file_search.desc": (
        "Prohledej indexovane projektove soubory (PRD, handoff, docs). "
        "Vraci relevantni sekce/chunky MISTO celych souboru — setri kontext."
    ),
    "tool.file_search.param.query": "Co hledas v projektovych souborech.",
    "tool.file_search.param.scope": "project (default) | {project_name}",
    "tool.file_search.param.file_filter": "Glob pattern, napr. *.md nebo PRD*",
    "tool.file_search.param.limit": "Max pocet chunku (default 5, max 10)",

    "tool.project_context.desc": "Vrati Project DNA a aktualni kontext pro detekovany projekt.",

    "tool.session_bridge.desc": "Nacti nebo uloz session bridge (shrnuti session pro kontinuitu).",
    "tool.session_bridge.param.action": "load | save",
    "tool.session_bridge.param.content": "Obsah bridge (pouze pro save).",

    "tool.decision_log.desc": "Prohledej log rozhodnuti pro aktualni nebo specifikovany projekt.",
    "tool.decision_log.param.query": "Filtr. Prazdne = posledni rozhodnuti.",
    "tool.decision_log.param.project": "Konkretni projekt. Default: aktualni.",
    "tool.decision_log.param.limit": "Pocet vysledku (default 5).",

    "tool.verify_identity.desc": (
        "POVINNE pred jakymkoliv deployem, SSH, push, PM2, DB migraci. "
        "Overi Identity Card a vrati VERIFIED/BLOCKED/WARNING."
    ),
    "tool.verify_identity.param.action_type": (
        "deploy|ssh|push|pm2|db-migrate|docker-remote|proxy-reload|service-mgmt"
    ),

    "tool.identity_set.desc": "Nastav pole Project Identity Card.",
    "tool.identity_set.param.fields": (
        'Klice a hodnoty k nastaveni. Napr: {{"deploy_ssh_alias": "my-server", "deploy_app_port": 3000}}'
    ),
    "tool.identity_set.param.lock_safety": "Zamknout safety pole?",

    "tool.recommend_tech.desc": "Doporuc technologicky stack na zaklade podobnych projektu.",
    "tool.recommend_tech.param.description": "Popis projektu (jednoduchy web, SaaS...)",
    "tool.recommend_tech.param.similar_to": "Nazev existujiciho projektu k inspiraci.",
    "tool.recommend_tech.param.category": "saas-app|agency-site|simple-website|ecommerce|api|cli-tool",

    # ======================================================================
    # server.py — error messages
    # ======================================================================
    "server.unknown_tool": "Neznamy nastroj: {name}",
    "server.tool_error": "Chyba v {name}: {error}",

    # ======================================================================
    # memory_search.py
    # ======================================================================
    "memory_search.no_results": (
        "Zadne vysledky pro '{query}'. Pamet je prazdna nebo dotaz neodpovida zadnym faktum."
    ),
    "memory_search.header": "## Nalezeno {count} vysledku pro '{query}'\n",
    "memory_search.stale": "STALE — source file {source_file} se zmenil od zapisu tohoto faktu!",
    "memory_search.stale_hint": "-> OVER pred pouzitim: Read {source_file}",
    "memory_search.deleted": "DELETED — source file {source_file} byl smazan!",
    "memory_search.cross_project": "CROSS-PROJECT — z projektu {project}",
    "memory_search.linked_fact": "[{id}] {preview}",

    # ======================================================================
    # memory_write.py
    # ======================================================================
    "memory_write.exists_unchanged": "Fakt uz existuje (beze zmeny): {preview}...",
    "memory_write.updated": "Aktualizovano v pameti: {preview}... [projekt: {project}, typ: {type}]",
    "memory_write.saved": "Ulozeno do pameti: {preview}... [projekt: {project}, typ: {type}]",
    "memory_write.failed_locked": "NEULOŽENO — databaze zamcena/busy, data NEBYLA ulozena: {preview}... Zahrn tento obsah do navratoveho textu jako fallback.",
    "memory_write.blocked_secret": (
        "BLOKOVANO — Obsah zrejme obsahuje secret ({secret_type}). "
        "Secrets se NESMI ukladat do pameti. Odstraň citliva data a zkus znovu."
    ),

    # ======================================================================
    # memory_delete.py
    # ======================================================================
    "memory_delete.no_ids": "Zadna ID ke smazani.",
    "memory_delete.deleted": "Smazano {deleted} faktu z pameti.",

    # ======================================================================
    # memory_link.py
    # ======================================================================
    "tool.memory_link.desc": "Manualne propoj dva fakty v CogniLayer pameti.",
    "tool.memory_link.param.source_id": "UUID zdrojoveho faktu.",
    "tool.memory_link.param.target_id": "UUID ciloveho faktu.",
    "memory_link.not_found": "Fakt nenalezen: {id}",
    "memory_link.already_linked": "Uz propojeno: '{source}' <-> '{target}'",
    "memory_link.linked": "Propojeno: '{source}' <-> '{target}'",
    "memory_link.self_link": "Nelze propojit fakt sam se sebou.",

    # ======================================================================
    # file_search.py
    # ======================================================================
    "file_search.no_results": "Zadne vysledky pro '{query}'.",
    "file_search.not_indexed": "Zadne vysledky pro '{query}'.\nPoznamka: Pro tento projekt nebyly zaindexovany zadne dokumenty. Spust file_index() pro indexaci docs (PRD, README, konfigurace).",
    "file_search.header": "## Nalezeno {count} chunku pro '{query}'\n",
    "file_search.no_title": "(bez nadpisu)",
    "file_search.section_label": "sekce",

    # ======================================================================
    # project_context.py
    # ======================================================================
    "project_context.no_project": "Zadny aktivni projekt. Spust claude v projektovem adresari.",
    "project_context.not_registered": "Projekt '{project}' neni registrovany v CogniLayer.",
    "project_context.dna_placeholder": "## Project DNA: {project}\n[DNA jeste nebyla vygenerovana]",
    "project_context.stats": (
        "\n## Statistiky\n"
        "- Faktu v pameti: {facts_count} (hot: {hot_count})\n"
        "- Indexovanych chunku: {chunks_count}\n"
        "- Sessions: {sessions_count}\n"
        "- Zaznamenanych zmen: {changes_count}"
    ),
    "project_context.health_header": "\n## Zdravi pameti\n",
    "project_context.health_stats": "- Celkem: {total} | Hot: {hot} | Warm: {warm} | Cold: {cold}",
    "project_context.most_retrieved": "- Nejcasteji vyhledavano: \"{content}\" ({count}x)",
    "project_context.never_retrieved": "- Nikdy nevyhledano: {count} faktu",
    "project_context.gaps_header": "## Mezery ve znalostech (nevyresene)",
    "project_context.gaps_item": "- \"{query}\" (dotazano {times}x)",
    "project_context.no_gaps": "## Mezery ve znalostech\nZadne nevyresene mezery.",
    "project_context.avg_retrievals": "- Prumer vyhledani/fakt: {avg:.1f}",

    # ======================================================================
    # session_bridge.py
    # ======================================================================
    "session_bridge.no_bridge": "Zadny session bridge k dispozici.",
    "session_bridge.missing_content": "Chybi obsah bridge ke ulozeni.",
    "session_bridge.no_session": "Zadna aktivni session.",
    "session_bridge.saved": "Session bridge ulozen.",
    "session_bridge.unknown_action": "Neznama akce: {action}. Pouzij 'load' nebo 'save'.",

    # ======================================================================
    # decision_log.py
    # ======================================================================
    "decision_log.no_decisions": "Zadna rozhodnuti{search_info} v projektu {project}.",
    "decision_log.search_info": " pro '{query}'",
    "decision_log.header": "## Rozhodnuti pro {project}\n",
    "decision_log.reason_label": "Duvod: ",
    "decision_log.alternatives_label": "Alternativy: ",

    # ======================================================================
    # verify_identity.py
    # ======================================================================
    "verify_identity.blocked_no_project": "BLOCKED — Zadny aktivni projekt.",
    "verify_identity.blocked_unknown_action": (
        "BLOCKED — Neznamy action_type: {action_type}. Povolene: {allowed}"
    ),
    "verify_identity.not_set": "[NENASTAVENO]",
    "verify_identity.blocked_no_identity": (
        "BLOCKED — Projekt '{project}' nema Identity Card.\n"
        "Chybi safety pole pro '{action_type}':\n{missing}\n\n"
        "ZEPTEJ SE uzivatele na tyto hodnoty.\n"
        "Pouzij /identity set pro konfiguraci."
    ),
    "verify_identity.blocked_missing_fields": (
        "BLOCKED — Chybi safety pole pro '{action_type}':\n{missing}\n\n"
        "ZEPTEJ SE uzivatele na tyto hodnoty.\n"
        "Pouzij /identity set pro konfiguraci."
    ),
    "verify_identity.warning_unlocked": (
        "WARNING — Identity pole existuji ale NEJSOU ZAMKNUTE.\n\n"
        "Aktualni hodnoty:\n{fields}\n\n"
        "Prezentuj hodnoty uzivateli a pozadej explicitni potvrzeni.\n"
        "Pro zamknuti: /identity lock"
    ),
    "verify_identity.blocked_tampered": (
        "BLOCKED — Safety pole byla zmenena mimo /identity update!\n"
        "Hash nesedi: expected {expected}, got {actual}\n"
        "Pouzij /identity lock pro re-zamknuti."
    ),
    "verify_identity.verified": (
        "VERIFIED — Project: {project}\n"
        "Server: {ssh_alias} ({ssh_host})\n"
        "App Port: {app_port}\n"
        "Deploy Path: {deploy_path}\n"
        "PM2: {pm2_name} (id={pm2_id})\n"
        "Domain: {domain}\n"
        "Method: {method}\n"
        "Git Branch: {branch}\n\n"
        "POTVRD s uzivatelem: 'Budu {action_type} na {ssh_alias} pro {domain}.'"
    ),

    # ======================================================================
    # identity_set.py
    # ======================================================================
    "identity_set.no_project": "Zadny aktivni projekt.",
    "identity_set.unknown_fields": "Neznama pole: {invalid}. Povolena: {allowed}",
    "identity_set.blocked_locked": (
        "BLOCKED — Safety pole jsou zamknuta.\n"
        "Pokus o zmenu: {changes}\n"
        "Pouzij /identity update pro zmenu zamknutych poli."
    ),
    "identity_set.updated": "Identity Card aktualizovana pro {project}:",
    "identity_set.safety_locked": "zamknuto",
    "identity_set.safety_unlocked": "odemknuto",
    "identity_set.safety_status": "Safety pole: {status}",

    # ======================================================================
    # recommend_tech.py
    # ======================================================================
    "recommend_tech.header": "## Tech doporuceni\n",
    "recommend_tech.based_on_project": "Na zaklade projektu: {project}\n",
    "recommend_tech.recommended_stack": "Doporuceny stack:",
    "recommend_tech.apply_hint": "Pro aplikovani: /identity tech-from {project}",
    "recommend_tech.no_identity": "Projekt '{project}' nema Identity Card.",
    "recommend_tech.no_projects": (
        "Zadne projekty s Identity Card v databazi. Pouzij /onboard pro registraci projektu."
    ),
    "recommend_tech.based_on_desc": "Na zaklade popisu: {description}\n",
    "recommend_tech.similar_projects": "Podobne projekty v portfoliu:",
    "recommend_tech.apply_stack_hint": "Pro aplikovani stacku: /identity tech-from <nazev-projektu>",
    "recommend_tech.edit_hint": "Pro upravu: /identity set framework=... css_approach=...",

    # ======================================================================
    # hooks/on_session_start.py
    # ======================================================================
    "claude_md.template": (
        "## CogniLayer v4 Aktivni\n"
        "Trvala pamet + code intelligence je ZAPNUTA.\n"
        "PRI PRVNI ZPRAVE UZIVATELE v teto session mu strucne rekni:\n"
        "  'CogniLayer v4 aktivni — trvala pamet zapnuta. Napis /cognihelp pro prehled prikazu.'\n"
        "Rekni to JEDNOU, strucne, pak pokracuj s jeho pozadavkem.\n"
        "\n"
        "## Nastroje — JAK PRACOVAT\n"
        "\n"
        "PRVNI SPUSTENI NA PROJEKTU:\n"
        'Kdyz DNA ukazuje "[nova session]" nebo "[prvni session]":\n'
        "1. Spust /onboard — zaindexuje docs projektu (PRD, README), vytvori zakladni pamet\n"
        "2. Spust code_index() — vytvori AST index pro code intelligence\n"
        "Oboje je jednorazove. Potom se aktualizuje inkrementalne.\n"
        "Pokud file_search nebo code_search vraci prazdno → jeste nebyly spusteny.\n"
        "\n"
        "NEJDRIV POCHOP (pred zmenami):\n"
        "- memory_search(query) → co vime? Minule bugy, rozhodnuti, gotchas\n"
        "- code_context(symbol) → jak kod funguje? Kdo vola, co vola, zavislosti\n"
        "- file_search(query) → hledej v docs projektu (PRD, README) bez cteni celych souboru\n"
        "- code_search(query) → najdi kde je funkce/trida definovana\n"
        "Pouzij OBOJI pamet + code nastroje pro uplny obraz. Jsou rychle — volej paralelne.\n"
        "\n"
        "PRED RIZIKOVOU ZMENOU (povinne):\n"
        "- Prejmenovani, mazani, presun funkce/tridy → code_impact(symbol) NEJDRIV\n"
        "- Zmena signatury nebo navratove hodnoty → code_impact(symbol) NEJDRIV\n"
        "- Uprava sdilenych utilit pouzivanych v mnoha souborech → code_impact(symbol) NEJDRIV\n"
        "- TAKE: memory_search(symbol) → over souvisejici rozhodnuti nebo zname gotchas\n"
        "Oboji je nutne. Struktura rekne co se rozbije, pamet rekne PROC to bylo tak postavene.\n"
        "\n"
        "PO DOKONCENI PRACE:\n"
        "- memory_write(content) → uloz dulezite zjisteni okamzite\n"
        "  (error_fix, gotcha, pattern, api_contract, procedure, decision)\n"
        '- session_bridge(action="save", content="Progress: ...; Open: ...")\n'
        "NECEKEJ na /harvest — session muze crashnout.\n"
        "\n"
        "PROTOKOL PAMETI PRO SUBAGENTY:\n"
        "Pri spousteni Agent nastroje pro pruzkum nebo analyzu:\n"
        "- Zadat v promptu: syntetizovat nalezy do konsolidovanych memory_write(content, type, tags=\"subagent,<tema-ukolu>\") faktu\n"
        "  Priradit popisny tag kazemu subagentovi (napr. tags=\"subagent,auth-review\", tags=\"subagent,perf-analysis\")\n"
        "- NEPSAT kazdy objev zvlast — seskupit souvisejici nalezy do ucelenych faktu\n"
        "- Zapisovat do pameti az jako POSLEDNI krok pred return, ne prubezne — setri turns a tokeny\n"
        "- Kazdy fakt musi byt samostatny se specifickymi detaily (cesty k souborum, hodnoty, kod)\n"
        "- Kdyz se nalezy tykaji konkretniho souboru, pridat domain a source_file pro lepsi vyhledavani a detekci zastaralosti\n"
        "- Ukoncit kazdy fakt radkem 'Search: klicove1, klicove2' — keywords UVNITR faktu preziji context compaction\n"
        "- Zaznamenat i vyznamne negativni nalezy (napr. 'rate limiting v src/api/ neexistuje' — zabrani opakovani hledani)\n"
        "- Vratit: akcni shrnuti (cesty k souborum, nazvy funkci, konkretni hodnoty) + co bylo ulozeno + klicova slova pro memory_search\n"
        "- Pokud MCP nastroje nejsou dostupne nebo selzou → vratit klicove poznatky primo v textu jako fallback\n"
        "- Spoustet subagenty jako foreground (default) pro spolehlive MCP — uzivatel muze Ctrl+B presunout na pozadi pozdeji\n"
        "Proc: bez protokolu subagent vraci vsechna data do parent kontextu (40K+ tokenu).\n"
        "S protokolem nalezy jdou do DB a parent dostane ~500 tokenu shrnuti + on-demand memory_search.\n"
        "\n"
        "PRED DEPLOY/PUSH:\n"
        '- verify_identity(action_type="...") → povinna safety brana\n'
        "- Pokud BLOCKED → ZASTAV a zeptej se uzivatele\n"
        "- Pokud VERIFIED → PRECTI uzivateli cilovy server a pozadej potvrzeni\n"
        "\n"
        "## VERIFY-BEFORE-ACT\n"
        "Kdyz memory_search vrati fakt oznaceny ⚠ STALE:\n"
        "1. Precti zdrojovy soubor a over ze fakt stale plati\n"
        "2. Pokud se zmenil → aktualizuj pres memory_write\n"
        "3. NIKDY nedelej zmeny na zaklade STALE faktu bez overeni\n"
        "\n"
        "## Sprava procesu (Windows)\n"
        "- NIKDY nepouzivej `taskkill //F //IM node.exe` — zabije VSECHNY Node.js VCETNE Claude Code CLI!\n"
        "- Pouzij: `npx kill-port PORT` nebo najdi PID pres `netstat -ano | findstr :PORT` pak `taskkill //F //PID XXXX`\n"
        "\n"
        "## Git pravidla\n"
        '- Commituj casto, male atomicke zmeny. Format: "[typ] co a proc"\n'
        "- commit = Tier 1 (delej sam). push = Tier 3 (verify_identity)."
    ),

    "claude_md.do_not_delete": "auto-generated, nemaz",

    "crash.session_summary": "[CRASH] Session nebyla korektne ukoncena",
    "crash.recovery": (
        "## Crash Recovery\n"
        "Posledni session ({start_time}) nebyla korektne ukoncena (pad/kill).\n"
        "Zaznamenano {changes} zmen souboru pred padem.\n"
        "Posledni zmenene soubory: {last_files}\n"
        "Bridge z predposledni session je platny (vyse).\n"
        'Pro detail pouzij: memory_search("zmeny posledni session")'
    ),
    "crash.no_files": "zadne",

    "dna.unknown_stack": "neznamy",
    "dna.unknown_style": "[neznamy]",
    "dna.deploy_not_set": "[NENASTAVENO]",
    "dna.new_session": "[nova session]",
    "dna.first_session": "[prvni session]",
    "dna.not_generated": "[DNA jeste nebyla vygenerovana]",

    # ======================================================================
    # memory_chain.py
    # ======================================================================
    "tool.memory_chain.desc": (
        "Vytvor kauzalni retez mezi dvema fakty. "
        "Sleduje pricina->dusledek vztahy (caused, led_to, blocked, fixed, broke)."
    ),
    "tool.memory_chain.param.cause_id": "UUID faktu priciny.",
    "tool.memory_chain.param.effect_id": "UUID faktu dusledku.",
    "tool.memory_chain.param.relationship": (
        "Typ vztahu: caused|led_to|blocked|fixed|broke (default: caused)"
    ),
    "memory_chain.self_chain": "Nelze vytvorit kauzalni retez z faktu na sebe sama.",
    "memory_chain.invalid_relationship": (
        "Neplatny typ vztahu '{relationship}'. Platne: {valid}"
    ),
    "memory_chain.not_found": "Fakt nenalezen: {id}",
    "memory_chain.cross_project": (
        "Nelze propojit fakty napric projekty: {cause_project} != {effect_project}"
    ),
    "memory_chain.already_exists": (
        "Kauzalni retez uz existuje: '{cause}' -> '{effect}'"
    ),
    "memory_chain.created": (
        "Kauzalni retez vytvoren: '{cause}' --[{relationship}]--> '{effect}'"
    ),

    # ======================================================================
    # memory_search.py — causal chain display
    # ======================================================================
    "memory_search.chain_caused": "{relationship}: [{id}] {preview}",
    "memory_search.chain_caused_by": "{relationship} by: [{id}] {preview}",

    # ======================================================================
    # project_context.py — episodes + organization
    # ======================================================================
    "project_context.episodes_header": "## Posledni epizody",
    "project_context.episodes_item": "- [{outcome}] \"{title}\" ({date})",
    "project_context.org_header": "## Organizace pameti",
    "project_context.org_stats": (
        "- Clustery: {clusters} | Aktivni: {active} | Reference: {reference} | Archiv: {archive}"
    ),
    "project_context.org_contradictions": "- Kontradikce: {count} nevyresenych",

    # ======================================================================
    # consolidate.py
    # ======================================================================
    "consolidate.no_project": "Zadny aktivni projekt. Zadej nazev projektu nebo spust v adresari projektu.",
    "consolidate.report": (
        "## Konsolidacni report pro {project}\n"
        "- Nalezenych clusteru: {clusters} ({labeled} oznacenych)\n"
        "- Tiery: Aktivni={active} | Reference={reference} | Archiv={archive}\n"
        "- Novych kontradikci: {contradictions}"
    ),
    "consolidate.stale_contradiction": (
        "Stejny soubor '{file}' ma vice {type} faktu s ruznymi mtime (jeden muze byt stale)"
    ),
    "consolidate.age_contradiction": (
        "Stejna domena '{domain}' ma {type} fakty >30 dni od sebe (mohou byt zastarale)"
    ),

    # ======================================================================
    # hooks/on_session_end.py
    # ======================================================================
    "session_end.emergency_header": "[Emergency bridge — running bridge nebyl aktualizovan]",
    "session_end.and_more": "  ... a {count} dalsich",
    "session_end.no_changes": "Zadne zmeny ani fakty v teto session.",

    # ======================================================================
    # session_init.py (Codex MCP tool)
    # ======================================================================
    "tool.session_init.desc": (
        "Inicializuj CogniLayer session (POUZE pro Codex CLI — Claude Code pouziva hooky, "
        "NEVOLEJ pokud uz mas CogniLayer kontext v CLAUDE.md). "
        "Vraci DNA + bridge + crash recovery."
    ),
    "tool.session_init.param.project_path": (
        "Cesta k adresari projektu. Auto-detekce z CWD pokud neni zadano."
    ),
    "session_init.no_db": "CogniLayer DB nenalezena. Spust nejdriv install.",
    "session_init.invalid_path": "Neplatna cesta k projektu: {path}",
    "session_init.error": "Chyba pri inicializaci session: {error}",
    "session_init.header": "## Session inicializovana pro {project}\nSession ID: {session_id}",
    "session_init.instructions": (
        "## Pripominky\n"
        "- Pouzivej memory_write proaktivne pro ukladani poznatku\n"
        "- Na konci session: session_bridge(action=\"save\", content=\"Progress: ...; Open: ...\")\n"
        "- Pred deployem/pushem: verify_identity(action_type=\"...\")"
    ),

    # ======================================================================
    # File indexing (file_index)
    # ======================================================================
    "tool.file_index.desc": (
        "Zaindexuj dokumentacni soubory projektu (README, konfigurace, PRD, YAML, JSON, TOML) "
        "do file_chunks, aby file_search() vracel vysledky. "
        "Spust jednou na projekt. Inkrementalni — reindexuje jen zmenene soubory."
    ),
    "tool.file_index.param.project_path": "Prepis cestu projektu. Vychozi: detekovana ze session.",
    "tool.file_index.param.full": "Vynutit plnou reindexaci (smazat vsechny chunky). Vychozi: false (inkrementalni).",
    "tool.file_index.param.time_budget": "Max sekund pro indexaci (vychozi 30). Pri timeoutu se vrati castecny vysledek.",
    "file_index.no_path": "Nelze urcit cestu projektu. Zadej project_path nebo nejdriv spust session_init.",
    "file_index.invalid_path": "Neplatna cesta projektu: {path}",
    "file_index.error": "Indexace souboru selhala: {error}",
    "file_index.success": (
        "Indexace souboru dokoncena pro '{project}'.\n"
        "  Souboru zaindexovano v tomto behu: {indexed}\n"
        "  Celkem zaindexovanych souboru: {total_files}\n"
        "  Celkem chunku: {total_chunks}\n"
        "  Indexovatelnych souboru nalezeno: {available}\n"
        "file_search() je nyni pripraveno."
    ),

    # ======================================================================
    # Code Intelligence tools
    # ======================================================================
    "tool.code_index.desc": (
        "Zaindexuj zdrojovy kod projektu (tree-sitter AST → symboly + reference do SQLite). "
        "Aktivuje code_context, code_impact a code_search. Inkrementalni ve vychozim stavu."
    ),
    "tool.code_index.param.project_path": "Prepis cestu projektu. Vychozi: detekovana ze session.",
    "tool.code_index.param.full": "Vynutit plnou reindexaci (ignorovat cache). Vychozi: false (inkrementalni).",
    "tool.code_index.param.time_budget": "Max sekund pro indexaci (vychozi 30). Pri timeoutu se vrati castecny vysledek.",

    "tool.code_search.desc": (
        "Hledej symboly kodu (funkce, tridy, metody, rozhrani) podle nazvu nebo signatury. "
        "Pouziva FTS5 fulltext. Vyzaduje predchozi spusteni code_index."
    ),
    "tool.code_search.param.query": "Hledany vyraz — nazev symbolu, cast nazvu, nebo klicove slovo.",
    "tool.code_search.param.kind": "Filtr podle druhu: function|class|method|interface|variable|type_alias|enum",
    "tool.code_search.param.limit": "Max vysledku (vychozi 20, max 50).",

    "tool.code_context.desc": (
        "360° pohled na symbol kodu: definice, kdo ho vola (incoming), "
        "co vola (outgoing), potomci (metody). Vyzaduje code_index."
    ),
    "tool.code_context.param.symbol": "Nazev symbolu nebo kvalifikovany nazev (napr. 'open_db' nebo 'MyClass.method').",
    "tool.code_context.param.project_name": "Prepis projektu. Vychozi: aktualni.",

    "tool.code_impact.desc": (
        "Analyza blast radius — BFS pruchod prichozich referenci pro nalezeni "
        "vseho co ovlivni zmena symbolu. Vyzaduje code_index."
    ),
    "tool.code_impact.param.symbol": "Symbol pro analyzu dopadu.",
    "tool.code_impact.param.max_depth": "Max BFS hloubka (1-5, vychozi 3).",
    "tool.code_impact.param.project_name": "Prepis projektu. Vychozi: aktualni.",

    # Code Intelligence result messages
    "code.no_treesitter": (
        "tree-sitter-language-pack neni nainstalovany. "
        "Spust: pip install tree-sitter-language-pack"
    ),
    "code.no_project": "Zadny aktivni projekt. Spust Claude v projektovem adresari.",
    "code.not_indexed": (
        "Projekt '{project}' jeste nema code index. "
        "Nejdriv spust code_index pro vytvoreni databaze symbolu."
    ),
    "code.db_busy": "Databaze je zaneprazdnena (jiny proces drzi zamek). Zkus znovu za moment.",
    "code.db_error": "Chyba databaze: {error}",
    "code.generic_error": "Chyba code intelligence: {error}",

    "code.index_header": "## Code Index: {project}",
    "code.index_partial": (
        "Indexace prerusena po {elapsed}s — castecny vysledek. "
        "Spust code_index znovu pro dokonceni."
    ),
    "code.index_complete": "Indexace dokoncena za {elapsed}s.",
    "code.index_stats": (
        "- Skenovanych souboru: {files_total}\n"
        "- Zaindexovanych souboru: {files_indexed} (preskoceno: {files_skipped})\n"
        "- Extrahovanych symbolu: {symbols}\n"
        "- Nalezenych referenci: {references}\n"
        "- Vyresenych referenci: {resolved}"
    ),
    "code.index_errors": "Chyby ({count}):",
    "code.index_db_totals": "- **Celkem v indexu**: {symbols} symbolu, {references} referenci",

    "code.search_header": "## Nalezeno {count} symbolu pro '{query}'",
    "code.search_no_results": "Zadne symboly nalezeny pro '{query}'.",

    "code.context_header": "## Symbol: {symbol}",
    "code.context_incoming": "### Prichozi reference ({count}):",
    "code.context_no_incoming": "### Prichozi reference: zadne",
    "code.context_outgoing": "### Odchozi reference ({count}):",
    "code.context_no_outgoing": "### Odchozi reference: zadne",
    "code.context_children": "### Potomci ({count}):",
    "code.symbol_not_found": "Symbol '{symbol}' nebyl nalezen v code indexu.",

    "code.impact_header": (
        "## Analyza dopadu: {symbol}\n"
        "**Ovlivneno:** {total} symbolu v {files} souborech"
    ),
    "code.impact_no_refs": "Zadne prichozi reference — tento symbol neni referencovan jinym kodem.",
    "code.impact_depth": "### Hloubka {depth} ({count} symbolu):",
    "code.impact_files": "### Ovlivnene soubory:",
    "code.impact_timeout": "Analyza vyprsela po {elapsed}s — vysledky mohou byt neuplne.",
}


_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": _EN,
    "cs": _CS,
}


def t(key: str, **kwargs) -> str:
    """Get translated string. Falls back: current locale -> 'en' -> key itself."""
    text = _TRANSLATIONS.get(_language, {}).get(key)
    if text is None:
        text = _TRANSLATIONS.get("en", {}).get(key)
    if text is None:
        return key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def get_language() -> str:
    """Return current language code."""
    return _language
