"""Register CogniLayer in Claude Code settings.json."""

import json
import sys
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

    settings["hooks"]["SessionStart"] = [
        {
            "matcher": "*",
            "hooks": [{"type": "command", "command": hook_start}]
        }
    ]

    settings["hooks"]["SessionEnd"] = [
        {
            "matcher": "*",
            "hooks": [{"type": "command", "command": hook_end}]
        }
    ]

    settings["hooks"]["PostToolUse"] = [
        {
            "matcher": "Write|Edit|NotebookEdit",
            "hooks": [{"type": "command", "command": hook_change}]
        }
    ]

    # Write back
    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    print(f"CogniLayer registered in {CLAUDE_SETTINGS}")
    print(f"  MCP server: {server_path}")
    print(f"  Hooks: SessionStart, SessionEnd, PostToolUse")
    return settings


if __name__ == "__main__":
    register()
