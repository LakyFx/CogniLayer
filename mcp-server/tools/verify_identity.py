"""verify_identity — Safety gate before deploy/SSH/push operations."""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import open_db
from utils import get_active_session


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
        return "BLOCKED — Zadny aktivni projekt."

    required = REQUIRED_FIELDS.get(action_type, [])
    if not required:
        return f"BLOCKED — Neznamy action_type: {action_type}. Povolene: {', '.join(REQUIRED_FIELDS.keys())}"

    db = open_db()
    try:
        row = db.execute(
            "SELECT * FROM project_identity WHERE project = ?", (project,)
        ).fetchone()
    finally:
        db.close()

    if not row:
        missing = ", ".join(f"- {f}: [NENASTAVENO]" for f in required)
        return (
            f"BLOCKED — Projekt '{project}' nema Identity Card.\n"
            f"Chybi safety pole pro '{action_type}':\n{missing}\n\n"
            f"ZEPTEJ SE uzivatele na tyto hodnoty.\n"
            f"Pouzij /identity set pro konfiguraci."
        )

    identity = dict(row)

    # Check required fields
    missing = []
    for field in required:
        if not identity.get(field):
            missing.append(field)

    if missing:
        missing_str = "\n".join(f"- {f}: [NENASTAVENO]" for f in missing)
        return (
            f"BLOCKED — Chybi safety pole pro '{action_type}':\n{missing_str}\n\n"
            f"ZEPTEJ SE uzivatele na tyto hodnoty.\n"
            f"Pouzij /identity set pro konfiguraci."
        )

    # Check if locked
    if not identity.get("safety_locked_at"):
        fields_str = "\n".join(
            f"- {f}: {identity.get(f, '[NENASTAVENO]')}" for f in required
        )
        return (
            f"WARNING — Identity pole existuji ale NEJSOU ZAMKNUTE.\n\n"
            f"Aktualni hodnoty:\n{fields_str}\n\n"
            f"Prezentuj hodnoty uzivateli a pozadej explicitni potvrzeni.\n"
            f"Pro zamknuti: /identity lock"
        )

    # Verify hash integrity
    stored_hash = identity.get("safety_lock_hash", "")
    computed_hash = _compute_safety_hash(identity)
    if stored_hash and stored_hash != computed_hash:
        return (
            f"BLOCKED — Safety pole byla zmenena mimo /identity update!\n"
            f"Hash nesedi: expected {stored_hash}, got {computed_hash}\n"
            f"Pouzij /identity lock pro re-zamknuti."
        )

    # VERIFIED
    return (
        f"VERIFIED — Project: {project}\n"
        f"Server: {identity.get('deploy_ssh_alias', '?')} ({identity.get('deploy_ssh_host', '?')})\n"
        f"App Port: {identity.get('deploy_app_port', '?')}\n"
        f"Deploy Path: {identity.get('deploy_path', '?')}\n"
        f"PM2: {identity.get('pm2_process_name', '?')} (id={identity.get('pm2_process_id', '?')})\n"
        f"Domain: {identity.get('domain_primary', '?')}\n"
        f"Method: {identity.get('deploy_method', '?')}\n"
        f"Git Branch: {identity.get('git_production_branch', '?')}\n\n"
        f"POTVRD s uzivatelem: 'Budu {action_type} na {identity.get('deploy_ssh_alias', '?')} "
        f"pro {identity.get('domain_primary', '?')}.'"
    )
