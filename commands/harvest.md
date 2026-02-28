VOLITELNY — prubezny zapis faktu a running bridge pokryvaji 95%.
Pouzij /harvest kdyz chces explicitni shrnuti nebo doplnit architekturni fakty.

Analyzuj aktualni session a uloz klicove informace do CogniLayer pameti.

Kroky:
1. Projdi konverzaci a identifikuj (pouzij VSECH 14 typu):

   ZAKLADNI:
   - Rozhodnuti (proc jsme zvolili konkretni pristup) -> memory_write(type="decision")
   - Nove fakty o projektu -> memory_write(type="fact")
   - Vyresene problemy a jejich reseni -> memory_write(type="issue")
   - Otevrene ukoly -> memory_write(type="task")
   - Reusable patterns/snippets -> memory_write(type="pattern"|"skill")

   ROZSIRENE (DULEZITE — casto obsahuji nejhodnotnejsi znalosti):
   - Pasti a nebezpeci — veci co NEFUNGUJI -> memory_write(type="gotcha")
   - Presne postupy ktere se NESMI preskocit -> memory_write(type="procedure")
   - Chyby a jejich opravy (error -> fix) -> memory_write(type="error_fix")
   - Presne prikazy (deploy, build, SSH, DB) -> memory_write(type="command")
   - Vykonove limity a optimalizace -> memory_write(type="performance")
   - Jak komponenty/soubory komunikuji -> memory_write(type="api_contract")
   - Zavislosti mezi balicky/buildem/deployem -> memory_write(type="dependency")
   - Pravidla specificka pro projekt/klienta -> memory_write(type="client_rule")

   POZOR: Fakty ktere byly ulozeny PRUBEZNE behem session (proaktivni write)
   uz v pameti jsou. Zkontroluj existujici fakty pres memory_search a
   NEPREPISUJ je — pouze doplnuj co chybi.

2. ARCHITEKTURNI FAKTY — pri kazdem harvest zapis fakty o kodove architekture:
   - Ktere soubory za co odpovidaji a jak spolu souvisi
   - API endpointy: cesta, co dela, jake parametry, odkud se vola
   - Klicove funkce: nazev, ucel, kde jsou, co vraci
   - Datove toky: odkud kam data teci (API -> cache -> frontend)

3. Kazdy fakt MUSI byt self-contained:
   - SPATNE: "Pouzili jsme jose" (kdo? kde? proc?)
   - SPRAVNE: "MyProject pouziva jose library pro JWT autentizaci misto jsonwebtoken kvuli bezpecnostnim zranitelnostem"

4. Pro kazdy identifikovany fakt zavolej memory_write s:
   - content: self-contained popis
   - type: spravny typ
   - tags: relevantni tagy oddelene carkou
   - domain: oblast (auth, ui, deploy, seo, perf...)

5. Zavolej session_bridge s action "save" a shrnutim:
   - Decisions: klicova rozhodnuti
   - Progress: co bylo dokonceno
   - Open: co zustava rozpracovane (konkretni soubory/ukoly)
   - Notes: dulezite poznamky pro pristi session

6. Vypis uzivateli co bylo ulozeno (pocty dle typu).
