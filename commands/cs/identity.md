Spravuj Project Identity Card pro tento projekt.

Argumenty: $ARGUMENTS

Prikazy:
- `/identity` (bez argumentu) — zobraz aktualni Identity Card
- `/identity set <field>=<value> ...` — nastav pole
- `/identity lock` — zamkni safety pole (po potvrzeni)
- `/identity tech-from <project>` — zkopiruj tech stack z jineho projektu
- `/identity update <field>=<value> reason="..."` — zmen zamknute safety pole
- `/identity recommend [popis]` — doporuc tech stack pro novy projekt
- `/identity audit` — zobraz historii zmen safety poli
- `/identity server-map` — zobraz vsechny projekty na danem serveru

Kroky:
1. Parsuj argumenty (prazdne = zobraz kartu)
2. Pro "set": zavolej identity_set(fields)
   - Safety pole (deploy_*, pm2_*, github_*, domain_*, db_*, env_*):
     po zamknuti NELZE menit bez /identity update
   - Tech pole (framework, css_approach, design_system...):
     volne menitelne kdykoliv
3. Pro "lock": zobraz vsechna safety pole, pozadej uzivatele o potvrzeni,
   pak zamkni pres identity_set s lock_safety=true
4. Pro "tech-from": zavolej recommend_tech(similar_to=project),
   pak zkopiruj POUZE tech pole (safety zustane nedotcene)
5. Pro "update": zkontroluj ze pole je zamknute, pozadej reason,
   zaloguj zmenu do identity_audit_log pres identity_set
6. Pro "recommend": zavolej recommend_tech(description=args)
7. Pro "server-map": dotaz na vsechny projekty se stejnym deploy_ssh_alias,
   zobraz tabulku: projekt | port | PM2 | domain | metoda,
   zvyrazni konflikty (duplicitni porty!)
8. Pro "audit": dotaz na identity_audit_log pro aktualni projekt

Bezpecnost:
- Safety pole po zamknuti NELZE menit bez /identity update + reason
- /identity update VZDY zaloguje zmenu do audit logu
