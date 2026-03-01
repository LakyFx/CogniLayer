"""verify_identity — Safety gate before deploy/SSH/push operations."""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session
from i18n import t


# Required fields per action type
REQUIRED_FIELDS = {
    "deploy": ["deploy_ssh_alias", "deploy_ssh_host", "deploy_app_port",
               "deploy_path", "deploy_method", "domain_primary"],
    "ssh": ["deploy_ssh_alias", "deploy_ssh_host"],
    "push": ["github_repo_url", "git_production_branch"],
    "pm2": ["deploy_ssh_alias", "pm2_process_name"],
    "db-migrate": ["db_type", "db_connection_hint", "deploy_ssh_alias"],
    "docker-remote": ["deploy_ssh_alias", "deploy_ssh_host"],
    "proxy-reload": ["deploy_ssh_alias", "reverse_proxy"],
    "service-mgmt": ["deploy_ssh_alias", "deploy_ssh_host"],
}

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


def _compute_safety_hash(identity: dict) -> str:
    """Compute SHA256 hash of safety fields for tampering detection."""
    values = []
    for field in sorted(SAFETY_FIELDS):
        values.append(f"{field}={identity.get(field, '')}")
    return hashlib.sha256("|".join(values).encode()).hexdigest()[:16]


def verify_identity(action_type: str) -> str:
    """Verify project identity before sensitive operations."""
    session = get_active_session()
    project = session.get("project", "")

    if not project:
        return t("verify_identity.blocked_no_project")

    required = REQUIRED_FIELDS.get(action_type, [])
    if not required:
        return t("verify_identity.blocked_unknown_action",
                 action_type=action_type, allowed=', '.join(REQUIRED_FIELDS.keys()))

    db = open_db()
    try:
        row = db.execute(
            "SELECT * FROM project_identity WHERE project = ?", (project,)
        ).fetchone()
    finally:
        db.close()

    if not row:
        not_set = t("verify_identity.not_set")
        missing = ", ".join(f"- {f}: {not_set}" for f in required)
        return t("verify_identity.blocked_no_identity",
                 project=project, action_type=action_type, missing=missing)

    identity = dict(row)

    # Check required fields
    missing = []
    for field in required:
        if not identity.get(field):
            missing.append(field)

    if missing:
        not_set = t("verify_identity.not_set")
        missing_str = "\n".join(f"- {f}: {not_set}" for f in missing)
        return t("verify_identity.blocked_missing_fields",
                 action_type=action_type, missing=missing_str)

    # Check if locked
    if not identity.get("safety_locked_at"):
        not_set = t("verify_identity.not_set")
        fields_str = "\n".join(
            f"- {f}: {identity.get(f, not_set)}" for f in required
        )
        return t("verify_identity.warning_unlocked", fields=fields_str)

    # Verify hash integrity
    stored_hash = identity.get("safety_lock_hash", "")
    computed_hash = _compute_safety_hash(identity)
    if stored_hash and stored_hash != computed_hash:
        return t("verify_identity.blocked_tampered",
                 expected=stored_hash, actual=computed_hash)

    # VERIFIED
    return t("verify_identity.verified",
             project=project,
             ssh_alias=identity.get('deploy_ssh_alias', '?'),
             ssh_host=identity.get('deploy_ssh_host', '?'),
             app_port=identity.get('deploy_app_port', '?'),
             deploy_path=identity.get('deploy_path', '?'),
             pm2_name=identity.get('pm2_process_name', '?'),
             pm2_id=identity.get('pm2_process_id', '?'),
             domain=identity.get('domain_primary', '?'),
             method=identity.get('deploy_method', '?'),
             branch=identity.get('git_production_branch', '?'),
             action_type=action_type)
