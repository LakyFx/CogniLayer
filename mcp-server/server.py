"""CogniLayer MCP Server — Phase 1 (FTS5 only).

Entry point for the MCP server registered in ~/.claude/settings.json.
Provides 10 tools for Claude Code to interact with CogniLayer memory.
"""

import sys
import json
from pathlib import Path

# Ensure our package is importable
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools.memory_search import memory_search
from tools.memory_write import memory_write
from tools.memory_delete import memory_delete
from tools.file_search import file_search
from tools.project_context import project_context
from tools.session_bridge import session_bridge
from tools.decision_log import decision_log
from tools.verify_identity import verify_identity
from tools.identity_set import identity_set
from tools.recommend_tech import recommend_tech
from i18n import t

server = Server("cognilayer")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="memory_search",
            description=t("tool.memory_search.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": t("tool.memory_search.param.query")
                    },
                    "scope": {
                        "type": "string",
                        "description": t("tool.memory_search.param.scope"),
                        "default": "project"
                    },
                    "type": {
                        "type": "string",
                        "description": t("tool.memory_search.param.type")
                    },
                    "limit": {
                        "type": "integer",
                        "description": t("tool.memory_search.param.limit"),
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memory_write",
            description=t("tool.memory_write.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": t("tool.memory_write.param.content")
                    },
                    "type": {
                        "type": "string",
                        "description": t("tool.memory_write.param.type"),
                        "default": "fact"
                    },
                    "tags": {
                        "type": "string",
                        "description": t("tool.memory_write.param.tags")
                    },
                    "domain": {
                        "type": "string",
                        "description": t("tool.memory_write.param.domain")
                    },
                    "source_file": {
                        "type": "string",
                        "description": t("tool.memory_write.param.source_file")
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="memory_delete",
            description=t("tool.memory_delete.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": t("tool.memory_delete.param.ids")
                    }
                },
                "required": ["ids"]
            }
        ),
        Tool(
            name="file_search",
            description=t("tool.file_search.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": t("tool.file_search.param.query")
                    },
                    "scope": {
                        "type": "string",
                        "description": t("tool.file_search.param.scope"),
                        "default": "project"
                    },
                    "file_filter": {
                        "type": "string",
                        "description": t("tool.file_search.param.file_filter")
                    },
                    "limit": {
                        "type": "integer",
                        "description": t("tool.file_search.param.limit"),
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="project_context",
            description=t("tool.project_context.desc"),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="session_bridge",
            description=t("tool.session_bridge.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": t("tool.session_bridge.param.action"),
                        "enum": ["load", "save"]
                    },
                    "content": {
                        "type": "string",
                        "description": t("tool.session_bridge.param.content")
                    }
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="decision_log",
            description=t("tool.decision_log.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": t("tool.decision_log.param.query")
                    },
                    "project": {
                        "type": "string",
                        "description": t("tool.decision_log.param.project")
                    },
                    "limit": {
                        "type": "integer",
                        "description": t("tool.decision_log.param.limit"),
                        "default": 5
                    }
                }
            }
        ),
        Tool(
            name="verify_identity",
            description=t("tool.verify_identity.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "description": t("tool.verify_identity.param.action_type"),
                        "enum": ["deploy", "ssh", "push", "pm2", "db-migrate",
                                 "docker-remote", "proxy-reload", "service-mgmt"]
                    }
                },
                "required": ["action_type"]
            }
        ),
        Tool(
            name="identity_set",
            description=t("tool.identity_set.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "object",
                        "description": t("tool.identity_set.param.fields")
                    },
                    "lock_safety": {
                        "type": "boolean",
                        "description": t("tool.identity_set.param.lock_safety"),
                        "default": False
                    }
                },
                "required": ["fields"]
            }
        ),
        Tool(
            name="recommend_tech",
            description=t("tool.recommend_tech.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": t("tool.recommend_tech.param.description")
                    },
                    "similar_to": {
                        "type": "string",
                        "description": t("tool.recommend_tech.param.similar_to")
                    },
                    "category": {
                        "type": "string",
                        "description": t("tool.recommend_tech.param.category")
                    }
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "memory_search":
            result = memory_search(
                query=arguments["query"],
                scope=arguments.get("scope", "project"),
                type=arguments.get("type"),
                limit=arguments.get("limit", 5)
            )
        elif name == "memory_write":
            result = memory_write(
                content=arguments["content"],
                type=arguments.get("type", "fact"),
                tags=arguments.get("tags"),
                domain=arguments.get("domain"),
                source_file=arguments.get("source_file")
            )
        elif name == "memory_delete":
            result = memory_delete(ids=arguments["ids"])
        elif name == "file_search":
            result = file_search(
                query=arguments["query"],
                scope=arguments.get("scope", "project"),
                file_filter=arguments.get("file_filter"),
                limit=arguments.get("limit", 5)
            )
        elif name == "project_context":
            result = project_context()
        elif name == "session_bridge":
            result = session_bridge(
                action=arguments["action"],
                content=arguments.get("content")
            )
        elif name == "decision_log":
            result = decision_log(
                query=arguments.get("query"),
                project=arguments.get("project"),
                limit=arguments.get("limit", 5)
            )
        elif name == "verify_identity":
            result = verify_identity(action_type=arguments["action_type"])
        elif name == "identity_set":
            result = identity_set(
                fields=arguments["fields"],
                lock_safety=arguments.get("lock_safety", False)
            )
        elif name == "recommend_tech":
            result = recommend_tech(
                description=arguments.get("description"),
                similar_to=arguments.get("similar_to"),
                category=arguments.get("category")
            )
        else:
            result = t("server.unknown_tool", name=name)
    except Exception as e:
        result = t("server.tool_error", name=name, error=str(e))

    return [TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def test_tools():
    """Quick test to verify all tools are registered."""
    import asyncio

    async def _test():
        tools = await list_tools()
        print(f"Registered tools: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:60]}...")
        return len(tools)

    count = asyncio.run(_test())
    return count


if __name__ == "__main__":
    if "--test" in sys.argv:
        count = test_tools()
        if count == 10:
            print(f"\nOK: All {count} tools registered.")
        else:
            print(f"\nERROR: Expected 10 tools, got {count}.")
            sys.exit(1)
    else:
        import asyncio
        asyncio.run(main())
