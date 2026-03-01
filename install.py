"""CogniLayer installer — copies files to ~/.cognilayer/ and registers in Claude Code.

Usage:
    python install.py           # Install for Claude Code (default)
    python install.py --codex   # Install for Codex CLI
    python install.py --both    # Install for both
"""

import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
CLAUDE_COMMANDS = Path.home() / ".claude" / "commands"
REPO_DIR = Path(__file__).parent.resolve()
VERSION = (REPO_DIR / "VERSION").read_text(encoding="utf-8").strip()
IS_SAME_DIR = REPO_DIR.resolve() == COGNILAYER_HOME.resolve()


def _find_scripts_dir() -> Path | None:
    """Find Python Scripts/bin directory that's likely in PATH."""
    if platform.system() == "Windows":
        # Python Scripts dir (usually in PATH on Windows)
        scripts = Path(sys.executable).parent / "Scripts"
        if scripts.exists():
            return scripts
    else:
        # ~/.local/bin is standard on Linux/Mac
        local_bin = Path.home() / ".local" / "bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        return local_bin
    return None


def check_python_version():
    if sys.version_info < (3, 11):
        print(f"ERROR: Python 3.11+ required (for tomllib). You have {sys.version}")
        sys.exit(1)


def check_mcp_installed():
    try:
        import mcp  # noqa: F401
        print("[ok] mcp package found")
    except ImportError:
        print("[!] mcp package not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp"])
        print("[ok] mcp installed")


def check_pyyaml_installed():
    try:
        import yaml  # noqa: F401
        print("[ok] pyyaml package found")
    except ImportError:
        print("[!] pyyaml package not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml"])
        print("[ok] pyyaml installed")


def check_textual_installed():
    try:
        import textual  # noqa: F401
        print(f"[ok] textual package found (v{textual.__version__})")
    except ImportError:
        print("[!] textual not found. Installing (needed for TUI dashboard)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "textual"])
        print("[ok] textual installed")


def backup_database():
    """Backup memory.db before migration if it exists."""
    db_path = COGNILAYER_HOME / "memory.db"
    if db_path.exists():
        backup_name = f"memory.db.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        backup_path = COGNILAYER_HOME / backup_name
        shutil.copy2(db_path, backup_path)
        print(f"  [ok] Database backed up: {backup_name}")


def install_git_hook():
    """Install post-commit hook for auto-deploy to ~/.cognilayer/."""
    git_dir = REPO_DIR / ".git"
    if not git_dir.exists():
        print("  [skip] Not a git repo — skipping hook")
        return
    hook_src = REPO_DIR / "hooks" / "git-post-commit"
    hook_dst = git_dir / "hooks" / "post-commit"
    if not hook_src.exists():
        print("  [skip] hooks/git-post-commit not found in repo")
        return
    if hook_dst.exists():
        # Check if it's already our hook
        if hook_dst.read_text(encoding="utf-8").strip() == hook_src.read_text(encoding="utf-8").strip():
            print("  [ok] post-commit hook already installed")
            return
        print("  [skip] post-commit hook exists (custom) — not overwriting")
        return
    shutil.copy2(hook_src, hook_dst)
    hook_dst.chmod(0o755)
    print("  [ok] post-commit hook installed (auto-deploy on commit)")


def install_cli_wrapper():
    """Install 'cognilayer' command so users can type it from anywhere."""
    scripts_dir = _find_scripts_dir()
    if not scripts_dir:
        print("  [skip] Could not find Scripts directory for CLI wrapper")
        return

    if platform.system() == "Windows":
        wrapper = scripts_dir / "cognilayer.bat"
        wrapper.write_text(
            '@echo off\n'
            f'python "{COGNILAYER_HOME / "tui" / "app.py"}" %*\n',
            encoding="utf-8",
        )
        print(f"  [ok] CLI wrapper installed: {wrapper}")
    else:
        wrapper = scripts_dir / "cognilayer"
        wrapper.write_text(
            '#!/usr/bin/env bash\n'
            f'python3 "{COGNILAYER_HOME / "tui" / "app.py"}" "$@"\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        print(f"  [ok] CLI wrapper installed: {wrapper}")

        # Check if ~/.local/bin is in PATH
        path_dirs = (os.environ.get("PATH") or "").split(":")
        if str(scripts_dir) not in path_dirs:
            print(f"  [!] Add to PATH: export PATH=\"{scripts_dir}:$PATH\"")


def _safe_copy(src: Path, dst: Path, label: str):
    """Copy file, skip if src == dst (running from ~/.cognilayer/)."""
    if src.resolve() == dst.resolve():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  [copy] {label}")


def copy_files():
    """Copy source files to ~/.cognilayer/"""
    if IS_SAME_DIR:
        print("  [info] Running from ~/.cognilayer/ — skipping file copy (already in place)")
        install_cli_wrapper()
        return
    dirs_to_create = [
        COGNILAYER_HOME,
        COGNILAYER_HOME / "mcp-server" / "indexer",
        COGNILAYER_HOME / "mcp-server" / "search",
        COGNILAYER_HOME / "mcp-server" / "tools",
        COGNILAYER_HOME / "hooks",
        COGNILAYER_HOME / "logs",
        COGNILAYER_HOME / "cache" / "embeddings",
        COGNILAYER_HOME / "tui" / "screens",
        COGNILAYER_HOME / "tui" / "widgets",
        CLAUDE_COMMANDS,
    ]
    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)

    # Copy MCP server files
    mcp_src = REPO_DIR / "mcp-server"
    mcp_dst = COGNILAYER_HOME / "mcp-server"

    for src_file in mcp_src.rglob("*.py"):
        rel = src_file.relative_to(mcp_src)
        dst_file = mcp_dst / rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        print(f"  [copy] mcp-server/{rel}")

    # Copy hooks
    hooks_src = REPO_DIR / "hooks"
    hooks_dst = COGNILAYER_HOME / "hooks"
    for src_file in hooks_src.glob("*.py"):
        shutil.copy2(src_file, hooks_dst / src_file.name)
        print(f"  [copy] hooks/{src_file.name}")

    # Copy TUI dashboard
    tui_src = REPO_DIR / "tui"
    tui_dst = COGNILAYER_HOME / "tui"
    if tui_src.exists():
        for src_file in tui_src.rglob("*.py"):
            rel = src_file.relative_to(tui_src)
            dst_file = tui_dst / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            print(f"  [copy] tui/{rel}")
        for src_file in tui_src.rglob("*.tcss"):
            rel = src_file.relative_to(tui_src)
            dst_file = tui_dst / rel
            shutil.copy2(src_file, dst_file)
            print(f"  [copy] tui/{rel}")

    # Copy config
    config_src = REPO_DIR / "config.yaml"
    config_dst = COGNILAYER_HOME / "config.yaml"
    if not config_dst.exists():
        shutil.copy2(config_src, config_dst)
        print("  [copy] config.yaml (new)")
    else:
        print("  [skip] config.yaml (already exists, not overwriting)")

    # Copy onboard helper
    helper_src = REPO_DIR / "onboard_helper.py"
    if helper_src.exists():
        shutil.copy2(helper_src, COGNILAYER_HOME / "onboard_helper.py")
        print("  [copy] onboard_helper.py")

    # Copy diagnostic tool
    diag_src = REPO_DIR / "diagnose.py"
    if diag_src.exists():
        shutil.copy2(diag_src, COGNILAYER_HOME / "diagnose.py")
        print("  [copy] diagnose.py")

    # Copy VERSION file
    shutil.copy2(REPO_DIR / "VERSION", COGNILAYER_HOME / "VERSION")
    print(f"  [copy] VERSION ({VERSION})")

    # Install CLI wrapper (cognilayer command)
    install_cli_wrapper()

    # Install git post-commit hook (auto-deploy on commit)
    install_git_hook()

    # Copy slash commands (locale-aware)
    config_dst = COGNILAYER_HOME / "config.yaml"
    language = "en"
    if config_dst.exists():
        try:
            import yaml
            with open(config_dst, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            language = cfg.get("language", "en")
        except Exception:
            pass
    commands_src = REPO_DIR / "commands" / language
    if not commands_src.exists():
        commands_src = REPO_DIR / "commands" / "en"
    for src_file in commands_src.glob("*.md"):
        shutil.copy2(src_file, CLAUDE_COMMANDS / src_file.name)
        print(f"  [copy] commands/{language}/{src_file.name}")


def init_database():
    """Initialize SQLite database."""
    sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))
    from init_db import init_db
    tables, all_names = init_db()
    print(f"  [ok] Database initialized: {len(all_names)} objects")


def register_mcp(codex: bool = False):
    """Register MCP server and hooks in Claude Code or Codex CLI."""
    sys.path.insert(0, str(COGNILAYER_HOME / "hooks"))
    sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))
    if codex:
        from register_codex import register
        register()
    else:
        from register import register
        register()


def test_server():
    """Test the server as a subprocess — exactly as Claude Code would start it.

    This catches dependency issues that in-process imports would miss
    (e.g., mcp not installed for the registered Python version).
    """
    import json as json_mod

    # Read registration info
    registered_python = sys.executable.replace("\\", "/")
    server_path = str(COGNILAYER_HOME / "mcp-server" / "server.py").replace("\\", "/")

    if CLAUDE_SETTINGS.exists():
        settings = json_mod.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        mcp_cfg = settings.get("mcpServers", {}).get("cognilayer", {})
        if mcp_cfg:
            registered_python = mcp_cfg.get("command", registered_python)
            server_path = (mcp_cfg.get("args") or [server_path])[0]
            print(f"[ok] MCP server registered in settings.json")
            print(f"     command: {registered_python}")
            print(f"     server:  {server_path}")
        else:
            print("[WARNING] MCP server NOT found in settings.json — registration may have failed")
    else:
        print("[WARNING] ~/.claude/settings.json not found — Claude Code may not be installed")

    # Verify Python executable exists
    python_path = Path(registered_python.replace("/", os.sep))
    if not python_path.exists():
        print(f"\n[WARNING] Python executable not found: {registered_python}")
        print(f"          MCP server will fail to start!")
        print(f"          Fix: re-run install.py with the correct Python")
        return

    # Actually run the server --test as subprocess (catches missing deps)
    print(f"\n  Testing server startup (subprocess)...")
    try:
        result = subprocess.run(
            [registered_python, server_path, "--test"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            # Count tools from output
            for line in result.stdout.split("\n"):
                if "Registered tools:" in line:
                    print(f"  {line.strip()}")
                if line.startswith("OK:") or line.startswith("\nOK:"):
                    print(f"\n[ok] {line.strip()}")
        else:
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            error = stderr or stdout
            print(f"\n[ERROR] Server test failed (exit code {result.returncode}):")
            # Show error, highlighting missing modules
            for line in error.split("\n"):
                if "ModuleNotFoundError" in line or "ImportError" in line:
                    print(f"  >>> {line}")
                    # Extract module name and suggest fix
                    if "No module named" in line and "'" in line:
                        module = line.split("'")[1]
                        print(f"\n  Fix: \"{registered_python}\" -m pip install {module}")
                elif line.strip():
                    print(f"  {line}")
    except subprocess.TimeoutExpired:
        print(f"\n[WARNING] Server test timed out (30s)")
    except Exception as e:
        print(f"\n[ERROR] Could not test server: {e}")


def main():
    codex_mode = "--codex" in sys.argv
    both_mode = "--both" in sys.argv
    target = "Codex CLI" if codex_mode else "Both" if both_mode else "Claude Code"

    print("=" * 50)
    print(f"  CogniLayer v{VERSION} Installer ({target})")
    print("=" * 50)
    print()

    print("[1/6] Checking Python version...")
    check_python_version()
    print(f"  [ok] Python {sys.version.split()[0]}")

    print("\n[2/6] Checking dependencies...")
    check_mcp_installed()
    check_pyyaml_installed()
    check_textual_installed()

    print("\n[3/6] Copying files...")
    copy_files()

    print("\n[4/6] Backing up database...")
    backup_database()

    print("\n[5/6] Initializing database...")
    init_database()

    print("\n[6/6] Registering...")
    if both_mode:
        register_mcp(codex=False)
        print()
        register_mcp(codex=True)
    else:
        register_mcp(codex=codex_mode)

    # Run verification
    print("\nRunning verification...")
    test_server()

    # Show diagnostic summary
    python_cmd = sys.executable.replace("\\", "/")
    print("\n" + "=" * 50)
    print(f"  CogniLayer v{VERSION} — Installation complete!")
    print("=" * 50)
    print()
    print(f"  Python:     {python_cmd}")
    print(f"  Home:       {str(COGNILAYER_HOME).replace(chr(92), '/')}")
    print(f"  Settings:   {str(CLAUDE_SETTINGS).replace(chr(92), '/')}" if not codex_mode else "")
    print()
    print("  Next steps:")
    print("  1. Restart Claude Code (required for MCP server to connect)")
    print("  2. Edit ~/.cognilayer/config.yaml — set projects.base_path")
    print("  3. Run /onboard to build initial memory")
    print("  4. Run /cognihelp to see all commands")
    print("  5. Run 'cognilayer' in terminal for TUI dashboard")
    print()
    print("  Trouble? Run: python diagnose.py --fix")
    print()


if __name__ == "__main__":
    main()
