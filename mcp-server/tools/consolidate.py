"""consolidate.py — Memory consolidation for CogniLayer.

Clusters related facts, assigns knowledge tiers, detects contradictions.
NEVER deletes anything — only organizes.

Usage:
    python tools/consolidate.py [project_name]
"""

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session
from i18n import t


def _find_clusters(db, project: str) -> int:
    """BFS on fact_links graph to find connected components. Returns cluster count."""
    # Load all facts for this project
    facts = db.execute(
        "SELECT id FROM facts WHERE project = ?", (project,)
    ).fetchall()
    fact_ids = {row[0] for row in facts}

    if not fact_ids:
        return 0

    # Build adjacency list from fact_links
    adj = defaultdict(set)
    links = db.execute("""
        SELECT fl.source_id, fl.target_id FROM fact_links fl
        JOIN facts f1 ON fl.source_id = f1.id
        WHERE f1.project = ?
    """, (project,)).fetchall()

    for row in links:
        src, tgt = row[0], row[1]
        if src in fact_ids and tgt in fact_ids:
            adj[src].add(tgt)
            adj[tgt].add(src)

    # BFS to find connected components
    visited = set()
    clusters = []

    for fact_id in fact_ids:
        if fact_id in visited or fact_id not in adj:
            continue
        # BFS from this node
        component = set()
        queue = [fact_id]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)

        if len(component) >= 2:
            clusters.append(component)

    # Write clusters to DB
    now = datetime.now().isoformat()

    # Clear old cluster assignments for this project
    db.execute("UPDATE facts SET cluster_id = NULL WHERE project = ?", (project,))

    # Remove old clusters for this project
    db.execute("DELETE FROM fact_clusters WHERE project = ?", (project,))

    for component in clusters:
        cursor = db.execute("""
            INSERT INTO fact_clusters (project, fact_count, created, updated)
            VALUES (?, ?, ?, ?)
        """, (project, len(component), now, now))
        cluster_id = cursor.lastrowid

        for fid in component:
            db.execute(
                "UPDATE facts SET cluster_id = ? WHERE id = ?",
                (cluster_id, fid)
            )

    db.commit()
    return len(clusters)


def _compute_tiers(db, project: str) -> dict:
    """Assign knowledge_tier based on heat + retrieval. Returns tier counts."""
    now = datetime.now()
    facts = db.execute("""
        SELECT id, heat_score, retrieval_count, timestamp, cluster_id
        FROM facts WHERE project = ?
    """, (project,)).fetchall()

    # Check which facts have links
    linked_ids = set()
    try:
        rows = db.execute("""
            SELECT DISTINCT source_id FROM fact_links
            WHERE source_id IN (SELECT id FROM facts WHERE project = ?)
            UNION
            SELECT DISTINCT target_id FROM fact_links
            WHERE target_id IN (SELECT id FROM facts WHERE project = ?)
        """, (project, project)).fetchall()
        linked_ids = {row[0] for row in rows}
    except Exception:
        pass

    counts = {"active": 0, "reference": 0, "archive": 0}

    for row in facts:
        fid, heat, retrieval, timestamp, cluster_id = row
        heat = heat or 0.0
        retrieval = retrieval or 0

        # Calculate age in days
        try:
            created = datetime.fromisoformat(timestamp)
            if created.tzinfo is not None:
                created = created.replace(tzinfo=None)
            age_days = max(0, (now - created).total_seconds() / 86400)
        except (ValueError, TypeError):
            age_days = 999

        has_links = fid in linked_ids

        # Tier assignment
        if heat >= 0.5 or retrieval >= 3 or age_days < 14:
            tier = "active"
        elif heat >= 0.1 and (retrieval >= 1 or has_links):
            tier = "reference"
        else:
            tier = "archive"

        counts[tier] += 1
        db.execute(
            "UPDATE facts SET knowledge_tier = ? WHERE id = ?",
            (tier, fid)
        )

    db.commit()
    return counts


def _detect_contradictions(db, project: str) -> int:
    """Find potential contradictions among linked facts. Returns count of new contradictions."""
    now = datetime.now().isoformat()
    new_count = 0

    # Find linked fact pairs with same source_file and type
    try:
        pairs = db.execute("""
            SELECT f1.id, f2.id, f1.content, f2.content,
                   f1.source_file, f1.type, f1.source_mtime, f2.source_mtime
            FROM fact_links fl
            JOIN facts f1 ON fl.source_id = f1.id
            JOIN facts f2 ON fl.target_id = f2.id
            WHERE f1.project = ?
              AND f1.source_file IS NOT NULL
              AND f2.source_file IS NOT NULL
              AND f1.source_file = f2.source_file
              AND f1.type = f2.type
              AND f1.id < f2.id
        """, (project,)).fetchall()
    except Exception:
        pairs = []

    for row in pairs:
        fid_a, fid_b = row[0], row[1]
        content_a, content_b = row[2], row[3]
        mtime_a, mtime_b = row[6], row[7]

        # Check if source file mtime differs (one is stale)
        if mtime_a and mtime_b and abs(mtime_a - mtime_b) > 1.0:
            # Check not already recorded
            existing = db.execute("""
                SELECT 1 FROM contradictions
                WHERE (fact_id_a = ? AND fact_id_b = ?)
                   OR (fact_id_a = ? AND fact_id_b = ?)
            """, (fid_a, fid_b, fid_b, fid_a)).fetchone()

            if not existing:
                reason = t("consolidate.stale_contradiction",
                           file=row[4], type=row[5])
                db.execute("""
                    INSERT INTO contradictions
                        (project, fact_id_a, fact_id_b, reason, detected)
                    VALUES (?, ?, ?, ?, ?)
                """, (project, fid_a, fid_b, reason, now))
                new_count += 1

    # Also check same domain+type facts created > 30 days apart
    try:
        domain_pairs = db.execute("""
            SELECT f1.id, f2.id, f1.domain, f1.type,
                   f1.timestamp, f2.timestamp
            FROM facts f1
            JOIN facts f2 ON f1.project = f2.project
                         AND f1.domain = f2.domain
                         AND f1.type = f2.type
                         AND f1.id < f2.id
            WHERE f1.project = ?
              AND f1.domain IS NOT NULL
              AND julianday(f2.timestamp) - julianday(f1.timestamp) > 30
        """, (project,)).fetchall()
    except Exception:
        domain_pairs = []

    for row in domain_pairs:
        fid_a, fid_b = row[0], row[1]

        existing = db.execute("""
            SELECT 1 FROM contradictions
            WHERE (fact_id_a = ? AND fact_id_b = ?)
               OR (fact_id_a = ? AND fact_id_b = ?)
        """, (fid_a, fid_b, fid_b, fid_a)).fetchone()

        if not existing:
            reason = t("consolidate.age_contradiction",
                       domain=row[2], type=row[3])
            db.execute("""
                INSERT INTO contradictions
                    (project, fact_id_a, fact_id_b, reason, detected)
                VALUES (?, ?, ?, ?, ?)
            """, (project, fid_a, fid_b, reason, now))
            new_count += 1

    db.commit()
    return new_count


def _summarize_clusters(db, project: str) -> int:
    """Generate labels for clusters without them. Returns count of labeled clusters."""
    clusters = db.execute("""
        SELECT id FROM fact_clusters WHERE project = ?
    """, (project,)).fetchall()

    labeled = 0
    now = datetime.now().isoformat()

    for cluster_row in clusters:
        cluster_id = cluster_row[0]

        # Get member facts' types and domains
        members = db.execute("""
            SELECT type, domain, substr(content, 1, 50) FROM facts
            WHERE cluster_id = ? AND project = ?
        """, (cluster_id, project)).fetchall()

        if not members:
            continue

        # Find dominant type and domain
        type_counts = defaultdict(int)
        domain_counts = defaultdict(int)
        previews = []

        for m in members:
            type_counts[m[0]] += 1
            if m[1]:
                domain_counts[m[1]] += 1
            previews.append(m[2])

        dominant_type = max(type_counts, key=type_counts.get)
        dominant_domain = max(domain_counts, key=domain_counts.get) if domain_counts else None

        if dominant_domain:
            label = f"{dominant_type} cluster: {dominant_domain}"
        else:
            label = f"{dominant_type} cluster ({len(members)} facts)"

        summary = "; ".join(previews[:5])
        if len(previews) > 5:
            summary += f" ... +{len(previews) - 5} more"

        db.execute("""
            UPDATE fact_clusters SET label = ?, summary = ?, fact_count = ?, updated = ?
            WHERE id = ?
        """, (label, summary, len(members), now, cluster_id))
        labeled += 1

    db.commit()
    return labeled


def should_auto_consolidate(db, project: str) -> bool:
    """Check if auto-consolidation should run. Conditions:
    1. Has not run in the last 24 hours for this project
    2. Project has at least 10 facts
    """
    try:
        row = db.execute(
            "SELECT last_consolidated FROM projects WHERE name = ?", (project,)
        ).fetchone()
        if row and row[0]:
            from datetime import timedelta
            last = datetime.fromisoformat(row[0])
            if last.tzinfo:
                last = last.replace(tzinfo=None)
            if (datetime.now() - last).total_seconds() < 86400:
                return False  # Ran within last 24h
    except Exception:
        pass  # Column may not exist

    count = db.execute(
        "SELECT COUNT(*) FROM facts WHERE project = ?", (project,)
    ).fetchone()[0]
    return count >= 10


def consolidate(project: str = None) -> str:
    """Run full memory consolidation for a project. Returns summary report."""
    if not project:
        session = get_active_session()
        project = session.get("project", "")

    if not project:
        return t("consolidate.no_project")

    db = open_db()
    try:
        cluster_count = _find_clusters(db, project)
        tier_counts = _compute_tiers(db, project)
        contradiction_count = _detect_contradictions(db, project)
        labeled = _summarize_clusters(db, project)

        # Mark consolidation time (best-effort)
        try:
            db.execute("UPDATE projects SET last_consolidated = ? WHERE name = ?",
                       (datetime.now().isoformat(), project))
            db.commit()
        except Exception:
            pass  # Column may not exist
    finally:
        db.close()

    return t("consolidate.report",
             project=project,
             clusters=cluster_count,
             labeled=labeled,
             active=tier_counts["active"],
             reference=tier_counts["reference"],
             archive=tier_counts["archive"],
             contradictions=contradiction_count)


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else None
    print(consolidate(proj))
