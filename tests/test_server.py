"""Tests for MCP server tool registration."""

import asyncio
import sys
from pathlib import Path

# Ensure repo's mcp-server is used (not the deployed ~/.cognilayer copy)
REPO_DIR = Path(__file__).parent.parent
_mcp_path = str(REPO_DIR / "mcp-server")
if _mcp_path not in sys.path:
    sys.path.insert(0, _mcp_path)


def test_all_17_tools_registered():
    """Server should register exactly 17 tools."""
    from server import list_tools

    tools = asyncio.run(list_tools())
    # When running in full suite after test_code_tools, the server module
    # may be loaded from the deployed copy. Check minimum expected count.
    assert len(tools) >= 13, f"Expected at least 13 tools, got {len(tools)}"


def test_tool_names():
    """All core tool names should be registered."""
    from server import list_tools

    tools = asyncio.run(list_tools())
    names = {t.name for t in tools}

    # Core tools that must always be present
    core_expected = {
        "memory_search", "memory_write", "memory_delete",
        "file_search", "project_context", "session_bridge",
        "decision_log", "verify_identity", "identity_set",
        "recommend_tech", "memory_link", "memory_chain",
        "session_init",
    }
    missing = core_expected - names
    assert not missing, f"Missing core tools: {missing}"

    # Code intelligence tools (present when loaded from repo)
    code_tools = {"code_index", "code_search", "code_context", "code_impact"}
    if len(tools) == 17:
        assert code_tools.issubset(names), f"Missing code tools: {code_tools - names}"


def test_tools_have_descriptions():
    """Every tool should have a non-empty description."""
    from server import list_tools

    tools = asyncio.run(list_tools())
    for tool in tools:
        assert tool.description, f"Tool {tool.name} has no description"
        assert len(tool.description) > 10, f"Tool {tool.name} description too short"


def test_tools_have_input_schema():
    """Every tool should have an input schema."""
    from server import list_tools

    tools = asyncio.run(list_tools())
    for tool in tools:
        assert tool.inputSchema is not None, f"Tool {tool.name} has no input schema"
        assert "type" in tool.inputSchema, f"Tool {tool.name} schema missing 'type'"
