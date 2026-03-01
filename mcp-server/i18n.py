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
    "tool.memory_search.param.limit": "Max results (default 5, max 10)",

    "tool.memory_write.desc": (
        "Save important information to CogniLayer memory. "
        "Use PROACTIVELY — save as you learn, not just during /harvest."
    ),
    "tool.memory_write.param.content": "What to remember. Must be self-contained.",
    "tool.memory_write.param.type": (
        "Type: fact|decision|pattern|issue|task|skill|gotcha|"
        "procedure|error_fix|command|performance|api_contract|dependency|client_rule"
    ),
    "tool.memory_write.param.tags": "Tags separated by comma.",
    "tool.memory_write.param.domain": "Domain: auth, ui, deploy, seo...",
    "tool.memory_write.param.source_file": "Relative path to the file where the fact was observed.",

    "tool.memory_delete.desc": "Delete facts from CogniLayer memory by ID.",
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

    # ======================================================================
    # memory_write.py
    # ======================================================================
    "memory_write.exists_unchanged": "Fact already exists (unchanged): {preview}...",
    "memory_write.updated": "Updated in memory: {preview}... [project: {project}, type: {type}]",
    "memory_write.saved": "Saved to memory: {preview}... [project: {project}, type: {type}]",

    # ======================================================================
    # memory_delete.py
    # ======================================================================
    "memory_delete.no_ids": "No IDs to delete.",
    "memory_delete.deleted": "Deleted {deleted} facts from memory.",

    # ======================================================================
    # file_search.py
    # ======================================================================
    "file_search.no_results": "No chunks found for '{query}'. Files may not be indexed yet.",
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
        "## Memory Tools\n"
        "You have access to the `cognilayer` MCP server:\n"
        "- memory_search(query) — search memory semantically\n"
        "- memory_write(content) — save important information\n"
        "- file_search(query) — search project files (PRD, docs...)\n"
        "- decision_log(query) — find past decisions\n"
        "\n"
        "When unsure about context or project history,\n"
        "ALWAYS search memory first via memory_search.\n"
        "When you need info from PRD or docs, use file_search\n"
        "INSTEAD of reading the entire file.\n"
        "\n"
        "## VERIFY-BEFORE-ACT — MANDATORY\n"
        "When memory_search returns a fact marked with ⚠ STALE:\n"
        "1. ALWAYS read the source file and verify the fact still holds\n"
        "2. If the fact changed -> update it via memory_write\n"
        "3. NEVER make changes based on STALE facts without verification\n"
        "\n"
        "## PROACTIVE MEMORY — IMPORTANT\n"
        "When you discover something important during work, SAVE IT IMMEDIATELY:\n"
        '- Bug and fix -> memory_write(type="error_fix")\n'
        '- Pitfall/danger -> memory_write(type="gotcha")\n'
        '- Exact procedure -> memory_write(type="procedure")\n'
        '- How components communicate -> memory_write(type="api_contract")\n'
        '- Performance issue -> memory_write(type="performance")\n'
        '- Important command -> memory_write(type="command")\n'
        "DO NOT wait for /harvest — session may crash.\n"
        "\n"
        "## RUNNING BRIDGE — CRITICAL\n"
        "After completing each task AUTOMATICALLY update session bridge:\n"
        '  session_bridge(action="save", content="Progress: ...; Open: ...")\n'
        "This is Tier 1 — do it yourself, don't announce, it's part of the job.\n"
        "\n"
        "## Safety Rules — MANDATORY\n"
        "- Before ANY deploy, push, ssh, pm2, docker, db migration:\n"
        '  1. ALWAYS call verify_identity(action_type="...") first\n'
        "  2. If it returns BLOCKED — STOP and ask the user\n"
        "  3. If it returns VERIFIED — READ the target server to the user and request confirmation\n"
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
    # hooks/on_session_end.py
    # ======================================================================
    "session_end.emergency_header": "[Emergency bridge — running bridge was not updated]",
    "session_end.and_more": "  ... and {count} more",
    "session_end.no_changes": "No changes or facts in this session.",
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
    "tool.memory_search.param.limit": "Max pocet vysledku (default 5, max 10)",

    "tool.memory_write.desc": (
        "Uloz dulezitou informaci do CogniLayer pameti. "
        "Pouzivej PROAKTIVNE — ukladej jak se ucis, ne jen pri /harvest."
    ),
    "tool.memory_write.param.content": "Co si zapamatovat. Musi byt self-contained.",
    "tool.memory_write.param.type": (
        "Typ: fact|decision|pattern|issue|task|skill|gotcha|"
        "procedure|error_fix|command|performance|api_contract|dependency|client_rule"
    ),
    "tool.memory_write.param.tags": "Tagy oddelene carkou.",
    "tool.memory_write.param.domain": "Oblast: auth, ui, deploy, seo...",
    "tool.memory_write.param.source_file": "Relativni cesta k souboru kde byl fakt pozorovan.",

    "tool.memory_delete.desc": "Smaz fakty z CogniLayer pameti podle ID.",
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

    # ======================================================================
    # memory_write.py
    # ======================================================================
    "memory_write.exists_unchanged": "Fakt uz existuje (beze zmeny): {preview}...",
    "memory_write.updated": "Aktualizovano v pameti: {preview}... [projekt: {project}, typ: {type}]",
    "memory_write.saved": "Ulozeno do pameti: {preview}... [projekt: {project}, typ: {type}]",

    # ======================================================================
    # memory_delete.py
    # ======================================================================
    "memory_delete.no_ids": "Zadna ID ke smazani.",
    "memory_delete.deleted": "Smazano {deleted} faktu z pameti.",

    # ======================================================================
    # file_search.py
    # ======================================================================
    "file_search.no_results": "Zadne chunky nalezeny pro '{query}'. Soubory mozna nebyly zaindexovany.",
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
        "## Pametove nastroje\n"
        "Mas pristup k MCP serveru `cognilayer`:\n"
        "- memory_search(query) — prohledej pamet semanticky\n"
        "- memory_write(content) — zapamatuj si dulezitou informaci\n"
        "- file_search(query) — hledej v projektovych souborech (PRD, docs...)\n"
        "- decision_log(query) — najdi minula rozhodnuti\n"
        "\n"
        "Kdyz si nejsi jisty kontextem nebo historii projektu,\n"
        "VZDY nejdriv prohledej pamet pomoci memory_search.\n"
        "Kdyz potrebujes info z PRD nebo docs, pouzij file_search\n"
        "MISTO cteni celeho souboru.\n"
        "\n"
        "## VERIFY-BEFORE-ACT — POVINNE\n"
        "Kdyz memory_search vrati fakt oznaceny ⚠ STALE:\n"
        "1. VZDY precti zdrojovy soubor a over ze fakt stale plati\n"
        "2. Pokud se fakt zmenil → aktualizuj ho pres memory_write\n"
        "3. NIKDY nedelej zmeny na zaklade STALE faktu bez overeni\n"
        "\n"
        "## PROAKTIVNI PAMET — DULEZITE\n"
        "Kdyz behem prace zjistis neco duleziteho, OKAMZITE to uloz:\n"
        '- Chyba a oprava → memory_write(type="error_fix")\n'
        '- Past/nebezpeci → memory_write(type="gotcha")\n'
        '- Presny postup → memory_write(type="procedure")\n'
        '- Jak komponenty komunikuji → memory_write(type="api_contract")\n'
        '- Vykonovy problem → memory_write(type="performance")\n'
        '- Dulezity prikaz → memory_write(type="command")\n'
        "NECEKEJ na /harvest — session muze crashnout.\n"
        "\n"
        "## RUNNING BRIDGE — KRITICKE\n"
        "Po kazdem dokonceni ukolu AUTOMATICKY aktualizuj session bridge:\n"
        '  session_bridge(action="save", content="Progress: ...; Open: ...")\n'
        "Toto je Tier 1 — delej sam, neoznamuj, je to soucast prace.\n"
        "\n"
        "## Safety pravidla — POVINNE\n"
        "- Pred JAKYMKOLIV deployem, push, ssh, pm2, docker, db migraci:\n"
        '  1. VZDY nejdriv zavolej verify_identity(action_type="...")\n'
        "  2. Pokud vrati BLOCKED — ZASTAV a zeptej se uzivatele\n"
        "  3. Pokud vrati VERIFIED — PRECTI uzivateli cilovy server a pozadej potvrzeni\n"
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
    # hooks/on_session_end.py
    # ======================================================================
    "session_end.emergency_header": "[Emergency bridge — running bridge nebyl aktualizovan]",
    "session_end.and_more": "  ... a {count} dalsich",
    "session_end.no_changes": "Zadne zmeny ani fakty v teto session.",
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
