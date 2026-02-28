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

server = Server("cognilayer")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="memory_search",
            description=(
                "Prohledej CogniLayer pamet. Najde relevantni informace "
                "z minulych sessions, rozhodnuti, patterns a faktu. "
                "Automaticky detekuje STALE fakty (source_file se zmenil)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Co hledas. Prirozeny jazyk."
                    },
                    "scope": {
                        "type": "string",
                        "description": "project (default) | all | {project_name}",
                        "default": "project"
                    },
                    "type": {
                        "type": "string",
                        "description": "Typ faktu: decision|fact|pattern|issue|task|skill|gotcha|procedure|error_fix|command|performance|api_contract|dependency|client_rule"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max pocet vysledku (default 5, max 10)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memory_write",
            description=(
                "Uloz dulezitou informaci do CogniLayer pameti. "
                "Pouzivej PROAKTIVNE — ukladej jak se ucis, ne jen pri /harvest."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Co si zapamatovat. Musi byt self-contained."
                    },
                    "type": {
                        "type": "string",
                        "description": "Typ: fact|decision|pattern|issue|task|skill|gotcha|procedure|error_fix|command|performance|api_contract|dependency|client_rule",
                        "default": "fact"
                    },
                    "tags": {
                        "type": "string",
                        "description": "Tagy oddelene carkou."
                    },
                    "domain": {
                        "type": "string",
                        "description": "Oblast: auth, ui, deploy, seo..."
                    },
                    "source_file": {
                        "type": "string",
                        "description": "Relativni cesta k souboru kde byl fakt pozorovan."
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="memory_delete",
            description="Smaz fakty z CogniLayer pameti podle ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "UUID faktu ke smazani."
                    }
                },
                "required": ["ids"]
            }
        ),
        Tool(
            name="file_search",
            description=(
                "Prohledej indexovane projektove soubory (PRD, handoff, docs). "
                "Vraci relevantni sekce/chunky MISTO celych souboru — setri kontext."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Co hledas v projektovych souborech."
                    },
                    "scope": {
                        "type": "string",
                        "description": "project (default) | {project_name}",
                        "default": "project"
                    },
                    "file_filter": {
                        "type": "string",
                        "description": "Glob pattern, napr. *.md nebo PRD*"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max pocet chunku (default 5, max 10)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="project_context",
            description="Vrati Project DNA a aktualni kontext pro detekovany projekt.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="session_bridge",
            description="Nacti nebo uloz session bridge (shrnuti session pro kontinuitu).",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "load | save",
                        "enum": ["load", "save"]
                    },
                    "content": {
                        "type": "string",
                        "description": "Obsah bridge (pouze pro save)."
                    }
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="decision_log",
            description="Prohledej log rozhodnuti pro aktualni nebo specifikovany projekt.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Filtr. Prazdne = posledni rozhodnuti."
                    },
                    "project": {
                        "type": "string",
                        "description": "Konkretni projekt. Default: aktualni."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Pocet vysledku (default 5).",
                        "default": 5
                    }
                }
            }
        ),
        Tool(
            name="verify_identity",
            description=(
                "POVINNE pred jakymkoliv deployem, SSH, push, PM2, DB migraci. "
                "Overi Identity Card a vrati VERIFIED/BLOCKED/WARNING."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "description": "deploy|ssh|push|pm2|db-migrate|docker-remote|proxy-reload|service-mgmt",
                        "enum": ["deploy", "ssh", "push", "pm2", "db-migrate",
                                 "docker-remote", "proxy-reload", "service-mgmt"]
                    }
                },
                "required": ["action_type"]
            }
        ),
        Tool(
            name="identity_set",
            description="Nastav pole Project Identity Card.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "object",
                        "description": "Klice a hodnoty k nastaveni. Napr: {\"deploy_ssh_alias\": \"my-server\", \"deploy_app_port\": 3000}"
                    },
                    "lock_safety": {
                        "type": "boolean",
                        "description": "Zamknout safety pole?",
                        "default": False
                    }
                },
                "required": ["fields"]
            }
        ),
        Tool(
            name="recommend_tech",
            description="Doporuc technologicky stack na zaklade podobnych projektu.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Popis projektu (jednoduchy web, SaaS...)"
                    },
                    "similar_to": {
                        "type": "string",
                        "description": "Nazev existujiciho projektu k inspiraci."
                    },
                    "category": {
                        "type": "string",
                        "description": "saas-app|agency-site|simple-website|ecommerce|api|cli-tool"
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
            result = f"Neznamy nastroj: {name}"
    except Exception as e:
        result = f"Chyba v {name}: {str(e)}"

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
        for t in tools:
            print(f"  - {t.name}: {t.description[:60]}...")
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
