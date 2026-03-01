Proved onboarding pro VSECHNY projekty v base_path (viz config.yaml).

Kroky:
1. Listuj vsechny adresare v base_path z config.yaml
2. Pro kazdy adresar ktery obsahuje kod (package.json, *.php, pyproject.toml):
   a) Registruj projekt v DB
   b) Proved /onboard (viz vyse)
   c) Loguj progress: "[3/20] Onboarding MyProject... hotovo (45 faktu, 120 chunku)"
3. Po dokonceni vsech:
   - Zobraz souhrnnou tabulku (projekt, fakty, chunky, stack, safety status)
   - Zobraz server-map (vsechny projekty se stejnym deploy_ssh_alias)
   - Upozorni na projekty kde chybi safety pole
   - Celkova statistika: "20 projektu, {N} faktu, {N} chunku, {X}MB DB"

POZOR:
- Onboarding JEDNOHO projektu trva ~2-5 minut (cteni, analyza, zapis)
- Vsech 20 projektu = ~30-60 minut
- Tokeny: kazdy projekt ~5-15K tokenu na analyzu
- Celkem: ~100-300K tokenu jednorazove (pak se to vrati v usporach)
