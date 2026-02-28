"""recommend_tech — Recommend tech stack based on similar projects."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db


def recommend_tech(description: str = None, similar_to: str = None,
                   category: str = None) -> str:
    """Recommend tech stack for a project based on existing projects."""
    db = open_db()
    try:
        results = []

        # If similar_to specified, get that project's identity
        if similar_to:
            row = db.execute("""
                SELECT framework, framework_version, language, css_approach,
                       ui_library, db_technology, hosting_pattern, containerization,
                       design_system, design_fonts, build_tool, package_manager,
                       project_category
                FROM project_identity WHERE project = ?
            """, (similar_to,)).fetchone()

            if row:
                stack = dict(row)
                lines = [f"## Tech doporuceni\n\nNa zaklade projektu: {similar_to}\n"]
                lines.append("Doporuceny stack:")
                for k, v in stack.items():
                    if v:
                        lines.append(f"- {k}: {v}")
                lines.append(f"\nPro aplikovani: /identity tech-from {similar_to}")
                return "\n".join(lines)
            else:
                return f"Projekt '{similar_to}' nema Identity Card."

        # Search by category
        if category:
            rows = db.execute("""
                SELECT project, framework, language, css_approach, db_technology,
                       hosting_pattern, project_category
                FROM project_identity
                WHERE project_category = ?
            """, (category,)).fetchall()
        else:
            rows = db.execute("""
                SELECT project, framework, language, css_approach, db_technology,
                       hosting_pattern, project_category
                FROM project_identity
                WHERE framework IS NOT NULL
            """).fetchall()

        if not rows:
            return "Zadne projekty s Identity Card v databazi. Pouzij /onboard pro registraci projektu."

        lines = ["## Tech doporuceni\n"]
        if description:
            lines.append(f"Na zaklade popisu: {description}\n")

        lines.append("Podobne projekty v portfoliu:")
        for row in rows:
            r = dict(row)
            tech_parts = [v for v in [r.get("framework"), r.get("language"),
                                       r.get("css_approach"), r.get("db_technology")] if v]
            lines.append(f"- {r['project']}: {', '.join(tech_parts) or '?'} ({r.get('project_category', '?')})")

        lines.append(f"\nPro aplikovani stacku: /identity tech-from <nazev-projektu>")
        lines.append(f"Pro upravu: /identity set framework=... css_approach=...")

        return "\n".join(lines)
    finally:
        db.close()
