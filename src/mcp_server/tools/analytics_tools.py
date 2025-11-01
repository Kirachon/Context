"""
Analytics MCP Tools (Story 5-3)
"""

import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from fastmcp import FastMCP
from src.analytics.usage import usage
from src.security.authz import require_role, Roles
from src.security.audit import record_event
from src.mcp_server.tools.instrumentation import instrument_tool


def register_analytics_tools(mcp: FastMCP):
    @mcp.tool()
    @instrument_tool("analytics_incr")
    async def analytics_incr(key: str, count: int = 1) -> Dict[str, Any]:
        usage().incr(key, count)
        return {
            "success": True,
            "value": usage().get(key),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    @instrument_tool("analytics_all")
    async def analytics_all() -> Dict[str, Any]:
        return {
            "success": True,
            "counters": usage().all(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @mcp.tool()
    @instrument_tool("analytics_reset")
    @require_role([Roles.ADMIN])
    async def analytics_reset() -> Dict[str, Any]:
        usage().reset()
        record_event("analytics_reset", "mcp", {"actor_role": Roles.ADMIN})
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
