OPTIONAL — proactive fact writing and running bridge cover 95%.
Use /harvest when you want an explicit summary or to add architectural facts.

Analyze the current session and save key information to CogniLayer memory.

Steps:
1. Review the conversation and identify (use ALL 14 types):

   BASIC:
   - Decisions (why we chose a specific approach) -> memory_write(type="decision")
   - New facts about the project -> memory_write(type="fact")
   - Resolved issues and their solutions -> memory_write(type="issue")
   - Open tasks -> memory_write(type="task")
   - Reusable patterns/snippets -> memory_write(type="pattern"|"skill")

   ADVANCED (IMPORTANT — often contains the most valuable knowledge):
   - Pitfalls and dangers — things that DON'T WORK -> memory_write(type="gotcha")
   - Exact procedures that MUST NOT be skipped -> memory_write(type="procedure")
   - Errors and their fixes (error -> fix) -> memory_write(type="error_fix")
   - Exact commands (deploy, build, SSH, DB) -> memory_write(type="command")
   - Performance limits and optimizations -> memory_write(type="performance")
   - How components/files communicate -> memory_write(type="api_contract")
   - Dependencies between packages/build/deploy -> memory_write(type="dependency")
   - Rules specific to project/client -> memory_write(type="client_rule")

   NOTE: Facts that were saved PROACTIVELY during the session
   are already in memory. Check existing facts via memory_search and
   DO NOT overwrite them — only add what's missing.

2. ARCHITECTURAL FACTS — on every harvest write facts about code architecture:
   - Which files are responsible for what and how they relate
   - API endpoints: path, what it does, parameters, where it's called from
   - Key functions: name, purpose, location, return value
   - Data flows: where data flows from/to (API -> cache -> frontend)

3. Every fact MUST be self-contained:
   - BAD: "We used jose" (who? where? why?)
   - GOOD: "MyProject uses jose library for JWT authentication instead of jsonwebtoken due to security vulnerabilities"

4. For each identified fact call memory_write with:
   - content: self-contained description
   - type: correct type
   - tags: relevant tags separated by comma
   - domain: area (auth, ui, deploy, seo, perf...)

5. Call session_bridge with action "save" and summary:
   - Decisions: key decisions
   - Progress: what was completed
   - Open: what remains in progress (specific files/tasks)
   - Notes: important notes for next session

6. List to the user what was saved (counts by type).
