"""Generate demo database with realistic fake data for TUI screenshots."""

import sqlite3
import uuid
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import sys
import random

# Reuse schema from init_db
sys.path.insert(0, str(Path.home() / ".cognilayer" / "mcp-server"))


def create_demo_db() -> str:
    """Create a temp DB with demo data. Returns path to temp DB."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False, prefix="cognilayer_demo_")
    db_path = tmp.name
    tmp.close()

    db = sqlite3.connect(db_path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")

    # Create minimal schema
    db.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            name TEXT PRIMARY KEY,
            path TEXT,
            dna TEXT,
            last_session TEXT
        );
        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY,
            project TEXT,
            content TEXT NOT NULL,
            type TEXT DEFAULT 'fact',
            domain TEXT,
            tags TEXT,
            source_file TEXT,
            source_hash TEXT,
            session_id TEXT,
            timestamp TEXT,
            heat_score REAL DEFAULT 1.0,
            retrieval_count INTEGER DEFAULT 0,
            knowledge_tier TEXT DEFAULT 'active',
            cluster_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            project TEXT,
            start_time TEXT,
            end_time TEXT,
            summary TEXT,
            bridge_content TEXT,
            episode_title TEXT,
            episode_tags TEXT,
            outcome TEXT,
            facts_count INTEGER DEFAULT 0,
            changes_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            project TEXT,
            file_path TEXT,
            action TEXT,
            timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS knowledge_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            query TEXT,
            hit_count INTEGER DEFAULT 0,
            best_score REAL DEFAULT 0.0,
            first_seen TEXT,
            last_seen TEXT,
            times_seen INTEGER DEFAULT 1,
            resolved INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS contradictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            fact_id_a TEXT,
            fact_id_b TEXT,
            reason TEXT,
            detected TEXT,
            resolved INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS fact_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            label TEXT,
            summary TEXT,
            fact_count INTEGER DEFAULT 0,
            created TEXT
        );
        CREATE TABLE IF NOT EXISTS fact_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id_a TEXT,
            fact_id_b TEXT,
            relation TEXT,
            created TEXT
        );
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            decision TEXT,
            reasoning TEXT,
            timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS project_identity (
            project TEXT PRIMARY KEY,
            data TEXT
        );
        CREATE TABLE IF NOT EXISTS identity_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            field TEXT,
            old_value TEXT,
            new_value TEXT,
            timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS tech_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            stack TEXT
        );
        CREATE TABLE IF NOT EXISTS causal_chains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cause_fact_id TEXT,
            effect_fact_id TEXT,
            relation TEXT,
            created TEXT
        );
    """)

    now = datetime.now()
    random.seed(42)  # Reproducible

    # --- Projects ---
    projects = [
        ("my-saas-app", "~/projects/my-saas-app", "Next.js 14 + Supabase + Stripe SaaS"),
        ("portfolio-site", "~/projects/portfolio-site", "Astro + TailwindCSS portfolio"),
        ("api-backend", "~/projects/api-backend", "FastAPI + PostgreSQL REST API"),
        ("mobile-app", "~/projects/mobile-app", "React Native + Expo mobile app"),
        ("discord-bot", "~/projects/discord-bot", "Discord.js bot with slash commands"),
    ]
    for name, path, dna in projects:
        db.execute("INSERT INTO projects VALUES (?, ?, ?, ?)",
                   (name, path, dna, (now - timedelta(hours=random.randint(1, 48))).isoformat()))

    # --- Facts ---
    demo_facts = [
        # my-saas-app
        ("my-saas-app", "Auth uses Supabase with row-level security (RLS) enabled on all tables", "fact", "auth", 0.92, "active"),
        ("my-saas-app", "Stripe webhook endpoint is /api/webhooks/stripe — must verify signature", "api_contract", "billing", 0.85, "active"),
        ("my-saas-app", "NEVER use getServerSideProps — all pages use App Router server components", "gotcha", "architecture", 0.95, "active"),
        ("my-saas-app", "Database migrations run via Supabase CLI: supabase db push", "command", "deploy", 0.78, "active"),
        ("my-saas-app", "Pricing page uses static data from /lib/pricing.ts — not from DB", "decision", "billing", 0.71, "active"),
        ("my-saas-app", "User onboarding flow: signup → verify email → select plan → dashboard", "procedure", "auth", 0.65, "reference"),
        ("my-saas-app", "Rate limiting on API: 100 req/min per user, implemented in middleware.ts", "pattern", "api", 0.58, "reference"),
        ("my-saas-app", "CSS uses Tailwind with custom design tokens in tailwind.config.ts", "fact", "ui", 0.42, "reference"),
        ("my-saas-app", "Image uploads go to Supabase Storage bucket 'avatars' with 5MB limit", "api_contract", "storage", 0.35, "reference"),
        ("my-saas-app", "Fixed: CORS error on /api/webhooks — needed to exclude from middleware auth check", "error_fix", "api", 0.28, "archive"),
        ("my-saas-app", "React Query cache time set to 5 minutes for dashboard data", "performance", "api", 0.22, "archive"),
        ("my-saas-app", "Deployment: Vercel with preview deploys on PR, production on main", "fact", "deploy", 0.15, "archive"),

        # portfolio-site
        ("portfolio-site", "Uses Astro content collections for blog posts in /src/content/blog/", "pattern", "architecture", 0.88, "active"),
        ("portfolio-site", "Contact form sends via Resend API — key in RESEND_API_KEY env var", "api_contract", "email", 0.75, "active"),
        ("portfolio-site", "Dark mode toggle uses prefers-color-scheme + localStorage fallback", "pattern", "ui", 0.62, "reference"),
        ("portfolio-site", "Images optimized with Astro Image component — WebP format, lazy loading", "performance", "ui", 0.45, "reference"),
        ("portfolio-site", "Deploy to Netlify via git push to main branch", "command", "deploy", 0.31, "archive"),

        # api-backend
        ("api-backend", "All endpoints require JWT auth except /health and /auth/login", "api_contract", "auth", 0.91, "active"),
        ("api-backend", "Database uses Alembic for migrations: alembic upgrade head", "command", "database", 0.82, "active"),
        ("api-backend", "Pydantic v2 models for request/response validation in /app/schemas/", "pattern", "architecture", 0.73, "active"),
        ("api-backend", "Background tasks use Celery with Redis broker on port 6379", "dependency", "infrastructure", 0.68, "active"),
        ("api-backend", "Fixed: N+1 query in /users endpoint — added joinedload for user.roles", "error_fix", "database", 0.55, "reference"),
        ("api-backend", "Pagination pattern: offset/limit with max 100 items, default 20", "pattern", "api", 0.41, "reference"),
        ("api-backend", "Docker compose: app (8000), postgres (5432), redis (6379), worker", "fact", "infrastructure", 0.33, "archive"),
        ("api-backend", "Test coverage at 84% — missing coverage in webhook handlers", "task", "testing", 0.19, "archive"),

        # mobile-app
        ("mobile-app", "Navigation uses React Navigation v6 with typed routes in /navigation/types.ts", "pattern", "navigation", 0.87, "active"),
        ("mobile-app", "Push notifications via Expo Push API — token stored in user profile", "api_contract", "notifications", 0.76, "active"),
        ("mobile-app", "Offline mode: AsyncStorage caches last 50 items, syncs on reconnect", "pattern", "storage", 0.64, "reference"),
        ("mobile-app", "GOTCHA: iOS simulator doesn't support push notifications — use TestFlight", "gotcha", "testing", 0.52, "reference"),
        ("mobile-app", "App store deployment: eas build + eas submit", "command", "deploy", 0.38, "archive"),

        # discord-bot
        ("discord-bot", "Commands registered via REST API on bot startup — not guild-specific", "fact", "architecture", 0.83, "active"),
        ("discord-bot", "Rate limit: 50 messages per channel per 10 seconds", "performance", "api", 0.69, "active"),
        ("discord-bot", "SQLite database for user XP/levels stored in /data/bot.db", "dependency", "database", 0.47, "reference"),
        ("discord-bot", "Fixed: Bot crashes on DM — added guild check before accessing member roles", "error_fix", "commands", 0.34, "archive"),
    ]

    fact_ids = []
    for i, (proj, content, ftype, domain, heat, tier) in enumerate(demo_facts):
        fid = str(uuid.uuid4())
        fact_ids.append((fid, proj))
        age_hours = int((1.0 - heat) * 200) + random.randint(0, 48)
        ts = (now - timedelta(hours=age_hours)).isoformat()
        retrieval = int(heat * 15) + random.randint(0, 5)
        tags = f"{domain},{ftype}" if random.random() > 0.5 else domain
        db.execute(
            "INSERT INTO facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fid, proj, content, ftype, domain, tags, f"src/{domain}/{ftype}.py",
             None, None, ts, heat, retrieval, tier, None)
        )

    # --- Sessions ---
    outcomes = ["productive", "debugging", "planning", "exploratory", "maintenance"]
    session_titles = [
        ("my-saas-app", "Bug fix: auth, billing", "debugging"),
        ("my-saas-app", "Decision: architecture", "planning"),
        ("my-saas-app", "Knowledge: api, deploy", "productive"),
        ("my-saas-app", "Session: ui, storage", "productive"),
        ("my-saas-app", "Procedure: auth", "productive"),
        ("portfolio-site", "Pattern: architecture, ui", "productive"),
        ("portfolio-site", "Knowledge: email, deploy", "exploratory"),
        ("portfolio-site", "Performance: ui", "maintenance"),
        ("api-backend", "Bug fix: database", "debugging"),
        ("api-backend", "Knowledge: auth, infrastructure", "productive"),
        ("api-backend", "Pattern: api, architecture", "productive"),
        ("api-backend", "Task: testing", "maintenance"),
        ("mobile-app", "Pattern: navigation, storage", "productive"),
        ("mobile-app", "Gotcha discovery: testing", "debugging"),
        ("mobile-app", "Knowledge: notifications", "exploratory"),
        ("discord-bot", "Bug fix: commands", "debugging"),
        ("discord-bot", "Knowledge: architecture, database", "productive"),
    ]

    for i, (proj, title, outcome) in enumerate(session_titles):
        sid = str(uuid.uuid4())
        start = now - timedelta(hours=(len(session_titles) - i) * 8 + random.randint(0, 4))
        end = start + timedelta(minutes=random.randint(15, 120))
        facts_c = random.randint(1, 8)
        changes_c = random.randint(2, 25)
        bridge = f"Progress: {title}. Changes: {changes_c} files modified. Open: continue with next feature."
        db.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, proj, start.isoformat(), end.isoformat(), None, bridge,
             title, proj, outcome, facts_c, changes_c)
        )

    # --- Knowledge Gaps ---
    gaps = [
        ("my-saas-app", "how to handle subscription cancellation", 0, 0.12, 4),
        ("my-saas-app", "email template customization", 0, 0.08, 2),
        ("api-backend", "websocket authentication pattern", 0, 0.15, 3),
        ("api-backend", "database backup procedure", 0, 0.05, 5),
        ("mobile-app", "deep linking configuration", 0, 0.21, 2),
        ("discord-bot", "slash command permissions", 1, 0.67, 1),
    ]
    for proj, query, resolved, score, times in gaps:
        first = (now - timedelta(days=random.randint(1, 14))).isoformat()
        last = (now - timedelta(hours=random.randint(1, 48))).isoformat()
        db.execute(
            "INSERT INTO knowledge_gaps (project, query, hit_count, best_score, first_seen, last_seen, times_seen, resolved) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (proj, query, 0, score, first, last, times, resolved)
        )

    # --- Contradictions ---
    if len(fact_ids) > 10:
        db.execute(
            "INSERT INTO contradictions (project, fact_id_a, fact_id_b, reason, detected, resolved) VALUES (?, ?, ?, ?, ?, ?)",
            ("my-saas-app", fact_ids[0][0], fact_ids[11][0],
             "Conflicting deployment targets: Vercel vs self-hosted mentioned",
             (now - timedelta(hours=12)).isoformat(), 0)
        )
        db.execute(
            "INSERT INTO contradictions (project, fact_id_a, fact_id_b, reason, detected, resolved) VALUES (?, ?, ?, ?, ?, ?)",
            ("api-backend", fact_ids[17][0], fact_ids[23][0],
             "Auth requirement conflict: JWT required vs public endpoints list mismatch",
             (now - timedelta(hours=6)).isoformat(), 0)
        )

    # --- Clusters ---
    cluster_data = [
        ("my-saas-app", "Authentication & Security", "Supabase auth, RLS, JWT, middleware", 4),
        ("my-saas-app", "Billing & Payments", "Stripe integration, pricing, webhooks", 3),
        ("my-saas-app", "Deployment & DevOps", "Vercel, CI/CD, database migrations", 3),
        ("api-backend", "Database Layer", "PostgreSQL, Alembic, query optimization", 4),
        ("api-backend", "API Design", "Pydantic, pagination, rate limiting", 3),
        ("mobile-app", "App Architecture", "Navigation, offline storage, notifications", 3),
    ]
    cluster_id = 1
    for proj, label, summary, count in cluster_data:
        db.execute(
            "INSERT INTO fact_clusters (id, project, label, summary, fact_count, created) VALUES (?, ?, ?, ?, ?, ?)",
            (cluster_id, proj, label, summary, count, (now - timedelta(hours=24)).isoformat())
        )
        # Assign some facts to clusters
        proj_facts = [f for f in fact_ids if f[1] == proj]
        for fid, _ in proj_facts[:count]:
            db.execute("UPDATE facts SET cluster_id = ? WHERE id = ?", (cluster_id, fid))
        cluster_id += 1

    # --- Changes (file change log) ---
    files = [
        "src/app/page.tsx", "src/app/api/auth/route.ts", "src/lib/stripe.ts",
        "src/components/Dashboard.tsx", "src/middleware.ts", "package.json",
        "src/app/api/webhooks/stripe/route.ts", "tailwind.config.ts",
    ]
    for i in range(45):
        proj = random.choice([p[0] for p in projects])
        db.execute(
            "INSERT INTO changes (project, file_path, action, timestamp) VALUES (?, ?, ?, ?)",
            (proj, random.choice(files), random.choice(["Write", "Edit"]),
             (now - timedelta(hours=random.randint(0, 96))).isoformat())
        )

    db.commit()
    db.close()
    return db_path
