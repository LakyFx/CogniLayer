Proved kompletni pruzkum aktualniho projektu a vybuduj zakladni pamet.

Kroky:
1. Projdi strukturu projektu (soubory, adresare, max depth 4)
2. Identifikuj a precti KLICOVE soubory:
   - Config: package.json, tsconfig.json, docker-compose.yml, .htaccess
   - Entry points: app/layout.tsx, index.php, server.ts, main.py
   - API: vsechny soubory v api/, routes/, app/api/
   - Auth: auth.*, middleware.*, login.*
   - DB: schema.*, models.*, migrations/
   - Deploy: deploy.md, Dockerfile, .github/workflows/
   - Styly: hlavni CSS soubor(y)
   - Config soubory: *.config.*, .env.example

3. Pro kazdy klicovy soubor zapis do pameti:
   - api_contract: jake endpointy existuji, co prijimaji/vraci
   - fact: jake komponenty/stranky existuji a co delaji
   - pattern: jake vzory se v projektu pouzivaji (auth, data flow, styling)
   - dependency: dulezite zavislosti a jejich konfigurace
   - command: build/deploy/start prikazy z package.json scripts

4. Zapis architekturni prehled:
   - Datovy tok: odkud kam data teci (API → cache → frontend)
   - Autentizace: jak funguje (session/JWT/OAuth, kde je implementovana)
   - Routing: jak je organizovany (file-based, custom router)
   - Stav: kde se drzi stav (DB, session, localStorage, context)

5. Detekuj a zapis:
   - gotcha: zname problemy viditelne z kodu (TODO komentare, hacky, workaroundy)
   - performance: potencialni vykonove problemy viditelne z kodu
   - client_rule: pravidla z CLAUDE.md, README, komentaru

6. Nastav Identity Card:
   - Tech pole: auto-detect (framework, CSS, DB, package manager)
   - Safety pole: extrahuj z deploy.md, .git/config, docker-compose.yml
   - Safety pole NEZAMYKAT — jen predvyplnit, uzivatel potvrdi pozdeji

7. Vypis uzivateli shrnuti:
   "Onboarding dokoncen pro {projekt}:
    - {N} faktu ulozeno ({breakdown dle typu})
    - {N} souboru zaindexovano ({N} chunku)
    - Identity Card: tech auto-detected, safety needs confirmation
    - Odhadovana uspora: ~{X}K tokenu na session"
