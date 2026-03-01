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
CLAUDE_COMMANDS = Path.home() / ".claude" / "commands"
REPO_DIR = Path(__file__).parent


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


def copy_files():
    """Copy source files to ~/.cognilayer/"""
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

    # Install CLI wrapper (cognilayer command)
    install_cli_wrapper()

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
    """Quick test to verify installation."""
    sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))
    from server import test_tools
    count = test_tools()
    if count == 13:
        print(f"\n[ok] All {count} tools registered successfully.")
    else:
        print(f"\n[ERROR] Expected 13 tools, got {count}.")
        sys.exit(1)


def main():
    codex_mode = "--codex" in sys.argv
    both_mode = "--both" in sys.argv
    target = "Codex CLI" if codex_mode else "Both" if both_mode else "Claude Code"

    print("=" * 50)
    print(f"  CogniLayer Installer ({target})")
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

    print("\n" + "=" * 50)
    print("  Installation complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Edit ~/.cognilayer/config.yaml")
    print("     Set projects.base_path to your projects directory")
    print()
    if codex_mode:
        print("  2. Start Codex CLI in any project:")
        print("     cd ~/projects/my-app && codex")
    else:
        print("  2. Start Claude Code in any project:")
        print("     cd ~/projects/my-app && claude")
    print()
    print("  3. Run /onboard to build initial memory")
    print()
    print("  4. Run /status to verify everything works")
    print()
    print("  5. Launch TUI dashboard (requires textual):")
    print("     cognilayer")
    print()

    # Optional: run test
    print("Running verification test...")
    test_server()


if __name__ == "__main__":
    main()
