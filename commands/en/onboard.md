Perform a complete scan of the current project and build initial memory.

Steps:
1. Scan project structure (files, directories, max depth 4)
2. Identify and read KEY files:
   - Config: package.json, tsconfig.json, docker-compose.yml, .htaccess
   - Entry points: app/layout.tsx, index.php, server.ts, main.py
   - API: all files in api/, routes/, app/api/
   - Auth: auth.*, middleware.*, login.*
   - DB: schema.*, models.*, migrations/
   - Deploy: deploy.md, Dockerfile, .github/workflows/
   - Styles: main CSS file(s)
   - Config files: *.config.*, .env.example

3. For each key file write to memory:
   - api_contract: what endpoints exist, what they accept/return
   - fact: what components/pages exist and what they do
   - pattern: what patterns are used in the project (auth, data flow, styling)
   - dependency: important dependencies and their configuration
   - command: build/deploy/start commands from package.json scripts

4. Write architectural overview:
   - Data flow: where data flows from/to (API -> cache -> frontend)
   - Authentication: how it works (session/JWT/OAuth, where implemented)
   - Routing: how it's organized (file-based, custom router)
   - State: where state is kept (DB, session, localStorage, context)

5. Detect and write:
   - gotcha: known problems visible from code (TODO comments, hacks, workarounds)
   - performance: potential performance issues visible from code
   - client_rule: rules from CLAUDE.md, README, comments

6. Set Identity Card:
   - Tech fields: auto-detect (framework, CSS, DB, package manager)
   - Safety fields: extract from deploy.md, .git/config, docker-compose.yml
   - Safety fields DO NOT LOCK — just pre-fill, user confirms later

7. Show summary to user:
   "Onboarding complete for {project}:
    - {N} facts saved ({breakdown by type})
    - {N} files indexed ({N} chunks)
    - Identity Card: tech auto-detected, safety needs confirmation
    - Estimated savings: ~{X}K tokens per session"
