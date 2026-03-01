Manage Project Identity Card for this project.

Arguments: $ARGUMENTS

Commands:
- `/identity` (no arguments) — show current Identity Card
- `/identity set <field>=<value> ...` — set fields
- `/identity lock` — lock safety fields (after confirmation)
- `/identity tech-from <project>` — copy tech stack from another project
- `/identity update <field>=<value> reason="..."` — change locked safety fields
- `/identity recommend [description]` — recommend tech stack for new project
- `/identity audit` — show history of safety field changes
- `/identity server-map` — show all projects on a given server

Steps:
1. Parse arguments (empty = show card)
2. For "set": call identity_set(fields)
   - Safety fields (deploy_*, pm2_*, github_*, domain_*, db_*, env_*):
     after locking CANNOT be changed without /identity update
   - Tech fields (framework, css_approach, design_system...):
     freely changeable at any time
3. For "lock": show all safety fields, ask user for confirmation,
   then lock via identity_set with lock_safety=true
4. For "tech-from": call recommend_tech(similar_to=project),
   then copy ONLY tech fields (safety stays untouched)
5. For "update": verify field is locked, request reason,
   log change to identity_audit_log via identity_set
6. For "recommend": call recommend_tech(description=args)
7. For "server-map": query all projects with same deploy_ssh_alias,
   display table: project | port | PM2 | domain | method,
   highlight conflicts (duplicate ports!)
8. For "audit": query identity_audit_log for current project

Security:
- Safety fields after locking CANNOT be changed without /identity update + reason
- /identity update ALWAYS logs change to audit log
