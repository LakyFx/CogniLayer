Perform onboarding for ALL projects in base_path (see config.yaml).

Steps:
1. List all directories in base_path from config.yaml
2. For each directory that contains code (package.json, *.php, pyproject.toml):
   a) Register project in DB
   b) Perform /onboard (see above)
   c) Log progress: "[3/20] Onboarding MyProject... done (45 facts, 120 chunks)"
3. After completing all:
   - Show summary table (project, facts, chunks, stack, safety status)
   - Show server-map (all projects with same deploy_ssh_alias)
   - Warn about projects missing safety fields
   - Total statistics: "20 projects, {N} facts, {N} chunks, {X}MB DB"

NOTE:
- Onboarding ONE project takes ~2-5 minutes (reading, analysis, writing)
- All 20 projects = ~30-60 minutes
- Tokens: each project ~5-15K tokens for analysis
- Total: ~100-300K tokens one-time (then pays back in savings)
