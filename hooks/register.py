"""Register CogniLayer in Claude Code settings.json."""

import json
from pathlib import Path

CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
COGNILAYER_HOME = Path.home() / ".cognilayer"


def register():
    """Add CogniLayer MCP server and hooks to settings.json."""
    # Use forward slashes for all paths (Git Bash compatibility on Windows)
    home_str = str(COGNILAYER_HOME).replace("\\", "/")
    server_path = f"{home_str}/mcp-server/server.py"

    # Read existing settings
    settings = {}
    if CLAUDE_SETTINGS.exists():
        settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))

    # Add MCP server
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    settings["mcpServers"]["cognilayer"] = {
        "command": "python",
        "args": [server_path]
    }

    # Add hooks
    if "hooks" not in settings:
        settings["hooks"] = {}

    hook_start = f"python {home_str}/hooks/on_session_start.py"
    hook_end = f"python {home_str}/hooks/on_session_end.py"
    hook_change = f"python {home_str}/hooks/on_file_change.py"

    cognilayer_hooks = {
        "SessionStart": {
            "matcher": "*",
            "hooks": [{"type": "command", "command": hook_start}]
        },
        "SessionEnd": {
            "matcher": "*",
            "hooks": [{"type": "command", "command": hook_end}]
        },
        "PostToolUse": {
            "matcher": "Write|Edit|NotebookEdit",
            "hooks": [{"type": "command", "command": hook_change}]
        },
    }

    for hook_type, new_entry in cognilayer_hooks.items():
        existing = settings.get("hooks", {}).get(hook_type, [])
        # Remove any existing CogniLayer entries
        filtered = [
            entry for entry in existing
            if not any(
                "cognilayer" in h.get("command", "") or ".cognilayer" in h.get("command", "")
                for h in entry.get("hooks", [])
            )
        ]
        # Append the new CogniLayer hook entry
        filtered.append(new_entry)
        settings["hooks"][hook_type] = filtered

    # Write back
    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    print(f"CogniLayer registered in {CLAUDE_SETTINGS}")
    print(f"  MCP server: {server_path}")
    print(f"  Hooks: SessionStart, SessionEnd, PostToolUse")
    return settings


if __name__ == "__main__":
    register()
