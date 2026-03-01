"""identity_set — Set Project Identity Card fields."""

import hashlib
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session
from i18n import t

SAFETY_FIELDS = {
    "deploy_ssh_alias", "deploy_ssh_host", "deploy_ssh_port", "deploy_ssh_user",
    "deploy_app_port", "deploy_path", "deploy_method",
    "pm2_process_name", "pm2_process_id",
    "github_repo_url", "github_org", "git_production_branch",
    "domain_primary", "domain_aliases",
    "reverse_proxy", "reverse_proxy_config_path",
    "db_type", "db_connection_hint",
    "env_file_pattern", "env_secrets_note",
}

TECH_FIELDS = {
    "framework", "framework_version", "language",
    "css_approach", "ui_library", "db_technology",
    "hosting_pattern", "containerization",
    "design_system", "design_fonts", "design_notes",
    "build_tool", "package_manager", "project_category",
}

ALL_FIELDS = SAFETY_FIELDS | TECH_FIELDS


def _compute_safety_hash(identity: dict) -> str:
    values = []
    for field in sorted(SAFETY_FIELDS):
        values.append(f"{field}={identity.get(field, '')}")
    return hashlib.sha256("|".join(values).encode()).hexdigest()[:16]


def identity_set(fields: dict, lock_safety: bool = False) -> str:
    """Set Identity Card fields for current project."""
    session = get_active_session()
    project = session.get("project", "")
    session_id = session.get("session_id", "")

    if not project:
        return t("identity_set.no_project")

    # Validate field names
    invalid = [k for k in fields if k not in ALL_FIELDS]
    if invalid:
        return t("identity_set.unknown_fields",
                 invalid=', '.join(invalid), allowed=', '.join(sorted(ALL_FIELDS)))

    now = datetime.now().isoformat()

    db = open_db()
    try:
        existing = db.execute(
            "SELECT * FROM project_identity WHERE project = ?", (project,)
        ).fetchone()

        if existing:
            existing_dict = dict(existing)
            # Check if safety fields are locked and we're trying to change them
            if existing_dict.get("safety_locked_at") and not lock_safety:
                safety_changes = [k for k in fields if k in SAFETY_FIELDS]
                if safety_changes:
                    return t("identity_set.blocked_locked",
                             changes=', '.join(safety_changes))

            # Update existing
            set_parts = []
            params = []
            for k, v in fields.items():
                set_parts.append(f"{k} = ?")
                params.append(v)

                # Audit log for safety fields
                if k in SAFETY_FIELDS:
                    old_val = existing_dict.get(k)
                    if old_val != v:
                        db.execute("""
                            INSERT INTO identity_audit_log
                            (project, field_name, old_value, new_value, changed_by, session_id, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (project, k, str(old_val) if old_val else None,
                              str(v), "user-explicit", session_id, now))

            set_parts.append("updated = ?")
            params.append(now)
            params.append(project)

            db.execute(
                f"UPDATE project_identity SET {', '.join(set_parts)} WHERE project = ?",
                params
            )
        else:
            # Create new identity card
            columns = ["project", "created", "updated"]
            values = [project, now, now]
            for k, v in fields.items():
                columns.append(k)
                values.append(v)

            placeholders = ", ".join(["?"] * len(columns))
            db.execute(
                f"INSERT INTO project_identity ({', '.join(columns)}) VALUES ({placeholders})",
                values
            )

            # Audit log for new safety fields
            for k, v in fields.items():
                if k in SAFETY_FIELDS:
                    db.execute("""
                        INSERT INTO identity_audit_log
                        (project, field_name, old_value, new_value, changed_by, session_id, timestamp)
                        VALUES (?, ?, NULL, ?, ?, ?, ?)
                    """, (project, k, str(v), "user-explicit", session_id, now))

        # Lock safety if requested
        if lock_safety:
            # Get current full identity for hash
            current = dict(db.execute(
                "SELECT * FROM project_identity WHERE project = ?", (project,)
            ).fetchone())
            current.update(fields)
            lock_hash = _compute_safety_hash(current)

            db.execute("""
                UPDATE project_identity
                SET safety_locked_at = ?, safety_locked_by = 'user', safety_lock_hash = ?
                WHERE project = ?
            """, (now, lock_hash, project))

        db.commit()
    finally:
        db.close()

    # Format response
    lines = [t("identity_set.updated", project=project)]
    for k, v in fields.items():
        category = "[safety]" if k in SAFETY_FIELDS else "[tech]"
        lines.append(f"  {category} {k}: {v}")
    lock_status = t("identity_set.safety_locked") if lock_safety else t("identity_set.safety_unlocked")
    lines.append(t("identity_set.safety_status", status=lock_status))

    return "\n".join(lines)
