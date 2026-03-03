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
- memory_search(query) — search memory semantically
- memory_write(content) — save important information
- file_search(query) — search project files (PRD, docs...)
- decision_log(query) — find past decisions
- session_bridge(action) — load/save session continuity
- session_init(project_path) — initialize session (CALL THIS FIRST)

## SESSION LIFECYCLE — CRITICAL
Codex has no hooks, so YOU must manage the session lifecycle:
1. **AT START**: Call `session_init()` — returns DNA + bridge + crash recovery
2. **DURING WORK**: Use memory_write proactively to save findings
3. **AT END**: Call `session_bridge(action="save", content="Progress: ...; Open: ...")`

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
- memory_search(query) — prohledej pamet semanticky
- memory_write(content) — zapamatuj si dulezitou informaci
- file_search(query) — hledej v projektovych souborech (PRD, docs...)
- decision_log(query) — najdi minula rozhodnuti
- session_bridge(action) — nacti/uloz kontinuitu session
- session_init(project_path) — inicializuj session (ZAVOLEJ JAKO PRVNI)

## ZIVOTNI CYKLUS SESSION — KRITICKE
Codex nema hooks, takze TY musis ridit zivotni cyklus session:
1. **NA ZACATKU**: Zavolej `session_init()` — vrati DNA + bridge + crash recovery
2. **BEHEM PRACE**: Pouzivej memory_write proaktivne pro ukladani poznatku
3. **NA KONCI**: Zavolej `session_bridge(action="save", content="Progress: ...; Open: ...")`

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
