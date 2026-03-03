"""CogniLayer MCP Server — V3 (FTS5 + vector + linking + gap tracking + episodes + causal chains + Codex).

Entry point for the MCP server registered in ~/.claude/settings.json or ~/.codex/config.toml.
Provides 17 tools for Claude Code / Codex CLI to interact with CogniLayer memory and code intelligence.
"""

import logging
import sys
import json
from pathlib import Path

# Setup logging to file (stderr is used by MCP protocol, so we log to file)
LOG_DIR = Path.home() / ".cognilayer" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "cognilayer.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

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
from tools.memory_link import memory_link
from tools.memory_chain import memory_chain
from tools.session_init import session_init
from tools.code_index import code_index
from tools.code_search import code_search
from tools.code_context import code_context
from tools.code_impact import code_impact
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
        Tool(
            name="memory_link",
            description=t("tool.memory_link.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": t("tool.memory_link.param.source_id")
                    },
                    "target_id": {
                        "type": "string",
                        "description": t("tool.memory_link.param.target_id")
                    }
                },
                "required": ["source_id", "target_id"]
            }
        ),
        Tool(
            name="memory_chain",
            description=t("tool.memory_chain.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "cause_id": {
                        "type": "string",
                        "description": t("tool.memory_chain.param.cause_id")
                    },
                    "effect_id": {
                        "type": "string",
                        "description": t("tool.memory_chain.param.effect_id")
                    },
                    "relationship": {
                        "type": "string",
                        "description": t("tool.memory_chain.param.relationship"),
                        "default": "caused",
                        "enum": ["caused", "led_to", "blocked", "fixed", "broke"]
                    }
                },
                "required": ["cause_id", "effect_id"]
            }
        ),
        Tool(
            name="session_init",
            description=t("tool.session_init.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": t("tool.session_init.param.project_path")
                    }
                }
            }
        ),
        Tool(
            name="code_index",
            description=t("tool.code_index.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": t("tool.code_index.param.project_path")
                    },
                    "full": {
                        "type": "boolean",
                        "description": t("tool.code_index.param.full"),
                        "default": False
                    },
                    "time_budget": {
                        "type": "number",
                        "description": t("tool.code_index.param.time_budget"),
                        "default": 30.0
                    }
                }
            }
        ),
        Tool(
            name="code_search",
            description=t("tool.code_search.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": t("tool.code_search.param.query")
                    },
                    "kind": {
                        "type": "string",
                        "description": t("tool.code_search.param.kind")
                    },
                    "limit": {
                        "type": "integer",
                        "description": t("tool.code_search.param.limit"),
                        "default": 20
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="code_context",
            description=t("tool.code_context.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": t("tool.code_context.param.symbol")
                    },
                    "project_name": {
                        "type": "string",
                        "description": t("tool.code_context.param.project_name")
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="code_impact",
            description=t("tool.code_impact.desc"),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": t("tool.code_impact.param.symbol")
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": t("tool.code_impact.param.max_depth"),
                        "default": 3
                    },
                    "project_name": {
                        "type": "string",
                        "description": t("tool.code_impact.param.project_name")
                    }
                },
                "required": ["symbol"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    import time as _t
    _start = _t.time()
    logging.info("Tool call: %s args=%s", name, {k: str(v)[:50] for k, v in arguments.items()})
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
        elif name == "memory_link":
            result = memory_link(
                source_id=arguments["source_id"],
                target_id=arguments["target_id"]
            )
        elif name == "memory_chain":
            result = memory_chain(
                cause_id=arguments["cause_id"],
                effect_id=arguments["effect_id"],
                relationship=arguments.get("relationship", "caused")
            )
        elif name == "session_init":
            result = session_init(
                project_path=arguments.get("project_path")
            )
        elif name == "code_index":
            result = code_index(
                project_path=arguments.get("project_path"),
                full=arguments.get("full", False),
                time_budget=arguments.get("time_budget", 30.0)
            )
        elif name == "code_search":
            result = code_search(
                query=arguments["query"],
                kind=arguments.get("kind"),
                limit=arguments.get("limit", 20)
            )
        elif name == "code_context":
            result = code_context(
                symbol=arguments["symbol"],
                project_name=arguments.get("project_name")
            )
        elif name == "code_impact":
            result = code_impact(
                symbol=arguments["symbol"],
                max_depth=arguments.get("max_depth", 3),
                project_name=arguments.get("project_name")
            )
        else:
            result = t("server.unknown_tool", name=name)
    except Exception as e:
        logging.error("Tool %s failed in %.3fs: %s", name, _t.time() - _start, e, exc_info=True)
        result = t("server.tool_error", name=name, error=str(e))

    _elapsed = _t.time() - _start
    logging.info("Tool %s completed in %.3fs (%d chars)", name, _elapsed, len(result))
    return [TextContent(type="text", text=result)]


async def main():
    logging.info("CogniLayer MCP server starting (v%s)", get_version())

    # Auto-migrate schema on startup with retry (handles concurrent MCP server starts)
    import time as _time
    for attempt in range(3):
        try:
            from db import open_db
            from init_db import upgrade_schema
            db = open_db()
            upgrade_schema(db)
            db.close()
            logging.info("Schema migration OK")
            break
        except Exception as e:
            if attempt < 2:
                logging.warning("Schema migration attempt %d failed: %s, retrying...", attempt + 1, e)
                _time.sleep(0.5 * (attempt + 1))
            else:
                logging.warning("Schema migration failed after 3 attempts (non-fatal): %s", e)

    # Pre-load heavy native libraries BEFORE stdio_server takes over stdin/stdout.
    # ONNX Runtime (used by fastembed) and sqlite-vec hang when loaded after
    # stdin/stdout become MCP JSON-RPC pipes (likely due to OMP/BLAS thread init
    # conflicting with pipe I/O on Windows).
    try:
        from embedder import embed_text
        logging.info("Pre-loading embedding model...")
        embed_text("warmup")  # Forces model load while stdout is still free
        logging.info("Embedding model loaded OK")
    except Exception as e:
        logging.warning("Embedding model pre-load failed (non-fatal): %s", e)

    try:
        from db import open_db, ensure_vec
        _db = open_db()
        ensure_vec(_db)
        _db.close()
        logging.info("sqlite-vec pre-loaded OK")
    except Exception as e:
        logging.warning("sqlite-vec pre-load failed (non-fatal): %s", e)

    logging.info("Starting stdio transport...")
    async with stdio_server() as (read_stream, write_stream):
        logging.info("MCP server ready, waiting for requests")
        await server.run(read_stream, write_stream, server.create_initialization_options())


def get_version() -> str:
    """Read version from VERSION file."""
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "unknown"


def test_tools():
    """Quick test to verify all tools are registered."""
    import asyncio

    version = get_version()
    print(f"CogniLayer v{version}")

    async def _test():
        tools = await list_tools()
        print(f"Registered tools: {len(tools)}")
        for tool in tools:
            desc = tool.description[:60].encode("ascii", errors="replace").decode("ascii")
            print(f"  - {tool.name}: {desc}...")
        return len(tools)

    count = asyncio.run(_test())
    return count


if __name__ == "__main__":
    if "--test" in sys.argv:
        count = test_tools()
        if count == 17:
            print(f"\nOK: All {count} tools registered.")
        else:
            print(f"\nERROR: Expected 17 tools, got {count}.")
            sys.exit(1)
    else:
        import asyncio
        asyncio.run(main())
