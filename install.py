"""CogniLayer installer — copies files to ~/.cognilayer/ and registers in Claude Code."""

import shutil
import subprocess
import sys
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
CLAUDE_COMMANDS = Path.home() / ".claude" / "commands"
REPO_DIR = Path(__file__).parent


def check_python_version():
    if sys.version_info < (3, 10):
        print(f"ERROR: Python 3.10+ required. You have {sys.version}")
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


def register_mcp():
    """Register MCP server and hooks in Claude Code settings."""
    sys.path.insert(0, str(COGNILAYER_HOME / "hooks"))
    from register import register
    register()


def test_server():
    """Quick test to verify installation."""
    sys.path.insert(0, str(COGNILAYER_HOME / "mcp-server"))
    from server import test_tools
    count = test_tools()
    if count == 10:
        print(f"\n[ok] All {count} tools registered successfully.")
    else:
        print(f"\n[ERROR] Expected 10 tools, got {count}.")
        sys.exit(1)


def main():
    print("=" * 50)
    print("  CogniLayer Installer")
    print("=" * 50)
    print()

    print("[1/5] Checking Python version...")
    check_python_version()
    print(f"  [ok] Python {sys.version.split()[0]}")

    print("\n[2/5] Checking dependencies...")
    check_mcp_installed()
    check_pyyaml_installed()

    print("\n[3/5] Copying files...")
    copy_files()

    print("\n[4/5] Initializing database...")
    init_database()

    print("\n[5/5] Registering in Claude Code...")
    register_mcp()

    print("\n" + "=" * 50)
    print("  Installation complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Edit ~/.cognilayer/config.yaml")
    print("     Set projects.base_path to your projects directory")
    print()
    print("  2. Start Claude Code in any project:")
    print("     cd ~/projects/my-app && claude")
    print()
    print("  3. Run /onboard to build initial memory")
    print()
    print("  4. Run /status to verify everything works")
    print()

    # Optional: run test
    print("Running verification test...")
    test_server()


if __name__ == "__main__":
    main()
