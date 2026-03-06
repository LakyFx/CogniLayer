"""Generate AGENTS.md with CogniLayer instructions for Codex CLI.

Reuses detection logic from on_session_start.py but generates Codex-specific
instructions (no hooks — explicit MCP tool calls via AGENTS.md).

Usage:
    python generate_agents_md.py [project_path]
"""

import sys
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
DB_PATH = COGNILAYER_HOME / "memory.db"

sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))
sys.path.insert(0, str(COGNILAYER_HOME / "hooks"))

try:
    from i18n import t, get_language
except ImportError:
    def t(key, **kwargs):
        return key
    def get_language():
        return "en"

COGNILAYER_START = "# === COGNILAYER ==="
COGNILAYER_END = "# === END COGNILAYER ==="


def get_agents_md_template() -> str:
    """Build the CogniLayer block for AGENTS.md (Codex-specific)."""
    lang = get_language()
    if lang == "cs":
        return _TEMPLATE_CS
    return _TEMPLATE_EN


_TEMPLATE_EN = """## CogniLayer Memory Tools
You have access to the `cognilayer` MCP server with these tools:

**Memory:**
- memory_search(query) — search memory semantically (facts, decisions, patterns)
- memory_write(content, type) — save important information (14 fact types)
- memory_delete(ids) — remove outdated facts by ID
- memory_link(source_id, target_id) — bidirectional link between facts
- memory_chain(cause_id, effect_id, relationship) — causal chain (caused, led_to, blocked, fixed, broke)

**Search & Context:**
- file_search(query) — search indexed project docs (README, configs, PRD)
- file_index(project_path) — index project docs so file_search works (run once per project)
- project_context() — get project DNA, health metrics, session info
- decision_log(query) — find past decisions
- recommend_tech(description) — suggest tech stack from similar projects

**Code Intelligence:**
- code_index(project_path) — index codebase via tree-sitter AST parsing
- code_search(query) — find functions, classes, methods by name
- code_context(symbol) — 360 view: who calls it, what it calls, dependencies
- code_impact(symbol) — blast radius: what breaks if you change this symbol

**Session & Safety:**
- session_init(project_path) — initialize session (CALL THIS FIRST)
- session_bridge(action, content) — load/save session continuity
- verify_identity(action_type) — safety gate before deploy/push/SSH
- identity_set(fields) — configure project Identity Card

## SESSION LIFECYCLE — CRITICAL
Codex has no hooks, so YOU must manage the session lifecycle:
1. **AT START**: Call `session_init()` — returns DNA + bridge + crash recovery
2. **DURING WORK**: Use memory_write proactively to save findings
3. **AT END**: Call `session_bridge(action="save", content="Progress: ...; Open: ...")`

## FIRST RUN ON NEW PROJECT — IMPORTANT
If this is the first session on this project (DNA shows "[new session]"):
1. Call `session_init()` to register the project
2. Call `file_index()` to index documentation (README, configs, PRD)
3. Call `code_index()` to index source code (needs tree-sitter)
4. Read key project files and save findings to memory:
   - Architecture overview → memory_write(type="fact")
   - API endpoints → memory_write(type="api_contract")
   - Build/deploy commands → memory_write(type="command")
   - Known pitfalls → memory_write(type="gotcha")
   - Key patterns → memory_write(type="pattern")
   - Important dependencies → memory_write(type="dependency")
Steps 2-3 are one-time. Step 4 is where YOU (the AI) add intelligent analysis.
After onboarding, file_search and code_search will return results instantly.

## VERIFY-BEFORE-ACT — MANDATORY
When memory_search returns a fact marked with STALE:
1. ALWAYS read the source file and verify the fact still holds
2. If the fact changed -> update it via memory_write
3. NEVER make changes based on STALE facts without verification

## PROACTIVE MEMORY — IMPORTANT
When you discover something important during work, SAVE IT IMMEDIATELY:
- Bug and fix -> memory_write(type="error_fix")
- Pitfall/danger -> memory_write(type="gotcha")
- Exact procedure -> memory_write(type="procedure")
- How components communicate -> memory_write(type="api_contract")
- Performance issue -> memory_write(type="performance")
- Important command -> memory_write(type="command")

## Safety Rules — MANDATORY
- Before ANY deploy, push, ssh, pm2, docker, db migration:
  1. ALWAYS call verify_identity(action_type="...") first
  2. If it returns BLOCKED — STOP and ask the user
  3. If it returns VERIFIED — READ the target server to the user and request confirmation

## Git Rules
- Commit often, small atomic changes. Format: "[type] what and why"
- commit = Tier 1 (do it yourself). push = Tier 3 (verify_identity)."""


_TEMPLATE_CS = """## CogniLayer Pametove nastroje
Mas pristup k MCP serveru `cognilayer` s temito nastroji:

**Pamet:**
- memory_search(query) — prohledej pamet semanticky (fakta, rozhodnuti, patterny)
- memory_write(content, type) — zapamatuj si dulezitou informaci (14 typu faktu)
- memory_delete(ids) — smaz zastarale fakty podle ID
- memory_link(source_id, target_id) — obousmerny odkaz mezi fakty
- memory_chain(cause_id, effect_id, relationship) — kauzalni retez (caused, led_to, blocked, fixed, broke)

**Hledani a kontext:**
- file_search(query) — hledej v indexovanych docs projektu (README, konfigurace, PRD)
- file_index(project_path) — zaindexuj docs projektu aby file_search fungoval (jednorazove)
- project_context() — ziskej DNA projektu, metriky zdravi, info o session
- decision_log(query) — najdi minula rozhodnuti
- recommend_tech(description) — doporuc tech stack z podobnych projektu

**Code Intelligence:**
- code_index(project_path) — zaindexuj kod pres tree-sitter AST parsing
- code_search(query) — najdi funkce, tridy, metody podle jmena
- code_context(symbol) — 360 pohled: kdo vola, co vola, zavislosti
- code_impact(symbol) — blast radius: co se rozbije pri zmene symbolu

**Session a bezpecnost:**
- session_init(project_path) — inicializuj session (ZAVOLEJ JAKO PRVNI)
- session_bridge(action, content) — nacti/uloz kontinuitu session
- verify_identity(action_type) — bezpecnostni brana pred deploy/push/SSH
- identity_set(fields) — nastav Identity Card projektu

## ZIVOTNI CYKLUS SESSION — KRITICKE
Codex nema hooks, takze TY musis ridit zivotni cyklus session:
1. **NA ZACATKU**: Zavolej `session_init()` — vrati DNA + bridge + crash recovery
2. **BEHEM PRACE**: Pouzivej memory_write proaktivne pro ukladani poznatku
3. **NA KONCI**: Zavolej `session_bridge(action="save", content="Progress: ...; Open: ...")`

## PRVNI SPUSTENI NA NOVEM PROJEKTU — DULEZITE
Pokud je toto prvni session na projektu (DNA ukazuje "[nova session]"):
1. Zavolej `session_init()` pro registraci projektu
2. Zavolej `file_index()` pro indexaci dokumentace (README, konfigurace, PRD)
3. Zavolej `code_index()` pro indexaci zdrojoveho kodu (vyzaduje tree-sitter)
4. Precti klicove soubory projektu a uloz poznatky do pameti:
   - Prehled architektury → memory_write(type="fact")
   - API endpointy → memory_write(type="api_contract")
   - Build/deploy prikazy → memory_write(type="command")
   - Zname pasti → memory_write(type="gotcha")
   - Klicove patterny → memory_write(type="pattern")
   - Dulezite zavislosti → memory_write(type="dependency")
Kroky 2-3 jsou jednorazove. Krok 4 je kde TY (AI) pridas inteligentni analyzu.
Po onboardingu file_search a code_search vraci vysledky okamzite.

## VERIFY-BEFORE-ACT — POVINNE
Kdyz memory_search vrati fakt oznaceny STALE:
1. VZDY precti zdrojovy soubor a over ze fakt stale plati
2. Pokud se fakt zmenil → aktualizuj ho pres memory_write
3. NIKDY nedelej zmeny na zaklade STALE faktu bez overeni

## PROAKTIVNI PAMET — DULEZITE
Kdyz behem prace zjistis neco duleziteho, OKAMZITE to uloz:
- Chyba a oprava → memory_write(type="error_fix")
- Past/nebezpeci → memory_write(type="gotcha")
- Presny postup → memory_write(type="procedure")
- Jak komponenty komunikuji → memory_write(type="api_contract")
- Vykonovy problem → memory_write(type="performance")
- Dulezity prikaz → memory_write(type="command")

## Safety pravidla — POVINNE
- Pred JAKYMKOLIV deployem, push, ssh, pm2, docker, db migraci:
  1. VZDY nejdriv zavolej verify_identity(action_type="...")
  2. Pokud vrati BLOCKED — ZASTAV a zeptej se uzivatele
  3. Pokud vrati VERIFIED — PRECTI uzivateli cilovy server a pozadej potvrzeni

## Git pravidla
- Commituj casto, male atomicke zmeny. Format: "[typ] co a proc"
- commit = Tier 1 (delej sam). push = Tier 3 (verify_identity)."""


def inject_agents_md(project_path: Path, dna: str = "", bridge: str | None = None,
                     crash_info: str | None = None):
    """Inject CogniLayer block into AGENTS.md at project_path."""
    agents_md = project_path / "AGENTS.md"
    template = get_agents_md_template()

    lines = [COGNILAYER_START, ""]
    lines.append(template)

    if dna:
        lines.append("")
        lines.append(dna)

    if bridge:
        lines.append("")
        lines.append(f"## Last Session Bridge\n{bridge}")

    if crash_info:
        lines.append("")
        lines.append(crash_info)

    lines.append("")
    lines.append(COGNILAYER_END)
    block = "\n".join(lines)

    if agents_md.exists():
        content = agents_md.read_text(encoding="utf-8")
        if COGNILAYER_START in content and COGNILAYER_END in content:
            before = content[:content.index(COGNILAYER_START)]
            after = content[content.index(COGNILAYER_END) + len(COGNILAYER_END):]
            new_content = before + block + after
        else:
            new_content = content.rstrip() + "\n\n" + block + "\n"
    else:
        new_content = block + "\n"

    agents_md.write_text(new_content, encoding="utf-8", newline="\n")
    print(f"AGENTS.md updated at {agents_md}")


def main():
    """Generate AGENTS.md with CogniLayer block for a project."""
    import sqlite3
    from on_session_start import (
        detect_project, register_project_if_new,
        get_or_generate_dna, get_latest_bridge, open_db
    )
    from tools.project_context import _check_crash_recovery

    project_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    project_path = project_path.resolve()

    if not DB_PATH.exists():
        print("CogniLayer DB not found. Run install first.")
        sys.exit(1)

    project_name = detect_project(project_path)
    db = open_db()
    try:
        register_project_if_new(db, project_name, project_path)
        crash_info = _check_crash_recovery(db, project_name)
        dna = get_or_generate_dna(db, project_name, project_path)
        bridge = get_latest_bridge(db, project_name)
        db.commit()

        inject_agents_md(project_path, dna, bridge, crash_info)
        print(f"Project: {project_name}")
        print(f"DNA: {'generated' if dna else 'none'}")
        print(f"Bridge: {'yes' if bridge else 'none'}")
        print(f"Crash recovery: {'yes' if crash_info else 'none'}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
