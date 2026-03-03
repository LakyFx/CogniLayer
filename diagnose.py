"""CogniLayer Diagnostic Tool — checks everything needed for MCP server to work.

Usage:
    python diagnose.py           # Run all checks
    python diagnose.py --fix     # Run checks and attempt auto-fixes

Exit codes:
    0 = all checks passed
    1 = some checks failed (see output)
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

COGNILAYER_HOME = Path.home() / ".cognilayer"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
FIX_MODE = "--fix" in sys.argv

# Colors (ANSI, works in modern terminals)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

results = []


def check(name: str, passed: bool, detail: str = "", fix_hint: str = ""):
    """Record a check result."""
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    results.append((name, passed, detail, fix_hint))
    print(f"  [{status}] {name}")
    if detail:
        print(f"         {detail}")
    if not passed and fix_hint:
        print(f"         {YELLOW}Fix: {fix_hint}{RESET}")
    return passed


def warn(name: str, detail: str = ""):
    """Record a warning (not a failure)."""
    print(f"  [{YELLOW}WARN{RESET}] {name}")
    if detail:
        print(f"         {detail}")


def check_python_version():
    """Check Python >= 3.11."""
    v = sys.version_info
    ok = v >= (3, 11)
    check(
        "Python version",
        ok,
        f"Python {v.major}.{v.minor}.{v.micro}",
        "Install Python 3.11+ from https://python.org" if not ok else "",
    )
    return ok


def check_cognilayer_home():
    """Check ~/.cognilayer/ exists."""
    ok = COGNILAYER_HOME.exists()
    check(
        "CogniLayer home directory",
        ok,
        str(COGNILAYER_HOME),
        "Run: python install.py" if not ok else "",
    )
    return ok


def check_database():
    """Check memory.db exists and has tables."""
    db_path = COGNILAYER_HOME / "memory.db"
    if not db_path.exists():
        check("Database exists", False, str(db_path), "Run: python install.py")
        return False

    import sqlite3
    try:
        db = sqlite3.connect(str(db_path))
        tables = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        db.close()
        has_core = all(t in tables for t in ["facts", "projects", "sessions"])
        has_code = "code_symbols" in tables
        detail = f"{len(tables)} tables found"
        if not has_core:
            detail += " (missing core tables: facts, projects, sessions)"
        elif not has_code:
            detail += " (missing Code Intelligence tables — re-run install.py)"
        check(
            "Database schema",
            has_core,
            detail,
            "Run: python install.py (will re-initialize schema)" if not has_core else "",
        )
        if has_core and not has_code:
            warn("Code Intelligence tables missing", "Run: python install.py to upgrade schema")
        return has_core
    except Exception as e:
        check("Database readable", False, str(e))
        return False


def check_mcp_package():
    """Check mcp package is importable."""
    try:
        import mcp  # noqa: F401
        version = getattr(mcp, "__version__", "unknown")
        check("mcp package", True, f"version {version}")
        return True
    except ImportError:
        ok = False
        if FIX_MODE:
            print(f"         {CYAN}Attempting auto-fix...{RESET}")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "mcp"],
                    stdout=subprocess.DEVNULL,
                )
                ok = True
                check("mcp package", True, "auto-installed")
            except Exception:
                pass
        if not ok:
            check(
                "mcp package",
                False,
                "Not installed",
                f"Run: {sys.executable} -m pip install mcp",
            )
        return ok


def check_pyyaml():
    """Check pyyaml is importable."""
    try:
        import yaml  # noqa: F401
        check("pyyaml package", True)
        return True
    except ImportError:
        ok = False
        if FIX_MODE:
            print(f"         {CYAN}Attempting auto-fix...{RESET}")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "pyyaml"],
                    stdout=subprocess.DEVNULL,
                )
                ok = True
                check("pyyaml package", True, "auto-installed")
            except Exception:
                pass
        if not ok:
            check(
                "pyyaml package",
                False,
                "Not installed",
                f"Run: {sys.executable} -m pip install pyyaml",
            )
        return ok


def check_textual():
    """Check textual is importable."""
    try:
        import textual  # noqa: F401
        check("textual package", True, f"v{textual.__version__}")
        return True
    except ImportError:
        ok = False
        if FIX_MODE:
            print(f"         {CYAN}Attempting auto-fix...{RESET}")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "textual"],
                    stdout=subprocess.DEVNULL,
                )
                ok = True
                check("textual package", True, "auto-installed")
            except Exception:
                pass
        if not ok:
            check(
                "textual package",
                False,
                "Not installed (needed for TUI)",
                f"Run: {sys.executable} -m pip install textual",
            )
        return ok


def check_treesitter():
    """Check tree-sitter-language-pack (required for Code Intelligence)."""
    try:
        import tree_sitter_language_pack  # noqa: F401
        check("tree-sitter-language-pack", True, "Code Intelligence available")
        return True
    except ImportError:
        ok = False
        if FIX_MODE:
            print(f"         {CYAN}Attempting auto-fix...{RESET}")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "tree-sitter-language-pack"],
                    stdout=subprocess.DEVNULL,
                )
                ok = True
                check("tree-sitter-language-pack", True, "auto-installed")
            except Exception:
                pass
        if not ok:
            check(
                "tree-sitter-language-pack",
                False,
                "Not installed (Code Intelligence disabled)",
                f"Run: {sys.executable} -m pip install tree-sitter-language-pack",
            )
        return ok


def check_optional_deps():
    """Check optional dependencies (fastembed, sqlite-vec)."""
    try:
        import fastembed  # noqa: F401
        check("fastembed (optional)", True, "vector search available")
    except ImportError:
        warn("fastembed not installed", "Vector search disabled (FTS5 still works)")

    try:
        import sqlite_vec  # noqa: F401
        check("sqlite-vec (optional)", True)
    except ImportError:
        warn("sqlite-vec not installed", "Vector search disabled (FTS5 still works)")


def check_settings_json():
    """Check Claude Code settings.json has CogniLayer registered."""
    if not CLAUDE_SETTINGS.exists():
        check(
            "settings.json exists",
            False,
            str(CLAUDE_SETTINGS),
            "Run: python install.py",
        )
        return False, None, None

    try:
        settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    except Exception as e:
        check("settings.json readable", False, str(e))
        return False, None, None

    mcp_cfg = settings.get("mcpServers", {}).get("cognilayer", {})
    if not mcp_cfg:
        check(
            "MCP server registered",
            False,
            "cognilayer not found in mcpServers",
            "Run: python install.py",
        )
        return False, None, None

    python_cmd = mcp_cfg.get("command", "")
    server_path = (mcp_cfg.get("args") or [""])[0]

    check("MCP server registered", True, f"command: {python_cmd}")

    # Check Python executable exists
    python_path = Path(python_cmd.replace("/", os.sep))
    python_exists = python_path.exists()
    check(
        "Registered Python exists",
        python_exists,
        str(python_path),
        f"Re-run: python install.py (will use current Python: {sys.executable})"
        if not python_exists else "",
    )

    # Check server.py exists
    server_file = Path(server_path.replace("/", os.sep))
    server_exists = server_file.exists()
    check(
        "Server script exists",
        server_exists,
        str(server_file),
        "Run: python install.py" if not server_exists else "",
    )

    return True, python_cmd, server_path


def check_server_subprocess(python_cmd: str, server_path: str):
    """Actually try to start the MCP server as Claude Code would."""
    print(f"\n  Testing server startup (as subprocess)...")
    print(f"  Command: {python_cmd} {server_path} --test")

    try:
        result = subprocess.run(
            [python_cmd, server_path, "--test"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(server_path).parent),
        )

        if result.returncode == 0:
            # Parse tool count from output
            lines = result.stdout.strip().split("\n")
            tool_count = None
            for line in lines:
                if "Registered tools:" in line:
                    try:
                        tool_count = int(line.split(":")[-1].strip())
                    except ValueError:
                        pass
            if tool_count and tool_count >= 13:
                check("Server startup test", True, f"{tool_count} tools registered")
            else:
                check("Server startup test", True, f"Exit code 0, output: {result.stdout[:100]}")
            return True
        else:
            # Server failed — show the error
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()
            error_msg = stderr or stdout or "(no output)"

            # Detect common issues
            if "ModuleNotFoundError" in error_msg:
                # Extract module name
                module = "unknown"
                for line in error_msg.split("\n"):
                    if "No module named" in line:
                        module = line.split("'")[1] if "'" in line else line
                        break
                check(
                    "Server startup test",
                    False,
                    f"Missing module: {module}",
                    f"Run: \"{python_cmd}\" -m pip install {module}",
                )
            elif "ImportError" in error_msg:
                check(
                    "Server startup test",
                    False,
                    f"Import error: {error_msg[:200]}",
                    f"Check that all dependencies are installed for: {python_cmd}",
                )
            else:
                check(
                    "Server startup test",
                    False,
                    f"Exit code {result.returncode}: {error_msg[:200]}",
                )
            return False

    except subprocess.TimeoutExpired:
        check("Server startup test", False, "Timeout (30s) — server may be hanging")
        return False
    except FileNotFoundError:
        check(
            "Server startup test",
            False,
            f"Python executable not found: {python_cmd}",
            "Re-run: python install.py",
        )
        return False
    except Exception as e:
        check("Server startup test", False, str(e))
        return False


def check_hooks():
    """Check hook files exist."""
    hooks = ["on_session_start.py", "on_session_end.py", "on_pre_compact.py", "on_file_change.py"]
    hooks_dir = COGNILAYER_HOME / "hooks"
    all_ok = True
    for hook in hooks:
        path = hooks_dir / hook
        if not path.exists():
            check(f"Hook: {hook}", False, "File missing", "Run: python install.py")
            all_ok = False
    if all_ok:
        check("Hook files", True, f"All {len(hooks)} hooks present")
    return all_ok


def check_mcp_for_registered_python(python_cmd: str):
    """Check if 'mcp' package is installed for the Python registered in settings.json."""
    if python_cmd == sys.executable.replace("\\", "/"):
        # Same Python — already checked above
        return True

    print(f"\n  Checking dependencies for registered Python: {python_cmd}")
    try:
        result = subprocess.run(
            [python_cmd, "-c", "import mcp; print(f'mcp={getattr(mcp, \"__version__\", \"ok\")}')"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            check("mcp in registered Python", True, result.stdout.strip())
            return True
        else:
            stderr = result.stderr.strip()
            check(
                "mcp in registered Python",
                False,
                f"mcp not importable: {stderr[:100]}",
                f"Run: \"{python_cmd}\" -m pip install mcp pyyaml",
            )
            if FIX_MODE:
                print(f"         {CYAN}Attempting auto-fix...{RESET}")
                try:
                    subprocess.check_call(
                        [python_cmd, "-m", "pip", "install", "mcp", "pyyaml"],
                        stdout=subprocess.DEVNULL,
                    )
                    print(f"         {GREEN}Fixed! mcp installed for {python_cmd}{RESET}")
                    return True
                except Exception as e:
                    print(f"         {RED}Auto-fix failed: {e}{RESET}")
            return False
    except FileNotFoundError:
        check(
            "mcp in registered Python",
            False,
            f"Python not found: {python_cmd}",
            "Re-run: python install.py",
        )
        return False
    except Exception as e:
        check("mcp in registered Python", False, str(e))
        return False


def main():
    print("=" * 55)
    print(f"  CogniLayer Diagnostic Tool {'(--fix mode)' if FIX_MODE else ''}")
    print("=" * 55)
    print(f"  Platform:  {platform.system()} {platform.release()}")
    print(f"  Python:    {sys.executable}")
    print(f"  Version:   {sys.version.split()[0]}")
    print()

    print("[1/7] Python version")
    check_python_version()

    print("\n[2/7] Dependencies (current Python)")
    check_mcp_package()
    check_pyyaml()
    check_textual()
    check_treesitter()
    check_optional_deps()

    print("\n[3/7] CogniLayer home")
    if check_cognilayer_home():
        check_database()

    print("\n[4/7] Claude Code registration")
    registered, python_cmd, server_path = check_settings_json()

    if registered and python_cmd:
        # KEY CHECK: is mcp installed for the Python that Claude Code will use?
        current_python = sys.executable.replace("\\", "/")
        if python_cmd != current_python:
            print(f"\n[5/7] Dependencies for REGISTERED Python")
            print(f"  {YELLOW}Note: registered Python differs from current!{RESET}")
            print(f"  Current:    {current_python}")
            print(f"  Registered: {python_cmd}")
            check_mcp_for_registered_python(python_cmd)
        else:
            print(f"\n[5/7] Dependencies for registered Python")
            check("Same as current Python", True, "No additional check needed")
    else:
        print(f"\n[5/7] Skipped (MCP not registered)")

    print("\n[6/7] Hook files")
    check_hooks()

    if registered and python_cmd and server_path:
        print(f"\n[7/7] Server startup test")
        check_server_subprocess(python_cmd, server_path)
    else:
        print(f"\n[7/7] Skipped (MCP not registered)")

    # Summary
    total = len(results)
    passed = sum(1 for _, ok, _, _ in results if ok)
    failed = total - passed

    print("\n" + "=" * 55)
    if failed == 0:
        print(f"  {GREEN}All {total} checks passed!{RESET}")
        print(f"  CogniLayer should work correctly.")
    else:
        print(f"  {RED}{failed} of {total} checks FAILED{RESET}")
        print()
        print(f"  Failed checks:")
        for name, ok, detail, fix_hint in results:
            if not ok:
                print(f"    - {name}")
                if fix_hint:
                    print(f"      {YELLOW}Fix: {fix_hint}{RESET}")
        if not FIX_MODE:
            print(f"\n  Tip: Run 'python diagnose.py --fix' to attempt auto-fixes")
    print("=" * 55)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
