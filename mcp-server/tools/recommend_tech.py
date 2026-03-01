"""recommend_tech — Recommend tech stack based on similar projects."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from i18n import t


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
                lines = [t("recommend_tech.header") + "\n" + t("recommend_tech.based_on_project", project=similar_to)]
                lines.append(t("recommend_tech.recommended_stack"))
                for k, v in stack.items():
                    if v:
                        lines.append(f"- {k}: {v}")
                lines.append("\n" + t("recommend_tech.apply_hint", project=similar_to))
                return "\n".join(lines)
            else:
                return t("recommend_tech.no_identity", project=similar_to)

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
            return t("recommend_tech.no_projects")

        lines = [t("recommend_tech.header")]
        if description:
            lines.append(t("recommend_tech.based_on_desc", description=description))

        lines.append(t("recommend_tech.similar_projects"))
        for row in rows:
            r = dict(row)
            tech_parts = [v for v in [r.get("framework"), r.get("language"),
                                       r.get("css_approach"), r.get("db_technology")] if v]
            lines.append(f"- {r['project']}: {', '.join(tech_parts) or '?'} ({r.get('project_category', '?')})")

        lines.append("\n" + t("recommend_tech.apply_stack_hint"))
        lines.append(t("recommend_tech.edit_hint"))

        return "\n".join(lines)
    finally:
        db.close()
